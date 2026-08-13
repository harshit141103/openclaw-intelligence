# OpenClaw Rubric + Pytest Generator

A five-stage pipeline that turns an OpenClaw `task.py` (single-turn **or** multi-turn) plus its README and optional `inject/mutations.json` into a complete, non-overlapping, full-coverage evaluation triple:

- `test_outputs.py` — deterministic pytest assertions
- `rubric.json` — **normal** non-deterministic criteria (LLM-judged)
- `rubric_trap.json` — trap-concept criteria (LLM-judged, with `trap_concept` field)

## The 5-stage flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Stage 1 — Classify every requirement: deterministic vs non-deterministic     │
│           (requirement_extractor.py → requirements.json)                     │
└──────────────────────────────────────────────────────────────────────────────┘
                                  │
              ┌───────────────────┴───────────────────┐
              ▼                                       ▼
┌──────────────────────────────┐         ┌─────────────────────────────────────┐
│ Stage 2 — pytest from        │         │ Stage 3 — Assemble rubric prompt    │
│ deterministic requirements   │         │ from non-deterministic + trap       │
│ (pytest_generator.py →       │         │ requirements (run.py →              │
│ test_outputs.py)             │         │ rubric_generation_prompt.md)        │
└──────────────────────────────┘         └─────────────────────────────────────┘
                                                       │
                                                       ▼
                                  ┌──────────────────────────────────────────┐
                                  │ Stage 4 — Agent fills two rubrics        │
                                  │ (off-process LLM → response JSON object) │
                                  └──────────────────────────────────────────┘
                                                       │
                                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Stage 5 — Validate three-way disjoint + full Stage 1 coverage                │
│           (validator.py → validation_report.md, exit 0/1)                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

Single-turn tasks are the degenerate case of multi-turn (one entry in `TURNS`), so the same pipeline handles both — no special-casing.

### Why five stages

Stage 1 makes the routing **explicit and auditable**: every prompt sentence, every `task.py` CHECKER, every TURN instruction, and every mutation lands in exactly one row of `requirements.json` with a `routes_to` field. Stages 2 and 3 then *consume* that inventory rather than each one independently inspecting the task. The validator (Stage 5) closes the loop by replaying the inventory and confirming every row was actually covered by either pytest or the rubric.

This is the mechanism that satisfies all five of the user requirements at once:

