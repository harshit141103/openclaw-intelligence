#!/usr/bin/env python3
"""
mock_data_qc.py - Mock data schema QC tool.

Validates task ``mock_data/`` overlays against canonical ``environment/``
schemas using the SAME contracts the harness uses at mock-stack import time.

Catches every failure mode that would crash the per-task mock-stack at
``_store.eager_load()``:

  Class A  required strict_int / strict_float / strict_bool blank or
           unparseable                                                  FAIL
  Class B  ragged CSV row (unquoted comma -> extra fields)              FAIL
  Class C  duplicate header columns                                     FAIL
  Class D  invalid UTF-8 in the CSV file                                FAIL
  Class E  missing required column (declared via strict_* helper)       FAIL
  Class F  primary-key collision (harness logs WARN + auto-suffixes)    MAJOR
  Schema   column-set / column-order / format drift vs canonical    FAIL/MAJOR/MINOR
  JSON     shape mismatch vs canonical                              MAJOR/MINOR

By default, ALSO runs a ``--live-import`` phase: copy canonical files to a
tmpdir, overlay the user's files on top, then ``exec`` the canonical
``*_data.py`` with ``__file__`` pointing into the merged tmpdir.  This is the
gold-standard verifier because it executes the exact import path the harness
uses.  Use ``--no-live-import`` to skip (faster, but less authoritative).

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

# Values that look bool-shaped to the format-drift detector.
BOOL_VALUES: Set[str] = {"true", "false", "yes", "no", "1", "0", "t", "f"}

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
    every CSV-backed table registered via ``_store.register(...)``:

      contracts[slug][csv_filename] = {
          required_int / required_float / required_bool: blank crashes
          required_present:                              column must exist
          optional:                                      anything goes
      }
      primary_keys[slug][csv_filename] = "<pk column name>"
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
        self._load()

    # ------------------------------------------------------------------
    # Public lookup API
    # ------------------------------------------------------------------

    def get_contract(self, slug: str, csv_filename: str) -> Optional[Dict[str, List[str]]]:
        return self.contracts.get(slug, {}).get(csv_filename)

    def get_primary_key(self, slug: str, csv_filename: str) -> Optional[str]:
        return self.primary_keys.get(slug, {}).get(csv_filename)

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
            for data_py in sorted(entry.glob("*_data.py")):
                try:
                    contracts, pks = self._parse_data_py(data_py)
                except Exception as exc:
                    print(
                        f"[INFO] CoercerContracts: cannot process "
                        f"{slug}/{data_py.name}: {exc}",
                        file=sys.stderr,
                    )
                    continue
                self.contracts[slug].update(contracts)
                self.primary_keys[slug].update(pks)

    # ------------------------------------------------------------------
    # Per-file parser
    # ------------------------------------------------------------------

    def _parse_data_py(
        self, path: Path
    ) -> Tuple[Dict[str, Dict[str, List[str]]], Dict[str, str]]:
        """Return ``(csv_filename -> contract, csv_filename -> primary_key)``."""
        src = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            print(
                f"[INFO] CoercerContracts: syntax error in {path.name}: {exc}",
                file=sys.stderr,
            )
            return {}, {}

        # 1. Walk all ``_coerce_<table>`` functions; build a name->contract map.
        coerce_contracts: Dict[str, Dict[str, List[str]]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("_coerce_"):
                coerce_contracts[node.name] = self._analyze_coerce_func(node)

        # 2. Walk all ``_store.register("table", primary_key="...",
        #    initial_loader=lambda: _coerce_T(_load("Y.csv", "T")))`` calls,
        #    binding each CSV filename to its contract + PK.
        contracts_out: Dict[str, Dict[str, List[str]]] = {}
        pks_out: Dict[str, str] = {}
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "register"
            ):
                continue
            pk = None
            loader = None
            for kw in node.keywords:
                if (kw.arg == "primary_key"
                    and isinstance(kw.value, ast.Constant)
                    and isinstance(kw.value.value, str)):
                    pk = kw.value.value
                elif kw.arg == "initial_loader":
                    loader = kw.value
            csv_file, coerce_func = self._extract_loader_target(loader)
            if csv_file is None:
                continue
            contract = coerce_contracts.get(coerce_func, _empty_contract()) \
                if coerce_func else _empty_contract()
            contracts_out[csv_file] = contract
            if pk is not None:
                pks_out[csv_file] = pk

        return contracts_out, pks_out

    @staticmethod
    def _extract_loader_target(
        node: Optional[ast.AST],
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Walk into a lambda / call expression to find the CSV filename and the
        wrapping ``_coerce_*`` function name, if any.

        Recognises:
          ``lambda: _coerce_X(_load("Y.csv", "X"))``       -> ("Y.csv", "_coerce_X")
          ``lambda: _load("Y.csv", "X")``                  -> ("Y.csv", None)
          ``lambda: [_strip_ctx(r) for r in _load(...)]``  -> ("Y.csv", None)
          ``lambda: _coerce_X([... _load(...) ...])``      -> ("Y.csv", "_coerce_X")
        """
        if node is None:
            return None, None
        if isinstance(node, ast.Lambda):
            node = node.body

        # ``_coerce_X(...)`` -- coerce wrapper
        if isinstance(node, ast.Call):
            func_name = _get_call_name(node.func)
            if func_name and func_name.startswith("_coerce_") and node.args:
                for sub in ast.walk(node.args[0]):
                    if (isinstance(sub, ast.Call)
                        and _get_call_name(sub.func) == "_load"
                        and sub.args
                        and isinstance(sub.args[0], ast.Constant)
                        and isinstance(sub.args[0].value, str)):
                        return sub.args[0].value, func_name
            if func_name == "_load" and node.args:
                if (isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                    return node.args[0].value, None

        # ``[_strip_ctx(r) for r in _load("Y.csv", "X")]`` -- list comp etc.
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call)
                and _get_call_name(sub.func) == "_load"
                and sub.args
                and isinstance(sub.args[0], ast.Constant)
                and isinstance(sub.args[0].value, str)):
                return sub.args[0].value, None

        return None, None

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


