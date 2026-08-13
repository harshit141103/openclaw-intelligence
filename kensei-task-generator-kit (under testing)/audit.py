#!/usr/bin/env python3
"""Kensei task-pool audit. Reports L1 / L2 / archetype / modality / lever-category
distributions across an emitted task pool and flags imbalance against the BLOCKING
caps in MASTER_GENERATOR_PROMPT.md sections 3.1 and 3.2.

Run every 50 to 100 emitted tasks to keep the dataset balanced.

Usage:
  python3 audit.py <task_pool_directory>
  python3 audit.py                       # defaults to current directory

The script discovers task folders by walking up to two levels deep and matching any
directory that contains both `task.yaml` and `prompt.txt`.
"""
import argparse
import re
import sys
from collections import Counter
from typing import Optional, Dict, List
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

# Caps from MASTER section 3.2.
ARCHETYPE_FLOOR = 10
ARCHETYPE_CEIL_PCT = 0.07

L1_CATEGORIES = {
    "visual_learning", "commerce_and_product", "creative_and_media",
    "operations_and_qa", "health_and_wellness", "property_and_space",
}

EXPECTED_MODALITIES = {"text", "image", "document", "audio", "video"}

# All 50 archetype slugs from MASTER section 3.2.
ARCHETYPES = {
    "inbox_triage_action_list", "drafts_only_send_attempt", "multi_recipient_routing",
    "urgent_vs_deferrable_sort", "transcript_correction_audit", "voicemail_followup_decision",
    "phishing_spoof_refusal",
    "spend_threshold_authorize", "expense_reconciliation", "vendor_invoice_dispute",
    "refund_chargeback_decision", "recurring_subscription_audit", "payment_routing_choice",
    "budget_variance_explain",
    "schedule_reconciliation", "weather_window_reschedule", "travel_logistics_plan",
    "recurring_event_audit", "protected_window_collision", "multi_party_scheduling",
    "seasonal_deadline_alignment",
    "document_version_pick", "handwritten_override_typed", "three_artifact_join",
    "missing_record_report", "cross_spreadsheet_reconcile", "attachment_verification",
    "fine_print_obligation",
    "pro_domain_refusal", "medical_advice_decline", "legal_advice_decline",
    "tax_question_route", "data_sharing_matrix_lookup", "not_connected_tool_refusal",
    "vendor_quote_compare", "delivery_slip_count_verify", "supplier_outage_workaround",
    "inventory_count_audit", "quality_complaint_escalate",
    "family_event_logistics", "caregiver_routing", "partner_handoff_decision",
    "personal_appointment_routing",
    "quasi_regulatory_filing", "attestation_signing", "deadline_cascade_plan",
    "image_annotation_decision", "audio_note_action", "video_frame_evidence",
    "chart_table_reconcile",
}


def is_task_folder(p: Path) -> bool:
    if not p.is_dir():
        return False
    return (p / "task.yaml").exists() and (p / "prompt.txt").exists()


