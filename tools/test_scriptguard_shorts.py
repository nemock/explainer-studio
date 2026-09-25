#!/usr/bin/env python3
"""Regression: scriptguard must check Shorts hook/outro takes against shorts/plan.json,
and unstick_stale_script.py must be able to --accept and --fix them.

Run:  python3 tools/test_scriptguard_shorts.py

2026-09-25, #69 wp-engine-automattic-drama-continues: after the operator's Finish, the
ten-lives hook in shorts/plan.json was rewritten. The guard only read seg_NNN stamps, so
`unstick_stale_script.py --accept` reported "guard now OK" and skipped the Shorts card,
and the `shorts` stage would have rendered the OLD hook audio under the NEW hook
captions. It was fixed by hand (work/shorts_restamp.py in that project). This asserts
the guard now blocks on that exact shape, that --accept (by card id and by stem) and
--fix resolve it, and that the long-form paths behave as before.
"""
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from explainer2.project import Project          # noqa: E402
from explainer2.media import scriptguard        # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "unstick", ROOT / "tools" / "unstick_stale_script.py")
unstick = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(unstick)
# fix() shells out to kill_render.py for the machine-global render-lock note; a test
# must never touch that.
unstick.subprocess.run = lambda *a, **k: None

OLD_HOOK = "An appeals court just revived a lawsuit over a countdown built into the robot."
NEW_HOOK = "Every da Vinci instrument ships with a countdown. Ten uses, then it quits."
OUTRO = "Ten uses, then it turns itself off."
HOOK_ID, OUTRO_ID = 2, 3            # two script segments (0, 1), then the Short cards
HOOK_STEM = "short_ten-lives_hook"

failures = []


def expect(cond, msg):
    if not cond:
        failures.append(msg)


def make_proj(tmp):
    d = Path(tmp) / "proj"
    v = d / "voiceover"
    v.mkdir(parents=True)
    (d / "work").mkdir()
    (d / "shorts" / "ten-lives" / "video").mkdir(parents=True)
    (d / "video").mkdir()
    (d / "project.json").write_text(json.dumps({"title": "t", "slug": "s",
                                                "voice_source": "operator"}))
    segs = [{"id": 0, "slide": "s1", "text": "First line."},
            {"id": 1, "slide": "s2", "text": "Second line."}]
    (d / "script.json").write_text(json.dumps({"segments": segs}))
    for s in segs:
        (v / f"seg_{s['id']:03d}.wav").write_bytes(b"\x00")
        scriptguard.stamp(v, f"seg_{s['id']:03d}", s["text"], seg_id=s["id"], slide=s["slide"])
    write_plan(d, OLD_HOOK)
    (v / f"{HOOK_STEM}.wav").write_bytes(b"\x00")
    scriptguard.stamp(v, HOOK_STEM, OLD_HOOK, seg_id=HOOK_ID, slide="SHORT 1 · HOOK")
    (v / "short_ten-lives_outro.wav").write_bytes(b"\x00")
    scriptguard.stamp(v, "short_ten-lives_outro", OUTRO, seg_id=OUTRO_ID, slide="SHORT 1 · OUTRO")
    return Project.load(d)


def write_plan(d, hook):
    (d / "shorts" / "plan.json").write_text(json.dumps([
        {"slug": "ten-lives", "title": "T", "segments": [0], "hook": hook, "outro": OUTRO}]))


def row(rep, cid):
    return next(r for r in rep["segments"] if r["id"] == cid)


