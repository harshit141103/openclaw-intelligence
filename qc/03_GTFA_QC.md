# Kensei — Golden Steer Flow QC (Step 3 of 4)

> **Scope**: Validate the authoring trace (`golden_steer_flow.md`) for construction integrity: authoritative-value coverage, source-carrier traceability, FK consistency, trap materialization, ghost excludability, noise purity, schema fidelity. Verifies the task was built correctly, not just whether an answer exists.
> **Inputs**: `golden_steer_flow.md`, `TASK_PHASE1.md`, `prompt.txt`, `data/` directory, `mock_data/<api>/` directory, `persona/{AGENTS,MEMORY,SOUL}.md`, `environment/<slug>-api/<file>` (canonical schema source)
> **Prerequisite**: Prompt, Data & Alignment QC (Step 2) must PASS — specifically, the Ask Decomposition from Step 2 is required as input.
> **Verdict Framework**: PASS / MINOR_ISSUES / MAJOR_ISSUES / FAIL
> **Version**: 2.0 (June 2026)

---

> Every authoritative value in `golden_steer_flow.md` must be traceable to a single concrete source carrier (file:row:cell). Zero tolerance for fabrication, placeholders, or qualitative load-bearing values. Flag if the steer flow is producible from a single source class (LIVE alone / ARTIFACT alone / STALE alone) or if any gate from §2 of the steer flow is missing or marked FAIL.

---

## 1. Authoritative Values Coverage

Map every required fact derivable from the prompt's Ask Decomposition (Step 2) to a row in §1.1 Authoritative Values of `golden_steer_flow.md`:

| Ask # | Required Fact | Steer-Flow Row | Class | Concrete Value Present? | Status |
|---|---|---|---|---|---|

Checks:
- [ ] Every **deliverable fact** has a row in §1.1 Authoritative Values.
- [ ] Every **data-retrieval fact** has a Concrete value column populated (no placeholders, no `TBD`, no ellipsis, no `<token>`).
- [ ] Every **cross-reference fact** has a JOIN-style source carrier (two file paths or one carrier marked `mirrored in <other>`).
- [ ] Every **decision fact** has Class = `LIVE` or `ARTIFACT` (never `STALE`).
- [ ] Every **constraint fact** lives in §1.2 In-world scope boundary with the AGENTS.md or MEMORY.md rule cited.
- [ ] No required fact is left unaddressed.
- [ ] No row carries any of the banned vague qualifiers on a load-bearing slot: `approximately`, `roughly`, `around`, `about`, `~`, `mostly`, `largely`, `generally`, `typically`, `usually`, `often`, `ideally`, `preferably`, `effectively`, `appropriately`, `properly`, `correctly`, `accurately`, `clearly`, `consistent`, `relevant`, `appropriate`, `proper`, `at least`, `at most`, `atleast`, `atmost`, `successfully`, `meaningfully`, `reasonably`, `sufficiently`, `adequately`, `frequently`, `rarely`, `occasionally`, `sometimes`, `should try to`, `attempts to`. (Unified list, identical to `04_Rubric_QC.md` Phase 0 Rule 2.)

**FAIL trigger 1.a**: A required fact has no row in §1.1 Authoritative Values.
**FAIL trigger 1.b**: A row in §1.1 carries a placeholder, ellipsis, `TBD`, or banned vague qualifier on a load-bearing value.
**MAJOR_ISSUES**: A non-core required fact has no row.
**MINOR_ISSUES**: §1.1 introduces values the prompt never asked for (over-specification).

---

## 2. Source Carrier Traceability

### 2.1 Carrier Verification Table

| # | Field | Class | Source Carrier (file:row:cell) | Concrete Value | File Exists? | Row Contains Value? | Class Matches Location? | Status |
|---|---|---|---|---|---|---|---|---|
| C1 | [field name from §1.1] | LIVE / ARTIFACT / STALE | [exact file:row:cell] | [value at that location] | YES/NO | YES/NO | YES/NO | |

Trace every row in §1.1. For each:
- Verify the named file resolves to a real file in the task bundle.
- Verify the named row/cell/page/region actually contains the stated value.
- Verify Class agrees with location: `LIVE` carriers live under `mock_data/<api>/`, `ARTIFACT` carriers live under `data/`, `STALE` carriers have explicit `SUPERSEDED` marker plus the carrier of the live revision.

