"""
golden_steer_parser.py — parses the Kensei v5.0 ``golden_steer_flow.md``.

The canonical template (RL_MM/Prompt2-MockDataCreation.md §13) is an
8-section document authored at Phase 2 tail with ZERO placeholders:

  Section 1: Focal Event and Scope
  Section 2: Canonical Solve Path             (6 fixed-role steps)
  Section 3: Value Lock                       (code block: VAR = "value")
  Section 4: Fairness Ledger                  (markdown table)
  Section 5: Signal Set Declaration           (signal/noise prose)
  Section 6: Poison-Pill Record               (optional — red-line trap)
  Section 7: Task.py Authoring Notes          (CONSTANTS + CHECKERS + MUTATIONS)
  Section 8: Phase-2 Fingerprint

The generator REQUIRES Sections 3 and 7 (they drive pytest emission).
Other sections inform the rubric prompt but are not fatal if missing.

Returns a ``GoldenSteer`` dataclass; raises ``GoldenSteerParseError`` on
malformed required sections (with line numbers).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


class GoldenSteerParseError(ValueError):
    """Raised when golden_steer_flow.md is missing a required section or
    its required section is malformed. The message names the section and
    points at the offending line so the author can fix it."""


@dataclass
class ValueLockEntry:
    """A single ``VAR = "value"  # source: ...`` line in Section 3."""
    key: str
    value: str
    source: str | None = None
    line: int = 0


@dataclass
class CanonicalStep:
    """One numbered step in Section 2's 6-step canonical solve path."""
    index: int
    label: str
    body: str
    line: int = 0


@dataclass
class FairnessRow:
    """One row of Section 4's Fairness Ledger markdown table."""
    trap_type: str
    carrier_file: str
    materialized_form: str
    design_intent: str
    line: int = 0


@dataclass
class PoisonPill:
    """Section 6 — optional red-line trap record."""
    pill_location: str
    pill_text: str
    violated_rule: str
    correct_response: str
    checker_id: str
    line: int = 0


@dataclass
class Checker:
    """One entry in Section 7's CHECKERS bullet list."""
    checker_id: str
    description: str
    threshold: str = ""
    line: int = 0


@dataclass
class Mutation:
    """One entry in Section 7's MUTATIONS bullet list (silent/loud)."""
    name: str
    description: str
    line: int = 0


@dataclass
class GoldenSteer:
    """Parsed golden_steer_flow.md."""
    focal_event: str = ""
    scope_boundary: str = ""
    task_persona: str = ""
    active_services: list[str] = field(default_factory=list)
    distractor_services: list[str] = field(default_factory=list)
    canonical_steps: list[CanonicalStep] = field(default_factory=list)
    convergence_evidence: str = ""
    value_lock: list[ValueLockEntry] = field(default_factory=list)
    fairness_ledger: list[FairnessRow] = field(default_factory=list)
    signal_files: list[str] = field(default_factory=list)
    poison_pill: PoisonPill | None = None
    constants: list[ValueLockEntry] = field(default_factory=list)
    checkers: list[Checker] = field(default_factory=list)
    mutations: list[Mutation] = field(default_factory=list)
    readme_facts: dict[str, str] = field(default_factory=dict)
    fingerprint: dict[str, str] = field(default_factory=dict)
    source_path: Path | None = None

    def value_for(self, key: str) -> str | None:
        for entry in self.value_lock:
            if entry.key == key:
                return entry.value
        return None


_SECTION_RE = re.compile(r"^\s*##\s+Section\s+(\d+)\s*:\s*(.+?)\s*$", re.IGNORECASE)


