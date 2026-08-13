# Rubric Generation — Per-Task User Prompt (Kensei v5.0)

You are operating under the system prompt that defines the single-file rubric format, the disjoint rule against pytest, the 6 trap concepts, and the plain-prose §5A criterion-writing rules. Read the task inputs below and produce the rubric JSON.

This prompt is the output of **Stage 3** of the v2 pipeline. Stage 1 already classified every requirement in the bundle as deterministic or non-deterministic. Stage 2 already emitted pytest for the deterministic half. Your job is **Stage 4**: write the rubric for the non-deterministic half (including the subjective layer of every trap).

---

## TASK CONTEXT

```
Focal event:         {{FOCAL_EVENT}}
Scope boundary:      {{SCOPE_BOUNDARY}}
Persona:             {{TASK_PERSONA}}
Active services:     {{ACTIVE_SERVICES}}
Distractor services: {{DISTRACTOR_SERVICES}}
```

---

## STAGE 1 OUTPUT — Non-deterministic requirements inventory (THIS IS YOUR COVERAGE FLOOR)

The Stage 1 classifier walked ``prompt.txt`` + ``golden_steer_flow.md`` Sections 2/4/6/7 + ``mock_data_description.md`` PART B B4 and extracted every requirement that is NOT deterministic. Each row below is a requirement the rubric layer is responsible for.

The deterministic items (routed to pytest) are intentionally hidden — they are already in ``test_outputs.py`` below and are OFF-LIMITS for the rubric.

{{REQUIREMENTS_INVENTORY}}

The inventory is heuristic. You may add criteria for non-deterministic requirements the classifier missed, but you may not drop any flagged row.

---

## prompt.txt (the agent-facing task description)

```
{{PROMPT_BODY}}
```

---

## golden_steer_flow.md — Section 2: Canonical Solve Path

The 6-step solve path a 3-expert-convergent agent follows. Use this to understand what the agent must reason about; each step that produces a state change is already in pytest, while each step that explains / identifies / reconciles is rubric-territory.

{{CANONICAL_PATH}}

---

## golden_steer_flow.md — Section 3: Value Lock (concrete answer values)

Every concrete value the agent must produce, with its mock-data source. Pytest already asserts each row at the value level; the rubric explains *why* each value was chosen.

{{VALUE_LOCK}}

---

## golden_steer_flow.md — Section 4: Fairness Ledger (the trap source)

Every trap in the task, with carrier file and materialized form. **Every row below MUST have at least one rubric criterion that probes its subjective layer** (explanation quality, refusal quality, reconciliation quality, etc.) using real entities from the mock-data sample.

{{FAIRNESS_LEDGER}}

---

## golden_steer_flow.md — Section 6: Poison-Pill Record (red-line, if present)

{{POISON_PILL}}

---

## mock_data_description.md — PART B B4: Rubric Contract

Required facts, required refusals, hard-fail negative checkers, completeness requirement.

{{RUBRIC_CONTRACT}}

---

## Sample of real mock-data entity names + IDs + values (USE THESE in your criteria)

To satisfy Rule 3 (self-contained), every criterion embeds at least one concrete identifier. Use entities from this sample whenever you need to name a specific claim, party, policy, file, or amount.

{{MOCK_DATA_VALUES}}

---

## golden_steer_flow.md — Section 7: CHECKERS list (these are in pytest already)

For reference only — these checks are deterministic and already in ``test_outputs.py``. Do NOT duplicate them in the rubric.

{{CHECKERS}}

---

## ALREADY-GENERATED PYTEST (do NOT duplicate any of these checks)

```python
{{PYTEST_BODY}}
```

---

## RUBRIC STYLE EXAMPLES (use plain prose like this — NOT bracketed tags)

The following are example criteria in the v2 plain-prose style. Note: NO bracketed tag prefixes; every criterion begins immediately with ``"The response"`` or ``"The agent"``; each criterion embeds at least one concrete identifier.

{{RUBRIC_TEMPLATE_EXAMPLES}}

---

## YOUR JOB

Produce a single JSON array of criteria conforming to the system prompt. Either:

```json
[ {...}, {...}, ... ]
```

or with the optional envelope:

```json
{"rubric": [ {...}, {...}, ... ]}
```

### Coverage you MUST hit

- Every row in the Stage 1 inventory is covered by ≥1 rubric criterion.
- Every row in the Fairness Ledger has ≥1 criterion probing its subjective layer.
- The Poison-Pill (if present) has ≥1 negative criterion (``is_positive: false`` + negative score) about refusal quality.
- Every required fact / refusal in the B4 Rubric Contract has ≥1 criterion.
- The rubric does NOT duplicate any check pytest already performs.

### Required structural properties

#### Criterion writing rules (apply to every criterion — full spec in §5A of the system prompt; violators are auto-rejected at Stage 5)

1. **Rule 1 — Adverb-free.** No ``explicitly``, ``exactly``, ``correctly``, ``consistently``, ``appropriately``, ``properly``, ``fully``, ``completely``, ``clearly``, ``plainly``, ``adequately``, ``sufficiently``, ``accurately``, ``thoroughly``, ``reasonable``, ``sensible``, ``proper``.
2. **Rule 2 — Atomic.** One sentence, one verb, one observable fact. No `` and ``, `` while ``, `` including ``, `` as well as ``.
3. **Rule 3 — Self-contained (validator-enforced).** Every criterion contains at least one concrete identifier (digit run, UPPERCASE hyphenated code, quoted literal, dotted notation). No bare ``it`` / ``they`` / ``them``.
4. **Rule 4 — Affirmative-only.** No ``not``, ``does not``, ``do not``, ``must not``, ``fails to``, ``fail to``, ``avoids``, ``refuses``, ``omits``, ``without``, ``never``. Polarity lives in ``is_positive: false`` + negative ``score``.
5. **Score-polarity lock.** ``score`` ∈ {-5, -3, -1, 1, 3, 5}. ``is_positive: true`` → score ∈ {1, 3, 5}. ``is_positive: false`` → score ∈ {-1, -3, -5}. ≥1 ``is_positive: false`` required.

#### Other structural rules

- Plain prose, **NO bracketed tag prefixes** like ``[CORE — ...]`` or ``[TRAP — ...]``. Start immediately with ``"The response"`` or ``"The agent"``.
- Each criterion is value-level (names the specific entity), not existence-level.
- **NO turn-ID references** (``T0`` / ``T42`` / ``RL1`` / ``SM3`` / ``"turn 17"``). Describe the moment by content.
- Score distribution: ≥2 criteria at score 5; several at 3; several at 1; ≥1 negative.
- Numbering sequential ``R1, R2, ..., Rn``.
- No ``trap_concept`` field — the rubric stores only the 7 core fields.

### Output

A single JSON array (or ``{"rubric": [...]}`` envelope). No markdown fences. No prose. Just the JSON.
