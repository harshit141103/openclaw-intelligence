# Kensei Task Generation Pipeline

How to turn ONE persona into a complete, hard-but-fair agent-evaluation task, end to end.

The pipeline produces a drop-in task bundle: an instruction, a mock environment (mock API data + attached artifacts), deterministic + LLM-judged graders, and a golden answer key.

## Stages at a glance

```
Persona (SOUL.md, AGENTS.md, MEMORY.md)
   |
   v  [Prompt 1: Task Architect]
prompt.txt  +  artifacts_description.txt  +  mock_data_description.md
   |
   v  [Source the artifacts]
artifacts/  (real files: PDFs, images, .docx, .xlsx, ...)
   |
   v  [Prompt 2: Mock Data Generator]
mock_data/{slug}-api/ tree  +  golden_steer_flow.md
   |
   v  [Prompt 3: task.yaml from golden_steer_flow.md and task data]
task.py  (+ task README, optional inject/mutations.json)
   |
   v  [Rubrics & PY Generator: run.py]
tests/test_outputs.py  +  tests/rubric.json
   |
   v  [QC]            ->   [Create input bundle]   ->   [Push to GitHub]
```

## Prerequisites

- The three pipeline tools (in this repo):
  - `prompt-1-task-architect-v5.md`  (Phase 1 system prompt)
  - `prompt-2-mock-data-generator-v5.md`  (Phase 2 system prompt)
  - `Rubrics and PY Generator/`  (the rubric + pytest toolkit; `run.py`)
- `python3` with `python-docx`, `openpyxl`, and `fpdf2` (for sourcing Office and PDF artifacts).
- A persona folder containing at least `SOUL.md`, `AGENTS.md`, `MEMORY.md`.

## Stage 1 - Prompt 1 (Task Architect): persona -> 3 spec files

- INPUT: one persona.
- RUN: use `prompt-1-task-architect-v5.md` as the system prompt and give it the persona files.
- OUTPUT (exactly 3 files):
  - `prompt.txt` - the instruction handed to the eval agent. It is NATURAL and GOAL-ONLY (states WHAT to achieve, never HOW). It leaks no steps, no values, no field labels, no filters, no service names.
  - `artifacts_description.txt` - the artifact set: ~5-10 load-bearing signal carriers hidden among ~40-50 noise files, all with generic filenames.
  - `mock_data_description.md` - two parts:
    - PART A = the mock-data generation spec (services, per-file schemas, FK, ghost recipes, volume).
    - PART B = the task design intent: the in-world scope boundary, the trap ledger (each trap + its carrier + fairness design), the rubric contract, and the value-lock KEY SCHEMA (variable names only, placeholders, ZERO concrete values).
- Phase 1 never writes a concrete artifact value; everything is placeholders at this stage.

## Stage 2 - Source the artifacts

- Read `artifacts_description.txt`. Materialize each artifact as a REAL file with a generic name (`file_1.pdf`, `data_3.csv`, `img_2.png`, `file_13.docx`, `file_2.xlsx`, ...).
- Generate Office carriers with `python-docx` / `openpyxl`; PDFs with `fpdf2` / `reportlab`. Reuse the persona's own `Artifacts/` for the bulk of the noise files.
- Human-like, no em-dashes, no AI tells. Place everything in the task's `artifacts/` folder.

## Stage 3 - Prompt 2 (Mock Data Generator): -> mock data + golden steer flow

- INPUTS (5): `prompt.txt`, `artifacts_description.txt`, `mock_data_description.md` (with PART B), the sourced artifact contents, and the schema-headers block (the real `environment/{slug}-api/` column and key headers).
- RUN: use `prompt-2-mock-data-generator-v5.md` as the system prompt.
- OUTPUT:
  - `mock_data/{slug}-api/` - the mock API tree, schema-matched to `environment/`. Authoritative live values are minted here (a balance, a date), while the persona's MEMORY may carry a stale copy.
  - `golden_steer_flow.md` - authored LAST, with CONCRETE values: the value-lock, the canonical solve path, the fairness ledger, plus convergence and uniqueness confirmations. This is the answer key + the input to task.py authoring.

## Stage 4 - Author task.py (from golden_steer_flow.md)

- Convert `golden_steer_flow.md` into `task.py`: `TASK_METADATA`, `TURNS`, and `CHECKERS` (the deterministic must-pass + hard-fail checks), plus a task `README` and optional `inject/mutations.json`.
- The value-lock becomes task.py constants; the canonical path + hard-fails become the CHECKERS.

## Stage 5 - Rubrics & PY Generator

- Put `task.py` + `README` (+ `inject/mutations.json`) in a task directory.
- GENERATE:
  ```
  cd "Rubrics and PY Generator"
  python3 run.py --task-dir <task-dir>
  ```
  This writes `tests/test_outputs.py` (one pytest checker per CHECKER), `tests/rubric_generation_prompt.md`, and `tests/trap_coverage.json`.
