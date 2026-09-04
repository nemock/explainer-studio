#!/usr/bin/env python3
"""frame_qc.py — framing regression guard for rendered explainer slides.

Built 2026-08-30 after the FWF daily shipped a punch card ("UNREAD") clipped at both
frame edges to six platforms. Nothing in the chain looked at a pixel: `validate` checks
manifest/caption structure, `qa` checks timing and dead air, and `stills` on a Remotion
project only extracts frames from an mp4 that was already rendered. A slide could be
visually broken and every gate still reported ok.

## What this can and cannot do (read before extending it)

The first cut of this tool tried to flag ANY ink reaching the frame edge. That does not
work on these decks, and the measurements are worth recording so nobody rebuilds it:

  * The paper sets are FULL-BLEED by design. Art at the frame edge is correct, not a
    defect, so edge ink on its own means nothing.
  * Type ink and the dark end of the set ground are the same colour to within a rounding
    error. Measured on FWF 2026-08-29: glyph ink (43,18,66), dark set ground on slide 9
    (47,21,60), set artwork at the slide 1 left edge (48,23,71). A colour-keyed
    discriminator cannot separate them, so do not try.

That first version flagged 10 of 11 slides on a deck with exactly one clipped slide. A
checker that cries wolf gets ignored, which is worse than no checker.

So this tool is deliberately NARROW. It checks the one case that is unambiguous:

  EDGE_CLIP  on slides whose whole job is one centred block of type (`punch`, `cta`),
             ink touching the left or right edge INSIDE the type's own vertical band is
             clipped type. On a correctly fitted punch card that band is clean ground on
             both sides, because the word is centred with margins. This is precisely the
             defect that shipped, and it regression-guards the CvgPunch fit fix.

  DEAD_BAND  advisory. The top of the frame is empty while content sits low. Reliable
             (it measures emptiness, which needs no type/art discrimination) but it is a
             composition smell, never an error.

Everything else — is the type legible over the set, is the crop sensible, do the props
collide — needs either eyes or renderer-level text metrics. The durable fix for text
overflow is PREVENTION in the component (fit the type to the frame) rather than
detection here; see CvgPunch in remotion/src/components/Circumvent.tsx.

Usage:
    python3 frame_qc.py <project_dir> [--aspect 9:16] [--json out.json] [--strict]

Exit: 0 clean/advisory-only, 1 blocking defect, 2 could not run.
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys

try:
    from PIL import Image
except ImportError:
    print("frame_qc: Pillow is required (pip install Pillow)", file=sys.stderr)
    sys.exit(2)


EDGE_COLS = 4          # how many columns at each edge count as "the edge"
INK_DELTA = 46         # luma distance from ground before a pixel counts as ink
CLIP_RUN_MIN = 30      # consecutive ink rows at the edge before it is a clipped glyph
TYPE_BAND = (0.30, 0.72)   # vertical slice a centred punch/cta word occupies
DEAD_BAND_FRAC = 0.26
DEAD_BAND_INK = 0.004

# Slide types that are one centred block of type, where the edge test is meaningful.
CENTRED_TYPE_SLIDES = {"punch", "cta"}


def _ground_luma(px, w, h):
    """Median of a sparse interior sample — the paper ground dominates these frames."""
    vals = []
    step = max(1, min(w, h) // 90)
    for y in range(0, h, step):
        for x in range(0, w, step):
            vals.append(px[x, y])
    vals.sort()
    return vals[len(vals) // 2]


def analyse(path, slide_type):
    im = Image.open(path).convert("L")
    w, h = im.size
    px = im.load()
    ground = _ground_luma(px, w, h)

    y0, y1 = int(h * TYPE_BAND[0]), int(h * TYPE_BAND[1])
    longest = {"left": 0, "right": 0}
    if slide_type in CENTRED_TYPE_SLIDES:
        for side, xs in (("left", range(0, EDGE_COLS)),
                         ("right", range(w - EDGE_COLS, w))):
            run = 0
            for y in range(y0, y1):
                hit = any(abs(px[x, y] - ground) >= INK_DELTA for x in xs)
                run = run + 1 if hit else 0
                longest[side] = max(longest[side], run)

    band_h = int(h * DEAD_BAND_FRAC)
    step = max(1, min(w, h) // 300)
    ink = tot = 0
    for y in range(0, band_h, step):
        for x in range(0, w, step):
            tot += 1
            if abs(px[x, y] - ground) >= INK_DELTA:
                ink += 1
    band_frac = ink / max(1, tot)

    return {
        "file": os.path.basename(path),
        "slide_type": slide_type,
        "size": [w, h],
        "ground_luma": ground,
        "edge_run_left": longest["left"],
        "edge_run_right": longest["right"],
        "top_band_ink_frac": round(band_frac, 5),
        "edge_checked": slide_type in CENTRED_TYPE_SLIDES,
    }


def findings_for(a):
    out = []
    sides = [s for s in ("left", "right") if a["edge_run_%s" % s] >= CLIP_RUN_MIN]
    if sides:
        out.append({
            "code": "EDGE_CLIP", "blocking": True, "slide": a["file"],
            "detail": "%s slide: %s edge has an unbroken ink run of %d px inside the type "
                      "band — the word is clipped by the frame"
                      % (a["slide_type"], "/".join(sides),
                         max(a["edge_run_left"], a["edge_run_right"])),
        })
    if a["top_band_ink_frac"] < DEAD_BAND_INK:
        out.append({
            "code": "DEAD_BAND", "blocking": False, "slide": a["file"],
            "detail": "top %.0f%% of the frame is empty (ink %.3f%%)"
                      % (DEAD_BAND_FRAC * 100, a["top_band_ink_frac"] * 100),
        })
    return out


def slide_types(proj):
    deck = proj / "deck.json"
    if not deck.is_file():
        return {}
    return {s["id"]: s.get("type", "?") for s in json.loads(deck.read_text())["slides"]}


def collect_frames(proj, aspect, workdir):
    """Always extract from the mp4 for the requested aspect. stills/ is NOT used: it is
    rendered at whatever aspect the routine asked for (4:5 on the booth shows), so
    trusting it silently checks the wrong frame shape."""
    vid = proj / "video" / ("explainer_%s.mp4" % aspect.replace(":", "x"))
    tl = proj / "work" / "timeline.json"
    if not (vid.exists() and tl.exists()):
        return [], None
    timeline = json.loads(tl.read_text())
    # The timeline is narration time; the mp4 opens with the intro (show title panel
    # on the six personal shows since 2026-09-03, brand sting on deep dives). Read the
    # offset back from the staged Remotion props (mirrors remotion_engine.intro_offset_s,
    # inlined because this tool runs standalone) so each frame is sampled from the
    # slide it names rather than ~2.4 s into the previous one.
    off = 0.0
    props = proj / "work" / "remotion" / "props.json"
    if props.exists():
        try:
            pd = json.loads(props.read_text())
            off = float(pd.get("audioFrom") or 0) / float(pd.get("fps") or 30)
        except (OSError, ValueError):
            off = 0.0
    workdir.mkdir(parents=True, exist_ok=True)
    made = []
    for i, s in enumerate(timeline["slides"], 1):
        t = off + s["start"] + (s["end"] - s["start"]) * 0.6
        dst = workdir / ("slide_%02d_%s.png" % (i, s["id"]))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.3f" % t,
                        "-i", str(vid), "-frames:v", "1", str(dst)], check=True)
        made.append((dst, s["id"]))
    return made, vid.name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--strict", action="store_true",
                    help="treat advisory findings as blocking too")
    args = ap.parse_args()

    proj = pathlib.Path(args.project)
    if not proj.is_dir():
        print("frame_qc: no such project %s" % proj, file=sys.stderr)
        return 2

    types = slide_types(proj)
    frames, src = collect_frames(proj, args.aspect, proj / "work" / "frame_qc")
    if not frames:
        print("frame_qc: need video/explainer_%s.mp4 and work/timeline.json"
              % args.aspect.replace(":", "x"), file=sys.stderr)
        return 2

    analyses = [analyse(str(f), types.get(sid, "?")) for f, sid in frames]
    findings = []
    for a in analyses:
        findings.extend(findings_for(a))

    blocking = [f for f in findings if f["blocking"]]
    advisory = [f for f in findings if not f["blocking"]]

    print("frame_qc — %s  (%d slides from %s, aspect %s)"
          % (proj.name, len(frames), src, args.aspect))
    print()
    for a in analyses:
        codes = [f["code"] for f in findings if f["slide"] == a["file"]]
        mark = "FAIL" if any(f["blocking"] for f in findings if f["slide"] == a["file"]) \
               else ("warn" if codes else "ok  ")
        edge = ("L%-4d R%-4d" % (a["edge_run_left"], a["edge_run_right"])
                if a["edge_checked"] else "not checked")
        print("  %s %-24s %-10s edge=%-16s top_ink=%.3f%% %s"
              % (mark, a["file"], a["slide_type"], edge,
                 a["top_band_ink_frac"] * 100, ",".join(codes)))

    if findings:
        print()
        for f in blocking + advisory:
            print("  [%s] %s %s: %s"
                  % ("BLOCK" if f["blocking"] else "advis", f["code"], f["slide"], f["detail"]))

    print()
    print("%d blocking, %d advisory" % (len(blocking), len(advisory)))

    if args.json_out:
        pathlib.Path(args.json_out).write_text(json.dumps(
            {"project": str(proj), "aspect": args.aspect, "source": src,
             "slides": analyses, "findings": findings,
             "blocking": len(blocking), "advisory": len(advisory)}, indent=2) + "\n")

    return 1 if (blocking or (args.strict and advisory)) else 0


if __name__ == "__main__":
    sys.exit(main())