def parse(path: Path) -> GoldenSteer:
    """Parse a golden_steer_flow.md file. Raises on missing required sections."""
    if not path.exists():
        raise GoldenSteerParseError(
            f"golden_steer_flow.md not found at {path}. The v2 generator is "
            "forward-only — it requires the Kensei Phase 2 bundle "
            "(prompt.txt + mock_data_description.md + golden_steer_flow.md + "
            "mock_data/). Existing pre-v5.0 tasks are not supported."
        )

    text = path.read_text()
    lines = text.splitlines()
    sections = _split_sections(lines)

    steer = GoldenSteer(source_path=path)

    if 1 in sections:
        _parse_section_1(sections[1], steer)
    if 2 in sections:
        _parse_section_2(sections[2], steer)

    if 3 not in sections:
        raise GoldenSteerParseError(
            f"{path.name}: Section 3 (Value Lock) is required but not found. "
            "The pytest layer needs concrete VALUE_LOCK entries to assert against."
        )
    _parse_section_3(sections[3], steer)

    if 4 in sections:
        _parse_section_4(sections[4], steer)
    if 5 in sections:
        _parse_section_5(sections[5], steer)
    if 6 in sections:
        _parse_section_6(sections[6], steer)

    if 7 not in sections:
        raise GoldenSteerParseError(
            f"{path.name}: Section 7 (Task.py Authoring Notes) is required but "
            "not found. The pytest layer needs the CHECKERS list (and any "
            "MUTATIONS) to know what to assert."
        )
    _parse_section_7(sections[7], steer)

    if 8 in sections:
        _parse_section_8(sections[8], steer)

    if not steer.value_lock:
        raise GoldenSteerParseError(
            f"{path.name}: Section 3 (Value Lock) parsed but contains zero "
            'entries. Expected a ``VALUE_LOCK:`` code block with at least one '
            '``VAR = "value"`` line.'
        )
    if not steer.checkers:
        raise GoldenSteerParseError(
            f"{path.name}: Section 7 (Task.py Authoring Notes) parsed but "
            "contains zero CHECKERS entries. Expected a ``CHECKERS required`` "
            'bullet list with at least one ``- `<checker_id>`: <what it checks>'
            "``."
        )

    return steer


def _split_sections(lines: list[str]) -> dict[int, list[tuple[int, str]]]:
    """Return ``{section_index: [(line_no, line), ...]}`` for the 8 sections."""
    sections: dict[int, list[tuple[int, str]]] = {}
    current_idx: int | None = None
    for i, line in enumerate(lines, start=1):
        m = _SECTION_RE.match(line)
        if m:
            current_idx = int(m.group(1))
            sections.setdefault(current_idx, [])
            continue
        if current_idx is not None:
            sections[current_idx].append((i, line))
    return sections


def _line_lookup(rows: list[tuple[int, str]], prefix: str) -> tuple[int, str] | None:
    needle = prefix.lower()
    for line_no, line in rows:
        if line.strip().lower().startswith(needle):
            return line_no, line
    return None


def _strip_bold_marker(text: str) -> str:
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", text).strip()


def _split_csv_list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _parse_section_1(rows: list[tuple[int, str]], steer: GoldenSteer) -> None:
    """Section 1 prose with bold-labelled key: value lines."""
    field_map = {
        "focal event:": "focal_event",
        "in-world scope boundary:": "scope_boundary",
        "task persona:": "task_persona",
        "active services:": "active_services",
        "distractor services:": "distractor_services",
    }
    for line_no, line in rows:
        stripped = _strip_bold_marker(line.strip())
        lower = stripped.lower()
        for key, attr in field_map.items():
            if lower.startswith(key):
                raw_value = stripped[len(key):].strip()
                if attr in ("active_services", "distractor_services"):
                    setattr(steer, attr, _split_csv_list(raw_value))
                else:
                    setattr(steer, attr, raw_value)
                break


