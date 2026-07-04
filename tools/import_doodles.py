#!/usr/bin/env python3
"""Import the operator's CopyDoodles library into the motion engine's doodle set.

CopyDoodles (Persistent Marketing, Inc. — operator-purchased, royalty-free EULA) are
Sharpie-drawn-and-scanned annotation graphics: arrows, ovals, boxes, crossouts,
underline scribbles, brackets, stars. They complement the procedural rough.js
annotations (Annotate.tsx): doodles are authentic hand-drawn STAMPS; rough.js draws
precise point-to-point geometry. Both render in the same annotation overlay.

What this script does per image:
  1. combined alpha = existing_alpha x ink_darkness (kills any white background,
     keeps the anti-aliased ink edge — the source sets mix real-alpha PNGs with
     white-matted scans, which is why the alpha "looks broken" when composited)
  2. recolors all ink to brand white #f5f7ff (tint happens at render time via CSS
     mask, so ONE asset serves green/red/white)
  3. trims to the ink bounding box (+4px pad)
  4. writes library/doodles/<category>/<name>.png + a manifest.json index

LICENSE BOUNDARY (EULA §1: no distribution/transfer of the files): the output lives
ONLY in `library/` — already gitignored ("licensed for use, not redistribution", same
rule as the music beds). The render engine stages referenced doodles into each
project's private work/remotion/public/ dir. Never commit these files; never copy
them into a public repo path. Flattened into rendered video = permitted promotional
use; the standalone files = not distributable.

Usage:
  python3 tools/import_doodles.py                # import from the default source
  python3 tools/import_doodles.py --src <dir>    # alternate source root
"""
import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "library" / "doodles"
DEFAULT_SRC = Path("/Volumes/Stuff/Archive/Graphics and Fonts/CopyDoodles")
BRAND_WHITE = (245, 247, 255)

# category -> list of source dirs (relative to the CopyDoodles root). Shape sets only —
# the word-phrase sets ("double_your_profits" etc.) are deliberately excluded: wrong
# register for the channel (operator directive 2026-07-04: no infomercial aesthetics).
SOURCES = {
    "arrows":    ["1_Black_CopyDoodles/Black_arrows"],
    "ovals":     ["1_Black_CopyDoodles/Black_ovals"],
    "boxes":     ["1_Black_CopyDoodles/Black_boxes"],
    "brackets":  ["1_Black_CopyDoodles/Black_brackets"],
    "bullets":   ["1_Black_CopyDoodles/Black_bullets"],
    "crossouts": ["1_Black_CopyDoodles/Black_crossouts"],
    "lines":     ["1_Black_CopyDoodles/Black_lines"],
    "misc":      ["1_Black_CopyDoodles/Black_misc_doodles"],
    "numbers":   ["1_Black_CopyDoodles/Black_numbers"],
    "shapes":    ["CopyDoodles_CD_Volume_2/Black_CopyDoodles/Black_shapes"],
}
# a few genuinely useful shape items from Top_25 (its word items are skipped)
TOP25_PICKS = {"asterisk.png", "asterisk_2.png", "check_mark.png",
               "star_1.png", "star_2.png", "star_3.png"}
# word-art that slipped into shape folders
SKIP_NAMES = {"think_outside_the_box.png", "cd_image_1.png", "cd_image_2.png"}

MIN_INK_PX = 40          # skip effectively-empty scans
MAX_DIM = 1200           # none should exceed this, but cap for safety


def process(src_path: Path, dst_path: Path):
    """White-ink alpha PNG from a black-ink scan. Returns (w, h) or None to skip."""
    im = Image.open(src_path).convert("RGBA")
    if max(im.size) > MAX_DIM:
        im.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)
    gray = im.convert("L")
    a_old = im.getchannel("A")
    # ink darkness (255-L) gated by the existing alpha -> kills white-matted bgs
    a_new = Image.eval(gray, lambda l: 255 - l)
    alpha = Image.composite(a_new, Image.new("L", im.size, 0), a_old.point(lambda a: 255 if a > 8 else 0))
    # gentle contrast: drop near-invisible haze, keep anti-aliased edges
    alpha = alpha.point(lambda a: 0 if a < 18 else a)
    bbox = alpha.getbbox()
    if bbox is None:
        return None
    if sum(1 for a in alpha.crop(bbox).getdata() if a > 64) < MIN_INK_PX:
        return None
    pad = 4
    bbox = (max(0, bbox[0] - pad), max(0, bbox[1] - pad),
            min(im.width, bbox[2] + pad), min(im.height, bbox[3] + pad))
    alpha = alpha.crop(bbox)
    out = Image.new("RGBA", alpha.size, BRAND_WHITE + (0,))
    out.putalpha(alpha)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst_path, "PNG")
    return out.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(DEFAULT_SRC))
    args = ap.parse_args()
    src_root = Path(args.src)
    if not src_root.exists():
        sys.exit(f"source not found (volume unmounted?): {src_root}")

    entries, skipped = [], 0
    jobs = [(cat, d) for cat, dirs in SOURCES.items() for d in dirs]
    for cat, rel in jobs:
        d = src_root / rel
        if not d.exists():
            print(f"WARN missing source dir: {rel}")
            continue
        for f in sorted(d.glob("*.png")):
            if f.name in SKIP_NAMES:
                continue
            name = f.stem.lower().replace(" ", "_")
            dst = OUT / cat / f"{name}.png"
            size = process(f, dst)
            if size is None:
                skipped += 1
                continue
            entries.append({"name": f"{cat}/{name}", "category": cat,
                            "file": f"{cat}/{name}.png", "w": size[0], "h": size[1]})
    for f in sorted((src_root / "Top_25").glob("*.png")):
        if f.name not in TOP25_PICKS:
            continue
        name = f.stem.lower()
        dst = OUT / "misc" / f"{name}.png"
        size = process(f, dst)
        if size:
            entries.append({"name": f"misc/{name}", "category": "misc",
                            "file": f"misc/{name}.png", "w": size[0], "h": size[1]})

    manifest = {
        "generated": time.strftime("%Y-%m-%d"),
        "source": "CopyDoodles (Persistent Marketing, Inc.) — operator-purchased library",
        "license": ("Royalty-free EULA: OK composited/flattened into promotional video; "
                    "the files themselves are NOT redistributable — this directory stays "
                    "gitignored (library/), never enters a public repo, and is staged only "
                    "into per-project private work dirs at render time."),
        "ink": "brand white #f5f7ff; tint at render via CSS mask",
        "count": len(entries),
        "doodles": entries,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    by_cat = {}
    for e in entries:
        by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1
    print(json.dumps({"imported": len(entries), "skipped_empty": skipped,
                      "by_category": by_cat, "out": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
