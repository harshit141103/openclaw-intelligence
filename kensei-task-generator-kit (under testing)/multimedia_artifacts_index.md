# Multimedia Artifacts Archive: What It Has and What It Does Not

The kit assumes you have a multimedia archive mounted on disk at an operator-chosen root. The archive is ~3.2 GB and is NOT bundled in this kit; you pass its path via `--add-dir` when invoking the generator (see README section 1). Throughout this document, the placeholder `<multimedia_artifacts_root>/` stands for that path:

```
<multimedia_artifacts_root>/
```

## What the archive contains

```
multimedia-artifacts/
├── docx/2026-05-28_round1/   # ~311 DOCX files, hex-named, mixed real-world content
├── pptx/2026-05-28_round1/   # ~393 PPTX files, hex-named
├── xlsx/2026-05-28_round1/   # ~485 XLSX files, hex-named
└── README.md                 # single line, no documentation
```

Total: roughly 1,189 office documents. Filenames are MD5-like 16-character or 32-character hex strings, not human-readable. You inspect the content to find structural fits for your tasks.

## What the archive does NOT contain

- No images (JPG, PNG, HEIC, WEBP, GIF)
- No audio (MP3, M4A, WAV, AAC, OGG)
- No video (MP4, MOV, AVI, WEBM)
- No PDFs at the top level
- No archive metadata or content index

Anything in the missing categories MUST come from either the persona's own `home/` tree, or from web scraping (Stage 3).

## How the master generator prompt uses the archive

Stage 2 of the three-stage multimodal acquisition pipeline. Sequence:

1. Persona's `home/` first (Stage 1). Most authentic.
2. If still missing artifacts AND the need is for DOCX, PPTX, or XLSX, browse this archive (Stage 2).
3. For everything else, or if the archive does not contain a structural fit, web scrape (Stage 3).

## How to choose from the archive

Browse `docx/2026-05-28_round1/` and open files in batches. Look for ones whose internal structure (sections, headers, tables, embedded charts) match what your task needs. Then surgically rewrite line items, cell values, header rows, or paragraph text to fit the scenario.

DO NOT regenerate the file. DO NOT use a model to write a new file from scratch. The layout, the embedded styles, the watermark or header artifacts, and the document quirks must come from the real file. Only the LITERAL CONTENT inside the document changes.

Record every use in the task's `home/_provenance.json` with `stage: multimedia_archive`, the source path in this archive, and a note describing what was rewritten.

## Provenance integrity

If you copy a file verbatim from the archive without modification, mark it `note: "copied verbatim"`. If you rewrite content but preserve structure, name the specific edits (`note: "header preserved, all five line items rewritten with Clearwater budget figures, total cell deliberately blanked"`).

This kit treats provenance as a first-class deliverable. The downstream STANDALONE generators do not read `_provenance.json`, but human reviewers and the data-quality team do.
