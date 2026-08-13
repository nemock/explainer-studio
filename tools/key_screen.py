#!/usr/bin/env python3
"""key_screen.py — turn a papercraft set's flat green screen into a real transparent hole.

The on-camera cold open (references/paper-world/ON-CAMERA-COLD-OPEN.md) needs the
monitor's screen to be "a hole in the papercraft with the real video behind it… the seam
is the whole illusion; do not butt them flush." Compositing the footage ON TOP of a green
rectangle cannot produce that seam: the video's hard edge lands over the paper and the
bezel never overlaps it.

So we cut the hole for real. The set is generated with the screen as a flat #3ddc84 paper
panel (the one place green is allowed in that plate), and this script:

  1. segments the largest green component,
  2. ERODES it by a few pixels, so the hole is slightly SMALLER than the painted green —
     the eroded ring is where antialiasing and green spill live, and leaving it as opaque
     paper is what stops a green fringe showing around the footage,
  3. feathers the last pixel of alpha so the edge is not a staircase,
  4. despills whatever green survives inside the feather, pulling it toward the bezel navy,
  5. writes the RGBA PNG plus a sidecar JSON with the measured screen rect.

The rect is in fractions of the image and is what the deck slide's `screen` field carries;
PaperMonitor.tsx positions the video with it. Measure once here, never eyeball it.

Usage:
  python3 tools/key_screen.py <in.png> <out.png> [--erode 4] [--feather 2] [--bezel 2c1e4e]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


def hex_rgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--erode", type=int, default=4,
                    help="pixels to shrink the hole by, so paper covers the spill ring")
    ap.add_argument("--feather", type=int, default=2, help="soft edge width in pixels")
    ap.add_argument("--bezel", default="2c1e4e", help="colour to despill toward")
    ap.add_argument("--aspect", default="16:9",
                    help="centre-crop to this aspect first; 'none' to skip")
    a = ap.parse_args()

    img = Image.open(a.src).convert("RGB")

    # CROP TO THE COMP ASPECT BEFORE MEASURING. The rect this script emits is in fractions
    # of the image, but PaperMonitor positions the footage in fractions of the FRAME. Those
    # two spaces are only the same when `objectFit: cover` is a no-op — i.e. when the plate
    # already has the composition's aspect. The first set here was 1344x752 (1.787) against
    # a 16:9 frame (1.778); cover then scaled the plate 0.5% and shifted it ~5px, so every
    # authored coordinate was off by that much and the footage edge poked out from under the
    # bezel. Cropping here makes the mismatch structurally impossible instead of asking the
    # component to model it.
    if a.aspect != "none":
        aw, ah = (float(v) for v in a.aspect.split(":"))
        want = aw / ah
        W0, H0 = img.size
        have = W0 / H0
        if abs(have - want) > 1e-6:
            if have > want:                      # too wide: trim the sides
                new_w = int(round(H0 * want))
                off = (W0 - new_w) // 2
                img = img.crop((off, 0, off + new_w, H0))
            else:                                # too tall: trim top and bottom
                new_h = int(round(W0 / want))
                off = (H0 - new_h) // 2
                img = img.crop((0, off, W0, off + new_h))
            print(f"  cropped {W0}x{H0} -> {img.size[0]}x{img.size[1]} for exact {a.aspect}")

    arr = np.asarray(img).astype(int)
    H, W = arr.shape[:2]
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]

    green = (g > 110) & (g - r > 45) & (g - b > 35)
    lab, n = ndimage.label(green)
    if not n:
        sys.exit("no green screen panel found — was the set generated with a green screen?")
    sizes = ndimage.sum(green, lab, range(1, n + 1))
    panel = lab == (int(np.argmax(sizes)) + 1)

    ys, xs = np.nonzero(panel)
    rect = {"x0": xs.min() / W, "x1": xs.max() / W, "y0": ys.min() / H, "y1": ys.max() / H}
    fill = sizes[int(np.argmax(sizes))] / ((xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1))

    # Shrink the hole so the eroded ring (antialiasing + spill) stays as opaque paper.
    hole = ndimage.binary_erosion(panel, iterations=a.erode) if a.erode else panel
    if not hole.any():
        sys.exit(f"erode={a.erode} removed the whole panel — lower it")

    # Feather: distance-transform the last few pixels inside the hole.
    if a.feather > 0:
        dist = ndimage.distance_transform_edt(hole)
        alpha_hole = np.clip(dist / (a.feather + 1e-6), 0, 1)
    else:
        alpha_hole = hole.astype(float)
    alpha = (1.0 - alpha_hole)  # 1 = opaque paper, 0 = fully cut away

    # Despill. This must NOT be weighted by alpha: eroding the hole leaves a ring of
    # FULLY OPAQUE painted-green pixels between the hole edge and the true paper edge,
    # and an alpha-weighted despill gives those a weight of zero — which left 10,576
    # bright green pixels ringing the footage on the first run here. That ring is the
    # inner lip of the bezel and should read as bezel, so it gets despilled at full
    # strength. Antialiased spill just OUTSIDE the panel is caught too, by measuring
    # greenness over a dilated neighbourhood rather than trusting the hard mask.
    out = arr.astype(float).copy()
    near = ndimage.binary_dilation(panel, iterations=max(a.erode + a.feather, 3) + 2)
    greenness = np.clip((g - np.maximum(r, b)) / 60.0, 0, 1) * near
    if greenness.any():
        bez = np.array(hex_rgb(a.bezel), dtype=float)
        w = greenness[..., None]
        out = out * (1 - w) + bez * w

    rgba = np.dstack([np.clip(out, 0, 255).astype(np.uint8),
                      (alpha * 255).round().astype(np.uint8)])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(a.out)

    meta = {"source": Path(a.src).name, "screen": {k: round(v, 4) for k, v in rect.items()},
            "screen_width_frac": round(rect["x1"] - rect["x0"], 4),
            "rect_fill": round(float(fill), 4), "erode_px": a.erode, "feather_px": a.feather,
            "image_size": [W, H], "hole_px": int(hole.sum())}
    Path(a.out).with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")

    print(f"wrote {a.out}")
    print(f"  screen  x {rect['x0']:.3f}-{rect['x1']:.3f}  y {rect['y0']:.3f}-{rect['y1']:.3f}")
    print(f"  width   {meta['screen_width_frac']:.3f} of frame   rect-fill {fill:.3f}")
    print(f"  hole    {int(hole.sum()):,} px cut, eroded {a.erode}, feathered {a.feather}")
    if fill < 0.95:
        print("  WARNING: the green panel is not a clean rectangle — check the plate")


if __name__ == "__main__":
    main()
