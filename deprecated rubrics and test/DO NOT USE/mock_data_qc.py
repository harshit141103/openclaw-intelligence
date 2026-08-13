#!/usr/bin/env python3
"""
mock_data_qc.py - Mock data schema QC tool.

Validates task ``mock_data/`` overlays against canonical ``environment/``
schemas using the SAME contracts the harness uses at mock-stack import time.

Catches every failure mode that would crash the per-task mock-stack at
``_store.eager_load()``:

  Class A  required strict_int / strict_float / strict_bool blank or
           unparseable                                                  FAIL
  Class B  ragged CSV row                                               FAIL
           JSON row missing a REQUIRED key (strict_* accessor)          FAIL
           JSON row ragged in optional keys only (harness tolerates)    MINOR
  Class C  duplicate header columns (CSV)                               FAIL
  Class D  invalid UTF-8 in the data file                               FAIL
  Class E  missing required column/key (declared via strict_* helper)   FAIL
  Class F  primary-key collision (harness logs WARN + auto-suffixes)    MAJOR
  Class G  table JSON not a top-level array of objects                  FAIL
  Schema   key-set / column-order / format drift vs canonical       FAIL/MAJOR/MINOR
  JSON     document shape mismatch vs canonical                     MAJOR/MINOR

Data format contract (post CSV->JSON migration):
  - Table JSON:    top-level ARRAY of flat row OBJECTS; every scalar cell
                   stored as a STRING ("true", "5400", "3200.00"); loaded
                   via ``read_json_with_ctx`` + strict_*/opt_* coercers.
  - NATIVE table:  top-level ARRAY of row OBJECTS with NATIVE JSON types,
                   loaded via a raw ``json.load`` loader (no coercer), e.g.
                   quickbooks invoices/bills.  The harness only requires
                   list-of-dicts + the declared primary key per row, so the
                   checker skips ragged/key-set checks for these.
  - Document JSON: top-level OBJECT with native JSON types; registered via
                   ``_store.register_document(...)``; shape-compared, plus
                   Class A when the document loader wraps a ``_coerce_*``.

By default, ALSO runs a ``--live-import`` phase: copy canonical files to a
tmpdir, overlay the user's files on top, then ``exec`` the canonical
``*_data.py`` with ``__file__`` pointing into the merged tmpdir.  This is the
gold-standard verifier because it executes the exact import path the harness
uses.  Attribution is baseline-driven: each canonical ``*_data.py`` is first
imported WITHOUT the overlay (cached per slug); an overlay run that fails
while the canonical baseline passes is overlay-caused (FAIL), otherwise it
is a pre-existing canonical defect (INFO).
Use ``--no-live-import`` to skip (faster, but less authoritative).

Standard library only, Python 3.7+.
"""

import argparse
import ast
import csv
import importlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEVERITY_RANK = {"FAIL": 4, "MAJOR": 3, "MINOR": 2, "INFO": 1, "PASS": 0}

# Filenames that mark a JSON file as a postman/swagger collection (not a schema).
COLLECTION_RE = re.compile(r"(postman|swagger|openapi|collection)", re.IGNORECASE)

# Regex for ISO-8601 dates / datetimes (used by format-drift detection).
ISO_DATE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}"
    r"(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$"
)

# Values that look bool-shaped to the format-drift detector.  Deliberately
# excludes "1"/"0"/"t"/"f": integer columns full of 0/1 would otherwise be
# misclassified as bool and spam INFO drift findings.
BOOL_VALUES: Set[str] = {"true", "false", "yes", "no"}

# Mirror of ``_mutable_store._TRUE_TOKENS`` / ``_FALSE_TOKENS``.  Kept in sync
# with /home/ec2-user/WildClawBench/environment/_mutable_store.py.
BOOL_TRUE_TOKENS = frozenset({"true", "1", "yes", "t", "y"})
BOOL_FALSE_TOKENS = frozenset({"false", "0", "no", "f", "n"})
BOOL_VALID_TOKENS = BOOL_TRUE_TOKENS | BOOL_FALSE_TOKENS

# Helper names from ``_mutable_store`` we recognise inside ``_coerce_*``
# function bodies.  These are the AUTHORITATIVE source of column contracts.
HELPER_REQUIRED_INT = {"strict_int"}
HELPER_REQUIRED_FLOAT = {"strict_float"}
HELPER_REQUIRED_BOOL = {"strict_bool"}
# ``strict_str`` and ``strict_csv_list`` raise on missing column but tolerate
# blank values, so they count as "column must exist in header" only.
HELPER_REQUIRED_PRESENT = {"strict_str", "strict_csv_list"}
HELPER_OPTIONAL = {"opt_int", "opt_float", "opt_bool", "opt_str", "opt_csv_list"}


# ---------------------------------------------------------------------------
# AST utility helpers
# ---------------------------------------------------------------------------

def _get_call_name(func_node: ast.AST) -> Optional[str]:
    """Return string function name from a Call's ``func`` node."""
    if isinstance(func_node, ast.Name):
        return func_node.id
    if isinstance(func_node, ast.Attribute):
        return func_node.attr
    return None


def _get_subscript_key(slice_node: ast.AST) -> Optional[str]:
    """Extract a string key from a Subscript slice (3.8 + 3.9+ compatible)."""
    if hasattr(ast, "Index") and isinstance(slice_node, ast.Index):  # type: ignore[attr-defined]
        inner = slice_node.value  # type: ignore[attr-defined]
    else:
        inner = slice_node
    if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
        return inner.value
    if hasattr(ast, "Str") and isinstance(inner, ast.Str):  # type: ignore[attr-defined]
        return inner.s  # type: ignore[attr-defined]
    return None


def _extract_column_arg(call: ast.Call) -> Optional[str]:
    """
    Given a Call node like ``strict_int(r, "col")``, return ``"col"``.
    Accepts positional column-name arg at index 1 or kwarg ``column="..."``.
    """
    if (len(call.args) >= 2
        and isinstance(call.args[1], ast.Constant)
        and isinstance(call.args[1].value, str)):
        return call.args[1].value
    for kw in call.keywords:
        if (kw.arg == "column"
            and isinstance(kw.value, ast.Constant)
            and isinstance(kw.value.value, str)):
            return kw.value.value
    return None


def _empty_contract() -> Dict[str, List[str]]:
    return {
        "required_int": [],
        "required_float": [],
        "required_bool": [],
        "required_present": [],
        "optional": [],
    }


# ---------------------------------------------------------------------------
# CoercerContracts -- AST parser for environment/<slug>-api/*_data.py
# ---------------------------------------------------------------------------

