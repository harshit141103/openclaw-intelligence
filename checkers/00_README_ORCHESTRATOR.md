# QC Checker Orchestrator

**Version**: 3.0 — Split architecture for optimal LLM context management.

## Architecture

The QC pipeline is split into 4 focused checkers, each designed for a single LLM pass:

| File | Cognitive Mode | Checks | What It Catches |
|---|---|---|---|
| `01_structural_mechanical.md` | Deterministic — file existence, JSON schema, grep patterns | P1, P2, P3, P4, P7 (52 checks) | ~45% of defects — structural, test infra, rubric schema, oracle leaks |
| `02_semantic_crossfile.md` | Reasoning — cross-file data tracing, code analysis | P5, P6 (23 checks) | ~35% of defects — rubric/test/seed/API consistency, environment wiring |
| `03_design_difficulty.md` | Judgment — prompt quality, task design, difficulty | P8, P8B (20 checks) | ~15% of defects — prompt prose, media quality, join necessity, traps |
| `04_portfolio_runtime.md` | Portfolio — cross-task + evidence checking | P9, P10 (12 checks) | ~5% of defects — portfolio health, naming, runtime evidence |

**Total**: 107 checks across 4 files (~220 lines each vs 890 in one file).

## Execution Order (MANDATORY)

```
Pass 1: 01_structural_mechanical.md   ← Run FIRST. Cheapest checks, highest catch rate.
Pass 2: 02_semantic_crossfile.md      ← Run SECOND. Needs files read in Pass 1.
Pass 3: 03_design_difficulty.md       ← Run THIRD. Subjective judgment calls.
Pass 4: 04_portfolio_runtime.md       ← Run LAST. Cross-task + evidence. Needs Pass 1-3 results.
```

**Each pass is independent** — the LLM can be given one checker file at a time. Pass 4 benefits from having Pass 1-3 results available but can run standalone.

## How To Use

### Single-task validation:
```
Prompt: "Use [checker file] to validate the task at [path/to/task_name/]"
```
Run each checker file against the same task in sequence.

### Batch validation:
```
Prompt: "Use [checker file] to validate ALL tasks in [path/to/Deliverables/]"
```
Run Pass 1 across all tasks first (fast filter — identifies empty/broken tasks to skip). Then run Passes 2-3 only on tasks that survived Pass 1.

### Context budget guidance:
- Each checker is ~220 lines of instructions
- One task's files consume ~5K-15K tokens depending on complexity
- **Recommended batch size**: 3-5 tasks per LLM invocation per checker
- For 63 tasks: ~13 invocations per checker, ~52 total invocations

## Shared Output Schema

Every checker produces the SAME JSON format per task:

```json
{
  "task_id": "<dirname>",
  "checker": "01_structural | 02_semantic | 03_design | 04_portfolio",
  "verdict": "PASS | FIXABLE | FAIL",
  "hard_fails": [
    {"check_id": "P1.3", "title": "...", "file": "...", "description": "...", "fix_type": "auto-fixable | requires-human"}
  ],
  "should_fix": [
    {"check_id": "P3.12", "title": "...", "file": "...", "description": "..."}
  ],
  "review_flags": [
    {"check_id": "P8.4", "title": "...", "description": "..."}
  ]
}
```

### Final Verdict (after all 4 passes):
```
SHIPPABLE  = 0 HARD-FAILs across all 4 passes
FIXABLE    = 1-3 HARD-FAILs, all auto-fixable
NEEDS-REDESIGN = 4+ HARD-FAILs, or any requires-human HARD-FAIL
```

## Severity Tiers (Rebalanced)

| Tier | Count | When to use |
|---|---|---|
| **HARD-FAIL** | ~40 checks | Instant rejection. Meta WILL reject. Structural impossibility, data doesn't exist, contradictions. |
| **SHOULD-FIX** | ~45 checks | Scoring degradation. Fix before shipping, document if not fixed. |
| **REVIEW-FLAG** | ~15 checks | Needs human judgment. LLM flags but can't determine severity. Subjective items. |

## Deliverable Structure Reference

```
<task_name>/
  prompt.txt                          # Raw prompt text
  rubric.json                         # Rubric file — AT TASK ROOT
  golden_trajectory.json              # Reference trajectory
  trajectories/
    Claude Opus 4.7/pass_summary.json, run_1/{output.json, report.json}
    GPT 5.5/pass_summary.json, run_1/{output.json, report.json}
  rework/*.md                         # Optional — prior delivery feedback
  data/
    instruction.md                    # Prompt in markdown
    task.toml                         # Metadata + API config
    environment/
      Dockerfile
      docker-compose.yaml
      <svc-api>/                      # FLAT layout (youtube-api/, etsy-api/, etc.)
        server.py, requirements.txt, *.csv, *.json, *_data.py
      artifacts/inputs/files/         # User-uploaded media/documents
      persona/                        # SINGULAR directory
        AGENT.md (or AGENTS.md), SOUL.md, MEMORY.md
      skills/<skill-name>/SKILL.md
      litellm-proxy/
    solution/solve.sh
    tests/
      test.sh, test_outputs.py, test_weights.json
```

**API catalog** (ports 8000-8009): Amazon Seller, Etsy, Google Classroom, Instagram Graph, Linear, MyFitnessPal, Pinterest, QuickBooks, Ring, YouTube Data.
