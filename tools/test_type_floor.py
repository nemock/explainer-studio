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
ROOT = Path(__file__).resolve().parents[1]

# THEMES NOT YET ON THE SCALE. Every theme in WORLD_BY_THEME is either on phoneType or named
# here with the reason. The 2026-11-01 upgrade shipped opt-in, this test checked only inline
# sizes, and the daily and every weekly show stayed on 23-28 px type for four more days with
# every gate green (operator caught it on a phone, 2026-11-05). A world can no longer be left
# out by nobody deciding: adding a theme, or leaving one here, is now a visible choice.
UNSCALED = {
    "plg-guide": "published series; operator has not decided",
    "pmg-guide": "mid-series; operator has not decided",
    "brg-deep-dive": "operator has not decided",
    "brg-paper": "operator has not decided",
    "wte-guide": "operator has not decided",
}

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
    "Circumvent.tsx": 0,
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


def theme_problems():
    """Themes on neither list, stale exceptions, and the engine's tuple out of step."""
    ts = (ROOT / "remotion/src/brands/papercraft.ts").read_text()
    block = ts[ts.index("const WORLD_BY_THEME"):]
    block = block[:block.index("};")]
    worlds = dict(re.findall(r"'([\w-]+)':\s*(PAPER_\w+)", block))
    assert worlds, "WORLD_BY_THEME not found"

    def scaled(name):
        m = re.search(r"const %s: PaperWorldTokens = \{(.*?)\n\};" % name, ts, re.S)
        assert m, f"{name} definition not found"
        if re.search(r"\bphoneType:\s*true", m.group(1)):
            return True
        parent = re.search(r"\.\.\.(PAPER_\w+)", m.group(1))
        return scaled(parent.group(1)) if parent else False

    on = {t for t, w in worlds.items() if scaled(w)}
    engine = (ROOT / "src/explainer2/remotion_engine.py").read_text()
    tuple_of = lambda name: set(re.findall(r'"([\w-]+)"', re.search(
        r"^%s = (.*?\))" % name, engine, re.S | re.M).group(1)))
    py = tuple_of("PHONE_TYPE_THEMES") | tuple_of("_CVG_STYLE_THEMES")
    out = []
    for t in sorted(worlds):
        if t not in on and t not in UNSCALED:
            out.append(f"theme {t}: no phoneType and no reason in UNSCALED, so it ships unreadable type")
        if t in on and t in UNSCALED:
            out.append(f"theme {t}: on phoneType but still listed in UNSCALED; remove it")
        if (t in on) != (t in py):
            out.append(f"theme {t}: phoneType {t in on} but PHONE_TYPE_THEMES {t in py} (captions would disagree)")
    return out, len(on), len(worlds)


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
    theme_bad, n_on, n_all = theme_problems()
    bad += theme_bad
    if bad:
        print("FAIL —", len(bad), "type problem(s):")
        for b in bad:
            print("  -", b)
        return 1
    print(f"PASS — no new sub-floor font sizes across {len(counts)} components; "
          f"{n_on} of {n_all} themes on the scale, {len(UNSCALED)} named exceptions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
