#!/usr/bin/env python3
"""Regression: build_spec must REFUSE a figure mark or a frame-space annotation that its
renderer cannot draw where it was authored.

Run:  python3 tools/test_mark_contract.py [<project_dir> ...]

FigMark (remotion/src/components/Media.tsx) draws circle/box/underline at `at` and
arrow/strike from `from` to `to`, and puts any point it cannot find at the image centre.
Two shapes got past deck_census, slidecheck, qa and validate:

    strike authored as at+w      Product Leadership module 6, first render (5)   drew nothing
    underline authored from/to   modules 3 + 4, published (7)                    line at centre

AnnotateOverlay (remotion/src/components/Annotate.tsx) reads the same geometry, plus `at`
for a doodle, and puts a missing point at the FRAME centre; a kind it does not know (an
absent one included) and a colour outside green/red/white draw nothing. On published
renders (2026-09-24):

    strike authored as at+w      #67 s14 s29                                     drew nothing
    underline authored from/to   #48 s11 s12 s14 s21, its trust-it-less Short    frame centre
    color amber / navy           ISO 14971 modules 9-12 (24), #48 s11 s13         drew nothing

Amber became a real ink the same day (both overlays), so it is asserted as VALID below; navy
and any other colour outside green/red/white/amber are still refused.

Asserted here, against a throwaway project:
  - build_spec raises MalformedMarkError naming the slide and the missing field, for both
    mark shapes and for every route a mark reaches the spec by (figure, footage, a direct
    component), plus an unknown kind and a malformed coordinate;
  - the same for annotations, on slides of several types: both shipped shapes, an absent and
    an unknown kind, a doodle without `at`, both shipped colours, a malformed coordinate;
    marks and annotations are refused together, in one error;
  - the render path writes BLOCKED-MARKS.md and re-raises, and a later clean build deletes
    it; a Short's block sends the reader to the parent deck its slides are copied from;
  - a deck using every kind correctly still builds, each mark and annotation passed through
    untouched apart from the cueFrame build_spec has always added. A mark's colour is never
    refused (FigMark falls back to the accent), and a slide no segment renders is never
    checked;
  - tools/deck_census.py FAILs a deck carrying either kind of problem, lists every one, and
    stops counting those slides as annotated; a valid deck passes that check.

Then each project on the command line must build clean through the real build_spec. The
default is Product Leadership module 6, whose deck was fixed after its first render (34
marks), and #19, whose 11 annotations cover four kinds including doodles. That call only
reads the project; the guarded render path, which writes into it, is never used on a real
project here. A project that is not on this machine is reported as SKIP, not PASS.
"""
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from explainer2 import remotion_engine as E  # noqa: E402
from explainer2.project import Project  # noqa: E402

DEFAULT_PROJECTS = [
    "/Volumes/Casima/claudeCode/Product_Leadership_Operators_Guide/module-06",
    "/Volumes/Casima/claudeCode/explainer-content/projects/2026-06-14_19_outreach-vs-audience",
]

failures = []


def make_project(d, slides, **data):
    """A throwaway 16:9 plg-guide project at `d`, one 2 s segment per slide. No
    alignment.json, so every cue falls back to its proportional frame, which is all
    build_spec needs. `data` adds project.json keys."""
    d = Path(d)
    (d / "work").mkdir(parents=True)
    (d / "project.json").write_text(json.dumps({
        "title": "t", "slug": "s", "aspect": "16:9", "width": 1920, "height": 1080,
        "fps": 30, "theme": "plg-guide", **data}))
    write_deck(d, slides)
    segs = [{"id": i, "slide": s["id"], "start": 2.0 * i, "end": 2.0 * (i + 1)}
            for i, s in enumerate(slides)]
    (d / "work" / "segments.json").write_text(json.dumps(
        {"duration": 2.0 * len(slides), "segments": segs}))
    return Project.load(d)


def write_deck(d, slides):
    (Path(d) / "deck.json").write_text(json.dumps({"slides": slides}))


def figure(sid, *marks):
    return {"id": sid, "type": "figure", "image": "x.png", "marks": list(marks)}


