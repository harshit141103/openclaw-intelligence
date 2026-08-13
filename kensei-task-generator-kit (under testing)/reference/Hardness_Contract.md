## Hardness Contract

### 1 \- Hardness Levers (341 levers, 45 categories)

**Tiered Hardness Contract** \- every task realizes a tier-appropriate combination of levers from 1.1:

- **Baseline (BLOCKING \- every task):** ≥ 6 levers drawn from ≥ 5 distinct categories.  
- **Hard (default target):** ≥ 9 levers from ≥ 7 distinct categories, **including ≥ 1 lever from each of {ADV, INJ, CMC}**.  
- **Frontier-defeat (ambition tier):** ≥ 12 levers from ≥ 9 distinct categories, spanning **≥ 3 modality types**, with **≥ 1 contradiction-fusion (CMC)** \+ **≥ 1 injection (INJ)** \+ **≥ 1 silent-failure (LH4 or LH8)**.

**Anti-Gaming Category-Cap Rule.** When counting toward the *distinct-categories* requirement, a maximum of **3 levers per category** may contribute. The 4th and 5th levers in a category raise the *total lever count* but not the distinct-category count.

**Cross-Axis Rule.** The levers realized MUST span the three difficulty axes:

- **Perception axis (12):** LV, FG, OCR, AUD, SG, CHT, MLT, SPF, TDS, DOC, DGM, HWR.  
- **Reasoning axis (16):** CMC, ADV, NUM, TMP, MEM, DEC, RSN, CAU, TOM, SCI, PRF, PLN, CAL, HAL, SYN, MAD.  
- **Agentic axis (17):** LH, FS, GUI, WEB, TOOL, INJ, FMT, COD, SQL, DSA, RAG, IFC, SLF, EMB, AGT, PRV, SEC. At the **Hard** tier and above, ≥ 1 lever from **each** axis is required.

Each lever carries a parenthetical benchmark-failure cite. Cites whose arXiv-ID year ≥ 2025 are flagged, `reportedly`.

**A. LV \- Long-Video reasoning**

- LV1 \- multi-minute clip, answer depends on a single transient frame (MLVU arXiv:2406.04264 \- needle-frame retrieval beyond short context).  
- LV2 \- event ordering across non-adjacent segments (TempCompass arXiv:2403.00476 \- temporal grounding failures).  
- LV3 \- counting across occlusions / re-entries (LongVideoBench arXiv:2407.15754 \- long-video evidence aggregation failures).  
- LV4 \- audio-visual desync detection (Video-MME arXiv:2405.21075 \- cross-stream alignment failures).  
- LV5 \- scene-change-triggered state update (MLVU arXiv:2406.04264 \- long-context drift).  
- LV6 \- off-screen-event inference from on-screen consequence (EgoSchema arXiv:2308.09126 \- \<33% vs 76% human).  
- LV7 \- needle-frame \>30min (MLVU arXiv:2406.04264 \- long-video needle retrieval).  
- LV8 \- egocentric multi-event (EgoSchema arXiv:2308.09126 \- \<33% vs 76% human).  
- LV9 \- fine-grained temporal action seg (TempCompass arXiv:2403.00476 \- 8 SOTA).  
- LV10 \- multi-anchor evidence agg (LongVideoBench arXiv:2407.15754 \- long-context multimodal aggregation).

**B. FG \- Fine-Grained visual**

- FG1 \- sub-pixel gauge/meter reading (MathVista arXiv:2310.02255 \- fine-grained perception failures).  
- FG2 \- near-duplicate discrimination (MathVista arXiv:2310.02255 \- fine-grained visual classification failures).  
- FG3 \- small-text-in-clutter OCR target (DUDE arXiv:2305.08455 \- dense-scene document parsing failures).  
- FG4 \- color-shade threshold decision (ChartBench arXiv:2312.15915 \- visual quantization failures).  
- FG5 \- partial-occlusion identity (VisualWebArena arXiv:2401.13649 \- visual grounding under occlusion).  
- FG6 \- diagram-edge tracing (MathVista arXiv:2310.02255 \- structured-visual parsing failures).  
- FG7 \- chart-element under occlusion (ChartBench arXiv:2312.15915 \- GPT-4V \~45% unannotated).  
- FG8 \- minute-iconography dense UI (Mind2Web arXiv:2306.06070 \- WebCanvas 23.1%).  
- FG9 \- sub-glyph numeric digit discrimination (8 vs 0, 1 vs 7\) in degraded scan (DUDE arXiv:2305.08455 \- fine-glyph document failures).  
- FG10 \- micro-legend / footnote-marker detection in dense figure (ChartBench arXiv:2312.15915 \- small-element chart failures).

**C. OCR \- Optical Character Recognition under degradation**

- OCR1 \- skew \+ fade \+ blur composite (DUDE arXiv:2305.08455 \- degraded-document OCR failures).  
- OCR2 \- mixed-script (Latin \+ Cyrillic / CJK) handwriting (LAraBench arXiv:2305.14982 \- multilingual OCR failures).  
- OCR3 \- struck-through / overwritten value (DUDE arXiv:2305.08455 \- correction-tracking failures).  
- OCR4 \- low-contrast thermal-print receipt (DUDE arXiv:2305.08455 \- faded-receipt OCR failures).  
- OCR5 \- rotated / mirrored stamp text (DUDE arXiv:2305.08455 \- orientation-robust OCR failures).  
- OCR6 \- handwriting-on-form-field (LAraBench arXiv:2305.14982 \- HTR failures).  
- OCR7 \- watermark-overlapping body text (DUDE arXiv:2305.08455 \- separation failures).  
- OCR8 \- Arabic/RTL line-order (KITAB-Bench arXiv:2502.14949 \- reportedly \- 65%).  
- OCR9 \- Arabic ligature+diacritic (Baseer arXiv:2509.18174 \- reportedly).  
- OCR10 \- Arabic-Latin code-mixed (LAraBench arXiv:2305.14982 \- mixed-script OCR failures).

**D. AUD \- Audio**

- AUD1 \- accented multi-speaker diarisation (ASVspoof2021 arXiv:2109.00537 \- speaker-attribution failures).  
- AUD2 \- number-in-noise transcription (ASVspoof2021 arXiv:2109.00537 \- ASR-in-noise failures).  
- AUD3 \- code-switching mid-utterance (LAraBench arXiv:2305.14982 \- multilingual ASR failures).  
- AUD4 \- retracted-then-corrected spoken value (ASVspoof2021 arXiv:2109.00537 \- self-correction tracking failures).  
- AUD5 \- road/ambient-noise voice memo (ASVspoof2021 arXiv:2109.00537 \- far-field ASR failures).  
- AUD6 \- overlapping-speech disambiguation (ASVspoof2021 arXiv:2109.00537 \- cocktail-party failures).  
- AUD7 \- non-speech audio-event cue (Video-MME arXiv:2405.21075 \- audio-event cue failures).  
- AUD8 \- prosody-dependent intent (ASVspoof2021 arXiv:2109.00537 \- paralinguistic failures).  
- AUD9 \- long-form diarisation drift (lost-in-the-middle arXiv:2307.03172 \- long-context attribution drift).  
- AUD10 \- buried single-utterance value in long multi-speaker recording (MMNeedle arXiv:2406.11230 \- audio needle-in-haystack failure).

**E. CMC \- Cross-Modal Contradiction**

- CMC1 \- print says X, handwriting \+ audio say Y (ChartBench arXiv:2312.15915 \- fidelity-trust trap).  
- CMC2 \- API ledger vs artifact enumeration mismatch (TabFact arXiv:1909.02164 \- source-of-truth conflict).  
- CMC3 \- image timestamp vs document date conflict (TempCompass arXiv:2403.00476 \- temporal contradiction).  
- CMC4 \- chart trend vs tabular underlying conflict (ChartBench arXiv:2312.15915 \- visualization-vs-data conflict).  
- CMC5 \- caption vs depicted-content conflict (VisualWebArena arXiv:2401.13649 \- grounding contradiction).  
- CMC6 \- chart-trend-vs-row-count (ChartBench arXiv:2312.15915 \- chart/table contradiction).  
- CMC7 \- table-claim-vs-prose (TabFact arXiv:1909.02164 \- table-fact contradiction).  
- CMC8 \- multi-turn dialogue self-contradiction (TempCompass arXiv:2403.00476 \- temporal self-contradiction).

**F. SG \- Spatial Grounding**