def _check_json(
    slug: str,
    fname: str,
    fpath: Path,
    schema: Dict,
    findings: List[Finding],
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

    task_shape = extract_shape(data)
    can_shape = schema["shape"]

    raw_findings: List[Tuple[str, str]] = []
    compare_json_shapes(can_shape, task_shape, fname, raw_findings)
    for sev, msg in raw_findings:
        findings.append(Finding(sev, slug, fname, msg))


# ---------------------------------------------------------------------------
# Live-import check -- gold standard, mirrors the harness exactly
# ---------------------------------------------------------------------------

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

    Only failures referencing an overlaid filename are reported as FAIL --
    canonical defects surface as INFO (not the user's concern).
    """
    overlay = task_dir / "mock_data"
    if not overlay.is_dir():
        return

    sys_path_added = False
    if str(env_dir) not in sys.path:
        sys.path.insert(0, str(env_dir))
        sys_path_added = True

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

                g: Dict[str, Any] = {
                    "__file__": str(fake),
                    "__name__": f"_mockqc_live_{task_name}_{slug}",
                }
                try:
                    exec(code, g)
                except Exception as exc:
                    msg = str(exc).split("\n")[0]
                    overlay_names = [
                        f.name for f in api_overlay.rglob("*") if f.is_file()
                    ]
                    is_overlay_caused = any(name in msg for name in overlay_names)
                    if is_overlay_caused:
                        findings.append(Finding(
                            "FAIL", slug, "",
                            f"Class A/E live-import: {msg}",
                        ))
                    else:
                        # Surface as INFO so the operator can still see it,
                        # but don't fail the task on canonical issues.
                        findings.append(Finding(
                            "INFO", slug, "",
                            f"live-import (non-overlay): {msg}",
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
        if sys_path_added:
            try:
                sys.path.remove(str(env_dir))
            except ValueError:
                pass


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
                _check_json(slug, fname, fpath, schema, findings)

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
            f"  Loaded contracts for {n_contracts} CSV files and "
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
