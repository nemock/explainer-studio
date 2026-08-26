#!/usr/bin/env python3
"""Regression suite for the Cvg scene map — the blank-card class of bug.

Run:  python3 tools/test_cvg_scene_map.py

Four times now a legal deck type has reached `_circumvent_scene`, carried its content in
fields `CvgScene` does not print, and rendered as a set with a kicker and nothing else:

    stat / statgrid   FMF 2026-08-07 s3, MMT 2026-08-10 s4/s6/s9    fixed 2026-08-12
    reframe           TTD 2026-08-13 s8                             fixed 2026-08-20
    ring              MMT 2026-08-24 s9                             fixed 2026-08-24

Each fix added the one missing branch. This file exists so the NEXT one is caught here
instead of by a blocked publish run: every type the classic map handles is asserted to
produce something printable through the Cvg map too.

`slidecheck.py` catches the same defect at render time, against the built spec. This
catches it at author time, against the map itself, which is the cheaper end.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from explainer2.remotion_engine import _circumvent_scene  # noqa: E402

TEXT_KEYS = ("headline", "word", "term", "definition", "quote", "attrib", "label",
             "title", "mark", "before", "strike", "after")
LIST_KEYS = ("items", "steps", "stats", "points", "events")
PAIR_KEYS = ("left", "right")

failures = []


def printable(fields):
    """Mirrors slidecheck._has_content: kicker/subkicker deliberately excluded, because a
    scene carrying only a kicker IS the blank card we are hunting."""
    for k in TEXT_KEYS:
        if isinstance(fields.get(k), str) and fields[k].strip():
            return True
    for k in LIST_KEYS:
        if fields.get(k):
            return True
    for k in PAIR_KEYS:
        v = fields.get(k)
        if isinstance(v, dict) and any(str(x).strip() for x in v.values() if x is not None):
            return True
    return False


def check(name, slide, expect_text=None, expect_component=None):
    t = slide.get("type")
    headline = slide.get("headline") or slide.get("title") or slide.get("word") or ""
    comp, fields = _circumvent_scene(slide, t, slide.get("kicker", ""),
                                     slide.get("accent", []) or [], headline)
    if not printable(fields):
        failures.append(f"{name}: type {t!r} -> {comp} renders BLANK (fields={fields!r})")
        return
    if expect_component and comp != expect_component:
        failures.append(f"{name}: expected component {expect_component}, got {comp}")
    if expect_text and expect_text not in json.dumps(fields, ensure_ascii=False):
        failures.append(f"{name}: expected {expect_text!r} in rendered fields, got {fields!r}")


# --- the four historical failures, each with the field shape that shipped blank ---------
check("stat (MMT 2026-08-10 s4)",
      {"type": "stat", "kicker": "Story 1", "value": "$287.5M",
       "label": "iRhythm is buying VitalConnect"},
      expect_text="$287.5M")

check("statgrid (FMF 2026-08-07 s3)",
      {"type": "statgrid", "kicker": "reported by Boston Scientific",
       "stats": [{"value": "4", "label": "deaths"},
                 {"value": "2,557", "label": "serious injuries"}]},
      expect_text="2,557")

check("reframe (TTD 2026-08-13 s8)",
      {"type": "reframe", "kicker": "the pivot",
       "before": "a hiring problem", "strike": "hiring", "after": "a categorization problem"},
      expect_component="CvgReframe", expect_text="categorization")

check("ring (MMT 2026-08-24 s9)",
      {"type": "ring", "kicker": "the number the program is aimed at", "value": 12,
       "label": "of eligible patients currently get a thrombectomy"},
      expect_text="12%")

# The kicker-only scene the first draft of slidecheck wrongly passed. Blank is the CORRECT
# outcome here — there is nothing authored to show. It is asserted because a regression that
# started counting the kicker as content would resurrect every bug above by making the
# blank-card check unfalsifiable.
_, _f = _circumvent_scene(
    {"type": "stat", "kicker": "reported by Boston Scientific, as of March 18, 2026"},
    "stat", "reported by Boston Scientific, as of March 18, 2026", [], "")
if printable(_f):
    failures.append("kicker-only stat now counts as content — the blank-card check has "
                    f"been defeated (fields={_f!r})")

# --- % handling: author-supplied suffix must not be doubled ------------------------------
_, f = _circumvent_scene({"type": "ring", "value": "12%", "label": "of patients"},
                         "ring", "", [], "")
if "12%%" in f["headline"] or "12% %" in f["headline"]:
    failures.append(f"ring: doubled percent suffix -> {f['headline']!r}")

_, f = _circumvent_scene({"type": "ring", "value": 0, "label": "of patients"},
                         "ring", "", [], "")
if not f["headline"].startswith("0%"):
    failures.append(f"ring: value 0 dropped (falsy-check bug) -> {f['headline']!r}")

# --- every type the classic map handles must survive the Cvg map -------------------------
SAMPLES = {
    "ring":       {"value": 12, "label": "of patients"},
    "progress":   {"value": 40, "label": "complete"},
    "pictograph": {"filled": 12, "total": 100, "label": "of eligible patients"},
    "funnel":     {"stages": [{"label": "Leads", "value": 100}, {"label": "Demos", "value": 20}]},
    "waterfall":  {"start": {"label": "Start", "value": 100},
                   "steps": [{"label": "Churn", "value": -20}], "end": {"label": "End", "value": 80}},
    "timeline":   {"events": [{"date": "2024", "label": "CE mark"}, {"date": "2026", "label": "De Novo"}]},
    "diagram":    {"bars": [{"label": "Q1", "value": 10}, {"label": "Q2", "value": 14}]},
    "trend":      {"points": [1, 2, 3], "end_label": "up and to the right"},
    "ranked":     {"bars": [{"label": "Medtronic", "value": 41}]},
    "keepcard":   {"label": "Keep this one", "sub": "the card worth saving"},
    "stat":       {"value": "$287.5M", "label": "iRhythm is buying VitalConnect"},
    "statgrid":   {"stats": [{"value": "4", "label": "deaths"}]},
    "reframe":    {"before": "a hiring problem", "strike": "hiring", "after": "a categorization problem"},
    "quote":      {"quote": "We're not going to wait around", "attribution": "Quentin Blackford"},
    "define":     {"term": "De Novo", "definition": "the pathway with no predicate"},
    "list":       {"items": ["one", "two"]},
    "steps":      {"steps": ["first", "second"]},
    "compare":    {"left": {"title": "A", "value": "1"}, "right": {"title": "B", "value": "2"}},
    "punch":      {"word": "STALL"},
    "statement":  {"headline": "a plain line"},
    "hook":       {"headline": "a plain line"},
    "payoff":     {"headline": "a plain line"},
    "highlight":  {"headline": "a plain line", "mark": ["plain"]},
    "cta":        {"headline": "and subscribe", "mark": "papercraft-mmt/mark_mmt.png"},
}
for t, body in SAMPLES.items():
    check(f"sample:{t}", {"type": t, "kicker": "k", **body})

# --- the net: an unknown type carrying content must not render blank ---------------------
check("unknown type with content (the net)",
      {"type": "sankey_9000", "kicker": "some kicker",
       "label": "authored content that must survive"},
      expect_text="authored content that must survive")

# --- coverage: no type in the classic map may be missing from this file ------------------
src = (ROOT / "src/explainer2/remotion_engine.py").read_text()
body = src[src.index("def _scene_for"):]
classic = set()
for m in re.finditer(r'if t (?:==|in) (\("[^)]*"\)|"[^"]+")', body):
    classic |= set(re.findall(r'"([^"]+)"', m.group(1)))
# Types handled above the Cvg dispatch or deliberately excluded from these worlds.
EXEMPT = {"oncamera", "sting", "figure", "footage", "waveform", "schematic", "delta", "flow"}
uncovered = sorted(classic - set(SAMPLES) - EXEMPT)
if uncovered:
    failures.append("classic-map types with no sample in this suite (add one, then a "
                    f"branch in _circumvent_scene if it renders blank): {uncovered}")

# ----------------------------------------------------------------------------------------
if failures:
    print(f"FAIL — {len(failures)} problem(s):")
    for f_ in failures:
        print("  -", f_)
    sys.exit(1)
print(f"PASS — {len(SAMPLES)} types + 4 historical regressions + the net, all render content")
