#!/usr/bin/env python3
"""Regression: `explainer2 stills` picks its path by ENGINE, not by whether deck/index.html
happens to be on disk.

Run:  ~/myenv/bin/python3.12 tools/test_stills_engine.py

Until 2026-10-03 stills.run() took the legacy Playwright path whenever deck/index.html
existed. deck-playbook §5 has every author run `explainer2 deck`, which writes that file on
Remotion projects too, so phase 1 saved a show's stills from the legacy HTML deck instead of
from the video it had just rendered, and nothing failed: the 2026-09-21 daily founder tip's
stills/ show its compare card as two empty "vs" boxes on flat purple, while its video shows
the cut-paper city. Asserted here, with ffmpeg, Chromium and the render lock stubbed so
nothing renders:
  - a Remotion project that HAS deck/index.html takes the video path by default, and never
    launches Chromium or takes the render lock;
  - engine="deck" takes the Playwright path under the lock, and refuses a missing
    deck/index.html before taking the lock;
  - through the CLI, `stills <dir>` with no flag is the video path and `--engine deck` the
    deck path, and the default equals `media`'s: phase1_render.py runs both verbs without
    --engine and relies on them agreeing.
"""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from explainer2 import cli, stills          # noqa: E402
from explainer2.project import Project      # noqa: E402

CALLS = []


def fake_run(cmd, **_kw):
    """ffmpeg stand-in: record the call and write the frame it was asked for."""
    CALLS.append(("ffmpeg", cmd))
    Path(cmd[-1]).write_bytes(b"png")
    return subprocess.CompletedProcess(cmd, 0, "", "")


class FakePage:
    def goto(self, url): CALLS.append(("goto", url))
    def wait_for_function(self, _js): pass
    def evaluate(self, _js, _arg=None): pass
    def screenshot(self, path, clip): Path(path).write_bytes(b"png")
    def close(self): pass


class FakeBrowser:
    def new_page(self, **_kw): return FakePage()
    def close(self): pass


@contextlib.contextmanager
def fake_playwright():
    CALLS.append(("chromium", None))
    yield types.SimpleNamespace(chromium=types.SimpleNamespace(launch=lambda **_kw: FakeBrowser()))


stills.subprocess = types.SimpleNamespace(run=fake_run)
stills.sync_playwright = fake_playwright
stills.renderlock = types.SimpleNamespace(
    acquire=lambda proj: CALLS.append(("lock", None)) or "LOCK",
    release=lambda lock: CALLS.append(("unlock", lock)))


def kinds():
    return [k for k, _ in CALLS]


def make_project(root):
    d = root / "proj"
    (d / "work").mkdir(parents=True)
    (d / "video").mkdir()
    (d / "deck").mkdir()
    (d / "project.json").write_text(json.dumps({"title": "t", "aspect": "16:9",
                                                "aspects": ["16:9"]}))
    (d / "work" / "timeline.json").write_text(json.dumps({"duration": 10.0, "slides": [
        {"id": "s01", "start": 0.0, "end": 4.0}, {"id": "s02", "start": 4.0, "end": 10.0}]}))
    # Not a real mp4: ffmpeg is stubbed, only the path matters.
    (d / "video" / "explainer_16x9.mp4").write_bytes(b"\x00")
    # What `explainer2 deck` leaves behind on a Remotion project (deck-playbook §5).
    (d / "deck" / "index.html").write_text("<html></html>")
    return d


with tempfile.TemporaryDirectory() as td:
    d = make_project(Path(td).resolve())       # Project.load resolves /var -> /private/var
    video = str(d / "video" / "explainer_16x9.mp4")

    # 1) the bug's exact shape: a Remotion project with deck/index.html on disk
    CALLS.clear()
    r = stills.run(Project.load(d))
    assert r.get("engine") == "remotion", f"took the legacy deck path: {r}"
    assert kinds() == ["ffmpeg", "ffmpeg"], CALLS          # no Chromium, no render lock
    assert all(c[c.index("-i") + 1] == video for _, c in CALLS), CALLS
    assert sorted(p.name for p in (d / "stills").glob("*.png")) == [
        "slide_01_s01.png", "slide_02_s02.png"]

    # 2) engine="deck": the Playwright path, under the render lock
    CALLS.clear()
    r = stills.run(Project.load(d), engine="deck")
    assert r["engine"] == "deck" and r["count"] == 2, r
    assert kinds()[0] == "lock" and kinds()[-1] == "unlock", CALLS
    assert "chromium" in kinds() and "ffmpeg" not in kinds(), CALLS

    # 3) engine="deck" without deck/index.html: refused before the lock is taken
    (d / "deck" / "index.html").unlink()
    CALLS.clear()
    try:
        stills.run(Project.load(d), engine="deck")
        raise AssertionError("the deck path ran without deck/index.html")
    except FileNotFoundError as e:
        assert "deck stage" in str(e), e
    assert not CALLS, CALLS
    (d / "deck" / "index.html").write_text("<html></html>")

    # 4) through the CLI, the way phase1_render.py calls it (no --engine), and with the flag
    for argv, want in ((["stills", str(d), "--aspect", "16:9"], "remotion"),
                       (["stills", str(d), "--engine", "deck"], "deck")):
        CALLS.clear()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(argv)
        got = json.loads(buf.getvalue())["engine"]
        assert got == want, (argv, got)

# 5) phase 1 runs `media <dir>` and then `stills <dir> --aspect A`, neither with --engine,
#    so the two verbs' defaults must name the same engine
seen = {}
real = cli.cmd_media, cli.cmd_stills
cli.cmd_media = lambda a: seen.setdefault("media", a.engine)
cli.cmd_stills = lambda a: seen.setdefault("stills", a.engine)
try:
    cli.main(["media", "unused"])
    cli.main(["stills", "unused"])
finally:
    cli.cmd_media, cli.cmd_stills = real
assert seen == {"media": "remotion", "stills": "remotion"}, seen

print("test_stills_engine: 5 checks passed")
