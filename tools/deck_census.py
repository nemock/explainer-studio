#!/usr/bin/env python3
"""deck_census.py — the visual-variety floor check (motion-playbook §4b, 2026-07-06).

Tallies a project's deck.json against the quantified floor that exists because #18
shipped as a narrated PowerPoint (14/22 text slides, 0 data-viz, 0 cues). Run before
every render; paste the tally into PLAYBOOK deck-gate notes. Pure stdlib, read-only.

Usage: python3 tools/deck_census.py <project_dir>
Exit code: 0 = floor passed, 1 = floor failed (advisories never fail the run).
"""
import json
import re
import sys
from pathlib import Path

# Typography-only slide types (motion-playbook §4b census definition).
TEXT_TYPES = {"statement", "reframe", "punch", "quote", "highlight", "define", "list"}
DATA_VIZ_TYPES = {"stat", "statgrid", "delta", "trend", "ranked", "waterfall",
                  "gauge", "pictograph", "donut", "ring", "bars"}
TEACHING_TYPES = {"schematic", "figure"}
# Strong signals that a segment SPEAKS a number (numbers are spelled out in scripts).
NUMBER_RE = re.compile(
    r"\d|percent|per cent|dollars?|million|billion|thousand|hundred", re.IGNORECASE)


def slide_has_cues(s):
    if s.get("cues"):
        return True
    if any(a.get("cue") for a in s.get("annotations", [])):
        return True
    if any(st.get("cue") for st in s.get("schematic", {}).get("stages", [])):
        return True
    fig = s.get("figure") or {}
    if any(m.get("cue") for m in fig.get("moves", [])) or fig.get("highlight", {}).get("cue"):
        return True
    if any(p.get("cue") for p in fig.get("assemble", {}).get("pieces", [])):
        return True
    return False


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.strip())
    pdir = Path(sys.argv[1]).resolve()
    deck_path = pdir / "deck.json"
    if not deck_path.exists():
        sys.exit(f"no deck.json in {pdir} — author it first (deck/motion playbooks)")
    slides = json.loads(deck_path.read_text())["slides"]
    n = len(slides)

    types = {}
    text_flags = []
    for s in slides:
        t = s.get("type", "?")
        types[t] = types.get(t, 0) + 1
        text_flags.append(t in TEXT_TYPES)

    text_count = sum(text_flags)
    text_pct = 100.0 * text_count / n if n else 0.0
    max_run, run = 0, 0
    for f in text_flags:
        run = run + 1 if f else 0
        max_run = max(max_run, run)

    annotated = sum(1 for s in slides if s.get("annotations"))
    cued = sum(1 for s in slides if slide_has_cues(s))
    dataviz = sum(types.get(t, 0) for t in DATA_VIZ_TYPES)
    teaching = sum(types.get(t, 0) for t in TEACHING_TYPES)
    footage = types.get("footage", 0)
    has_hook = slides[0].get("type") == "hook" if slides else False
    has_punch = types.get("punch", 0) > 0
    teaching_needed = max(1, round(n / 18))

    # Advisory: segments that speak a number while their slide is typography-only.
    number_offenders = []
    script_path = pdir / "script.json"
    if script_path.exists():
        segs = json.loads(script_path.read_text())["segments"]
        slide_by_id = {s["id"]: s for s in slides}
        for seg in segs:
            sl = slide_by_id.get(seg.get("slide"))
            if sl and NUMBER_RE.search(seg.get("text", "")):
                if sl.get("type") in TEXT_TYPES:
                    number_offenders.append(f"{seg.get('slide')} ({sl.get('type')})")

    print(f"deck census — {pdir.name}  ({n} slides)")
    print("  types: " + ", ".join(f"{t}:{c}" for t, c in sorted(types.items(), key=lambda x: -x[1])))
    checks = [
        (f"text-type slides {text_count}/{n} = {text_pct:.0f}% (cap 40%)", text_pct <= 40),
        (f"longest text-type run {max_run} (cap 2)", max_run <= 2),
        (f"schematic/figure slides {teaching} (need ≥{teaching_needed} ≈ one per act)", teaching >= teaching_needed),
        (f"hero cold open (first slide type=hook): {has_hook}; midroll punch present: {has_punch}", has_hook and has_punch),
        (f"annotated slides {annotated}/{n} (need ≥ 1/3)", annotated * 3 >= n),
        (f"slides with authored narration cues {cued} (need ≥ 1; 0 = failed deck)", cued >= 1),
    ]
    ok = True
    for label, passed in checks:
        ok &= passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
    print(f"  [info] data-viz slides: {dataviz} · footage slides: {footage}")
    if number_offenders:
        print(f"  [ADVISORY] segments speaking numbers on text-only slides "
              f"(floor rule 2 — give each a synced data-viz): {', '.join(number_offenders)}")
    print("  FLOOR: " + ("PASS" if ok else "FAIL — fix before render (motion-playbook §4b)"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