def _parse_section_2(rows: list[tuple[int, str]], steer: GoldenSteer) -> None:
    """Section 2 — 6 fixed-role numbered steps. Numbered list ``1. ... 6. ...``."""
    step_re = re.compile(r"^\s*(\d+)\.\s+(.+)$")
    label_re = re.compile(r"^\s*\*\*([^*]+)\*\*:?\s*(.*)$")
    current: CanonicalStep | None = None

    for line_no, line in rows:
        m = step_re.match(line)
        if m:
            if current is not None:
                steer.canonical_steps.append(current)
            idx = int(m.group(1))
            rest = m.group(2).strip()
            label_match = label_re.match(rest)
            if label_match:
                label = label_match.group(1).strip()
                body = label_match.group(2).strip()
            else:
                label = ""
                body = rest
            current = CanonicalStep(index=idx, label=label, body=body, line=line_no)
            continue

        if current is not None and line.strip():
            current.body = (current.body + " " + line.strip()).strip()
        elif current is not None and not line.strip() and current.body:
            steer.canonical_steps.append(current)
            current = None

        stripped = _strip_bold_marker(line.strip())
        if stripped.lower().startswith("convergence evidence:"):
            steer.convergence_evidence = stripped[len("convergence evidence:"):].strip()

    if current is not None:
        steer.canonical_steps.append(current)


def _parse_section_3(rows: list[tuple[int, str]], steer: GoldenSteer) -> None:
    """Section 3 — VALUE_LOCK code block.

    ::

        ```
        VALUE_LOCK:
          VAR_1 = "concrete value"   # source: claims-api/claim_records.csv, ...
          VAR_2 = "concrete value"   # source: Phase-2 minted
        ```
    """
    inside_block = False
    seen_header = False
    found_any = False
    entry_re = re.compile(
        r"""^\s*
            (?P<key>[A-Z][A-Z0-9_]+)
            \s*=\s*
            (?P<value>"[^"]*"|'[^']*'|[^#]+?)
            \s*(?:\#\s*(?P<comment>.*))?
            \s*$""",
        re.VERBOSE,
    )

    for line_no, line in rows:
        stripped = line.strip()
        if stripped.startswith("```"):
            inside_block = not inside_block
            continue
        if not inside_block:
            continue
        if stripped.lower().startswith("value_lock:"):
            seen_header = True
            continue
        if not stripped or stripped.startswith("#"):
            continue
        m = entry_re.match(line)
        if not m:
            continue
        raw_value = m.group("value").strip()
        if (raw_value.startswith('"') and raw_value.endswith('"')) or (
            raw_value.startswith("'") and raw_value.endswith("'")
        ):
            value = raw_value[1:-1]
        else:
            value = raw_value
        steer.value_lock.append(
            ValueLockEntry(
                key=m.group("key"),
                value=value,
                source=(m.group("comment") or "").strip() or None,
                line=line_no,
            )
        )
        found_any = True

    if not found_any:
        first_line = rows[0][0] if rows else 0
        raise GoldenSteerParseError(
            f"Section 3 (Value Lock) starting near line {first_line} has no "
            'parseable ``VAR = "value"`` entries inside a ``VALUE_LOCK:`` code '
            "block. Check that the fenced block uses triple backticks and that "
            "every line follows the ``VAR_NAME = \"value\"  # source: …`` shape."
        )
    if not seen_header:
        pass


def _parse_section_4(rows: list[tuple[int, str]], steer: GoldenSteer) -> None:
    """Section 4 — Fairness Ledger markdown table.

    ::

        | Trap type | Carrier file | Materialized form | Design intent satisfied? |
        |-----------|--------------|-------------------|--------------------------|
        | trap_1    | file         | text/value        | YES - citation           |
    """
    for line_no, line in rows:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        first = cells[0].lower()
        if first.startswith("trap type") or set(first) <= {"-", " "}:
            continue
        steer.fairness_ledger.append(
            FairnessRow(
                trap_type=cells[0],
                carrier_file=cells[1],
                materialized_form=cells[2],
                design_intent=cells[3],
                line=line_no,
            )
        )