### 2.2 Correctness Verification

- [ ] Every quantitative value matches the carrier exactly (no rounding errors, no transpositions).
- [ ] Every identifier matches the carrier exactly (case + spelling, ISO timestamps include offset).
- [ ] Every decision derives from concrete carriers cited in §1.1 (not fabricated).
- [ ] No authoritative value contradicts the carrier it cites.
- [ ] For media-dependent values: the claimed region/page/cell content is consistent with the actual artifact in `data/`.
- [ ] Calculated values use formulas with carrier-grounded inputs and the result is itself stored in a carrier.

**FAIL trigger 2.2.a**: A core authoritative value contradicts the carrier it cites.
**FAIL trigger 2.2.b**: A core authoritative value references a file or row not present in the bundle (fabrication).
**FAIL trigger 2.2.c**: Class label and carrier path disagree (`LIVE` value carried by `data/`, `ARTIFACT` value carried by `mock_data/`).
**MAJOR_ISSUES**: A peripheral value contradicts its carrier or is fabricated.
**MAJOR_ISSUES**: A media-dependent value cannot be verified from the provided artifact.

---

## 3. Cross-Source Convergence (Three-Lens Audit)

### 3.1 Lens Presence Check

Verify §1.3 Convergence Check Across Three Expert Lenses is present and complete in `golden_steer_flow.md`:

| Lens | Required Coverage | Present? |
|---|---|---|
| Financial analyst | Money / balances / drift causes / threshold checks | YES/NO |
| Task-domain expert | Domain workflow / temporal ordering / red-line discipline | YES/NO |
| Rubric checker | Enumerated required facts + required refusals + hard-fail negative-check anchors | YES/NO |

### 3.2 Reachability Flags

- [ ] Every required fact appears under at least one lens conclusion.
- [ ] Every required refusal (e.g. poison-pill trap response) is named in the Rubric-checker lens with the violated rule cited.
- [ ] Steer flow producible from `mock_data/` alone (LIVE only)? → FLAG if YES (`data/` artifacts unused = HR2 violation).
- [ ] Steer flow producible from `data/` alone (ARTIFACT only)? → FLAG if YES (`mock_data/` decorative).
- [ ] Steer flow producible from persona alone? → FLAG if YES (data layer decorative).
- [ ] Zero cross-modal JOIN rows in §1.1? → FLAG if YES.
- [ ] Both source classes present but never joined inside a single fact? → FLAG if YES.

**FAIL trigger 3.2.a**: Steer flow fully producible from `mock_data/` alone (artifacts decorative).
**FAIL trigger 3.2.b**: Steer flow fully producible from `data/` alone (mock APIs decorative).
**FAIL trigger 3.2.c**: Steer flow fully producible from persona alone (data layer decorative).
**FAIL trigger 3.2.d**: One of the three lenses is missing or empty.
**MAJOR_ISSUES**: Zero cross-modal JOIN rows in §1.1; sources used independently but never fused.

---

## 4. Objectivity & Phrasing

Carries Rule 1 and Rule 2 from `04_Rubric_QC.md` Phase 0. Applies to every load-bearing string in `golden_steer_flow.md` (`§1.1` values, `§4` trap field strings, `§5` recipe descriptions, `§6` sweep assertions).

### 4.1 Banned Qualifiers and Phrasing

- [ ] Zero em-dashes (U+2014) in any load-bearing value or rule citation.
- [ ] Zero brackets (`<...>`, `[...]`, `{...}`) wrapping a value to be evaluated — values must be concrete, not templated.
- [ ] Zero placeholders: `TBD`, `XXX`, `<TOKEN>`, `{value}`, `...`, `tbd`, `??`.
- [ ] Zero banned vague qualifiers on load-bearing values: `approximately`, `roughly`, `around`, `about`, `~`, `mostly`, `largely`, `generally`, `typically`, `usually`, `often`, `ideally`, `preferably`, `effectively`, `appropriately`, `properly`, `correctly`, `accurately`, `clearly`, `consistent`, `relevant`, `appropriate`, `proper`, `at least`, `at most`, `atleast`, `atmost`, `successfully`, `meaningfully`, `reasonably`, `sufficiently`, `adequately`, `frequently`, `rarely`, `occasionally`, `sometimes`, `should try to`, `attempts to`. (Unified list, identical to `04_Rubric_QC.md` Phase 0 Rule 2.)
- [ ] Dates use ISO format with offset (`2026-10-16T16:00:00-05:00`) — not `Friday afternoon`, not `mid-October`.
- [ ] Dollar amounts include decimal cents (`$3,037.50`) — not `~$3k`.
- [ ] File paths are full paths from the task bundle root (`mock_data/plaid-api/accounts.csv`) — not abbreviated (`plaid.csv`).
- [ ] Identifiers match the carrier exactly (case + spelling).