- AUTHOR the rubric: feed `tests/rubric_generation_prompt.md` to an LLM and save the result as `tests/rubric.json` (and `tests/rubric_trap.json` if the generator splits the trap view).
- VALIDATE:
  ```
  python3 run.py --task-dir <task-dir> --validate-only
  ```
  It must print `Result: PASS`. If not, read `tests/validation_report.md`, fix `rubric.json` (or `task.py`), and re-run.

## Stage 6 - QC

- Automated: `validation_report.md` shows `Result: PASS` (rubric schema, count 15-25, prefix rule, score distribution, trap coverage, pytest coverage, no rubric/pytest overlap).
- Manual:
  - Convergence: 3 independent experts would reach the SAME answer + SAME refusals.
  - Value-lock is consistent across artifacts and mock_data.
  - No noise file carries a value that competes with any graded slot.
  - Red lines fire (no-send, no-pay over threshold, off-limits contacts, etc.).
  - Zero em-dashes anywhere; target pass@8 <= 40%.

## Stage 7 - Create the input bundle (`input/<task_id>/`)

This is the authoritative bundle the harness consumes. The top-level directory name IS the `task_id` (only `[a-zA-Z0-9_.-]` characters are safe).
```
input/<task_id>/                   # task_id directory (safe characters: [a-zA-Z0-9_.-] per b10)
├── prompt.txt                     # REQUIRED — user-facing prompt text (UTF-8)
├── rubric.json                    # REQUIRED — rubric definition (JSON array or {"rubrics": [...]})
├── test_output.py                 # REQUIRED - test file
├── test_weights.json              # REQUIRED - test weight file
├── task.yaml                      # REQUIRED - yaml config file
├── golden_steer_flow.md           # REQUIRED - the golden steer flow for that task
├── persona/                       # OPTIONAL — agent personality / context files
│   ├── AGENTS.md                  #   agent startup instructions
│   ├── MEMORY.md                  #   long-term agent context
│   ├── HEARTBEAT.md               
│   ├── TOOLS.md
│   ├── IDENTITY.md
│   ├── USER.md
│   └── SOUL.md                    #   persona description
├── data/                          # OPTIONAL — task input files staged into the agent workspace
│   ├── home
│   ├── any_file.pdf               #   files discovered recursively; subdirectories preserved (b16 Gap B)
│   ├── audio_1.m4a                #   audio/video files supported (b33)
│   ├── data_1.xlsx                #   office documents supported (b46)
│   └── img_1.jpg                  #   images, PDFs, text files, etc.
├── mock_data/                     # OPTIONAL — per-task mock API data overrides
│   ├── gmail-api/                 #   must correspond to environment/gmail-api/
│   │   ├── messages.json
│   │   ├── threads.json
│   │   └── profile.json
│   └── google-calendar-api/
│       └── events.json
```

Rules:
- `prompt.txt` and `rubric.json` are REQUIRED;
- `rubric.json` is the LLM-judged grader: either a bare list of criteria, or an object `{"rubrics": [...]}`.
- `persona/` seeds the agent: `AGENTS.md` is read at startup, `MEMORY.md` is long-term context, `SOUL.md` is the persona description.
- `data/` is staged into the agent workspace at `/root/workspace`. Loose files (`.pdf`, audio `.m4a/.mp3/.wav/.ogg/.aac`, `video/*`, `.xlsx/.docx/.pptx`, images) are recursed via `rglob` with subdirectories preserved.
- Any `data/` subdirectory whose name ends in `-api` MUST match an existing `environment/<api>-api/`; it is bind-mounted READ-ONLY over the baked baseline at runtime (this is how your mock_data overlays the live API).
- Keep the rest of the task package beside the bundle in the repo: `test_outputs.py` (the deterministic grader from Stage 5), `task_config.yaml` (`id, name, difficulty, category, subcategory, taxonomy, tags, mock_apis, required_skills, distractor_skills, modality_tags, dependency_tags, dimensions`), and `golden_steer_flow.md` (answer key / reference).

## Stage 8 - Push to GitHub

```
git init
git add .
git commit -m "Add <task-id> evaluation task"
git push           # or: gh repo create ... ; or branch + open a PR
```

## Conventions (apply throughout)

- `prompt.txt` is goal-only and written in the persona's authentic voice.
- Generic artifact filenames; at least 4-5 modalities required to answer; `.docx`/`.xlsx` as load-bearing carriers (csv/json demoted to noise).
- Authoritative values live in the live API mock data; MEMORY may be stale (and every stale-cache trap ships its fairness block).
- No em-dashes and no AI traces in any generated file.
- Difficulty comes from a conjunction of crisp, FAIR requirements, never from ambiguity.
