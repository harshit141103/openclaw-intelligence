# Kensei Task Generator Kit

This is a self-contained kit for generating WildClawBench task folders from any production-ready persona, using a SOTA model like Claude Opus 4.7 / 4.8 or GPT 5.5.

## What is in this kit

```
kensei-task-generator-kit/
├── README.md                              # this file
├── MASTER_GENERATOR_PROMPT.md             # the system prompt you feed to the model
├── mock_api_catalog.md                    # surface map of all 101 mock APIs
├── multimedia_artifacts_index.md          # what the multimedia archive does and does not have
├── reference/                             # authoritative reference docs the prompt cites
│   ├── Hardness_Contract.md
│   ├── Kensei.md
│   ├── hardening_prompt.txt
│   ├── STANDALONE_COMBINED_SYSTEM_PROMPT.md
│   ├── STANDALONE_RUBRICGEN_SYSTEM_PROMPT.md
│   └── STANDALONE_TESTGEN_SYSTEM_PROMPT.md
├── exemplar_task/
│   └── ian_salazar 49a43412-9f86-4e89-aab9-0870a49934/   # reference shape and tone
└── personas/                              # 4 production-ready personas as input examples
    ├── craig-figueroa/
    ├── ben-cox/
    ├── floyd-whitaker/
    └── christopher-morris/
```

## The 30-second mental model

1. You hand a model `MASTER_GENERATOR_PROMPT.md` as the SYSTEM prompt, and a persona folder path as the USER message.
2. The model emits 10 to 14 task folders for that persona, each containing `prompt.txt`, `task.yaml`, `GTFA.txt`, `home/`, `mock_data/`, `persona/` (the 7 .md files), and a `home/_provenance.json` recording where each multimodal artifact came from. The persona's home tree is copied wholesale as baseline; task-specific artifacts are overlaid in the matching macOS subdirs. The persona's mock state is copied wholesale as baseline; task-specific overlay mutations are applied on top.
3. You run the downstream `reference/STANDALONE_COMBINED_SYSTEM_PROMPT.md` over each task folder to auto-generate `rubric.json`, `test_output.py`, and `test_weights.json`.
4. You drop the completed folders into the WildClawBench pipeline.

Each task is single-turn, agentic, multimodal, and tuned so that combined pytest plus LLM-judge pass rate stays strictly below 40 percent (target below 30 percent) on Claude Opus 4.7 / 4.8 and GPT 5.5.

## Read this before your first run (common pitfalls)

These are the mistakes that bite teammates on their first try. The full troubleshooting list is at the bottom of this file; this is the short version.

1. **The multimedia archive is NOT bundled.** The kit ships the 101-API mock environment at `./environment/`, the 4 personas under `personas/`, and the reference docs. The 3.2 GB multimedia archive (docx, pptx, xlsx) lives outside the kit and must be mounted via `--add-dir <path/to/multimedia-artifacts>` in Step 1.
2. **Output folder uses `home/`, per the user brief.** Both the INPUT persona folder AND the OUTPUT task folder use `home/` for the macOS-style tree. This diverges from the reference exemplar (which uses `data/`) and from the downstream STANDALONE generator (which was written for `data/`). When running STANDALONE, the operator either renames `home/` to `data/` on copy OR passes `--add-dir <task>/home` and patches the STANDALONE invocation. The persona's home tree is copied wholesale into the task's home/ as baseline (not curated).
3. **Folder name has a literal SPACE before the UUID.** Format: `<first>_<last> <UUID>`. Not an underscore.
4. **API names carry the `-api` suffix.** In `task.yaml`, use `gmail-api`, not `gmail`. The downstream test generator binds method names to these strings.
5. **3 to 4 required APIs per task, not 5.** The reference exemplar has 5 APIs; the master prompt mandates 3 to 4. The exemplar is a tone reference, not a schema reference.
6. **Stub APIs cannot be required.** `bamboohr-api`, `confluence-api`, `salesforce-api`, `wordpress-api` only respond to `/health`. They are usable as distractors only.
7. **Zero em-dashes in any emitted text file.** Sweep every emitted file with the em-dash and en-dash greps before declaring a task done; both counts must be zero.
8. **No `ai_generated` in `_provenance.json`.** Every artifact's stage must be one of `persona_home`, `multimedia_archive`, `web_scrape`, or `authored_overlay`. Regulator PDFs (APHA, USDA, FMCSA, OSHA, HHS, DOT) must be `web_scrape`, never `authored_overlay`.