### 4.2 Two-Evaluator Test

- [ ] Two independent evaluators given the same prompt + `golden_steer_flow.md` produce the same Authoritative Values table cell-for-cell.
- [ ] No row in §1.1 requires subjective judgment to verify.
- [ ] Every trap block in §4 has a single-key disambiguator that two evaluators would derive identically.

**FAIL trigger 4.1.a**: A load-bearing value carries a banned vague qualifier or placeholder.
**FAIL trigger 4.1.b**: A core authoritative value is not ISO-typed (date without offset, dollar without cents, identifier without exact carrier match).
**MAJOR_ISSUES**: A core authoritative value or trap disambiguator fails the two-evaluator test.
**MINOR_ISSUES**: A non-load-bearing prose line carries a vague qualifier.

---

## 5. Schema Fidelity (Gate K)

Validate §2 Gate K of `golden_steer_flow.md` against `environment/<slug>-api/<file>` canonical schemas.

- [ ] Every column header named in any `mock_data/<api>/<file>` matches the first row of `environment/<api>/<file>` exactly (case + spelling + order).
- [ ] No Phase-1 placeholder filenames used (e.g. `accounts.json` when canonical is `accounts.csv`; `bookings.csv` when canonical is `flight_offers.json`).
- [ ] Steer flow includes an explicit `HR6 schema-fidelity wins over Phase-1 placeholder` note for every divergence.
- [ ] FK columns named in §3 use canonical column names from the environment schemas.
- [ ] Foreign service files (e.g. `paypal-api/orders.csv` vs unsupported `paypal-api/transactions.csv`) are flagged when the steer flow names a non-canonical file.

**FAIL trigger 5.a**: A column header in any cited `mock_data/` file does not match `environment/<slug>-api/<file>` row 1.
**FAIL trigger 5.b**: A non-canonical filename is used without an explicit divergence note.
**MAJOR_ISSUES**: A canonical file exists but the steer flow uses a Phase-1 placeholder synonym.

---

## 6. Filler Competition Audit (§1.4)

Verify §1.4 Filler Competition Audit of `golden_steer_flow.md` proves uniqueness for every load-bearing slot.

- [ ] Every authoritative slot from §1.1 appears in §1.4 with a per-slot uniqueness proof.
- [ ] Each proof names the unique carrier row plus every variant-name ghost (e.g. `Bella Bella Alterations LLC` flagged as distinct from `Bella Donna Bridal & Alterations`).
- [ ] No load-bearing slot has more than one row carrying the same value in active service files.
- [ ] Variant-name ghosts are excluded by a single key (name mismatch, date mismatch, status mismatch).

**FAIL trigger 6.a**: A load-bearing slot has two or more rows in active service files carrying the same value.
**MAJOR_ISSUES**: A load-bearing slot is missing from §1.4 entirely.
**MINOR_ISSUES**: A variant-name ghost is named but the single-key exclusion is implicit instead of explicit.

---

## 7. Gate Report Audit (S11 Gates A–O+)

Validate §2 Internal Validation Report in `golden_steer_flow.md`. Every gate must be present and marked PASS with notes.

