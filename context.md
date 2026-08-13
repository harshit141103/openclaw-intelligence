# Talos SFT — Context

**Owner:** Ethara.AI | **Project:** Openclaw RL  
**Purpose:** SFT/RL training data authoring pipeline — produces multi-turn, multi-day agentic tasks that systematically fail frontier LLMs.

---

## What This Repo Is

A task authoring framework for creating evaluation scenarios that expose weaknesses in frontier models (Claude Opus, Sonnet, etc.) on realistic multi-day workplace workflows.

Inspired by two benchmarks:
- **ClawMark** (Evolvent AI, NUS, MIT, UC Berkeley) — multi-day coworker agent evaluation with silent mutations, red-lines, backend writeback
- **OfficeQA Pro** (Databricks AI Research) — enterprise document reasoning with temporal revisions, analytical precision

---

## Architecture

Tasks run on the **OpenClaw Harness** — isolated Docker Compose stacks with 5 mock services:

| Service | Purpose |
|---------|---------|
| Filesystem | Mounted workspace — files, artifacts |
| GreenMail (SMTP/IMAP) | Email communication |
| Notion-compatible KB | Policies, wikis, project records |
| Google Sheets-compatible | Spreadsheets, data |
| Radicale (CalDAV) | Calendar, scheduling |

An **orchestrator** advances turns (simulated days), applies between-turn mutations, and runs deterministic Python checkers against live service state.

---

## Task Bundle Structure

```
task_name/
├── task.py              # Metadata, turns, mutations, checker rubric
├── inject/
│   ├── stage0/          # Seeded at task start
│   ├── stage1/          # Injected between Day 1 → Day 2
│   ├── stage2/          # Injected between Day 2 → Day 3
│   └── ...
├── artifacts/           # Multimodal evidence (PDFs, audio, images, spreadsheets)
└── README.md            # Human-readable task description
```

---

## Design Principles

| Principle | How |
|-----------|-----|
| Fail frontier models | Silent mutations, temporal traps, cross-modal contradictions |
| No LLM-as-judge | All checkers are deterministic Python (lambdas querying service state) |
| Multi-system writeback | Agent must commit results to 4+ services, not just reason |
| Red-line pressure | Social engineering pressure — agent must NOT act prematurely |
| 4-phase quality gate | Author → Source artifacts → Review (3 AI audits + human) → Trajectory verify |

---

## Failure Categories Targeted

| Category | Failure Rate | Trigger |
|----------|-------------|---------|
| Silent-change detection | 56.5% | Mutate service values between turns without announcement |
| Backend writeback | 53.6% | Require agent to commit to a service, not just reason |
| Red-line / premature action | Universal | Pressure + withheld dependency |
| Temporal revision | High | Same metric, multiple values across revisions |
| Adjacent value extraction | High | Dense nested tables, similar labels |
| Analytical precision | High | Multi-step formulas, specific rounding |

---

## Current State

- **1 completed task:** `insurance_auto_claim_settlement` — 5 days, 38 checkers, 4 red-lines, estimated <10% strict pass on frontier models
- **Inject stages** scaffolded (stage0–stage4), artifacts pending sourcing
- `README-Claude-Small-Business.md` is reference material (domain inspiration)

---

## Key Files

| File | Purpose |
|------|---------|
| `BRIEF-DataOps-TaskCreation.md` | Full methodology guide for task authors |
| `SUMMARY-Papers.md` | ClawMark + OfficeQA Pro paper summaries |
| `AHT-Breakdown.md` | Per-task time breakdown (16h / 4 days) and daily schedule |
| `GoldenTrajectory.md` | Golden trajectory process, delivery JSON schema, artifact sourcing |
| `tasks/insurance_auto_claim_settlement/task.py` | Reference implementation (turns, mutations, checkers) |
| `tasks/insurance_auto_claim_settlement/README.md` | Detailed task walkthrough with expected failures |

---

## Task Authoring Checklist

- [ ] Spans 3+ turns (simulated days)
- [ ] At least 1 silent mutation tied to a checker
- [ ] At least 1 writeback requirement (commit to a service)
- [ ] At least 1 red-line constraint (forbidden action under pressure)
- [ ] Evidence spans 2+ modalities
- [ ] Decoy values present (plausible-but-wrong data nearby)
- [ ] All checkers deterministic Python
- [ ] 3 invariants: silent→checker, cross-modal→2 modalities, red-line→state check
- [ ] Passed trajectory review with 2 reference models
- [ ] Bit-identical checker results across 2 re-runs
