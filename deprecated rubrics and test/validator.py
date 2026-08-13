"""
validator.py — Stage 5 of the v2 generator.

Validates the single-file ``rubric.json`` against the v2 contract:

  * 7-field schema (no trap_concept stored on criteria)
  * valid enums (type, evaluation_target, importance, score)
  * prefix rule ("The response" / "The agent")
  * §5A criterion writing rules (Rule 1/2/3/4 + score-polarity lock)
  * disjointness from ``test_outputs.py``
  * requirements coverage against ``requirements.json`` (Stage 1 inventory)
  * trap-coverage: every trap concept present in pytest also appears
    somewhere in rubric criterion prose
  * Value Lock present in mock_data tree

Pure Python — no LLM calls.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter
from pathlib import Path

import golden_steer_parser
import mock_data_reader

VALID_TYPES = {
    "task completion", "instruction following", "factuality and hallucination",
    "tool use", "agent behavior", "safety & boundaries",
}
VALID_EVAL_TARGETS = {
    "state_change", "user_facing_message", "trajectory", "final_answer",
}
VALID_IMPORTANCE = {"critically_important", "important"}
VALID_SCORES = {-5, -3, -1, 1, 3, 5}
REAL_TRAP_CONCEPTS = {
    "silent_mutation", "backend_writeback", "red_line",
    "cross_modal_contradiction", "decoy_value", "temporal_revision",
}

REQUIRED_FIELDS = {
    "number", "criterion", "is_positive", "type",
    "evaluation_target", "importance", "score",
}

PREFIX_RULE: dict[str, str] = {
    "user_facing_message": "The response",
    "final_answer": "The response",
    "state_change": "The agent",
    "trajectory": "The agent",
}

STOPWORDS: set[str] = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "was", "are", "be", "been", "by", "as", "at", "this", "that",
    "it", "its", "agent", "response", "must", "should", "have", "has",
    "did", "does", "do", "not", "no", "any", "all", "some", "from",
}

BANNED_ADVERBS: set[str] = {
    "explicitly", "exactly", "correctly", "consistently",
    "appropriately", "properly", "fully", "completely",
    "clearly", "plainly", "adequately", "sufficiently",
    "accurately", "thoroughly", "reasonable", "sensible", "proper",
}

NEGATION_PHRASES: list[str] = [
    "does not", "do not", "must not", "fails to", "fail to",
]
NEGATION_WORDS: set[str] = {
    "not", "avoids", "refuses", "omits", "without", "never",
}

COMPOUND_JOINERS: list[str] = [
    " and ", " while ", " including ", " as well as ",
]

BARE_PRONOUNS: set[str] = {"it", "they", "them"}

_IDENTIFIER_RE = re.compile(
    r"""(?x)
    \b\d+\b
    | "[^"]+"
    | '[^']+'
    | `[^`]+`
    | \b[A-Za-z_][A-Za-z_0-9]*\.[A-Za-z_][A-Za-z_0-9]*\b
    | \b[A-Z][A-Z0-9]*-[A-Z0-9\-]*\d[A-Z0-9\-]*\b
    """
)

_TURN_ID_RE = re.compile(
    r"""(?x)
    (?:^|\s|[(,;\-])
    (?:
      T\d{1,3}
    | RL\d{1,2}
    | SM\d{1,2}
    | turn\s+\d{1,3}
    )
    (?=\s|[),;:.\-!?]|$)
    """,
    re.IGNORECASE,
)

OVERLAP_THRESHOLD = 0.40
COVERAGE_THRESHOLD = 0.18
COVERAGE_CONTAINMENT_THRESHOLD = 0.50
COVERAGE_MIN_REQ_TOKENS = 3


def tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
    return {t for t in tokens if t not in STOPWORDS and len(t) > 2}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def containment(small: set, large: set) -> float:
    if not small:
        return 0.0
    return len(small & large) / len(small)


def coverage_match(req_tokens: set, criterion_tokens: set) -> bool:
    if len(req_tokens) < COVERAGE_MIN_REQ_TOKENS:
        return False
    if jaccard(req_tokens, criterion_tokens) >= COVERAGE_THRESHOLD:
        return True
    return containment(req_tokens, criterion_tokens) >= COVERAGE_CONTAINMENT_THRESHOLD


def load_json_array(path: Path, label: str) -> tuple[list | None, list[str]]:
    errors: list[str] = []
    if not path.exists():
        errors.append(f"{label} not found at {path}")
        return None, errors
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        errors.append(f"{label} is not valid JSON: {e}")
        return None, errors
    if not isinstance(raw, list):
        errors.append(
            f"{label} must be a JSON array at the top level (got {type(raw).__name__})"
        )
        return None, errors
    return raw, errors


def validate_schema(rubric: list[dict]) -> list[str]:
    issues: list[str] = []
    for i, c in enumerate(rubric):
        name = c.get("number", f"R#{i}") if isinstance(c, dict) else f"R#{i}"
        if not isinstance(c, dict):
            issues.append(f"[{name}] not a dict")
            continue
        missing = REQUIRED_FIELDS - c.keys()
        if missing:
            issues.append(f"[{name}] missing fields: {sorted(missing)}")
        extra = c.keys() - REQUIRED_FIELDS
        if extra:
            issues.append(
                f"[{name}] unexpected fields {sorted(extra)} — v2 rubric stores "
                "only the 7 core fields (trap_concept is NOT a stored field; "
                "trap coverage lives in pytest docstring tags + the Trap Ledger)"
            )
        if c.get("type") not in VALID_TYPES:
            issues.append(f"[{name}] invalid type: {c.get('type')!r}")
        if c.get("evaluation_target") not in VALID_EVAL_TARGETS:
            issues.append(
                f"[{name}] invalid evaluation_target: {c.get('evaluation_target')!r}"
            )
        if c.get("importance") not in VALID_IMPORTANCE:
            issues.append(
                f"[{name}] invalid importance: {c.get('importance')!r} "
                "(allowed: critically_important, important)"
            )
        if not isinstance(c.get("is_positive"), bool):
            issues.append(f"[{name}] is_positive must be boolean")
        score = c.get("score")
        if not isinstance(score, int) or score not in VALID_SCORES:
            issues.append(
                f"[{name}] score must be one of {{-5,-3,-1,1,3,5}}, got {score!r}"
            )
            continue
        if c.get("is_positive") is True and score < 0:
            issues.append(
                f"[{name}] score-polarity mismatch: is_positive=true must have score "
                f"in {{1,3,5}} (got {score})"
            )
        if c.get("is_positive") is False and score > 0:
            issues.append(
                f"[{name}] score-polarity mismatch: is_positive=false must have score "
                f"in {{-1,-3,-5}} (got {score})"
            )
    return issues


def validate_count(rubric: list[dict]) -> list[str]:
    n = len(rubric)
    issues = []
    if n < 10:
        issues.append(
            f"rubric.json has {n} criteria — minimum 10 expected for complete "
            "coverage of a typical task's non-deterministic + trap surface area"
        )
    if n > 30:
        issues.append(
            f"rubric.json has {n} criteria — soft cap is 30; consider consolidating "
            "or moving deterministic checks to pytest"
        )
    return issues


def validate_prefixes(rubric: list[dict]) -> list[str]:
    issues = []
    for c in rubric:
        if not isinstance(c, dict):
            continue
        crit = (c.get("criterion") or "").strip()
        et = c.get("evaluation_target")
        expected = PREFIX_RULE.get(et)
        if not expected:
            continue
        if not crit.startswith(expected):
            issues.append(
                f"[{c.get('number')}] criterion must start with '{expected}' "
                f"(evaluation_target={et}); got: {crit[:60]!r}"
            )
    return issues


def validate_mandatory_negative(rubric: list[dict]) -> list[str]:
    if not any(c.get("is_positive") is False for c in rubric if isinstance(c, dict)):
        return [
            "rubric has no negative criteria (is_positive=false). "
            "≥1 required to penalize forbidden actions / hallucinations."
        ]
    return []


def validate_score_distribution(rubric: list[dict], *, require_min_5s: int = 2) -> list[str]:
    issues = []
    pos_scores = [
        c["score"] for c in rubric
        if isinstance(c, dict) and c.get("is_positive") and isinstance(c.get("score"), int)
    ]
    if not pos_scores:
        return ["rubric has no positive criteria with scores."]
    if len(pos_scores) >= 3 and all(s == 5 for s in pos_scores):
        issues.append(
            "all positive criteria are score 5 — must use a 5/3/1 distribution"
        )
    counts = Counter(pos_scores)
    if counts.get(5, 0) < require_min_5s:
        issues.append(
            f"need ≥{require_min_5s} criteria at score 5 (core outcomes); "
            f"have {counts.get(5, 0)}"
        )
    return issues


def validate_no_turn_ids(rubric: list[dict]) -> list[str]:
    issues = []
    for c in rubric:
        if not isinstance(c, dict):
            continue
        crit = c.get("criterion", "")
        matches = _TURN_ID_RE.findall(crit)
        if matches:
            found = ", ".join(m.strip() for m in matches)
            issues.append(
                f"[{c.get('number')}] criterion text contains turn/mutation ID(s): "
                f"{found}. Rephrase to describe the moment by content, not ID. "
                f"Criterion: {crit[:100]!r}"
            )
    return issues


def validate_no_banned_adverbs(rubric: list[dict]) -> list[str]:
    issues = []
    for c in rubric:
        if not isinstance(c, dict):
            continue
        text = c.get("criterion") or ""
        words = set(re.findall(r"[a-zA-Z]+", text.lower()))
        hits = sorted(BANNED_ADVERBS & words)
        if hits:
            issues.append(
                f"[{c.get('number')}] criterion contains banned adverb(s): "
                f"{', '.join(hits)}. Replace with the literal value/fact "
                f"being checked. Criterion: {text[:120]!r}"
            )
    return issues


def validate_affirmative_only(rubric: list[dict]) -> list[str]:
    issues = []
    for c in rubric:
        if not isinstance(c, dict):
            continue
        text = c.get("criterion") or ""
        lower = text.lower()
        hits = [p for p in NEGATION_PHRASES if p in lower]
        words = set(re.findall(r"[a-zA-Z]+", lower))
        hits.extend(sorted(NEGATION_WORDS & words))
        if hits:
            issues.append(
                f"[{c.get('number')}] criterion contains negation token(s): "
                f"{', '.join(hits)}. Rewrite affirmatively; polarity belongs "
                f"in is_positive=false + negative score. Criterion: {text[:120]!r}"
            )
    return issues


def validate_atomic(rubric: list[dict]) -> list[str]:
    issues = []
    for c in rubric:
        if not isinstance(c, dict):
            continue
        text = c.get("criterion") or ""
        lower = text.lower()
        hits = [j.strip() for j in COMPOUND_JOINERS if j in lower]
        if re.search(r"[.!?]\s+[A-Z]", text):
            hits.append("multi-sentence")
        if hits:
            issues.append(
                f"[{c.get('number')}] criterion is not atomic — found: "
                f"{', '.join(hits)}. Split into separate single-fact criteria. "
                f"Criterion: {text[:120]!r}"
            )
    return issues


def validate_self_contained(rubric: list[dict]) -> list[str]:
    issues = []
    for c in rubric:
        if not isinstance(c, dict):
            continue
        text = c.get("criterion") or ""
        words = set(re.findall(r"[a-zA-Z]+", text.lower()))
        pronoun_hits = sorted(BARE_PRONOUNS & words)
        has_identifier = bool(_IDENTIFIER_RE.search(text))
        problems: list[str] = []
        if pronoun_hits:
            problems.append(f"bare pronoun(s): {', '.join(pronoun_hits)}")
        if not has_identifier:
            problems.append(
                "no concrete identifier (claim ID, policy number, named party, "
                "file path, dotted field, dollar amount, or digit sequence)"
            )
        if problems:
            issues.append(
                f"[{c.get('number')}] criterion is not self-contained — "
                f"{'; '.join(problems)}. Embed the specific identifier and "
                f"replace any pronoun with the named entity. "
                f"Criterion: {text[:120]!r}"
            )
    return issues


def validate_numbering(rubric: list[dict]) -> list[str]:
    issues = []
    for i, c in enumerate(rubric):
        if not isinstance(c, dict):
            continue
        expected = f"R{i+1}"
        if c.get("number") != expected:
            issues.append(
                f"position {i+1}: expected number {expected!r}, got {c.get('number')!r}"
            )
    return issues


def parse_pytest_functions(pytest_path: Path) -> list[dict]:
    if not pytest_path.exists():
        return []
    tree = ast.parse(pytest_path.read_text())
    functions: list[dict] = []

    method_nodes: set[int] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_doc = ast.get_docstring(node) or ""
            class_tags = _parse_tags(class_doc)
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name.startswith(
                    "test_"
                ):
                    method_nodes.add(id(child))
                    method_doc = ast.get_docstring(child) or ""
                    method_tags = _parse_tags(method_doc)
                    tags = {**class_tags, **method_tags}
                    functions.append({
                        "name": f"{node.name}.{child.name}",
                        "docstring": class_doc + "\n" + method_doc,
                        "trap_concept": tags.get("trap", "none"),
                        "value_lock_key": tags.get("value_lock"),
                        "checker_id": tags.get("checker"),
                        "mutation_name": tags.get("mutation"),
                    })

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            if id(node) in method_nodes:
                continue
            doc = ast.get_docstring(node) or ""
            tags = _parse_tags(doc)
            functions.append({
                "name": node.name,
                "docstring": doc,
                "trap_concept": tags.get("trap", "none"),
                "value_lock_key": tags.get("value_lock"),
                "checker_id": tags.get("checker"),
                "mutation_name": tags.get("mutation"),
            })
    return functions


_TAG_RE = re.compile(r"\[(?P<key>[a-z_]+):(?P<value>[^\]]+)\]")


def _parse_tags(text: str) -> dict[str, str]:
    return {m.group("key"): m.group("value").strip() for m in _TAG_RE.finditer(text)}


def detect_overlap_against_pytest(
    rubric: list[dict], pytest_fns: list[dict], threshold: float = OVERLAP_THRESHOLD
) -> list[dict]:
    flags = []
    for c in rubric:
        if not isinstance(c, dict):
            continue
        crit_tokens = tokenize(c.get("criterion", ""))
        for fn in pytest_fns:
            doc_tokens = tokenize(fn["docstring"])
            score = jaccard(crit_tokens, doc_tokens)
            if score >= threshold:
                flags.append({
                    "rubric_number": c.get("number"),
                    "rubric_criterion": c.get("criterion"),
                    "pytest_fn": fn["name"],
                    "jaccard": round(score, 3),
                })
    return flags


def compute_trap_coverage(rubric: list[dict], pytest_fns: list[dict]) -> dict:
    """Joint trap-concept coverage.

    A trap concept is "covered" by rubric.json when at least one criterion's
    prose contains a keyword associated with that concept (keywords match the
    Stage 1 ``TRAP_CATEGORY_KEYWORDS`` table).
    """
    pytest_traps = Counter(
        fn["trap_concept"] for fn in pytest_fns
        if fn["trap_concept"] in REAL_TRAP_CONCEPTS
    )
    rubric_traps = Counter()
    for concept in REAL_TRAP_CONCEPTS:
        keywords = TRAP_KEYWORDS_BY_CONCEPT.get(concept, [])
        for c in rubric:
            if not isinstance(c, dict):
                continue
            text = (c.get("criterion") or "").lower()
            if any(k in text for k in keywords):
                rubric_traps[concept] += 1

    coverage = {}
    for concept in REAL_TRAP_CONCEPTS:
        coverage[concept] = {
            "in_pytest": pytest_traps.get(concept, 0),
            "in_rubric": rubric_traps.get(concept, 0),
            "total": pytest_traps.get(concept, 0) + rubric_traps.get(concept, 0),
        }
    return coverage


TRAP_KEYWORDS_BY_CONCEPT = {
    "silent_mutation": [
        "silent", "stale", "cached", "drift", "fresh value", "re-read",
        "freshness", "mutation",
    ],
    "backend_writeback": [
        "writeback", "write back", "commit", "persist", "save", "post",
    ],
    "red_line": [
        "refuse", "decline", "forbidden", "prohibited", "policy violation",
        "red line", "red-line", "poison pill", "poison-pill",
    ],
    "cross_modal_contradiction": [
        "contradict", "conflict", "mismatch", "discrepancy", "reconcile",
        "cross-modal",
    ],
    "decoy_value": [
        "decoy", "adjacent", "lookalike", "wrong row", "wrong cell",
    ],
    "temporal_revision": [
        "revision", "supersede", "outdated", "endorsement", "newer version",
        "replaced", "revised",
    ],
}


def validate_trap_coverage_gaps(trap_coverage: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for concept, data in trap_coverage.items():
        if data["in_pytest"] > 0 and data["in_rubric"] == 0:
            warnings.append(
                f"trap concept '{concept}' has {data['in_pytest']} pytest "
                "function(s) but 0 rubric criteria — the subjective layer is missing."
            )
    return errors, warnings


def load_requirements(output_dir: Path) -> list[dict]:
    req_path = output_dir / "requirements.json"
    if not req_path.exists():
        return []
    try:
        payload = json.loads(req_path.read_text())
    except json.JSONDecodeError:
        return []
    return payload.get("requirements", [])


def validate_requirement_coverage(
    requirements: list[dict],
    rubric: list[dict],
    pytest_fns: list[dict],
) -> tuple[list[str], list[dict]]:
    """For each Stage 1 requirement, confirm it is covered by its routing layer."""
    errors: list[str] = []
    report: list[dict] = []

    checker_to_fn: dict[str, str] = {}
    value_lock_to_fn: dict[str, str] = {}
    mutation_to_fn: dict[str, str] = {}
    for fn in pytest_fns:
        if fn.get("checker_id"):
            checker_to_fn[fn["checker_id"]] = fn["name"]
        if fn.get("value_lock_key"):
            value_lock_to_fn[fn["value_lock_key"]] = fn["name"]
        if fn.get("mutation_name"):
            mutation_to_fn[fn["mutation_name"]] = fn["name"]

    for r in requirements:
        rq_id = r.get("id", "?")
        route = r.get("routes_to")
        text = r.get("text", "")
        row = {"rq_id": rq_id, "routes_to": route, "covered_by": [], "status": "MISS"}

        if route == "pytest":
            tag = (
                r.get("checker_id")
                or r.get("value_lock_key")
                or r.get("mutation_name")
            )
            if r.get("checker_id") and r["checker_id"] in checker_to_fn:
                row["covered_by"].append(f"pytest:{checker_to_fn[r['checker_id']]}")
                row["status"] = "OK"
            elif r.get("value_lock_key") and r["value_lock_key"] in value_lock_to_fn:
                row["covered_by"].append(
                    f"pytest:{value_lock_to_fn[r['value_lock_key']]}"
                )
                row["status"] = "OK"
            elif r.get("mutation_name") and r["mutation_name"] in mutation_to_fn:
                row["covered_by"].append(
                    f"pytest:{mutation_to_fn[r['mutation_name']]}"
                )
                row["status"] = "OK"
            else:
                errors.append(
                    f"[{rq_id}] routed to pytest but no matching test function "
                    f"found for tag={tag!r}"
                )
        elif route == "rubric":
            req_tokens = tokenize(text)
            if len(req_tokens) < COVERAGE_MIN_REQ_TOKENS:
                row["covered_by"] = ["rubric:short-RQ-skip"]
                row["status"] = "OK (RQ too short to enforce)"
                report.append(row)
                continue
            matches = []
            for c in rubric:
                if not isinstance(c, dict):
                    continue
                if coverage_match(req_tokens, tokenize(c.get("criterion", ""))):
                    matches.append(c.get("number"))
            if matches:
                row["covered_by"] = [f"rubric:{n}" for n in matches]
                row["status"] = "OK"
            else:
                errors.append(
                    f"[{rq_id}] routed to rubric but no criterion with Jaccard "
                    f"≥ {COVERAGE_THRESHOLD} or containment ≥ "
                    f"{COVERAGE_CONTAINMENT_THRESHOLD} found. "
                    f"Requirement: {text[:120]!r}"
                )
        report.append(row)
    return errors, report


def validate_value_lock_in_mock_data(task_dir: Path) -> list[str]:
    """Check #23 — every Value Lock concrete value appears in mock_data."""
    issues: list[str] = []
    steer_path = task_dir / "golden_steer_flow.md"
    mock_dir = task_dir / "mock_data"
    if not steer_path.exists() or not mock_dir.exists():
        return issues
    try:
        steer = golden_steer_parser.parse(steer_path)
        data = mock_data_reader.load(mock_dir)
    except Exception as exc:
        issues.append(f"mock_data verification skipped: {exc}")
        return issues
    _, missing = mock_data_reader.verify_value_lock_coverage(data, steer.value_lock)
    for key in missing:
        entry = steer.value_for(key)
        issues.append(
            f"VALUE_LOCK {key} = {entry!r} does not appear anywhere in "
            "mock_data/. The agent has no path to discover this value."
        )
    return issues


def build_report(
    task_dir: Path,
    rubric: list[dict] | None,
    pytest_fns: list[dict],
    sections_data: dict,
) -> tuple[str, bool]:
    sections = [f"# Validation Report — {task_dir.name}\n"]

    def section(title: str, issues: list[str], pass_msg: str = "PASS"):
        if not issues:
            return f"## {title}\n\n✓ {pass_msg}\n"
        body = "\n".join(f"- ✗ {iss}" for iss in issues)
        return f"## {title}\n\n✗ FAIL ({len(issues)} issue(s))\n\n{body}\n"

    n = len(rubric or [])

    sections.append(section(
        "1. Schema (7 fields, valid enums, score-polarity lock)",
        sections_data["schema"],
        f"all {n} criteria have exactly the 7 required fields",
    ))
    sections.append(section(
        "2. Count (≥10, soft cap 30)",
        sections_data["count"],
        f"count={n}",
    ))
    sections.append(section(
        "3. Prefix rule (The response / The agent)",
        sections_data["prefix"],
    ))
    sections.append(section(
        "4. ≥1 negative criterion",
        sections_data["mandatory_negative"],
    ))
    sections.append(section(
        "5. Score distribution (uses 5/3/1)",
        sections_data["score_distribution"],
    ))
    sections.append(section(
        "6. Numbering R1..Rn",
        sections_data["numbering"],
    ))
    sections.append(section(
        "7. No turn-ID references",
        sections_data["turn_ids"],
        "no turn/mutation IDs (T0, RL1, SM3, etc.) found in criterion text",
    ))
    sections.append(section(
        "8. Rule 1 — no banned adverbs",
        sections_data["adverbs"],
        "no judge-shortcut adverbs found",
    ))
    sections.append(section(
        "9. Rule 4 — affirmative-only criterion text",
        sections_data["affirmative"],
        "no negation tokens found",
    ))
    sections.append(section(
        "10. Rule 2 — atomic single-fact criterion text",
        sections_data["atomic"],
        "no compound joiners and no multi-sentence criteria",
    ))
    sections.append(section(
        "11. Rule 3 — self-contained criterion text",
        sections_data["self_contained"],
        "no bare pronouns and every criterion contains a concrete identifier",
    ))

    overlap = sections_data["overlap_rubric_pytest"]
    if not overlap:
        sections.append(
            f"## 12. Disjoint check: rubric vs pytest\n\n"
            f"✓ PASS — no overlap above Jaccard threshold {OVERLAP_THRESHOLD}\n"
        )
    else:
        rows = "\n".join(
            f"| {f['rubric_number']} | {f['pytest_fn']} | {f['jaccard']} |" for f in overlap
        )
        sections.append(
            f"## 12. Disjoint check: rubric vs pytest\n\n"
            f"⚠ REVIEW ({len(overlap)} flag(s)) — Jaccard ≥ {OVERLAP_THRESHOLD} indicates possible overlap.\n\n"
            f"| rubric | pytest | Jaccard |\n|---|---|---|\n{rows}\n"
            "Heuristic flags — human review required.\n"
        )

    cov = sections_data["trap_coverage"]
    cov_rows = "\n".join(
        f"| {concept} | {data['in_pytest']} | {data['in_rubric']} | {data['total']} |"
        for concept, data in cov.items()
    )
    cov_warnings = sections_data["trap_coverage_warnings"]
    cov_warn_block = ""
    if cov_warnings:
        cov_warn_block = "\n⚠ WARNINGS:\n" + "\n".join(f"- {w}" for w in cov_warnings) + "\n"
    sections.append(
        "## 13. Trap concept joint coverage\n\n"
        "| Trap concept | In pytest | In rubric | Total |\n|---|---|---|---|\n"
        f"{cov_rows}\n{cov_warn_block}\n"
    )

    sections.append(f"## 14. Pytest summary\n\nTotal functions: {len(pytest_fns)}\n")

    cov_errors = sections_data["requirement_coverage_errors"]
    cov_report = sections_data["requirement_coverage_report"]
    req_total = sections_data["requirements_total"]
    if req_total == 0:
        cov15 = (
            "## 15. Stage 1 inventory coverage\n\n"
            "requirements.json not found — Stage 1 inventory check skipped. "
            "Re-run pytest_generator.generate() to populate it.\n"
        )
    else:
        ok_count = sum(1 for r in cov_report if r["status"].startswith("OK"))
        cov_rows = "\n".join(
            f"| {r['rq_id']} | {r['routes_to']} | "
            f"{', '.join(r['covered_by']) or '(none)'} | {r['status']} |"
            for r in cov_report
        )
        cov_err_block = ""
        if cov_errors:
            cov_err_block = "\n\n✗ FAIL — uncovered requirements:\n" + "\n".join(
                f"- {e}" for e in cov_errors
            )
        cov15 = (
            "## 15. Stage 1 inventory coverage\n\n"
            f"{ok_count}/{req_total} requirements covered.\n\n"
            "| RQ | Routed to | Covered by | Status |\n|---|---|---|---|\n"
            f"{cov_rows}\n{cov_err_block}\n"
        )
    sections.append(cov15)

    vl_issues = sections_data["value_lock_in_mock_data"]
    sections.append(section(
        "16. Value Lock cells present in mock_data",
        vl_issues,
        "every Value Lock value is reachable in the mock data tree",
    ))

    all_hard_issues = (
        sections_data["schema"] + sections_data["count"] + sections_data["prefix"]
        + sections_data["mandatory_negative"] + sections_data["score_distribution"]
        + sections_data["numbering"] + sections_data["turn_ids"]
        + sections_data["adverbs"] + sections_data["affirmative"]
        + sections_data["atomic"] + sections_data["self_contained"]
        + cov_errors + vl_issues
    )
    all_pass = not all_hard_issues
    summary = (
        f"**Overall: {'✓ PASS' if all_pass else '✗ FAIL'}** "
        f"({len(all_hard_issues)} hard issue(s), "
        f"{len(overlap)} overlap flag(s), "
        f"{len(cov_warnings)} trap-coverage warning(s))\n"
    )
    sections.insert(1, summary)
    return "\n".join(sections), all_pass


def validate_and_collect(task_dir: Path, output_dir: Path) -> tuple[bool, dict]:
    """Run all checks, write validation_report.md, return ``(ok, sections_data)``."""
    rubric_path = output_dir / "rubric.json"
    pytest_path = output_dir / "test_outputs.py"

    rubric, load_errors = load_json_array(rubric_path, "rubric.json")
    pytest_fns = parse_pytest_functions(pytest_path)

    if rubric is None:
        report = f"# Validation Report — {task_dir.name}\n\n**Overall: ✗ FAIL**\n\n"
        report += "\n".join(f"- ✗ {e}" for e in load_errors)
        report += f"\n\nPytest functions found: {len(pytest_fns)}\n"
        (output_dir / "validation_report.md").write_text(report + "\n")
        return False, {
            "load_errors": load_errors,
            "rubric": [],
            "pytest_fns": pytest_fns,
            "requirements": [],
        }

    requirements = load_requirements(output_dir)
    coverage_errors, coverage_report = validate_requirement_coverage(
        requirements, rubric, pytest_fns
    )
    trap_coverage = compute_trap_coverage(rubric, pytest_fns)
    _, trap_warnings = validate_trap_coverage_gaps(trap_coverage)

    sections_data = {
        "schema": validate_schema(rubric),
        "count": validate_count(rubric),
        "prefix": validate_prefixes(rubric),
        "mandatory_negative": validate_mandatory_negative(rubric),
        "score_distribution": validate_score_distribution(rubric),
        "numbering": validate_numbering(rubric),
        "turn_ids": validate_no_turn_ids(rubric),
        "adverbs": validate_no_banned_adverbs(rubric),
        "affirmative": validate_affirmative_only(rubric),
        "atomic": validate_atomic(rubric),
        "self_contained": validate_self_contained(rubric),
        "overlap_rubric_pytest": detect_overlap_against_pytest(rubric, pytest_fns),
        "trap_coverage": trap_coverage,
        "trap_coverage_warnings": trap_warnings,
        "requirement_coverage_errors": coverage_errors,
        "requirement_coverage_report": coverage_report,
        "requirements_total": len(requirements),
        "value_lock_in_mock_data": validate_value_lock_in_mock_data(task_dir),
    }

    report, all_pass = build_report(task_dir, rubric, pytest_fns, sections_data)
    (output_dir / "validation_report.md").write_text(report)

    cov_path = output_dir / "trap_coverage.json"
    if cov_path.exists():
        existing = json.loads(cov_path.read_text())
        existing["rubric_count"] = len(rubric)
        existing["combined_coverage"] = trap_coverage
        existing["overlap_flags"] = sections_data["overlap_rubric_pytest"]
        existing["trap_coverage_warnings"] = trap_warnings
        cov_path.write_text(json.dumps(existing, indent=2) + "\n")

    sections_data["rubric"] = rubric
    sections_data["pytest_fns"] = pytest_fns
    sections_data["requirements"] = requirements
    sections_data["load_errors"] = load_errors
    return all_pass, sections_data


def validate(task_dir: Path, output_dir: Path) -> bool:
    ok, _ = validate_and_collect(task_dir, output_dir)
    return ok


def summarize_failures_for_retry(sections_data: dict) -> dict:
    """Compact payload for the Stage 4 retry-loop patch prompt."""
    requirements = sections_data.get("requirements", [])
    rubric = sections_data.get("rubric", [])
    cov_errors = sections_data.get("requirement_coverage_errors", []) or []
    cov_report = sections_data.get("requirement_coverage_report", []) or []

    rq_index = {r["id"]: r for r in requirements}

    uncovered_rqs = []
    for err in cov_errors:
        m = re.match(r"\[(RQ\d+)\]\s*(.*)", err)
        if not m:
            continue
        rq_id = m.group(1)
        reason = m.group(2).strip()
        r = rq_index.get(rq_id, {})
        uncovered_rqs.append({
            "id": rq_id,
            "source": r.get("source", "?"),
            "text": r.get("text", "?"),
            "routes_to": r.get("routes_to", "?"),
            "trap_concept": r.get("trap_concept", "none"),
            "reason": reason,
        })

    def collect(section_key: str, pattern: str, *fields: str) -> list[dict]:
        out: list[dict] = []
        regex = re.compile(pattern)
        for issue in sections_data.get(section_key, []):
            m = regex.match(issue)
            if not m:
                continue
            row = {"number": m.group(1)}
            for i, field in enumerate(fields, start=2):
                row[field] = m.group(i)
            out.append(row)
        return out

    prefix_violations = collect(
        "prefix",
        r"\[([R]\d+)\]\s*criterion must start with '([^']+)' \(evaluation_target=(\w+)\); got: '([^']+)",
        "required", "evaluation_target", "current_first",
    )
    turn_id_violations = collect(
        "turn_ids",
        r"\[([R]\d+)\]\s*criterion text contains turn/mutation ID\(s\): (.+?)\. Rephrase",
        "found_ids",
    )
    adverb_violations = collect(
        "adverbs",
        r"\[([R]\d+)\]\s*criterion contains banned adverb\(s\): (.+?)\. Replace",
        "found_adverbs",
    )
    negation_violations = collect(
        "affirmative",
        r"\[([R]\d+)\]\s*criterion contains negation token\(s\): (.+?)\. Rewrite",
        "found_negations",
    )
    compound_violations = collect(
        "atomic",
        r"\[([R]\d+)\]\s*criterion is not atomic — found: (.+?)\. Split",
        "found_joiners",
    )
    self_contained_violations = collect(
        "self_contained",
        r"\[([R]\d+)\]\s*criterion is not self-contained — (.+?)\. Embed",
        "problems",
    )

    cov = sections_data.get("trap_coverage", {}) or {}
    missing_trap_concepts: list[str] = [
        concept for concept, stats in cov.items()
        if isinstance(stats, dict) and stats.get("in_pytest", 0) > 0 and stats.get("in_rubric", 0) == 0
    ]

    return {
        "uncovered_rqs": uncovered_rqs,
        "prefix_violations": prefix_violations,
        "turn_id_violations": turn_id_violations,
        "adverb_violations": adverb_violations,
        "negation_violations": negation_violations,
        "compound_violations": compound_violations,
        "self_contained_violations": self_contained_violations,
        "missing_trap_concepts": missing_trap_concepts,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Validate rubric.json + test_outputs.py")
    p.add_argument("--task-dir", required=True, type=Path)
    p.add_argument(
        "--output-dir", type=Path, default=None,
        help="Directory containing rubric.json + test_outputs.py "
        "(default: <task-dir>/tests/)",
    )
    args = p.parse_args(argv)
    task_dir = args.task_dir.resolve()
    output_dir = (args.output_dir or (task_dir / "tests")).resolve()
    ok = validate(task_dir, output_dir)
    print(
        f"Validation: {'PASS' if ok else 'FAIL'} — see "
        f"{output_dir / 'validation_report.md'}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