| Gate | Required Coverage | Status |
|---|---|---|
| A | Volume bands (per-service row counts within spec from `TASK_PHASE1.md` Part C) | PASS/FAIL |
| B | HR1 multi-source — signal carriers span ≥6 distinct sources | PASS/FAIL |
| C | HR2 non-text modality — image/PDF/xlsx carries plant values not in text-only carriers | PASS/FAIL |
| D | HR3 MM-Without — removing media drops ≥50% of required facts | PASS/FAIL |
| E | HR4 cross-modal fusion — stale carrier vs revision carrier resolved by single-key disambiguator | PASS/FAIL |
| F | HR5 cognitive steps — documented multi-step solve path with ≥6 distinct sources touched | PASS/FAIL |
| G | HR3 anti-leak — FORBIDDEN_IN_NOISE sweep passes for every plant value | PASS/FAIL |
| H | HR4 ghost excludability — every ghost row excludable by single key | PASS/FAIL |
| I | HR3 distractor purity — declared Distractor APIs carry zero plant values in the focal window | PASS/FAIL |
| J | HR1 FK consistency — every foreign key resolves; mirror values match | PASS/FAIL |
| K | HR6 schema fidelity — every column header matches `environment/<slug>-api/<file>` row 1 | PASS/FAIL |
| L | HR7 realistic filler — cultural-name mix, plausible dates within ±60 days of focal event | PASS/FAIL |
| M | HR8 internal validation — generator assertion sweeps run pre-emission | PASS/FAIL |
| N1 | Poison-pill carrier alignment — pill row in spec-named carrier with `from_addr` matching MEMORY contact | PASS/FAIL |
| O1 | Authoritative-vs-stale uniqueness — only one current value across all mock_data files | PASS/FAIL |

**FAIL trigger 7.a**: Any gate is marked FAIL or missing entirely.
**FAIL trigger 7.b**: A gate is marked PASS without notes (no evidence of the check).
**MAJOR_ISSUES**: A gate is marked PASS but the notes don't cite a specific carrier or count.

---

## 8. FK Consistency Proof Audit (§3)

Validate §3 FK Consistency Proof of `golden_steer_flow.md`.

- [ ] Every FK relation in the table resolves: Source row references a Target row that exists in the target file.
- [ ] Mirror values match across services bit-for-bit (gmail body timestamp ↔ calendar event `start`, transaction row ↔ receipt image OCR, etc.).
- [ ] Persona contacts (`from_addr` values) match `persona/MEMORY.md` Contacts section exactly.
- [ ] Drift-explanation chains (LIVE balance < MEMORY estimate) are explicable with concrete transactions naming dates + vendors + amounts.

**FAIL trigger 8.a**: An FK reference in §3 is unresolved (target row does not exist).
**FAIL trigger 8.b**: A mirror value in §3 differs across services (silent overwrite).
**MAJOR_ISSUES**: A drift-explanation chain has unexplained delta.

---

## 9. Trap Materialization Audit (§4)

Validate §4 Trap Materialization of `golden_steer_flow.md`. Every trap block must carry all required fields.

Required fields per trap block:

| Field | Required | What it means |
|---|---|---|
| `carrier_file` | YES | The exact `mock_data/` or `data/` file path holding the trap |
| `stale_val` | YES (for revision traps) | The misleading value the agent is tempted to use |
| `live_val` | YES (for revision traps) | The correct value the agent must adopt |
| `freshness_ts` | YES (for revision traps) | The timestamp or signal that proves which value is current |
| `drift_cause` | YES (for memory/balance traps) | The concrete chain of events that explains the gap |
| `disambiguator_key` | YES | The single key (date / status / `account_id` / etc.) that resolves the conflict |
| `uniqueness_check` | YES | Proof that no other row carries the same misleading value |
| `correct_response` | YES (for red-line / poison-pill traps) | The agent's correct action with rule citation |
| `checker_id + weight` | YES | The deterministic Python checker that grades the trap response |

Maps to D.5.4 9-Trap Inventory (from `Prompt-Input-Mock-QC.md`):
- Trap maps to ≥1 of `decoy-value` / `temporal-revision` / `cross-modal-contradiction` / `backend-writeback` / `distractor-noise` / `multi-hop-synthesis` / `financial-approval-threshold` / `constraint-conflict` / `poison-pill`.

**FAIL trigger 9.a**: A trap block is missing any required field listed above.
**FAIL trigger 9.b**: A trap's `disambiguator_key` is not a single key (e.g. requires joining three conditions).
**FAIL trigger 9.c**: A red-line trap has no `correct_response` with a verbatim AGENTS.md rule citation.
**MAJOR_ISSUES**: A trap does not map to any D.5.4 9-trap inventory category.

