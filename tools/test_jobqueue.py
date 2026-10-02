#!/usr/bin/env python3
"""The render queue: submit, order, run, wait, cancel, recover, time out, route.

Run:  python3 tools/test_jobqueue.py

2026-10-01. Six sessions in 29 hours ran a render in their own foreground, because only
`explainer2 render` could be handed off in one command and everything else needed a
hand-written launcher. jobqueue.py makes "submit" a real operation and tools/render_queue.py
runs the spool under launchd. This exercises the whole path against a temporary spool with
harmless commands (no render, no network, no model).
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_TMP = tempfile.mkdtemp(prefix="jobqueue-test-")
os.environ["EXPLAINER_QUEUE_DIR"] = _TMP          # never the real spool
os.environ["EXPLAINER_QUEUE_QUIET"] = "1"         # no desktop notifications from a test
sys.path.insert(0, str(ROOT / "src"))
from explainer2 import jobqueue as jq              # noqa: E402
from explainer2 import cli                         # noqa: E402

LOG = []


def log(m):
    LOG.append(m)


def sh(script):
    return ["/bin/sh", "-c", script]


def drain():
    return jq.run_forever(log=log)


def main():
    assert jq.spool() == Path(_TMP)
    assert not jq.enabled(), "a fresh spool is off until the installer says otherwise"
    subprocess.run([sys.executable, str(ROOT / "tools" / "render_queue.py"),
                    "--enable", ""], check=True, capture_output=True)
    assert jq.enabled()

    # 1. Routing only happens inside a session, and never inside a job.
    env = os.environ
    saved = {k: env.get(k) for k in ("CLAUDECODE", "EXPLAINER_QUEUE_RUNNER")}
    env["CLAUDECODE"] = "1"
    env.pop("EXPLAINER_QUEUE_RUNNER", None)
    assert jq.should_route()
    env["EXPLAINER_QUEUE_RUNNER"] = "1"
    assert not jq.should_route(), "a job the runner started must run inline"
    env.pop("EXPLAINER_QUEUE_RUNNER")
    env.pop("CLAUDECODE")
    assert not jq.should_route(), "launchd and a terminal run inline"

    # 2. Submit is idempotent while the job is live, and order is priority then age.
    a, made = jq.submit("media", sh("echo a"), project=_TMP, label="a")
    assert made and a["state"] == "queued" and a["priority"] == jq.PRI_MEDIA
    a2, made2 = jq.submit("media", sh("echo a"), project=_TMP, label="a")
    assert not made2 and a2["id"] == a["id"], "same job re-submitted must re-attach"
    time.sleep(1.1)                                 # ids and submitted_at are per-second
    b, _ = jq.submit("phase1", sh("echo b"), label="b")
    c, _ = jq.submit("shorts", sh("echo c"), label="c")
    assert [j["label"] for j in jq.queued()] == ["b", "a", "c"], \
        [j["label"] for j in jq.queued()]

    # 3. A wait that times out says so with 75 and does not disturb the job.
    out = []
    assert jq.wait(a["id"], timeout=0, out=out.append) == jq.RC_STILL_RUNNING
    assert "Re-issue" in out[-1] and jq.get(a["id"])["state"] == "queued"

    # 4. The runner drains in order, records exit codes, and writes each job's log.
    drain()
    for j, word in ((a, "a"), (b, "b"), (c, "c")):
        d = jq.get(j["id"])
        assert d["state"] == "done" and d["rc"] == 0, d
        assert word in Path(d["log"]).read_text()
    started = [m for m in LOG if m.startswith("started")]
    assert [m.split(": ")[1].split("]")[0] for m in started] == ["b", "a", "c"], started
    out = []
    assert jq.wait(a["id"], timeout=0, out=out.append) == 0
    # ...and a finished job can be submitted again as a NEW job.
    a3, made3 = jq.submit("media", sh("echo a"), project=_TMP, label="a")
    assert made3 and a3["id"] != a["id"]
    drain()

    # 5. A failing job is failed with its exit code; wait returns it.
    f, _ = jq.submit("cmd", sh("echo boom; exit 3"), label="f")
    drain()
    d = jq.get(f["id"])
    assert d["state"] == "failed" and d["rc"] == 3, d
    assert jq.wait(f["id"], timeout=0, out=lambda *_: None) == 3

    # 6. The child sees the runner marker and none of the session's CLAUDE* variables.
    os.environ["CLAUDECODE"] = "1"
    os.environ["CLAUDE_CODE_SESSION_ID"] = "test-session"
    e, _ = jq.submit("cmd", sh("env"), label="env")
    drain()
    os.environ.pop("CLAUDECODE")
    os.environ.pop("CLAUDE_CODE_SESSION_ID")
    text = Path(jq.get(e["id"])["log"]).read_text()
    assert "EXPLAINER_QUEUE_RUNNER=1" in text and f"EXPLAINER_JOB_ID={e['id']}" in text
    assert "CLAUDECODE=" not in text and "CLAUDE_CODE_SESSION_ID" not in text, text
    assert jq.get(e["id"])["submitted_by"]["session"] == "test-session"

    # 7. A job that outlives its budget is killed and failed, not left holding the queue.
    t, _ = jq.submit("cmd", sh("sleep 60"), label="slow", timeout_s=2)
    t0 = time.time()
    drain()
    d = jq.get(t["id"])
    assert d["state"] == "failed" and "timed out" in d["note"], d
    assert time.time() - t0 < 30

    # 8. Cancel: a queued job never runs; a running one is killed.
    q1, _ = jq.submit("cmd", sh("echo never"), label="never")
    assert jq.cancel(q1["id"])["state"] == "cancelled"
    drain()
    assert jq.get(q1["id"])["state"] == "cancelled"
    assert not Path(jq.get(q1["id"])["log"]).exists()
    r1, _ = jq.submit("cmd", sh("sleep 60"), label="running")
    th = threading.Thread(target=drain)
    th.start()
    for _ in range(100):
        if jq.get(r1["id"])["state"] == "running":
            break
        time.sleep(0.1)
    assert jq.get(r1["id"])["state"] == "running"
    jq.cancel(r1["id"])
    th.join(timeout=40)
    assert not th.is_alive(), "cancelling the running job must release the runner"
    assert jq.get(r1["id"])["state"] == "cancelled"

    # 9. A job left `running` by a dead runner is re-queued once and then runs.
    z, _ = jq.submit("cmd", sh("echo recovered"), label="z")
    dead = subprocess.Popen(["/usr/bin/true"])
    dead.wait()
    jq.update(z["id"], state="running", pid=dead.pid, pid_started="never", attempts=1)
    drain()
    d = jq.get(z["id"])
    assert d["state"] == "done" and "recovered" in Path(d["log"]).read_text(), d
    # ...but not forever.
    y, _ = jq.submit("cmd", sh("echo y"), label="y")
    jq.update(y["id"], state="running", pid=dead.pid, pid_started="never",
              attempts=jq.MAX_ATTEMPTS)
    drain()
    assert jq.get(y["id"])["state"] == "failed"

    # 10. Routed argv: the project path is made canonical, the wait flags are dropped.
    link = Path(_TMP) / "link"
    real = Path(_TMP) / "real proj"
    real.mkdir()
    link.symlink_to(real)

    class A:
        pass
    args = A()
    args.project_dir = str(link)
    args._argv = ["shorts", str(link), "--only", "cut-1", "--no-wait", "--wait-secs", "30"]
    assert cli._routed_argv(args) == ["shorts", str(real.resolve()), "--only", "cut-1"]
    assert cli._is_heavy(None) and cli._is_heavy({"align"}) and not cli._is_heavy({"manifest", "qa"})

    # 10b. A child of a job that holds the engine lock passes through instead of
    #      deadlocking on its own parent (`explainer2 submit -- <script that locks>`).
    from explainer2 import renderlock
    os.environ[renderlock.HELD_ENV] = "1"
    said = []
    try:
        assert renderlock.acquire(label="inner", log=said.append) is None
    finally:
        os.environ.pop(renderlock.HELD_ENV)
    assert "passing through" in said[0], said
    renderlock.release(None)                        # and releasing that is a no-op
    assert jq._exec_locked(["--label", "t", "--no-lock", "--", "/usr/bin/true"]) == 0
    assert jq._exec_locked(["--no-lock", "--", "/usr/bin/false"]) == 1

    # 11. Status reads, and names the queue.
    s = jq.status_text()
    assert s.startswith("RENDER QUEUE:") and "ENGINE LOCK:" in s, s

    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
    print("OK — test_jobqueue")


if __name__ == "__main__":
    sys.exit(main())
