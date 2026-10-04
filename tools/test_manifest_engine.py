#!/usr/bin/env python3
"""Regression: manifest.json records the engine that rendered the video, and names
deck/index.html only when the deck engine rendered from it.

Run:  ~/myenv/bin/python3.12 tools/test_manifest_engine.py

Sibling of test_stills_engine.py, same bug. manifest.py wrote "deck": "deck/index.html"
whenever that file existed, and `explainer2 deck` writes it on Remotion projects too, so a
Remotion video's manifest named an HTML deck its render never read: Product Leadership
module 8's still does (2026-10-04). Asserted here:
  - by default (remotion), `deck` is null even with deck/index.html on disk, and
    generator.engine says remotion;
  - with engine="deck", `deck` names the file, and stays null if the file is missing;
  - through the CLI, `media --only manifest` and the `manifest` stage both pass their
    --engine through, and both default to remotion like every other verb.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["EXPLAINER_QUEUE_DIR"] = tempfile.mkdtemp(prefix="manifest-engine-test-")  # never the real spool
os.environ["EXPLAINER_QUEUE_QUIET"] = "1"
sys.path.insert(0, str(ROOT / "src"))

from explainer2 import cli, manifest        # noqa: E402
from explainer2.project import Project      # noqa: E402


def read(d):
    m = json.loads((d / "manifest.json").read_text())
    return m["deck"], m["generator"].get("engine")


with tempfile.TemporaryDirectory() as td:
    d = Path(td).resolve() / "proj"
    (d / "video").mkdir(parents=True)
    (d / "deck").mkdir()
    (d / "project.json").write_text(json.dumps({"title": "t", "slug": "t", "aspect": "16:9",
                                                "aspects": ["16:9"]}))
    # Not a real mp4: only its existence matters to the manifest (ffprobe returns None).
    (d / "video" / "explainer_16x9.mp4").write_bytes(b"\x00")
    # What `explainer2 deck` leaves behind on a Remotion project.
    (d / "deck" / "index.html").write_text("<html></html>")

    # 1) the bug's shape: Remotion, with deck/index.html on disk
    manifest.run(Project.load(d))
    assert read(d) == (None, "remotion"), read(d)

    # 2) the deck engine renders from that file, so its manifest names it
    manifest.run(Project.load(d), engine="deck")
    assert read(d) == ("deck/index.html", "deck"), read(d)

    # 3) ...but never a file that is not there
    (d / "deck" / "index.html").unlink()
    manifest.run(Project.load(d), engine="deck")
    assert read(d) == (None, "deck"), read(d)
    (d / "deck" / "index.html").write_text("<html></html>")

    # 4) through the CLI: `media --only manifest` and the `manifest` stage, with and
    #    without --engine
    for argv, want in ((["media", str(d), "--only", "manifest"], (None, "remotion")),
                       (["media", str(d), "--only", "manifest", "--engine", "deck"],
                        ("deck/index.html", "deck")),
                       (["manifest", str(d)], (None, "remotion")),
                       (["manifest", str(d), "--engine", "deck"], ("deck/index.html", "deck"))):
        with contextlib.redirect_stdout(io.StringIO()):
            rc = cli.main(argv)
        assert rc == 0 and read(d) == want, (argv, rc, read(d))

print("test_manifest_engine: 4 checks passed")
