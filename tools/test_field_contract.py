#!/usr/bin/env python3
"""Regression: build_spec must REFUSE an authored field that its Paper* component never
receives, and the two drops that prompted the guard must stay fixed.

Run:  python3 tools/test_field_contract.py [<project_dir> ...]

The paper type map (_papercraft_component in src/explainer2/remotion_engine.py) builds
each Paper* component's fields from the slide, and a field it did not pass along vanished
without a word: no error, a passing census, a successful render. Two shipped that way on
the Product Leadership series, found 2026-09-26:

    compare `title` + `accent`   modules 5 + 6 (16), 5 on #55               no header line
    highlight `mark`             modules 1, 3, 4 + 6 (14), 12 on the deep dives   plain ink

Asserted here, against throwaway projects:
  - the type map: a highlight's `mark` becomes PaperStatement's accent on every theme that
    reaches the paper map (and `accent` still works without one), and a compare or a delta
    hands `title` and `accent` to PaperCompare;
  - build_spec raises DroppedFieldError naming the slide, the field and the component, for
    each shape found on published decks: a compare's subkicker, a quote's kicker, a quote's
    headline shadowed by its `quote`, a closing card's badge, a hook's marks, a punch's
    subkicker;
  - no false positives: a value equal to its default, two fields carrying the same words,
    the fields build_spec, the presenter and Shorts read themselves, a classic component,
    a direct-component slide, and the bad deck again on a non-paper theme;
  - the render path writes BLOCKED-FIELDS.md and re-raises, clears a stale BLOCKED-MARKS.md
    (every mark passed to get that far), and a later clean build deletes it; a Short's block
    sends the reader to the parent deck;
  - tools/deck_census.py FAILs the bad deck, listing every problem, and passes the good one;
  - the component side, which the engine guard cannot see: every field the map hands a
    Paper* component is read in that component's source (remotion/src/components), apart
    from the gaps listed in KNOWN_UNREAD below.

Then each project on the command line must build clean through the real build_spec, pass
that census line, and deliver every compare title and highlight mark it authors. The
default is Product Leadership modules 5 and 6, which carry them. That only reads the
project. A project that is not on this machine is reported as SKIP, not PASS.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from explainer2 import remotion_engine as E  # noqa: E402
from explainer2.project import Project  # noqa: E402

DEFAULT_PROJECTS = [
    "/Volumes/Casima/claudeCode/Product_Leadership_Operators_Guide/module-05",
    "/Volumes/Casima/claudeCode/Product_Leadership_Operators_Guide/module-06",
]
# The themes whose slides reach _papercraft_component. circumvent is listed there too, but
# its own Cvg map claims every slide first.
PAPER_MAP_THEMES = ("plg-guide", "nemock-deep-dive", "wte-guide")
FIELDS_LINE = "authored fields their paper component never receives"

failures = []


def make_project(d, slides, **data):
    """A throwaway 16:9 plg-guide project at `d`, one 2 s segment per slide. No
    alignment.json, so every cue falls back to its proportional frame, which is all
    build_spec needs. `data` adds or overrides project.json keys."""
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


def census(d):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "deck_census.py"), str(d)],
                       capture_output=True, text=True)
    return r.stdout + r.stderr


# --- 1) the two fixes, on the type map itself -----------------------------------------
LEFT = {"title": "The email", "value": "Every term scores", "kind": "bad"}
RIGHT = {"title": "The bet", "value": "Believing isn't a number", "kind": "good"}
TITLE = "Scoring the thing your strategy is built on"          # module 6 s28, published
DELTA_TITLE = "Fifteen where there used to be two and a half."  # #56 s37, published
for theme in PAPER_MAP_THEMES:
    comp, f = E._scene_for({"type": "highlight", "headline": "It was one window.",
                            "mark": ["one window"]}, theme=theme)
    if comp != "PaperStatement" or f.get("accent") != ["one window"]:
        failures.append(f"{theme}: highlight `mark` did not become the accent: {comp} {f!r}")
    comp, f = E._scene_for({"type": "highlight", "headline": "It was one window.",
                            "accent": ["window"]}, theme=theme)
    if f.get("accent") != ["window"]:
        failures.append(f"{theme}: a highlight with `accent` and no `mark` lost it: {f!r}")
    comp, f = E._scene_for({"type": "compare", "title": TITLE, "accent": ["your strategy"],
                            "left": LEFT, "right": RIGHT}, theme=theme)
    if comp != "PaperCompare" or f.get("title") != TITLE or f.get("accent") != ["your strategy"]:
        failures.append(f"{theme}: compare `title`/`accent` did not reach PaperCompare: "
                        f"{comp} {f!r}")
    # delta renders through the same component and carries the same header (#56 s37)
    comp, f = E._scene_for({"type": "delta", "from": "2.5%", "from_label": "October 2025",
                            "to": "15.8%", "to_label": "1 July 2026", "title": DELTA_TITLE,
                            "accent": ["two and a half"]}, theme=theme)
    if comp != "PaperCompare" or f.get("title") != DELTA_TITLE or f.get("accent") != ["two and a half"]:
        failures.append(f"{theme}: delta `title`/`accent` did not reach PaperCompare: "
                        f"{comp} {f!r}")


# --- 2) the shapes found on published decks, each refused -------------------------------
# (slide, the field it drops, the problem line that must name it)
BAD = [
    ({"id": "b01", "type": "compare", "title": TITLE, "left": LEFT, "right": RIGHT,
      "subkicker": "a line under the trays"}, "subkicker",         # PLG module 4 s15 s23
     "b01: `subkicker` is authored on this compare slide, but PaperCompare never receives it"),
    ({"id": "b02", "type": "quote", "kicker": "THE LINE", "quote": "the words",
      "attribution": "someone"}, "kicker",                         # PLG module 1 s42
     "b02: `kicker` is authored on this quote slide, but PaperStatement never receives it"),
    ({"id": "b03", "type": "quote", "quote": "the words", "headline": "other words"},
     "headline",                                                   # shadowed by `quote`
     "b03: `headline` is authored on this quote slide, but PaperStatement never receives it"),
    ({"id": "b04", "type": "payoff", "headline": "Like and subscribe",
      "badge": "plg_like_subscribe.png"}, "badge",                 # PLG modules 1-3
     "b04: `badge` is authored on this payoff slide, but PaperBookCTA never receives it"),
    ({"id": "b05", "type": "hook", "headline": "h", "image": "x.png",
      "marks": [{"kind": "circle", "at": [0.5, 0.5]}]}, "marks",   # #55 and #49
     "b05: `marks` is authored on this hook slide, but PaperHook never receives it"),
    ({"id": "b06", "type": "punch", "word": "No.", "subkicker": "a line under the word"},
     "subkicker",                                                  # PLG module 1 s10 s32
     "b06: `subkicker` is authored on this punch slide, but PaperPunch never receives it"),
]
# The same slides, same ids, with the dropped field deleted: the fix a deck author makes.
FIXED = [{k: v for k, v in s.items() if k != field} for s, field, _ in BAD]

# Every field on these arrives, or is read by something other than the type map.
GOOD = [
    {"id": "g01", "type": "compare", "kicker": "THE TEST", "title": TITLE,
     "accent": ["your strategy"], "left": LEFT, "right": RIGHT,
     "cues": {"l": "the email", "r": "the bet"}, "source": "Source",
     "source_url": "https://example.com", "transition": "tear",
     "annotations": [{"kind": "circle", "at": [0.5, 0.5]}]},
    {"id": "g02", "type": "highlight", "headline": "It was one window.", "mark": ["one window"]},
    # `set` equals the default monitor: taking it away changes nothing, but it is read
    {"id": "g03", "type": "oncamera", "set": "papercraft/desk_monitor.png", "video": "take.mp4",
     "screen": {"x": 0.3, "y": 0.2, "w": 0.4, "h": 0.4}},
    # the same words in two fields: the `word` wins, and the shadowed `headline` says
    # nothing the screen does not already show, so it is a duplicate, not a drop
    {"id": "g04", "type": "punch", "word": "Focus.", "headline": "Focus."},
    {"id": "g05", "type": "statement", "headline": "h", "chibi": "wave", "chibiSide": "left",
     "chibiFlip": True},
    # classic Figure: not a paper component, so not this guard's to judge
    {"id": "g06", "type": "figure", "image": "x.png", "title": "t", "caption": "c",
     "image_9x16": "y.png", "marks_9x16": [{"kind": "circle", "at": [0.5, 0.5]}],
     "note_to_self": "not a paper slide"},
    # a direct component's fields are its own
    {"id": "g07", "component": "PaperAtom", "fields": {"anything": 1}, "stray": "x"},
]

with tempfile.TemporaryDirectory() as tmp:
    proj = make_project(Path(tmp) / "proj", [s for s, _, _ in BAD])

    # build_spec refuses, naming every drop once
    try:
        E.build_spec(proj)
        failures.append("bad deck: build_spec returned a spec instead of raising")
    except E.DroppedFieldError as e:
        if len(e.problems) != len(BAD):
            failures.append(f"bad deck: expected {len(BAD)} problems, got {len(e.problems)}: "
                            f"{e.problems!r}")
        for _, _, expect in BAD:
            if not any(p.startswith(expect) for p in e.problems):
                failures.append(f"bad deck: no problem line starts with {expect!r}")
            if expect not in str(e):
                failures.append(f"bad deck: the error text omits {expect!r}")
        print("refusal, as the render log shows it:")
        print("  " + str(e).replace("\n", "\n  "))

    # the render path: BLOCKED-FIELDS.md + re-raise, and a stale marks block is cleared
    blocked = proj.dir / E.FIELDS_BLOCKED_NAME
    stale_marks = proj.dir / E.MARKS_BLOCKED_NAME
    stale_marks.write_text("# BLOCKED: stale, from a render before the marks were fixed\n")
    lines = []
    try:
        E._build_spec_guarded(proj, log=lines.append)
        failures.append("render path: returned a spec instead of raising")
    except E.DroppedFieldError:
        pass
    if not blocked.exists():
        failures.append(f"render path: {blocked.name} was not written")
    else:
        text = blocked.read_text()
        for s, _, _ in BAD:
            if f"- {s['id']}: `" not in text:
                failures.append(f"render path: {blocked.name} does not name {s['id']}")
        if "_papercraft_component" not in text or "Ask the operator" not in text:
            failures.append(f"render path: {blocked.name} does not explain the type map or "
                            f"the engine-change case")
    if stale_marks.exists():
        failures.append(f"render path: the stale {stale_marks.name} survived a build whose "
                        f"marks all passed")
    if not any(l.startswith("fields-guard: BLOCKED") for l in lines):
        failures.append(f"render path: no BLOCKED log line (got {lines!r})")

    # the census fails the same deck and lists every problem
    out = census(proj.dir)
    if f"[FAIL] {FIELDS_LINE}: {len(BAD)}" not in out:
        failures.append(f"census: no FAIL line for {len(BAD)} dropped fields:\n{out}")
    for _, _, expect in BAD:
        if expect not in out:
            failures.append(f"census: does not list {expect!r}")

    # fixed in place (same ids, dropped fields deleted): builds, and the block clears itself
    write_deck(proj.dir, FIXED)
    lines = []
    try:
        E._build_spec_guarded(proj, log=lines.append)
    except (E.DroppedFieldError, E.MalformedMarkError) as e:
        failures.append(f"fixed deck: still refused: {e}")
    if blocked.exists():
        failures.append(f"fixed deck: stale {blocked.name} was not deleted")
    if not any(l.startswith("fields-guard:") and "cleared" in l for l in lines):
        failures.append(f"fixed deck: no 'cleared' log line (got {lines!r})")

with tempfile.TemporaryDirectory() as tmp:
    # nothing dropped: builds, and the census passes the check. The guard names nothing
    # here even slide by slide, so no problem can hide behind a missing segment.
    proj = make_project(Path(tmp) / "proj", GOOD)
    for s in GOOD:
        for p in E._dropped_field_problems(s["id"], s, "plg-guide"):
            failures.append(f"good deck: false positive: {p}")
    try:
        E.build_spec(proj)
    except (E.DroppedFieldError, E.MalformedMarkError) as e:
        failures.append(f"good deck: refused: {e}")
    if f"[PASS] {FIELDS_LINE}: none" not in census(proj.dir):
        failures.append("census: the good deck did not pass the dropped-field check")

with tempfile.TemporaryDirectory() as tmp:
    # the bad deck on a non-paper theme: every slide goes to a classic component, which
    # this guard does not judge
    proj = make_project(Path(tmp) / "proj", [s for s, _, _ in BAD], theme="")
    try:
        E.build_spec(proj)
    except E.DroppedFieldError as e:
        failures.append(f"non-paper theme: refused, but no paper component is involved: {e}")

with tempfile.TemporaryDirectory() as tmp:
    # a Short's slides are copied from the parent on every run, so its block must send the
    # reader to the parent's deck and the shorts command, not to the Short's own deck
    parent = Path(tmp).resolve() / "parent"
    proj = make_project(parent / "shorts" / "cut-a", [BAD[0][0]], derived_from="parent")
    try:
        E._build_spec_guarded(proj, log=lambda m: None)
        failures.append("short: returned a spec instead of raising")
    except E.DroppedFieldError:
        pass
    blocked = proj.dir / E.FIELDS_BLOCKED_NAME
    text = blocked.read_text() if blocked.exists() else ""
    if f"explainer2 shorts '{parent}' --only cut-a" not in text:
        failures.append(f"short: {blocked.name} does not give the parent's shorts command")
    if "parent's `deck.json`" not in text:
        failures.append(f"short: {blocked.name} does not send the reader to the parent deck")

# --- 3) the component side: a field the map hands over that the component never reads ---
# The engine guard sees what a component RECEIVES. Half of the compare bug was the other
# side: PaperCompare was never written to read a title. This reads each Paper* component's
# source and asks the same question of it. KNOWN_UNREAD are the gaps still open, left for
# the operator because closing them changes how shipped slides look; a fix that reads the
# field must delete its entry here (PaperReframe's `strike` was the first, 2026-09-27).
KNOWN_UNREAD = {
    ("PaperBookCTA", "accent"): "draws the closing headline in plain ink (41 closing cards "
                                "and Short outros author one)",
}
PROBES = [
    {"type": "statement", "headline": "h"}, {"type": "highlight", "headline": "h", "mark": ["h"]},
    {"type": "quote", "quote": "q", "attribution": "a"},
    {"type": "define", "term": "t", "definition": "d"}, {"type": "punch", "word": "w"},
    {"type": "compare", "title": "t", "left": LEFT, "right": RIGHT},
    {"type": "delta", "from": 1, "to": 2}, {"type": "reframe", "before": "b", "after": "a"},
    {"type": "statgrid", "stats": [{"value": "1", "label": "l"}]},
    {"type": "timeline", "events": [{"date": "d", "label": "l"}]}, {"type": "stat", "value": "40%"},
    {"type": "steps", "steps": ["a"]}, {"type": "list", "items": ["a"]},
    {"type": "trend", "points": [1, 2]}, {"type": "ring", "value": 40},
    {"type": "keepcard", "image": "x.png", "label": "l"}, {"type": "payoff", "headline": "h"},
    {"type": "hook", "set": "s.png", "headline": "h"}, {"type": "hook", "headline": "h"},
    {"type": "oncamera", "video": "v.mp4"},
]
component_src = {}
for tsx in sorted((ROOT / "remotion" / "src" / "components").glob("*.tsx")):
    text = tsx.read_text()
    for m in re.finditer(r"export const (\w+)\s*:\s*React\.FC", text):
        nxt = re.search(r"\nexport const ", text[m.end():])
        component_src[m.group(1)] = text[m.start():m.end() + nxt.start()] if nxt else text[m.start():]
handed = {}
for p in PROBES:
    comp, fields = E._scene_for(p, theme="plg-guide")
    if comp.startswith("Paper"):
        handed.setdefault(comp, set()).update(fields)
for comp, keys in sorted(handed.items()):
    body = component_src.get(comp)
    if body is None:
        failures.append(f"component side: no `export const {comp}: React.FC` in "
                        f"remotion/src/components")
        continue
    for k in sorted(keys):
        read = re.search(rf"fields\??\.{k}\b|fields\[['\"]{k}['\"]\]", body)
        if not read and (comp, k) not in KNOWN_UNREAD:
            failures.append(f"component side: the map hands {comp} `{k}`, which it never reads")
        if read and (comp, k) in KNOWN_UNREAD:
            failures.append(f"component side: {comp} reads `{k}` now; delete its KNOWN_UNREAD "
                            f"entry")
print(f"component side: {sum(len(k) for k in handed.values())} fields handed to {len(handed)} "
      f"Paper* components; known unread: "
      + "; ".join(f"{c}.{k} {why}" for (c, k), why in KNOWN_UNREAD.items()))

# --- 4) real projects: build clean, and every compare title and highlight mark arrives --
STINGS = ("PaperSting", "BRGPaperSting", "BrandSting", "CvgTitle")
checked = 0
for p in sys.argv[1:] or DEFAULT_PROJECTS:
    d = Path(p)
    if not ((d / "deck.json").exists() and (d / "work" / "segments.json").exists()):
        print(f"SKIP  {d.name}: no deck.json + work/segments.json on this machine")
        continue
    try:
        spec = E.build_spec(Project.load(d))
    except (E.DroppedFieldError, E.MalformedMarkError) as e:
        failures.append(f"{d.name}: refused — {e}")
        continue
    slides = {s["id"]: s for s in json.loads((d / "deck.json").read_text())["slides"]}
    segs = json.loads((d / "work" / "segments.json").read_text())["segments"]
    off = 1 if spec["scenes"] and spec["scenes"][0]["component"] in STINGS else 0
    titles = marks = 0
    for seg, sc in zip(segs, spec["scenes"][off:]):
        s, f = slides.get(seg["slide"], {}), sc["fields"]
        if sc["component"] == "PaperCompare" and s.get("title"):
            titles += 1
            if f.get("title") != s["title"] or f.get("accent") != (s.get("accent") or []):
                failures.append(f"{d.name} {s['id']}: compare title/accent did not arrive: {f!r}")
        if sc["component"] == "PaperStatement" and s.get("type") == "highlight" and s.get("mark"):
            marks += 1
            if f.get("accent") != s["mark"]:
                failures.append(f"{d.name} {s['id']}: highlight mark did not arrive: {f!r}")
    if f"[PASS] {FIELDS_LINE}: none" not in census(d):
        failures.append(f"{d.name}: the census dropped-field check did not pass")
    print(f"ok    {d.name}: builds clean — {titles} compare titles and {marks} highlight "
          f"marks delivered")
    checked += 1

# ------------------------------------------------------------------------------------------
if failures:
    print(f"FAIL — {len(failures)} problem(s):")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print(f"PASS — compare and delta titles and highlight marks reach their paper components on "
      f"{len(PAPER_MAP_THEMES)} themes; {len(BAD)} dropped fields refused (BLOCKED-FIELDS.md "
      f"written, then cleared; the census fails them too); {len(GOOD)} slides with nothing "
      f"dropped pass; {len(handed)} Paper* components read what they are handed "
      f"({len(KNOWN_UNREAD)} known gap{'' if len(KNOWN_UNREAD) == 1 else 's'}); "
      f"{checked} real project(s) build clean")