# --- the two shapes that shipped, and the other ways a mark can break the contract ------
BAD = [
    (figure("s01", {"kind": "strike", "at": [0.5, 0.42], "w": 0.3, "cue": "crossed out"}),
     "s01: marks[0] strike is missing `from` and `to`"),          # module 6, first render
    (figure("s02", {"kind": "underline", "from": [0.3, 0.6], "to": [0.7, 0.6], "cue": "line"}),
     "s02: marks[0] underline is missing `at`"),                  # modules 3 + 4, published
    (figure("s03", {"kind": "circle", "at": [0.4, 0.5], "w": 0.2},    # valid, must not be named
                   {"kind": "arrow", "from": [0.1, 0.1]}),
     "s03: marks[1] arrow is missing `to`"),
    ({"id": "s04", "type": "footage", "image": "x.mp4", "marks": [{"kind": "box", "at": [0.5]}]},
     "s04: marks[0] box `at` must be an [x, y] pair"),
    ({"id": "s05", "component": "Figure",
      "fields": {"image": "x.png", "marks": [{"kind": "highlight", "at": [0.5, 0.5]}]}},
     "s05: marks[0] has kind 'highlight'"),
]

GOOD_MARKS = [
    {"kind": "circle", "at": [0.4, 0.5], "w": 0.2, "h": 0.3, "color": "green", "cue": "c"},
    {"kind": "box", "at": [0.6, 0.4], "w": 0.3, "h": 0.2},
    {"kind": "underline", "at": [0.5, 0.62], "w": 0.3, "h": 0.05},  # h ignored; 8 real decks
    {"kind": "arrow", "from": [0.1, 0.1], "to": [0.4, 0.45], "color": "red"},
    {"kind": "strike", "from": [0.3, 0.5], "to": [0.7, 0.5]},
    {"at": [0.5, 0.5], "w": 0.25},                  # no kind: FigMark draws a circle, so legal
]
GOOD = [figure("g01", *GOOD_MARKS),
        {"id": "g02", "type": "footage", "image": "x.mp4", "marks": GOOD_MARKS[:1]},
        {"id": "g03", "component": "Figure", "fields": {"image": "x.png", "marks": GOOD_MARKS[3:5]}}]

with tempfile.TemporaryDirectory() as tmp:
    proj = make_project(Path(tmp) / "proj", [s for s, _ in BAD])

    # 1) build_spec itself refuses, naming every bad mark once and no good one
    try:
        E.build_spec(proj)
        failures.append("bad deck: build_spec returned a spec instead of raising")
    except E.MalformedMarkError as e:
        if len(e.problems) != len(BAD):
            failures.append(f"bad deck: expected {len(BAD)} problems, got {len(e.problems)}: "
                            f"{e.problems!r}")
        for _, expect in BAD:
            if not any(p.startswith(expect) for p in e.problems):
                failures.append(f"bad deck: no problem line starts with {expect!r}")
            if expect not in str(e):
                failures.append(f"bad deck: the error text (what the render log shows) "
                                f"omits {expect!r}")
        if any(p.startswith("s03: marks[0]") for p in e.problems):
            failures.append("bad deck: the valid circle on s03 was reported")
        print("refusal, as the render log shows it:")
        print("  " + str(e).replace("\n", "\n  "))

    # 2) the render path turns it into a block: BLOCKED-MARKS.md + re-raise
    blocked = proj.dir / E.MARKS_BLOCKED_NAME
    lines = []
    try:
        E._build_spec_guarded(proj, log=lines.append)
        failures.append("render path: returned a spec instead of raising")
    except E.MalformedMarkError:
        pass
    if not blocked.exists():
        failures.append(f"render path: {blocked.name} was not written")
    else:
        text = blocked.read_text()
        for s, _ in BAD:
            if f"- {s['id']}: marks[" not in text:
                failures.append(f"render path: {blocked.name} does not name {s['id']}")
    if not any(l.startswith("marks-guard: BLOCKED") for l in lines):
        failures.append(f"render path: no BLOCKED log line (got {lines!r})")

    # 3) fix every slide in place: the same project builds, and the stale block clears itself
    write_deck(proj.dir, [figure(s["id"], GOOD_MARKS[0]) for s, _ in BAD])
    lines = []
    try:
        E._build_spec_guarded(proj, log=lines.append)
    except E.MalformedMarkError as e:
        failures.append(f"fixed deck: still refused: {e.problems!r}")
    if blocked.exists():
        failures.append(f"fixed deck: stale {blocked.name} was not deleted")
    if not any("cleared" in l for l in lines):
        failures.append(f"fixed deck: no 'cleared' log line (got {lines!r})")