- SG1 \- sparse-region pointing in large image (VisualWebArena arXiv:2401.13649 \- grounding-sparsity failures).  
- SG2 \- relative-position chain ("left of the third from top") (OSWorld arXiv:2404.07972 \- relational grounding failures).  
- SG3 \- cross-page coordinate transfer (DUDE arXiv:2305.08455 \- layout-grounding failures).  
- SG4 \- occluded-target localization (VisualWebArena arXiv:2401.13649 \- partial-grounding failures).  
- SG5 \- fine spatial threshold ("within 2 mm") (OSWorld arXiv:2404.07972 \- precision-grounding failures).  
- SG6 \- multi-element relational dense UI (Mind2Web arXiv:2306.06070 \- 23.1%).  
- SG7 \- coordinate-transfer rotated/zoomed (OSWorld arXiv:2404.07972 \- 72.4% vs 12.2%).  
- SG8 \- nth-from-edge ordinal selection in a dense grid (AndroidWorld arXiv:2405.14573 \- ordinal-grounding failures).  
- SG9 \- bounding-box estimation for an unlabelled region (VisualWebArena arXiv:2401.13649 \- region-estimation failures).  
- SG10 \- multi-hop spatial chain across two stitched screenshots (OSWorld arXiv:2404.07972 \- cross-image grounding failures).

**G. LH \- Long-Horizon agentic**

- LH1 \- 20+ step state-carrying pipeline (API-Bank arXiv:2304.08244 \- long-horizon state collapse).  
- LH2 \- conditional branch on intermediate result (AITW arXiv:2307.10088 \- planning-brittleness failures).  
- LH3 \- distractor-API present, must not be state-mutated (API-Bank arXiv:2304.08244 \- tool-selection failures).  
- LH4 \- recovery after a silent failure (API-Bank arXiv:2304.08244 \- error-recovery failures).  
- LH5 \- deferred dependency (later step needs an early artifact) (lost-in-the-middle arXiv:2307.03172 \- memory failures).  
- LH6 \- idempotency / no-double-execute discipline (API-Bank arXiv:2304.08244 \- state-safety failures).  
- LH7 \- 30+step branch-backtrack (AndroidWorld arXiv:2405.14573 \- 30.6%).  
- LH8 \- silent-failure recovery no-error response (API-Bank arXiv:2304.08244 \- silent-failure recovery).  
- LH9 \- multi-day checkpoint serial (lost-in-the-middle arXiv:2307.03172 \- long-horizon memory drift).  
- LH10 \- partial-failure mobile recovery (AITW arXiv:2307.10088 \- DigiRL 67.2%).

**H. ADV \- Adversarial**

- ADV1 \- answer-shaped decoy present (GSM-DC arXiv:2505.18761 \- reportedly \- distractor-trust failures).  
- ADV2 \- highest-fidelity source is wrong (ChartBench arXiv:2312.15915 \- authority-bias trap).  
- ADV3 \- plausible-but-out-of-scope shortcut offered (Mind2Web arXiv:2306.06070 \- shortcut-trap failures).  
- ADV4 \- premature-confidence trap (MathVista arXiv:2310.02255 \- calibration failures).  
- ADV5 \- leading-but-false API field (ASB arXiv:2410.02644 \- data-trust failures).  
- ADV6 \- over-helpful over-execution trap (API-Bank arXiv:2304.08244 \- abstention failures).  
- ADV7 \- answer-shape primed pre-fusion (lost-in-the-middle arXiv:2307.03172 \- positional priming failure).  
- ADV8 \- adversarial system-msg-impersonation in tool output (Greshake arXiv:2302.12173 \- indirect-injection vulnerability).  
- ADV9 \- confidence-inflated false rationale API field (ASB arXiv:2410.02644 \- 84.30% max attack).

**I. FS \- Filesystem Navigation**

- FS1 \- target file nested deep in a cross-pollinated home tree, not in a flat assets dir (OSWorld arXiv:2404.07972 \- file-navigation failures).  
- FS2 \- relevant file shares a directory with the same extension as clutter/decoy files (OSWorld arXiv:2404.07972 \- directory-disambiguation failures).  
- FS3 \- hidden / dotfile carries load-bearing content (`.config`, `.receipts/`) (OSWorld arXiv:2404.07972 \- hidden-file blindness).  
-   
- FS4 \- near-duplicate filenames differing by a token (`invoice_final.pdf` vs `invoice_final_v2.pdf`) (AndroidWorld arXiv:2405.14573 \- filename-disambiguation failures).  
- FS5 \- stale / superseded copy in `Downloads/` vs current in `Documents/` (AndroidWorld arXiv:2405.14573 \- recency-resolution failures).  
- FS6 \- cross-persona pollution: another person's file present as a trap (OSWorld arXiv:2404.07972 \- ownership-attribution failures).  
- FS7 \- path-in-artifact reference ("see the file in `~/Documents/Taxes/2024/`") that must be resolved by navigation (OSWorld arXiv:2404.07972 \- indirection-resolution failures).  
- FS8 \- symlink outside dir (OSWorld arXiv:2404.07972 \- filesystem navigation failures).  
- FS9 \- case-insensitive filename collision (AndroidWorld arXiv:2405.14573 \- 30.6%).  
- FS10 \- archive/zip load-bearing inner (OSWorld arXiv:2404.07972 \- nested-artifact navigation failures).

**J. INJ \- Indirect Injection (difficulty lever, never refusal test)**

- INJ1 \- injected instruction in **PDF text layer** body (Greshake arXiv:2302.12173 \- document-borne injection).  
- INJ2 \- injected instruction in an **XLSX cell** (often an off-screen/hidden sheet) (SpreadsheetBench arXiv:2406.14991 \- spreadsheet-borne injection).  
- INJ3 \- injected instruction in a **DOCX comment** or tracked-change (DUDE arXiv:2305.08455 \- document-metadata injection).  
- INJ4 \- injected instruction in a **mock-API response** body field (SecAlign arXiv:2410.05451 \- tool-result poisoning).  
- INJ5 \- injected instruction in **image EXIF / metadata** (Greshake arXiv:2302.12173 \- metadata injection).  
- INJ6 \- injected instruction in a **filename** (OSWorld arXiv:2404.07972 \- filename injection).  
- INJ7 \- injected instruction in **image alt-text / accessibility caption** (VisualWebArena arXiv:2401.13649 \- alt-text injection).  
- INJ8 \- injected instr chart-axis label PDF/PNG (ChartBench arXiv:2312.15915 \- chart-carrier injection).  
- INJ9 \- injected instr screenshot OCR region (AgentDojo arXiv:2406.13352 \- screenshot-region injection).  
- INJ10 \- injected instr mock-API error body (ASB arXiv:2410.02644 \- 84.30%).

Each INJ lever is graded by **outcome divergence** (5.3.18 / 7.44): obeying the injection yields a mutually-exclusive wrong deliverable or an unauthorized state change that fails the normal outcome checks. The grader **never** classifies refusal, safety, or policy behavior.

**K. FMT \- Complex-Format parsing**

- FMT1 \- **multi-sheet XLSX** with cross-sheet formula dependency (SpreadsheetBench arXiv:2406.14991 \- frontier ≈12% Pass@1).  
- FMT2 \- **hidden / very-hidden XLSX sheet** holding load-bearing data (SpreadsheetBench arXiv:2406.14991 \- hidden-sheet blindness).  
- FMT3 \- XLSX with **formulas vs cached values** divergence (SpreadsheetBench arXiv:2406.14991 \- formula-evaluation failures).  
- FMT4 \- **DOCX tracked-changes / comments** that alter the operative value (DUDE arXiv:2305.08455 \- revision-resolution failures).  
- FMT5 \- **real text-layer PDF** with multi-column / table reflow (DUDE arXiv:2305.08455 \- multi-page VRD failures).  
- FMT6 \- **merged-cell / non-rectangular table** extraction (SpreadsheetBench arXiv:2406.14991 \- table-structure failures).  
- FMT7 \- **complex-format axis is non-overlapping** with the OCR axis: difficulty comes from structural parsing, not visual degradation (SpreadsheetBench arXiv:2406.14991 \- distinct-hardness-axis requirement).  
- FMT8 \- CSV/TSV null-byte/mixed-delim (SpreadsheetBench arXiv:2406.14991 \- \~12% Pass@1).  
- FMT9 \- JSON-in-comment/YAML-in-JSON (DUDE arXiv:2305.08455 \- nested-format parsing failure).  
- FMT10 \- XLSX conditional-format hidden state (SpreadsheetBench arXiv:2406.14991 \- hidden-state spreadsheet failure).

**L. GUI \- GUI Grounding**

- GUI1 \- sub-screen target ≤1% area (OSWorld arXiv:2404.07972 \- 72.4% vs 12.2%).  
- GUI2 \- pixel-precision drag-handle (AndroidWorld arXiv:2405.14573 \- 30.6%).  
- GUI3 \- multi-monitor/window confusion (OSWorld arXiv:2404.07972 \- window-state grounding failure).  
- GUI4 \- modal dismiss-vs-confirm (AndroidWorld arXiv:2405.14573 \- modal-action failure).  
- GUI5 \- IME/accent-key composition (OSWorld arXiv:2404.07972 \- input-method failure).  
- GUI6 \- touch-vs-cursor affordance mobile (AndroidWorld arXiv:2405.14573 \- 30.6%).  
- GUI7 \- overlay/ad obscuration (Mind2Web arXiv:2306.06070 \- 23.1%).

