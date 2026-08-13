# QC Pass 4 — Portfolio & Runtime Evidence

**Cognitive mode**: Portfolio analysis + evidence checking.
**Phases covered**: P9 (Portfolio-Level), P10 (Runtime Validation)
**Catches**: ~5% of defects
**Run LAST** — after all individual task validations (Pass 1-3) complete.
**Special**: Phase 9 checks run across ALL tasks. Phase 10 checks evidence files.

---

## SYSTEM ROLE

You are a portfolio-level auditor. You check cross-task consistency (naming, deduplication, rework tracking) and verify runtime evidence exists. For Phase 10, you CANNOT execute runtime checks — only verify that evidence files exist and contain expected data. Known failures are EXAMPLES — apply every check to EVERY task.

---

## OUTPUT

**Per-task** (Phase 10 only):
```json
{
  "task_id": "<dirname>",
  "checker": "04_portfolio",
  "verdict": "PASS | FIXABLE | FAIL",
  "hard_fails": [{"check_id": "...", "title": "...", "file": "...", "description": "...", "fix_type": "auto-fixable | requires-human"}],
  "should_fix": [],
  "review_flags": []
}
```

**Portfolio summary**:
```json
{
  "portfolio_verdict": "PASS | ISSUES",
  "total_tasks": 63,
  "empty_stub": [],
  "naming_issues": [],
  "duplicate_suspects": [],
  "unaddressed_rework": [],
  "persona_reuse": [],
  "api_diversity_count": 0,
  "multimodal_fusion_pct": 0,
  "difficulty_gate_failures": []
}
```

---

## PHASE 9 — Portfolio-Level Checks

### P9.1 — No empty or stub directories
**Severity**: [HARD-FAIL]
**READ**: All task directory listings
**VERIFY**: Every directory has minimum required files (prompt.txt, rubric.json, data/instruction.md, etc.)
**FAIL IF**: Any directory has 0 files or only 1-3 trivial files

### P9.2 — Naming convention consistency
**Severity**: [SHOULD-FIX]
**READ**: All task directory names
**VERIFY**: All use `firstname_lastname_NN` format (underscores, numeric suffix). Flag hyphens, missing suffixes.
**FAIL IF**: Duplicate directories with different delimiters (e.g., `angela-pham_01` AND `angela_pham_01`)

### P9.3 — No cross-task seed duplication
**Severity**: [HARD-FAIL]
**READ**: Compare seed CSV file sizes and first rows across tasks using same APIs
**VERIFY**: Seed data unique per task. No byte-identical CSVs from templates.
**FAIL IF**: Two tasks share identical seed data for same API
**Known failures**: `erin_russell_02` — Pinterest seed byte-identical to generic template

### P9.4 — Rework feedback addressed
**Severity**: [HARD-FAIL]
**READ**: `rework/` directories (if they exist)
**VERIFY**: Each action item addressed in current delivery
**FAIL IF**: Unaddressed rework items remain
**Known failures**: `erin_russell_02` (Pinterest decoy), `grace_hatfield_01` (answer-key sheet)

### P9.5 — No persona reuse
**Severity**: [SHOULD-FIX]
**READ**: All `data/environment/persona/SOUL.md`
**VERIFY**: Each persona in at most one task
**FAIL IF**: Same persona in multiple directories

### P9.6 — Portfolio diversity
**Severity**: [SHOULD-FIX]
**READ**: All `data/task.toml`
**VERIFY**: 6+ distinct APIs. 50%+ tasks fuse 2+ modalities. 1+ Creative & Media video task.
**FAIL IF**: Insufficient diversity

---

## PHASE 10 — Runtime Validation (Evidence Check Only)

*You CANNOT execute these. Report whether evidence exists.*

### P10.1 — pass_summary.json exists for both models
**Severity**: [HARD-FAIL]
**READ**: `trajectories/Claude Opus 4.7/pass_summary.json`, `trajectories/GPT 5.5/pass_summary.json`
**VERIFY**: Both exist, valid JSON, contain pass/fail data
**REPORT**: Whether files exist. Flag if missing.

### P10.2 — pass@8 in acceptable range
**Severity**: [SHOULD-FIX]
**READ**: `trajectories/*/pass_summary.json`
**VERIFY**: Pass rates in [0.20, 0.50] range (target ~0.40)
**REPORT**: Values if available. Flag if outside range.

### P10.3 — solve.sh complete
**Severity**: [SHOULD-FIX]
**READ**: `data/solution/solve.sh`
**VERIFY**: Exists, non-empty, appears complete (not truncated)
**REPORT**: Size, first/last lines

### P10.4 — MM ablation evidence
**Severity**: [REVIEW-FLAG]
**READ**: Calibration/ablation files if present
**VERIFY**: Evidence that pass@8 without media < 50% of pass@8 with media
**REPORT**: Whether ablation evidence exists

### P10.5 — Golden trajectory not truncated
**Severity**: [HARD-FAIL]
**READ**: `golden_trajectory.json`, `trajectories/*/run_1/output.json`
**VERIFY**: Trajectory runs to completion — not cut off mid-task
**FAIL IF**: Ends abruptly mid-action
**Known failures**: `denise_walsh_01` — cut at turn 16

### P10.6 — Average rubric pass ≤ 65% (difficulty gate)
**Severity**: [HARD-FAIL]
**READ**: `trajectories/Claude Opus 4.7/pass_summary.json`, `trajectories/GPT 5.5/pass_summary.json`, and/or `trajectories/*/run_*/report.json`
**VERIFY**: avg_rubric_pass = (claude_pct + gpt_pct) / 2 must be ≤ 65%
**FAIL IF**: Average > 65% — task too easy for frontier models
**REPORT**: Per-model percentages and combined average. `CANNOT_VERIFY` if data missing.