with tempfile.TemporaryDirectory() as tmp:
    # 4) valid marks of every kind, on every route, pass through untouched
    proj = make_project(Path(tmp) / "proj", GOOD)
    try:
        spec = E.build_spec(proj)
    except E.MalformedMarkError as e:
        failures.append(f"good deck: refused: {e.problems!r}")
        spec = {"scenes": []}
    want = {"g01": GOOD_MARKS, "g02": GOOD_MARKS[:1], "g03": GOOD_MARKS[3:5]}
    got = {s["id"]: sc["fields"].get("marks") for s, sc in zip(GOOD, spec["scenes"])}
    for sid, marks in want.items():
        out = got.get(sid) or []
        if [{k: v for k, v in m.items() if k != "cueFrame"} for m in out] != marks:
            failures.append(f"good deck {sid}: marks changed on the way through: {out!r}")
        if not all(isinstance(m.get("cueFrame"), int) for m in out):
            failures.append(f"good deck {sid}: a mark lost its cueFrame: {out!r}")

with tempfile.TemporaryDirectory() as tmp:
    # 5) a Short copies its slides from the parent on every run, so its block must send the
    #    reader to the parent's deck and the shorts command, not to the Short's own deck
    parent = Path(tmp).resolve() / "parent"
    proj = make_project(parent / "shorts" / "cut-a", [BAD[1][0]], derived_from="parent")
    try:
        E._build_spec_guarded(proj, log=lambda m: None)
        failures.append("short: returned a spec instead of raising")
    except E.MalformedMarkError:
        pass
    blocked = proj.dir / E.MARKS_BLOCKED_NAME
    text = blocked.read_text() if blocked.exists() else ""
    if f"explainer2 shorts '{parent}' --only cut-a" not in text:
        failures.append(f"short: {blocked.name} does not give the parent's shorts command")
    if "parent's `deck.json`" not in text:
        failures.append(f"short: {blocked.name} does not send the reader to the parent deck")


# --- frame-space annotations: the same contract, plus doodle, plus colour (2026-09-24) ----
def annotated(sid, typ, *anns, **extra):
    """A slide of `typ` carrying `anns`. Annotations draw over any scene, so the types vary."""
    return {"id": sid, "type": typ, "headline": "h", **extra, "annotations": list(anns)}


BAD_ANNS = [
    (annotated("a01", "compare", {"kind": "strike", "at": [0.28, 0.5], "w": 0.22, "h": 0.1,
                                  "cue": "came and went"}),
     "a01: annotations[0] strike is missing `from` and `to`"),    # #67 s14 s29: drew nothing
    (annotated("a02", "quote", {"kind": "underline", "from": [0.2, 0.66], "to": [0.8, 0.66],
                                "color": "red", "cue": "screws up"}),
     "a02: annotations[0] underline is missing `at`"),            # #48: at the frame centre
    (annotated("a03", "statement", {"at": [0.5, 0.5], "w": 0.2}),  # a mark would be a circle
     "a03: annotations[0] has no `kind`"),
    (annotated("a04", "punch", {"kind": "highlight", "at": [0.5, 0.5]}),
     "a04: annotations[0] has kind 'highlight'"),
    (annotated("a05", "figure", {"kind": "doodle", "name": "misc/star", "w": 0.1},
               image="x.png"),
     "a05: annotations[0] doodle is missing `at`"),
    (annotated("a06", "stat", {"kind": "circle", "at": [0.5, 0.4], "color": "orange"}),
     "a06: annotations[0] circle has color 'orange'"),            # no such ink: invisible
    (annotated("a07", "statement", {"kind": "circle", "at": [0.3, 0.5]},   # valid, not named
               {"kind": "arrow", "from": [0.5, 0.82], "to": [0.5, 0.62], "color": "navy"}),
     "a07: annotations[1] arrow has color 'navy'"),               # #48 s13: right place, unseen
    (annotated("a08", "statement", {"kind": "box", "at": "centre"}),
     "a08: annotations[0] box `at` must be an [x, y] pair"),
    (BAD[1][0], BAD[1][1]),                   # a bad figure mark, refused in the same error
]

