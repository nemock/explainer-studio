#!/usr/bin/env python3
"""Downscale rendered stills/frames to small JPEG previews for visual QA.

Why this exists (2026-08-25): Reading a full-res render (a 1920x1080 PNG is
often 1-3 MB) into a Claude session embeds it as base64 in the session
transcript. Over a long run those Reads dominated transcripts (85% of a
172 MB session file) and ballooned the desktop app past 13 GB RAM. So the
standing rule (SKILL.md hard rule 9): verification Reads go through this
helper -- Read the preview JPEG it writes, never the full-res PNG. Full-res
files are for the actual video pipeline only.

Usage (absolute paths; flat args -- permission-matcher friendly):
    python3 tools/frame_preview.py <image> [<image> ...]
    python3 tools/frame_preview.py <image> --out-dir /abs/dir --max 800

Writes <out-dir>/<stem>_preview.jpg (default out-dir: previews/ beside each
source) and prints one preview path per line -- Read those paths.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

DEFAULT_MAX = 800
JPEG_QUALITY = 80


def make_preview(src: Path, out_dir: Path | None, max_dim: int) -> Path:
    dest_dir = out_dir if out_dir else src.parent / "previews"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{src.stem}_preview.jpg"

    im = Image.open(src)
    im.thumbnail((max_dim, max_dim), Image.LANCZOS)
    if im.mode in ("RGBA", "LA", "P"):
        # JPEG has no alpha; composite onto white so cutouts stay judgeable.
        background = Image.new("RGB", im.size, (255, 255, 255))
        background.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
        im = background
    elif im.mode != "RGB":
        im = im.convert("RGB")
    im.save(dest, "JPEG", quality=JPEG_QUALITY)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("images", nargs="+", help="source image(s), absolute paths")
    parser.add_argument("--out-dir", help="directory for previews (default: previews/ beside each source)")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX, help=f"max dimension in px (default {DEFAULT_MAX})")
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else None
    failed = False
    for name in args.images:
        src = Path(name)
        if not src.is_file():
            print(f"MISSING: {src}", file=sys.stderr)
            failed = True
            continue
        print(make_preview(src, out_dir, args.max))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
