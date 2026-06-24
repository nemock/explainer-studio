"""Clean a cutout's alpha matte for compositing: drop low-confidence pixels
(which carry background contamination — e.g. Gemini's baked-in checkerboard
tints semi-transparent hair wisps), erode slightly, then feather the edge so
it reads soft at thumbnail scale instead of knife-cut.

Usage: python tools/clean_matte.py <in.png> <out.png> [--threshold 60] [--erode 2] [--feather 3] [--no-trim]

By default the cleaned cutout is cropped to its alpha bounding box (`--trim`).
This is load-bearing for thumbnails: a wide transparent PNG with the subject in
the middle, placed by the brand template, otherwise renders the subject
dead-centre under the headline instead of anchored to one side (caught 2026-06-24
on #12). Pass --no-trim to keep the original canvas.
"""
import argparse

import numpy as np
from PIL import Image, ImageFilter


def clean(src, dst, threshold=60, erode=2, feather=3.0, trim=True):
    im = Image.open(src).convert("RGBA")
    rgba = np.array(im)
    a = rgba[:, :, 3].astype(np.float32)

    # binarize: low-confidence (contaminated) pixels go fully transparent
    mask = (a >= threshold).astype(np.uint8) * 255
    m = Image.fromarray(mask, "L")
    for _ in range(max(0, erode)):
        m = m.filter(ImageFilter.MinFilter(3))
    m = m.filter(ImageFilter.GaussianBlur(feather))

    rgba[:, :, 3] = np.array(m)
    out = Image.fromarray(rgba, "RGBA")
    if trim:
        bbox = out.split()[-1].getbbox()  # tight bounds of non-transparent alpha
        if bbox:
            out = out.crop(bbox)
    out.save(dst)
    return dst


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--threshold", type=int, default=60)
    ap.add_argument("--erode", type=int, default=2)
    ap.add_argument("--feather", type=float, default=3.0)
    ap.add_argument("--no-trim", dest="trim", action="store_false",
                    help="keep the original canvas instead of cropping to the alpha bbox")
    args = ap.parse_args()
    print(clean(args.src, args.dst, args.threshold, args.erode, args.feather, args.trim))