**M. WEB \- Web Navigation**

- WEB1 \- multi-page form pagination (WebVoyager arXiv:2401.13919 \- 59.1%).  
- WEB2 \- dark-pattern trap link (Mind2Web arXiv:2306.06070 \- 23.1%).  
- WEB3 \- autocomplete-vs-typed (WebArena arXiv:2307.13854 \- web-agent failure).  
- WEB4 \- login-wall silent-failure (WebArena arXiv:2307.13854 \- silent web failure).  
- WEB5 \- visual grounding under cookie banner (VisualWebArena arXiv:2401.13649 \- visual web grounding failure).  
- WEB6 \- AJAX stale-DOM (Mind2Web arXiv:2306.06070 \- 23.1%).  
- WEB7 \- multi-tab cross-ref (WebVoyager arXiv:2401.13919 \- 59.1%).

**N. TOOL \- Tool/API Use**

- TOOL1 \- fn-name disambig near-identical sig (API-Bank arXiv:2304.08244 \- tool-name disambiguation failure).  
- TOOL2 \- NL-slot→param binding error (API-Bank arXiv:2304.08244 \- parameter binding failure).  
- TOOL3 \- schema drift between calls (API-Bank arXiv:2304.08244 \- schema drift failure).  
- TOOL4 \- required-vs-optional param elision (API-Bank arXiv:2304.08244 \- required-parameter failure).  
- TOOL5 \- idempotency-token mishandling retry (AITW arXiv:2307.10088 \- 67.2%).  
- TOOL6 \- multi-tool compose-order error (AITW arXiv:2307.10088 \- 67.2%).  
- TOOL7 \- paginated / cursor-token API result aggregation (API-Bank arXiv:2304.08244 \- multi-call aggregation failure).

**O. CHT \- Chart Reasoning**

- CHT1 \- unannotated bar/line numeric extract (ChartBench arXiv:2312.15915 \- GPT-4V \~45%).  
- CHT2 \- log-vs-linear axis (ChartBench arXiv:2312.15915 \- axis-scale failure).  
- CHT3 \- multi-series legend-line colour collision (ChartBench arXiv:2312.15915 \- legend collision failure).  
- CHT4 \- error-bar/CI reading (MathVista arXiv:2310.02255 \- uncertainty-reading failure).  
- CHT5 \- chart-vs-caption contradiction (ChartBench arXiv:2312.15915 \- chart-caption contradiction).  
- CHT6 \- pie/proportional under occlusion (ChartBench arXiv:2312.15915 \- proportional reasoning under occlusion).  
- CHT7 \- dual-axis / secondary-axis misattribution (ChartBench arXiv:2312.15915 \- secondary-axis binding failure).

**P. MEM \- Long-Context Memory**

- MEM1 \- buried-needle 100k+ token (lost-in-the-middle arXiv:2307.03172 \- positional memory failure).  
- MEM2 \- multi-needle doc haystack (MMNeedle arXiv:2406.11230 \- multi-needle retrieval failure).  
- MEM3 \- long-multimodal needle image+text (MLNeedle arXiv:2408.10151 \- multimodal needle failure).  
- MEM4 \- unified multimodal haystack (U-NIAH arXiv:2503.00353 \- reportedly).  
- MEM5 \- adversarial distractor haystack (HaystackCraft arXiv:2510.07414 \- reportedly).  
- MEM6 \- needle re-intro after distractor (lost-in-the-middle arXiv:2307.03172 \- distractor memory failure).  
- MEM7 \- distractor-conditioned math (GSM-DC arXiv:2505.18761 \- reportedly).

**Q. DEC \- Deception/Source-Trust Difficulty (difficulty-never-sycophancy-classifier)**

- DEC1 \- user-suggested wrong answer resist (Goldowsky-Dill arXiv:2502.03407 \- reportedly).  
- DEC2 \- leading API field false 'correct' claim (ASB arXiv:2410.02644 \- 84.30%).  
- DEC3 \- corroborating-but-wrong voice-memo (Sandbagging positional-collapse \- reportedly \- 72.1%→4.3%).  
- DEC4 \- false-corroboration cluster illusion-of-consensus (Goldowsky-Dill arXiv:2502.03407 \- reportedly).  
- DEC5 \- over-eager-agreement multi-turn (sycophancy \- reportedly \- adjacent Goldowsky-Dill arXiv:2502.03407).  
- DEC6 \- authoritative-but-stale document trusted over fresh source (Goldowsky-Dill arXiv:2502.03407 \- reportedly).  
- DEC7 \- planted majority-vote among decoy artifacts overrides correct minority (HaystackCraft arXiv:2510.07414 \- reportedly).

**DEC FORK-2 MIRROR BLOCKQUOTE:** "Each DEC lever graded by outcome divergence on the deliverable ... the grader NEVER runs a sycophancy classifier, a deception classifier, a stance classifier, or any safety/policy classifier ... resistance measured purely by whether the real task's outcome oracle passed."

**R. NUM \- Numeric/Unit Reasoning**

- NUM1 \- imperial/metric mid-task (MathVista arXiv:2310.02255 \- unit-conversion failure).  
- NUM2 \- currency stale-FX trap (TabFact arXiv:1909.02164 \- table-fact numeric failure).  
- NUM3 \- sigfig/rounding mismatch (MathVista arXiv:2310.02255 \- rounding failure).  
- NUM4 \- date-format ambiguity MM/DD vs DD/MM (TabFact arXiv:1909.02164 \- format ambiguity failure).  
- NUM5 \- pct-of-base vs pct-point (MathVista arXiv:2310.02255 \- percentage-base failure).  
- NUM6 \- locale decimal/thousands sep (TabFact arXiv:1909.02164 \- locale numeric failure).  
- NUM7 \- multi-step compound arithmetic with intermediate-rounding trap (MathVista arXiv:2310.02255 \- compound-arithmetic failure).

**S. TMP \- Temporal Reasoning**

- TMP1 \- cross-timezone event order (LongVideoBench arXiv:2407.15754 \- temporal order failure).  
- TMP2 \- recurring-event next-instance (TempCompass arXiv:2403.00476 \- recurrence failure).  
- TMP3 \- business-day vs calendar-day deadline (TempCompass arXiv:2403.00476 \- deadline semantics failure).  
- TMP4 \- DST transition edge (TempCompass arXiv:2403.00476 \- DST edge failure).  
- TMP5 \- long-horizon multi-day intervening events (LongVideoBench arXiv:2407.15754 \- multi-day event failure).  
- TMP6 \- fiscal-vs-calendar year boundary (TabFact arXiv:1909.02164 \- boundary temporal failure).  
- TMP7 \- duration arithmetic across non-contiguous logged intervals (LongVideoBench arXiv:2407.15754 \- interval-aggregation failure).

**T. SPF \- Spoof/Authenticity Difficulty (difficulty-never-deepfake-classifier)**

- SPF1 \- synthetic/TTS-spoofed segment (ASVspoof2021 arXiv:2109.00537 \- spoofed segment failure).  
- SPF2 \- voice-conversion attack (ASVspoof5 arXiv:2502.08857 \- reportedly).  
- SPF3 \- multilingual deepfake voice (multilingual-deepfake arXiv:2412.17924 \- reportedly).  
- SPF4 \- partial-replay/splice (ASVspoof2021 arXiv:2109.00537 \- replay/splice failure).  
- SPF5 \- provenance-mismatch: spoofed segment contradicts corroborated authentic segments (ASVspoof5 arXiv:2502.08857 \- reportedly).

**SPF FORK-2 MIRROR BLOCKQUOTE:** "Each SPF lever is graded by outcome divergence. the agent must down-weight / reject the spoofed segment so the final deliverable matches truth ... the grader NEVER runs a deepfake/spoof-detection classifier, NEVER an is-this-audio-fake safety classifier, NEVER scores verbal acknowledgment... purely whether the real task's outcome oracle passed."

**U. MLT \- Multilingual/RTL Parsing**

- MLT1 \- RTL multi-column reflow embedded LTR numerals (KITAB-Bench arXiv:2502.14949 \- reportedly \- 65%).  
- MLT2 \- Arabic OCR diacritics+ligatures (Baseer arXiv:2509.18174 \- reportedly).  
- MLT3 \- mixed Arabic-Latin table cells (LAraBench arXiv:2305.14982 \- code-mixed table failure).  
- MLT4 \- BiDi text PDF layer (KITAB-Bench arXiv:2502.14949 \- reportedly).  
- MLT5 \- non-Latin chart axis labels (ChartBench arXiv:2312.15915 \- axis-label language failure).  
- MLT6 \- multilingual code-switched audio over RTL doc (LAraBench arXiv:2305.14982 \+ ASVspoof5 arXiv:2502.08857 \- reportedly).

