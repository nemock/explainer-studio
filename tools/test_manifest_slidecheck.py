#!/usr/bin/env python3
"""Regression: manifest.run() must gate ready_for_post on slidecheck's blocking findings.

Run:  python3 tools/test_manifest_slidecheck.py

Four blank-card incidents (stat/statgrid 2026-08-12, reframe 2026-08-20, ring 2026-08-24)
all shipped or nearly shipped with manifest.json AND handoff.json saying
ready_for_post: true, because the manifest builder only ever checked that the mp4 files
existed and the video was long enough. slidecheck ran only inside `explainer2 validate`,
which nothing forces before publish. This asserts the manifest itself now refuses
readiness over a scene that would render blank — and still says ready when every scene
carries content, so the gate cannot be quietly widened in either direction.

Companion to test_cvg_scene_map.py (the map, at author time) and slidecheck.py
(the built spec, at validate time); this covers the publish flag both of those feed.
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from explainer2 import manifest  # noqa: E402


class FakeProj:
    """The attribute surface manifest.run() actually touches, nothing more."""
    def __init__(self, d):
        self.dir = d
        self.work = d / "work"
        self.aspects = ["9:16"]
        self.min_length = None
        self.data = {"title": "t", "slug": "s"}
        self.voice = "af_heart"
        self.series = None
        self.content_type = "deepdive"

    def write_json(self, path, obj):
        path.write_text(json.dumps(obj, indent=2))


def make_proj(tmp, scenes):
    d = Path(tmp) / "proj"
    (d / "video").mkdir(parents=True)
    (d / "work" / "remotion").mkdir(parents=True)
    # Not a real mp4: ffprobe fails -> duration None, which is fine because
    # min_length is None; only the file-exists check matters here.
    (d / "video" / "explainer_9x16.mp4").write_bytes(b"\x00")
    (d / "work" / "remotion" / "props.json").write_text(json.dumps({"scenes": scenes}))
    return FakeProj(d)


failures = []

# The MMT 2026-08-24 s9 shape — a scene the spec would render blank.
with tempfile.TemporaryDirectory() as tmp:
    proj = make_proj(tmp, [{"component": "CvgScene",
                            "fields": {"kicker": "the number", "headline": ""}}])
    r = manifest.run(proj)
    m = json.loads((proj.dir / "manifest.json").read_text())
    if r["ready_for_post"] is not False:
        failures.append(f"blank scene: ready_for_post must be False, got {r['ready_for_post']!r}")
    if not m["status"].get("blank_slides"):
        failures.append("blank scene: status.blank_slides empty — the reason is not recorded")
    if m["status"]["ready_for_post"] is not False:
        failures.append("blank scene: manifest.json status.ready_for_post must be False")

# Every scene carries content — readiness must survive the new gate.
with tempfile.TemporaryDirectory() as tmp:
    proj = make_proj(tmp, [{"component": "CvgScene",
                            "fields": {"kicker": "k", "headline": "12% of eligible patients"}}])
    r = manifest.run(proj)
    m = json.loads((proj.dir / "manifest.json").read_text())
    if r["ready_for_post"] is not True:
        failures.append(f"good scene: ready_for_post must be True, got {r['ready_for_post']!r}")
    if m["status"].get("blank_slides"):
        failures.append(f"good scene: spurious blank_slides {m['status']['blank_slides']!r}")

if failures:
    print(f"FAIL — {len(failures)} problem(s):")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS — manifest refuses ready_for_post over a blank scene, grants it over content")