with tempfile.TemporaryDirectory() as tmp:
    proj = make_proj(tmp)
    v = proj.voiceover_dir

    # 1. Everything recorded against the current text: OK, and the Short rows are checked.
    rep = scriptguard.check(proj)
    expect(rep["ok"], f"clean project should pass: {rep['reason']}")
    expect(row(rep, HOOK_ID).get("kind") == "short" and row(rep, HOOK_ID)["status"] == "match",
           f"hook card should be checked and match: {row(rep, HOOK_ID)}")
    expect(row(rep, HOOK_ID)["stem"] == HOOK_STEM, "hook card must map to the booth's stem")

    # 2. The incident: the hook is rewritten in plan.json after recording.
    write_plan(proj.dir, NEW_HOOK)
    rep = scriptguard.check(proj)
    expect(not rep["ok"], "a rewritten Short hook must block")
    expect(rep["stale"] == [HOOK_ID], f"only the hook card is stale, got {rep['stale']}")
    try:
        scriptguard.enforce(proj, log=lambda m: None)
        failures.append("enforce() must raise on a stale Short card")
    except scriptguard.StaleScriptError:
        pass
    blocked = scriptguard.blocked_path(proj)
    expect(blocked.exists(), "BLOCKED.md must be written")
    body = blocked.read_text() if blocked.exists() else ""
    expect("shorts/plan.json" in body and OLD_HOOK in body and NEW_HOOK in body,
           "BLOCKED.md must name plan.json and show both hook texts")

    # 3. --accept by card id re-stamps the hook; guard passes.
    unstick.accept(proj, rep, [str(HOOK_ID)])
    rep = scriptguard.check(proj)
    expect(rep["ok"], f"--accept {HOOK_ID} should clear it: {rep['reason']}")
    expect(scriptguard.read_meta(v, HOOK_STEM)["source"] == "operator-accepted",
           "accepted hook must be re-stamped operator-accepted")

    # 4. --accept by stem works the same way.
    write_plan(proj.dir, OLD_HOOK)
    rep = scriptguard.check(proj)
    expect(rep["stale"] == [HOOK_ID], "hook is stale again after the plan reverts")
    unstick.accept(proj, rep, [f"{HOOK_STEM}.wav"])
    expect(scriptguard.check(proj)["ok"], "--accept <stem>.wav should clear it")

    # 5. --fix: the stale take and its old-text alternate go aside; an alternate stamped
    #    with the NEW text stays; only this cut's mp4 goes, the long-form is kept.
    (v / f"{HOOK_STEM}.take1.wav").write_bytes(b"\x00")
    scriptguard.stamp(v, f"{HOOK_STEM}.take1", OLD_HOOK)
    (v / f"{HOOK_STEM}.take2.wav").write_bytes(b"\x00")
    scriptguard.stamp(v, f"{HOOK_STEM}.take2", NEW_HOOK)
    (proj.work / "record_done.json").write_text("{}")
    short_mp4 = proj.dir / "shorts" / "ten-lives" / "video" / "explainer_9x16.mp4"
    long_mp4 = proj.dir / "video" / "explainer_16x9.mp4"
    short_mp4.write_bytes(b"\x00")
    long_mp4.write_bytes(b"\x00")
    write_plan(proj.dir, NEW_HOOK)
    rep = scriptguard.check(proj)
    moved = unstick.fix(proj, rep)
    expect(moved == [HOOK_ID], f"fix should move the hook card, moved {moved}")
    expect(not (v / f"{HOOK_STEM}.wav").exists() and (v / f"{HOOK_STEM}.oldtext.bak").exists(),
           "stale hook wav must be moved to .oldtext.bak")
    expect(not (v / f"{HOOK_STEM}.take1.wav").exists()
           and (v / f"{HOOK_STEM}.take1.oldtext.bak").exists()
           and (v / f"{HOOK_STEM}.take1.oldtext.meta.json").exists(),
           "old-text alternate take and its stamp must move aside")
    expect((v / f"{HOOK_STEM}.take2.wav").exists(),
           "an alternate take stamped with the current text must stay")
    expect(not short_mp4.exists(), "the stale cut's mp4 must be deleted")
    expect(long_mp4.exists(), "the long-form mp4 must survive a Shorts-only fix")
    expect(not (proj.work / "record_done.json").exists(), "record_done.json must be superseded")
    rep = scriptguard.check(proj)
    expect(rep["ok"] and HOOK_ID in rep["not_recorded"],
           f"after --fix the hook is simply unrecorded: {rep['reason']}")

    # 6. An unstamped Short take is reported but does not block, even when script.json
    #    is newer than the audio (the mtime layer is about script.json).
    (v / f"{HOOK_STEM}.wav").write_bytes(b"\x00")
    scriptguard.meta_path(v, HOOK_STEM).unlink(missing_ok=True)
    later = time.time() + 60
    os.utime(proj.script_json, (later, later))
    rep = scriptguard.check(proj)
    expect(rep["ok"], f"an unstamped Short take alone must not block: {rep['reason']}")
    expect(row(rep, HOOK_ID)["status"] == "unstamped", "unstamped hook must be reported")

    # 7. Long-form regression: a stale segment still blocks.
    script = json.loads(proj.script_json.read_text())
    script["segments"][1]["text"] = "Second line, rewritten."
    proj.script_json.write_text(json.dumps(script))
    rep = scriptguard.check(proj)
    expect(not rep["ok"] and rep["stale"] == [1], f"stale segment must still block: {rep['stale']}")

if failures:
    print("FAIL")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("OK — Shorts hook/outro takes are guarded; --accept and --fix handle them")