GOOD_ANNS = [
    {"kind": "circle", "at": [0.4, 0.5], "w": 0.2, "h": 0.3, "color": "green", "cue": "c",
     "label": "here"},
    {"kind": "box", "at": [0.6, 0.4], "w": 0.3, "h": 0.2, "color": "red"},
    {"kind": "underline", "at": [0.5, 0.62], "w": 0.3, "h": 0.05, "color": "white"},
    {"kind": "arrow", "from": [0.1, 0.1], "to": [0.4, 0.45]},
    {"kind": "strike", "from": [0.3, 0.5], "to": [0.7, 0.5], "color": None},  # null: default
    {"kind": "doodle", "name": "misc/star", "at": [0.7, 0.3], "w": 0.12, "rotate": -8,
     "reveal": "wipe", "color": "white"},
    {"kind": "circle", "at": [0.2, 0.7], "w": 0.1, "color": "amber"},  # ISO 14971's ink
]
NAVY_MARK = {"kind": "circle", "at": [0.5, 0.5], "color": "navy"}   # FigMark: the accent
GOOD_ANN_SLIDES = [annotated("g01", "statement", *GOOD_ANNS[:3]),
                   dict(annotated("g02", "figure", *GOOD_ANNS[3:], image="x.png"),
                        marks=[NAVY_MARK])]
# In deck.json but in no segment, so never rendered: never checked, never refused.
UNRENDERED = annotated("u01", "statement", {"kind": "strike", "at": [0.5, 0.5]})


def census(d):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "deck_census.py"), str(d)],
                       capture_output=True, text=True)
    return r.stdout + r.stderr


with tempfile.TemporaryDirectory() as tmp:
    proj = make_project(Path(tmp) / "proj", [s for s, _ in BAD_ANNS])

    # 6) build_spec refuses every bad annotation and the bad mark, once each, in one error
    try:
        E.build_spec(proj)
        failures.append("bad annotations: build_spec returned a spec instead of raising")
    except E.MalformedMarkError as e:
        if len(e.problems) != len(BAD_ANNS):
            failures.append(f"bad annotations: expected {len(BAD_ANNS)} problems, got "
                            f"{len(e.problems)}: {e.problems!r}")
        for _, expect in BAD_ANNS:
            if not any(p.startswith(expect) for p in e.problems):
                failures.append(f"bad annotations: no problem line starts with {expect!r}")
        if any(p.startswith("a07: annotations[0]") for p in e.problems):
            failures.append("bad annotations: the valid circle on a07 was reported")
        if not any("frame centre" in p for p in e.problems):
            failures.append("bad annotations: no line says the annotation lands on the frame "
                            "centre")
        print("annotation refusal, as the render log shows it:")
        print("  " + str(e).replace("\n", "\n  "))

    # 7) the render path: BLOCKED-MARKS.md names the annotations and explains the overlay
    blocked = proj.dir / E.MARKS_BLOCKED_NAME
    try:
        E._build_spec_guarded(proj, log=lambda m: None)
        failures.append("annotation render path: returned a spec instead of raising")
    except E.MalformedMarkError:
        pass
    text = blocked.read_text() if blocked.exists() else ""
    for s, _ in BAD_ANNS[:-1]:
        if f"- {s['id']}: annotations[" not in text:
            failures.append(f"annotation render path: {blocked.name} does not name {s['id']}")
    if "AnnotateOverlay" not in text or "`doodle`" not in text:
        failures.append(f"annotation render path: {blocked.name} does not explain the "
                        f"annotation overlay or its doodle row")

    # 8) the census fails the same deck, lists every problem, and counts only a07 (its circle
    #    draws) as annotated
    out = census(proj.dir)
    if f"[FAIL] marks/annotations that would draw in the wrong place or not at all: " \
       f"{len(BAD_ANNS)}" not in out:
        failures.append(f"census: no FAIL line for {len(BAD_ANNS)} problems:\n{out}")
    for _, expect in BAD_ANNS:
        if expect not in out:
            failures.append(f"census: does not list {expect!r}")
    if f"annotated slides 1/{len(BAD_ANNS)}" not in out:
        failures.append(f"census: malformed marks/annotations still count as annotated:\n{out}")

    # 9) fixed in place: builds, and the stale block clears itself
    write_deck(proj.dir, [annotated(s["id"], "statement", GOOD_ANNS[0]) for s, _ in BAD_ANNS])
    try:
        E._build_spec_guarded(proj, log=lambda m: None)
    except E.MalformedMarkError as e:
        failures.append(f"fixed annotations: still refused: {e.problems!r}")
    if blocked.exists():
        failures.append(f"fixed annotations: stale {blocked.name} was not deleted")

