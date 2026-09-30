#!/usr/bin/env python3
"""Regression: a studio render killed partway is relaunched, and every skip is logged.

Run:  python3 tools/test_watcher_studio_relaunch.py

2026-09-30, #70 claude-nine-loops: the watcher launched phase 1 at 14:06. At 14:20 the
operator's session stopped it with kill_render.py to fix deck.json, expecting the next
cycle to relaunch. The killed encode had left a partial video/explainer_16x9.mp4, and
studio_rendered() counted any mp4 newer than record_done.json as a finished render, so
run_studio() skipped the project with a bare `continue` every cycle for two hours and
logged nothing. module-07 took the render slot at 15:42; #70 was relaunched by hand at
16:42. This asserts the killed-render shape relaunches, that a finished render is still
recognised, and that each skip decision writes one log line (throttled on repeats).
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "recording_watcher", ROOT / "tools" / "recording_watcher.py")
rw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rw)

LOG = []
LAUNCHED = []
RUNNING = [0]
rw.log = lambda cfg, msg: LOG.append(msg)
rw.script_guard_ok = lambda cfg, proj: (True, "")
rw.live_renders = lambda cfg: RUNNING[0]
rw.launch_render = lambda cfg, show, proj: LAUNCHED.append(proj.name)

CFG = {"max_concurrent_renders": 1}


def dead_pid():
    p = subprocess.Popen(["/usr/bin/true"])
    p.wait()
    return p.pid


def make_project(root, name):
    """A recorded studio project, as #70 stood at 14:20: DONE, deck authored, operator
    voice, one phase-1 attempt whose worker is gone, a partial mp4, no render_complete."""
    p = root / name
    (p / "work").mkdir(parents=True)
    (p / "video").mkdir()
    (p / "project.json").write_text(json.dumps({"voice_source": "operator"}))
    (p / "script.json").write_text("{}")
    (p / "deck.json").write_text("{}")
    done = p / "work" / "record_done.json"
    done.write_text("{}")
    past = time.time() - 900
    os.utime(done, (past, past))                 # recorded 15 minutes ago
    (p / "video" / "explainer_16x9.mp4").write_bytes(b"\x00" * 64)   # partial encode
    (p / "work" / "publish_lock.json").write_text(
        json.dumps({"pid": dead_pid(), "ts": past + 60}))
    (p / "work" / "render_attempts.json").write_text(
        json.dumps({"count": 1, "ts": past + 60}))
    return p


def cycle(root):
    LOG.clear()
    LAUNCHED.clear()
    show = {"id": "explainer-studio", "mode": "studio", "lookback_days": 3,
            "project_globs": [str(root / "*")]}
    return rw.run_studio(CFG, show, dry=False, spawned=False)


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        proj = make_project(root, "2026-09-30_70_killed")

        # 1. The #70 shape relaunches, and says why.
        assert not rw.studio_rendered(proj), "partial mp4 must not count as rendered"
        assert cycle(root) is True
        assert LAUNCHED == [proj.name], LAUNCHED
        assert any(m.startswith("STUDIO-RELAUNCH") for m in LOG), LOG

        # 2. The render cap still holds, and is logged.
        RUNNING[0] = 1
        assert cycle(root) is False and LAUNCHED == []
        assert any(m.startswith("RENDER-CAP") for m in LOG), LOG
        RUNNING[0] = 0

        # 3. So does the crash-loop cap.
        (proj / "work" / "render_attempts.json").write_text(
            json.dumps({"count": rw.CRASHLOOP_AFTER, "ts": time.time()}))
        assert cycle(root) is False and LAUNCHED == []
        assert any(m.startswith("RENDER-CRASHLOOP") for m in LOG), LOG
        (proj / "work" / "render_attempts.json").write_text(
            json.dumps({"count": 1, "ts": time.time() - 900}))

        # 4. A live worker backs off with one line, not one per cycle.
        (proj / "work" / "publish_lock.json").write_text(
            json.dumps({"pid": os.getpid(), "ts": time.time()}))
        cycle(root)
        assert LAUNCHED == [] and len(LOG) == 1 and "still active" in LOG[0], LOG
        cycle(root)
        assert LOG == [], f"repeat back-off inside the hour must stay quiet: {LOG}"
        (proj / "work" / "publish_lock.json").write_text(
            json.dumps({"pid": dead_pid(), "ts": time.time()}))

        # 5. results.json from `media --only narrate,align` is not a render...
        (proj / "work" / "results.json").write_text(
            json.dumps({"narrate": {}, "align": {}}))
        assert not rw.studio_rendered(proj)
        # ...but one that got through `render` is, and is logged once.
        (proj / "work" / "results.json").write_text(
            json.dumps({"narrate": {}, "align": {}, "render": {}}))
        assert rw.studio_rendered(proj).startswith("work/results.json")
        cycle(root)
        assert LAUNCHED == [] and len(LOG) == 1 \
            and LOG[0].startswith("STUDIO-RENDERED"), LOG
        cycle(root)
        assert LOG == [], f"a rendered project is reported once, not every cycle: {LOG}"

        # 6. A finished render from before a re-record does not count.
        old = time.time() - 3600
        os.utime(proj / "work" / "results.json", (old, old))
        cycle(root)
        assert LAUNCHED == [proj.name], LOG

    print("OK — test_watcher_studio_relaunch")


if __name__ == "__main__":
    sys.exit(main())