---

## 10. Ghost Recipe Ledger Audit (§5)

Validate §5 Ghost Recipe Ledger of `golden_steer_flow.md`.

- [ ] Table columns: `File | Recipe | Rows | Excludability key`.
- [ ] Every ghost row is excludable by a single key (date threshold, `status=cancelled`, name mismatch).
- [ ] Recipe names drawn from the canonical set: `WRONG_PERIOD`, `RETIRED_STATUS`, `SUBTLE_DUPLICATE`, `NAME_VARIANT`, `WRONG_AMOUNT`, `WRONG_VENDOR`.
- [ ] Total ghost row count matches the Phase-1 fingerprint (`ghost_recipe_total: N`) if `TASK_PHASE1.md` specifies one.
- [ ] No ghost row carries a load-bearing plant value (cross-check with §6 FORBIDDEN_IN_NOISE).

**FAIL trigger 10.a**: A ghost row has no excludability key.
**FAIL trigger 10.b**: A ghost row carries a value that appears in the §6 FORBIDDEN_IN_NOISE list.
**MAJOR_ISSUES**: Total ghost count mismatches the Phase-1 fingerprint.
**MINOR_ISSUES**: A recipe name is outside the canonical set (custom recipe without justification).

---

## 11. Noise-Purity Sweep Audit (Gate G, §6)

Validate §6 Noise-Purity Sweep of `golden_steer_flow.md`.

- [ ] A `FORBIDDEN_IN_NOISE` list is defined containing every load-bearing plant value (numeric, identifier, vendor string).
- [ ] Per-service sweep assertions are enumerated for every active mock service.
- [ ] Every sweep is marked PASS.
- [ ] Every carve-out (a noise/corroboration row allowed to carry a plant value) is explicitly named with the spec section that mandates the corroboration.
- [ ] Cross-reference: every value in §1.1 Authoritative Values appears in `FORBIDDEN_IN_NOISE`.

**FAIL trigger 11.a**: A load-bearing value from §1.1 is missing from `FORBIDDEN_IN_NOISE`.
**FAIL trigger 11.b**: A sweep is marked FAIL or a leak is reported without a carve-out justification.
**MAJOR_ISSUES**: A carve-out has no spec citation.

---

## 12. Distractor File Notes Audit (§7)

Validate §7 Distractor File Notes of `golden_steer_flow.md`.

- [ ] Every declared Distractor API (per `TASK_PHASE1.md` Part D distractor list) has a per-service purity narrative.
- [ ] Each narrative cites the file path and confirms zero plant values in the focal window.
- [ ] Distractor APIs declared have at least one `test_negative_weight_*` test in `test_outputs.py` per `QC_TEST_OUTPUTS_PROMPT.md` cross-cutting check C5.

**FAIL trigger 12.a**: A declared Distractor API has no §7 narrative.
**MAJOR_ISSUES**: A §7 narrative does not name the file path or focal window.

---

## Automatic FAIL Triggers

1. A required fact has no row in §1.1 Authoritative Values (1.a).
2. A row in §1.1 carries a placeholder, ellipsis, `TBD`, or banned vague qualifier on a load-bearing value (1.b).
3. A core authoritative value contradicts its cited carrier (2.2.a).
4. A core authoritative value references a file/row not in the bundle — fabrication (2.2.b).
5. Class label and carrier path disagree (2.2.c).
6. Steer flow is fully producible from `mock_data/` alone, `data/` alone, or persona alone (3.2.a / 3.2.b / 3.2.c).
7. One of the three lenses in §1.3 is missing or empty (3.2.d).
8. A load-bearing value carries a banned vague qualifier or placeholder (4.1.a).
9. A core authoritative value is not ISO-typed (4.1.b).
10. A column header in any cited `mock_data/` file does not match `environment/<slug>-api/<file>` row 1 (5.a).
11. A non-canonical filename is used without an explicit divergence note (5.b).
12. A load-bearing slot has two or more rows carrying the same value in active service files (6.a).
13. Any S11 gate (A–O+) is marked FAIL or missing (7.a) or marked PASS without notes (7.b).
14. An FK reference in §3 is unresolved (8.a) or a mirror value differs across services (8.b).
15. A trap block is missing a required field (9.a) or has a non-single-key disambiguator (9.b) or a red-line trap has no `correct_response` with rule citation (9.c).
16. A ghost row has no excludability key (10.a) or carries a value in `FORBIDDEN_IN_NOISE` (10.b).
17. A `FORBIDDEN_IN_NOISE` list omits a load-bearing value (11.a) or a sweep reports an uncarved leak (11.b).
18. A declared Distractor API has no §7 narrative (12.a).