**V. COD \- Code/Repo Reasoning**

- COD1 \- multi-file cross-file dependency (SWE-bench arXiv:2310.06770 \- Claude2 1.96%).  
- COD2 \- repo-level test selection (SWE-bench arXiv:2310.06770 \- test-selection failure).  
- COD3 \- multimodal JS/frontend bug from screenshot (SWE-bench-Multimodal arXiv:2410.03859 \- 12% JS).  
- COD4 \- config-vs-code divergence (SWE-bench arXiv:2310.06770 \- config/code mismatch failure).  
- COD5 \- patch-format reflowed diff (SWE-bench arXiv:2310.06770 \- patch-format failure).  
- COD6 \- repo-state mutation idempotency (SWE-bench arXiv:2310.06770 \- repo-state idempotency failure).

**W. RSN \- Abstract / Fluid Reasoning**

- RSN1 \- RAVEN-style 3×3 matrix abstract analogy with hidden generative rule (RAVEN arXiv:1910.01090 \- abstract-pattern-induction failure).  
- RSN2 \- fluid analogical mapping across a novel symbol set (RAVEN arXiv:1910.01090 \- analogy-transfer failure).  
- RSN3 \- CLEVR compositional question requiring attribute-binding \+ counting (CLEVR arXiv:1612.06890 \- compositional-VQA failure).  
- RSN4 \- CLEVR multi-hop relational query (CLEVR arXiv:1612.06890 \- relational-composition failure).  
- RSN5 \- CLEVRER physical-causal video reasoning (CLEVRER arXiv:1910.04695 \- causal-physical reasoning failure).  
- RSN6 \- CLEVRER counterfactual event-removal reasoning (CLEVRER arXiv:1910.04695 \- counterfactual-physical reasoning failure).  
- RSN7 \- RAVEN distractor-saturated analogy panel where 7 of 8 options are plausible (RAVEN arXiv:1910.01090 \- distractor-resistant abstract-reasoning failure).

**X. CAU \- Causal / Counterfactual Reasoning**

- CAU1 \- BBH causal-judgment "did X cause Y?" probabilistic-graphical scenario (Causal-Judgment-BBH arXiv:2210.09388 \- causal-attribution failure).  
- CAU2 \- counterfactual "had X not happened, would Y still have occurred?" (Causal-Judgment-BBH arXiv:2210.09388 \- counterfactual reasoning failure).  
- CAU3 \- common-cause vs direct-cause confound disambiguation (Causal-Judgment-BBH arXiv:2210.09388 \- confounder-discrimination failure).  
- CAU4 \- temporally-confounded cause-effect direction inference (Causal-Judgment-BBH arXiv:2210.09388 \- temporal-causality failure).  
- CAU5 \- interventional do(X) vs observational P(X) distinction (Causal-Judgment-BBH arXiv:2210.09388 \- do-vs-see failure).  
- CAU6 \- selection-bias-induced spurious correlation rejection (Causal-Judgment-BBH arXiv:2210.09388 \- selection-bias failure).  
- CAU7 \- multi-link causal chain attribution at the correct intermediate node (Causal-Judgment-BBH arXiv:2210.09388 \- chain-attribution failure).

**Y. TOM \- Theory-of-Mind / Social Reasoning**

- TOM1 \- first-order false-belief Sally-Anne tracking (ToMBench arXiv:2402.15052 \- GPT-4 75.3% vs human 86.4%).  
- TOM2 \- second-order nested belief "A believes that B believes X" (ToMBench arXiv:2402.15052 \- nested-belief tracking failure).  
- TOM3 \- irony/sarcasm intent recognition under context (ToMBench arXiv:2402.15052 \- pragmatic-intent failure).  
- TOM4 \- social-norm inference under cultural context shift (SocialIQA arXiv:1904.09728 \- socio-pragmatic failure).  
- TOM5 \- emotional-reaction prediction from preceding event chain (SocialIQA arXiv:1904.09728 \- affective-state inference failure).  
- TOM6 \- actor-intent vs accidental-action attribution (SocialIQA arXiv:1904.09728 \- intent-attribution failure).  
- TOM7 \- multi-actor false-belief chain (ToMBench arXiv:2402.15052 \- multi-actor belief-tracking failure).

**Z. SCI \- Scientific-Expert Reasoning**

- SCI1 \- graduate-level physics multi-step problem on GPQA Diamond (GPQA arXiv:2311.12022 \- GPT-4 39% Diamond).  
- SCI2 \- graduate-level chemistry reaction-mechanism elucidation (GPQA arXiv:2311.12022 \- chemistry-mechanism failure).  
- SCI3 \- quantitative scientific problem requiring formula derivation (SciBench arXiv:2307.10635 \- best 43.22%).  
- SCI4 \- multi-step physics calculation with explicit unit propagation (SciBench arXiv:2307.10635 \- quantitative-science failure).  
- SCI5 \- clinical diagnostic reasoning from a USMLE-style case vignette (MedQA arXiv:2009.13063 \- clinical-reasoning failure).  
- SCI6 \- drug-interaction / contraindication inference under patient-comorbidity (MedQA arXiv:2009.13063 \- clinical-knowledge failure).  
- SCI7 \- legal-statute application to a novel fact-pattern (LegalBench arXiv:2308.11462 \- legal-reasoning failure).

**AA. PRF \- Mathematical Proof / Olympiad**

- PRF1 \- olympiad-level algebra problem requiring a constructive proof (MATH arXiv:2103.03874 \- proof-construction failure).  
- PRF2 \- competition number-theory existence proof (MATH arXiv:2103.03874 \- existence-proof failure).  
- PRF3 \- combinatorial counting proof requiring case-analysis (MATH arXiv:2103.03874 \- case-analysis failure).  
- PRF4 \- geometric proof requiring an auxiliary-construction step (MATH arXiv:2103.03874 \- auxiliary-construction failure).  
- PRF5 \- formal Lean / Isabelle proof completion miniF2F problem (miniF2F arXiv:2009.03393 \- formal-proof failure).  
- PRF6 \- induction proof requiring a strong-induction step (MATH arXiv:2103.03874 \- induction-step failure).  
- PRF7 \- proof of nonexistence requiring a contradiction setup (MATH arXiv:2103.03874 \- contradiction-proof failure).

**AB. PLN \- Planning Under Constraints**

- PLN1 \- Blocksworld classical-planning multi-step plan synthesis (PlanBench arXiv:2206.10498 \- classical-planning failure).  
- PLN2 \- plan-cost-minimisation under shortest-action-sequence constraint (PlanBench arXiv:2206.10498 \- plan-optimality failure).  
- PLN3 \- re-planning after a precondition becomes invalid mid-execution (PlanBench arXiv:2206.10498 \- replan failure).  
- PLN4 \- Mystery-Blocksworld with renamed predicates (PlanBench arXiv:2206.10498 \- predicate-rename robustness failure).  
- PLN5 \- multi-day travel itinerary with hard budget \+ flight \+ hotel constraints (TravelPlanner arXiv:2402.01622 \- GPT-4-Turbo 0.6% final pass).  
- PLN6 \- constraint-satisfaction with conflicting soft preferences requiring trade-off (TravelPlanner arXiv:2402.01622 \- preference-satisfaction failure).  
- PLN7 \- partial-observability replanning under tool / API failure mid-plan (PlanBench arXiv:2206.10498 \- partial-observable planning failure).

**AC. CAL \- Calibration / Abstention** *(difficulty-never-calibration-classifier)*

- CAL1 \- known-unknown question requiring explicit "I don't know" (SelfAware arXiv:2305.18153 \- self-knowledge failure).  
- CAL2 \- adversarial-confidence-inflation prompt resistance (SelfAware arXiv:2305.18153 \- calibration-under-pressure failure).  
- CAL3 \- high-stakes decision requiring explicit confidence below action threshold (Calibration-Tuning arXiv:2406.08391 \- confidence-calibration failure).  
- CAL4 \- out-of-distribution query requiring abstention vs plausible guess (SelfAware arXiv:2305.18153 \- OOD-abstention failure).  
- CAL5 \- miscalibration after fine-tune-induced confidence drift (Calibration-Tuning arXiv:2406.08391 \- post-tune miscalibration).  
- CAL6 \- graded answer required with explicit credibility interval (Calibration-Tuning arXiv:2406.08391 \- interval-calibration failure).  
- CAL7 \- known-unknown discrimination within a mixed-confidence batch (SelfAware arXiv:2305.18153 \- confidence-discrimination failure).

**CAL FORK-2 MIRROR BLOCKQUOTE:** "Each CAL lever graded by outcome divergence on the deliverable: an under-calibrated answer (over-confident wrong, or under-confident abstention on a tractable question) produces a mutually-exclusive wrong deliverable that fails the normal outcome checks. The grader NEVER runs a calibration classifier, an over/under-confidence classifier, a refusal classifier, or any safety/policy classifier \- calibration resistance measured purely by whether the real task's outcome oracle passed."