## How to run it

### Step 1: Prepare your runtime

You need a model invocation that can:
- Accept large system prompts (this one is roughly 30 KB).
- Read files from disk. The 101-API mock environment is BUNDLED in this kit at `./environment/`, so adding the kit root via `--add-dir` covers it. The multimedia archive (~3.2 GB of docx/pptx/xlsx) lives OUTSIDE the kit; give the model `--add-dir` access to wherever you have it on disk. You also need `--add-dir` access to the persona folder you are generating for.
- Scrape the web for missing multimodal artifacts (give it search and fetch tools, or accept the COPY / WEB_SCRAPE directives the generator emits and fulfil them with your own scraper).

A reference `opencode` invocation looks like this. Adjust paths for your machine.

```bash
opencode \
  --system-prompt /Users/macbookpro/Desktop/Kensei-Knowledge/kensei-task-generator-kit/MASTER_GENERATOR_PROMPT.md \
  --add-dir /Users/macbookpro/Desktop/Kensei-Knowledge/kensei-task-generator-kit \
  --add-dir /Users/macbookpro/Desktop/Kensei-Knowledge/unified-personas/craig-figueroa \
  --add-dir <path/to/multimedia-artifacts> \
  -p "Generate tasks for persona at /Users/macbookpro/Desktop/Kensei-Knowledge/unified-personas/craig-figueroa"
```

You can name multiple personas in the user message; the generator processes them sequentially.

### Step 2: Fulfil COPY and WEB_SCRAPE directives

The generator does not inline binary content. Instead, for every binary multimodal artifact it emits a directive like:

```
<<<COPY: <task_folder>/home/Documents/Calf_Mortality_Review_Winter_2025.docx>>>
FROM: /Users/macbookpro/Desktop/Kensei-Knowledge/unified-personas/craig-figueroa/home/Music/Calf_Mortality_Review_Winter_2025.docx
PROVENANCE: persona_home, copied verbatim
<<<END>>>
```

or

```
<<<COPY: <task_folder>/home/Pictures/clearwater_field_datasheet_2026_12_02.jpg>>>
FROM: WEB_SCRAPE
SOURCE_URL: https://www.usgs.gov/.../field_datasheet_template.pdf
SCRAPE_DATE: 2026-06-10
POST_PROCESS: rendered page 3, handwritten over with synthetic readings, exported as JPG
PROVENANCE: web_scrape
<<<END>>>
```

You (or a small post-processor) fulfil these directives by copying or scraping the files into place. A reference fulfilment loop:

```python
# directive_runner.py (sketch, not a full implementation)
import re, shutil, requests
from pathlib import Path

def run(stream):
    for m in re.finditer(r'<<<COPY: (.*?)>>>(.*?)<<<END>>>', stream, re.DOTALL):
        dest, body = m.group(1), m.group(2)
        # parse FROM, SOURCE_URL, etc and fulfil
        ...
```

We deliberately keep this loop out of the generator's responsibility so the generator can run as a pure text model.

### Step 3: Generate rubric, tests, weights

For each task folder Stage 1 produced, run the bundled wrapper to invoke the STANDALONE prompt and split its output into the three downstream files:

```bash
./run_standalone.sh "<task_folder_path>"
```

