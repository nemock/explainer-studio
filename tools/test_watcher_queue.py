#!/usr/bin/env python3
"""The recording watcher after 2026-10-01: queue submission, a stale render sentinel,
per-show isolation, identical-failure verdicts, and operator text alerts.

Run:  python3 tools/test_watcher_queue.py

Each block is a failure that happened or was one step from happening:
  * a re-record after a blocked publish would have published the OLD render, because
    render_complete.json was trusted by existence alone
  * one hung `launch_booth --status` raised out of the whole cycle (2026-09-30)
  * The Teardown re-ran one align error six times over two hours (2026-10-01)
  * a daily episode sat blocked two days behind a single desktop notification
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
_SPOOL = tempfile.mkdtemp(prefix="watcher-queue-test-")
os.environ["EXPLAINER_QUEUE_DIR"] = _SPOOL
os.environ["EXPLAINER_QUEUE_QUIET"] = "1"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rw = _load("recording_watcher")
p1 = _load("phase1_render")
jq = rw.jobqueue

LOG = []
rw.log = lambda cfg, msg: LOG.append(msg)


def touch(path, age=0, text="{}"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    t = time.time() - age
    os.utime(path, (t, t))


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        proj = root / "2026-10-01_episode"
        work = proj / "work"

        # 1. render_done: a sentinel older than the recording is not a render of it.
        assert not rw.render_done(proj)
        touch(work / "record_done.json", age=600)
        touch(work / "render_complete.json", age=300)
        assert rw.render_done(proj)
        touch(work / "record_done.json", age=10)            # the operator re-recorded
        assert not rw.render_done(proj), "an old render must not stand for a new recording"
        (work / "record_done.json").unlink()
        assert rw.render_done(proj), "with no Finish marker there is nothing to compare"

        # 2. A lock naming a queued job is alive exactly while that job is.
        subprocess.run([sys.executable, str(ROOT / "tools" / "render_queue.py"), "--enable", ""],
                       check=True, capture_output=True)
        cfg = {"use_render_queue": True, "python": sys.executable,
               "launch_booth": str(ROOT / "tools" / "launch_booth.py"),
               "explainer_bin": "/usr/bin/true", "claude_cwd": td,
               "logs_dir": str(root / "logs")}
        assert rw.use_queue(cfg) and not rw.use_queue({})
        show = {"id": "test-show"}
        rw.launch_render(cfg, show, proj)
        lk = rw.read_lock(proj)
        job = jq.get(lk["job"])
        assert job and job["state"] == "queued" and job["priority"] == jq.PRI_SHOW, job
        assert job["argv"][1].endswith("phase1_render.py") and "--profile" not in job["argv"]
        assert rw.worker_alive(lk) and "render job" in rw.worker_name(lk)
        assert rw.read_attempts(proj, "render")["count"] == 1
        rw.launch_render(cfg, show, proj)                    # same project again
        assert rw.read_lock(proj)["job"] == job["id"], "must re-attach, not queue a second render"
        assert rw.read_attempts(proj, "render")["count"] == 1
        jq.cancel(job["id"])
        assert not rw.worker_alive(rw.read_lock(proj))
        studio = dict(show, id="studio", mode="studio")
        rw.launch_render(cfg, studio, root / "module-01")
        sj = jq.get(rw.read_lock(root / "module-01")["job"])
        assert sj["priority"] == jq.PRI_STUDIO and sj["argv"][-2:] == ["--profile", "studio"]
        assert [j["id"] for j in jq.queued()] == [sj["id"]]
        jq.cancel(sj["id"])
        # A plain pid lock still works (the direct-launch fallback, and phase 2).
        assert rw.worker_alive({"pid": os.getpid()}) and not rw.worker_alive({"pid": 999999})
        assert not rw.worker_alive(None)

        # 3. A hung booth status is an ERROR state, not an exception.
        rw.subprocess_run_real = rw.subprocess.run

        def hang(*a, **k):
            raise subprocess.TimeoutExpired(a[0], 120)
        rw.subprocess.run = hang
        try:
            state, full = rw.booth(cfg, ["--status"], proj)
        finally:
            rw.subprocess.run = rw.subprocess_run_real
        assert state == "ERROR" and "did not answer" in full

        # 4. One show raising does not cost the next show its cycle.
        seen = []

        def fake_show(cfg_, show_, dry, spawned):
            seen.append(show_["id"])
            if show_["id"] == "bad":
                raise RuntimeError("boom")
            return spawned
        real_show = rw.run_show
        rw.run_show = fake_show
        LOG.clear()
        try:
            rw.run({"shows": [{"id": "bad"}, {"id": "good"}, {"id": "off", "enabled": False}]},
                   dry=True)
        finally:
            rw.run_show = real_show
        assert seen == ["bad", "good"], seen
        assert any(m.startswith("WATCHER-ERROR bad") for m in LOG), LOG

        # 5. phase1 names the failing stage, and an identical failure builds a streak.
        t0 = time.time() - 5
        now = time.strftime("%H:%M:%S")
        (work / "run.log").write_text(
            "00:00:01 FAIL  render: RuntimeError: an older launch\n"
            f"{now} START narrate\n{now} OK    narrate (1.0s) {{}}\n{now} START align\n"
            f"{now} FAIL  align: RuntimeError: targets length is too long for CTC (155 vs 159)\n")
        stage, detail = p1.failure_detail(proj, t0)
        assert stage == "align" and "CTC (N vs N)" in detail, (stage, detail)
        assert p1.record_failure(proj, "media", 1, since=t0) == 1
        assert p1.record_failure(proj, "media", 1, since=t0) == 2
        d = json.loads((work / "render_failure.json").read_text())
        assert d["stage"] == "align" and d["fp"].startswith("media:1:align:"), d
        # A failure with no FAIL line of its own (a later verb) does not inherit one.
        assert p1.failure_detail(proj, time.time() + 60) == ("", "")

        # 6. Two identical failures in an audio stage is a verdict; elsewhere it takes three.
        blocked, fp, why = rw.render_blocked(proj)
        assert blocked and "at align" in why and "CTC" in why, why
        (work / "render_failure.json").write_text(json.dumps(
            {"fp": "stills:1", "verb": "stills", "rc": 1, "streak": 2, "ts": time.time()}))
        assert not rw.render_blocked(proj)[0]
        (work / "render_failure.json").write_text(json.dumps(
            {"fp": "stills:1", "verb": "stills", "rc": 1, "streak": 3, "ts": time.time()}))
        assert rw.render_blocked(proj)[0]

        # 7. Operator alerts: once per fingerprint, retried on failure, capped at three.
        sent = root / "sent.txt"
        ok_cmd = ["/bin/sh", "-c", f'printf "%s\\n" "$1" >> "{sent}"', "alert"]
        acfg = dict(cfg, operator_alert_cmd=ok_cmd)
        LOG.clear()
        assert rw.alert_operator(acfg, proj, "operator_alert_x.json", "fp1", "re-record card 4")
        assert not rw.alert_operator(acfg, proj, "operator_alert_x.json", "fp1", "re-record card 4")
        assert rw.alert_operator(acfg, proj, "operator_alert_x.json", "fp2", "re-record card 5")
        assert sent.read_text().splitlines() == ["re-record card 4", "re-record card 5"]
        bad = dict(cfg, operator_alert_cmd=["/usr/bin/false"])
        os.environ["PATH_BACKUP"] = os.environ.get("PATH", "")
        real_run = rw.subprocess.run
        calls = []

        def counting(cmd, *a, **k):
            calls.append(cmd[0])
            if cmd[0] == "/usr/bin/osascript":
                return subprocess.CompletedProcess(cmd, 0, "", "")
            return real_run(cmd, *a, **k)
        rw.subprocess.run = counting
        try:
            for _ in range(5):
                rw.alert_operator(bad, proj, "operator_alert_y.json", "fp1", "x")
        finally:
            rw.subprocess.run = real_run
        assert calls.count("/usr/bin/false") == 3, calls
        assert calls.count("/usr/bin/osascript") == 3, "a failed text falls back to the desktop"

        # 8. Only a recording-stage block texts the operator; so does a stale script and
        #    a publish block that says it needs him.
        (work / "render_failure.json").write_text(json.dumps(
            {"fp": "a", "verb": "media", "rc": 1, "stage": "align", "detail": "CTC",
             "streak": 2, "ts": time.time()}))
        rw.alert_if_recording_fault(acfg, show, proj, "a")
        (work / "render_failure.json").write_text(json.dumps(
            {"fp": "b", "verb": "media", "rc": 1, "stage": "render", "detail": "chrome",
             "streak": 3, "ts": time.time()}))
        rw.alert_if_recording_fault(acfg, show, proj, "b")
        lines = sent.read_text().splitlines()
        assert len(lines) == 3 and "failing at align" in lines[2], lines
        rw.alert_stale_script(acfg, show, proj, "segment 3 text changed")
        (work / "publish_block.json").write_text(json.dumps(
            {"watch": "work/render_complete.json", "was": "{}", "reason": "over 180 s"}))
        rw.alert_if_publish_needs_operator(acfg, show, proj, "p1")
        assert len(sent.read_text().splitlines()) == 4, "a block that does not name him stays quiet"
        (work / "publish_block.json").write_text(json.dumps(
            {"watch": "work/render_complete.json", "was": "{}", "reason": "over 180 s",
             "needs_operator": True, "operator_action": "cut and re-record card 6"}))
        rw.alert_if_publish_needs_operator(acfg, show, proj, "p1")
        lines = sent.read_text().splitlines()
        assert len(lines) == 5 and "cut and re-record card 6" in lines[4], lines

    print("OK — test_watcher_queue")


if __name__ == "__main__":
    sys.exit(main())
