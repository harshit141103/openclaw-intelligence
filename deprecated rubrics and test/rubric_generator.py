"""
rubric_generator.py — v2 parser for the agent's rubric response.

The v2 rubric is a SINGLE flat list of criteria (no normal/trap split).
Each criterion has exactly the 7 fields the validator enforces:

    number, criterion, is_positive, type, evaluation_target,
    importance, score

Numbering is sequential ``R1..Rn``. Mixed positive + negative criteria
live in the same list, distinguished by ``is_positive`` + score sign.
trap_concept is NOT a stored field — trap coverage lives in pytest
docstring tags and the Trap Ledger / Poison-Pill records, NOT inside
rubric.json.

This module accepts the LLM response in any of these shapes (in order
of preference):

  1. ``{"rubric": [ ... ]}``       — explicit single-list envelope
  2. bare JSON array               — same payload, no envelope
  3. ``{"criteria": [ ... ]}``     — alternative envelope key
"""
from __future__ import annotations

import json
import re
from pathlib import Path


class RubricGenerationError(Exception):
    """Raised when the agent response cannot be parsed into a rubric list."""


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    fence = re.match(r"^```(?:json)?\s*\n(.*?)\n```\s*$", stripped, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return stripped


def _slice_first_object(text: str) -> str:
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last < first:
        raise RubricGenerationError(
            "Agent response did not contain a JSON object. First 500 chars:\n"
            + text[:500]
        )
    return text[first : last + 1]


def _slice_first_array(text: str) -> str:
    first = text.find("[")
    last = text.rfind("]")
    if first == -1 or last == -1 or last < first:
        raise RubricGenerationError(
            "Agent response did not contain a JSON array. First 500 chars:\n"
            + text[:500]
        )
    return text[first : last + 1]


def extract_rubric(text: str) -> list[dict]:
    """Parse the LLM response into a single flat rubric list."""
    stripped = _strip_code_fence(text)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        try:
            parsed = json.loads(_slice_first_object(stripped))
        except (RubricGenerationError, json.JSONDecodeError):
            parsed = json.loads(_slice_first_array(stripped))

    if isinstance(parsed, list):
        return _coerce_list(parsed)

    if isinstance(parsed, dict):
        for key in ("rubric", "criteria"):
            if key in parsed and isinstance(parsed[key], list):
                return _coerce_list(parsed[key])
        if "normal_rubric" in parsed or "trap_rubric" in parsed:
            merged = list(parsed.get("normal_rubric") or [])
            merged.extend(parsed.get("trap_rubric") or [])
            return _coerce_list(merged)
        raise RubricGenerationError(
            "Parsed JSON object is missing the rubric list. Expected a "
            "top-level 'rubric' or 'criteria' key holding an array. Got "
            f"keys: {sorted(parsed.keys())}"
        )

    raise RubricGenerationError(
        f"Parsed JSON is neither object nor list (got {type(parsed).__name__})."
    )


def _coerce_list(arr: list) -> list[dict]:
    out: list[dict] = []
    for c in arr:
        if isinstance(c, dict):
            c.pop("trap_concept", None)
            out.append(c)
    return out


def _renumber(rubric: list[dict]) -> list[dict]:
    return [{**c, "number": f"R{i}"} for i, c in enumerate(rubric, start=1)]


def save_rubric(text: str, output_dir: Path | str) -> dict:
    """Parse the agent response and write ``rubric.json`` (single file)."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rubric = _renumber(extract_rubric(text))
    rubric_path = output_dir / "rubric.json"
    rubric_path.write_text(json.dumps(rubric, indent=2) + "\n")

    return {
        "rubric_path": str(rubric_path),
        "rubric_count": len(rubric),
    }


def save_rubrics(text: str, output_dir: Path | str) -> dict:
    """Backwards-compatible alias for ``save_rubric``."""
    return save_rubric(text, output_dir)