The wrapper sits at the kit root. It reads `<task>/task.yaml` to pull the inline `required_apis` and `distractor_apis` lists, invokes `opencode run` with `STANDALONE_COMBINED_SYSTEM_PROMPT.md` attached as the operating instructions, captures the model output, finds the one fenced JSON block STANDALONE emits, and writes:

- `<task>/rubric.json`
- `<task>/test_output.py`
- `<task>/test_weights.json`

A task is only complete after Stage 1 (this generator) plus Stage 2 (this wrapper). A folder missing those three files is incomplete and cannot be benchmarked.

Two CLI mismatches worth knowing about (the wrapper handles both):

- The installed `opencode` CLI in this environment does not expose a `--system-prompt` flag. The wrapper attaches `STANDALONE_COMBINED_SYSTEM_PROMPT.md` as a user-message file and instructs the model to treat it as its operating instructions for the turn.
- STANDALONE's output JSON key is `tests/test_outputs.py` (plural). The exemplar and our tree diagram both use `test_output.py` (singular). pytest collects either. The wrapper writes the singular form and accepts the plural key from STANDALONE's output.

If you need to run STANDALONE manually instead of through the wrapper, the underlying invocation is:

```bash
REQUIRED=$(python3 -c "import yaml; print(', '.join(yaml.safe_load(open('<task_dir>/task.yaml'))['required_apis']))")
DISTRACTOR=$(python3 -c "import yaml; print(', '.join(yaml.safe_load(open('<task_dir>/task.yaml'))['distractor_apis']))")

opencode run \
  --dir "<task_dir>" \
  --file /Users/macbookpro/Desktop/Kensei-Knowledge/kensei-task-generator-kit/reference/STANDALONE_COMBINED_SYSTEM_PROMPT.md \
  --file "<task_dir>/prompt.txt" \
  --file "<task_dir>/task.yaml" \
  --file "<task_dir>/GTFA.txt" \
  "Treat the attached STANDALONE_COMBINED_SYSTEM_PROMPT.md as your complete operating instructions. Read prompt.txt and the task content under <task_dir>. The canonical mock-API source-of-truth lives at /Users/macbookpro/Desktop/Kensei-Knowledge/kensei-task-generator-kit/environment. Required APIs: ${REQUIRED}. Distractor APIs: ${DISTRACTOR}. Emit one fenced JSON block with the three keys STANDALONE specifies."
```

The output is one fenced JSON block with three string-valued keys. Split it into three files at the task root.

### Step 4: Validate

A task is complete only when:
- The folder name follows `<first>_<last> <UUID>` with a literal space.
- The task folder contains `home/`, `mock_data/`, `persona/` at the root (NOT `data/`).
- Every file under `mock_data/<api-name>/` matches a canonical filename in `./environment/<api-name>-api/` (bundled in this kit) and its schema matches `<name>_data.py`.
- `home/_provenance.json` has zero entries with stage `ai_generated`, and carries top-level `persona_home_baseline` and `persona_mock_baseline` notes pointing at the persona source paths copied wholesale.
- The correct answer is nowhere verbatim in `prompt.txt`, any persona `.md`, any data artifact, or any mock_data file.
- The em-dash and en-dash sweeps return zero on every emitted text file.
- The CHANNEL DEPENDENCY MAP in `GTFA.txt` shows every requirement depending on at least two of {prompt, persona, home, mock_data}, with a counterfactual fact loss recorded per used channel.

## Workflow summary

```
persona folder ──▶ MASTER_GENERATOR_PROMPT.md ──▶ N task folders (home/, mock_data/, persona/, prompt.txt, task.yaml, GTFA.txt)
                                                                │
                                                                ▼
                                                    fulfil COPY / WEB_SCRAPE directives (binary artifacts)
                                                                │
                                                                ▼
                                            STANDALONE_COMBINED_SYSTEM_PROMPT.md per folder
                                                                │
                                                                ▼
                                          rubric.json + test_output(s).py + test_weights.json
                                                                │
                                                                ▼
                                                       WildClawBench pipeline
```

