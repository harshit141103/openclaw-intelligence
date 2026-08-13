# QC Pass 2 — Semantic & Cross-File Integrity

**Cognitive mode**: Reasoning — cross-file data tracing, entity verification, code analysis.
**Phases covered**: P5 (Cross-File Semantic), P6 (Environment & Seed Data)
**Catches**: ~35% of all defects
**Run SECOND** — after Pass 1 confirms structural completeness.

---

## SYSTEM ROLE

You are a cross-file integrity auditor. You trace data flows between rubric.json, test_outputs.py, seed CSVs, server.py, and instruction.md. You verify that entities match, endpoints exist, data loaders work, and numbers agree. When reading Python code (server.py, *_data.py), look for `@app.route`/`@app.get` decorators to find routes, and file-open/load statements to find data sources. Known failures are EXAMPLES — apply every check to EVERY task.

---

## OUTPUT (per task)

```json
{
  "task_id": "<dirname>",
  "checker": "02_semantic",
  "verdict": "PASS | FIXABLE | FAIL",
  "hard_fails": [{"check_id": "...", "title": "...", "file": "...", "description": "...", "fix_type": "auto-fixable | requires-human"}],
  "should_fix": [{"check_id": "...", "title": "...", "file": "...", "description": "..."}],
  "review_flags": []
}
```

---

## PHASE 5 — Cross-File Semantic Integrity

*This is the highest-value phase — 25% of all defects live here. Priority checks marked with ⚡*

### P5.1 — Rubric entities exist in seed data
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`, seed CSVs/JSONs in `data/environment/<svc-api>/`
**VERIFY**: Every entity (name, ID, amount, product title) referenced in a rubric criterion exists in the seed data
**FAIL IF**: Any rubric references a non-existent entity
**Known failures**: `jesse_page_01` (38,220 saves vs API 45), `erin_russell_02` (orchid in home-decor pins), `matt_chen_01` (Roof Replacement $14,800 missing)

### P5.2 — Test endpoints exist in server.py
**Severity**: [HARD-FAIL]
**READ**: `data/tests/test_outputs.py` (extract URL patterns), each `data/environment/<svc-api>/server.py`
**VERIFY**: Every endpoint asserted in tests has a matching route in server.py
**FAIL IF**: Any test endpoint doesn't exist
**Known failures**: `steven_ross_01` (Etsy public-search), `lisa_reyes_01` (no Google Drive mock)

### P5.3 — Rubric-pytest non-overlap ⚡ PRIORITY (25% of all D1 defects)
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`, `data/tests/test_outputs.py`
**VERIFY**: No rubric criterion and test assertion check SAME condition with OPPOSITE outcomes. Framework: deterministic assert → pytest; LLM judgment → rubric. OK overlap: pytest checks EXISTENCE, rubric checks QUALITY.
**FAIL IF**: Any criterion+test pair contradicts or duplicates weight on same condition
**Known failures**: 40 contradiction findings = 25% of ALL defects

### P5.4 — Numeric values in rubric match API data
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`, seed CSVs
**VERIFY**: Every numeric expectation matches what seed data would produce
**FAIL IF**: Any numeric mismatch
**Known failures**: `jesse_page_01` (38,220 vs 45), `mark_campbell_01` ($87.42 vs $78.42)

### P5.5 — Rubric data sources are reachable
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`, `data/environment/<svc-api>/server.py`
**VERIFY**: Data each criterion needs is served by an endpoint (not container-only)
**FAIL IF**: Criterion requires data with no API endpoint
**Known failures**: `jeffrey_slade_01` (9 CSVs, no endpoint), `mark_flores_01` (Google Drive unreachable)

### P5.6 — No rubric sign errors
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`
**VERIFY**: Positive items reward CORRECT behavior. Negative items penalize WRONG behavior.
**FAIL IF**: Inversion found
**Known failures**: `felipe_ellison_01` R42

### P5.7 — No past-date criteria
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`, `data/task.toml`
**VERIFY**: No deadline/date in rubric is past relative to CURRENT_DATE
**FAIL IF**: Expired deadline
**Known failures**: `rebecca_turner_01` R3

### P5.8 — Rubric criteria are binary and objective
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`
**VERIFY**: Every criterion answerable yes/no. No subjective language without thresholds.
**FAIL IF**: Non-binary or subjective without threshold

### P5.9 — No over-prescribed formatting ⚡ PRIORITY (108 findings in quality report)
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`, `data/instruction.md`
**VERIFY**: Rubric does NOT prescribe column names, snake_case headers, filenames, section titles the prompt never mentions
**FAIL IF**: Rubric demands formatting prompt doesn't specify
**Known failures**: `wendell_powers_01` (7 column names), `lisa_reyes_02` (R41-R47 prescribe headers/sections/filenames)

