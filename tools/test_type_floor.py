#!/usr/bin/env python3
"""Ratchet: no NEW sub-floor font sizes in the Remotion components.

Run:  python3 tools/test_type_floor.py            (fails on a regression)
      python3 tools/test_type_floor.py --baseline (prints current counts, to paste below)

Why (operator, 2026-11-01, #79): every component carried its own inline `fontSize: height *
0.0NN`, and most were sized for a monitor. Under ~0.044 of the frame's short side (48 px at
1080) type is unreadable on a phone held upright. remotion/src/type.ts now owns the sizes as
roles with phone floors, and a component adopts it by wrapping its old literal:
`fontSize: ts('sub', height * 0.026)`. That legacy argument is what unscaled worlds still
render, so it is allowed; so is an explicit phone branch, `phone ? <scaled> : <legacy>`
(the variable is `phone` or `on`, from useTypeScale). A BARE literal under the floor is not.

The bare ones that remain are in components or branches that no phone-type world reaches
(Circumvent, Chem, the legacy branches of the scaled components). Rewriting them all would
move every other show's renders, which is not this change. So this is a ratchet, not a ban:
each file may hold at most its BASELINE count. Adding one fails. Removing some prints a
reminder to lower the baseline, so the count only ever goes down.
"""
import re
import sys
from pathlib import Path

COMPONENTS = Path(__file__).resolve().parents[1] / "remotion" / "src" / "components"
FLOOR = 0.044
EXPR = re.compile(r"fontSize:\s*([^,}]+)")
RAW = re.compile(r"\b(height|H|U|M|frameH|cardH)\s*\*\s*(0\.\d+)")
PHONE_BRANCH = re.compile(r"(phone|on)\s*\?")

# Bare sub-floor literals per file on 2026-11-01, after the phone type scale landed.
BASELINE = {
    "Annotate.tsx": 0,
    "Audio.tsx": 0,
    "BRGPaperSting.tsx": 1,
    "Background.tsx": 0,
    "CTA.tsx": 2,
    "Captions.tsx": 0,
    "Chem.tsx": 0,
    "ChibiPresenter.tsx": 0,
    "Circumvent.tsx": 7,
    "CvgTitle.tsx": 0,
    "DataViz2.tsx": 0,
    "Extras.tsx": 3,
    "Hero3D.tsx": 1,
    "KeepCard.tsx": 1,
    "KineticHook.tsx": 2,
    "Media.tsx": 1,
    "PaperBackground.tsx": 0,
    "PaperData.tsx": 1,
    "PaperHook.tsx": 0,
    "PaperMonitor.tsx": 0,
    "PaperNote.tsx": 0,
    "PaperSet.tsx": 0,
    "PaperStage.tsx": 0,
    "PaperSting.tsx": 1,
    "PaperText.tsx": 0,
    "PaperWorld.tsx": 0,
    "Schematic.tsx": 2,
    "SourceLine.tsx": 0,
    "StatCounter.tsx": 3,
    "StatGrid.tsx": 2,
    "TalkingScene.tsx": 1,
    "TextScenes.tsx": 7,
    "colorize.tsx": 0,
}


def bare_subfloor(text):
    """Line numbers of `fontSize:` expressions that are a bare `<dim> * k`, k < FLOOR."""
    hits = []
    for m in EXPR.finditer(text):
        expr = m.group(1).strip()
        if expr.startswith("ts(") or PHONE_BRANCH.match(expr):
            continue
        r = RAW.search(expr)
        if r and float(r.group(2)) < FLOOR:
            hits.append(text.count("\n", 0, m.start()) + 1)
    return hits


def main():
    counts = {f.name: bare_subfloor(f.read_text()) for f in sorted(COMPONENTS.glob("*.tsx"))}
    if "--baseline" in sys.argv:
        for name, hits in counts.items():
            print(f'    "{name}": {len(hits)},')
        return 0
    bad, lower = [], []
    for name, hits in counts.items():
        allowed = BASELINE.get(name, 0)
        if len(hits) > allowed:
            bad.append(f"{name}: {len(hits)} bare sub-floor font sizes (baseline {allowed}), "
                       f"lines {hits}. Wrap the size in ts('<role>', <legacy>) "
                       f"(remotion/src/type.ts) instead of adding a literal.")
        elif len(hits) < allowed:
            lower.append(f"{name}: {len(hits)} < baseline {allowed}; lower it in BASELINE")
    for line in lower:
        print("note:", line)
    if bad:
        print("FAIL —", len(bad), "file(s) gained tiny type:")
        for b in bad:
            print("  -", b)
        return 1
    print(f"PASS — no new sub-floor font sizes across {len(counts)} components")
    return 0


if __name__ == "__main__":
    sys.exit(main())