def _parse_section_5(rows: list[tuple[int, str]], steer: GoldenSteer) -> None:
    """Section 5 — bullet list of signal files."""
    bullet_re = re.compile(r"^\s*[-*]\s+(?:`([^`]+)`|([^ ]+))\s*(?:[-—]\s*(.*))?$")
    in_signal_block = False
    for line_no, line in rows:
        stripped = line.strip()
        if stripped.lower().startswith("**signal set"):
            in_signal_block = True
            continue
        if stripped.lower().startswith("**noise"):
            in_signal_block = False
            continue
        if not in_signal_block:
            continue
        m = bullet_re.match(line)
        if not m:
            continue
        filename = (m.group(1) or m.group(2) or "").strip()
        if filename and filename not in steer.signal_files:
            steer.signal_files.append(filename)


def _parse_section_6(rows: list[tuple[int, str]], steer: GoldenSteer) -> None:
    """Section 6 — Poison-Pill Record. Optional; key/value lines.

    Field labels (bold) — Pill location, Pill text (verbatim), Violated AGENTS.md
    rule (verbatim), Correct agent response, Checker ID.
    """
    fields = {
        "pill location:": "pill_location",
        "pill text (verbatim):": "pill_text",
        "pill text:": "pill_text",
        "violated agents.md rule (verbatim):": "violated_rule",
        "violated agents.md rule:": "violated_rule",
        "violated rule:": "violated_rule",
        "correct agent response:": "correct_response",
        "checker id:": "checker_id",
    }
    payload: dict[str, str] = {}
    first_line: int | None = None
    for line_no, line in rows:
        stripped = _strip_bold_marker(line.strip())
        lower = stripped.lower()
        for label, attr in fields.items():
            if lower.startswith(label):
                payload[attr] = stripped[len(label):].strip().strip("`")
                if first_line is None:
                    first_line = line_no
                break

    if "pill_location" not in payload and "pill_text" not in payload:
        return

    steer.poison_pill = PoisonPill(
        pill_location=payload.get("pill_location", ""),
        pill_text=payload.get("pill_text", ""),
        violated_rule=payload.get("violated_rule", ""),
        correct_response=payload.get("correct_response", ""),
        checker_id=payload.get("checker_id", ""),
        line=first_line or 0,
    )


def _parse_section_7(rows: list[tuple[int, str]], steer: GoldenSteer) -> None:
    """Section 7 — Task.py Authoring Notes.

    Subsections (Markdown bold labels):
      **CONSTANTS to define:**       code block of ``VAR = "value"``
      **CHECKERS required:**         bullet list of ``- `<id>`: <desc>``
      **Silent/loud MUTATIONS:**     bullet list of ``- MUTATION `<name>`: <desc>``
      **README key facts:**          bullet list of ``- <label>: <value>``
    """
    subsection: str | None = None
    in_code_block = False
    const_re = re.compile(
        r'^\s*(?P<key>[A-Z][A-Z0-9_]+)\s*=\s*(?P<value>"[^"]*"|\'[^\']*\'|.+?)\s*$'
    )
    checker_re = re.compile(
        r"^\s*[-*]\s+`(?P<id>[^`]+)`\s*:\s*(?P<desc>.+?)\s*(?:-\s*hard-fail threshold:\s*(?P<threshold>.+))?$",
        re.IGNORECASE,
    )
    mutation_re = re.compile(
        r"^\s*[-*]\s+MUTATION\s+`(?P<name>[^`]+)`\s*:\s*(?P<desc>.+)$",
        re.IGNORECASE,
    )
    readme_re = re.compile(r"^\s*[-*]\s+(?P<label>[^:]+):\s*(?P<value>.+)$")

    for line_no, raw_line in rows:
        line = raw_line
        stripped = _strip_bold_marker(raw_line.strip())
        lower = stripped.lower()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if lower.startswith("constants to define"):
            subsection = "constants"
            continue
        if lower.startswith("checkers required"):
            subsection = "checkers"
            continue
        if lower.startswith("silent/loud mutations") or lower.startswith("mutations"):
            subsection = "mutations"
            continue
        if lower.startswith("readme key facts"):
            subsection = "readme"
            continue

        if subsection == "constants" and in_code_block:
            m = const_re.match(line)
            if not m:
                continue
            raw_value = m.group("value").strip()
            if (raw_value.startswith('"') and raw_value.endswith('"')) or (
                raw_value.startswith("'") and raw_value.endswith("'")
            ):
                value = raw_value[1:-1]
            else:
                value = raw_value
            steer.constants.append(
                ValueLockEntry(key=m.group("key"), value=value, line=line_no)
            )
            continue

        if subsection == "checkers":
            m = checker_re.match(line)
            if not m:
                continue
            steer.checkers.append(
                Checker(
                    checker_id=m.group("id"),
                    description=m.group("desc").strip(),
                    threshold=(m.group("threshold") or "").strip(),
                    line=line_no,
                )
            )
            continue

        if subsection == "mutations":
            m = mutation_re.match(line)
            if not m:
                continue
            steer.mutations.append(
                Mutation(
                    name=m.group("name"),
                    description=m.group("desc").strip(),
                    line=line_no,
                )
            )
            continue

        if subsection == "readme":
            m = readme_re.match(line)
            if not m:
                continue
            steer.readme_facts[m.group("label").strip().lower()] = m.group(
                "value"
            ).strip()


