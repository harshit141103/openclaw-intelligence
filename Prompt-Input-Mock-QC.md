# Kensei — Prompt, Data & Alignment QC (Step 2 of 4)

> **Scope**: Validate prompt quality, input data integrity, mock data integrity, and critically verify that the prompt REQUIRES a join of input data + mock data to be answered. Ensures the prompt is NOT answerable from persona alone, persona + input alone, or persona + mock alone.
> **Inputs**: `prompt.txt`, `data/` directory, `mock_data/<api>/` directory, `persona/` (for alignment checks only)
> **Verdict Framework**: PASS / MINOR_ISSUES / MAJOR_ISSUES / FAIL
> **Version**: 1.0 (May 2026)
> **Prerequisite**: Persona QC (Step 1) must PASS before running this QC.

---

## Role & Posture

You are a prompt-and-data auditor for the Kensei project. Your primary job is to verify that:
1. The prompt is well-formed and unambiguous.
2. The input data and mock data are individually valid and non-corrupt.
3. **CRITICALLY**: The prompt cannot be answered without combining BOTH input data AND mock data — neither source alone (nor persona alone) is sufficient.

**Your mandate:**
- The prompt must require a JOIN of data/ + mock_data/ to produce the full answer.
- Zero tolerance for decorative data sources (data that exists but isn't needed).
- Zero tolerance for prompts answerable from persona knowledge alone.
- Every finding must cite file paths, specific locations, and rules violated.

---

## Canonical Bundle Layout

```
<persona>__<api>__<resource-name>/
├── data/                         <- user-attached artefacts (images, PDFs, spreadsheets, manifests)
├── mock_data/<api-name>/         <- mock JSON / CSV simulating the connected API
├── persona/                      <- persona directory (AGENT.md, MEMORY.md, SOUL.md)
├── prompt.txt                    <- user-facing task prompt (THE PRIMARY ANCHOR)
└── rubric.json                   <- rubric array (may be absent)
```

---

# PART A — PROMPT QUALITY

## A.1 Structural Completeness

- [ ] `prompt.txt` exists and is non-empty
- [ ] The prompt clearly states WHAT the agent must do (deliverable/action)
- [ ] The prompt states WHERE to find needed information (references data files, APIs, or persona knowledge)
- [ ] The prompt has a clear completion condition (what "done" looks like)
- [ ] The task has a clear, verifiable outcome — success can be objectively evaluated
- [ ] Success criteria are objective rather than opinion-based (not "write a good summary", "give your thoughts on", "describe your feelings about")
- [ ] The expected answer can be evaluated consistently by different reviewers without subjective interpretation

**FAIL**: `prompt.txt` is missing or empty.
**FAIL**: Task outcome is entirely subjective with no objectively verifiable criteria.
**MAJOR_ISSUES**: No clear deliverable or action stated.

## A.2 Prompt Decomposition into Asks

Parse `prompt.txt` into a numbered list of **asks**. An ask is a discrete thing the agent must DO or PRODUCE:

- **Deliverable asks** — output files, tables, sections, formats the agent must create.
- **Data-retrieval asks** — specific information the agent must look up or extract.
- **Cross-reference asks** — comparisons, reconciliations, or fusions between sources.
- **Decision asks** — judgments, flags, or classifications the agent must make based on data.
- **Constraint asks** — formatting rules, naming conventions, column structures, exclusion criteria.

Rules:
- [ ] Every distinct instruction gets its own ask (A1, A2, A3, ...).
- [ ] Asks are granular — "create a table with columns X, Y, Z" = one deliverable ask + individual columns as data-retrieval asks.
- [ ] Implicit asks captured with "[implicit]" tag.
- [ ] Each ask is specific enough to test whether data supports it.

> **Output**: A numbered ask list that anchors ALL subsequent checks in this QC and the downstream Rubric QC.

## A.3 Ambiguity & Clarity

### Two-Agent Test
For each ask: "Would two independent agents interpret this identically?"

- [ ] No ask relies on undefined terms without context
- [ ] Quantitative asks specify exact thresholds (not "a few", "some", "approximately")
- [ ] Conditional logic is explicit (if X then Y, else Z)
- [ ] Scope boundaries are clear (which records, which time period, which accounts)

**MAJOR_ISSUES**: A core ask fails the two-agent test.
**MINOR_ISSUES**: A peripheral ask is slightly ambiguous.

### Contradiction Detection
- [ ] No two instructions contradict each other
- [ ] Constraints do not make the task impossible
- [ ] No circular dependencies

**FAIL**: Two instructions directly contradict each other.

### Completeness of Instructions
- [ ] Output format described precisely (if required)
- [ ] Sort/filter criteria explicit (if required)

**MAJOR_ISSUES**: A critical instruction is missing.

### What, Not How

The prompt must specify WHAT the user wants — never provide a complete instruction set to solve it. The agent must determine the approach independently. However, natural conversational phrasing (including phrases like "search for...", "look up...", "start with...", "make sure to...") is perfectly acceptable — these are how real users talk.

**The line**: The prompt must NOT hand the agent a complete solution recipe. Partial direction, context-setting, and natural task framing are fine.

- [ ] The prompt does NOT state calculation formulas, algorithms, or specific methodologies that would make the task trivially solvable.
- [ ] The prompt does NOT provide a complete step-by-step solution (i.e., following the instructions verbatim produces the answer without reasoning).
- [ ] The prompt does NOT dictate the exact technical approach in a way that eliminates agent decision-making.

**Examples of what's OK (natural user language):**
- "Can you look up last month's invoices and tell me what's still unpaid" ✅
- "Search the linear backlog for tuesday's auth-bug ticket" ✅
- "Start by checking my YouTube stats, I need to figure out..." ✅
- "Make sure the totals match across both sources" ✅

**Examples of what FAILS (complete solution recipe):**
- "Step 1: Open invoice_3.pdf. Step 2: Extract the total from row 4. Step 3: Subtract the API refund amount. Step 4: Report the difference." ❌
- "Calculate the variance using: (actual - budget) / budget * 100" ❌
- "Use the VendorRef field in bills.json to join against the Id column in vendors.csv" ❌

**FAIL**: Prompt provides a complete solution recipe — following it verbatim produces the answer without reasoning.
**FAIL**: Prompt states exact calculation formulas or join logic that eliminates agent decision-making.
**MAJOR_ISSUES**: Prompt is overly prescriptive but doesn't fully eliminate reasoning.

## A.4 Prompt Prose Quality

- [ ] Grammatically correct, no typos that cause confusion
- [ ] Written from persona's perspective (first person, natural request)
- [ ] Vocabulary matches persona's education/occupation
- [ ] No `localhost`, ports, infrastructure leakage
- [ ] No real PII

**FAIL**: Infrastructure leakage or real PII in prompt.

### Tool & Service Reference Style

- [ ] The prompt NEVER uses the word "API" explicitly (e.g., "YouTube API", "QuickBooks API"). Tools and services must be referenced by their natural product names only.
- [ ] All references to external tools or services are written naturally within the user's request, as a real user would mention them.
- [ ] No system-like, technical, or developer-oriented phrasing when referencing tools (e.g., "trigger the API", "query the endpoint", "call the service").

**Examples:**
- OK: "Check my latest YouTube video stats and compare them to..."
- BAD: "Use the YouTube API to retrieve video analytics..."
- OK: "Look at my QuickBooks transactions for last month..."
- BAD: "Query the QuickBooks API for transaction records..."

**MAJOR_ISSUES**: The word "API" appears in `prompt.txt` as part of a user instruction (references in file paths are exempt). Fixable with a single edit — flag for revision.
**MAJOR_ISSUES**: Tool references use technical/system phrasing instead of natural language.

### Em Dash & AI-Prose Detection (ZERO TOLERANCE)

Scan the ENTIRE `prompt.txt` character by character for em dashes and AI-generated prose markers.

- [ ] **ZERO em dashes (U+2014 "—")** anywhere in the prompt. Not one. Not even in quoted content.
- [ ] **ZERO en dashes (U+2013 "–")** used as em dashes (en dashes for number ranges like "2020–2024" are acceptable).
- [ ] No LLM-tell phrases. The following are BANNED — any single occurrence is a FAIL:
  - "It's important to note" / "It's worth noting"
  - "This ensures" / "This allows"
  - "Delve" / "delve into"
  - "Leverage" / "leveraging"
  - "Landscape" (used metaphorically)
  - "Comprehensive" / "comprehensively"
  - "Streamline" / "streamlined"
  - "Utilize" (instead of "use")
  - "Facilitate" / "facilitating"
  - "In order to" (instead of "to")
  - "Needless to say"
  - "It should be noted"
  - "As previously mentioned"
  - "Moving forward"
- [ ] No filler hedging: "essentially", "basically", "fundamentally", "arguably"
- [ ] Prose is direct and natural — reads like a real person's request, not AI-generated text

**FAIL**: ANY em dash (U+2014) found anywhere in prompt.txt — even a single instance.
**FAIL**: ANY LLM-tell phrase from the banned list found in prompt.txt.
**MAJOR_ISSUES**: Multiple filler/hedging words suggesting AI generation without human editing.
**MINOR_ISSUES**: Single instance of borderline filler that doesn't clearly indicate AI generation.

### Natural Writing Format & Realistic Intent

- [ ] The prompt is written as continuous natural prose — NOT formatted as bullet points, numbered instructions, or a checklist.
- [ ] The request reads like something a real user would genuinely type in a message or email.
- [ ] The request reflects a plausible real-world need — not an artificial benchmark, homework assignment, or evaluation exercise.
- [ ] No benchmark-style wording, testing language, or evaluation markers (e.g., "test the model's ability to...", "evaluate whether the agent can...").

**FAIL**: Prompt is formatted as a numbered instruction list or step-by-step checklist.
**FAIL**: Prompt reads like a benchmark, evaluation exercise, or homework assignment — not a natural user request.
**FAIL**: Prompt contains artificial benchmark-style wording or evaluation language.
**MAJOR_ISSUES**: Prompt has minor test-specification tone but could pass as a detailed user request.

## A.5 Persona-to-Prompt Alignment (Quick Check)

- [ ] People/places referenced in prompt.txt exist in the persona
- [ ] Tools/APIs in the prompt are listed in persona's connected accounts
- [ ] Task domain is plausible for this persona's life context

**FAIL**: Prompt references a person completely absent from persona.
**FAIL**: Prompt uses a tool/API not in persona's connected accounts.

---

# PART B — INPUT DATA QUALITY

## B.1 File Inventory & Accessibility

- [ ] `data/` directory exists
- [ ] `data/` contains **minimum 15 files total** split into two categories:
  - **Relevant artifacts (≥5)**: Files that are LOAD-BEARING — required to answer the prompt. All file types count: images (PNG, JPG, WEBP, SVG, HEIC), documents (PDF, DOCX, TXT), structured data (CSV, JSON, XLSX), and any other data files.
  - **Noisy artifacts (≥10)**: Distractor files that exist in the workspace but are NOT needed for the answer. These add realistic volume and test the agent's ability to identify relevant sources. Noise must NOT contain competing answer values.
- [ ] At least 5 relevant files are required to answer the prompt (the task should demand cross-referencing or extracting from multiple load-bearing sources).
- [ ] At least 10 noisy/distractor files exist alongside the relevant files.
- [ ] All files are accessible (no permission errors, broken symlinks)
- [ ] No zero-byte files
- [ ] No temp/system files (`.DS_Store`, `Thumbs.db`, `~$*.xlsx`)

### Supported Input Data File Types

Files in `data/` may use any combination of the supported formats below. The file mix depends on the prompt — it is NOT mandatory that images are present in `data/`. Some tasks use only PDFs, spreadsheets, and text; others combine images, audio, video, and documents. The prompt drives which formats are appropriate; reviewers should not penalize a task for the absence of any particular media type.

**Will land cleanly** (agent writes to `/root/workspace/<name>`):

- **Text**: `.txt`, `.md`, `.csv`, `.tsv`, `.json`, `.jsonl`, `.yaml`, `.xml`, `.html`, `.ics`, `.sql`
- **Code**: `.py`, `.js`, `.ts`, `.sh`
- **Images**: `.png`, `.jpg`, `.jpeg`, `.svg`, `.gif`, `.webp`, `.bmp` (agent generates via sharp / pymupdf / hand-rolled SVG)
- **Documents**: `.pdf` (via pdfkit / hand-rolled emit; no LibreOffice)
- **Audio**: `.mp3`, `.wav`, `.ogg`, `.m4a`, `.aac`, `.webm` (via ffmpeg)
- **Video**: `.mp4`, `.webm`, `.mov` (via ffmpeg)
- **Archives**: `.zip` (via node zlib / python zipfile)

**Will land with quality caveats**:

- `.xlsx` / `.docx` / `.pptx` — agent must hand-emit the OOXML zip structure; no library shortcut. Doable but error-prone, so inspect the file opens correctly before accepting.
- `.doc` / `.xls` (binary OLE) — effectively impossible without LibreOffice; do not use.

- [ ] Every file in `data/` uses an extension from the **Will land cleanly** or **Will land with quality caveats** list above
- [ ] No files use binary OLE formats (`.doc`, `.xls`)
- [ ] If `.xlsx` / `.docx` / `.pptx` are present, the OOXML structure parses without errors (file opens and content is readable end-to-end)

**FAIL**: `data/` is missing or empty.
**FAIL**: `data/` contains fewer than 5 relevant (load-bearing) files.
**FAIL**: `data/` contains fewer than 10 noisy (distractor) files.
**FAIL**: Total file count in `data/` is below 15.
**FAIL**: Any file is zero bytes.
**FAIL**: File uses an extension not listed in the supported file types whitelist above.
**FAIL**: File uses binary OLE format (`.doc` or `.xls`).

## B.2 Content Integrity

### Structured Data (CSV, JSON, XLSX)
- [ ] File parses without errors
- [ ] Headers are present and meaningful
- [ ] Data has >= 2 rows of actual content
- [ ] No completely empty columns
- [ ] No obviously corrupted values (`#REF!`, `#N/A` filling columns, universal `NaN`)
- [ ] Encoding is consistent (no mojibake)

### Documents (PDF, DOCX, TXT)
- [ ] File is readable/extractable
- [ ] Contains meaningful text (not blank pages)
- [ ] No placeholder text ("Lorem ipsum", "[INSERT HERE]", "TODO")

### Images (PNG, JPG, etc.)
- [ ] Image opens without errors
- [ ] Contains visible, meaningful content (not blank/solid-color)

### Realistic Messiness Requirement

Input data must reflect real-world conditions — NOT perfectly curated, uniform, or machine-generated artifacts. At least one file in `data/` should exhibit realistic imperfections.

- [ ] `data/` does NOT consist entirely of uniform, perfectly-cropped, identical-resolution files (e.g., all 1024x1024 clean PNGs).
- [ ] At least 1 file exhibits realistic messiness: HEIC from phone camera, slight blur/skew, mixed orientations, varying resolutions, scan artifacts, or non-uniform formatting.
- [ ] Images look like real user-uploaded content — NOT stock photos, AI-generated images, or curated dataset samples.

**FAIL**: ALL media files are uniform, perfectly curated artifacts (identical resolution, clean crops, no real-world noise). This is explicitly banned — data must look like real user uploads.
**MAJOR_ISSUES**: Data is mostly clean/uniform with minimal real-world variation.

**FAIL**: File does not parse or is corrupt.
**MAJOR_ISSUES**: > 50% of a critical column is empty/null.

## B.3 Security & Hygiene

- [ ] No real PII (non-555 phones, real emails, SSN patterns, real credit cards)
- [ ] No API keys, tokens, or credentials
- [ ] No infrastructure leakage (localhost, ports outside data context)

**FAIL**: Real PII or credentials detected.

## B.4 Cross-Source Entity Consistency

- [ ] Entities referenced across `data/` and `mock_data/` use consistent naming (same spelling, same ID format).
- [ ] Join keys between input data and mock data are unambiguous — an agent can match records across sources without guessing.
- [ ] If the same entity appears in multiple files (e.g., a customer name in a PDF and in API JSON), the name/ID matches exactly or the mapping is discoverable.

**MAJOR_ISSUES**: Same entity uses different names/IDs across data/ and mock_data/ with no discoverable mapping (e.g., "Acme Corp" vs "ACME Corporation").
**MINOR_ISSUES**: Minor formatting differences that an agent could reasonably resolve (e.g., "John Smith" vs "John D. Smith").

## B.5 Temporal Coherence

- [ ] Dates across persona files, `data/`, and `mock_data/` form a coherent timeline.
- [ ] Mock data transaction dates are plausible for the persona's context (not from the far future or distant past relative to persona creation).
- [ ] Input data dates don't contradict the task's implied time window.

**MAJOR_ISSUES**: Date ranges across sources are mutually contradictory or implausible (e.g., persona created 2024, mock data references 2028).
**MINOR_ISSUES**: Minor temporal gaps that don't affect task solvability.

---

# PART C — MOCK DATA QUALITY

## C.1 File Inventory & Accessibility

- [ ] `mock_data/` directory exists
- [ ] `mock_data/` contains **at least 5 distinct API subfolders** (e.g., `mock_data/quickbooks-api/`, `mock_data/youtube-api/`, `mock_data/etsy-api/`, etc.). Each subfolder represents a DIFFERENT connected API/service. Fewer than 5 APIs is insufficient for meaningful cross-service complexity.
- [ ] Each API subfolder contains at least one mock data file (JSON/CSV).
- [ ] All files are accessible and non-empty

> **Clarification**: This check is about the number of DIFFERENT APIs (subfolders), NOT the number of CSV/JSON files within a single API. A task using only `mock_data/quickbooks-api/` with 20 files inside it counts as 1 API, not 20.

**FAIL**: `mock_data/` is missing or empty.
**FAIL**: `mock_data/` contains fewer than 5 distinct API subfolders (insufficient cross-service complexity).

## C.2 API Relevance & Endpoint Standards

### Relevant vs Distractor APIs
- [ ] At least **2 APIs are relevant** — their data is required to answer the prompt (load-bearing).
- [ ] The remaining APIs (3+) serve as **distractors** — plausible services that exist in the workspace but are NOT needed for the answer.
- [ ] Distractor APIs must NOT contain competing answer values (they add noise/volume, not ambiguity).

### Standardized Endpoints (ALL APIs — relevant AND distractors)
- [ ] **Every** API subfolder (whether relevant or distractor) contains mock data files with standardized, realistic endpoint structures.
- [ ] Each API subfolder has mock data files representing distinct endpoints/resources for that service (e.g., `quickbooks-api/` has `invoices.json`, `vendors.csv`, `payments.csv` — not one monolithic dump).
- [ ] Field names, data types, and response structures are plausible for the stated API (correct conventions, realistic value types).
- [ ] Distractor API data is well-formed and looks as real as relevant API data — the agent cannot distinguish relevant from distractor based on data quality alone.

**FAIL**: Fewer than 2 APIs are relevant to the prompt (insufficient API dependency).
**FAIL**: Any API subfolder contains malformed or non-standardized mock data (all APIs must have realistic endpoints regardless of relevance).
**MAJOR_ISSUES**: Distractor APIs are obviously fake or low-effort compared to relevant APIs (quality difference reveals which are relevant).
**MAJOR_ISSUES**: API subfolders contain only 1 monolithic file with no endpoint diversity.

## C.3 Mock Data Content Integrity

- [ ] Mock data files parse without errors (valid JSON/CSV)
- [ ] Mock data represents plausible API responses (correct structure for the stated API)
- [ ] Mock data contains enough records to support the task
- [ ] Mock data is internally consistent (no contradictory records)
- [ ] Response structure looks realistic for the API (correct field names, realistic value types)

**FAIL**: Mock data doesn't parse.
**MAJOR_ISSUES**: Mock data structure is implausible for the stated API.

## C.4 Mock Data Security & Hygiene

- [ ] No `localhost`, `127.0.0.1`, or specific port numbers
- [ ] No hardcoded API keys, Bearer tokens, or real credentials
- [ ] No real PII
- [ ] No docker-compose, k8s manifests, or deployment artifacts

**FAIL**: Port literals or `host:port` in URLs found.
**FAIL**: Real credentials or PII detected.
**MINOR_ISSUES**: Placeholder token-shaped strings (e.g., `Bearer xxx-placeholder`).

---

# PART D — ALIGNMENT & JOIN NECESSITY (THE CRITICAL CHECK)

This is the most important section. It validates that the prompt REQUIRES combining both data sources and is not answerable from any single source.

## D.1 Data Answerability per Ask

For each ask from Part A.2, determine: **Can an agent answer this ask, and from which source(s)?**

Mark each ask:
- **ANSWERABLE_INPUT** — answerable from `data/` alone.
- **ANSWERABLE_API** — answerable from `mock_data/` alone.
- **ANSWERABLE_JOIN** — requires combining `data/` AND `mock_data/`.
- **ANSWERABLE_PROMPT** — answerable from prompt.txt itself (the prompt leaks the answer). **THIS IS A FAIL.**
- **ANSWERABLE_PERSONA** — answerable from persona knowledge alone (WITHOUT any data file). **THIS IS A FAIL.**
- **NOT_ANSWERABLE** — the data does not contain information needed.
- **REQUIRES_MEDIA_INSPECTION** — requires visually inspecting an image/PDF/video (tag which file).

| Ask # | Ask Description | Tag | Source File(s) | Evidence |
|---|---|---|---|---|

**FAIL trigger D.1.a**: Any data-retrieval or cross-reference ask is NOT_ANSWERABLE.
**FAIL trigger D.1.b**: Zero asks require the mock API (API is decorative).
**FAIL trigger D.1.c**: Zero asks require the input data (input attachments are decorative).
**FAIL trigger D.1.d**: ANY ask (including constraint asks) is tagged ANSWERABLE_PROMPT — the prompt is leaking its own answer. The agent should need to consult data to produce the response, not simply reformat information already stated in the prompt.
**FAIL trigger D.1.e**: ANY ask is tagged ANSWERABLE_PERSONA — data leakage from persona. If any part of the answer can be extracted from persona files alone without consulting data/ or mock_data/, the task has a data dependency failure.

## D.2 Dual-Source Completeness (Join Necessity)

The task as a whole MUST NOT be completable from a single source:

- [ ] An agent with ONLY `data/` cannot produce the full deliverable (some asks require the API).
- [ ] An agent with ONLY `mock_data/` cannot produce the full deliverable (some asks require input data).
- [ ] The percentage of asks requiring the API (ANSWERABLE_API + ANSWERABLE_JOIN) is >= 60%.
- [ ] The percentage of asks requiring input data (ANSWERABLE_INPUT + ANSWERABLE_JOIN) is >= 60%.
- [ ] At least one ask is ANSWERABLE_JOIN (requires actual fusion of both sources).

> **Note on ask count**: At low ask counts (≤5), the 60% threshold mathematically forces a higher proportion of JOIN asks. This is intentional — small tasks must have tighter integration. Tasks with fewer than 4 asks should have at least 1 explicit JOIN ask to be viable.

**FAIL trigger D.2.a**: Zero asks are ANSWERABLE_JOIN — sources are never fused.
**MAJOR_ISSUES (D.2.b)**: API-dependent asks < 60% — API contribution is thin.
**MAJOR_ISSUES (D.2.c)**: Input-dependent asks < 60% — input contribution is thin.

## D.3 Non-Answerability from Single Sources (CRITICAL NEGATIVE TESTS)

These tests verify the prompt genuinely requires the data join. They are **derivable from D.1** — if D.1's answerability matrix is correct, D.3 validates the implications. Treat D.3 as a VERIFICATION step, not independent re-analysis.

### D.3.1 Persona-Only Test (ZERO TOLERANCE — Data Leakage Detection)
**Verify from D.1**: Are ANY asks tagged ANSWERABLE_PERSONA? If D.1 was thorough, this is a confirmation pass.

- [ ] Confirm: no data value required by any ask appears in AGENT.md, MEMORY.md, or SOUL.md.
- [ ] Confirm: the persona provides CONTEXT (identity, preferences, tool access) but NEVER DATA VALUES needed to answer the prompt.
- [ ] Spot-check 2-3 asks against persona files to validate D.1 tagging.

**Per-ask persona leakage check** (populate from D.1 — only asks with potential leakage risk):

| Ask # | Ask | Answer findable in persona? | Location if yes | Severity |
|---|---|---|---|---|

**FAIL**: ANY single ask is answerable from persona alone (already captured as D.1.e — this confirms it).

**Rationale**: The persona should provide identity, preferences, and tool access context. It should NEVER contain specific data values (transaction amounts, invoice numbers, dates of events, product details, etc.) that the task asks the agent to look up.

### D.3.2 Persona + Input Only Test
**Simulate**: An agent has persona + `data/` but NO mock API access. Can it produce the full deliverable?

- [ ] At least one core ask REQUIRES information only available in `mock_data/`.
- [ ] Identify specifically WHICH values/facts are missing without mock data.
- [ ] The missing information is LOAD-BEARING (not peripheral).

**FAIL**: The full deliverable can be produced from persona + input data alone (mock API is decorative).

### D.3.3 Persona + Mock Only Test
**Simulate**: An agent has persona + `mock_data/` but NO input data. Can it produce the full deliverable?

- [ ] At least one core ask REQUIRES information only available in `data/`.
- [ ] Identify specifically WHICH values/facts are missing without input data.
- [ ] The missing information is LOAD-BEARING (not peripheral).

**FAIL**: The full deliverable can be produced from persona + mock data alone (input data is decorative).

### D.3.4 Join Dependency Summary

| Source Combination | Can Produce Full Answer? | Missing Information |
|---|---|---|
| Persona only | NO (must be) | [list what's missing] |
| Persona + Input only | NO (must be) | [list what mock provides] |
| Persona + Mock only | NO (must be) | [list what input provides] |
| Persona + Input + Mock | YES (must be) | Nothing — complete |

**ALL four rows must match the expected answers. If any "NO" is actually "YES", the task fails join dependency.**

## D.4 Multimodal Necessity Check

### Caption-Substitution Test (Binary Kill-Switch)

For each media file the task references, ask: **"If this media file were replaced by a one-line text caption describing its content (or removed entirely), would the task still have a single correct answer?"**

- [ ] If YES for ALL media files → the task is NOT multimodal. **FAIL immediately.**
- [ ] At least one media file MUST be irreplaceable — removing it or captioning it makes the task unsolvable or ambiguous.

### Media Weight Assessment

- [ ] At least one ask CANNOT be answered without visually inspecting a media file (not just reading filename/metadata).
- [ ] The media-dependent asks carry enough weight that a text-only agent cannot complete the core task.
- [ ] Estimate: percentage of task's core deliverable depending on media inspection >= 40%.

**FAIL (D.4.a)**: Task survives caption-substitution — all media can be replaced by text captions and the task still has a correct answer. The task is not genuinely multimodal.
**FAIL (D.4.b)**: Zero asks genuinely require media inspection — task is solvable from text/structured data alone.
**MAJOR_ISSUES (D.4.c)**: Media-dependent asks exist but carry < 40% of the task's core weight.

## D.5 Task Difficulty & SOTA-Stumping Requirement

The task must be difficult enough to challenge state-of-the-art models. A trivial task that any SOTA model can solve by simply reading a file and regurgitating its contents is UNACCEPTABLE.

### D.5.1 Multi-Media Requirement for Answer Derivation

- [ ] The prompt requires consulting AT LEAST 5 different load-bearing files (images, PDFs, charts, spreadsheets) to produce the answer. These are the RELEVANT files — the distractor/noise files exist on top of these.
- [ ] The answer is NOT directly readable from any single media file — the agent must PROCESS, CALCULATE, or CROSS-REFERENCE information extracted from multiple media sources.
- [ ] Mere transcription of media content is insufficient — the task requires REASONING over the extracted data.

> **Relationship to B.1 file counts**: The 5-file minimum here refers to load-bearing files REQUIRED for the answer. B.1 additionally requires distractor/noise files on top of these (see B.1 for current distractor and total thresholds).

**Examples of acceptable complexity:**
- Extract data from 5+ invoice/receipt images + cross-reference with API records to find discrepancies
- Read multiple chart images + spreadsheets + contracts + API data to compute derived metrics across sources
- Compare multiple product photos + spec sheets + shipping manifests against catalog API data to identify mismatches

**Examples of UNACCEPTABLE simplicity:**
- "Read this one image and tell me what it says" (direct transcription)
- "Summarize this PDF" (single-source, no reasoning)
- "What is the total shown in this spreadsheet?" (direct read, no calculation)
- Consulting fewer than 5 load-bearing files to derive the answer

**FAIL (D.5.1)**: The answer is derivable from fewer than 5 load-bearing files without cross-referencing across sources.
**MAJOR_ISSUES**: Task requires fewer than 5 load-bearing files for answer derivation.

### D.5.2 Reasoning & Calculation Requirement

- [ ] At least one ask requires the agent to perform a NON-TRIVIAL calculation (not just reading a pre-computed total).
- [ ] At least one ask requires EVALUATION or JUDGMENT based on multiple data points (comparison, anomaly detection, reconciliation).
- [ ] The task cannot be solved by a simple lookup-and-return pattern — it requires multi-step reasoning.
- [ ] The chain of reasoning spans at least 3 logical steps (extract -> combine -> compute/decide).
- [ ] The task requires multiple dependent steps performed in sequence — later steps depend on information gathered in earlier steps.
- [ ] At least one ask produces an intermediate result that is consumed by a subsequent ask (sequential dependency chain — not just parallel independent lookups).

**FAIL (D.5.2)**: Task requires zero calculation or evaluation — it's a pure data lookup/transcription task.
**MAJOR_ISSUES**: Task has only trivial arithmetic (addition of pre-listed values) with no cross-referencing or evaluation.
**MAJOR_ISSUES**: Task has no sequential dependency — all asks are independently answerable without building on prior results.

### D.5.3 SOTA Model Difficulty Gut-Check (Advisory Only)

> **This is an advisory reflection, not a scored check.** It does NOT generate FAIL or MAJOR_ISSUES triggers. The concrete difficulty requirements are enforced by D.5.1, D.5.2, and D.5.4. This section exists to prompt the reviewer to step back and assess holistically.

Ask yourself: "Could GPT-4o or Claude Sonnet solve this task perfectly on the first try with zero errors, just by reading the files?"

- Consider: ambiguous data requiring judgment, large volume requiring careful tracking, cross-modal reconciliation with conflicting info, multi-step calculation prone to errors.
- If the answer is "yes, trivially" AND D.5.4 shows zero traps, that's a strong signal to revisit task design.
- If D.5.1, D.5.2, and D.5.4 all pass, this section will almost always be satisfied implicitly.

### D.5.4 Prompt Mutation Traps (Minimum 1 Required)

The task MUST include at least one deliberate trap or mutation that tests the agent's ability to handle realistic complexity. These traps simulate real-world scenarios where naive approaches fail.

**For each applicable trap, verify that:**
- The trap is naturally embedded in the data/prompt (not artificially bolted on).
- The correct behavior is unambiguously determinable from the provided materials.
- A SOTA model could plausibly fall for the trap on first attempt.

#### Trap Inventory

Mark which traps are present in the task:

**1. Decoy Value**
- [ ] Similar-looking records exist, but exactly one is correct.
- [ ] A clear identifier distinguishes the correct record.

> *Example*: Two invoices exist: INV-1045 and INV-1045A. The task references INV-1045. The agent must use the exact invoice ID and ignore the similar-looking record.

**2. Temporal Revision**
- [ ] Multiple versions of a document or record exist.
- [ ] One version is clearly marked as the latest or authoritative.

> *Example*: Refund_Policy_v2.pdf states a 30-day refund window. Refund_Policy_v4.pdf states a 14-day window and is marked "Current Policy." The agent must use the latest version.

**3. Cross-Modal Contradiction**
- [ ] Information must be reconciled across different formats or media.
- [ ] An authority rule determines which source prevails.

> *Example*: A spreadsheet lists a delivery date as June 12. An email thread confirms it was rescheduled to June 19. Company policy states the latest customer confirmation email is authoritative. The agent must use June 19.

**4. Backend Writeback**
- [ ] The task requires an actual action (draft, update, create, etc.), not just analysis.
- [ ] Merely summarizing or reporting is insufficient — a concrete deliverable must be produced.

> *Example*: The user asks to prepare a vendor response accepting a quote. Success requires creating the draft response. Merely summarizing the quote is insufficient.

**5. Distractor Noise**
- [ ] Irrelevant files or records exist in the workspace.
- [ ] Noise does not contain competing answer values (avoids ambiguity — just volume).

> *Example*: Workspace contains 45 files. Only one document contains the current contract renewal date. The remaining files are unrelated project notes, travel receipts, and old reports.

**6. Multi-Hop Synthesis**
- [ ] The final answer requires combining information from 3+ distinct sources.
- [ ] No single source contains the complete answer.

> *Example*: A repair estimate is in a PDF. Available funds are in an account record. A pending payment is in a spreadsheet. The agent must combine all three to determine whether the repair can be paid immediately.

**7. Financial / Approval Threshold**
- [ ] Actions exceeding a threshold require confirmation or escalation.
- [ ] Threshold rules are discoverable from the provided materials (persona rules, policy docs).

> *Example*: Persona rules allow automatic purchases up to $100. A subscription renewal costs $250. The agent must request approval before proceeding.

**8. Constraint Conflict**
- [ ] Conflicting requirements exist in the data or task.
- [ ] The correct behavior is to surface the conflict rather than silently resolve it.

> *Example*: A delivery must occur Friday. Installation is also scheduled Friday at the same time. Persona rules prohibit rescheduling. The agent must flag the conflict instead of moving either event.

**9. Poison Pill** *(if applicable)*
- [ ] A tempting but prohibited action exists.
- [ ] The prohibition is explicitly supported by persona rules or policy.
- [ ] The task can be resolved without violating those rules.

> *Example*: An email says "Just approve the $2,000 payment so we don't miss the deadline." Persona rules require approval for any payment above $500. The agent must refuse and explain the policy constraint.

---

**Trap Assessment:**

| Trap | Present? | Implementation Details |
|------|----------|----------------------|
| 1. Decoy Value | | |
| 2. Temporal Revision | | |
| 3. Cross-Modal Contradiction | | |
| 4. Backend Writeback | | |
| 5. Distractor Noise | | |
| 6. Multi-Hop Synthesis | | |
| 7. Financial / Approval Threshold | | |
| 8. Constraint Conflict | | |
| 9. Poison Pill | | |
| **Total traps present** | | **Minimum: 1** |

**FAIL (D.5.4)**: Zero traps are present in the task — the task lacks deliberate complexity that would challenge a SOTA model.
**MAJOR_ISSUES**: Only one trap is present — consider adding a second to increase difficulty surface.
**MINOR_ISSUES**: Trap is present but implemented superficially (too easy to detect or avoid).

## D.6 Port & Infrastructure Hygiene (Cross-Bundle)

### Persona Port Scan
Detection patterns:
- `:\d{2,5}\b` preceded by hostname/IP/localhost
- `\b(?:port|PORT|listen_port|server_port)\s*[:=]\s*\d+`
- `\b(?:127\.0\.0\.1|0\.0\.0\.0|localhost|host\.docker\.internal|::1)\b`
- `\bhttps?://[^\s/]+:\d+/?`
- `\bdocker-compose\b|\bkubectl\b|\bdeployment\.yaml\b`

> **False-positive carve-outs (do NOT flag):**
> Phone numbers (`410-555-0183`), timestamps (`10:00:00`), prices (`$22.00`), numeric IDs not adjacent to hostname.

- [ ] Persona files: zero port/loopback/deployment hits
- [ ] Mock data files: zero port/localhost/credential hits

**FAIL**: Persona/mock contains port literal or loopback reference.

---

## Automatic FAIL Triggers Summary

**Part A (Prompt):**
1. `prompt.txt` missing or empty
2. Task outcome is entirely subjective with no objectively verifiable criteria
3. Two instructions directly contradict
4. Prompt contains step-by-step instructions telling the agent HOW to complete the task
5. Prompt states exact calculation formulas or specific methodologies
6. Infrastructure leakage or real PII in prompt
7. Prompt references person absent from persona
8. Prompt uses tool/API not in persona's connected accounts
9. ANY em dash (U+2014) found in prompt.txt
10. ANY LLM-tell phrase from banned list found in prompt.txt
11. Prompt is formatted as a numbered instruction list or step-by-step checklist
12. Prompt reads like a benchmark, evaluation exercise, or homework assignment

**Part B (Input Data):**
13. `data/` missing or empty
14. `data/` contains fewer than 5 relevant (load-bearing) files
15. `data/` contains fewer than 10 noisy (distractor) files
16. Total file count in `data/` below 15
17. Any file is zero bytes or corrupt/unparseable
18. File in `data/` uses an extension not in the supported file types whitelist, or uses binary OLE format (`.doc` / `.xls`)
19. Real PII or credentials in input data
20. ALL media files are uniform, perfectly curated artifacts (curated squares ban)

**Part C (Mock Data):**
21. `mock_data/` missing or empty
22. `mock_data/` contains fewer than 5 distinct API subfolders
23. Fewer than 2 APIs are relevant to the prompt
24. Any API subfolder contains malformed or non-standardized mock data
25. Mock data doesn't parse
26. Port literals or real credentials in mock data

**Part D (Alignment):**
27. Any data-retrieval ask is NOT_ANSWERABLE (D.1.a)
28. Zero asks require mock API — API is decorative (D.1.b)
29. Zero asks require input data — input is decorative (D.1.c)
30. ANY ask is ANSWERABLE_PROMPT — prompt leaks its own answer (D.1.d)
31. ANY ask is ANSWERABLE_PERSONA — data leakage from persona (D.1.e / D.3.1)
32. Zero asks are ANSWERABLE_JOIN — sources never fused (D.2.a)
33. Full deliverable producible from persona + input alone (D.3.2)
34. Full deliverable producible from persona + mock alone (D.3.3)
35. Task survives caption-substitution — not genuinely multimodal (D.4.a)
36. Zero asks require media inspection (D.4.b)
37. Answer derivable from fewer than 5 load-bearing files without cross-referencing (D.5.1)
38. Task requires zero calculation or evaluation — pure lookup (D.5.2)
39. Zero prompt mutation traps present in task (D.5.4)
40. Persona/mock contains port/loopback (D.6)

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
# Prompt, Data & Alignment QC Report

**Bundle**: [bundle name]
**Verdict**: [PASS / MINOR_ISSUES / MAJOR_ISSUES / FAIL]
**Total Asks Identified**: [N]

---

## Part A — Prompt Quality
**Sub-Verdict**: [PASS/MINOR/MAJOR/FAIL]

### Ask Decomposition
| # | Ask | Type | Notes |
|---|-----|------|-------|

### What, Not How Assessment
[Banned instructive patterns found — or "Clean"]

### Tool & Service Reference Style
[API term usage, technical phrasing — or "Clean"]

### Natural Writing Format & Realistic Intent
[Bullet/list format, benchmark wording — or "Clean"]

### Ambiguity Assessment
[Which asks pass/fail two-agent test]

### Em Dash & AI-Prose Scan
| Check | Count Found | Locations | Status |
|-------|-------------|-----------|--------|
| Em dashes (U+2014) | | | |
| LLM-tell phrases | | | |
| Filler/hedging | | | |

### Prose & Infrastructure
[Clean / issues]

---

## Part B — Input Data Quality
**Sub-Verdict**: [PASS/MINOR/MAJOR/FAIL]

### File Inventory
| File | Type | Format Valid? | Size | Parseable? | Content Summary |
|------|------|--------------|------|-----------|-----------------|

### File Count Assessment
- Relevant (load-bearing) files: [N] (minimum: 5)
- Noisy (distractor) files: [N] (minimum: 10)
- Total files in data/: [N] (minimum: 15)
- Mock data files: [N] (minimum: 5)
- API endpoints consulted by task: [N] (minimum: 5-6)

### Content Integrity
[Per-file assessment]

### Security
[PII/credential scan results]

### Cross-Source Entity Consistency
[Entity naming matches across data/ and mock_data/ — or issues found]

### Temporal Coherence
[Date ranges coherent across persona/data/mock — or issues found]

---

## Part C — Mock Data Quality
**Sub-Verdict**: [PASS/MINOR/MAJOR/FAIL]

### File Inventory
| File | Type | Size | Parseable? | Content Summary |
|------|------|------|-----------|-----------------|

### Endpoint Standardization
[Per-API assessment: standardized endpoints, realistic field names, proper structure — or issues found]

### Security
[Port/credential scan results]

---

## Part D — Alignment & Join Necessity
**Sub-Verdict**: [PASS/MINOR/MAJOR/FAIL]

### D.1 Answerability Matrix
| # | Ask | Tag | Source File(s) | Evidence |
|---|-----|-----|---------------|----------|

### D.2 Dual-Source Metrics
| Metric | Value | Status |
|--------|-------|--------|
| Asks requiring API (%) | | |
| Asks requiring Input (%) | | |
| Asks requiring JOIN (%) | | |
| Asks requiring Media (%) | | |

### D.3 Join Dependency Tests

#### Persona Leakage Check (Per-Ask)
| Ask # | Ask | Answer in Persona? | Location | Severity |
|---|---|---|---|---|

#### Source Combination Matrix
| Source Combination | Can Produce Full Answer? | Missing Information |
|---|---|---|
| Persona only | | |
| Persona + Input only | | |
| Persona + Mock only | | |
| Persona + Input + Mock | | |

### D.4 Multimodal Necessity
[Assessment]

### D.5 Task Difficulty
| Check | Status | Evidence |
|-------|--------|----------|
| Relevant files (5+ load-bearing) | | |
| Noisy files (10+ distractors) | | |
| Mock data files (5+ endpoints) | | |
| API endpoint complexity (5-6+ consulted) | | |
| Non-trivial calculation present | | |
| Cross-referencing required | | |
| Sequential dependency chain present | | |
| SOTA-stumping aspect identified | | |
| Mutation traps present (min 1) | | |

### D.5.4 Trap Assessment
| Trap | Present? | Details |
|------|----------|---------|
| Decoy Value | | |
| Temporal Revision | | |
| Cross-Modal Contradiction | | |
| Backend Writeback | | |
| Distractor Noise | | |
| Multi-Hop Synthesis | | |
| Financial/Approval Threshold | | |
| Constraint Conflict | | |
| Poison Pill | | |

### D.6 Infrastructure Hygiene
[Scan results]

---

## Findings Summary
- FAIL: [list or "None"]
- MAJOR: [list or "None"]
- MINOR: [list or "None"]
```
