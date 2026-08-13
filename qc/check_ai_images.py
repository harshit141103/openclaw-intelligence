#!/usr/bin/env python3
"""
QC checker for AI-generated and stock images in task input data.
v2.0 — Extended detection vectors.

Detection coverage (14 vectors):
  1.  EXIF metadata AI tool tokens (70+ generators incl. 2024-2026)
  2.  PNG tEXt/iTXt generation parameter keys (SD/ComfyUI/InvokeAI)
  3.  XMP metadata parsing (CreatorTool, DigitalSourceType, generator tags)
  4.  IPTC DigitalSourceType (trainedAlgorithmicMedia, composites)
  5.  Filename AI/stock signatures (40+ patterns)
  6.  Stock photo watermark signatures in all metadata layers
  7.  C2PA/CAI manifest byte markers (elevated to major_issue in 2026)
  8.  EXIF Make/Model absence on JPEG (camera fingerprint gap)
  9.  EXIF Software tag analysis (AI tools + image editors)
  10. Known AI output dimensions (1024x1024, SDXL, DALL-E, Flux sizes)
  11. DPI anomaly detection (72 DPI without camera metadata)
  12. File compression ratio analysis
  13. Animated GIF rejection
  14. EXIF date vs persona timeline window

Known limitations (documented, not solvable locally):
  - SynthID pixel watermarks require Google's proprietary API
  - Frequency-domain / PRNU analysis requires numpy + reference DB
  - Metadata can be stripped by any editor; dimension check is the
    only signal that survives total metadata stripping

Exit codes:
    0  PASS — no FAIL findings
    1  FAIL — at least one finding
    2  ERROR — bad arguments, missing directory, or missing Pillow

Requires: pip install Pillow
Optional: pip install pillow-heif  (for HEIC/HEIF support)
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import date, datetime
from typing import Iterable

try:
    from PIL import ExifTags, Image, IptcImagePlugin, UnidentifiedImageError
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow", file=sys.stderr)
    sys.exit(2)

# Try to register HEIF/HEIC support if available
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

__version__ = "2.0.0"

# ---------------------------------------------------------------------------
# Detection token dictionaries
# ---------------------------------------------------------------------------

AI_TOKENS = (
    # ── Stable Diffusion / open-source family ──
    "stable diffusion", "stable-diffusion", "sdxl", "sd-xl",
    "sd 1.5", "sd1.5", "sd 2.1", "sd2.1", "sd 3", "sd3",
    "automatic1111", "auto1111", "a1111",
    "comfyui", "comfy ui",
    "invokeai", "invoke ai",
    "fooocus",
    # ── Midjourney ──
    "midjourney", "mj v", " mj ",
    # ── OpenAI ──
    "dall-e", "dall\u00b7e", "dalle", "dall_e",
    "chatgpt", "openai",
    "gpt-image", "gpt image", "gpt-image-1", "gpt_image",
    "gpt-4o", "gpt4o",
    # ── Adobe ──
    "firefly", "adobe firefly",
    # ── Google ──
    "imagen", "imagen 2", "imagen2", "imagen 3", "imagen3",
    "gemini", "google ai", "google generative ai", "google deepmind",
    "image fx", "imagefx",
    "synthid",
    "sora",
    # ── Meta ──
    "meta ai", "meta imagine", "emu edit", "emu video",
    # ── xAI ──
    "grok",
    # ── Microsoft ──
    "bing image creator", "microsoft designer", "copilot image",
    # ── Apple ──
    "apple intelligence", "image playground",
    # ── Other commercial ──
    "leonardo.ai", "leonardo ai",
    "ideogram",
    "recraft",
    "canva ai", "magic media",
    "jasper art",
    "craiyon",
    # ── Open-source / community ──
    "flux.1", "flux 1", "flux1", "black forest labs", "bfl",
    "playground v",
    "nightcafe", "starryai", "wombo",
    "novelai",
    "stability.ai", "stabilityai", "stability ai",
    "runway gen", "runwayml",
    "kling ai", "luma dream", "luma labs",
    "tensor.art", "civitai",
    "pixart",
)

# Tokens meaningful only inside XMP / IPTC (too generic for filenames)
XMP_AI_TOKENS = (
    "trainedalgorithmicmedia",
    "compositewithtrainedalgorithmicmedia",
    "algorithmicmedia",
    "digitalcreation",
    "c2pa.created",
)

PNG_AI_TEXT_KEYS = (
    "parameters",
    "prompt", "negative_prompt", "negativeprompt",
    "sd-metadata", "sd_metadata",
    "comfyui", "workflow",
    "generation_data", "generation-data",
    "invokeai_metadata", "invokeai-metadata",
    "automatic1111",
    "dream",
)

FILENAME_TELLS = (
    # OpenAI
    "chatgpt image", "chatgpt_image", "chatgpt-image",
    "dall\u00b7e", "dalle_", "dalle-", "dall-e", "dall_e",
    "gpt-image", "gpt_image",
    # Stable Diffusion
    "_xl_lightning", "_sdxl_", "_sd_", "_sd15_",
    "stable_diffusion", "stable-diffusion",
    # Midjourney
    "midjourney_", "_mj_", "mj_v",
    # Adobe
    "firefly_", "adobe_firefly",
    # Google
    "imagen_", "gemini_", "imagefx_",
    # Flux
    "flux_",
    # Other tools
    "ideogram_", "recraft_", "leonardo_",
    "canva_ai", "craiyon_", "copilot_image",
    # Generic AI patterns
    "generated_image", "ai_generated", "ai-generated", "ai_image",
)

STOCK_TOKENS = (
    "shutterstock", "getty images", "getty image",
    "istock", "istockphoto",
    "alamy", "dreamstime", "depositphotos",
    "123rf", "adobe stock", "adobestock",
    "unsplash", "pexels", "pixabay",
)

# Image editors — informational, indicates possible manipulation
EDITOR_TOKENS = (
    "photoshop", "gimp", "affinity photo", "paint.net",
    "pixelmator", "krita", "corel paintshop",
)

# C2PA / CAI manifest markers (JUMBF box signatures)
C2PA_MARKERS = (b"jumb\x00c2pa", b"jumb\x00caim", b"jumd\x00cacb")

# Known AI output dimensions — no real camera sensor outputs these
AI_DIMENSIONS: set[tuple[int, int]] = {
    # Perfect squares
    (256, 256), (512, 512), (768, 768), (1024, 1024), (2048, 2048),
    # DALL-E 3
    (1024, 1792), (1792, 1024),
    # SDXL
    (1344, 768), (768, 1344),
    (1152, 896), (896, 1152),
    (1216, 832), (832, 1216),
    (896, 896),
    # Flux
    (1024, 1536), (1536, 1024),
    # SD 1.5
    (512, 768), (768, 512),
    # Older models
    (256, 384), (384, 256),
}

# Supported image file extensions
IMG_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".heic", ".heif", ".avif",
    ".tiff", ".tif", ".bmp",
}


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def load_image_safely(path: pathlib.Path):
    try:
        return Image.open(path), None
    except UnidentifiedImageError as e:
        return None, f"unreadable image: {e}"
    except Exception as e:  # noqa: BLE001
        return None, f"open error: {e}"


def exif_haystack(img) -> dict[str, str]:
    """Extract all EXIF tags as {lowercase_name: lowercase_value}."""
    try:
        raw = img.getexif() or {}
    except Exception:  # noqa: BLE001
        return {}
    out: dict[str, str] = {}
    for tag_id, value in raw.items():
        name = ExifTags.TAGS.get(tag_id, f"tag_{tag_id}")
        out[str(name).lower()] = str(value).lower()
    return out


def png_text_haystack(img) -> dict[str, str]:
    """Extract PNG tEXt / iTXt / zTXt chunks."""
    if img.format != "PNG":
        return {}
    return {str(k).lower(): str(v).lower() for k, v in (img.info or {}).items()}


def xmp_haystack(img) -> str:
    """Extract XMP metadata as a single lowercase string.

    Handles JPEG (img.info['xmp']), PNG (iTXt 'XML:com.adobe.xmp'),
    WebP (img.info['xmp']), and TIFF (tag 700).
    """
    xmp_bytes = b""

    # JPEG / WebP: stored in img.info["xmp"]
    raw = (img.info or {}).get("xmp")
    if isinstance(raw, bytes):
        xmp_bytes = raw
    elif isinstance(raw, str):
        xmp_bytes = raw.encode("utf-8", errors="ignore")

    # PNG: might be in iTXt key "XML:com.adobe.xmp"
    if not xmp_bytes and img.format == "PNG":
        for key in ("XML:com.adobe.xmp", "xml:com.adobe.xmp"):
            val = (img.info or {}).get(key)
            if val:
                if isinstance(val, bytes):
                    xmp_bytes = val
                else:
                    xmp_bytes = str(val).encode("utf-8", errors="ignore")
                break

    # TIFF: tag 700 is XMP
    if not xmp_bytes and img.format == "TIFF":
        try:
            td = img.tag_v2.get(700)
            if isinstance(td, bytes):
                xmp_bytes = td
        except Exception:  # noqa: BLE001
            pass

    return xmp_bytes.decode("utf-8", errors="ignore").lower() if xmp_bytes else ""


def find_tokens(haystack: str, tokens: Iterable[str]) -> list[str]:
    """Return all tokens that appear as substrings of haystack."""
    return [t for t in tokens if t in haystack]


def c2pa_present(path: pathlib.Path) -> bool:
    """Check first 64 KB of file for C2PA JUMBF box markers."""
    try:
        head = path.read_bytes()[:65536]
    except Exception:  # noqa: BLE001
        return False
    return any(m in head for m in C2PA_MARKERS)


def parse_date(s: str) -> date | None:
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y:%m:%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def parse_window(s: str) -> tuple[date, date]:
    try:
        a, b = s.split(":", 1)
        return (datetime.strptime(a, "%Y-%m-%d").date(),
                datetime.strptime(b, "%Y-%m-%d").date())
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"--persona-window must be YYYY-MM-DD:YYYY-MM-DD ({e})"
        ) from e


# ---------------------------------------------------------------------------
# Core per-file check
# ---------------------------------------------------------------------------

def check_file(path: pathlib.Path,
               window: tuple[date, date] | None) -> dict:
    result: dict = {
        "file": str(path),
        "fails": [],
        "major_issues": [],
        "minor_issues": [],
        "info": [],
    }

    name = path.name.lower()

    # ── 1. Filename AI signatures ──────────────────────────────────────────
    for t in find_tokens(name, FILENAME_TELLS):
        result["fails"].append(f"filename AI signature: {t!r}")

    # ── 2. Load image ──────────────────────────────────────────────────────
    img, err = load_image_safely(path)
    if err:
        result["fails"].append(err)
        return result

    w, h = img.size

    # ── 3. Animated GIF ────────────────────────────────────────────────────
    if img.format == "GIF":
        try:
            n = getattr(img, "n_frames", 1)
        except Exception:  # noqa: BLE001
            n = 1
        if n > 1:
            result["fails"].append(f"animated GIF rejected (n_frames={n})")

    # ── 4. EXIF AI tokens ─────────────────────────────────────────────────
    exif = exif_haystack(img)
    exif_blob = " ".join(exif.values())
    for t in find_tokens(exif_blob, AI_TOKENS):
        result["fails"].append(f"EXIF AI token: {t!r}")

    has_make = "make" in exif
    has_model = "model" in exif

    # ── 5. EXIF Make/Model absence (camera fingerprint gap) ────────────────
    if exif and img.format in ("JPEG", "TIFF", "HEIC", "HEIF"):
        if not has_make and not has_model:
            result["major_issues"].append(
                "EXIF present but no camera Make/Model "
                "(possible synthetic or editor-injected metadata)"
            )

    # ── 6. EXIF Software tag ──────────────────────────────────────────────
    software = exif.get("software", "")
    if software:
        for t in find_tokens(software, AI_TOKENS):
            result["fails"].append(f"EXIF Software identifies AI tool: {t!r}")
        for t in find_tokens(software, EDITOR_TOKENS):
            result["info"].append(f"EXIF Software: image editor {t!r}")

    # ── 7. PNG metadata ───────────────────────────────────────────────────
    png_meta = png_text_haystack(img)
    for k in PNG_AI_TEXT_KEYS:
        if k in png_meta:
            result["fails"].append(
                f"PNG tEXt key {k!r} present "
                f"(SD/ComfyUI/InvokeAI fingerprint)"
            )
    png_blob = " ".join(png_meta.values())
    for t in find_tokens(png_blob, AI_TOKENS):
        result["fails"].append(f"PNG metadata AI token: {t!r}")

    # ── 8. Stock signatures (EXIF + PNG + filename) ────────────────────────
    all_meta = exif_blob + " " + png_blob + " " + name
    for t in find_tokens(all_meta, STOCK_TOKENS):
        result["fails"].append(f"stock-photo signature: {t!r}")

    # ── 9. XMP metadata ───────────────────────────────────────────────────
    xmp = xmp_haystack(img)
    if xmp:
        for t in find_tokens(xmp, AI_TOKENS):
            result["fails"].append(f"XMP AI token: {t!r}")
        for t in find_tokens(xmp, XMP_AI_TOKENS):
            result["fails"].append(f"XMP AI provenance marker: {t!r}")
        for t in find_tokens(xmp, STOCK_TOKENS):
            result["fails"].append(f"XMP stock signature: {t!r}")
        result["info"].append("XMP metadata present")

    # ── 10. IPTC DigitalSourceType ────────────────────────────────────────
    # Primary location: XMP  (Iptc4xmpExt:DigitalSourceType)
    if xmp and "digitalsourcetype" in xmp:
        if "trainedalgorithmicmedia" in xmp:
            result["fails"].append(
                "IPTC DigitalSourceType=trainedAlgorithmicMedia "
                "(declared AI-generated)"
            )
        elif "compositewithtrainedalgorithmicmedia" in xmp:
            result["fails"].append(
                "IPTC DigitalSourceType="
                "compositeWithTrainedAlgorithmicMedia (AI-edited)"
            )

    # Fallback: legacy IPTC-IIM block
    try:
        iptc_data = IptcImagePlugin.getiptcinfo(img)
        if iptc_data:
            parts: list[str] = []
            for v in iptc_data.values():
                if isinstance(v, bytes):
                    parts.append(v.decode("utf-8", errors="ignore").lower())
                elif isinstance(v, (list, tuple)):
                    for item in v:
                        if isinstance(item, bytes):
                            parts.append(
                                item.decode("utf-8", errors="ignore").lower()
                            )
                        else:
                            parts.append(str(item).lower())
                else:
                    parts.append(str(v).lower())
            iptc_blob = " ".join(parts)
            for t in find_tokens(iptc_blob, AI_TOKENS):
                result["fails"].append(f"IPTC AI token: {t!r}")
    except Exception:  # noqa: BLE001
        pass

    # ── 11. Dimension check ───────────────────────────────────────────────
    if (w, h) in AI_DIMENSIONS:
        result["major_issues"].append(
            f"dimensions {w}\u00d7{h} match known AI output size"
        )
    elif w == h and w >= 256 and w % 64 == 0:
        result["major_issues"].append(
            f"perfect-square {w}\u00d7{h} at multiple of 64 "
            f"(no camera sensor outputs square images)"
        )
    elif (w % 64 == 0 and h % 64 == 0
          and 256 <= w <= 2048 and 256 <= h <= 2048
          and not has_make and not has_model):
        result["minor_issues"].append(
            f"dimensions {w}\u00d7{h} both multiples of 64, "
            f"no camera metadata"
        )

    # ── 12. DPI anomaly ───────────────────────────────────────────────────
    dpi = (img.info or {}).get("dpi")
    if dpi and img.format in ("JPEG", "TIFF", "HEIC", "HEIF"):
        try:
            x_dpi = round(float(dpi[0]))
            y_dpi = round(float(dpi[1]))
            if x_dpi == 72 and y_dpi == 72 and not has_make:
                result["minor_issues"].append(
                    "72 DPI without camera Make "
                    "(default for AI/web, unusual for cameras)"
                )
        except (TypeError, ValueError, IndexError):
            pass

    # ── 13. JPEG compression ratio ────────────────────────────────────────
    try:
        file_bytes = path.stat().st_size
        pixels = w * h
        if pixels >= 262144 and img.format == "JPEG":
            bpp = file_bytes / pixels
            if bpp < 0.3:
                result["fails"].append(
                    f"very low JPEG ratio ({bpp:.2f} B/px) "
                    f"-- possible AI output or heavy recompression"
                )
    except Exception:  # noqa: BLE001
        pass

    # ── 14. EXIF date vs persona window ───────────────────────────────────
    if window:
        dt_raw = exif.get("datetimeoriginal") or exif.get("datetime")
        if dt_raw:
            d = parse_date(dt_raw)
            if d is None:
                result["minor_issues"].append(
                    f"unparseable EXIF date: {dt_raw!r}"
                )
            elif not (window[0] <= d <= window[1]):
                result["fails"].append(
                    f"EXIF date {d.isoformat()} outside persona window "
                    f"{window[0].isoformat()}\u2013{window[1].isoformat()}"
                )

    # ── Missing EXIF on photo format ──────────────────────────────────────
    if not exif and img.format in ("JPEG", "HEIC", "HEIF"):
        result["minor_issues"].append(
            "no EXIF on JPEG/HEIC "
            "(stripped, screenshotted, or AI-generated)"
        )

    # ── C2PA manifest ─────────────────────────────────────────────────────
    if c2pa_present(path):
        result["major_issues"].append(
            "C2PA manifest detected -- review issuer "
            "(AI tools sign C2PA: Adobe Firefly, OpenAI, Google; "
            "cameras: Sony, Leica, iPhone 15+)"
        )

    # ── Deduplicate findings within each severity ─────────────────────────
    for key in ("fails", "major_issues", "minor_issues", "info"):
        result[key] = list(dict.fromkeys(result[key]))

    return result


# ---------------------------------------------------------------------------
# Iteration + CLI
# ---------------------------------------------------------------------------

def iter_images(root: pathlib.Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMG_EXT:
            yield p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="QC checker for AI-generated and stock images (v2.0).",
    )
    ap.add_argument(
        "data_dir",
        help="Directory to scan recursively for image files.",
    )
    ap.add_argument(
        "--persona-window",
        type=parse_window,
        metavar="YYYY-MM-DD:YYYY-MM-DD",
        help="Persona timeline window.  EXIF dates outside this range FAIL.",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Emit only the JSON report on stdout (suppress human summary).",
    )
    ap.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    args = ap.parse_args(argv)

    root = pathlib.Path(args.data_dir)
    if not root.exists():
        print(f"ERROR: directory not found: {root}", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 2

    files = list(iter_images(root))
    reports = [check_file(p, args.persona_window) for p in files]

    summary = {
        "checked": len(files),
        "files_with_fails": sum(1 for r in reports if r["fails"]),
        "total_fails": sum(len(r["fails"]) for r in reports),
        "files_with_major": sum(1 for r in reports if r["major_issues"]),
        "files_with_minor": sum(1 for r in reports if r["minor_issues"]),
        "persona_window": (
            f"{args.persona_window[0].isoformat()}:"
            f"{args.persona_window[1].isoformat()}"
            if args.persona_window else None
        ),
        "version": __version__,
    }

    print(json.dumps({"summary": summary, "reports": reports}, indent=2))

    if not args.json:
        print(file=sys.stderr)
        print(
            f"Scanned {summary['checked']} image(s) under {root}",
            file=sys.stderr,
        )
        if summary["total_fails"]:
            print(
                f"FAIL: {summary['total_fails']} finding(s) "
                f"across {summary['files_with_fails']} file(s)",
                file=sys.stderr,
            )
            for r in reports:
                if r["fails"]:
                    print(f"  {r['file']}", file=sys.stderr)
                    for f in r["fails"]:
                        print(f"    X {f}", file=sys.stderr)
        else:
            print(
                "PASS: no AI / stock / animated-GIF / "
                "out-of-window findings.",
                file=sys.stderr,
            )
        if summary["files_with_major"]:
            print(
                f"WARNING: {summary['files_with_major']} file(s) with "
                f"major issues (review recommended):",
                file=sys.stderr,
            )
            for r in reports:
                if r["major_issues"]:
                    print(f"  {r['file']}", file=sys.stderr)
                    for m in r["major_issues"]:
                        print(f"    > {m}", file=sys.stderr)
        if summary["files_with_minor"]:
            print(
                f"NOTE: {summary['files_with_minor']} file(s) with "
                f"minor notes.",
                file=sys.stderr,
            )

    return 1 if summary["total_fails"] else 0


if __name__ == "__main__":
    sys.exit(main())
