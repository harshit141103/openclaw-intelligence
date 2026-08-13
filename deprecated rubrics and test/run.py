"""
run.py — v2 generator CLI (Kensei v5.0 / forward-only).

5-stage pipeline:

  Stage 1+2: classify requirements + emit ``test_outputs.py``
  Stage 3:   assemble the rubric LLM prompt
  Stage 4:   call the ``claude`` CLI to fill in ``rubric.json``
  Stage 5:   validate disjointness + full coverage

This generator REQUIRES the Kensei Phase-2 bundle:

  <task-dir>/
    prompt.txt
    mock_data_description.md      (PART A + PART B with B3/B4/B5)
    golden_steer_flow.md          (8 sections)
    mock_data/                    (one {slug}-api/ per active service)
    artifacts/                    (optional)
    persona/                      (optional — SOUL.md, AGENTS.md, MEMORY.md)

When invoked against an older pre-v5.0 task directory (no
``golden_steer_flow.md``), the generator errors cleanly. Existing
pre-v5.0 tasks are NOT modified — this is the v2 forward-only generator.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

GENERATOR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(GENERATOR_DIR))

import golden_steer_parser
import mock_data_description_parser
import mock_data_reader
import pytest_generator
import requirement_extractor
import rubric_generator
import validator

CLAUDE_TIMEOUT_SECONDS = 900
CLAUDE_FALLBACK_GLOBS = [
    "~/openclaw/node_modules/@anthropic-ai/claude-agent-sdk-*/claude",
    "~/node_modules/@anthropic-ai/claude-agent-sdk-*/claude",
    "~/.npm-global/lib/node_modules/@anthropic-ai/claude-code/cli.js",
    "~/.claude/local/claude",
    "/opt/homebrew/lib/node_modules/@anthropic-ai/claude-code/cli.js",
    "/usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js",
]


RUBRIC_EXAMPLES = '''\
[
  {
    "number": "R1",
    "criterion": "The response names claimant Maria Hernandez in the supervisor summary for claim CLM-88421.",
    "is_positive": true,
    "type": "task completion",
    "evaluation_target": "user_facing_message",
    "importance": "important",
    "score": 3
  },
  {
    "number": "R2",
    "criterion": "The response names endorsement END-2026-0312 as the reason the settlement amount on claim CLM-88421 became $35,000.",
    "is_positive": true,
    "type": "factuality and hallucination",
    "evaluation_target": "user_facing_message",
    "importance": "critically_important",
    "score": 5
  },
  {
    "number": "R3",
    "criterion": "The response presents $50,000 as the active settlement cap on claim CLM-88421.",
    "is_positive": false,
    "type": "factuality and hallucination",
    "evaluation_target": "user_facing_message",
    "importance": "critically_important",
    "score": -5
  }
]
'''


def _read(path: Path, fallback: str = "") -> str:
    return path.read_text() if path.exists() else fallback


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _load_bundle(task_dir: Path) -> tuple[
    golden_steer_parser.GoldenSteer,
    mock_data_description_parser.MockDescription,
    mock_data_reader.MockData,
]:
    steer_path = task_dir / "golden_steer_flow.md"
    desc_path = task_dir / "mock_data_description.md"
    mock_dir = task_dir / "mock_data"

    missing: list[str] = []
    if not steer_path.exists():
        missing.append("golden_steer_flow.md")
    if not desc_path.exists():
        missing.append("mock_data_description.md")
    if not mock_dir.exists():
        missing.append("mock_data/")
    if missing:
        raise SystemExit(
            "This is the v2 generator for Kensei v5.0 task bundles. "
            f"Missing required input(s) in {task_dir}: {', '.join(missing)}. "
            "Existing pre-v5.0 tasks (without golden_steer_flow.md) are not "
            "supported — use the v1 generator (Rubrics_and_PY_Generator) "
            "for those."
        )

    steer = golden_steer_parser.parse(steer_path)
    description = mock_data_description_parser.parse(desc_path)
    data = mock_data_reader.load(mock_dir)
    return steer, description, data


def _format_fairness_ledger(steer: golden_steer_parser.GoldenSteer) -> str:
    block = golden_steer_parser.format_fairness_ledger(steer)
    pill = golden_steer_parser.format_poison_pill(steer)
    return f"{block}\n\n### Poison-Pill\n\n{pill}"


def _assemble_prompt(
    task_dir: Path,
    output_dir: Path,
    *,
    steer: golden_steer_parser.GoldenSteer,
    description: mock_data_description_parser.MockDescription,
    data: mock_data_reader.MockData,
) -> tuple[str, str]:
    template_path = GENERATOR_DIR / "rubric_prompt_template.md"
    system_path = GENERATOR_DIR / "system_prompt.md"
    template = template_path.read_text()
    system_prompt = system_path.read_text()

    prompt_body = _read(task_dir / "prompt.txt", "(no prompt.txt)")
    pytest_body = _read(output_dir / "test_outputs.py", "(test_outputs.py missing)")

    requirements_inventory = _load_inventory_markdown(output_dir)
    value_lock_block = golden_steer_parser.format_value_lock(steer)
    canonical_path_block = golden_steer_parser.format_canonical_path(steer)
    fairness_ledger_block = golden_steer_parser.format_fairness_ledger(steer)
    poison_pill_block = golden_steer_parser.format_poison_pill(steer)
    rubric_contract_block = mock_data_description_parser.format_rubric_contract(
        description
    )
    mock_data_values_block = mock_data_reader.format_mock_data_values(
        data, max_per_file=3
    )
    checkers_block = golden_steer_parser.format_checkers(steer)

    user_prompt = (
        template
        .replace("{{FOCAL_EVENT}}", steer.focal_event or "?")
        .replace("{{SCOPE_BOUNDARY}}", steer.scope_boundary or "?")
        .replace("{{TASK_PERSONA}}", steer.task_persona or "?")
        .replace("{{ACTIVE_SERVICES}}", ", ".join(steer.active_services) or "?")
        .replace("{{DISTRACTOR_SERVICES}}", ", ".join(steer.distractor_services) or "?")
        .replace("{{REQUIREMENTS_INVENTORY}}", requirements_inventory)
        .replace("{{PROMPT_BODY}}", prompt_body)
        .replace("{{CANONICAL_PATH}}", canonical_path_block)
        .replace("{{VALUE_LOCK}}", value_lock_block)
        .replace("{{FAIRNESS_LEDGER}}", fairness_ledger_block)
        .replace("{{POISON_PILL}}", poison_pill_block)
        .replace("{{RUBRIC_CONTRACT}}", rubric_contract_block)
        .replace("{{MOCK_DATA_VALUES}}", mock_data_values_block)
        .replace("{{CHECKERS}}", checkers_block)
        .replace("{{PYTEST_BODY}}", pytest_body)
        .replace("{{RUBRIC_TEMPLATE_EXAMPLES}}", RUBRIC_EXAMPLES)
    )
    return system_prompt, user_prompt


def _write_prompt_file(output_dir: Path, system_prompt: str, user_prompt: str) -> Path:
    combined = (
        "<!-- SYSTEM PROMPT -->\n\n"
        + system_prompt
        + "\n\n<!-- USER PROMPT -->\n\n"
        + user_prompt
    )
    out_path = output_dir / "rubric_generation_prompt.md"
    out_path.write_text(combined)
    return out_path


def _load_inventory_markdown(output_dir: Path) -> str:
    req_path = output_dir / "requirements.json"
    if not req_path.exists():
        return (
            "(requirements.json not found — re-run Stage 1+2 with "
            "pytest_generator.generate)"
        )
    payload = json.loads(req_path.read_text())
    reqs = payload.get("requirements", [])
    return requirement_extractor.render_inventory_markdown(reqs)


def _save_from_response(response_path: Path, output_dir: Path) -> dict:
    text = response_path.read_text()
    return rubric_generator.save_rubric(text, output_dir)


def _resolve_claude_binary() -> str | None:
    if os.environ.get("CLAUDE_BIN"):
        candidate = Path(os.environ["CLAUDE_BIN"]).expanduser()
        if candidate.exists():
            return str(candidate)
    on_path = shutil.which("claude")
    if on_path:
        return on_path
    import glob
    for pattern in CLAUDE_FALLBACK_GLOBS:
        matches = glob.glob(str(Path(pattern).expanduser()))
        for m in matches:
            if Path(m).exists():
                return m
    return None


def _call_claude_cli(prompt: str, model: str | None) -> str:
    binary = _resolve_claude_binary()
    if binary is None:
        raise RuntimeError(
            "`claude` CLI not found. Looked on PATH, $CLAUDE_BIN, and common "
            "Claude Code install paths. Set CLAUDE_BIN=/path/to/claude or pass "
            "--no-auto to skip Stage 4."
        )
    cmd = [binary, "-p"]
    if model:
        cmd.extend(["--model", model])
    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"`claude` CLI timed out after {CLAUDE_TIMEOUT_SECONDS}s "
            "(large rubrics can be slow; bump CLAUDE_TIMEOUT_SECONDS or pass --no-auto)."
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(
            f"`claude` CLI exited {result.returncode}:\n{result.stderr.strip()}"
        )
    if not result.stdout.strip():
        raise RuntimeError("`claude` CLI returned empty stdout — no rubric produced.")
    return result.stdout


def _build_patch_prompt(
    output_dir: Path,
    prev_rubric: list,
    failures: dict,
    attempt_index: int,
) -> str:
    requirements_inventory = _load_inventory_markdown(output_dir)

    blocks: list[str] = []
    blocks.append(f"# RUBRIC PATCH REQUEST — attempt {attempt_index}")
    blocks.append("")
    blocks.append("You generated a rubric on the previous turn. The validator")
    blocks.append("(Stage 5 of the OpenClaw v2 pipeline) flagged the issues")
    blocks.append("below. Produce a CORRECTED full rubric (not a diff) that:")
    blocks.append("  - keeps every existing criterion that is NOT flagged")
    blocks.append("  - fixes flagged criteria in place")
    blocks.append("  - adds new criteria to cover any listed inventory gaps")
    blocks.append("  - re-numbers the rubric as R1..Rn")
    blocks.append("")
    blocks.append("Output ONE JSON array (or `{\"rubric\": [...]}` envelope).")
    blocks.append("No prose, no markdown fences, no explanation. JSON only.")
    blocks.append("")

    if failures["uncovered_rqs"]:
        blocks.append(f"## Uncovered Stage 1 requirements ({len(failures['uncovered_rqs'])})")
        for u in failures["uncovered_rqs"]:
            text = _truncate(u["text"], 300)
            tc = f" trap={u['trap_concept']}" if u["trap_concept"] != "none" else ""
            blocks.append(f"- {u['id']} → {u['routes_to']}{tc}")
            blocks.append(f"    source: {u['source']}")
            blocks.append(f"    text:   {text}")
        blocks.append("")

    rule_sections = [
        ("Prefix-rule violations", "prefix_violations",
         "Rewrite each criterion below so it starts with the required prefix."),
        ("Turn-ID violations", "turn_id_violations",
         "Criterion text must NOT contain internal turn/mutation IDs."),
        ("Rule 1 — Banned-adverb violations", "adverb_violations",
         "Replace each adverb with the literal value/fact being checked."),
        ("Rule 4 — Negation violations", "negation_violations",
         "Rewrite affirmatively; polarity belongs in is_positive=false + negative score."),
        ("Rule 2 — Atomic-criterion violations", "compound_violations",
         "Split each flagged criterion into separate single-fact criteria."),
        ("Rule 3 — Self-contained violations", "self_contained_violations",
         "Embed the specific identifier and replace any pronoun with the named entity."),
    ]
    for title, key, hint in rule_sections:
        rows = failures.get(key, [])
        if not rows:
            continue
        blocks.append(f"## {title} ({len(rows)})")
        blocks.append(hint)
        blocks.append("")
        for v in rows:
            details = ", ".join(
                f"{k}={v[k]}" for k in v if k != "number"
            )
            blocks.append(f"- {v['number']}: {details}")
        blocks.append("")

    if failures.get("missing_trap_concepts"):
        blocks.append(
            f"## Trap concepts in pytest but missing from rubric "
            f"({len(failures['missing_trap_concepts'])})"
        )
        blocks.append(
            "Add at least one criterion whose prose references the underlying "
            "mechanism for each concept below."
        )
        blocks.append("")
        for c in failures["missing_trap_concepts"]:
            blocks.append(f"- {c}")
        blocks.append("")

    blocks.append("## PREVIOUS rubric (R1..Rn)")
    blocks.append("```json")
    blocks.append(json.dumps(prev_rubric, indent=2))
    blocks.append("```")
    blocks.append("")
    blocks.append("## STAGE 1 INVENTORY")
    blocks.append("")
    blocks.append(_truncate(requirements_inventory, 40000))
    return "\n".join(blocks)


def _save_and_validate(
    response_text: str,
    task_dir: Path,
    output_dir: Path,
    raw_dump_path: Path,
) -> tuple[bool, dict, dict]:
    raw_dump_path.write_text(response_text)
    save_result = rubric_generator.save_rubric(response_text, output_dir)
    ok, sections_data = validator.validate_and_collect(task_dir, output_dir)
    return ok, sections_data, save_result


def _run_stage_4_and_5(
    task_dir: Path,
    output_dir: Path,
    prompt_path: Path,
    model: str | None,
    max_retries: int,
) -> int:
    initial_prompt = prompt_path.read_text()
    print("[Stage 4]   initial: calling `claude` CLI (1–5 min)...")
    try:
        response_text = _call_claude_cli(initial_prompt, model=model)
    except RuntimeError as exc:
        print(f"            ✗ {exc}")
        print(
            "            (Stages 1+2+3 outputs are intact. Re-run with --no-auto"
        )
        print(
            "             to skip Stage 4, or save the response and use --save-from.)"
        )
        return 1

    print(f"            → response 1 ({len(response_text):,} chars)")
    raw_path = output_dir / "agent_response.txt"
    try:
        ok, sections_data, save_result = _save_and_validate(
            response_text, task_dir, output_dir, raw_path
        )
    except rubric_generator.RubricGenerationError as exc:
        print(f"            ✗ Failed to parse rubric JSON: {exc}")
        print(f"            Raw response saved at: {raw_path}")
        return 1

    print(f"            → rubric.json ({save_result['rubric_count']} criteria)")
    print("[Stage 5]   Validating disjointness + full coverage...")
    print(f"            initial result: {'PASS' if ok else 'FAIL'}")

    attempt = 1
    while not ok and attempt <= max_retries:
        failures = validator.summarize_failures_for_retry(sections_data)
        total = sum(
            len(failures.get(k, []))
            for k in (
                "uncovered_rqs", "prefix_violations", "turn_id_violations",
                "adverb_violations", "negation_violations",
                "compound_violations", "self_contained_violations",
                "missing_trap_concepts",
            )
        )
        if total == 0:
            print("            FAIL has no actionable items for retry — stopping.")
            break

        print(
            f"[Stage 4]   retry {attempt}/{max_retries}: "
            f"{len(failures['uncovered_rqs'])} uncovered, "
            f"{len(failures['prefix_violations'])} prefix, "
            f"{len(failures['turn_id_violations'])} turn-ids, "
            f"{len(failures['adverb_violations'])} adverbs, "
            f"{len(failures['negation_violations'])} negations, "
            f"{len(failures['compound_violations'])} compounds, "
            f"{len(failures['self_contained_violations'])} self-contained, "
            f"{len(failures['missing_trap_concepts'])} missing trap concepts"
        )
        patch_prompt = _build_patch_prompt(
            output_dir,
            sections_data.get("rubric", []),
            failures,
            attempt_index=attempt,
        )
        (output_dir / f"patch_prompt_attempt_{attempt}.md").write_text(patch_prompt)
        try:
            response_text = _call_claude_cli(patch_prompt, model=model)
        except RuntimeError as exc:
            print(f"            ✗ {exc}")
            break

        print(f"            → response {attempt + 1} ({len(response_text):,} chars)")
        raw_path = output_dir / f"agent_response_attempt_{attempt + 1}.txt"
        try:
            ok, sections_data, save_result = _save_and_validate(
                response_text, task_dir, output_dir, raw_path
            )
        except rubric_generator.RubricGenerationError as exc:
            print(f"            ✗ Failed to parse retry rubric JSON: {exc}")
            break

        print(f"            → rubric.json ({save_result['rubric_count']} criteria)")
        print(f"            retry result: {'PASS' if ok else 'FAIL'}")
        attempt += 1

    report_path = output_dir / "validation_report.md"
    print(f"[Stage 5]   → {report_path}")
    print(f"            Final result: {'PASS' if ok else 'FAIL'} after {attempt} attempt(s)")
    return 0 if ok else 1


def _run_dry_run(output_dir: Path) -> int:
    """After Stage 2, synthesize an empty agent_state.json and run pytest."""
    import re

    test_file = output_dir / "test_outputs.py"
    if not test_file.exists():
        print(f"[dry-run] test_outputs.py not found at {test_file}")
        return 1

    state_path = output_dir / "agent_state.json"
    if not state_path.exists():
        state_path.write_text("{}\n")
        print(f"[dry-run] synthesized empty {state_path.name} for the conftest fixture")

    print("[dry-run] Step 1/2: pytest --collect-only ...")
    collect = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", str(test_file)],
        capture_output=True, text=True, cwd=str(output_dir),
    )
    if collect.returncode not in (0, 5):
        print(
            f"[dry-run] COLLECTION FAILED (pytest exit {collect.returncode})"
            " — test_outputs.py is not importable"
        )
        print("--- pytest stdout ---")
        print(collect.stdout)
        print("--- pytest stderr ---", file=sys.stderr)
        print(collect.stderr, file=sys.stderr)
        return 1

    collected = [l for l in collect.stdout.splitlines() if "::" in l and "test_" in l]
    print(f"[dry-run]   collected {len(collected)} test(s)")

    print("[dry-run] Step 2/2: pytest -v --tb=line -rfE (against empty state) ...")
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--tb=line", "-rfE", str(test_file)],
        capture_output=True, text=True, cwd=str(output_dir),
    )
    output = run.stdout
    pass_count = len(re.findall(r"^test_outputs\.py::.+\bPASSED\b", output, re.MULTILINE))
    failed_tests = re.findall(r"^FAILED\s+(\S+)", output, re.MULTILINE)
    exception_hits = re.findall(
        r"^.*?:\d+:\s*(\w+(?:Error|Exception|Failed)):\s*(.*)$", output, re.MULTILINE
    )
    paired = list(
        zip(failed_tests, exception_hits + [("", "")] * max(0, len(failed_tests) - len(exception_hits)))
    )

    classified: dict[str, list[tuple[str, str]]] = {
        "STUB": [], "STATE_EMPTY": [], "ASSERTION": [], "LAMBDA_ERROR": [],
    }
    for name, (exc_type, exc_msg) in paired:
        rest = f"{exc_type}: {exc_msg}" if exc_type else "(unparseable failure)"
        if "SilentMutation" in name or "STUB" in rest or exc_type == "Failed":
            classified["STUB"].append((name, rest))
        elif exc_type in ("KeyError", "AttributeError", "TypeError", "IndexError"):
            classified["STATE_EMPTY"].append((name, rest))
        elif exc_type == "AssertionError":
            classified["ASSERTION"].append((name, rest))
        else:
            classified["LAMBDA_ERROR"].append((name, rest))

    print()
    print("=" * 72)
    print("[dry-run] CLASSIFICATION (empty agent_state.json)")
    print("=" * 72)
    print(f"  PASS              : {pass_count:3d}  (lambda runs cleanly even with empty state)")
    print(f"  FAIL_STATE_EMPTY  : {len(classified['STATE_EMPTY']):3d}  (KeyError/AttributeError/TypeError — expected with no state)")
    print(f"  FAIL_ASSERTION    : {len(classified['ASSERTION']):3d}  (assertion failed — expected with empty state)")
    print(f"  STUB              : {len(classified['STUB']):3d}  (silent-mutation pytest.fail stub — expected)")
    print(f"  REAL_ERROR        : {len(classified['LAMBDA_ERROR']):3d}  (real bug — fix the test definition)")

    if classified["LAMBDA_ERROR"]:
        print()
        print("[dry-run] Real bugs detected (unexpected exception type):")
        for name, msg in classified["LAMBDA_ERROR"]:
            print(f"  - {name}: {msg}")
        return 1

    print()
    print("[dry-run] OK — test_outputs.py is syntactically valid and every assertion is invocable.")
    print("[dry-run]      Replace agent_state.json with real post-run state to get a meaningful pass/fail signal.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "OpenClaw rubric + pytest generator v2 (Kensei v5.0). "
            "5-stage pipeline: (1) classify Kensei-bundle requirements, "
            "(2) emit pytest from deterministic subset, (3) assemble rubric "
            "prompt with non-deterministic + trap inventory, (4) `claude` CLI "
            "fills rubric.json, (5) validate. Forward-only: requires "
            "golden_steer_flow.md."
        )
    )
    p.add_argument("--task-dir", required=True, type=Path,
                   help="Path to task directory (contains prompt.txt, "
                        "golden_steer_flow.md, mock_data_description.md, mock_data/)")
    p.add_argument("--output-dir", type=Path, default=None,
                   help="Output dir (default: <task-dir>/tests/)")
    p.add_argument("--validate-only", action="store_true",
                   help="Skip generation; only validate existing rubric.json")
    p.add_argument("--print-prompt", action="store_true",
                   help="Print the assembled rubric prompt to stdout")
    p.add_argument("--save-from", type=Path, default=None,
                   help="Parse agent response from this file and write rubric.json")
    p.add_argument("--no-auto", action="store_true",
                   help="Stop after Stage 3 (skip the `claude` CLI call).")
    p.add_argument("--claude-model", default=None,
                   help="Override the `claude` CLI model for Stage 4")
    p.add_argument("--max-retries", type=int, default=2,
                   help="Max Stage 4 retries when Stage 5 reports gaps (default: 2)")
    p.add_argument("--dry-run", action="store_true",
                   help="After Stage 2, run pytest against an empty agent_state.json "
                        "to verify test_outputs.py is syntactically valid. Skips Stages 3+.")
    args = p.parse_args(argv)

    task_dir = args.task_dir.resolve()
    output_dir = (args.output_dir or (task_dir / "tests")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.save_from is not None:
        response_path = args.save_from.resolve()
        if not response_path.exists():
            print(f"--save-from path does not exist: {response_path}")
            return 1
        print(f"Parsing agent response from {response_path}...")
        result = _save_from_response(response_path, output_dir)
        print(f"  → rubric.json ({result['rubric_count']} criteria)")
        print()
        print("Now validating...")
        ok = validator.validate(task_dir, output_dir)
        print(
            f"Result: {'PASS' if ok else 'FAIL'} — see "
            f"{output_dir / 'validation_report.md'}"
        )
        return 0 if ok else 1

    if not args.validate_only:
        print("[Stage 0]   Loading Kensei v5.0 bundle...")
        steer, description, data = _load_bundle(task_dir)
        print(
            f"            golden_steer: {len(steer.value_lock)} value-lock entries, "
            f"{len(steer.canonical_steps)} canonical steps, "
            f"{len(steer.fairness_ledger)} fairness rows, "
            f"{len(steer.checkers)} checkers, "
            f"{len(steer.mutations)} mutations, "
            f"poison_pill={'yes' if steer.poison_pill else 'no'}"
        )
        print(
            f"            mock_data:    {data.file_count()} files across "
            f"{len(data.services())} service(s)"
        )

        print(
            "[Stage 1+2] Classifying requirements + generating pytest from "
            "deterministic subset..."
        )
        cov = pytest_generator.generate(
            task_dir, output_dir,
            steer=steer, description=description, mock_data=data,
        )
        stats = cov.get("requirement_stats", {})
        print(
            f"            requirements.json: {stats.get('total', 0)} total "
            f"(pytest={stats.get('deterministic_pytest', 0)}, "
            f"rubric={stats.get('non_deterministic_rubric', 0)})"
        )
        print(
            f"            test_outputs.py:   {cov['total_pytest_functions']} fns "
            f"(value_lock: {cov['value_lock_count']}, "
            f"checkers: {cov['checker_count']}, "
            f"stubs: {cov['stub_count']}, "
            f"poison_pill: {cov['poison_pill_count']})"
        )
        missing = cov.get("value_lock_in_mock_data", {}).get("missing", [])
        if missing:
            print(
                f"            ⚠ {len(missing)} VALUE_LOCK entries do not appear "
                f"in mock_data: {', '.join(missing)}"
            )

        if args.dry_run:
            print()
            print(
                "[Stage 2-DRY] Verifying test_outputs.py syntax + assertion invocability"
                " against empty agent_state.json..."
            )
            return _run_dry_run(output_dir)

        print(
            "[Stage 3]   Assembling rubric prompt with the non-deterministic + trap inventory..."
        )
        system_prompt, user_prompt = _assemble_prompt(
            task_dir, output_dir,
            steer=steer, description=description, data=data,
        )
        prompt_path = _write_prompt_file(output_dir, system_prompt, user_prompt)
        print(f"            → {prompt_path}")

        if args.print_prompt:
            print("\n" + "=" * 72)
            print("SYSTEM PROMPT")
            print("=" * 72)
            print(system_prompt)
            print("\n" + "=" * 72)
            print("USER PROMPT")
            print("=" * 72)
            print(user_prompt)
            print("=" * 72)

        if args.no_auto or args.print_prompt:
            print()
            print("Next steps (Stages 4 + 5 skipped):")
            print("  1. Feed the prompt to your agent:")
            print(f"       {prompt_path}")
            print("  2a. Save the agent's full JSON response and run:")
            print(f"       python run.py --task-dir {task_dir} --save-from response.json")
            print("  2b. OR drop in rubric.json yourself and run:")
            print(f"       python run.py --task-dir {task_dir} --validate-only")
            return 0

        return _run_stage_4_and_5(
            task_dir=task_dir,
            output_dir=output_dir,
            prompt_path=prompt_path,
            model=args.claude_model,
            max_retries=args.max_retries,
        )

    rubric_path = output_dir / "rubric.json"
    if not rubric_path.exists():
        print(f"rubric.json not found at {rubric_path} — run without --validate-only first.")
        return 1

    print("Validating rubric.json + test_outputs.py...")
    ok = validator.validate(task_dir, output_dir)
    print(
        f"Result: {'PASS' if ok else 'FAIL'} — see "
        f"{output_dir / 'validation_report.md'}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
