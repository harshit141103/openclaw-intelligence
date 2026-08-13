# QC Pass 3 — Design Quality & Task Difficulty

**Cognitive mode**: Judgment — prompt quality, persona alignment, media assessment, difficulty evaluation.
**Phases covered**: P8 (Prompt & Design), P8B (Join Necessity & Difficulty)
**Catches**: ~15% of defects
**Run THIRD** — after Pass 1-2 confirm structural/semantic integrity.
**Note**: Several checks are marked [SUBJECTIVE] — LLM assessment may be unreliable. Flag rather than hard-fail on borderline cases.

---

## SYSTEM ROLE

You are a task design auditor. You evaluate prompt quality, persona alignment, media necessity, and task difficulty. For [SUBJECTIVE] checks, err toward flagging rather than passing — false positives are cheaper than missed design defects. Known failures are EXAMPLES — apply every check to EVERY task.

---

## OUTPUT (per task)

```json
{
  "task_id": "<dirname>",
  "checker": "03_design",
  "verdict": "PASS | FIXABLE | FAIL",
  "hard_fails": [{"check_id": "...", "title": "...", "file": "...", "description": "...", "fix_type": "auto-fixable | requires-human"}],
  "should_fix": [{"check_id": "...", "title": "...", "file": "...", "description": "..."}],
  "review_flags": [{"check_id": "...", "title": "...", "description": "..."}]
}
```

---

## PHASE 8 — Prompt and Design Quality

### P8.1 — Prompt is 2-4 sentences [SUBJECTIVE]
**Severity**: [SHOULD-FIX]
**READ**: `data/instruction.md`
**VERIFY**: 2-4 sentences. No step enumeration ("First X, then Y, finally Z"). No numbered lists or bullet points. No formal requirement language.
**FAIL IF**: 5+ sentences, step enumeration, or structural markup

### P8.2 — No technical API names
**Severity**: [HARD-FAIL]
**READ**: `data/instruction.md`
**VERIFY**: No "YouTube Data API", "GET /courses/{id}/coursework". Natural-platform language only.
**FAIL IF**: Technical API references found

### P8.3 — No Socratic or over-casual framing
**Severity**: [SHOULD-FIX]
**READ**: `data/instruction.md`
**VERIFY**: No "What do you notice?", "Walk me through...". No excessive filler. Goal-oriented.
**FAIL IF**: Socratic or unusably casual framing

### P8.4 — Media is load-bearing [SUBJECTIVE]
**Severity**: [HARD-FAIL]
**READ**: `data/instruction.md`, files in `data/environment/artifacts/inputs/files/`
**VERIFY**: Removing all media makes task >50% unsolvable. Media essential, not decorative.
**FAIL IF**: Task solvable without media
**Known failures**: Pilot G8 — decorative meal photo

### P8.5 — Format diversity in media
**Severity**: [SHOULD-FIX]
**READ**: File extensions in inputs
**VERIFY**: At least 2 distinct formats (target 3+). At least 3 of 6 imperfection types.
**FAIL IF**: Monoculture or < 3 imperfection types

### P8.6 — No AI/stock images; photos match task inventory [SUBJECTIVE]
**Severity**: [HARD-FAIL]
**READ**: Image files, `rubric.json`, `data/instruction.md`
**VERIFY**: No AI-generated, watermarked stock, or Lorem ipsum. Photos depict task-specific items.
**FAIL IF**: AI-generated/stock/template detected, OR photos don't match task inventory
**Known failures**: `denise_walsh_01` (Pexels stock vs actual inventory)

### P8.7 — Persona voice matches SOUL.md [SUBJECTIVE]
**Severity**: [REVIEW-FLAG]
**READ**: `data/instruction.md`, `data/environment/persona/SOUL.md`
**VERIFY**: Prompt voice matches persona (formality, vocabulary, emotional register)
**FAIL IF**: Generic with no persona voice markers

### P8.8 — Task emerges from persona context [SUBJECTIVE]
**Severity**: [REVIEW-FLAG]
**READ**: `data/instruction.md`, `data/environment/persona/MEMORY.md`
**VERIFY**: Task naturally emerges from persona's occupation, hobbies, relationships
**FAIL IF**: Task feels contrived or unrelated

### P8.9 — Pipeline depth adequate [SUBJECTIVE]
**Severity**: [SHOULD-FIX]
**READ**: `data/instruction.md`
**VERIFY**: Task implies 5+ intermediate stages. No decorative stages.
**FAIL IF**: Trivially solvable in 1-2 steps

