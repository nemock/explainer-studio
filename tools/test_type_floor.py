#!/usr/bin/env python3
"""No sub-floor font sizes in the Remotion components, and no theme off the type scale.

Run:  python3 tools/test_type_floor.py

Why (operator, 2026-11-01, #79): every component carried its own inline `fontSize: height *
0.0NN`, and most were sized for a monitor. Under ~0.044 of the frame's short side (48 px at
1080) type is unreadable on a phone held upright. remotion/src/type.ts owns the sizes as roles
with phone floors, and a component takes one with `fontSize: ts('sub', height * 0.026)`.

Why this is a ban and not a ratchet (operator, 2026-11-05: "update everything moving forward"):
this used to allow each file its 2026-11-01 count of bare literals, on the theory that those
branches were unreachable. Then the scale went on for every theme, which makes every branch
reachable. It also looked only at `height`-based sizes, so all of Cut & Bond, which sizes off
frame width, was invisible to it. Now: no bare literal under the floor, on either axis.

And no theme off the scale, by accident. Every theme in themes.py resolves through
paperWorldFor() to a world with phoneType, which includes the fallback. The 2026-11-01 upgrade
shipped opt-in, this test checked only inline sizes, and the daily and every weekly show stayed on
23-28 px type for four more days with every gate green. A theme that really must stay off goes
in UNSCALED with the reason, which is a visible choice.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "remotion" / "src" / "components"
sys.path.insert(0, str(ROOT / "src"))
FLOOR = 0.044
EXPR = re.compile(r"fontSize:\s*([^,}]+)")
RAW = re.compile(r"\b(height|width|H|W|U|M|frameH|cardH)\s*\*\s*(0\.\d+)")
PHONE_BRANCH = re.compile(r"(phone|on)\s*\?")

UNSCALED = {}   # theme -> why it stays off. Empty, and it should stay that way.


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
    """Every theme in themes.py on the scale, counting the fallback world; stale exceptions."""
    from explainer2 import themes
    ts = (ROOT / "remotion/src/brands/papercraft.ts").read_text()
    block = ts[ts.index("const WORLD_BY_THEME"):]
    block = block[:block.index("};")]
    worlds = dict(re.findall(r"'([\w-]+)':\s*(PAPER_\w+)", block))
    assert worlds, "WORLD_BY_THEME not found"
    fallback = re.search(r"WORLD_BY_THEME\[theme\]\)\s*\|\|\s*(PAPER_\w+)", ts)
    assert fallback, "paperWorldFor's fallback world not found"

    def scaled(name):
        m = re.search(r"const %s: PaperWorldTokens = \{(.*?)\n\};" % name, ts, re.S)
        assert m, f"{name} definition not found"
        if re.search(r"\bphoneType:\s*true", m.group(1)):
            return True
        parent = re.search(r"\.\.\.(PAPER_\w+)", m.group(1))
        return scaled(parent.group(1)) if parent else False

    every = sorted(set(themes.THEMES) | set(worlds))
    on = {t for t in every if scaled(worlds.get(t, fallback.group(1)))}
    out = []
    for t in every:
        if t not in on and t not in UNSCALED:
            out.append(f"theme {t}: no phoneType and no reason in UNSCALED, so it ships unreadable type")
        if t in on and t in UNSCALED:
            out.append(f"theme {t}: on phoneType but still listed in UNSCALED; remove it")
    return out, len(on), len(every)


def main():
    bad = []
    n = 0
    for f in sorted(COMPONENTS.glob("*.tsx")):
        n += 1
        hits = bare_subfloor(f.read_text())
        if hits:
            bad.append(f"{f.name}: bare sub-floor font sizes at lines {hits}. Wrap the size in "
                       f"ts('<role>', <legacy>) (remotion/src/type.ts) instead of a literal.")
    theme_bad, n_on, n_all = theme_problems()
    bad += theme_bad
    if bad:
        print("FAIL —", len(bad), "type problem(s):")
        for b in bad:
            print("  -", b)
        return 1
    print(f"PASS — no sub-floor font sizes across {n} components; "
          f"{n_on} of {n_all} themes on the scale, {len(UNSCALED)} named exceptions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