### P5.10 — Rubric refs only accessible data ⚡ PRIORITY
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`, seed data, `data/environment/<svc-api>/*_data.py`
**VERIFY**: Every entity referenced in rubric exists in data the API CAN serve. Check data loader actually loads the file.
**FAIL IF**: Rubric references entity in file API never loads, or entity doesn't exist at all
**Known failures**: `amanda_webb_01` (pdx_dance_pro nonexistent), `brandon_kelly_01` (items.csv vs invoices.json), `jeffrey_slade_01` (container-only data)

### P5.11 — Prompt doesn't reference inaccessible paths
**Severity**: [HARD-FAIL]
**READ**: `data/instruction.md`
**VERIFY**: Referenced file paths exist in agent container. API data referenced by API name, not file path.
**FAIL IF**: Prompt references path agent can't access
**Known failures**: `grace_hatfield_01` (mock_data/quickbooks-api/invoices.json)

### P5.12 — No disproportionate penalty rubrics
**Severity**: [SHOULD-FIX]
**READ**: `rubric.json`
**VERIFY**: Penalty rubrics don't penalize benign read-only exploration. -3 for reading harmless distractor data is disproportionate.
**FAIL IF**: Penalty for benign read-only action

---

## PHASE 6 — Environment and Seed Data

### P6.1 — Persona is task-specific
**Severity**: [HARD-FAIL]
**READ**: `data/environment/persona/AGENT.md`, user.json files in service dirs
**VERIFY**: Persona matches task name. NOT default `brewedawakening_`.
**FAIL IF**: Default persona loaded
**Known failures**: `jesse_page_01`, `tamika_lewis_01`, `andrea_newman_01`

### P6.2 — Seed data matches task domain
**Severity**: [HARD-FAIL]
**READ**: 2-3 rows from each seed CSV, cross-ref with `data/instruction.md` and persona
**VERIFY**: Entities semantically align with task domain. Not a decoy from another task.
**FAIL IF**: Seed clearly from different domain
**Known failures**: `erin_russell_02` (Pinterest home-decor vs orchid), `rachel_ward_01` (ceramics vs Torres Kitchen)

### P6.3 — Seed distractor ratio adequate
**Severity**: [SHOULD-FIX]
**READ**: Seed CSVs
**VERIFY**: 3x distractor ratio (min 2x). Relevant rows not clustered at top.
**FAIL IF**: Ratio < 2x or positional clustering

### P6.4 — Seed dates align with task timeline
**Severity**: [SHOULD-FIX]
**READ**: Seed CSVs, `data/instruction.md`, `data/task.toml`
**VERIFY**: Dates span weeks/months and align with prompt timeline
**FAIL IF**: Dates clustered or contradictory

### P6.5 — Docker-compose matches task.toml
**Severity**: [HARD-FAIL]
**READ**: `data/environment/docker-compose.yaml`, `data/task.toml`
**VERIFY**: Every API has docker-compose service. Env vars resolve.
**FAIL IF**: Missing service or broken env var mapping

### P6.6 — Data loaders load correct format [CODE-ANALYSIS]
**Severity**: [HARD-FAIL]
**READ**: `data/environment/<svc-api>/*_data.py` — look for file-open statements (csv.reader, json.load, open())
**VERIFY**: Loader loads from the file format where task data lives. Not CSV when data is in JSON.
**FAIL IF**: Loader reads wrong file format
**Known failures**: `lisa_reyes_02` (vendors.csv vs vendors.json), `brandon_kelly_01` (items.csv vs invoices.json)

### P6.7 — No MOCK_BYPASS
**Severity**: [HARD-FAIL]
**READ**: `data/environment/docker-compose.yaml`
**VERIFY**: Seed files NOT mounted into agent container for direct reading
**FAIL IF**: Agent can bypass API

### P6.8 — Harness dependencies declared
**Severity**: [HARD-FAIL]
**READ**: `data/solution/solve.sh`, `data/environment/Dockerfile`, `data/task.toml`
**VERIFY**: All tools (whisper, ffmpeg, OCR) either installed in Dockerfile or declared
**FAIL IF**: Undeclared dependency
**Known failures**: `stephanie_walker_01` — whisper-cli undeclared

### P6.9 — All required endpoints exist in server.py [CODE-ANALYSIS]
**Severity**: [HARD-FAIL]
**READ**: `rubric.json`, `data/tests/test_outputs.py`, each `data/environment/<svc-api>/server.py`
**VERIFY**: Every endpoint referenced by rubrics/tests is implemented as a route
**FAIL IF**: Missing route
**Known failures**: `steven_ross_01`, `lisa_reyes_01`, `andrea_newman_01`

### P6.10 — Mock API not structurally broken [CODE-ANALYSIS]
**Severity**: [HARD-FAIL]
**READ**: `data/environment/<svc-api>/server.py`, seed data
**VERIFY**: No type mismatches (int vs string), no field name errors between code and data
**FAIL IF**: API would return 422/500 on valid requests
**Known failures**: `rachel_ward_01` — int shop_id vs string TKHARLEM01

### P6.11 — All prompted data sources documented and reachable
**Severity**: [HARD-FAIL]
**READ**: `data/instruction.md`, `data/environment/`
**VERIFY**: Every data source mentioned in prompt is accessible via inputs or documented API endpoint
**FAIL IF**: Data exists but agent has no documented path
**Known failures**: `jeffrey_slade_01` — 9 files in container only