| User requirement | Stage |
|---|---|
| "checks whether the part of the prompt is deterministic or non-deterministic and gather them" | 1 (`requirement_extractor.py`) |
| "take all the deterministic parts and generate pytest from them" | 2 (`pytest_generator.py`) |
| "non-deterministic part left + trap coverage will be used to generate the rubric" | 3+4 (`run.py` + agent) |
| "pytest and rubric will not overlap" | 5 (validator's three-way Jaccard check) |
| "pytest + rubrics will cover full task" | 5 (validator's Stage 1 inventory coverage check #14/18) |

## The three output layers

| Layer | File | What goes here | Mechanism | Fields | Numbering |
|---|---|---|---|---|---|
| Deterministic | `tests/test_outputs.py` | State changes, API calls, file contents, exact values, negative state assertions | Python pytest assertions | n/a | — |
| Non-deterministic (normal) | `tests/rubric.json` | Subjective quality, reasoning explanation, summary correctness, format adherence, helpfulness — everything the prompt asks for that isn't a hard state change and isn't a trap | Binary criteria scored by an LLM judge | **7** (number, criterion, is_positive, type, evaluation_target, importance, score) | `R1..Rn` |
| Trap coverage | `tests/rubric_trap.json` | The subjective layer of the 6 OpenClaw trap concepts (e.g. "did the agent explain *why* the silent mutation matters?") | Binary criteria scored by an LLM judge | **8** (the 7 above + `trap_concept`) | `T1..Tm` |

**All three sets are pairwise disjoint.** Nothing pytest checks appears in either rubric. Nothing in `rubric.json` appears in `rubric_trap.json`.

## Coverage contract

| Layer | Must cover | Must NOT cover |
|---|---|---|
| `test_outputs.py` | **Every** deterministic requirement in `requirements.json` (`routes_to=pytest`) | Anything subjective |
| `rubric.json` | **Every** non-deterministic non-trap requirement in `requirements.json` (`routes_to=normal_rubric`) | Anything in pytest; anything trap-specific |
| `rubric_trap.json` | The subjective layer for each trap requirement in `requirements.json` (`routes_to=trap_rubric`), plus ≥1 criterion per trap concept actually present | Anything in pytest; anything in `rubric.json` |

The validator enforces all three rows — uncovered Stage 1 rows are hard failures.

## Files

```
generator/
├── system_prompt.md            # The "constitution" — five-stage pipeline, two-array schema, trap concepts
├── rubric_prompt_template.md   # Per-task user prompt template ({{PLACEHOLDERS}} incl. {{REQUIREMENTS_INVENTORY}})
├── requirement_extractor.py    # Stage 1: classify prompt + checkers + turns + mutations → requirements.json
├── pytest_generator.py         # Stage 2: requirements.json + task.py + mutations → test_outputs.py
├── rubric_generator.py         # Stage 4 parser: agent JSON → rubric.json + rubric_trap.json
├── validator.py                # Stage 5: 18 checks incl. three-way disjoint + Stage 1 coverage
├── run.py                      # CLI orchestrator for stages 1→2→3 and Stage 5
└── README.md                   # This file
```

## Usage

**No API key required by the generator itself.** Stages 1, 2, 3, and 5 are pure Python. Only Stage 4 (the rubric LLM call) is off-process.

```bash
# Stages 1+2+3 — classify, emit test_outputs.py, assemble rubric_generation_prompt.md
python run.py --task-dir tasks/clinical_trial_adverse_event_escalation

# Stage 4 — feed rubric_generation_prompt.md to your agent.
#           The agent returns a JSON object: {"normal_rubric": [...], "trap_rubric": [...]}.

# Stage 5 — save the agent response and let the orchestrator split + validate:
python run.py --task-dir tasks/clinical_trial_adverse_event_escalation \
              --save-from response.json

# OR manually save the two arrays as rubric.json + rubric_trap.json and run:
python run.py --task-dir tasks/clinical_trial_adverse_event_escalation --validate-only
```

To print the full prompt to stdout (useful for piping directly to an agent):

```bash
python run.py --task-dir tasks/my_task --print-prompt
```

### Flags

| Flag | Behavior |
|---|---|
| (default) | Run Stages 1+2+3: generate `requirements.json`, `test_outputs.py`, `trap_coverage.json`, `rubric_generation_prompt.md`. |
| `--save-from <path>` | Run Stage 5 from an agent response: parse the JSON object at `<path>`, write `rubric.json` + `rubric_trap.json`, validate. |
| `--validate-only` | Run Stage 5 only: validate existing `rubric.json` + `rubric_trap.json` against `test_outputs.py` and `requirements.json`. |
| `--print-prompt` | After Stage 3, also print the assembled prompt to stdout. |
| `--output-dir <path>` | Override output directory (default: `<task-dir>/tests/`). |

## Outputs (under `<task-dir>/tests/`)

| File | Produced by | Stage | Content |
|---|---|---|---|
| `requirements.json` | `requirement_extractor.py` | 1 | Unified inventory: every prompt sentence, CHECKER, TURN instruction, mutation → one row with `id`, `source`, `text`, `classification`, `trap_concept`, `routes_to`, `checker_id?`, `turn?`. The *authoritative* coverage floor. |
| `test_outputs.py` | `pytest_generator.py` | 2 | One pytest fn per `CHECKER` from `task.py`, plus `@pytest.mark.skip` stubs for silent mutations with no obvious CHECKER coverage. Each fn tagged with `# trap: <concept>` and `# requirement: RQ<n>`. Authoritative list of all deterministic assertions. |
| `trap_coverage.json` | `pytest_generator.py` then `validator.py` | 2/5 | `{trap_concept: [pytest_fn_names]}` + `deterministic_inventory` + `pytest_function_to_requirement_id` + `requirement_stats` + post-validation combined coverage stats (`in_pytest`, `in_trap_rubric`, totals per concept) + overlap flags. |
| `rubric_generation_prompt.md` | `run.py` | 3 | The exact system + user prompts, with `{{REQUIREMENTS_INVENTORY}}` substituted to a markdown table of every non-deterministic Stage 1 row. Audit artifact for reproducibility. |
| `rubric.json` | `rubric_generator.py` from agent response | 4 | **Normal** rubric: 10–25 criteria, 7 fields each, no `trap_concept`. Covers non-deterministic prompt requirements. Numbering `R1..Rn`. |
| `rubric_trap.json` | `rubric_generator.py` from agent response | 4 | **Trap** rubric: ≥1 criterion per present trap concept, 8 fields each (incl. `trap_concept` ∈ 6 real concepts; never `"none"`). Numbering `T1..Tm`. |
| `validation_report.md` | `validator.py` | 5 | Pass/fail for all 18 checks (per-array schema, counts, prefixes, mandatory items, score distribution, numbering, three-way disjoint, trap concept coverage, **Stage 1 inventory coverage**). |

## The 6 trap concepts (from `feedback/knowledge.md`)

The Stage 1 extractor tags every requirement (heuristically) and the Stage 4 LLM tags every `rubric_trap.json` criterion with one of:

| ID | Concept | Empirical failure rate |
|---|---|---|
| `silent_mutation` | Service state changes between turns without announcement | 56.5% |
| `backend_writeback` | Agent reasons correctly but doesn't commit to a service | 53.6% |
| `red_line` | Forbidden action under social pressure | universal |
| `cross_modal_contradiction` | Conflicting values across email / sheet / PDF / audio | high |
| `decoy_value` | Plausible-but-wrong data adjacent to correct data | high |
| `temporal_revision` | Multiple versions of same metric; only latest is correct | high |

`rubric_trap.json` must use one of these six values for every `trap_concept` field — `"none"` is reserved for the extractor's `non_deterministic` classification of generic non-trap requirements and is never valid in the trap rubric.

After an evaluation run, the combined coverage in `trap_coverage.json` answers: *"What was the model's pass rate per trap concept, separately for deterministic state checks (pytest) vs subjective explanation quality (trap_rubric)?"*

## How the four invariants are enforced

### 1. Routing (Stage 1)
`requirement_extractor.py` walks `task.py CHECKERS` (deterministic), `README.md` (sentences containing requirement indicators like *must*, *should*, *ensure*), each TURN's `instruction` field, and `inject/mutations.json` (silent vs loud). Every survivor gets a `classification` (`deterministic` or `non_deterministic`) and a `routes_to` field (`pytest`, `normal_rubric`, or `trap_rubric`). Trap detection is a keyword scan against the 6 concept vocabularies.

### 2. Deterministic coverage (Stage 2)
Every CHECKER becomes exactly one pytest function. Each function carries a `# requirement: RQ<n>` link back to its Stage 1 row. Silent mutations without CHECKER coverage get a `@pytest.mark.skip` stub so the gap is visible rather than silent.

### 3. Non-deterministic coverage (Stage 3+4)
The rubric prompt embeds the full inventory of `routes_to ∈ {normal_rubric, trap_rubric}` rows as a markdown table under `{{REQUIREMENTS_INVENTORY}}`. The system prompt declares this the LLM's *coverage floor*: every row must be covered by ≥1 criterion in the appropriate array. Deterministic rows are intentionally hidden from the prompt because they are owned by pytest.

### 4. Disjoint + full coverage (Stage 5)
The validator runs:

- **Disjoint** (checks #11–13): three-way Jaccard similarity at threshold 0.40 (normal⊥pytest, trap⊥pytest, normal⊥trap). Pairs above threshold are reported as overlap.
- **Coverage** (check #14): replays `requirements.json` and confirms every row is covered.
  - `routes_to=pytest`: matches `[<checker_id>]` tag in a test function's docstring.
  - `routes_to=normal_rubric`: ≥1 `rubric.json` criterion with Jaccard ≥ 0.18 against the requirement text.
  - `routes_to=trap_rubric`: ≥1 `rubric_trap.json` criterion with matching `trap_concept`, with text Jaccard preferred but concept-match alone accepted as fallback.
  - Uncovered rows are hard failures.
- **Schema** (checks #1–10, 15–17): per-array field presence, types, count bounds, prefix rule, mandatory items, score distribution, sequential numbering, trap-concept value range, trap coverage gaps.

The validator's exit code is 0 only if zero hard failures occurred across all 18 checks.

## Multi-turn behavior

The extractor walks `TURNS` in order. A turn's `instruction` field contributes per-turn `non_deterministic` rows; checkers carry a `turn` field; mutations get per-turn `source` strings (`TURN 2 silent mutation (claim_service)`). The pytest generator carries the turn number through to each test function's docstring. The rubric LLM is told via the inventory to treat each turn's requirements as a separate coverage obligation. Single-turn tasks just have `TURNS=[…]` of length one and follow the same code path.

## Notes / limitations

- **Stage 1 extraction is heuristic**: sentence-splitting plus keyword classification. False negatives (a missed prompt sentence) are caught by the validator's coverage check only if the LLM also misses it — the safety net here is having two independent walks of the same prompt. False positives (a non-requirement sentence promoted to a row) just add a redundant rubric criterion.
- **Trap tagging in pytest is heuristic**: keyword matching over CHECKER id + description + type, with confidence reported per fn. Mis-tags can be corrected by editing the emitted `# trap: <concept>` comment.
- **Silent-mutation coverage heuristic is approximate**: if any CHECKER exists on the same turn as a silent mutation, we assume coverage and skip the stub.
- **`rubric.json` count bounds are soft**: 10 minimum, 25 soft cap. The system prompt instructs the LLM to walk the inventory row-by-row, so the actual count scales with prompt complexity.
- **Rubric generation is non-deterministic by definition**: re-running the LLM yields different criteria. The validator catches structural problems but cannot verify "the rubric is the best possible rubric." That's a human judgment.
- **Legacy single-array agent responses are auto-split** by `rubric_generator.py`: items with a real `trap_concept` value go to `rubric_trap.json`; everything else (including `trap_concept: "none"` or missing) goes to `rubric.json` with the field stripped. This eases migration from the old single-rubric format.
