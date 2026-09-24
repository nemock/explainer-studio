#!/usr/bin/env python3
"""Regression: build_spec must REFUSE a figure mark that breaks its kind's field contract.

Run:  python3 tools/test_mark_contract.py [<project_dir> ...]

FigMark (remotion/src/components/Media.tsx) draws circle/box/underline at `at` and
arrow/strike from `from` to `to`, and puts any point it cannot find at the image centre.
Two shapes got past deck_census, slidecheck, qa and validate:

    strike authored as at+w      Product Leadership module 6, first render (5)   drew nothing
    underline authored from/to   modules 3 + 4, published (7)                    line at centre

Asserted here, against a throwaway project:
  - build_spec raises MalformedMarkError naming the slide and the missing field, for both
    shapes and for every route a mark reaches the spec by (figure, footage, a direct
    component), plus an unknown kind and a malformed coordinate;
  - the render path writes BLOCKED-MARKS.md and re-raises, and a later clean build deletes
    it; a Short's block sends the reader to the parent deck its slides are copied from;
  - a deck using every kind correctly still builds, each mark passed through untouched
    apart from the cueFrame build_spec has always added.

Then each project on the command line (default: Product Leadership module 6, whose deck
was fixed after its first render) must build clean through the real build_spec. That call
only reads the project; the guarded render path, which writes into it, is never used on a
real project here. A project that is not on this machine is reported as SKIP, not PASS.
"""
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from explainer2 import remotion_engine as E  # noqa: E402
from explainer2.project import Project  # noqa: E402

DEFAULT_PROJECTS = ["/Volumes/Casima/claudeCode/Product_Leadership_Operators_Guide/module-06"]

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
    print(f"ok    {d.name}: builds clean — {sum(kinds.values())} marks checked {dict(kinds)}")
    checked += 1

# ------------------------------------------------------------------------------------------
if failures:
    print(f"FAIL — {len(failures)} problem(s):")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print(f"PASS — {len(BAD)} malformed marks refused (BLOCKED-MARKS.md written, then cleared), "
      f"{len(GOOD_MARKS)} valid kinds untouched, {checked} real project(s) build clean")