---

## Verdict

```
IF any FAIL trigger fires       -> FAIL
ELSE IF any MAJOR_ISSUES        -> MAJOR_ISSUES
ELSE IF any MINOR_ISSUES        -> MINOR_ISSUES
ELSE                            -> PASS
```

---

## Output Format

```markdown
# Golden Steer Flow QC Report

**Bundle**: [bundle name]
**Steer flow path**: [path to golden_steer_flow.md]
**Verdict**: [PASS / MINOR_ISSUES / MAJOR_ISSUES / FAIL]

---

## 1. Authoritative Values Coverage
| Ask # | Required Fact | Steer-Flow Row | Class | Concrete Value Present? | Status |
|---|---|---|---|---|---|

**Coverage Summary**: [N/N required facts have rows in §1.1]

---

## 2. Source Carrier Traceability

### Full Carrier Verification Table
| # | Field | Class | Source Carrier | Concrete Value | File Exists? | Row Contains Value? | Class Matches Location? |
|---|---|---|---|---|---|---|---|

### Correctness Summary
- Total rows traced: [N]
- Carriers resolved: [N]
- Mismatches: [N] — [list]
- Fabricated (no carrier): [N] — [list]

---

## 3. Cross-Source Convergence

### Lens Presence
| Lens | Present? | Notes |
|---|---|---|
| Financial analyst | YES/NO | |
| Task-domain expert | YES/NO | |
| Rubric checker | YES/NO | |

### Reachability Flags
- [ ] Producible from `mock_data/` alone? [YES/NO]
- [ ] Producible from `data/` alone? [YES/NO]
- [ ] Producible from persona alone? [YES/NO]
- [ ] Cross-modal JOIN rows present? [YES/NO]

---

## 4. Objectivity & Phrasing

### Phrasing Violations Found
| # | Row / Location | Banned Token | Severity |
|---|---|---|---|

### Two-Evaluator Test Results
[Assessment — which authoritative values pass/fail]

---

## 5. Schema Fidelity

### Header Mismatches
| File | Cited Column | Canonical Column (`environment/<slug>-api/<file>`) | Match? |
|---|---|---|---|

### Non-Canonical Filenames
| Cited Filename | Canonical Filename | Divergence Note Present? |
|---|---|---|

---

## 6. Filler Competition

### Slot Uniqueness Proofs
| Slot | Unique Carrier Row | Variant Ghosts Named | Single-Key Exclusion |
|---|---|---|---|

---

## 7. Gate Report (S11 Gates A–O+)
| Gate | Status | Notes |
|---|---|---|

---

## 8. FK Consistency Proof
| FK | Source | Target | Resolved? | Mirror Match? |
|---|---|---|---|---|

---

## 9. Trap Materialization
| Trap | Required Fields Present | Disambiguator Single-Key? | Failure Category Mapped |
|---|---|---|---|

---

## 10. Ghost Recipe Ledger
| File | Recipe | Rows | Excludability Key | Canonical Recipe? |
|---|---|---|---|---|

**Total Ghost Count**: [N] (Phase-1 fingerprint: [N or N/A])

---

## 11. Noise-Purity Sweep
| Service | Sweep Status | Carve-Outs (with spec citation) |
|---|---|---|

**FORBIDDEN_IN_NOISE coverage**: [N/N §1.1 values listed]

---

## 12. Distractor File Notes
| Distractor API | §7 Narrative Present | File Path Cited | Focal Window Cited |
|---|---|---|---|

---

## Findings Summary
- FAIL: [list or "None"]
- MAJOR: [list or "None"]
- MINOR: [list or "None"]
```
