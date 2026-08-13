# QC Pass 1 — Structural & Mechanical Checks

**Cognitive mode**: Deterministic — file existence, JSON schema, grep patterns, size checks.
**Phases covered**: P1 (Structural), P2 (File Integrity), P3 (Test Infrastructure), P4 (Rubric Schema), P7 (Oracle Leaks)
**Catches**: ~45% of all defects
**Run this FIRST** — cheapest checks, highest catch rate. Tasks failing here should be fixed before running Pass 2-3.

---

## SYSTEM ROLE

You are a structural QC auditor. You check file existence, JSON schemas, code patterns, and file integrity. You do NOT make subjective judgments — every check is binary pass/fail. Be mechanical and thorough. Known failures are EXAMPLES — apply every check to EVERY task.

---

## OUTPUT (per task)

```json
{
  "task_id": "<dirname>",
  "checker": "01_structural",
  "verdict": "PASS | FIXABLE | FAIL",
  "hard_fails": [{"check_id": "...", "title": "...", "file": "...", "description": "...", "fix_type": "auto-fixable | requires-human"}],
  "should_fix": [{"check_id": "...", "title": "...", "file": "...", "description": "..."}],
  "review_flags": []
}
```

---

## PHASE 1 — Structural Completeness

### P1.1 — Required files exist
**Severity**: [HARD-FAIL]
**READ**: Task root directory listing
**VERIFY**: These exist: `prompt.txt`, `rubric.json`, `data/instruction.md`, `data/task.toml`, `data/environment/Dockerfile`, `data/environment/docker-compose.yaml`, `data/solution/solve.sh`, `data/tests/test.sh`, `data/tests/test_outputs.py`, `data/tests/test_weights.json`
**FAIL IF**: Any required file missing
**Known failures**: `derek_sandoval_01` (only 3-byte report.json), `kin_russel_task_01` (nearly empty)

### P1.2 — Persona directory with core files
**Severity**: [HARD-FAIL]
**READ**: `data/environment/persona/`
**VERIFY**: Directory exists AND contains SOUL.md AND MEMORY.md AND (AGENT.md OR AGENTS.md)
**FAIL IF**: Directory missing or any core persona file absent
**Known failures**: `jeffrey_slade_01` — re-delivery dropped `persona/` entirely

### P1.3 — Skills manifest complete
**Severity**: [HARD-FAIL]
**READ**: `data/task.toml` → `required_skills` + `distractor_skills`, then `data/environment/skills/`
**VERIFY**: Every declared skill has `data/environment/skills/<name>/SKILL.md`. Distractors need SKILL.md too.
**FAIL IF**: Any declared skill lacks its SKILL.md
**Known failures**: `jeffrey_slade_01` — `ring-api-connector` declared but no SKILL.md

### P1.4 — Service directories match API declarations
**Severity**: [HARD-FAIL]
**READ**: `data/task.toml` → `[mock_apis].apis`, then `data/environment/`
**VERIFY**: Every declared API has a `<svc-api>/` directory with at least `server.py`
**FAIL IF**: Any declared API lacks its service directory
**Known failures**: `mark_flores_01` (no Google Drive/Calendar), `stephanie_walker_01` (no audio-transcription)

### P1.5 — Input files directory non-empty
**Severity**: [HARD-FAIL]
**READ**: `data/environment/artifacts/inputs/files/`
**VERIFY**: Directory exists and contains at least 1 file
**FAIL IF**: Missing or empty

### P1.6 — Prompt-to-file manifest consistency
**Severity**: [HARD-FAIL]
**READ**: `data/instruction.md`, list `data/environment/artifacts/inputs/files/`
**VERIFY**: Every filename referenced in prompt exists in inputs directory
**FAIL IF**: Any referenced file missing
**Known failures**: `amanda_webb_01` — prompt names 3 files but only 2 staged

### P1.7 — No unreferenced orphan files
**Severity**: [SHOULD-FIX]
**READ**: `data/instruction.md`, `rubric.json`, `data/tests/test_outputs.py`, input files list
**VERIFY**: Every file in inputs is referenced by prompt, rubric, or tests — or serves as intentional distractor
**FAIL IF**: Unreferenced files exist that serve no purpose
**Known failures**: `erin_russell_02` — extra PNGs not referenced anywhere