### P8.10 — Boundary Paradox resolved
**Severity**: [HARD-FAIL]
**READ**: `data/instruction.md`, persona SOUL.md, MEMORY.md
**VERIFY**: If persona is professional in task domain, AI positioned as research/organization tool, NOT advisor
**FAIL IF**: AI positioned as expert advisor in persona's own professional domain

### P8.11 — No em dashes or AI-prose in prompt
**Severity**: [HARD-FAIL]
**READ**: `data/instruction.md`, `prompt.txt`
**VERIFY**: ZERO em dashes (U+2014). ZERO LLM-tell phrases: "It's important to note", "This ensures", "Delve", "Leverage", "Comprehensive", "Streamline", "Utilize", "Facilitate", "In order to", "Needless to say", "Moving forward". No filler: "essentially", "basically", "fundamentally", "arguably".
**FAIL IF**: Any em dash or banned phrase found

### P8.12 — WHAT not HOW (no solution recipe)
**Severity**: [HARD-FAIL]
**READ**: `data/instruction.md`
**VERIFY**: No step-by-step instructions, calculation formulas, join logic. Natural direction OK.
**FAIL IF**: Following prompt verbatim produces answer without reasoning

### P8.13 — Natural prose, not benchmark/checklist
**Severity**: [HARD-FAIL]
**READ**: `data/instruction.md`
**VERIFY**: Continuous prose, not numbered instructions. No benchmark wording.
**FAIL IF**: Formatted as checklist or reads like evaluation exercise

### P8.14 — Persona tools match prompt references
**Severity**: [HARD-FAIL]
**READ**: `data/instruction.md`, `data/environment/persona/AGENT.md` (or AGENTS.md)
**VERIFY**: Every tool/service prompt references is in persona's connected accounts. People/places in prompt exist in persona.
**FAIL IF**: Prompt uses tool not in persona, or references absent person
**Known failures**: `amanda_webb_01` — Instagram @dance.amanda vs API serving brewedawakening_

---

## PHASE 8B — Data Join Necessity and Task Difficulty

### P8B.1 — Task requires joining input + API data
**Severity**: [HARD-FAIL]
**READ**: `data/instruction.md`, input files, seed data
**VERIFY**: Decompose prompt into asks. At minimum: (a) 1+ ask requires API data, (b) 1+ ask requires input files, (c) 1+ ask requires BOTH. Task NOT completable from single source.
**FAIL IF**: API is decorative, OR input files decorative, OR zero join asks

### P8B.2 — Caption-substitution test [SUBJECTIVE]
**Severity**: [HARD-FAIL]
**READ**: Media files, `data/instruction.md`
**VERIFY**: For each media file: if replaced by one-line caption, would task still have correct answer? If YES for ALL → not genuinely multimodal.
**FAIL IF**: All media replaceable by captions

### P8B.3 — At least 1 prompt mutation trap
**Severity**: [HARD-FAIL]
**READ**: `data/instruction.md`, input files, seed data
**VERIFY**: Task includes at least 1 trap: decoy value, temporal revision, cross-modal contradiction, distractor noise, multi-hop synthesis, financial threshold, constraint conflict, or poison pill.
**FAIL IF**: Zero traps — no deliberate complexity for SOTA models

### P8B.4 — Multi-step reasoning required
**Severity**: [HARD-FAIL]
**READ**: `data/instruction.md`, `rubric.json`
**VERIFY**: At least 1 non-trivial calculation. At least 1 evaluation across multiple data points. 3+ logical steps. Sequential dependency (intermediate result consumed by later ask).
**FAIL IF**: Pure lookup/transcription with zero calculation or sequential dependency

### P8B.5 — No port/infrastructure leakage
**Severity**: [HARD-FAIL]
**READ**: Persona files, `data/instruction.md`, input files
**VERIFY**: No localhost, 127.0.0.1, port numbers (:8000), docker-compose, kubectl. Carve-outs: phone numbers, timestamps, prices.
**FAIL IF**: Any infrastructure reference found

### P8B.6 — Cross-source entity naming consistency
**Severity**: [SHOULD-FIX]
**READ**: Input files, seed data
**VERIFY**: Entities use consistent naming across data sources. Join keys unambiguous.
**FAIL IF**: Same entity different names with no discoverable mapping