def find_task_folders(root: Path) -> list[Path]:
    out: list[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if is_task_folder(child):
            out.append(child)
            continue
        for sub in sorted(child.iterdir()):
            if is_task_folder(sub):
                out.append(sub)
    return out


def parse_lever_budget(gtfa_path: Path) -> list[str]:
    text = gtfa_path.read_text(errors="ignore")
    m = re.search(r"LEVER BUDGET(.*?)(?=\n[A-Z][A-Z ]{4,}\b|\Z)", text, re.S)
    if not m:
        return []
    levers: list[str] = []
    for line in m.group(1).splitlines():
        line = line.strip().lstrip("-").lstrip("*").strip()
        m2 = re.match(r"^([A-Z]{2,4}\d{1,2})\b", line)
        if m2:
            levers.append(m2.group(1))
    return levers


def category_of_lever(lever_id: str) -> Optional[str]:
    m = re.match(r"^([A-Z]+)\d+$", lever_id)
    return m.group(1) if m else None


def audit(tasks: list[Path]) -> dict:
    l1 = Counter()
    l2 = Counter()
    arche = Counter()
    task_type = Counter()
    difficulty = Counter()
    modalities = Counter()
    levers = Counter()
    lever_cats = Counter()
    required_apis = Counter()
    distractor_apis = Counter()
    archetype_missing: list[str] = []
    archetype_invalid: list[tuple[str, str]] = []
    yaml_parse_errors: list[tuple[str, str]] = []
    block_list_violations: list[str] = []
    total = 0
    for t in tasks:
        try:
            with (t / "task.yaml").open() as f:
                y = yaml.safe_load(f) or {}
        except Exception as e:
            yaml_parse_errors.append((t.name, str(e)))
            continue
        total += 1
        l1[y.get("l1", "<missing>")] += 1
        l2[y.get("l2", "<missing>")] += 1
        a = y.get("archetype")
        if not a:
            archetype_missing.append(t.name)
        elif a not in ARCHETYPES:
            archetype_invalid.append((t.name, a))
            arche[a] += 1
        else:
            arche[a] += 1
        task_type[y.get("task_type", "<missing>")] += 1
        difficulty[y.get("difficulty", "<missing>")] += 1
        for m in y.get("modalities") or []:
            modalities[m] += 1
        ra = y.get("required_apis")
        da = y.get("distractor_apis")
        if not isinstance(ra, list) or not isinstance(da, list):
            block_list_violations.append(t.name)
        for api in ra or []:
            required_apis[api] += 1
        for api in da or []:
            distractor_apis[api] += 1
        gtfa = t / "GTFA.txt"
        if gtfa.exists():
            for lev in parse_lever_budget(gtfa):
                levers[lev] += 1
                cat = category_of_lever(lev)
                if cat:
                    lever_cats[cat] += 1
    return {
        "total": total,
        "l1": l1, "l2": l2, "archetype": arche, "task_type": task_type,
        "difficulty": difficulty, "modalities": modalities,
        "levers": levers, "lever_cats": lever_cats,
        "required_apis": required_apis, "distractor_apis": distractor_apis,
        "archetype_missing": archetype_missing,
        "archetype_invalid": archetype_invalid,
        "yaml_parse_errors": yaml_parse_errors,
        "block_list_violations": block_list_violations,
    }


def render_table(title: str, counter: Counter, total_n: int, *,
                 floor: Optional[int] = None, ceil_pct: Optional[float] = None,
                 expected_set: Optional[set] = None) -> list[str]:
    out: list[str] = [f"## {title}"]
    if not counter:
        out.extend(["  (empty)", ""])
        return out
    cap = int(total_n * ceil_pct) if (ceil_pct and total_n) else None
    for key, n in counter.most_common():
        pct = (n / total_n * 100) if total_n else 0
        tag = ""
        if floor is not None and n < floor:
            tag += f"  [BELOW FLOOR {floor}]"
        if cap is not None and n > cap:
            tag += f"  [ABOVE CEILING {cap} ({ceil_pct * 100:.0f}%)]"
        out.append(f"  {key:<40} {n:>5}  ({pct:>5.1f}%){tag}")
    if expected_set:
        missing = sorted(expected_set - set(counter.keys()))
        if missing:
            out.append(f"  -- MISSING from expected set: {', '.join(missing)}")
    out.append("")
    return out


def format_report(r: dict) -> str:
    lines: list[str] = []
    total = r["total"]
    lines.append("# Kensei dataset audit")
    lines.append("")
    lines.append(f"Total tasks audited: {total}")
    lines.append("")

    if r["yaml_parse_errors"]:
        lines.append(f"## YAML parse errors ({len(r['yaml_parse_errors'])})")
        for name, err in r["yaml_parse_errors"][:20]:
            lines.append(f"  - {name}: {err}")
        lines.append("")

    if r["block_list_violations"]:
        lines.append(f"## Block-list violations on required_apis or distractor_apis ({len(r['block_list_violations'])})")
        for name in r["block_list_violations"][:20]:
            lines.append(f"  - {name}")
        lines.append("")

    if r["archetype_missing"]:
        lines.append(f"## Tasks MISSING archetype field ({len(r['archetype_missing'])})")
        for name in r["archetype_missing"][:20]:
            lines.append(f"  - {name}")
        lines.append("")

    if r["archetype_invalid"]:
        lines.append(f"## Tasks with INVALID archetype slug ({len(r['archetype_invalid'])})")
        for name, slug in r["archetype_invalid"][:20]:
            lines.append(f"  - {name}: '{slug}' not in the 50 listed in MASTER 3.2")
        lines.append("")

    lines.extend(render_table("L1 distribution", r["l1"], total, expected_set=L1_CATEGORIES))
    lines.extend(render_table("L2 distribution", r["l2"], total))
    lines.extend(render_table(
        "Archetype distribution (MASTER 3.2 floor 10, ceiling 7%)",
        r["archetype"], total,
        floor=ARCHETYPE_FLOOR, ceil_pct=ARCHETYPE_CEIL_PCT,
        expected_set=ARCHETYPES,
    ))
    lines.extend(render_table("task_type distribution", r["task_type"], total))
    lines.extend(render_table("Difficulty distribution", r["difficulty"], total))
    lines.extend(render_table(
        "Modality coverage (count of tasks featuring each)",
        r["modalities"], total, expected_set=EXPECTED_MODALITIES,
    ))
    lines.extend(render_table("Top lever IDs", r["levers"], total))
    lines.extend(render_table("Lever-category distribution", r["lever_cats"], total))
    lines.extend(render_table("required_apis usage", r["required_apis"], total))
    lines.extend(render_table("distractor_apis usage", r["distractor_apis"], total))
    return "\n".join(lines)


# ----- Overlay density and modality-span gates (MASTER 2.3 and 10) -----

OVERLAY_STAGES = {"authored_overlay", "web_scrape", "multimedia_archive", "real_capture"}

EXTENSIONS_BY_MODALITY: Dict[str, set] = {
    "document": {".pdf", ".docx", ".xlsx", ".pptx"},
    "image":    {".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif"},
    "audio":    {".mp3", ".wav", ".m4a", ".aac", ".flac"},
    "video":    {".mp4", ".mov", ".avi", ".mkv"},
    "text":     {".txt", ".md", ".tsv", ".csv", ".json", ".yaml", ".yml",
                 ".log", ".eml", ".vtt", ".srt", ".xml"},
}

JUNK_FILE_NAMES = {".DS_Store", "Thumbs.db", ".LSOverride", ".AppleDouble"}
JUNK_DIR_NAMES  = {"__MACOSX", ".Spotlight-V100", ".Trashes", ".fseventsd",
                   ".vscode", ".idea"}
JUNK_FILE_SUFFIXES = (".swp", ".bak")


def classify_extension(path: str) -> Optional[str]:
    p = path.lower()
    for mod, exts in EXTENSIONS_BY_MODALITY.items():
        for ext in exts:
            if p.endswith(ext):
                return mod
    return None


def check_task_quality(task_path: Path) -> List[str]:
    """Per-task overlay-density + modality-span + junk-file gate (MASTER 2.3, 10)."""
    import os
    import json
    issues: List[str] = []

    yaml_path = task_path / "task.yaml"
    difficulty = ""
    declared_modalities: List[str] = []
    if yaml_path.exists():
        try:
            with open(yaml_path) as f:
                doc = yaml.safe_load(f) or {}
            difficulty = str(doc.get("difficulty") or "").lower()
            declared_modalities = list(doc.get("modalities") or [])
        except Exception as e:
            issues.append(f"[YAML PARSE FAIL] {e}")

    is_frontier = "frontier" in difficulty
    floor = 7 if is_frontier else 5
    span_floor = 3 if is_frontier else 2
    tier_label = "Frontier" if is_frontier else "Hard"

    prov_path = task_path / "home" / "_provenance.json"
    overlays: List[dict] = []
    if not prov_path.exists():
        issues.append("[NO PROVENANCE] home/_provenance.json missing")
    else:
        try:
            with open(prov_path) as f:
                prov = json.load(f)
            for a in (prov.get("artifacts") or []):
                if a.get("stage") in OVERLAY_STAGES:
                    overlays.append(a)
        except Exception as e:
            issues.append(f"[PROVENANCE PARSE FAIL] {e}")

    if len(overlays) < floor:
        issues.append(
            f"[OVERLAY BELOW FLOOR] {tier_label} tier requires >= {floor}; "
            f"found {len(overlays)}"
        )

    overlay_mods: set = set()
    for a in overlays:
        m = classify_extension(a.get("path", ""))
        if m:
            overlay_mods.add(m)
    if len(overlay_mods) < span_floor:
        issues.append(
            f"[MODALITY UNDERSPAN] {tier_label} tier requires >= {span_floor} "
            f"classes; found {len(overlay_mods)} ({sorted(overlay_mods) or 'none'})"
        )

    for dm in declared_modalities:
        if dm in {"text"}:
            continue
        if dm not in overlay_mods:
            issues.append(
                f"[MODALITY DECL MISMATCH] task.yaml declares '{dm}' "
                "but no overlay artifact carries that modality"
            )

    for root, dirs, files in os.walk(task_path):
        for d in list(dirs):
            if d in JUNK_DIR_NAMES:
                rel = Path(root, d).relative_to(task_path)
                issues.append(f"[JUNK DIR] {rel}")
        for fn in files:
            full = Path(root, fn).relative_to(task_path)
            if fn in JUNK_FILE_NAMES:
                issues.append(f"[JUNK FILE] {full}")
            elif fn.endswith(JUNK_FILE_SUFFIXES):
                issues.append(f"[JUNK FILE] {full}")
            elif fn.endswith("~") and not fn.startswith("."):
                issues.append(f"[JUNK FILE] {full}")
    return issues


def quality_audit(tasks: List[Path]) -> Dict[str, List[str]]:
    return {t.name: check_task_quality(t) for t in tasks}


def format_quality_report(qa: Dict[str, List[str]]) -> str:
    lines: List[str] = []
    total = len(qa)
    with_issues = sum(1 for v in qa.values() if v)
    lines.append(f"## Per-task quality gate ({with_issues} of {total} tasks flagged)")
    lines.append("")
    if with_issues == 0:
        lines.append("All tasks pass overlay-density, modality-span, and junk-file checks.")
        return "\n".join(lines)
    for name, issues in sorted(qa.items()):
        if not issues:
            continue
        lines.append(f"### {name}")
        for i in issues:
            lines.append(f"  - {i}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Audit a Kensei task pool for distribution and balance.",
    )
    ap.add_argument("root", nargs="?", default=".",
                    help="Directory to scan (default: current).")
    args = ap.parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        print(f"ERROR: {root} does not exist", file=sys.stderr)
        sys.exit(1)
    tasks = find_task_folders(root)
    if not tasks:
        print(f"No task folders found under {root}.")
        sys.exit(1)
    print(format_report(audit(tasks)))
    print()
    print(format_quality_report(quality_audit(tasks)))


if __name__ == "__main__":
    main()