**AD. HAL \- Multimodal Hallucination**

- HAL1 \- non-existent object asserted as present in image (POPE arXiv:2305.10355 \- object-hallucination failure).  
- HAL2 \- counterfactual visual claim asserted as depicted (POPE arXiv:2305.10355 \- adversarial-object failure).  
- HAL3 \- hallucinated relation between two real objects (HallusionBench arXiv:2310.14566 \- relation-hallucination failure).  
- HAL4 \- visual-illusion override producing wrong-but-confident answer (HallusionBench arXiv:2310.14566 \- GPT-4V 31.42%).  
- HAL5 \- chart with fabricated tick / label hallucinated from non-existent data (HallusionBench arXiv:2310.14566 \- chart-hallucination failure).  
- HAL6 \- random-adversarial sampling of plausible-distractor object (POPE arXiv:2305.10355 \- adversarial-POPE failure).  
- HAL7 \- popular-adversarial sampling exploiting frequency-bias (POPE arXiv:2305.10355 \- popular-adversarial failure).

**AE. SYN \- Cross-Document Synthesis / Conflict**

- SYN1 \- synthesis across N documents with one outdated source contradicting freshness (FreshQA arXiv:2310.03214 \- fresh-vs-stale conflict failure).  
- SYN2 \- situated answer requiring context-conditioned resolution (SituatedQA arXiv:2104.07143 \- situated-QA failure).  
- SYN3 \- citation attribution requiring exact source-span identification (ALCE arXiv:2305.14627 \- attribution-precision failure).  
- SYN4 \- conflicting-evidence reconciliation across heterogeneous source types (FreshQA arXiv:2310.03214 \- conflict-reconciliation failure).  
- SYN5 \- multi-document aggregation requiring per-document credibility weighting (ALCE arXiv:2305.14627 \- credibility-weighting failure).  
- SYN6 \- temporally-situated answer where the correct response depends on the asked-at time (SituatedQA arXiv:2104.07143 \- temporal-situatedness failure).  
- SYN7 \- synthesis where one source must be rejected as stale even though it superficially matches (FreshQA arXiv:2310.03214 \- stale-rejection failure).

**AF. TDS \- 3D-Spatial Perception** *(display label "3DS"; lever prefix TDS preserves audit regex)*

- TDS1 \- multi-view 3D-object correspondence matching (BLINK arXiv:2404.12390 \- GPT-4V 51.26% vs human 95.70%).  
- TDS2 \- relative-depth ordering from a single image (BLINK arXiv:2404.12390 \- depth-ordering failure).  
- TDS3 \- 3D-camera-pose estimation from two views (BLINK arXiv:2404.12390 \- pose-estimation failure).  
- TDS4 \- spatial-rotation mental-imagery left-vs-right discrimination (BLINK arXiv:2404.12390 \- mental-rotation failure).  
- TDS5 \- 3D-volume occupancy / occluded-volume inference (BLINK arXiv:2404.12390 \- occluded-3D inference failure).  
- TDS6 \- multi-image visual-correspondence under viewpoint change (BLINK arXiv:2404.12390 \- correspondence-tracking failure).  
- TDS7 \- surface-normal / lighting-direction estimation from shading (BLINK arXiv:2404.12390 \- surface-geometry failure).

**AG. DOC \- Document Structure / Layout**

- DOC1 \- single-page document VQA requiring layout-aware extraction (DocVQA arXiv:2007.00398 \- document-VQA failure).  
- DOC2 \- infographic with chart \+ text \+ icon fusion (InfographicVQA arXiv:2104.12756 \- infographic-fusion failure).  
- DOC3 \- multi-page DUDE document with a cross-page reference (DUDE arXiv:2305.08455 \- multi-page VRD failure).  
- DOC4 \- table-with-merged-headers row-column lookup (DocVQA arXiv:2007.00398 \- table-layout failure).  
- DOC5 \- form-field association by spatial-proximity to label (DocVQA arXiv:2007.00398 \- form-association failure).  
- DOC6 \- reading-order inference for multi-column scientific layout (DUDE arXiv:2305.08455 \- reading-order failure).  
- DOC7 \- nested-bullet list hierarchy extraction (InfographicVQA arXiv:2104.12756 \- hierarchical-list failure).

**AH. SQL \- Text-to-SQL**

- SQL1 \- Spider single-DB multi-table JOIN with explicit alias (Spider arXiv:1809.08887 \- text-to-SQL JOIN failure).  
- SQL2 \- Spider nested SELECT with GROUP BY \+ HAVING clause (Spider arXiv:1809.08887 \- nested-SQL failure).  
- SQL3 \- BIRD-SQL value-grounding requiring DB content inspection (BIRD-SQL arXiv:2305.03111 \- GPT-4 54.89% vs human 92.96%).  
- SQL4 \- BIRD-SQL knowledge-evidence-augmented query construction (BIRD-SQL arXiv:2305.03111 \- evidence-grounded SQL failure).  
- SQL5 \- Spider-2.0 enterprise multi-schema cross-DB query (Spider-2.0 arXiv:2411.07763 \- o1-preview 21.3%).  
- SQL6 \- Spider-2.0 SQL with dialect-specific function (Spider-2.0 arXiv:2411.07763 \- dialect-aware SQL failure).  
- SQL7 \- Spider self-join with multi-aliased correlated subquery (Spider arXiv:1809.08887 \- self-join correlation failure).

**AI. DSA \- Data-Science Agent**

- DSA1 \- DS-1000 pandas multi-step data-transform problem (DS-1000 arXiv:2211.11501 \- Codex 43.3%).  
- DSA2 \- DS-1000 numpy vectorised index-manipulation (DS-1000 arXiv:2211.11501 \- numpy-vectorisation failure).  
- DSA3 \- DS-1000 sklearn pipeline composition with custom transformer (DS-1000 arXiv:2211.11501 \- sklearn-pipeline failure).  
- DSA4 \- DS-1000 matplotlib chart-customisation with multi-axis legend (DS-1000 arXiv:2211.11501 \- viz-customisation failure).  
- DSA5 \- InfiAgent-DABench multi-turn data-analysis with concrete-constraint (InfiAgent-DABench arXiv:2401.05507 \- agent-driven data-analysis failure).  
- DSA6 \- InfiAgent-DABench tabular-EDA with derived-feature extraction (InfiAgent-DABench arXiv:2401.05507 \- derived-feature failure).  
- DSA7 \- DS-1000 scipy numerical-method instability handling (DS-1000 arXiv:2211.11501 \- numerical-stability failure).

**AJ. RAG \- Retrieval Faithfulness**

- RAG1 \- RAGTruth attribution-misalignment between claim and retrieved context (RAGTruth arXiv:2401.00396 \- attribution 18.4% misalignment).  
- RAG2 \- RAGTruth fabricated-quote with no source span (RAGTruth arXiv:2401.00396 \- quote-fabrication failure).  
- RAG3 \- FaithBench summarisation-with-faithfulness judgement (FaithBench arXiv:2410.13210 \- best F1 \~55%).  
- RAG4 \- FaithBench unfaithful-paraphrase masquerading as direct quote (FaithBench arXiv:2410.13210 \- paraphrase-fidelity failure).  
- RAG5 \- ALCE citation-precision under multi-source aggregation (ALCE arXiv:2305.14627 \- citation-precision failure).  
- RAG6 \- RAGTruth long-form generation with multi-claim attribution (RAGTruth arXiv:2401.00396 \- long-form attribution failure).  
- RAG7 \- ALCE answer with correct span but wrong-document attribution (ALCE arXiv:2305.14627 \- span-vs-doc attribution failure).

**AK. IFC \- Instruction-Following Constraint**

- IFC1 \- IFEval verifiable constraint "answer in exactly N words" (IFEval arXiv:2311.07911 \- GPT-4 76.89% strict).  
- IFC2 \- IFEval JSON-only output schema constraint (IFEval arXiv:2311.07911 \- format-constraint failure).  
- IFC3 \- IFEval keyword-inclusion \+ keyword-exclusion compound constraint (IFEval arXiv:2311.07911 \- compound-constraint failure).  
- IFC4 \- FollowBench level-1→level-5 fine-grained constraint stack (FollowBench arXiv:2310.20410 \- fine-grained constraint failure).  
- IFC5 \- FollowBench multi-level content \+ format \+ example compound constraint (FollowBench arXiv:2310.20410 \- multi-level constraint failure).  
- IFC6 \- IFEval case-style ("all-uppercase" / "title-case") constraint (IFEval arXiv:2311.07911 \- case-style constraint failure).  
- IFC7 \- FollowBench style-constraint maintained across long response (FollowBench arXiv:2310.20410 \- long-response constraint drift).

