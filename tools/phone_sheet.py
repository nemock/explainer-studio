#!/usr/bin/env python3
"""phone_sheet.py — the phone test, plus an advisory fill check, for a rendered explainer.

Why (operator, 2026-11-01, #79): a 16:9 video on a phone held upright is about 390 pt wide,
so everything in a 1080 frame shrinks by ~0.2. #79's headlines were 32 px (6.5 pt there) and
its note sub-lines 22 px (4.5 pt), alone in the middle of a mostly empty frame. Nothing in the
chain ever looked at the frame at the size it is watched. This does:

  PHONE SHEET  one frame per slide (92% through it, after every cued build has landed), each
               scaled to 390 px wide, tiled into work/phone_sheet.png. LOOK at it at 100%:
               if you cannot read a slide there, a viewer cannot either.

  FILL CHECK   advisory. How much of the space above the captions the slide actually uses.
               Content is measured as EDGES (type, cut paper, rules), not as colour, because
               on these paper worlds the ground, the light falloff and the laid sheets are
               all low-contrast, while every glyph and object edge is high-contrast. Grain
               sits under the threshold. Reported per slide:
                 SPARSE    < 8% of the band is edge-dense, or the content's box covers < 25%
                 CROWDED   >= 24% of the band is edge-dense (a wall of type or notes)
               Both are composition smells, never errors. Calibrated on #79 (2026-11-01):
               the shipped "Two bets" (s08) measured 4.9% and its re-render on the phone type
               scale 12.1%; s13 5.5% -> 18.1%; shipped document figures run 15-22%; the
               crowded re-rendered s17 is 24.4%. A box measure alone does not separate them:
               three small notes spread across the frame still span a wide box.

The type floor itself is enforced in the components (remotion/src/type.ts), not detected
here; tools/test_type_floor.py stops new sub-floor sizes from creeping back in.

Usage:
    python3 tools/phone_sheet.py <project_dir>            # frames from video/*.mp4 (queued)
    python3 tools/phone_sheet.py <project_dir> --frames <dir_of_sNN.png>   # no decode

Writes work/phone_sheet.png, its preview (Read THAT, SKILL hard rule 9) and
work/phone_sheet.json. Exit 0 always unless it could not run (2): the fill check advises.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

PHONE_W = 390                 # a 16:9 frame on an upright phone, in points
BAND = (0.03, 0.04, 0.97, 0.72)   # x0, y0, x1, y1 of the frame above the caption band
EDGE_T = 22                   # gradient step that counts as an edge (paper grain is below)
SPARSE_BBOX = 0.25
SPARSE_INK = 0.08
CROWDED_INK = 0.24


def fill_metrics(img):
    """{'bbox': share of the band the content's box covers, 'ink': share of the band that is
    edge-dense}. `img` is a PIL image of the full frame."""
    import numpy as np
    from PIL import Image, ImageFilter
    g = img.convert("L")
    W, H = g.size
    x0, y0, x1, y1 = (int(BAND[0] * W), int(BAND[1] * H), int(BAND[2] * W), int(BAND[3] * H))
    a = np.asarray(g, dtype=np.int16)[y0:y1, x0:x1]
    gx = np.abs(np.diff(a, axis=1))[:-1, :]
    gy = np.abs(np.diff(a, axis=0))[:, :-1]
    edges = ((gx > EDGE_T) | (gy > EDGE_T)).astype(np.uint8) * 255
    # close glyphs and objects into blobs, so ink measures "covered by content"
    m = Image.fromarray(edges).filter(ImageFilter.MaxFilter(15))
    mask = np.asarray(m) > 0
    if not mask.any():
        return {"bbox": 0.0, "ink": 0.0}
    ys, xs = np.nonzero(mask)
    # robust box: ignore the outermost 0.5% of content pixels (a stray prop corner)
    lo_x, hi_x = np.percentile(xs, [0.5, 99.5])
    lo_y, hi_y = np.percentile(ys, [0.5, 99.5])
    area = mask.shape[0] * mask.shape[1]
    return {"bbox": round(float((hi_x - lo_x) * (hi_y - lo_y) / area), 3),
            "ink": round(float(mask.mean()), 3)}


def verdict(m):
    if m["bbox"] < SPARSE_BBOX or m["ink"] < SPARSE_INK:
        return "SPARSE"
    if m["ink"] >= CROWDED_INK:
        return "CROWDED"
    return "ok"


def grab_frames(pdir, out):
    """One PNG per slide from the rendered master (ffmpeg decode, PNG out)."""
    vids = sorted((pdir / "video").glob("explainer_*.mp4"))
    if not vids:
        sys.exit(f"phone_sheet: no video/explainer_*.mp4 in {pdir}")
    tl = json.loads((pdir / "work" / "timeline.json").read_text())
    out.mkdir(parents=True, exist_ok=True)
    frames = []
    for s in tl["slides"]:
        t = s["start"] + 0.92 * (s["end"] - s["start"])
        f = out / f"{s['id']}.png"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(vids[0]),
                        "-frames:v", "1", str(f)], check=True)
        frames.append(f)
    return frames


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--frames", help="use existing sNN.png frames from this dir (no decode)")
    a = ap.parse_args()
    pdir = Path(a.project).resolve()
    if a.frames:
        frames = sorted(Path(a.frames).resolve().glob("s[0-9]*.png"))
    else:
        from explainer2 import jobqueue
        # decoding a long master launches ffmpeg per slide: a render-class job, so from a
        # session it goes through the queue like every other one (CLAUDE.md rule 9)
        if jobqueue.should_route():
            sys.exit(jobqueue.submit_and_wait(
                "phone_sheet", [sys.executable, str(Path(__file__).resolve()), str(pdir)],
                project=str(pdir), label=f"phone_sheet:{pdir.name}"))
        frames = grab_frames(pdir, pdir / "work" / "phone_sheet")
    if not frames:
        print("phone_sheet: no frames found", file=sys.stderr)
        sys.exit(2)

    from PIL import Image, ImageDraw
    from frame_preview import make_preview
    PH = round(PHONE_W * 9 / 16)
    cols = 4
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (PHONE_W + 10) + 10, rows * (PH + 24) + 10), (28, 28, 32))
    d = ImageDraw.Draw(sheet)
    report = []
    for i, f in enumerate(frames):
        im = Image.open(f).convert("RGB")
        m = fill_metrics(im)
        v = verdict(m)
        report.append({"slide": f.stem, **m, "verdict": v})
        x, y = 10 + (i % cols) * (PHONE_W + 10), 10 + (i // cols) * (PH + 24)
        sheet.paste(im.resize((PHONE_W, PH), Image.LANCZOS), (x, y + 18))
        d.text((x, y + 2), f"{f.stem}  {'' if v == 'ok' else v}",
               fill=(255, 210, 90) if v != "ok" else (255, 255, 255))
    dst = pdir / "work" / "phone_sheet.png"
    sheet.save(dst)
    (pdir / "work" / "phone_sheet.json").write_text(json.dumps(report, indent=1))
    flagged = [r for r in report if r["verdict"] != "ok"]
    for r in flagged:
        print(f"  {r['verdict']:<8} {r['slide']}  content box {r['bbox']:.0%} of the band, "
              f"edge-dense {r['ink']:.0%}")
    print(f"phone sheet: {dst}\npreview:     {make_preview(dst, None, 1200)}")
    print(f"fill check (advisory): {len(flagged)} of {len(report)} slides flagged")


if __name__ == "__main__":
    main()
