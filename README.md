# OpenClaw Intelligence - Knowledge Base

**Owner:** Ethara.AI  
**Project:** OpenClaw RL  
**Domain:** SFT/RL training data for multi-day agentic task evaluation

---

## Purpose

This repository contains the knowledge base, methodology guides, research references, and task bundles for the OpenClaw project - a pipeline that produces multi-turn, multi-day agentic tasks designed to systematically fail frontier LLMs (Claude Opus, Sonnet, etc.) on realistic workplace workflows.

---

## Contents

| File / Directory | Description |
|------------------|-------------|
| `BRIEF-DataOps-TaskCreation.md` | Full methodology guide for task authors - research background, platform architecture, authoring workflow |
| `SUMMARY-Papers.md` | Summaries of foundational papers (ClawMark, OfficeQA Pro) |
| `AHT-Breakdown.md` | Per-task time breakdown (16h across 4 days) and daily schedule |
| `GoldenTrajectory.md` | Golden trajectory construction process, delivery JSON schema, artifact sourcing |
| `context.md` | Project context - architecture, design principles, failure categories |
| `Claude-Small-Business.md` | Domain reference material (small business scenarios) |
| `ClawMark.pdf` | ClawMark benchmark paper |
| `OfficeQA.pdf` | OfficeQA Pro benchmark paper |
| `tasks/` | Task bundles (see below) |

---

## Tasks

Each task is a self-contained evaluation scenario spanning 3–5 simulated workdays:

| Task | Domain |
|------|--------|
| `insurance_auto_claim_settlement` | Insurance - auto claims processing |
| `clinical_trial_adverse_event_escalation` | Pharma - clinical trial safety reporting |
| `software_sprint_delivery_coordination` | Engineering - sprint planning & delivery |

### Task Bundle Structure

```
task_name/
├── task.py              # Metadata, turns, mutations, checker rubric
├── inject/
│   ├── stage0/          # Seeded at task start
│   ├── stage1/          # Injected between Day 1 → Day 2
│   └── ...
├── artifacts/           # Multimodal evidence (PDFs, audio, images, spreadsheets)
└── README.md            # Human-readable task description
```

---

## Key Design Principles

- **Fail frontier models** - silent mutations, temporal traps, cross-modal contradictions
- **Deterministic evaluation** - all checkers are Python lambdas querying live service state (no LLM-as-judge)
- **Multi-system writeback** - agents must commit results to 4+ services, not just reason
- **Red-line pressure** - social engineering pressure; agents must NOT act prematurely
- **Real-world artifacts** - sourced from public data (court filings, policy templates, govt forms), never AI-synthesized

---

## Platform

Tasks execute on the **OpenClaw Harness** - isolated Docker Compose stacks with:

- Docker Filesystem (mounted workspace)
- GreenMail (SMTP/IMAP)
- Notion-compatible KB
- Google Sheets-compatible service
- Radicale (CalDAV)

An orchestrator advances turns, applies between-turn mutations, and runs checkers against live state.

---

## Research Foundations

- **ClawMark** (Evolvent AI, NUS, MIT, UC Berkeley) - 100 tasks, 1,537 checkers, 56.5% silent-change failure rate
- **OfficeQA Pro** (Databricks AI Research) - 133 questions over 89K pages, best agent at 57% accuracy