## Quality targets (from the master prompt)

- Combined pass rate: below 40 percent on Opus 4.7 / 4.8 and GPT 5.5. Target below 30 percent.
- Tasks per persona: 10 to 14, spread across at least 5 of the 7 Kensei L1 categories.
- Hardness Contract tier: Hard for most tasks; at least 2 tasks per persona at Frontier-defeat.
- Multimodal coverage: every task needs at least one media-dependent core requirement; at least 50 percent of tasks require fusing 2 or more modalities.
- Per-persona coverage minimums (Section 3.1 of the master prompt): >= 3 spend-threshold tasks, >= 2 protected-window tasks, >= 2 drafts-only routing tasks, >= 2 pro-domain refusal tasks where applicable, >= 1 Data Sharing Policy matrix task, >= 1 Not-Connected tool task.

## Things people misread the first time

1. The output folder is named with a SPACE between slug and UUID, not an underscore. Do not collapse it.
2. The output uses `home/`, per the user brief. The INPUT persona folder uses `home/` and the OUTPUT task folder ALSO uses `home/`. This diverges from the reference exemplar (which uses `data/`) and from the downstream STANDALONE generator (which expects `data/`); see the STANDALONE invocation step above for the rename-on-copy or `--add-dir`-and-patch workarounds.
3. The persona's `task/` folder is to be IGNORED. It contains author working notes from a different stage.
4. Stub APIs (`bamboohr-api`, `confluence-api`, `salesforce-api`, `wordpress-api`) only respond to `/health`. They can be used as distractors, never as required APIs.
5. API names in `task.yaml` carry the `-api` suffix (`gmail-api`, not `gmail`), matching the canonical directory naming. The downstream test generator binds method names to these strings.
6. `weights.json` in the exemplar vs `test_weights.json` in newer folders is a known naming drift. The master prompt picks `test_weights.json` to align with the downstream STANDALONE. Similarly `test_output.py` (singular) in the exemplar vs `test_outputs.py` (plural) in STANDALONE; pytest collects either.
7. The exemplar rubric uses 7 fields exactly (`number, criterion, is_positive, type, evaluation_target, importance, score`). Do not add `trap_concept`; the downstream generator forbids it.

## Known frontier-LLM failure modes when running this kit

These are mistakes the master prompt has explicit guards against. If you see one in output, the model has skipped a self-check.

- Model attempts to inline base64 image bytes instead of emitting `<<<COPY:>>>` directives. Reject and re-prompt the offending tasks.
- Model lists 5 required APIs because it copied the reference exemplar verbatim. The rule is 3 to 4. The exemplar's 5-API count is a one-off.
- Model uses em-dashes inside persona-overlay text it appended but not in original text. Sweep all emitted persona files, not just `prompt.txt`.
- Model writes `data/` instead of `home/` in `task.yaml`, in `_provenance.json`, or in COPY / COPY_TREE directive paths. The rule is `home/` for output (per user brief). The reference exemplar uses `data/` and may pattern-match the model into emitting `data/`; resist it.
- Model renders a regulator PDF (APHA, USDA, FMCSA, OSHA, HHS, DOT) from a DOCX template and tags it `authored_overlay`. The rule is `stage: web_scrape` for compliance PDFs; rendered DOCX cannot match issuing-authority artwork and the agent grader will trip.
- Model emits `_provenance.json` with `ai_generated` stage. Hard fail.
- Model treats persona's `task/` folder as input.
- Model writes the correct answer verbatim in a `notes.txt` or a `summary.md` inside `home/`. Hard fail of the no-answer-leak rule.

## Contact and ownership

This kit is independent of any other folder on disk; every file under `kensei-task-generator-kit/` is a copy or original. You can `tar czf kensei-task-generator-kit.tar.gz kensei-task-generator-kit/` and ship it.