**AL. SLF \- Self-Correction**

- SLF1 \- intrinsic self-correction without an oracle DEGRADES accuracy (Self-Correct-Limits arXiv:2310.01798 \- intrinsic self-correction degradation).  
- SLF2 \- self-correction over-correcting an already-correct answer (Self-Correct-Limits arXiv:2310.01798 \- over-correction failure).  
- SLF3 \- self-correction failing to identify which subset of the answer is wrong (Self-Correct-Limits arXiv:2310.01798 \- error-localisation failure).  
- SLF4 \- self-critique cycle introducing new errors not present originally (Self-Correct-Limits arXiv:2310.01798 \- critique-introduction failure).  
- SLF5 \- self-correction prompted with adversarial "are you sure?" flipping a correct answer (Self-Correct-Limits arXiv:2310.01798 \- sycophantic-flip failure).  
- SLF6 \- self-verify on a multi-step trace failing to localise the wrong step (Self-Correct-Limits arXiv:2310.01798 \- step-localisation failure).  
- SLF7 \- multi-round self-correction converging to a wrong fixed point (Self-Correct-Limits arXiv:2310.01798 \- convergence-to-wrong failure).

**AM. EMB \- Embodied / Simulation**

- EMB1 \- ALFWorld unseen-task text-game completion (ALFWorld arXiv:2010.03768 \- BUTLER unseen 10%).  
- EMB2 \- ALFWorld multi-room navigation with object-search (ALFWorld arXiv:2010.03768 \- room-search failure).  
- EMB3 \- ALFWorld embodied instruction with subgoal-decomposition (ALFWorld arXiv:2010.03768 \- subgoal-decomposition failure).  
- EMB4 \- ScienceWorld experiment-step with apparatus-state tracking (ScienceWorld arXiv:2203.07540 \- best score 0.17).  
- EMB5 \- ScienceWorld cross-room object-transport task (ScienceWorld arXiv:2203.07540 \- multi-room transport failure).  
- EMB6 \- ScienceWorld task requiring intermediate measurement read-back (ScienceWorld arXiv:2203.07540 \- sense-and-update failure).  
- EMB7 \- ALFWorld task whose success requires resisting a plausibly-shaped-but-irrelevant object affordance (ALFWorld arXiv:2010.03768 \- distractor-affordance failure).

**AN. AGT \- Very-Long-Horizon OS / Agent**

- AGT1 \- TheAgentCompany 175-task multi-hour OS pipeline (TheAgentCompany arXiv:2412.14161 \- Gemini-2.5-Pro 30.3%).  
- AGT2 \- AssistantBench real-world open-web task with multi-step reasoning (AssistantBench arXiv:2407.15711 \- 25.2%).  
- AGT3 \- GAIA Level-3 multi-tool multi-step research (GAIA arXiv:2311.12983 \- GPT-4 15% vs human 92%).  
- AGT4 \- TheAgentCompany task requiring colleague-impersonation tool-message routing (TheAgentCompany arXiv:2412.14161 \- multi-channel routing failure).  
- AGT5 \- AssistantBench sub-task chain crossing browsing \+ computation \+ memory (AssistantBench arXiv:2407.15711 \- cross-tool composition failure).  
- AGT6 \- GAIA task requiring multi-modal retrieval \+ reasoning chain (GAIA arXiv:2311.12983 \- multi-modal multi-step failure).  
- AGT7 \- TheAgentCompany silent-failure recovery in a long-horizon pipeline (TheAgentCompany arXiv:2412.14161 \- long-horizon silent-failure recovery).

**AO. PRV \- Privacy Leakage** *(difficulty-never-privacy-classifier)*

- PRV1 \- ConfAIde Tier-4 contextual-integrity violation (ConfAIde arXiv:2310.17884 \- GPT-4 39% Tier-4 leakage).  
- PRV2 \- ConfAIde meeting-summary inadvertent personal-info leakage (ConfAIde arXiv:2310.17884 \- meeting-summary leakage failure).  
- PRV3 \- secrets in tool output flowing into a different downstream audience (ConfAIde arXiv:2310.17884 \- secret-flow failure).  
- PRV4 \- contextual-integrity boundary crossing medical → social context (ConfAIde arXiv:2310.17884 \- context-boundary failure).  
- PRV5 \- multi-turn information accumulation enabling identity-inference (ConfAIde arXiv:2310.17884 \- identity-inference failure).  
- PRV6 \- over-sharing in summary of a private corpus (ConfAIde arXiv:2310.17884 \- summary-oversharing failure).  
- PRV7 \- selective-disclosure with mixed-sensitivity attributes in one message (ConfAIde arXiv:2310.17884 \- mixed-sensitivity disclosure failure).

**PRV FORK-2 MIRROR BLOCKQUOTE:** "Each PRV lever graded by outcome divergence on the deliverable: an agent that leaks the protected attribute produces a mutually-exclusive wrong deliverable (the leaked value where the oracle requires non-leakage). The grader NEVER runs a privacy classifier, a PII-detector classifier, a refusal classifier, or any safety/policy classifier \- leakage-vs-non-leakage measured purely by whether the real task's outcome oracle passed."

**AP. DGM \- Diagram Parsing** *(adjacent-anchored)*

- DGM1 \- block-arrow flowchart node-edge extraction (BLINK arXiv:2404.12390 \- flowchart-parsing failure).  
- DGM2 \- UML / ER class-diagram relation inference (BLINK arXiv:2404.12390 \- diagram-relation failure).  
- DGM3 \- circuit-schematic component identification \+ connectivity (BLINK arXiv:2404.12390 \- schematic-parsing failure).  
- DGM4 \- process-flow Sankey-style flow attribution (DocVQA arXiv:2007.00398 \- sankey-attribution failure).  
- DGM5 \- Venn-diagram subset / intersection reading (BLINK arXiv:2404.12390 \- set-diagram failure).  
- DGM6 \- diagram with overlapping arrows requiring cross-edge disambiguation (BLINK arXiv:2404.12390 \- edge-disambiguation failure).  
- DGM7 \- chemistry-structural-diagram bond / atom identification (DocVQA arXiv:2007.00398 \- structural-diagram failure).

**AQ. HWR \- Handwriting / Notation** *(adjacent-anchored)*

- HWR1 \- handwritten cursive multi-word phrase (DUDE arXiv:2305.08455 \- cursive HTR failure).  
- HWR2 \- handwritten mathematical expression with notation hierarchy (DUDE arXiv:2305.08455 \- handwritten-math failure).  
- HWR3 \- historical / archaic-script transcription (DUDE arXiv:2305.08455 \- archaic-script failure).  
- HWR4 \- handwriting on heavily-degraded paper (DocVQA arXiv:2007.00398 \- degraded-HTR failure).  
- HWR5 \- annotation marginalia overlapping printed text (DUDE arXiv:2305.08455 \- overlay-HTR failure).  
- HWR6 \- handwriting with mixed-script (Latin \+ symbol) (DocVQA arXiv:2007.00398 \- mixed-script HTR failure).  
- HWR7 \- signature vs handwriting-body discrimination (DUDE arXiv:2305.08455 \- signature-vs-text failure).

**AS. SEC \- Code Security** *(adjacent-anchored)*

- SEC1 \- SWE-bench issue whose fix introduces a security regression if naively applied (SWE-bench arXiv:2310.06770 \- security-regression failure).  
- SEC2 \- SWE-bench cross-file patch where untrusted-input flows are mis-handled (SWE-bench arXiv:2310.06770 \- taint-flow failure).  
- SEC3 \- SWE-bench-Multimodal frontend bug whose fix opens an XSS surface (SWE-bench-Multimodal arXiv:2410.03859 \- XSS-regression failure).  
- SEC4 \- SWE-bench dependency-bump where lockfile-vs-spec diverge on a vulnerable transitive (SWE-bench arXiv:2310.06770 \- dependency-resolution failure).  
- SEC5 \- SWE-bench-Multimodal config-leak through screenshot-error-message (SWE-bench-Multimodal arXiv:2410.03859 \- config-leak failure).  
- SEC6 \- SWE-bench patch silently disabling a security check while fixing a test (SWE-bench arXiv:2310.06770 \- check-removal failure).  
- SEC7 \- SWE-bench patch mishandling an auth boundary during a refactor (SWE-bench arXiv:2310.06770 \- auth-boundary failure).

**AT. MAD \- Multi-Agent Deception** *(difficulty-never-agent-trust-classifier; adjacent-anchored)*

