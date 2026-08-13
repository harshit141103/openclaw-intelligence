# Golden Trajectory — Process & Schema

---

## Overview

The golden trajectory is the ground-truth "perfect agent" execution of a task. It defines exactly what a correct agent should do at every turn — which tools to call, what outputs to produce, and why.

---

## Construction Process

### Step 1: Complete the Task First (Days 1–2)

The task must be fully authored before any golden trajectory work begins:
- `task.py` finalized (turns, mutations, checkers)
- Real-world artifacts sourced and staged
- Inject directories populated
- All checkers written and syntactically valid

### Step 2: Model Validation Run (Day 3, first half)

Run a SOTA model (Opus 4.7) end-to-end on the completed task.

| Action | Purpose |
|--------|---------|
| Run model through all turns | Collect raw trajectory (tool calls, outputs, service writes) |
| Run checkers against model output | Quantify difficulty — expect <30% strict pass |
| Identify specific failures | Map which traps fired, which mutations the model missed |
| Flag ambiguities | If model gets something right for wrong reason → fix checker |

**Difficulty Gate:**
- Opus strict pass < 30% → Proceed to golden trajectory
- Opus strict pass > 30% → Tighten traps, add mutations, re-run

### Step 3: Author Golden Trajectory (Day 3–4)

Using the model's failures as a "what NOT to do" reference, the SWE writes the correct agent behavior per turn.

**For each turn, the SWE writes:**

1. **Reasoning** — The internal thought process a perfect agent should have. Explains WHY these actions are correct and what traps to avoid.

2. **Actions** — Ordered sequence of tool calls. Critically includes re-reading services after mutations (the thing models miss).

3. **Outputs** — Exact artifacts produced: file contents, email bodies, spreadsheet cell values, Notion updates, calendar events.

4. **Checker Results** — Confirms every checker for this turn passes against the golden outputs.

**Key principle:** The SWE designed the traps, so they know the correct path. The model run just confirms the traps work and reveals any ambiguity in the prompts.

### Step 4: Validate (Day 4)

- Run all checkers against golden trajectory outputs → 100% pass required
- Re-run checkers a second time → bit-identical results (determinism check)
- Cross-reference: every checker has a corresponding golden output that satisfies it

---

## Why Model-First, GT-Second

1. **Difficulty gate** — No point writing a golden trajectory for a task the model already passes.
2. **Failure map** — Model's specific failures show exactly which traps fired. SWE writes golden knowing "Opus used $52,800 here — golden must use $49,100 and explain why."
3. **Ambiguity detection** — If model gets something right for the wrong reason (lucky keyword match), that's a checker vulnerability to fix before GT.
4. **Efficient GT writing** — SWE can diff against model output: "correct here, wrong here, wrong here" → golden trajectory is the corrected version with reasoning.

---

## Delivery Schema — `golden_trajectory.json`

```json
{
  "task_id": "INS_001_auto_claim_settlement",
  "model_used": "human_golden",
  "baseline_model": "claude-opus-4.7",
  "baseline_strict_pass_rate": 0.12,
  "created_by": "swe_identifier",
  "created_at": "2026-06-01T10:00:00Z",
  "turns": [
    {
      "turn": 0,
      "day": 1,
      "reasoning": "This is Day 1 intake. I must review all materials across all 5 services before writing anything. Critical: examine damage photos carefully against the written estimate to catch discrepancies. I must NOT send any outbound emails — instruction says internal review only.",
      "actions": [
        {
          "step": 1,
          "tool": "notion_read",
          "params": { "page_id": "policy_mci_7829_a" },
          "expected_observation": "Policy #MCI-7829-A: collision coverage $50,000, liability $100,000, deductible $1,000. No endorsements at this time."
        },
        {
          "step": 2,
          "tool": "sheets_read",
          "params": { "file": "repair_estimates.xlsx", "sheet": "Sheet1" },
          "expected_observation": "18 line items, total $47,200. Row 12: 'Rear-left quarter panel replacement' at $8,400."
        },
        {
          "step": 3,
          "tool": "filesystem_read",
          "params": { "path": "police_report.pdf" },
          "expected_observation": "Two-vehicle collision, other driver at fault, rear-end impact."
        },
        {
          "step": 4,
          "tool": "filesystem_read",
          "params": { "path": "damage_photo_rear_left.jpg" },
          "expected_observation": "Photo shows minor bumper scuff/crack — NOT consistent with full quarter panel replacement claimed in estimate."
        },
        {
          "step": 5,
          "tool": "filesystem_write",
          "params": {
            "path": "initial_assessment.md",
            "content": "..."
          },
          "expected_observation": "File written successfully."
        }
      ],
      "outputs": {
        "files_written": [
          {
            "path": "initial_assessment.md",
            "content": "# Initial Assessment — Claim #MC-2026-4471\n\n## Incident Summary\n...\n\n## Coverage Verification\n- Policy: MCI-7829-A\n- Collision limit: $50,000\n- Deductible: $1,000\n...\n\n## Discrepancies\n- **CRITICAL**: Rear-left damage photo shows minor bumper scuff only, but estimate claims full quarter panel replacement ($8,400). Likely inflated.\n..."
          }
        ],
        "emails_sent": [],
        "sheets_written": [],
        "notion_writes": [],
        "calendar_events": []
      },
      "checker_results": [
        { "checker_id": "D1_C1", "expected": true, "note": "File exists" },
        { "checker_id": "D1_C2", "expected": true, "note": "Mentions $50,000 collision limit" },
        { "checker_id": "D1_C3", "expected": true, "note": "Identifies rear-left photo vs estimate discrepancy" },
        { "checker_id": "D1_C4", "expected": true, "note": "Mentions $1,000 deductible" },
        { "checker_id": "D1_C5", "expected": true, "note": "No emails sent (red-line respected)" }
      ]
    }
  ],
  "final_score": {
    "total_checkers": 38,
    "passed": 38,
    "strict_pass": true
  }
}
```

---

## Schema Reference

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Matches `task.py` TASK_METADATA.id |
| `model_used` | string | `"human_golden"` for author-written |
| `baseline_model` | string | SOTA model used for validation run |
| `baseline_strict_pass_rate` | float | Model's strict pass rate (confirms difficulty) |
| `turns[].turn` | int | Turn index (0-based) |
| `turns[].day` | int | Simulated workday number |
| `turns[].reasoning` | string | Chain-of-thought explaining WHY these actions are correct |
| `turns[].actions[]` | array | Ordered tool calls with params and expected observations |
| `turns[].outputs` | object | All artifacts produced this turn (files, emails, sheets, notion, calendar) |
| `turns[].checker_results[]` | array | Expected checker verdicts — all must be `true` |
| `final_score.strict_pass` | boolean | Must be `true` — golden trajectory passes 100% of checkers |

---

## Real-World Artifact Sourcing (No AI Synthesis)

| Artifact Type | Source | Examples |
|---------------|--------|----------|
| PDFs | Public govt filings, court records, real policy templates | NHTSA accident reports, state DOI forms, actual insurance declarations pages |
| Photos | Creative Commons datasets, stock photo with commercial license | IIHS crash test photos, auto repair documentation images |
| Spreadsheets | Real financial templates, public dataset exports | Actual body shop estimate formats (Mitchell/CCC), treasury data |
| Audio | Licensed stock audio, public domain recordings | Real recorded statement templates (redacted), voicemail samples |
| Policy documents | Public sample policies from state DOI websites | Real auto policy jackets with endorsement formats |
