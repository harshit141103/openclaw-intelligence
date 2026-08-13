# Paper Summaries

## ClawMark

**"A Living-World Benchmark for Multi-Turn, Multi-Day, Multimodal Coworker Agents"**  
*Evolvent AI, NUS, MIT, UC Berkeley et al.*

A benchmark that evaluates AI "coworker agents" across multi-turn, multi-day scenarios in a dynamic sandboxed environment. Key properties:

- **100 tasks** across 13 professional scenarios, spanning 2–6 simulated workdays
- Environment mutates independently (emails arrive, calendars shift, databases update) — both announced ("loud") and unannounced ("silent") changes
- Fully multimodal inputs: photos, scanned PDFs, audio, video, spreadsheets
- Graded by **1,537 deterministic Python checkers** (no LLM-as-judge)
- Top result: Claude Sonnet 4.6 scored **75.8** weighted / **14%** strict task success; Claude Opus 4.6 led strict success at **20%**
- Critical finding: Most models suffer a steep "Day 2 drop" when silent mutations occur; dominant failures are silent-change detection (56.5%) and backend writeback (53.6%)

---

## OfficeQA Pro

**"End-to-End Grounded Multi-Document Reasoning over Enterprise Corpora"**  
*Databricks AI Research, March 2026*

A benchmark measuring AI agents on complex, multi-step analytical reasoning over real enterprise documents (U.S. Treasury Bulletins, 1939–present). Key properties:

- **133 core questions** over an 89,000-page corpus with 26M+ numerical values
- Requires navigating nested tables, footnotes, scan noise, and longitudinal revisions
- Frontier models score **<5%** on parametric knowledge alone; best agent (Claude Opus 4.6) reaches **48%** on raw PDFs, **57%** with parsed documents
- Structured parsing (Databricks `ai_parse_document`) yields **16% relative gain** and **4–9× speedup** over raw PDF
- AI agents outperform human annotators (56.7% vs 34.6% accuracy, 9× faster)
- Key failure modes: temporal revision handling, parsing faithfulness, visual understanding of dense charts, and analytical reasoning errors