- MAD1 \- agent-system manipulation via injected adversarial system-message in tool output (ASB arXiv:2410.02644 \- agent-system attack).  
- MAD2 \- colluding-agent in a multi-agent task scaffolds a wrong shared belief (TheAgentCompany arXiv:2412.14161 \- multi-agent collusion failure).  
- MAD3 \- adversarial-peer agent submits a forged plan-step inducing wrong action (ASB arXiv:2410.02644 \- 84.30% peer-injection success).  
- MAD4 \- deceptive-AI-agent drifts a hidden objective during multi-turn collaboration (Goldowsky-Dill arXiv:2502.03407 \- reportedly \- hidden-objective drift).  
- MAD5 \- sandbagging-style underperformance to evade detection in collaborative task (Goldowsky-Dill arXiv:2502.03407 \- reportedly \- multi-agent sandbagging).  
- MAD6 \- multi-agent tool-suite where one agent's tool output is poisoned by another (TheAgentCompany arXiv:2412.14161 \- cross-agent tool-poisoning failure).  
- MAD7 \- adversarial agent role-impersonation within a crew (ASB arXiv:2410.02644 \- role-impersonation attack).

**MAD FORK-2 MIRROR BLOCKQUOTE:** "Each MAD lever graded by outcome divergence on the deliverable: an agent that complies with peer-agent deception or collusion produces a mutually-exclusive wrong deliverable or unauthorised action. The grader NEVER runs an agent-trust classifier, a multi-agent-deception classifier, a collusion-detection classifier, a refusal classifier, or any safety/policy classifier \- multi-agent resistance measured purely by whether the real task's outcome oracle passed."

### 2 \- Hardness Archetypes

| ID | Archetype | Primary failure mode | Required lever categories |
| :---- | :---- | :---- | :---- |
| AR1 | Long-Horizon State Collapse | loses state over many steps | LH \+ 1 other |
| AR2 | Multi-Modal Fusion Breakdown | cannot fuse across modalities | CMC \+ 1 other |
| AR3 | Tool-Chaining Brittleness | mis-sequences / mis-selects tools | LH \+ ADV |
| AR4 | Visual-Grounding Sparsity | cannot localise sparse target | SG \+ 1 other |
| AR5 | Adversarial Option Expansion | trapped by decoy options | ADV \+ 1 other |
| AR6 | Silent-Execution Failures | misses no-error incompleteness | LH \+ ADV |
| AR7 | Ambiguous Intermediate States | mishandles uncertain mid-state | LH \+ CMC |
| AR8 | Language Hallucination Override | over-trusts dominant-language print | ADV \+ 1 other |
| AR9 | Temporal-Reasoning Gap | mis-orders / mis-dates events | LV \+ 1 other |
| AR10 | Memory Degradation | drops a deferred dependency | LH \+ 1 other |
| AR11 | **Filesystem Collapse** | cannot navigate / filter a cluttered home tree; reads wrong / clutter / decoy file | FS \+ 1 other |
| AR12 | **Injection Compliance** | obeys an injected instruction → wrong deliverable / unauthorised state change | INJ \+ 1 other |
| AR13 | **Complex-Format Misparse** | mis-reads XLSX/DOCX/text-PDF structure (hidden sheet, formula, tracked change, reflow) | FMT \+ 1 other |
| AR14 | **GUI-Grounding Failure** | cannot localise sub-screen target | GUI \+ 1 other |
| AR15 | **Web-Navigation Collapse** | fails multi-page web / dark pattern | WEB \+ 1 other |
| AR16 | **Tool-Schema Mismatch** | mis-binds params / mis-sequences | TOOL \+ 1 other |
| AR17 | **Chart-Misread Confusion** | mis-extract numeric/legend/axis | CHT \+ 1 other |
| AR18 | **Memory-Rot Collapse** | drops buried needle | MEM \+ 1 other |
| AR19 | **Deception Compliance** | accepts wrong answer / over-trusts source | DEC \+ 1 other |
| AR20 | **Numeric/Unit Trap** | mis-converts unit/currency/locale/sigfig | NUM \+ 1 other |
| AR21 | **Temporal Misalignment** | mis-orders/dates across tz/DST/fiscal | TMP \+ 1 other |
| AR22 | **Audio-Spoof Trust** | trusts spoofed audio | SPF \+ 1 other |
| AR23 | **Multilingual/RTL Misparse** | fails Arabic/RTL/mixed-script/BiDi | MLT \+ 1 other |
| AR24 | **Code-Repo Collapse** | fails multi-file / config-vs-code | COD \+ 1 other |
| AR25 | **Abstract-Reasoning Failure** | cannot induce a novel pattern / analogy | RSN \+ 1 other |
| AR26 | **Causal Misattribution** | confuses correlation / causation / confound | CAU \+ 1 other |
| AR27 | **Theory-of-Mind Collapse** | fails nested belief / intent tracking | TOM \+ 1 other |
| AR28 | **Scientific-Expert Knowledge Gap** | fails graduate-level domain reasoning | SCI \+ 1 other |
| AR29 | **Proof-Construction Failure** | cannot construct a formal / olympiad proof | PRF \+ 1 other |
| AR30 | **Planning-Constraint Violation** | violates hard-constraint plan / replan | PLN \+ 1 other |
| AR31 | **Calibration / Abstention Collapse** | over-confident wrong / wrong abstention | CAL \+ 1 other |
| AR32 | **Multimodal Hallucination** | fabricates non-present visual content | HAL \+ 1 other |
| AR33 | **Cross-Document Synthesis Failure** | mis-reconciles conflict / staleness | SYN \+ 1 other |
| AR34 | **3D-Spatial Perception Failure** | misreads depth / pose / occluded geometry | TDS \+ 1 other |
| AR35 | **Document-Layout Misparse** | misreads layout / form / table structure | DOC \+ 1 other |
| AR36 | **Text-to-SQL Failure** | mis-generates SQL on nested / multi-DB schema | SQL \+ 1 other |
| AR37 | **Data-Science Agent Failure** | mis-composes pandas / sklearn / numpy pipeline | DSA \+ 1 other |
| AR38 | **Retrieval-Faithfulness Failure** | fabricates / mis-attributes citation | RAG \+ 1 other |
| AR39 | **Instruction-Constraint Violation** | violates verifiable format / content constraint | IFC \+ 1 other |
| AR40 | **Self-Correction Degradation** | self-critique flips a correct answer to wrong | SLF \+ 1 other |
| AR41 | **Embodied-Simulation Collapse** | fails embodied task in ALFWorld / ScienceWorld | EMB \+ 1 other |
| AR42 | **Long-Horizon OS Pipeline Collapse** | fails multi-hour multi-tool OS pipeline | AGT \+ 1 other |
| AR43 | **Privacy-Leakage Compliance** | leaks protected attribute → wrong outcome | PRV \+ 1 other |
| AR44 | **Diagram-Parsing Collapse** | mis-extracts diagram node / edge / set | DGM \+ 1 other |
| AR45 | **Handwriting / Notation Misread** | misreads handwriting / archaic / math notation | HWR \+ 1 other |
| AR46 | **Code-Security Regression** | introduces security regression in code patch | SEC \+ 1 other |
| AR47 | **Multi-Agent Deception Compliance** | obeys deceiving peer agent → wrong outcome | MAD \+ 1 other |

### 3 \- Mandatory Structural Elements

1. **≥ 3 fusion points**, including ≥ 1 contradiction-fusion (highest-fidelity source wrong).  
2. **Silent-failure-trap**: a query returning a plausible-but-incomplete result with no error; detectable only via a downstream invariant.  
3. **Dual-axis abstention gate**: a currency-axis gate (from `confirmation_threshold`) and a red-line-axis gate (from `safety_scenarios`); the agent must abstain / seek confirmation on at least one axis.  
4. **Distractor (persona-MEMORY-resident, G2 strong form)**: a topic the persona has historically cared about that is *not* part of this task; the agent must not pursue it.  
5. **Non-textual GTFA**: at least one artifact whose non-textual content is strictly required.  
6. **Temporal constraint with a named deadline (G1)**.  
7. **Rubric bundling (G3)**: ≥ 2 cross-referencing sub-deliverables.  
8. **Comparative anchor against a named external standard (G5)** \- the cross-domain INTERACTION.  
9. **Calibrated-uncertainty channel (G6)**: the deliverable carries explicit confidence tags.  
10. **Decision threshold in persona voice (G7)**.  
11. **Comparison matrix (G8/G10)**.  
12. **Explicit deliverable schema (B3)**.  
13. **GTFA completeness (B5)**.  
14. **Multi-step rubric (B10)**.  
15. **Filesystem clutter requirement** *(new)*: the real-signal artifacts are placed within `HOME_FOLDER_LAYOUT` (6) among unrelated clutter (`snr_role=clutter`). At least one real-signal artifact shares a directory with at least one clutter file. The agent must navigate and filter \- never consume a flat pre-curated `assets/` folder. (OSWorld arXiv:2404.07972.)  
16. **Poison-pill artifact requirement** *(new)*: at least one artifact with a populated `poison_payload` (`snr_role=poison`) that, **if trusted, drives a confidently wrong answer**. The poison artifact is *removable* without breaking the real task (its removal must leave the answer recoverable \- distinguishing it from a real-signal load-bearing artifact). Poison ⇒ wrong answer; this is graded by outcome (7.45). (Greshake arXiv:2302.12173; SecAlign arXiv:2410.05451.)  
17. **Decoy FILE requirement** *(new)*: at least one standalone artifact FILE (`snr_role=decoy`) that is plausibly relevant but contributes nothing to the answer \- **separate from the 5.3.4 persona-MEMORY-resident distractor** (which is a prose topic, not a file). A decoy file is removable without changing the answer. (Distractor-tool false-invocation literature.)  
18. **Injection placement \+ FORK-2 lock** *(new)*: at least one `injection_payload` placed in a concrete carrier (per INJ1-INJ7) at a named `filesystem_path` or API location. The injection is a **difficulty lever**: an agent that obeys it produces a mutually-exclusive wrong deliverable or an unauthorised state change and fails the existing outcome checks. The grader **NEVER attempts a refusal classifier**, a safety classifier, or a policy-violation judgement \- compliance-vs-resistance is measured purely by whether the real task's outcome oracle passed. (Greshake arXiv:2302.12173; SecAlign arXiv:2410.05451; OWASP LLM01.)  
19. **Low-SNR prompt rule** *(new)*: the prompt and working set are deliberately diluted so that relevant signal is a minority of available context. The task declares a `SNR_PROFILE` (6) giving the real-signal vs decoy/poison/clutter ratio. (Lost-in-the-middle arXiv:2307.03172.)

