"""
mock_data_description_parser.py — parses the Kensei Phase-1
``mock_data_description.md`` for PART B subsections B3, B4, B5.

PART B carries the design-intent metadata the rubric/pytest generator
consumes (PART A is the file-tree spec consumed by Phase 2 itself).

  B3 — Trap Ledger (DESIGN parts; per-trap category + carrier)
  B4 — Rubric Contract (required facts, required refusals, hard-fail
       negative checkers, completeness requirement)
  B5 — Value-Lock KEY SCHEMA (variable name + source file/location
       placeholders — NO concrete values; concrete values live in
       golden_steer_flow.md Section 3)

Returns a ``MockDescription`` dataclass. PART B is REQUIRED — its absence
means the upstream Kensei pipeline did not produce a v5.0 spec, and the
generator cannot proceed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


class MockDescriptionParseError(ValueError):
    """Raised when mock_data_description.md PART B (or a required subsection)
    is missing or malformed."""


@dataclass
class TrapDesign:
    """One entry under PART B B3 Trap Ledger.

    Phase-1 only emits the DESIGN parts; Phase-2 records the materialized
    values in golden_steer_flow.md Section 4 / Section 6.
    """
    category: str
    realization: str = ""
    carrier: str = ""
    design_parts: dict[str, str] = field(default_factory=dict)


@dataclass
class KeySchemaEntry:
    """One entry under PART B B5 Value-Lock KEY SCHEMA.

    Phase-1 emits VARIABLE_NAME + source-location comments only. The
    concrete value comes from golden_steer_flow.md Section 3 (same key).
    """
    key: str
    placeholder: str
    source_file: str = ""
    source_location: str = ""
    kind: str = "primary"  # "primary" | "stale" | "decoy" | "distractor"


@dataclass
class RubricContract:
    """PART B B4 — what the agent must output / refuse / hard-fail on."""
    expected_format: str = ""
    required_facts: list[str] = field(default_factory=list)
    required_refusals: list[str] = field(default_factory=list)
    hard_fail_checks: list[tuple[str, str]] = field(default_factory=list)
    completeness_requirement: str = ""


@dataclass
class MockDescription:
    traps: list[TrapDesign] = field(default_factory=list)
    rubric_contract: RubricContract = field(default_factory=RubricContract)
    key_schema: list[KeySchemaEntry] = field(default_factory=list)
    raw_text: str = ""
    part_b_start_line: int = 0


_SUBSECTION_RE = re.compile(
    r"^\s*###\s*B(?P<n>\d+)\b\s*[.:\-]?\s*(?P<title>.*?)\s*$",
    re.IGNORECASE,
)
_PART_B_RE = re.compile(r"^\s*##\s+PART\s+B\b", re.IGNORECASE)
_PART_A_RE = re.compile(r"^\s*##\s+PART\s+A\b", re.IGNORECASE)


def parse(path: Path) -> MockDescription:
    if not path.exists():
        raise MockDescriptionParseError(
            f"mock_data_description.md not found at {path}. The v2 generator "
            "requires the Kensei Phase-1 spec (PART A file tree + PART B design "
            "intent)."
        )

    text = path.read_text()
    lines = text.splitlines()

    part_b_start = _find_part_b_start(lines)
    if part_b_start is None:
        raise MockDescriptionParseError(
            f"{path.name}: PART B (Task Design Intent) section not found. "
            "Expected a top-level ``## PART B`` heading containing B1-B5 "
            "subsections."
        )

    subsections = _collect_subsections(lines, start=part_b_start)

    desc = MockDescription(raw_text=text, part_b_start_line=part_b_start + 1)

    if "3" in subsections:
        _parse_b3_traps(subsections["3"], desc)
    if "4" in subsections:
        _parse_b4_rubric_contract(subsections["4"], desc)
    if "5" not in subsections:
        raise MockDescriptionParseError(
            f"{path.name}: PART B B5 (Value-Lock KEY SCHEMA) is required. The "
            "pytest layer needs the VARIABLE_NAME + source-file mapping to "
            "know where to assert each Value Lock entry."
        )
    _parse_b5_key_schema(subsections["5"], desc)

    return desc


def _find_part_b_start(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        if _PART_B_RE.match(line):
            return i
    return None


def _collect_subsections(
    lines: list[str], *, start: int
) -> dict[str, list[tuple[int, str]]]:
    """Return ``{subsection_number: [(line_no, line), ...]}`` for B1..B5."""
    out: dict[str, list[tuple[int, str]]] = {}
    current: str | None = None
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if _PART_A_RE.match(line) or line.startswith("## "):
            current = None
            if line.startswith("## ") and not line.lstrip("# ").upper().startswith(
                "PART B"
            ):
                break
        m = _SUBSECTION_RE.match(line)
        if m:
            current = m.group("n")
            out.setdefault(current, [])
            continue
        if current is not None:
            out[current].append((i + 1, line))
    return out


def _parse_b3_traps(rows: list[tuple[int, str]], desc: MockDescription) -> None:
    """B3 — one paragraph per trap, e.g.

    ::

        Trap 1 (Silent Mutation): realization = ...; CARRIER = mock tree
          - DESIGN PARTS:
            - authority_rule_quote: "..."
            - stale_value_source: "..."
    """
    header_re = re.compile(
        r"^\s*Trap\s+(?P<num>\d+)\s*\(\s*(?P<category>[^)]+?)\s*\)\s*:\s*(?P<rest>.*)$",
        re.IGNORECASE,
    )
    part_re = re.compile(r"^\s*[-*]\s+(?P<key>[a-z_]+)\s*:\s*(?P<value>.+)$")
    current: TrapDesign | None = None

    for _, line in rows:
        m = header_re.match(line)
        if m:
            if current is not None:
                desc.traps.append(current)
            rest = m.group("rest")
            realization, carrier = _extract_realization_and_carrier(rest)
            current = TrapDesign(
                category=m.group("category").strip(),
                realization=realization,
                carrier=carrier,
            )
            continue
        if current is None:
            continue
        part = part_re.match(line)
        if part:
            current.design_parts[part.group("key").lower()] = (
                part.group("value").strip().strip('"').strip("'")
            )

    if current is not None:
        desc.traps.append(current)


def _extract_realization_and_carrier(text: str) -> tuple[str, str]:
    realization = ""
    carrier = ""
    parts = [p.strip() for p in text.split(";") if p.strip()]
    for p in parts:
        low = p.lower()
        if low.startswith("realization"):
            realization = p.split("=", 1)[1].strip() if "=" in p else p
        elif low.startswith("carrier"):
            carrier = p.split("=", 1)[1].strip() if "=" in p else p
    return realization, carrier


def _parse_b4_rubric_contract(
    rows: list[tuple[int, str]], desc: MockDescription
) -> None:
    """B4 — bullet/key-value list:

    ::

        - Expected response format: ...
        - Required facts in response: [a, b, c]
        - Required refusals: [a, b]
        - Hard-fail negative checks: [checker_id: description, ...]
        - Completeness requirement: ...
    """
    field_map = {
        "expected response format": "expected_format",
        "required facts in response": "required_facts",
        "required facts": "required_facts",
        "required refusals": "required_refusals",
        "hard-fail negative checks": "hard_fail_checks",
        "hard fail negative checks": "hard_fail_checks",
        "completeness requirement": "completeness_requirement",
    }

    bullet_re = re.compile(r"^\s*[-*]\s+(?P<label>[^:]+):\s*(?P<value>.+)$")

    for _, line in rows:
        m = bullet_re.match(line)
        if not m:
            continue
        label = m.group("label").strip().lower()
        attr = field_map.get(label)
        if attr is None:
            continue
        raw_value = m.group("value").strip()

        if attr in ("expected_format", "completeness_requirement"):
            setattr(desc.rubric_contract, attr, raw_value.strip('"'))
            continue

        if attr == "hard_fail_checks":
            desc.rubric_contract.hard_fail_checks = _parse_checker_list(raw_value)
            continue

        desc.rubric_contract.__dict__[attr] = _parse_string_list(raw_value)


def _parse_string_list(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    parts = [p.strip().strip("'").strip('"') for p in raw.split(",")]
    return [p for p in parts if p]


def _parse_checker_list(raw: str) -> list[tuple[str, str]]:
    """Parse ``[id1: desc1, id2: desc2]``. Tolerant of commas inside descs by
    splitting on the next ``identifier:`` boundary."""
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    entries: list[tuple[str, str]] = []
    boundary = re.compile(r"(?<=[\s,])([A-Za-z_][A-Za-z0-9_\-]*)\s*:\s*")
    matches = list(boundary.finditer(" " + raw))
    if not matches:
        if ":" in raw:
            checker_id, desc = raw.split(":", 1)
            entries.append((checker_id.strip(), desc.strip()))
        return entries
    for i, m in enumerate(matches):
        checker_id = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(" " + raw)
        desc = (" " + raw)[start:end].rstrip(", \t")
        entries.append((checker_id, desc))
    return entries


def _parse_b5_key_schema(rows: list[tuple[int, str]], desc: MockDescription) -> None:
    """B5 — placeholder schema for the value-lock variables.

    Section may contain three labelled groups: primary value keys, stale/decoy
    keys, distractor keys. Within each group, lines follow
    ``{KEY} = "{PLACEHOLDER}"  # source: <file>, <location>``.
    """
    kind = "primary"
    entry_re = re.compile(
        r"""^\s*
            \{?(?P<key>[A-Z_][A-Z0-9_]*)\}?
            \s*=\s*
            (?P<value>"[^"]*"|'[^']*'|\{[^}]+\}|[^#]+?)
            \s*(?:\#\s*(?P<comment>.*))?
            \s*$""",
        re.VERBOSE,
    )

    for _, line in rows:
        stripped = line.strip()
        low = stripped.lower()
        if "stale" in low and "key" in low:
            kind = "stale"
            continue
        if "decoy" in low and "key" in low:
            kind = "decoy"
            continue
        if "distractor" in low and "key" in low:
            kind = "distractor"
            continue
        if not stripped or stripped.startswith("(") or stripped.startswith("#"):
            continue
        m = entry_re.match(line)
        if not m:
            continue
        comment = (m.group("comment") or "").strip()
        source_file, source_location = _split_source_comment(comment)
        raw_value = m.group("value").strip()
        if (raw_value.startswith('"') and raw_value.endswith('"')) or (
            raw_value.startswith("'") and raw_value.endswith("'")
        ):
            placeholder = raw_value[1:-1]
        else:
            placeholder = raw_value
        desc.key_schema.append(
            KeySchemaEntry(
                key=m.group("key"),
                placeholder=placeholder,
                source_file=source_file,
                source_location=source_location,
                kind=kind,
            )
        )


def _split_source_comment(comment: str) -> tuple[str, str]:
    """Extract ``source: <file>, <location>`` from a B5 comment."""
    if not comment:
        return "", ""
    lower = comment.lower()
    for prefix in ("source:", "source =", "stale:", "decoy:", "distractor:"):
        if lower.startswith(prefix):
            comment = comment[len(prefix):].strip()
            break
    parts = comment.split(",", 1)
    source_file = parts[0].strip()
    source_location = parts[1].strip() if len(parts) > 1 else ""
    return source_file, source_location


def lookup_key_schema(desc: MockDescription, key: str) -> KeySchemaEntry | None:
    for entry in desc.key_schema:
        if entry.key == key:
            return entry
    return None


def format_rubric_contract(desc: MockDescription) -> str:
    c = desc.rubric_contract
    lines = []
    if c.expected_format:
        lines.append(f"- Expected response format: {c.expected_format}")
    if c.required_facts:
        lines.append("- Required facts:")
        for fact in c.required_facts:
            lines.append(f"  - {fact}")
    if c.required_refusals:
        lines.append("- Required refusals:")
        for r in c.required_refusals:
            lines.append(f"  - {r}")
    if c.hard_fail_checks:
        lines.append("- Hard-fail negative checks:")
        for checker_id, desc_text in c.hard_fail_checks:
            lines.append(f"  - `{checker_id}`: {desc_text}")
    if c.completeness_requirement:
        lines.append(f"- Completeness: {c.completeness_requirement}")
    return "\n".join(lines) if lines else "(no rubric contract parsed)"