class CoercerContracts:
    """
    Parses each ``environment/<slug>-api/*_data.py`` file to extract, for
    every JSON-backed table registered via ``_store.register(...)``:

      contracts[slug][data_filename] = {
          required_int / required_float / required_bool: blank crashes
          required_present:                              key must exist
          optional:                                      anything goes
      }
      primary_keys[slug][data_filename] = "<pk key name>"

    Files registered via ``_store.register_document(...)`` (singleton
    document JSONs with native types) are recorded in
    ``documents[slug]`` so the checker can skip table-style validation.
    When a document loader wraps a ``_coerce_*`` function, its contract is
    kept in ``doc_contracts[slug]`` so Class A still runs on its rows.

    Tables whose loader is a raw ``json.load`` wrapper (no coercer) are
    recorded in ``native_tables[slug]``: the harness accepts heterogeneous
    native-typed rows there, requiring only the declared primary key.
    """

    # Promotion order for column classification: later entries override earlier.
    _PROMOTION_ORDER = [
        "optional",
        "required_present",
        "required_bool",
        "required_float",
        "required_int",
    ]

    def __init__(self, env_dir: str) -> None:
        self.env_dir = Path(env_dir)
        self.contracts: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
        self.primary_keys: Dict[str, Dict[str, str]] = {}
        self.documents: Dict[str, Set[str]] = {}
        self.native_tables: Dict[str, Set[str]] = {}
        self.doc_contracts: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public lookup API
    # ------------------------------------------------------------------

    def get_contract(self, slug: str, csv_filename: str) -> Optional[Dict[str, List[str]]]:
        return self.contracts.get(slug, {}).get(csv_filename)

    def get_primary_key(self, slug: str, csv_filename: str) -> Optional[str]:
        return self.primary_keys.get(slug, {}).get(csv_filename)

    def is_document(self, slug: str, filename: str) -> bool:
        return filename in self.documents.get(slug, set())

    def is_native(self, slug: str, filename: str) -> bool:
        return filename in self.native_tables.get(slug, set())

    def get_doc_contract(
        self, slug: str, filename: str
    ) -> Optional[Dict[str, List[str]]]:
        return self.doc_contracts.get(slug, {}).get(filename)

    # ------------------------------------------------------------------
    # Loader
    # ------------------------------------------------------------------

    def _load(self) -> None:
        for entry in sorted(self.env_dir.iterdir()):
            if not entry.is_dir() or not entry.name.endswith("-api"):
                continue
            slug = entry.name
            self.contracts[slug] = {}
            self.primary_keys[slug] = {}
            self.documents[slug] = set()
            self.native_tables[slug] = set()
            self.doc_contracts[slug] = {}
            for data_py in sorted(entry.glob("*_data.py")):
                try:
                    contracts, pks, docs, natives, doc_contracts = \
                        self._parse_data_py(data_py)
                except Exception as exc:
                    print(
                        f"[INFO] CoercerContracts: cannot process "
                        f"{slug}/{data_py.name}: {exc}",
                        file=sys.stderr,
                    )
                    continue
                self.contracts[slug].update(contracts)
                self.primary_keys[slug].update(pks)
                self.documents[slug].update(docs)
                self.native_tables[slug].update(natives)
                self.doc_contracts[slug].update(doc_contracts)

    # ------------------------------------------------------------------
    # Per-file parser
    # ------------------------------------------------------------------

    def _parse_data_py(
        self, path: Path
    ) -> Tuple[
        Dict[str, Dict[str, List[str]]],
        Dict[str, str],
        Set[str],
        Set[str],
        Dict[str, Dict[str, List[str]]],
    ]:
        """Return ``(contracts, primary_keys, documents, native_tables,
        doc_contracts)`` keyed by data filename."""
        src = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            print(
                f"[INFO] CoercerContracts: syntax error in {path.name}: {exc}",
                file=sys.stderr,
            )
            return {}, {}, set(), set(), {}

        # 1. Walk all ``_coerce*`` functions; build a name->contract map.
        coerce_contracts: Dict[str, Dict[str, List[str]]] = {}
        func_defs: Dict[str, ast.FunctionDef] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_defs[node.name] = node
                if node.name.startswith("_coerce"):
                    coerce_contracts[node.name] = self._analyze_coerce_func(node)

        # 2. Constant-resolution helpers: module-level simple assignments
        #    (for ``_bases = [... _load(...) ...]`` and dict-literal tables)
        #    and loader-kind classification (ctx-string vs raw json.load).
        module_assigns: Dict[str, ast.AST] = {}
        for stmt in tree.body:
            if (isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                module_assigns[stmt.targets[0].id] = stmt.value

        loader_kinds = self._classify_loaders(func_defs)

        contracts_out: Dict[str, Dict[str, List[str]]] = {}
        pks_out: Dict[str, str] = {}
        docs_out: Set[str] = set()
        natives_out: Set[str] = set()
        doc_contracts_out: Dict[str, Dict[str, List[str]]] = {}

        def bind_register(
            node: ast.Call, env: Optional[Dict[str, Any]]
        ) -> None:
            pk = None
            loader = None
            for kw in node.keywords:
                if kw.arg == "primary_key":
                    val = self._resolve_const(kw.value, env, module_assigns)
                    if isinstance(val, str):
                        pk = val
                elif kw.arg == "initial_loader":
                    loader = kw.value
            fname, coerce_func, loader_name = self._extract_loader_target(
                loader, func_defs, module_assigns, env,
            )
            if not isinstance(fname, str) or not fname:
                return
            if env is not None and not (path.parent / fname).exists():
                # Loop-unrolled / indirect resolution: only trust bindings
                # that point at a real file next to the *_data.py.
                return
            contract = coerce_contracts.get(coerce_func, _empty_contract()) \
                if coerce_func else _empty_contract()
            contracts_out[fname] = contract
            if pk is not None:
                pks_out[fname] = pk
            if (loader_name is not None
                    and loader_kinds.get(loader_name) == "raw"
                    and coerce_func is None):
                natives_out.add(fname)
            elif coerce_func is not None:
                natives_out.discard(fname)

        def bind_register_document(node: ast.Call) -> None:
            doc_loader = None
            for kw in node.keywords:
                if kw.arg == "initial_loader":
                    doc_loader = kw.value
            if doc_loader is None and len(node.args) >= 2:
                doc_loader = node.args[1]
            if (isinstance(doc_loader, ast.Name)
                    and doc_loader.id in func_defs):
                doc_loader = func_defs[doc_loader.id]
            fname, coerce_func, _kind = self._extract_loader_target(
                doc_loader, func_defs, module_assigns, None,
            )
            if fname is None:
                fname = self._find_json_filename(doc_loader)
            if fname is None:
                return
            docs_out.add(fname)
            if coerce_func and coerce_func in coerce_contracts:
                doc_contracts_out[fname] = coerce_contracts[coerce_func]

        def walk_registers(
            root: ast.AST, env: Optional[Dict[str, Any]]
        ) -> None:
            for node in ast.walk(root):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("register", "register_document")
                ):
                    continue
                if node.func.attr == "register_document":
                    if env is None:
                        bind_register_document(node)
                else:
                    bind_register(node, env)

        # Pass 1: direct registrations (constant filenames).
        walk_registers(tree, None)

        # Pass 2: registrations inside ``for k, v in <dict-literal>.items():``
        # loops -- unroll the loop and re-resolve with each binding.
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                for env in self._unroll_for(node, module_assigns):
                    for stmt in node.body:
                        walk_registers(stmt, env)

        return contracts_out, pks_out, docs_out, natives_out, doc_contracts_out

    @classmethod
    def _extract_loader_target(
        cls,
        node: Optional[ast.AST],
        func_defs: Optional[Dict[str, ast.FunctionDef]] = None,
        module_assigns: Optional[Dict[str, ast.AST]] = None,
        env: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Walk into a lambda / call / function-def to find the data filename,
        the wrapping ``_coerce*`` function name (if any), and the loader
        function name used (``_load`` vs ``_load_json``).

        Recognises:
          ``lambda: _coerce_X(_load("Y.json", "X"))``     -> ("Y.json", "_coerce_X", "_load")
          ``lambda: _load_json("Y.json")``                -> ("Y.json", None, "_load_json")
          ``lambda: [_coerce_x(r) for r in _load(...)]``  -> ("Y.json", "_coerce_x", "_load")
          ``lambda c=_csv: _coerce(_load(c, n), n)``      -> resolved via ``env`` defaults
          ``initial_loader=_load_users`` / ``lambda: _load_users()`` -> hops into the def
          ``lambda: [dict(b) for b in _bases]``           -> hops into the module assignment
        """
        loader_names = ("_load", "_load_json")
        func_defs = func_defs or {}
        module_assigns = module_assigns or {}
        if node is None:
            return None, None, None

        if isinstance(node, ast.Name) and node.id in func_defs:
            node = func_defs[node.id]

        local_env: Dict[str, Any] = dict(env) if env else {}
        if isinstance(node, ast.Lambda):
            args = node.args.args
            defaults = node.args.defaults
            if defaults:
                for arg, default in zip(args[-len(defaults):], defaults):
                    val = cls._resolve_const(default, local_env, module_assigns)
                    if val is not None:
                        local_env[arg.arg] = val
            node = node.body

        def filename_from(call: ast.Call) -> Optional[str]:
            if not call.args:
                return None
            val = cls._resolve_const(call.args[0], local_env, module_assigns)
            return val if isinstance(val, str) else None

        if isinstance(node, ast.Call):
            callee = _get_call_name(node.func)
            if (callee
                    and callee in func_defs
                    and callee not in loader_names
                    and not callee.startswith("_coerce")):
                node = func_defs[callee]

        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call):
                continue
            callee = _get_call_name(sub.func)
            if not (callee and callee.startswith("_coerce")):
                continue
            for arg in sub.args:
                for inner in ast.walk(arg):
                    if (isinstance(inner, ast.Call)
                            and _get_call_name(inner.func) in loader_names):
                        fname = filename_from(inner)
                        if fname:
                            return fname, callee, _get_call_name(inner.func)

        for sub in ast.walk(node):
            if not isinstance(sub, (ast.ListComp, ast.GeneratorExp)):
                continue
            elt_call = sub.elt if isinstance(sub.elt, ast.Call) else None
            callee = _get_call_name(elt_call.func) if elt_call else None
            if callee and callee.startswith("_coerce") and sub.generators:
                for inner in ast.walk(sub.generators[0].iter):
                    if (isinstance(inner, ast.Call)
                            and _get_call_name(inner.func) in loader_names):
                        fname = filename_from(inner)
                        if fname:
                            return fname, callee, _get_call_name(inner.func)

        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call)
                    and _get_call_name(sub.func) in loader_names):
                fname = filename_from(sub)
                if fname:
                    return fname, None, _get_call_name(sub.func)

        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id in module_assigns:
                assigned = module_assigns[sub.id]
                for inner in ast.walk(assigned):
                    if (isinstance(inner, ast.Call)
                            and _get_call_name(inner.func) in loader_names):
                        fname = filename_from(inner)
                        if fname:
                            return fname, None, _get_call_name(inner.func)

        return None, None, None

    @classmethod
    def _resolve_const(
        cls,
        node: Optional[ast.AST],
        env: Optional[Dict[str, Any]],
        module_assigns: Dict[str, ast.AST],
        depth: int = 0,
    ) -> Any:
        """Statically resolve a constant expression: literals, env-bound
        names, module-level assignments, and dict subscripts."""
        if node is None or depth > 5:
            return None
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if env and node.id in env:
                return env[node.id]
            target = module_assigns.get(node.id)
            if target is not None and target is not node:
                return cls._resolve_const(target, env, module_assigns, depth + 1)
            return None
        if isinstance(node, ast.Subscript):
            base = cls._resolve_const(node.value, env, module_assigns, depth + 1)
            key = _get_subscript_key(node.slice)
            if key is None:
                slice_node = node.slice
                if hasattr(ast, "Index") and isinstance(slice_node, ast.Index):  # type: ignore[attr-defined]
                    slice_node = slice_node.value  # type: ignore[attr-defined]
                key = cls._resolve_const(slice_node, env, module_assigns, depth + 1)
            if isinstance(base, dict):
                return base.get(key)
            return None
        try:
            return ast.literal_eval(node)
        except Exception:
            return None

    @classmethod
    def _unroll_for(
        cls, node: ast.For, module_assigns: Dict[str, ast.AST]
    ) -> List[Dict[str, Any]]:
        """For ``for k, v in <resolvable-dict>.items():`` return one env
        dict per entry; otherwise return []."""
        it = node.iter
        if not (isinstance(it, ast.Call)
                and isinstance(it.func, ast.Attribute)
                and it.func.attr == "items"
                and not it.args and not it.keywords):
            return []
        mapping = cls._resolve_const(it.func.value, None, module_assigns)
        if not isinstance(mapping, dict):
            return []
        target = node.target
        if isinstance(target, ast.Tuple) and len(target.elts) == 2:
            k_node, v_node = target.elts[0], target.elts[1]
            if isinstance(k_node, ast.Name) and isinstance(v_node, ast.Name):
                return [
                    {k_node.id: k, v_node.id: v} for k, v in mapping.items()
                ]
        return []

    @staticmethod
    def _classify_loaders(
        func_defs: Dict[str, ast.FunctionDef]
    ) -> Dict[str, str]:
        """Classify local loader defs: 'ctx' if the body calls
        ``read_json_with_ctx`` (string-cell rows), 'raw' if it calls
        ``json.load``/``json.loads`` (native-typed rows)."""
        kinds: Dict[str, str] = {"_load": "ctx", "_load_json": "raw"}
        for name, fn in func_defs.items():
            saw_ctx = False
            saw_raw = False
            for sub in ast.walk(fn):
                if isinstance(sub, ast.Call):
                    callee = _get_call_name(sub.func)
                    if callee == "read_json_with_ctx":
                        saw_ctx = True
                    elif callee in ("load", "loads"):
                        saw_raw = True
            if saw_ctx:
                kinds[name] = "ctx"
            elif saw_raw:
                kinds[name] = "raw"
        return kinds

    @staticmethod
    def _find_json_filename(node: Optional[ast.AST]) -> Optional[str]:
        if node is None:
            return None
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Constant)
                and isinstance(sub.value, str)
                and sub.value.endswith(".json")):
                return sub.value
        return None

    @classmethod
    def _analyze_coerce_func(
        cls, func_node: ast.FunctionDef
    ) -> Dict[str, List[str]]:
        """
        Classify every column referenced inside a ``_coerce_<table>`` body.

        Recognised forms:
          - ``strict_int(r, "col")``       -> required_int
          - ``strict_float(r, "col")``     -> required_float
          - ``strict_bool(r, "col")``      -> required_bool
          - ``strict_str(r, "col")``       -> required_present
          - ``strict_csv_list(r, "col")``  -> required_present
          - ``opt_*(r, "col", ...)``       -> optional
          - bare ``r["col"]`` subscript    -> required_present (column must exist)
        """
        col_class: Dict[str, str] = {}

        def promote(col: str, cls_name: str) -> None:
            prev = col_class.get(col, "optional")
            order = cls._PROMOTION_ORDER
            if order.index(cls_name) > order.index(prev):
                col_class[col] = cls_name

        for node in ast.walk(func_node):
            # Call form: helper(r, "col", ...)
            if isinstance(node, ast.Call):
                fname = _get_call_name(node.func)
                col = _extract_column_arg(node) if fname else None
                if not (fname and col):
                    continue
                if fname in HELPER_REQUIRED_INT:
                    promote(col, "required_int")
                elif fname in HELPER_REQUIRED_FLOAT:
                    promote(col, "required_float")
                elif fname in HELPER_REQUIRED_BOOL:
                    promote(col, "required_bool")
                elif fname in HELPER_REQUIRED_PRESENT:
                    promote(col, "required_present")
                elif fname in HELPER_OPTIONAL:
                    promote(col, "optional")
                continue

            # Subscript form: ``r["col"]`` / ``row["col"]``
            if isinstance(node, ast.Subscript):
                if (isinstance(node.value, ast.Name)
                    and node.value.id in ("r", "row")):
                    key = _get_subscript_key(node.slice)
                    if key is not None:
                        promote(key, "required_present")

        out = _empty_contract()
        for col, cls_name in col_class.items():
            out[cls_name].append(col)
        return out


# ---------------------------------------------------------------------------
# JSON shape extraction and comparison
# ---------------------------------------------------------------------------

def extract_shape(data: Any) -> Tuple:
    """Recursively extract structural shape from a JSON value."""
    if isinstance(data, dict):
        return ("dict", {k: extract_shape(v) for k, v in data.items()})
    if isinstance(data, list):
        elem = extract_shape(data[0]) if data else None
        return ("list", elem)
    return ("scalar", type(data).__name__)


def compare_json_shapes(
    can_shape: Tuple,
    task_shape: Tuple,
    path: str,
    out: List[Tuple[str, str]],
) -> None:
    """Append (severity, message) findings by comparing shapes recursively."""
    can_kind = can_shape[0]
    task_kind = task_shape[0] if task_shape else "none"

    if can_kind != task_kind:
        out.append((
            "MAJOR",
            f"type mismatch at '{path}': canonical={can_kind}, actual={task_kind}",
        ))
        return

    if can_kind == "dict":
        can_keys: Dict[str, Any] = can_shape[1]
        task_keys: Dict[str, Any] = task_shape[1]
        for key in sorted(can_keys):
            sub_path = f"{path}.{key}"
            if key not in task_keys:
                out.append(("MAJOR", f"missing canonical key '{sub_path}'"))
            else:
                compare_json_shapes(can_keys[key], task_keys[key], sub_path, out)
        for key in sorted(task_keys):
            if key not in can_keys:
                out.append(("MINOR", f"extra key '{path}.{key}' not in canonical"))

    elif can_kind == "list":
        can_elem = can_shape[1]
        task_elem = task_shape[1]
        if can_elem is not None and task_elem is not None:
            compare_json_shapes(can_elem, task_elem, f"{path}[]", out)
        elif can_elem is not None and task_elem is None:
            out.append((
                "INFO",
                f"canonical list at '{path}' is non-empty but task list is empty"
                " (cannot compare element shape)",
            ))


# ---------------------------------------------------------------------------
# Format/type drift detection (column-level, INFO only)
# ---------------------------------------------------------------------------

def classify_value(v: str) -> str:
    s = v.strip()
    if not s or s.lower() in ("null", "none", "na", "n/a"):
        return "null"
    if s.lower() in BOOL_VALUES:
        return "bool"
    if ISO_DATE_RE.match(s):
        return "date"
    try:
        int(s)
        return "int"
    except ValueError:
        pass
    try:
        float(s)
        return "float"
    except ValueError:
        pass
    return "str"


def detect_column_drift(
    col_name: str, values: List[str]
) -> Optional[Tuple[str, str]]:
    non_null = [v for v in values if v.strip() and v.strip().lower() not in ("null", "none")]
    if len(non_null) < 2:
        return None
    fmt_list = [classify_value(v) for v in non_null]
    counts: Dict[str, int] = defaultdict(int)
    for fmt in fmt_list:
        counts[fmt] += 1
    dominant = max(counts, key=lambda k: counts[k])
    minority = {k: n for k, n in counts.items() if k != dominant}
    if not minority:
        return None
    total = sum(counts.values())
    minority_count = sum(minority.values())
    if minority_count / total < 0.05:
        return None
    examples = [v for v in non_null if classify_value(v) != dominant][:3]
    msg = (
        f"column '{col_name}': format drift -- dominant={dominant}"
        f" ({counts[dominant]}/{total}), minority={dict(minority)}"
        f", example values={examples}"
    )
    return ("INFO", msg)


# ---------------------------------------------------------------------------
# EnvBaseline - canonical schema loader
# ---------------------------------------------------------------------------

class EnvBaseline:
    """Loads canonical schemas from environment/*-api/ directories."""

    def __init__(self, env_dir: str) -> None:
        self.env_dir = Path(env_dir)
        # schemas[slug][filename] = {"type": "csv"|"json", "columns"|"shape": ...}
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self._load()

    @staticmethod
    def _is_collection_json(filename: str) -> bool:
        return bool(COLLECTION_RE.search(filename))

    @staticmethod
    def _read_bytes(path: Path) -> bytes:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        return raw

    def _load_csv_schema(self, slug: str, path: Path) -> None:
        try:
            text = self._read_bytes(path).decode("utf-8", errors="replace")
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            reader = csv.reader(io.StringIO(text))
            header = next(reader, None)
            if not header or not any(h.strip() for h in header):
                print(
                    f"[WARN] ENV {slug}/{path.name}: empty/unparseable header",
                    file=sys.stderr,
                )
                return
            self.schemas[slug][path.name] = {
                "type": "csv",
                "columns": [h.strip() for h in header],
            }
        except Exception as exc:
            print(f"[WARN] ENV {slug}/{path.name}: {exc}", file=sys.stderr)

    def _load_json_schema(self, slug: str, path: Path) -> None:
        if self._is_collection_json(path.name):
            return
        try:
            text = self._read_bytes(path).decode("utf-8", errors="replace")
            if not text.strip():
                return
            data = json.loads(text)
            self.schemas[slug][path.name] = {
                "type": "json",
                "shape": extract_shape(data),
            }
        except Exception as exc:
            print(f"[WARN] ENV {slug}/{path.name}: {exc}", file=sys.stderr)

    def _load(self) -> None:
        for entry in sorted(self.env_dir.iterdir()):
            if not entry.is_dir() or not entry.name.endswith("-api"):
                continue
            slug = entry.name
            self.schemas[slug] = {}
            for f in sorted(entry.iterdir()):
                if f.name.startswith("__") or f.is_dir():
                    continue
                if f.suffix == ".csv":
                    self._load_csv_schema(slug, f)
                elif f.suffix == ".json":
                    self._load_json_schema(slug, f)

    def get_slugs(self) -> Set[str]:
        return set(self.schemas.keys())

    def get_files(self, slug: str) -> Set[str]:
        return set(self.schemas.get(slug, {}).keys())

    def get_schema(self, slug: str, filename: str) -> Optional[Dict]:
        return self.schemas.get(slug, {}).get(filename)


# ---------------------------------------------------------------------------
# Finding + Verdict
# ---------------------------------------------------------------------------

class Finding:
    __slots__ = ("severity", "service", "filename", "message")

    def __init__(
        self, severity: str, service: str, filename: str, message: str
    ) -> None:
        self.severity = severity
        self.service = service
        self.filename = filename
        self.message = message

    def __str__(self) -> str:
        loc = self.service + (f"/{self.filename}" if self.filename else "")
        return f"  [{self.severity}] {loc}: {self.message}"


def compute_verdict(findings: List[Finding]) -> str:
    sevs = {f.severity for f in findings}
    if "FAIL" in sevs:
        return "FAIL"
    if "MAJOR" in sevs:
        return "MAJOR_ISSUES"
    if "MINOR" in sevs:
        return "MINOR_ISSUES"
    return "PASS"


# ---------------------------------------------------------------------------
# Class A / B / C / F check helpers
# ---------------------------------------------------------------------------

def _check_class_b(
    slug: str,
    fname: str,
    text: str,
    findings: List[Finding],
) -> None:
    """
    Class B -- raw field-count check.

    Uses ``csv.reader`` (which honours quoted commas) and verifies every data
    row has exactly as many fields as the header.  Properly quoted commas do
    NOT trigger this check.
    """
    try:
        reader = csv.reader(io.StringIO(text))
        header = next(reader, None)
        if header is None:
            return
        expected = len(header)
        for row_num, row in enumerate(reader, start=2):
            actual = len(row)
            if actual != expected:
                findings.append(Finding(
                    "FAIL", slug, fname,
                    f"Class B: ragged row {row_num} has {actual} fields, "
                    f"expected {expected} (likely an unquoted comma -- quote the cell)",
                ))
    except Exception:
        # If raw parse fails entirely, DictReader will surface it too.
        pass


def _check_class_a(
    slug: str,
    fname: str,
    rows: List[Dict[str, str]],
    contract: Dict[str, List[str]],
    findings: List[Finding],
) -> None:
    """
    Class A -- coercer crash prediction.

      required_int   -> non-blank AND int-parseable
      required_float -> non-blank AND float-parseable AND finite
      required_bool  -> non-blank AND token in BOOL_VALID_TOKENS

    OPTIONAL and REQUIRED_PRESENT columns are silently skipped here.
    """
    req_int = set(contract.get("required_int", []))
    req_float = set(contract.get("required_float", []))
    req_bool = set(contract.get("required_bool", []))

    for row_num, row in enumerate(rows, start=2):

        for col in req_int:
            val = row.get(col)
            if val is None:
                val = ""
            val = str(val).strip()
            if not val:
                findings.append(Finding(
                    "FAIL", slug, fname,
                    f"Class A: required-int '{col}' blank at row {row_num} "
                    f"-- crashes task at import",
                ))
                continue
            try:
                int(val)
            except ValueError:
                findings.append(Finding(
                    "FAIL", slug, fname,
                    f"Class A: required-int '{col}' non-int value '{val[:40]}' "
                    f"at row {row_num} -- crashes task at import",
                ))

        for col in req_float:
            val = row.get(col)
            if val is None:
                val = ""
            val = str(val).strip()
            if not val:
                findings.append(Finding(
                    "FAIL", slug, fname,
                    f"Class A: required-float '{col}' blank at row {row_num} "
                    f"-- crashes task at import",
                ))
                continue
            try:
                f = float(val)
            except ValueError:
                findings.append(Finding(
                    "FAIL", slug, fname,
                    f"Class A: required-float '{col}' non-float value '{val[:40]}' "
                    f"at row {row_num} -- crashes task at import",
                ))
                continue
            # _mutable_store.strict_float rejects NaN / +-inf as well.
            if f != f or f in (float("inf"), float("-inf")):
                findings.append(Finding(
                    "FAIL", slug, fname,
                    f"Class A: required-float '{col}' non-finite value '{val[:40]}' "
                    f"at row {row_num} -- crashes task at import",
                ))

        for col in req_bool:
            val = row.get(col)
            if val is None:
                val = ""
            val = str(val).strip()
            if not val:
                findings.append(Finding(
                    "FAIL", slug, fname,
                    f"Class A: required-bool '{col}' blank at row {row_num} "
                    f"-- crashes task at import",
                ))
                continue
            if val.lower() not in BOOL_VALID_TOKENS:
                findings.append(Finding(
                    "FAIL", slug, fname,
                    f"Class A: required-bool '{col}' unrecognized value '{val[:40]}' "
                    f"at row {row_num} (expected one of "
                    f"{sorted(BOOL_VALID_TOKENS)}) -- crashes task at import",
                ))


def _check_pk_uniqueness(
    slug: str,
    fname: str,
    rows: List[Dict[str, str]],
    primary_key: Optional[str],
    findings: List[Finding],
) -> None:
    """
    Class F -- primary-key collision warning.

    Uses the column DECLARED in ``_store.register(..., primary_key=...)``.
    The harness silently auto-suffixes colliders with ``_pk`` so this doesn't
    crash imports, but downstream joins on the natural key get mangled --
    flag at MAJOR.
    """
    if not rows or not primary_key:
        return
    sample = rows[0]
    if primary_key not in sample:
        # PK column missing from header -- the missing-columns check already
        # flagged it; don't double-report.
        return

    seen: Dict[str, int] = {}
    duplicates: List[Tuple[str, int, int]] = []

    for row_num, row in enumerate(rows, start=2):
        val = str(row.get(primary_key, "")).strip()
        if not val:
            continue
        if val in seen:
            duplicates.append((val, seen[val], row_num))
        else:
            seen[val] = row_num

    if duplicates:
        examples = duplicates[:3]
        detail = "; ".join(
            f"{primary_key}='{v}' at rows {r1} and {r2}"
            for v, r1, r2 in examples
        )
        findings.append(Finding(
            "MAJOR", slug, fname,
            f"Class F: declared primary_key='{primary_key}' has "
            f"{len(duplicates)} collision(s) -- harness auto-suffixes '_pk' "
            f"but downstream joins will mismatch. {detail}",
        ))


# ---------------------------------------------------------------------------
# Per-file checks
# ---------------------------------------------------------------------------

def _read_task_bytes(fpath: Path) -> bytes:
    raw = fpath.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw


def _check_csv(
    slug: str,
    fname: str,
    fpath: Path,
    schema: Dict,
    strict_order: bool,
    findings: List[Finding],
    contract: Optional[Dict[str, List[str]]] = None,
    primary_key: Optional[str] = None,
) -> None:
    # Class D -- strict UTF-8.
    try:
        raw = _read_task_bytes(fpath)
    except Exception as exc:
        findings.append(Finding("FAIL", slug, fname, f"cannot read file: {exc}"))
        return

    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        findings.append(Finding(
            "FAIL", slug, fname,
            f"Class D: invalid UTF-8 ({exc}) -- crashes task at import",
        ))
        return

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    if not text.strip():
        findings.append(Finding("FAIL", slug, fname, "empty file"))
        return

    # Class B -- ragged-row check (raw csv.reader, before DictReader collapses).
    _check_class_b(slug, fname, text, findings)

    # Parse header.
    try:
        f_io = io.StringIO(text)
        reader = csv.DictReader(f_io)
        fieldnames = reader.fieldnames
    except Exception as exc:
        findings.append(Finding("FAIL", slug, fname, f"unparseable CSV: {exc}"))
        return

    if fieldnames is None or not any(h.strip() for h in fieldnames):
        findings.append(Finding("FAIL", slug, fname, "empty or missing CSV header"))
        return

    task_cols = [h.strip() for h in fieldnames]

    # Class C -- duplicate header columns.
    seen_cols: Dict[str, int] = defaultdict(int)
    for col in task_cols:
        seen_cols[col] += 1
    dupe_cols = sorted({c for c, n in seen_cols.items() if n > 1})
    if dupe_cols:
        findings.append(Finding(
            "FAIL", slug, fname,
            f"Class C: duplicate header columns {dupe_cols} "
            f"-- crashes task at import",
        ))

    # Schema column comparison.
    can_cols: List[str] = schema["columns"]
    can_set = set(can_cols)
    task_set = set(task_cols)

    missing = sorted(can_set - task_set)
    extra = sorted(task_set - can_set)

    if missing:
        # Class E -- missing canonical column = strict_* crash if it's strict.
        findings.append(Finding(
            "FAIL", slug, fname,
            f"missing canonical columns: {missing}",
        ))
    if extra:
        findings.append(Finding(
            "MAJOR", slug, fname,
            f"extra columns not in canonical: {extra}; canonical={can_cols}",
        ))

    if not missing and not extra and task_cols != can_cols:
        sev = "FAIL" if strict_order else "MINOR"
        suffix = " [promoted by --strict-order]" if strict_order else ""
        findings.append(Finding(
            sev, slug, fname,
            f"column order differs from canonical{suffix}; "
            f"canonical={can_cols}, actual={task_cols}",
        ))

    # Read rows for Class A + F + drift.
    rows: List[Dict[str, str]] = []
    try:
        for row in csv.DictReader(io.StringIO(text)):
            rows.append({k: (v or "") for k, v in row.items() if k is not None})
    except Exception:
        rows = []

    # Class A
    if contract and rows:
        _check_class_a(slug, fname, rows, contract, findings)

    # Class F
    if rows:
        _check_pk_uniqueness(slug, fname, rows, primary_key, findings)

    # Format drift (INFO).
    try:
        col_values: Dict[str, List[str]] = defaultdict(list)
        for row in rows:
            for col, val in row.items():
                if col and col.strip() in can_set:
                    col_values[col.strip()].append(val or "")
        for col, vals in col_values.items():
            result = detect_column_drift(col, vals)
            if result:
                sev, msg = result
                findings.append(Finding(sev, slug, fname, msg))
    except Exception:
        pass


def _is_table_shape(shape: Optional[Tuple]) -> bool:
    return (
        isinstance(shape, tuple)
        and shape[0] == "list"
        and isinstance(shape[1], tuple)
        and shape[1][0] == "dict"
    )


def _stringify_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _check_json_table(
    slug: str,
    fname: str,
    data,
    can_shape: Tuple,
    contract: Optional[Dict[str, List[str]]],
    primary_key: Optional[str],
    findings: List[Finding],
    native: bool = False,
) -> None:
    if not isinstance(data, list) or any(not isinstance(r, dict) for r in data):
        findings.append(Finding(
            "FAIL", slug, fname,
            "Class G: table JSON must be a top-level array of objects -- "
            "read_json_with_ctx raises CoerceError at import",
        ))
        return

    can_elem = can_shape[1][1] if _is_table_shape(can_shape) else None
    can_keys = set(can_elem.keys()) if can_elem else None

    if not data:
        if can_keys:
            findings.append(Finding(
                "INFO", slug, fname,
                "task table is empty; canonical has rows (allowed if intended)",
            ))
        return

    header = list(data[0].keys())
    header_set = set(header)

    if contract:
        for col in sorted(contract.get("required_present", [])):
            missing_rows = [
                idx for idx, row in enumerate(data, start=1)
                if col not in row
            ]
            if missing_rows:
                findings.append(Finding(
                    "FAIL", slug, fname,
                    f"Class B/E: required key '{col}' absent at row(s) "
                    f"{missing_rows[:5]}{' ...' if len(missing_rows) > 5 else ''}"
                    f" -- strict accessor raises at import",
                ))

    if native:
        if primary_key:
            missing_pk = [
                idx for idx, row in enumerate(data, start=1)
                if primary_key not in row
            ]
            if missing_pk:
                findings.append(Finding(
                    "FAIL", slug, fname,
                    f"primary key '{primary_key}' absent at row(s) "
                    f"{missing_pk[:5]}{' ...' if len(missing_pk) > 5 else ''}"
                    f" -- StoreError 'missing primary key' at import",
                ))
    else:
        ragged = [
            idx for idx, row in enumerate(data, start=1)
            if set(row.keys()) != header_set
        ]
        if ragged:
            findings.append(Finding(
                "MINOR", slug, fname,
                f"Class B: ragged object keys vs first object at row(s) "
                f"{ragged[:5]}{' ...' if len(ragged) > 5 else ''} -- "
                f"harness tolerates this; required-key absences are "
                f"reported separately as FAIL",
            ))

        if can_keys is not None:
            missing = sorted(can_keys - header_set)
            extra = sorted(header_set - can_keys)
            if missing:
                findings.append(Finding(
                    "FAIL", slug, fname,
                    f"Class E: missing canonical keys: {missing}",
                ))
            if extra:
                findings.append(Finding(
                    "MAJOR", slug, fname,
                    f"extra non-canonical keys: {extra}",
                ))

            for key in sorted(header_set & can_keys):
                can_kind = can_elem.get(key) if can_elem else None
                if can_kind != ("scalar", "str"):
                    continue
                for row in data:
                    val = row.get(key)
                    if val is not None and not isinstance(val, (str, dict, list)):
                        findings.append(Finding(
                            "MINOR", slug, fname,
                            f"key '{key}': native {type(val).__name__} value "
                            f"where canonical stores strings "
                            f"(table-JSON cells are quoted strings)",
                        ))
                        break

    rows_str = [
        {k: _stringify_cell(v) for k, v in row.items()}
        for row in data
    ]

    if contract:
        _check_class_a(slug, fname, rows_str, contract, findings)
    _check_pk_uniqueness(slug, fname, rows_str, primary_key, findings)

    if native:
        return

    try:
        if can_elem:
            check_cols = sorted(
                key for key in header_set & set(can_elem.keys())
                if can_elem.get(key) == ("scalar", "str")
            )
        else:
            check_cols = header
        for col in check_cols:
            vals = [r.get(col, "") for r in rows_str]
            result = detect_column_drift(col, vals)
            if result:
                sev, msg = result
                findings.append(Finding(sev, slug, fname, msg))
    except Exception:
        pass


def _check_json(
    slug: str,
    fname: str,
    fpath: Path,
    schema: Dict,
    findings: List[Finding],
    contract: Optional[Dict[str, List[str]]] = None,
    primary_key: Optional[str] = None,
    is_document: bool = False,
    native: bool = False,
    doc_contract: Optional[Dict[str, List[str]]] = None,
) -> None:
    try:
        raw = _read_task_bytes(fpath)
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        findings.append(Finding(
            "FAIL", slug, fname,
            f"Class D: invalid UTF-8 ({exc}) -- crashes task at import",
        ))
        return
    except Exception as exc:
        findings.append(Finding("FAIL", slug, fname, f"cannot read file: {exc}"))
        return

    if not text.strip():
        findings.append(Finding("FAIL", slug, fname, "empty file"))
        return

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        findings.append(Finding("FAIL", slug, fname, f"invalid JSON: {exc}"))
        return

    can_shape = schema["shape"]

    table_mode = not is_document and (
        _is_table_shape(can_shape)
        or contract is not None
        or primary_key is not None
    )
    if table_mode:
        _check_json_table(
            slug, fname, data, can_shape, contract, primary_key, findings,
            native,
        )
        return

    if is_document and doc_contract:
        if isinstance(data, list) and all(isinstance(r, dict) for r in data):
            doc_rows = [
                {k: _stringify_cell(v) for k, v in row.items()}
                for row in data
            ]
            _check_class_a(slug, fname, doc_rows, doc_contract, findings)
        elif isinstance(data, dict):
            doc_rows = [{k: _stringify_cell(v) for k, v in data.items()}]
            _check_class_a(slug, fname, doc_rows, doc_contract, findings)

    task_shape = extract_shape(data)

    raw_findings: List[Tuple[str, str]] = []
    compare_json_shapes(can_shape, task_shape, fname, raw_findings)
    for sev, msg in raw_findings:
        findings.append(Finding(sev, slug, fname, msg))


# ---------------------------------------------------------------------------
# Live-import check -- gold standard, mirrors the harness exactly
# ---------------------------------------------------------------------------

_CANON_BASELINE: Dict[str, Optional[str]] = {}


def _canonical_baseline_error(slug: str, canon: Path) -> Optional[str]:
    """Exec the canonical ``*_data.py`` against its own data dir and cache
    the first-line error (or None).  Attribution anchor: if the canonical
    import succeeds, any merged-overlay failure must be overlay-caused."""
    if slug in _CANON_BASELINE:
        return _CANON_BASELINE[slug]
    err: Optional[str] = None
    try:
        code = compile(canon.read_text(), str(canon), "exec")
        g: Dict[str, Any] = {
            "__file__": str(canon),
            "__name__": f"_mockqc_base_{slug}",
        }
        exec(code, g)
    except Exception as exc:
        err = str(exc).split("\n")[0]
    finally:
        try:
            _ms = importlib.import_module("_mutable_store")
            _ms._STORES.pop(slug, None)  # type: ignore[attr-defined]
        except Exception:
            pass
    _CANON_BASELINE[slug] = err
    return err


def _live_import_check(
    task_name: str,
    task_dir: Path,
    env_dir: Path,
    findings: List[Finding],
) -> None:
    """
    Replicate the harness's overlay-on-canonical merge in a tmpdir, then
    ``exec`` each canonical ``*_data.py`` with ``__file__`` resolving inside
    that tmpdir.  Any exception raised by ``_store.eager_load()`` is a real
    harness failure.

    Attribution is baseline-driven: the canonical module is exec'd once
    against its own data (cached per slug).  If the canonical import passes
    but the merged overlay import fails, the failure is overlay-caused
    (FAIL); if the canonical baseline itself fails, the merged failure is
    surfaced as INFO (canonical defect, not the user's concern).
    """
    overlay = task_dir / "mock_data"
    if not overlay.is_dir():
        return

    saved_sys_path = list(sys.path)
    if str(env_dir) not in sys.path:
        sys.path.insert(0, str(env_dir))

    try:
        with tempfile.TemporaryDirectory(prefix="mockqc_") as tmproot_str:
            tmproot = Path(tmproot_str)
            for api_overlay in sorted(overlay.iterdir()):
                if not api_overlay.is_dir():
                    continue
                slug = api_overlay.name
                canon_dir = env_dir / slug
                if not canon_dir.is_dir():
                    continue
                canon = next(canon_dir.glob("*_data.py"), None)
                if canon is None:
                    continue

                # Build merged dir: canonical base + user overlay on top.
                merged = tmproot / f"{task_name}__{slug}"
                shutil.copytree(canon_dir, merged)
                for f in api_overlay.rglob("*"):
                    if f.is_file():
                        rel = f.relative_to(api_overlay)
                        dst = merged / rel
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, dst)

                fake = merged / canon.name
                try:
                    code = compile(canon.read_text(), str(fake), "exec")
                except SyntaxError as exc:
                    # Canonical defect, not user's fault.
                    print(
                        f"[INFO] live-import: canonical SyntaxError in "
                        f"{slug}/{canon.name}: {exc}",
                        file=sys.stderr,
                    )
                    continue

                base_err = _canonical_baseline_error(slug, canon)

                g: Dict[str, Any] = {
                    "__file__": str(fake),
                    "__name__": f"_mockqc_live_{task_name}_{slug}",
                }
                try:
                    exec(code, g)
                except Exception as exc:
                    msg = str(exc).split("\n")[0]
                    if base_err is None:
                        findings.append(Finding(
                            "FAIL", slug, "",
                            f"live-import (overlay-caused): {msg}",
                        ))
                    else:
                        findings.append(Finding(
                            "INFO", slug, "",
                            f"live-import (canonical baseline also fails: "
                            f"{base_err}): {msg}",
                        ))
                finally:
                    # Clear the per-api singleton so the next task's overlay
                    # can re-import the same module cleanly.
                    try:
                        _ms = importlib.import_module("_mutable_store")
                        _ms._STORES.pop(slug, None)  # type: ignore[attr-defined]
                    except Exception:
                        pass
    finally:
        sys.path[:] = saved_sys_path


# ---------------------------------------------------------------------------
# Task QC
# ---------------------------------------------------------------------------

def check_task(
    task_name: str,
    task_dir: Path,
    baseline: EnvBaseline,
    strict_order: bool,
    contracts: Optional[CoercerContracts] = None,
    live_import: bool = False,
    env_dir: Optional[Path] = None,
) -> Tuple[str, List[Finding]]:
    """Run QC on one task. Returns (verdict, findings)."""
    findings: List[Finding] = []
    mock_data_dir = task_dir / "mock_data"

    if not mock_data_dir.exists():
        return "PASS", []

    known_slugs = baseline.get_slugs()

    for api_dir in sorted(mock_data_dir.iterdir()):
        if not api_dir.is_dir():
            findings.append(Finding(
                "MINOR", str(api_dir.name), "",
                "unexpected non-directory entry at mock_data level",
            ))
            continue

        slug = api_dir.name

        if slug not in known_slugs:
            findings.append(Finding(
                "FAIL", slug, "",
                f"unknown service not found in environment/ (no '{slug}' folder)",
            ))
            continue

        env_files = baseline.get_files(slug)

        task_files: Dict[str, Path] = {}
        for f in sorted(api_dir.iterdir()):
            if f.is_dir():
                findings.append(Finding(
                    "MINOR", slug, f.name,
                    "unexpected subdirectory (expected flat folder)",
                ))
                continue
            task_files[f.name] = f

        for fname in sorted(task_files):
            if Path(fname).suffix not in (".csv", ".json"):
                findings.append(Finding(
                    "MINOR", slug, fname,
                    f"non-schema file type '{Path(fname).suffix}' in mock_data",
                ))

        schema_task = {k for k in task_files if Path(k).suffix in (".csv", ".json")}

        for fname in sorted(schema_task):
            if fname not in env_files:
                findings.append(Finding(
                    "MAJOR", slug, fname,
                    f"file not present in canonical schema for '{slug}'",
                ))

        for fname in sorted(env_files):
            if fname not in schema_task:
                findings.append(Finding(
                    "INFO", slug, fname,
                    "canonical file absent from task mock_data "
                    "(canonical fallback will be used by harness)",
                ))

        for fname in sorted(schema_task):
            if fname not in env_files:
                continue
            schema = baseline.get_schema(slug, fname)
            if schema is None:
                findings.append(Finding(
                    "INFO", slug, fname,
                    "no canonical schema loaded for this file (skipped)",
                ))
                continue

            fpath = task_files[fname]
            if schema["type"] == "csv":
                contract = contracts.get_contract(slug, fname) if contracts else None
                pk = contracts.get_primary_key(slug, fname) if contracts else None
                _check_csv(
                    slug, fname, fpath, schema, strict_order, findings,
                    contract, pk,
                )
            elif schema["type"] == "json":
                contract = contracts.get_contract(slug, fname) if contracts else None
                pk = contracts.get_primary_key(slug, fname) if contracts else None
                is_doc = contracts.is_document(slug, fname) if contracts else False
                native = contracts.is_native(slug, fname) if contracts else False
                doc_contract = (
                    contracts.get_doc_contract(slug, fname) if contracts else None
                )
                _check_json(
                    slug, fname, fpath, schema, findings,
                    contract, pk, is_doc, native, doc_contract,
                )

    # Live-import phase (ground truth).
    if live_import and env_dir is not None:
        _live_import_check(task_name, task_dir, env_dir, findings)

    return compute_verdict(findings), findings


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_task_report(
    task_name: str,
    verdict: str,
    findings: List[Finding],
    verbose: bool,
    quiet: bool,
    no_mock_data: bool = False,
) -> None:
    if no_mock_data:
        if not quiet:
            print(f"\n{'='*62}")
            print(f"TASK: {task_name:<28}  PASS (no mock_data, skipped)")
            print(f"{'='*62}")
        return

    if quiet and verdict not in ("FAIL", "MAJOR_ISSUES"):
        return

    print(f"\n{'='*62}")
    print(f"TASK: {task_name:<28}  {verdict}")
    print(f"{'='*62}")

    if verbose:
        show = {"FAIL", "MAJOR", "MINOR", "INFO"}
    elif quiet:
        show = {"FAIL", "MAJOR"}
    else:
        show = {"FAIL", "MAJOR", "MINOR"}

    visible = [f for f in findings if f.severity in show]
    for f in visible:
        print(str(f))

    if not visible and not quiet:
        print("  (no issues to display)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

DEFAULT_ENV_DIR = "/home/ec2-user/WildClawBench/environment"
DEFAULT_TASKS_DIR = "/home/ec2-user/WildClawBench/input"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Mock data schema QC: validate task mock_data/ overlays against "
            "canonical environment/ schemas using harness-equivalent contracts."
        )
    )
    parser.add_argument(
        "--env-dir", default=DEFAULT_ENV_DIR,
        help=f"Path to the environment/ directory (default: {DEFAULT_ENV_DIR})",
    )
    parser.add_argument(
        "--tasks-dir", "--input-dir", dest="tasks_dir",
        default=DEFAULT_TASKS_DIR,
        help=f"Path to the tasks/input directory (default: {DEFAULT_TASKS_DIR})",
    )
    parser.add_argument(
        "--task",
        help="Check only this single task name (default: all tasks)",
    )
    parser.add_argument(
        "--strict-order", action="store_true",
        help="Promote CSV column order mismatches from MINOR to FAIL",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Only show FAIL/MAJOR findings and the summary table",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show all findings including INFO",
    )
    parser.add_argument(
        "--no-coercer", action="store_true",
        help=(
            "Skip *_data.py AST parsing -- runs Class B/C/D/F and existing "
            "structural checks only; skips Class A (coercer crash)"
        ),
    )
    parser.add_argument(
        "--no-live-import", action="store_true",
        help=(
            "Skip the live-import phase (faster but less authoritative). "
            "Default is to RUN live-import."
        ),
    )
    args = parser.parse_args()

    env_dir = Path(args.env_dir)
    tasks_dir = Path(args.tasks_dir)

    for p, label in [(env_dir, "--env-dir"), (tasks_dir, "--tasks-dir")]:
        if not p.exists():
            print(f"ERROR: {label} does not exist: {p}", file=sys.stderr)
            return 1

    print(f"Loading canonical schemas from {env_dir} ...")
    baseline = EnvBaseline(str(env_dir))
    n_slugs = len(baseline.get_slugs())
    n_files = sum(len(v) for v in baseline.schemas.values())
    print(f"  Discovered {n_slugs} API services, {n_files} schema files total.")

    contracts: Optional[CoercerContracts] = None
    if not args.no_coercer:
        print("Parsing coercer contracts from *_data.py files ...")
        contracts = CoercerContracts(str(env_dir))
        n_contracts = sum(len(v) for v in contracts.contracts.values())
        n_pks = sum(len(v) for v in contracts.primary_keys.values())
        print(
            f"  Loaded contracts for {n_contracts} data files and "
            f"{n_pks} primary keys across {n_slugs} services."
        )

    live_import = not args.no_live_import
    if live_import:
        print(
            "Live-import phase ENABLED (canonical+overlay merge in tmpdir, "
            "executes canonical *_data.py)."
        )
    else:
        print("Live-import phase DISABLED (--no-live-import).")

    if args.task:
        task_dir_arg = tasks_dir / args.task
        if not task_dir_arg.exists():
            print(
                f"ERROR: task '{args.task}' not found in {tasks_dir}",
                file=sys.stderr,
            )
            return 1
        task_dirs = [task_dir_arg]
    else:
        task_dirs = sorted(d for d in tasks_dir.iterdir() if d.is_dir())

    results: List[Tuple[str, str, List[Finding], bool]] = []
    any_fail = False

    for task_dir in task_dirs:
        task_name = task_dir.name
        has_mock_data = (task_dir / "mock_data").exists()

        if not has_mock_data:
            print_task_report(
                task_name, "PASS", [], args.verbose, args.quiet,
                no_mock_data=True,
            )
            results.append((task_name, "PASS (no mock_data)", [], True))
            continue

        verdict, findings = check_task(
            task_name, task_dir, baseline, args.strict_order, contracts,
            live_import=live_import, env_dir=env_dir,
        )
        print_task_report(task_name, verdict, findings, args.verbose, args.quiet)
        results.append((task_name, verdict, findings, False))

        if verdict == "FAIL":
            any_fail = True

    # Summary table.
    print(f"\n{'='*62}")
    print("FINAL SUMMARY")
    print(f"{'='*62}")
    hdr = f"{'Task':<60} {'Verdict':<18} Findings"
    print(hdr)
    print("-" * len(hdr))
    for task_name, verdict, findings, skipped in results:
        if skipped:
            print(f"  {task_name:<60} {verdict:<18}")
        else:
            fc = sum(1 for f in findings if f.severity == "FAIL")
            mc = sum(1 for f in findings if f.severity == "MAJOR")
            nc = sum(1 for f in findings if f.severity == "MINOR")
            ic = sum(1 for f in findings if f.severity == "INFO")
            detail = (
                f"FAIL={fc} MAJOR={mc} MINOR={nc} INFO={ic}"
                if findings else "clean"
            )
            print(f"  {task_name:<60} {verdict:<18} {detail}")

    print()
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