with tempfile.TemporaryDirectory() as tmp:
    # 10) valid annotations of every kind pass through untouched; a mark's colour is free
    proj = make_project(Path(tmp) / "proj", GOOD_ANN_SLIDES)
    out = census(proj.dir)
    if "[PASS] marks/annotations that would draw in the wrong place or not at all: none" \
            not in out or "annotated slides 2/2" not in out:
        failures.append(f"census, valid deck: expected a PASS and 2/2 annotated:\n{out}")
    write_deck(proj.dir, GOOD_ANN_SLIDES + [UNRENDERED])
    try:
        spec = E.build_spec(proj)
    except E.MalformedMarkError as e:
        failures.append(f"good annotations: refused: {e.problems!r}")
        spec = {"scenes": []}
    want = {"g01": GOOD_ANNS[:3], "g02": GOOD_ANNS[3:]}
    got = {s["id"]: sc.get("annotations") for s, sc in zip(GOOD_ANN_SLIDES, spec["scenes"])}
    for sid, anns in want.items():
        out = got.get(sid) or []
        if [{k: v for k, v in a.items() if k != "cueFrame"} for a in out] != anns:
            failures.append(f"good annotations {sid}: changed on the way through: {out!r}")
        if not all(isinstance(a.get("cueFrame"), int) for a in out):
            failures.append(f"good annotations {sid}: an annotation lost its cueFrame: {out!r}")
    g02 = spec["scenes"][1]["fields"].get("marks") if len(spec["scenes"]) > 1 else None
    if [{k: v for k, v in m.items() if k != "cueFrame"} for m in (g02 or [])] != [NAVY_MARK]:
        failures.append(f"good annotations: the navy figure mark did not pass through: {g02!r}")

# --- real projects: must build clean ------------------------------------------------------
checked = 0
for p in sys.argv[1:] or DEFAULT_PROJECTS:
    d = Path(p)
    if not ((d / "deck.json").exists() and (d / "work" / "segments.json").exists()):
        print(f"SKIP  {d.name}: no deck.json + work/segments.json on this machine")
        continue
    try:
        spec = E.build_spec(Project.load(d))
    except E.MalformedMarkError as e:
        failures.append(f"{d.name}: refused — {e}")
        continue
    kinds = Counter(m.get("kind") or "circle" for sc in spec["scenes"]
                    for m in (sc["fields"].get("marks") or []))
    akinds = Counter(a.get("kind") for sc in spec["scenes"] for a in (sc.get("annotations") or []))
    print(f"ok    {d.name}: builds clean — {sum(kinds.values())} marks checked {dict(kinds)}, "
          f"{sum(akinds.values())} annotations checked {dict(akinds)}")
    checked += 1

# ------------------------------------------------------------------------------------------
if failures:
    print(f"FAIL — {len(failures)} problem(s):")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print(f"PASS — {len(BAD)} malformed marks and {len(BAD_ANNS) - 1} malformed annotations refused "
      f"(BLOCKED-MARKS.md written, then cleared; the census fails them too), "
      f"{len(GOOD_MARKS)} valid marks and {len(GOOD_ANNS)} valid annotations (every kind and "
      f"ink) untouched, "
      f"{checked} real project(s) build clean")