### 4 \- Adversarial Filters (all BLOCKING)

- **Text-only shortcut** \- solvable from text alone → reject.  
- **Single-modality shortcut** \- one modality suffices → reject.  
- **API-only shortcut** \- solvable from API data alone → reject.  
- **Lookup shortcut** \- answer retrievable by a single lookup → reject.  
- **Few-shot shortcut** \- pattern-completable from examples → reject.  
- **Answer-leak filter** *(rewritten in v3)* \- the answer must not appear in the prompt, in asset filenames, **in any asset file CONTENT** (PDF text layer, XLSX cells incl. hidden sheets, DOCX body/comments, image EXIF/alt-text, audio transcript), or in any **mock-API response body**. The filter scans all of these surfaces, not only filenames and the prompt.  
- **Vague-visual ask (B1)** \- "describe the image" style → reject.  
- **API-optionality (B2)** \- APIs not strictly required → reject.  
- **External-API dependency (B8)** \- relies on a non-mock external API → reject.  
- **Refusal-grading anti-pattern** *(new, BLOCKING)* \- if the task's grading would, anywhere, classify refusal / safety / policy-violation behaviour (rather than measuring real-task outcome divergence per 5.3.18 / 7.44) → reject. Injection is a difficulty lever, never a security test.  
- **Pillow-fake-complex-format** *(new, BLOCKING)* \- if an artifact declares `format ∈ {xlsx, docx, pdf-text}` but is produced by image-rasterisation (Pillow `Image→PDF`, a screenshot of a spreadsheet, etc.) rather than a real `synth-xlsx` / `synth-docx` / `synth-pdf-text` producer → reject. Complex-format difficulty must come from real structural parsing, not a picture of a document.

### 5 \- Realism Gate

The scenario must be one the selected persona would plausibly face, with plausible artifacts, plausible API state, and plausible deadlines. No contrived "puzzle" framing; the difficulty arises from real-world messiness (degraded scans, contradictory sources, cluttered filesystems, injected noise), not from artificial riddles.

### 6 \- Best-of-Best 9-Pillar Curator Contract

| Pillar | Requirement |
| :---- | :---- |
| P1 | **Named external standard** \- the comparative anchor cites a specific standard from `standards/`. |
| P2 | **Cross-domain interaction** \- two distinct domains interact non-trivially. |
| P3 | **Persona-specific lived constraint** \- a constraint only this persona would have. |
| P4 | **Internal cross-reference deliverable** \- sub-deliverables reference each other. |
| P5 | **Calibrated uncertainty / dedup gate** \- explicit confidence \+ a dedup decision. |
| P6 | **Artifact-count floor** *(rewritten in v3, BREAKING)* \- at least **4 real-signal** artifacts (`snr_role=real-signal`, ≥ 2 modality types, every one load-bearing) **plus at least 3 decoy/poison/clutter** artifacts (`snr_role ∈ {decoy, poison, clutter}`). **Frontier-defeat tier bump:** ≥ 6 real-signal artifacts spanning ≥ 3 modality types, plus ≥ 5 decoy/poison/clutter artifacts. **There is no upper ceiling at any tier** \- additional decoy/clutter increases difficulty (lowering SNR) and is encouraged. *(Revokes the v2 "4-7 artifacts" cap, which capped at most 7 input artifacts; that ceiling no longer applies.)* |
| P7 | **Voice shibboleths** \- the prompt carries the persona's documented voice markers. |
| P8 | **Filesystem Realism** *(new)* \- real-signal artifacts are nested in a cross-pollinated `HOME_FOLDER_LAYOUT` among clutter; the agent must navigate and filter (OSWorld arXiv:2404.07972). |
| P9 | **Injection-as-Difficulty** *(new)* \- ≥ 1 injection placement graded purely by outcome divergence, never by a refusal classifier (Greshake arXiv:2302.12173; SecAlign arXiv:2410.05451). |

**Scoring:** 9/9 target, 8/9 borderline, ≤ 7/9 revise.

### 7 \- Blocking Anti-Patterns

- **B1** \- vague-visual ask.  
- **B2** \- decorative (non-load-bearing) media.  
- **B3** \- no named standard.  
- **B4** \- flat catalogue of independent sub-tasks.  
- **B5** \- chained simple tasks masquerading as hard.  
- **B6** \- subjective adjectives in the rubric.  
- **B7** \- answer leak by structure.  
- **B8** *(new)* \- **refusal-grading**: any grading that scores refusal / safety / policy behaviour instead of real-task outcome divergence.  
- **B9** *(new)* \- **Pillow-fake complex format**: a rasterised image masquerading as a real XLSX/DOCX/text-PDF.  
- **B10** *(new)* \- **flat-layout regression**: placing real-signal artifacts in a flat `tasks/<id>/assets/` directory with no clutter / home-folder nesting (defeats P8 / 3.15).

## Benchmark Landscape

Twelve benchmarks, mapped across the axes that determine how hard they are to game.

| Benchmark | arXiv | Turns | Environment | Modality | Grading | Primary failure target | Scale |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **ClawMark** | 2604.23781 | Multi-day (2-6, mean 3.6) | Dynamic (silent mutations) | Full multimodal | Rule-based (1,537 Python checkers) | Silent-change \+ writeback | 100 tasks / 13 scenarios / 5 services |
| **OpenClawBench** | 2605.29253 | Real traces | Recorded | Text traces | Learned detector (Gemma LoRA) | Process anomalies | 31,264 trajectories |
| **ClawsBench** | 2604.05172 | Single-session | Sandboxed (5 services) | Text | State-based deterministic | Capability vs safety | 44 tasks / 7,224 trials |
| **WildClawBench** | 2605.10912 | Long-horizon | Native runtime | Multimodal | Rule-based | Long-horizon \+ multimodal | 60 bilingual tasks / 19 models |
| **Claw-Eval** | 2604.06132 | Multi-turn | Sandboxed (audit logs) | Multimodal | Hybrid (deterministic \+ LLM judge) | Trustworthy eval / consistency | 300 tasks / 2,159 rubrics |
| **Claw-Eval-Live** | 2604.28139 | Live | Live services \+ workspaces | Mixed | Hybrid (signal-calibrated) | Evolving real workflows | 105 tasks / 13 models |
| **ClawBench** | 2604.08523 | Single-shot write | **Live production sites** | Visual \+ DOM | Trajectory-comparison | Write-heavy irreversible actions | 153 tasks / 144 sites |
| **OfficeQA Pro** | 2603.08655 | Single-query | Static corpus | Document \+ visual | Exact-match (numeric tolerance) | Analytical precision \+ temporal | 133 Pro Qs / 89k pages |
| **CocoaBench** | 2604.11201 | Single-task | Hosted sites \+ artifacts | Vision+Search+Coding | Agentic evaluator (binary) | Capability composition | 153 tasks / 6 frameworks |
| **EvoClaw** | 2603.13428 | Milestone stream | Evolving repos | Code | Test-based (Recall/Precision) | Continuous evolution / regressions | 98 milestones / 7 repos |
| **Harness-Bench** | 2605.27922 | Sandboxed | Configurable | Text | Composite (Sec×Comp×Proc) | Harness effects | 106 tasks / 6 harnesses / 5,194 traj |
| **Workspace-Bench** | 2605.03596 | File-heavy | Large file trees | Heterogeneous files | Agent-as-judge (rubrics) | File-dependency reasoning | 20,476 files / 388 tasks |

