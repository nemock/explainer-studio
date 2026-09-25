#!/usr/bin/env python3
"""Regression: a Short swaps in a slide's portrait variant (`<field>_9x16`), and never
carries an image-space field measured off the OTHER image.

Run:  PYTHONPATH=src ~/myenv/bin/python3.12 tools/test_shorts_portrait.py

#69's document figures were cropped 2.8:1 for the long-form and copied verbatim into its
Shorts, where they rendered as a thin strip of illegible court text (QA 2026-09-25).
shorts._portrait_slide now builds each lifted slide. Asserted here:
  - no `_9x16` fields: the slide is unchanged (a copy, not the parent's dict);
  - `image_9x16` + `marks_9x16` + `moves_9x16`: all three swap in, and no `_9x16` key
    reaches the Short's deck;
  - `image_9x16` alone: the landscape marks/moves are DROPPED with a warning each, because
    their coordinates were measured off the landscape image;
  - `moves_9x16` alone: applies to the landscape image, landscape marks kept;
  - given the parent dir, a portrait variant carries `imageAspect` (read off the PNG) for
    FigureMarks' viewBox, and a landscape slide never does;
  - deck_census's portrait check reports a malformed `marks_9x16` under that name.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from explainer2.shorts import _portrait_slide  # noqa: E402
from explainer2.remotion_engine import _mark_problems  # noqa: E402

LAND_MARK = [{"kind": "box", "at": [0.72, 0.35], "w": 0.18, "h": 0.14, "cue": "typically ten"}]
LAND_MOVE = [{"to": {"x": 0.72, "y": 0.35, "scale": 1.55}, "cue": "The instruments"}]
TALL_MARK = [{"kind": "box", "at": [0.69, 0.42], "w": 0.26, "h": 0.07, "cue": "typically ten"}]
TALL_MOVE = [{"to": {"x": 0.67, "y": 0.42, "scale": 1.35}, "cue": "The instruments"}]
BASE = {"id": "s10", "type": "figure", "image": "assets/docshots/n9_lives.png",
        "kicker": "k", "marks": LAND_MARK, "moves": LAND_MOVE}

# 1) plain slide: unchanged, but a copy
w = []
s = _portrait_slide(BASE, w)
assert s == BASE and s is not BASE and not w, (s, w)

# 2) full portrait variant
w = []
s = _portrait_slide({**BASE, "image_9x16": "assets/docshots/n9_lives_9x16.png",
                     "marks_9x16": TALL_MARK, "moves_9x16": TALL_MOVE}, w)
assert s["image"].endswith("_9x16.png") and s["marks"] == TALL_MARK and s["moves"] == TALL_MOVE, s
assert not [k for k in s if k.endswith("_9x16")] and not w, (s, w)

# 3) image only: landscape marks/moves must not ride along
w = []
s = _portrait_slide({**BASE, "image_9x16": "assets/docshots/n9_lives_9x16.png"}, w)
assert "marks" not in s and "moves" not in s, s
assert len(w) == 2 and all("dropped" in x for x in w), w

# 4) moves only: a harder zoom on the SAME landscape image
w = []
s = _portrait_slide({**BASE, "moves_9x16": TALL_MOVE}, w)
assert s["image"] == BASE["image"] and s["marks"] == LAND_MARK and s["moves"] == TALL_MOVE, s
assert not w, w

# 4b) with the parent dir, the portrait image's aspect rides along for FigureMarks' viewBox;
#     a landscape slide never gets one (its marks keep the old 16:9 viewBox)
import tempfile  # noqa: E402
from PIL import Image  # noqa: E402
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "assets").mkdir()
    Image.new("RGB", (1311, 1311), "white").save(root / "assets/tall.png")
    w = []
    s = _portrait_slide({**BASE, "image_9x16": "assets/tall.png", "marks_9x16": TALL_MARK,
                         "moves_9x16": TALL_MOVE}, w, root)
    assert s["imageAspect"] == 1.0, s
    assert "imageAspect" not in _portrait_slide(BASE, [], root)

# 5) deck_census labels a bad portrait mark by its own field
bad = [{"kind": "underline", "from": [0.1, 0.5], "to": [0.9, 0.5]}]
probs = [p.replace(": marks", ": marks_9x16", 1) for p in _mark_problems("s10", bad, "marks")]
assert probs and probs[0].startswith("s10: marks_9x16[0] underline is missing `at`"), probs

print("test_shorts_portrait: 6 checks passed")