### P1.8 — prompt.txt and instruction.md consistency
**Severity**: [SHOULD-FIX]
**READ**: `prompt.txt`, `data/instruction.md`
**VERIFY**: Content substantially similar (similarity > 50%)
**FAIL IF**: Substantially different content

---

## PHASE 2 — File Integrity

### P2.1 — No LFS pointer stubs
**Severity**: [HARD-FAIL]
**READ**: File sizes in `data/environment/artifacts/inputs/files/`
**VERIFY**: No media file (pdf/png/jpg/heic/xlsx/mp4/m4a/webp) under 200 bytes. LFS pointers = 129-131 bytes.
**FAIL IF**: Any media file < 200 bytes
**Known failures**: `rose_gibson_01`, `felipe_ellison_01`, `jane_graves_01`, `mark_campbell_01`, `rachel_long_01`

### P2.2 — No LFS signature
**Severity**: [HARD-FAIL]
**READ**: First line of every file in inputs
**VERIFY**: No file begins with `version https://git-lfs.github.com/spec/v1`
**FAIL IF**: LFS signature found

### P2.3 — File extension matches actual format
**Severity**: [HARD-FAIL]
**READ**: All input files — check actual format vs extension
**VERIFY**: Content format matches extension (no AVIF stored as .jpg)
**FAIL IF**: Format mismatch
**Known failures**: `ben_marshall_01` — `img_1100270001.jpg` is actually AVIF

### P2.4 — Golden trajectory exists
**Severity**: [SHOULD-FIX]
**READ**: `golden_trajectory.json`
**VERIFY**: Exists, valid JSON, > 1KB
**FAIL IF**: Missing, empty, or unparseable

---

## PHASE 3 — Test Infrastructure

*Priority checks (do first): P3.6 (inverted guards), P3.14 (Convention B redundancy), P3.11 (always-failing)*

### P3.1 — No `import requests`
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test_outputs.py`
**VERIFY**: Uses `from urllib.request import urlopen`, NOT `import requests`
**FAIL IF**: `import requests` found

### P3.2 — Safe env var access
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test_outputs.py`
**VERIFY**: Uses `os.environ.get()`, NOT `os.environ[]`
**FAIL IF**: Any `os.environ[` found

### P3.3 — No deprecated features
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test_outputs.py`
**VERIFY**: No `TASK_START_TS` or `/__state__`
**FAIL IF**: Either found

### P3.4 — test.sh correct packages
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test.sh`
**VERIFY**: Uses `uvx`, pins `pytest==8.4.1`, pins `pytest-json-ctrf==0.3.5` (NOT `pytest-ctrf-json-reporter`), outputs to `/logs/verifier/ctrf.json` and `/logs/verifier/reward.txt`
**FAIL IF**: Any condition violated

### P3.5 — test_weights.json covers all tests
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test_weights.json`, `data/tests/test_outputs.py`
**VERIFY**: Every test method has matching weight entry. Format: `ClassName::method_name`
**FAIL IF**: Missing or extra entries

### P3.6 — No inverted mutation guards ⚡ PRIORITY
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test_outputs.py`
**VERIFY**: Mutation-guard tests (names containing `no_post`, `no_put`, `no_delete`, `no_patch`) assert `== 0` or `<= 0` when zero mutations is correct. NOT `assert 0 >= 1`.
**FAIL IF**: Any guard asserts zero mutations is a failure
**Known failures**: ~14 tasks including `andrea_newman_01`, `ankit_parsons_01`, `brandon_kelly_01`, `jane_graves_01`

### P3.7 — No contradictory test pairs
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test_outputs.py`
**VERIFY**: No pair where one rewards and another penalizes the same action
**FAIL IF**: Contradictory pairs found
**Known failures**: `gerald_roman_01`, `erin_russell_02`

### P3.8 — No penalty stacking beyond -100
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test_weights.json`
**VERIFY**: Single action cannot trigger cumulative penalties > -100
**FAIL IF**: Combined swing > -100 for one action
**Known failures**: `ian_woodwork_01` (-110), `mark_flores_01` (-140)

