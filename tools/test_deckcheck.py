#!/usr/bin/env python3
"""deckcheck: what can be known about a deck before anyone records it.

Run:  python3 tools/test_deckcheck.py

2026-10-01. Every "this slide will be empty" check ran against the built render spec,
which needs the recorded narration, so a deck was first checked after the operator had
recorded it. Two compare slides authored as `"sides": [A, B]` blocked the 2026-09-29 FWF
daily for two days, and the same slip had already shipped in 22 published dailies, each
as a kicker over three bare rules, because an unrendered `headline` made slidecheck call
the card non-empty. This asserts: the `sides` shape now draws; a compare with no sides is
blank whatever else it carries; deckcheck catches a missing slide, dropped structured
content and a length over a hard wall; and it renders and writes nothing but its report.
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from explainer2 import deckcheck, slidecheck             # noqa: E402
from explainer2 import remotion_engine as E              # noqa: E402
from explainer2.project import Project                   # noqa: E402

A = {"title": "POLITE", "value": "Would you drink more wine?", "kind": "bad"}
B = {"title": "USEFUL", "value": "What did you drink last Friday?", "kind": "good"}


def make(root, name, slides, texts, **pj):
    p = root / name
    (p / "work").mkdir(parents=True)
    data = {"title": name, "slug": name, "aspect": "9:16", "aspects": ["9:16"],
            "width": 1080, "height": 1920, "fps": 30, "theme": "fwf",
            "voice_source": "operator", "content_type": "short"}
    data.update(pj)
    (p / "project.json").write_text(json.dumps(data))
    (p / "deck.json").write_text(json.dumps({"slides": slides}))
    (p / "script.json").write_text(json.dumps({"segments": [
        {"id": i, "slide": sid, "text": t} for i, (sid, t) in enumerate(texts)]}))
    return Project.load(p)


def main():
    line = "Cutting buys you time, and the younger customers tell you what to grow next."
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        # 1. The `sides` shape draws: the engine hands the component left and right.
        comp, fields = E._scene_for({"id": "s8", "type": "compare", "kicker": "ASK",
                                     "sides": [A, B]}, theme="fwf")
        assert comp == "CvgCompare" and fields["left"] == A and fields["right"] == B, fields
        # ...and an explicit left/right still wins over a stray `sides`.
        _, f2 = E._scene_for({"id": "s", "type": "compare", "left": B, "right": A,
                              "sides": [A, B]}, theme="fwf")
        assert f2["left"] == B and f2["right"] == A

        # 2. A compare with neither side is blank even when it carries a headline, which
        #    is the exact shape that shipped 22 times.
        blank, _ = slidecheck.check_spec({"scenes": [
            {"component": "CvgCompare", "fields": {"kicker": "K", "headline": "Ten quarters in",
                                                   "left": {}, "right": {}}}]})
        assert blank and "neither side" in blank[0], blank
        ok_blank, _ = slidecheck.check_spec({"scenes": [
            {"component": "CvgCompare", "fields": {"left": A, "right": B}}]})
        assert not ok_blank

        # 3. A clean deck passes, and nothing but the report is written.
        good = make(root, "good", [
            {"id": "s1", "type": "hook", "kicker": "K", "headline": "A real headline"},
            {"id": "s2", "type": "compare", "kicker": "ASK", "sides": [A, B]},
            {"id": "cta", "type": "cta", "headline": "and subscribe"}],
            [("s1", line), ("s2", line), ("cta", "Like and subscribe.")])
        out = deckcheck.run(good)
        assert out["ok"], out["problems"]
        assert sorted(x.name for x in good.work.iterdir()) == ["deckcheck.json"]
        assert "DECKCHECK OK" in deckcheck.report(out)
        assert out["projection"]["measured_from_episodes"] == 0

        # 4. A compare with no sides at all is a problem, named by slide and booth card.
        empty = make(root, "empty", [
            {"id": "s1", "type": "hook", "headline": "H"},
            {"id": "s2", "type": "compare", "kicker": "ASK", "headline": "Two months apart"}],
            [("s1", line), ("s2", line)])
        out = deckcheck.run(empty)
        assert not out["ok"] and any("s2 (booth card 2)" in x and "nothing on it" in x
                                     for x in out["problems"]), out["problems"]
        assert "DECKCHECK FAILED" in deckcheck.report(out)

        # 5. A segment that names a slide the deck does not have.
        missing = make(root, "missing", [{"id": "s1", "type": "hook", "headline": "H"}],
                       [("s1", line), ("s9", line)])
        out = deckcheck.run(missing)
        assert not out["ok"] and any("`s9`" in x for x in out["problems"]), out["problems"]

        # 6. Structured content a component drops is a problem; a dropped accent is not.
        drop = make(root, "drop", [
            {"id": "s1", "type": "statement", "headline": "H", "bullets": ["one", "two"],
             "accent2": ["H"]}], [("s1", line)])
        out = deckcheck.run(drop)
        assert not out["ok"] and any("`bullets`" in x for x in out["problems"]), out
        assert not any("accent2" in x for x in out["problems"]), out["problems"]

        # 7. A hard wall: with no history the projection uses the slow default pace, and
        #    a script that cannot fit fails BEFORE anyone records it.
        long_text = " ".join(["word"] * 420)                 # 420 words: ~185 s at 2.27 w/s
        wall = make(root, "wall", [{"id": "s1", "type": "hook", "headline": "H"}],
                    [("s1", long_text)], max_length=180)
        out = deckcheck.run(wall)
        assert not out["ok"] and any("over the 180 s limit" in x for x in out["problems"]), out
        assert out["projection"]["words_per_second"] == deckcheck.FALLBACK_WPS_WALL
        fits = make(root, "fits", [{"id": "s1", "type": "hook", "headline": "H"}],
                    [("s1", " ".join(["word"] * 300))], max_length=180)
        assert deckcheck.run(fits)["ok"]
        # No wall, no problem, however long: length is an outcome for an unbounded show.
        free = make(root, "free", [{"id": "s1", "type": "hook", "headline": "H"}],
                    [("s1", long_text)])
        assert deckcheck.run(free)["ok"]

        # 8. The pace comes from the show's own finished episodes when it has them, and
        #    so does what the render adds on top of the narration.
        show = root / "show"
        show.mkdir()
        for i, (words, secs, rendered) in enumerate(((300, 150.0, 158.4), (260, 130.0, 138.4))):
            ep = show / f"2026-09-{20 + i}_ep"
            (ep / "work").mkdir(parents=True)
            (ep / "work" / "segments.json").write_text(json.dumps(
                {"duration": secs, "segments": [{"text": " ".join(["w"] * words)}]}))
            (ep / "manifest.json").write_text(json.dumps({"duration_s": rendered}))
        new = make(show, "2026-09-30_ep", [{"id": "s1", "type": "hook", "headline": "H"}],
                   [("s1", " ".join(["w"] * 340))], max_length=180)
        out = deckcheck.run(new)
        pr = out["projection"]
        assert pr["measured_from_episodes"] == 2 and pr["words_per_second"] == 2.0, pr
        assert pr["render_adds_s"] == 8.4 and abs(pr["projected_s"] - 178.4) < 0.2, pr
        assert not out["ok"], "178 s against a 180 s wall has no clearance"

    print("OK — test_deckcheck")


if __name__ == "__main__":
    sys.exit(main())