def _parse_section_8(rows: list[tuple[int, str]], steer: GoldenSteer) -> None:
    """Section 8 — Phase-2 Fingerprint code block of ``key = value`` lines."""
    in_code_block = False
    line_re = re.compile(r"^\s*(?P<key>[a-z_][a-z0-9_]*)\s*=\s*(?P<value>.+?)\s*$")
    for _, line in rows:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if not in_code_block:
            continue
        if stripped.lower().startswith("phase_2_fingerprint"):
            continue
        m = line_re.match(line)
        if not m:
            continue
        steer.fingerprint[m.group("key")] = m.group("value").strip()


def format_value_lock(steer: GoldenSteer) -> str:
    """Render the Value Lock as the LLM prompt block."""
    if not steer.value_lock:
        return "(no value_lock entries parsed)"
    lines = ["| Key | Value | Source |", "|---|---|---|"]
    for entry in steer.value_lock:
        value = (entry.value or "").replace("|", "\\|")
        source = (entry.source or "").replace("|", "\\|")
        lines.append(f"| {entry.key} | {value} | {source} |")
    return "\n".join(lines)


def format_canonical_path(steer: GoldenSteer) -> str:
    if not steer.canonical_steps:
        return "(no canonical solve path parsed)"
    lines = []
    for step in steer.canonical_steps:
        label = f" **{step.label}**" if step.label else ""
        lines.append(f"{step.index}.{label} {step.body}".rstrip())
    if steer.convergence_evidence:
        lines.append("")
        lines.append(f"Convergence: {steer.convergence_evidence}")
    return "\n".join(lines)


def format_fairness_ledger(steer: GoldenSteer) -> str:
    if not steer.fairness_ledger:
        return "(no fairness ledger rows parsed)"
    lines = [
        "| Trap type | Carrier file | Materialized form | Design intent |",
        "|---|---|---|---|",
    ]
    for row in steer.fairness_ledger:
        cells = [
            row.trap_type.replace("|", "\\|"),
            row.carrier_file.replace("|", "\\|"),
            row.materialized_form.replace("|", "\\|"),
            row.design_intent.replace("|", "\\|"),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def format_poison_pill(steer: GoldenSteer) -> str:
    p = steer.poison_pill
    if p is None:
        return "(no poison-pill / red-line trap declared)"
    return (
        f"- Pill location: {p.pill_location}\n"
        f"- Pill text: {p.pill_text}\n"
        f"- Violated rule: {p.violated_rule}\n"
        f"- Correct response: {p.correct_response}\n"
        f"- Checker ID: {p.checker_id}"
    )


def format_checkers(steer: GoldenSteer) -> str:
    if not steer.checkers:
        return "(no checkers declared)"
    lines = []
    for c in steer.checkers:
        suffix = f" — hard-fail: {c.threshold}" if c.threshold else ""
        lines.append(f"- `{c.checker_id}`: {c.description}{suffix}")
    return "\n".join(lines)