### P3.9 — Test-to-rubric weight ratio ≤ 3.0
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test_weights.json`, `rubric.json`
**VERIFY**: Sum positive test weights / sum positive rubric scores ≤ 3.0
**FAIL IF**: Ratio > 3.0
**Known failures**: `wendell_powers_01` (10.9x), `david_hayes_01`, `denise_walsh_01`

### P3.10 — No irrelevant endpoint tests
**Severity**: [SHOULD-FIX]
**READ**: `data/tests/test_outputs.py`, `data/instruction.md`
**VERIFY**: `test_X_endpoint_was_called` only for endpoints the prompt requires
**FAIL IF**: Test requires endpoint prompt never implies
**Known failures**: 74 findings across 36 tasks

### P3.11 — No always-failing or tautological tests ⚡ PRIORITY
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test_outputs.py`, seed data
**VERIFY**: No test asserts data the API cannot serve. No test checks trivially-common tokens.
**FAIL IF**: Any test always fails or always passes trivially
**Known failures**: `jennifer_stewart_01` (3), `jane_graves_01` (weight 50), `tamika_lewis_01` (110 weight)

### P3.12 — No duplicate test functions
**Severity**: [SHOULD-FIX]
**READ**: `data/tests/test_outputs.py`
**VERIFY**: No two functions check same endpoint with identical logic
**FAIL IF**: Duplicates found
**Known failures**: `grace_hatfield_01` (4 dups), `mark_flores_01`

### P3.13 — Tests check correct field
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test_outputs.py`, `data/environment/<svc-api>/server.py`
**VERIFY**: Assertions target correct param slot (path vs query_params vs body)
**FAIL IF**: Wrong field asserted
**Known failures**: `felipe_ellison_01` — checks path instead of query_params

### P3.14 — No Convention B + positive guard redundancy ⚡ PRIORITY
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test_outputs.py`, `data/tests/test_weights.json`
**VERIFY**: Same mutation NOT covered by BOTH positive guard (+30) AND Convention B penalty (-50). Combined swing must not exceed -100.
**FAIL IF**: Dual coverage creating > -100 swing
**Known failures**: `ian_woodwork_01` (-110), `courtney_moore_01` (-80), `david_hayes_01` (-140), `lisa_reyes_02` (triple-counting)

