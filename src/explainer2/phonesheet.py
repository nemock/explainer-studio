"""The phone test, plus an advisory fill check, for a rendered explainer.

Why (operator, 2026-11-01, #79): a 16:9 video on a phone held upright is about 390 pt wide,
so everything in a 1080 frame shrinks by ~0.2. #79's headlines were 32 px (6.5 pt there) and
its note sub-lines 22 px (4.5 pt), alone in the middle of a mostly empty frame. Nothing in the
chain ever looked at the frame at the size it is watched. This does:

  PHONE SHEET  one frame per slide (92% through it, after every cued build has landed), each
               scaled to the width it has on a phone, tiled into work/phone_sheet.png. LOOK at
               it at 100%: if you cannot read a slide there, a viewer cannot either.

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

Every render runs this from qa.run (operator 2026-11-05, "a continuous improvement state"), so
each one leaves a sheet and its flagged slides show up in the QA warnings without anyone asking.
It never fails a render. The type floor itself is enforced in the components
(remotion/src/type.ts) and by tools/test_type_floor.py, not detected here.
"""
import json
import subprocess
import tempfile
from pathlib import Path

PHONE_W = 390                 # a 16:9 frame on an upright phone, in points
PHONE_W_PORTRAIT = 195        # half size for a 9:16 frame: a Short's sheet stays readable to tile
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


def grab_frames(video, slides, offset_s, out):
    """One PNG per slide from the rendered master. `slides` are on the narration clock and the
    mp4 opens with the intro, so `offset_s` moves them onto the file's clock (the same shift
    qa.run makes; without it, a sting pushes every sample toward the next slide)."""
    frames = []
    for s in slides:
        t = offset_s + s["start"] + 0.92 * (s["end"] - s["start"])
        f = Path(out) / f"{s['id']}.png"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video),
                        "-frames:v", "1", str(f)], check=True)
        if f.exists():              # a sample past the end of the file writes nothing
            frames.append(f)
    return frames


def art_slides(deck_path):
    """Slide ids that carry an illustration. Detailed art is edge-dense by nature, so CROWDED says
    nothing about it: on #80 all six CROWDED flags were figures, and a warning that wrong that
    often gets ignored. SPARSE still applies to them."""
    try:
        slides = json.loads(Path(deck_path).read_text()).get("slides", [])
    except (OSError, ValueError):
        return set()
    return {s.get("id") for s in slides if s.get("type") in ("figure", "footage") or s.get("image")}


def build_sheet(frames, work_dir, art=()):
    """Tile the frames and measure each. Writes phone_sheet.png + .json, returns the report."""
    from PIL import Image, ImageDraw
    first = Image.open(frames[0])
    fw, fh = first.size
    portrait = fh > fw
    tw = PHONE_W_PORTRAIT if portrait else PHONE_W
    th = round(tw * fh / fw)
    cols = 8 if portrait else 4
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + 10) + 10, rows * (th + 24) + 10), (28, 28, 32))
    d = ImageDraw.Draw(sheet)
    report = []
    for i, f in enumerate(frames):
        im = Image.open(f).convert("RGB")
        m = fill_metrics(im)
        v = verdict(m)
        if v == "CROWDED" and f.stem in art:
            v = "ok"
        report.append({"slide": f.stem, **m, "verdict": v})
        x, y = 10 + (i % cols) * (tw + 10), 10 + (i // cols) * (th + 24)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y + 18))
        d.text((x, y + 2), f"{f.stem}  {'' if v == 'ok' else v}",
               fill=(255, 210, 90) if v != "ok" else (255, 255, 255))
    work_dir = Path(work_dir)
    sheet.save(work_dir / "phone_sheet.png")
    (work_dir / "phone_sheet.json").write_text(json.dumps(report, indent=1))
    return report


def summary(report):
    """One line for the QA warnings, or None when nothing is flagged."""
    flagged = [r for r in report if r["verdict"] != "ok"]
    if not flagged:
        return None
    parts = []
    for kind in ("SPARSE", "CROWDED"):
        ids = [r["slide"] for r in flagged if r["verdict"] == kind]
        if ids:
            parts.append(f"{kind} {', '.join(ids)}")
    return (f"phone check (advisory): {len(flagged)} of {len(report)} slides flagged: "
            f"{'; '.join(parts)}. Look at work/phone_sheet.png")


def run_for_render(video, slides, offset_s, work_dir):
    """Frames to a temp dir (a project keeps the sheet, not 100 full-res PNGs), then the sheet.
    `work_dir` is <project>/work, so the deck sits beside it."""
    art = art_slides(Path(work_dir).parent / "deck.json")
    with tempfile.TemporaryDirectory(prefix="phone_sheet_") as tmp:
        frames = grab_frames(video, slides, offset_s, tmp)
        if not frames:
            return []
        return build_sheet(frames, work_dir, art)