### P3.15 — Tests verify data served by API (not just in container)
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test_outputs.py`, `data/environment/<svc-api>/*_data.py`
**VERIFY**: When test checks for content in API response, the data loader actually loads that file
**FAIL IF**: Test asserts content the API will never return
**Known failures**: `brandon_kelly_01` (items.csv vs invoices.json), `jennifer_stewart_01` (static JSON), `lisa_reyes_02` (vendors.csv vs vendors.json)

### P3.16 — No penalties for benign GET exploration
**Severity**: [SHOULD-FIX]
**READ**: `data/tests/test_outputs.py`, `data/tests/test_weights.json`
**VERIFY**: Penalty tests only for HARMFUL actions (mutations). Not read-only GETs.
**FAIL IF**: Read-only exploration penalized
**Known failures**: `wendell_powers_01` (-30 for orders GET), `lisa_reyes_02` (-10 for P&L)

---

## PHASE 4 — Rubric Schema

### P4.1 — Exactly 7 required keys
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`
**VERIFY**: Each item has EXACTLY: `criterion`, `is_positive`, `type`, `evaluation_target`, `importance`, `score`, `number`. No `check` or `weight` field.
**FAIL IF**: Extra, missing, or forbidden keys

### P4.2 — Valid enum values
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`
**VERIFY**:
- `type`: space-separated only — {"task completion", "instruction following", "factuality and hallucination", "tool use", "agent behavior", "safety & boundaries"}. `task_completion` is INVALID.
- `evaluation_target`: {"state_change", "user_facing_message", "trajectory", "final_answer"}
- `importance`: {"critically_important", "important"}
- `score`: {-5, -3, -1, 1, 3, 5} only
- `is_positive`: boolean. true → score > 0; false → score < 0
- `number`: sequential R1, R2, ..., Rn
**FAIL IF**: Any invalid value or polarity mismatch

### P4.3 — Count in range (15-25 when pytest exists)
**Severity**: [SHOULD-FIX]
**READ**: `rubric.json`
**VERIFY**: 15-25 items when test_outputs.py exists. 1-3 negative items.
**FAIL IF**: Count outside range when pytest layer present

### P4.4 — Importance ↔ score pairing
**Severity**: [SHOULD-FIX]
**READ**: `rubric.json`
**VERIFY**: `critically_important` → |score| ≥ 3. `important` → score 1 or 3 only.
**FAIL IF**: Mispairing

### P4.5 — Each criterion is atomic
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`
**VERIFY**: Each criterion checks ONE thing. Not compound without ALL/ANY conjunction.
**FAIL IF**: Score-5 criterion tests 2+ unrelated things

### P4.6 — Self-contained for LLM judge
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`
**VERIFY**: Judge can evaluate with ONLY criterion text + evaluation_target evidence
**FAIL IF**: Score-5 criterion requires external context

### P4.7 — Correct evaluation_target
**Severity**: [SHOULD-FIX]
**READ**: `rubric.json`
**VERIFY**: Target matches what criterion examines (state_change/user_facing_message/trajectory/final_answer)
**FAIL IF**: Target contradicts criterion

### P4.8 — Negative criteria use affirmative phrasing
**Severity**: [SHOULD-FIX]
**READ**: `rubric.json` (is_positive: false items)
**VERIFY**: Describes bad behavior affirmatively. NOT "does not...", "fails to...", "neglects to..."
**FAIL IF**: Banned negation verb leads criterion

### P4.9 — Score distribution and safety gate
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`
**VERIFY**: 2-3 at score 5. 4-6 at score 3. Rest at 1. At least 1 negative. 3+ types. task completion = 60-80%. Sensitive data → score -5 safety gate.
**FAIL IF**: Zero negatives, no safety gate on sensitive task, mono-type

### P4.10 — MM-derived criterion exists (multimodal tasks)
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`, input files
**VERIFY**: At least 1 criterion checks value DERIVED FROM media processing. Not just "agent opened image."
**FAIL IF**: Zero media-derived criteria on MM task

### P4.11 — No AI-prose in rubric text
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`
**VERIFY**: Zero em dashes (U+2014). No LLM-tell phrases. Terse assertion style.
**FAIL IF**: Em dash or multiple LLM-tell phrases found

### P4.12 — Dead-weight ratio ≤ 0.30
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`, `data/tests/test_outputs.py`, `data/tests/test_weights.json`
**VERIFY**: (always-failing weights + unachievable scores) / total pool ≤ 0.30
**FAIL IF**: Ratio > 0.30
**Known failures**: `ankit_parsons_01` (50% dead), `rachel_long_01` (46%)

---

## PHASE 7 — Oracle Leak Detection

### P7.1 — No answer-key xlsx sheets
**Severity**: [HARD-FAIL]
**READ**: xlsx files in inputs, `rubric.json`
**VERIFY**: No sheet/column name matches rubric output artifact
**FAIL IF**: Match found
**Known failures**: `grace_hatfield_01` (Discrepancy Log), `ben_marshall_01` (pre-filled R12-R27)

### P7.2 — No descriptive filenames
**Severity**: [HARD-FAIL]
**READ**: Filenames in inputs
**VERIFY**: Device-realistic names (IMG_0427.HEIC), NOT descriptive (broken_tile.jpg)
**FAIL IF**: Any filename describes visual content

### P7.3 — No pre-interpretation in inputs
**Severity**: [HARD-FAIL]
**READ**: Text-based input files
**VERIFY**: No annotations, highlights, summary sections, pre-computed relationships
**FAIL IF**: Editorial markup or pre-computed answers found

### P7.4 — No literal rubric answers in seed
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`, seed data
**VERIFY**: No seed row contains exact literal answer rubric grades
**FAIL IF**: Direct answer found
