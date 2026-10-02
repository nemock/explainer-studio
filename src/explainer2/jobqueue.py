"""The render queue: the ONE way a render or encode reaches this Mac's encoder.

Why this exists (2026-10-01). `renderlock.py` is a lock, not a queue. A "queued" job
was a live process blocked on a flock, living inside whatever launched it, so whether
it survived depended on who started it: a job the launchd recording watcher launched
outlived an app quit, and one a Claude session launched did not (two renders and two
booths died with a force-quit that morning). Only `explainer2 render` detached itself;
`shorts`, `media`, `mark_stills` and every ad-hoc still or encode ran in the caller's
foreground, and the rule that they should not asked each session to hand-write a
launcher. Six sessions in 29 hours took the one-line path instead.

So submitting is now an operation the system offers:

  * a job is a small JSON file in a spool on the boot volume
  * a launchd agent (tools/render_queue.py) runs jobs ONE AT A TIME, lowest priority
    number first and oldest first within a priority, entirely outside any Claude session
  * the heavy CLI verbs submit themselves when they are run from inside a session, then
    wait cheaply for the result, so the command a session already types is the right one
  * the recording watcher submits its phase-1 renders to the same spool

The flock in renderlock.py is untouched and still taken inside each job. It is what
serializes this queue against the codebases that do not use the spool (waveform-studio,
daily_beats), and it remains the mutual exclusion; the spool decides order and ownership.

The queue is OPT-IN per machine: it is on when `<spool>/enabled` exists (written by the
installer, see tools/render_queue.py --install-help). Without it every verb behaves
exactly as before, so a fresh clone of this public repo is unaffected.
"""
import fcntl
import hashlib
import json
import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Lower runs first. Within a priority, oldest first.
PRI_SHOW = 10      # booth-show phase 1: a recorded episode waiting to publish
PRI_QUICK = 20     # stills, mark checks, ad-hoc commands: short, and a session is waiting
PRI_MEDIA = 30     # a media/render job from a session or routine
PRI_SHORTS = 40
PRI_STUDIO = 50    # long-form studio phase 1
DEFAULT_PRIORITY = {"phase1": PRI_SHOW, "cmd": PRI_QUICK, "mark_stills": PRI_QUICK,
                    "adlib": PRI_QUICK, "media": PRI_MEDIA, "narrate": PRI_MEDIA,
                    "align": PRI_MEDIA, "mux": PRI_MEDIA, "shorts": PRI_SHORTS}

# Wall-clock ceiling per job, counted from launch. Generous on purpose: a job can sit
# on the engine flock behind a multi-hour waveform encode before it renders a frame,
# and renderlock's own 3 h ceiling fails it loudly long before this does.
DEFAULT_TIMEOUT_S = {"cmd": 2 * 3600, "mark_stills": 2 * 3600, "adlib": 2 * 3600}
FALLBACK_TIMEOUT_S = 6 * 3600

MAX_ATTEMPTS = 2                 # a job interrupted by a reboot or a runner kill is re-queued once
WAIT_DEFAULT_S = 540             # under the Bash tool's 10-minute cap
WAIT_POLL_S = 2.0
RC_STILL_RUNNING = 75            # EX_TEMPFAIL: not a failure, re-issue `explainer2 wait <id>`
ACTIVE = ("queued", "running")
PATH_PREPEND = "/opt/homebrew/bin:/usr/local/bin"   # launchd's PATH has neither; npx/ffmpeg need both
HEAVY_STAGES = {"narrate", "align", "render", "mux"}


# ---- where the spool lives ---------------------------------------------------

def spool():
    """Boot volume on purpose: /tmp is wiped, and a launchd job cannot rely on
    /Volumes being mounted when it starts."""
    d = os.environ.get("EXPLAINER_QUEUE_DIR")
    return Path(d) if d else Path.home() / "Library" / "Application Support" / "explainer2" / "queue"


def enabled():
    return (spool() / "enabled").exists()


def in_session():
    """True inside a Claude Code session's tool call. The runner clears this for its
    children, so a job never tries to re-submit itself."""
    return os.environ.get("CLAUDECODE") == "1" and not os.environ.get("EXPLAINER_QUEUE_RUNNER")


def should_route():
    """A heavy verb run from a session goes to the queue instead of running inline."""
    return enabled() and in_session()


# ---- job records ---------------------------------------------------------------

def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _jobs_dir():
    d = spool() / "jobs"
    d.mkdir(parents=True, exist_ok=True)
    return d


class _Guard:
    """Short exclusive lock around every read-modify-write of the spool."""

    def __enter__(self):
        spool().mkdir(parents=True, exist_ok=True)
        self.fh = open(spool() / ".guard", "a+")
        fcntl.flock(self.fh, fcntl.LOCK_EX)
        return self

    def __exit__(self, *_):
        try:
            fcntl.flock(self.fh, fcntl.LOCK_UN)
        finally:
            self.fh.close()


def _write(job):
    p = _jobs_dir() / f"{job['id']}.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(job, indent=1))
    os.replace(tmp, p)               # a reader never sees a half-written job


def get(job_id):
    try:
        return json.loads((_jobs_dir() / f"{job_id}.json").read_text())
    except (OSError, ValueError):
        return None


def jobs(states=None):
    out = []
    for p in _jobs_dir().glob("*.json"):
        try:
            j = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if states is None or j.get("state") in states:
            out.append(j)
    return sorted(out, key=lambda j: j.get("id", ""))


def _order(j):
    return (j.get("priority", 99), j.get("submitted_at", ""), j.get("id", ""))


def queued():
    return sorted(jobs(("queued",)), key=_order)


def update(job_id, **fields):
    """Read-modify-write one job under the guard. Returns the new record or None."""
    with _Guard():
        j = get(job_id)
        if j is None:
            return None
        j.update(fields)
        _write(j)
        return j


def _key(kind, project, argv):
    raw = json.dumps([kind, str(project or ""), list(argv)])
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def resolve(path):
    """One canonical spelling per project. `projects/` is a symlink into another repo,
    so the same project used to be three different strings, three different admission
    locks, and a kill_render that could not find a render it was pointed at."""
    return str(Path(path).resolve())


def submit(kind, argv, project=None, label=None, priority=None, cwd=None,
           timeout_s=None, log_path=None, env=None):
    """Queue a job. Returns (job, created).

    Idempotent: while a job with the same kind, project and argv is queued or running,
    submitting it again returns THAT job. Re-running a command re-attaches to it rather
    than rendering twice, which is what makes a timed-out wait safe to repeat."""
    project = resolve(project) if project else None
    argv = [str(a) for a in argv]
    key = _key(kind, project, argv)
    with _Guard():
        for j in jobs(ACTIVE):
            if j.get("key") == key:
                return j, False
        jid = time.strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(2)
        logs = spool() / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        job = {
            "id": jid, "kind": kind, "key": key, "state": "queued",
            "label": label or (Path(project).name if project else kind),
            "project": project, "argv": argv,
            "cwd": str(cwd) if cwd else str(REPO),
            "env": dict(env or {}),
            "priority": DEFAULT_PRIORITY.get(kind, PRI_MEDIA) if priority is None else int(priority),
            "timeout_s": int(timeout_s or DEFAULT_TIMEOUT_S.get(kind, FALLBACK_TIMEOUT_S)),
            "log": str(log_path) if log_path else str(logs / f"{jid}.log"),
            "submitted_at": _now(), "attempts": 0,
            "submitted_by": {"session": os.environ.get("CLAUDE_CODE_SESSION_ID", ""),
                             "entrypoint": os.environ.get("CLAUDE_CODE_ENTRYPOINT", ""),
                             "cwd": os.getcwd()},
        }
        _write(job)
    kick()
    return job, True


def cli_argv(*args):
    """argv for an explainer2 verb as the runner will launch it. Keeps `explainer2.cli
    <verb> <project>` adjacent in the command line: kill_render, render-status and the
    watcher's process matching all key on exactly that."""
    return [sys.executable, "-m", "explainer2.cli"] + [str(a) for a in args]


def cli_env():
    return {"PYTHONPATH": str(REPO / "src")}


def kick():
    """Wake the runner. The launchd agent watches `trigger`; kickstart is a faster
    second route and is allowed to fail (it is unavailable in some sandboxes)."""
    try:
        (spool() / "trigger").write_text(_now())
    except OSError:
        pass
    try:
        label = json.loads((spool() / "enabled").read_text()).get("label")
    except (OSError, ValueError, AttributeError):
        label = None
    if label:
        try:
            subprocess.run(["/bin/launchctl", "kickstart", f"gui/{os.getuid()}/{label}"],
                           capture_output=True, timeout=10)
        except Exception:
            pass


def job_active(job_id):
    j = get(job_id) if job_id else None
    return bool(j) and j.get("state") in ACTIVE


def cancel(job_id):
    """Cancel a queued job, or kill a running one and everything under it."""
    from . import childproc
    with _Guard():
        j = get(job_id)
        if j is None:
            return None
        if j.get("state") not in ACTIVE:
            return j
        was_running = j.get("state") == "running"
        j.update(state="cancelled", finished_at=_now(), note="cancelled by request")
        _write(j)
    if was_running and j.get("pid"):
        childproc.kill_tree(int(j["pid"]))
    return j


# ---- waiting (cheap: a JSON read every couple of seconds, no heavy imports) -----

def _tail(path, n=60):
    try:
        lines = Path(path).read_text(errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-n:])


def _position(job):
    q = queued()
    for i, j in enumerate(q):
        if j["id"] == job["id"]:
            return i + 1, len(q)
    return 0, len(q)


def describe(job):
    return f"{job['id']} [{job['kind']}: {job['label']}]"


def wait(job_id, timeout=WAIT_DEFAULT_S, out=print):
    """Block until the job finishes or `timeout` seconds pass.

    Returns 0 when the job succeeded, its non-zero exit code when it failed, and
    RC_STILL_RUNNING (75) when it is still queued or running at the deadline. 75 is
    not a failure: the job keeps running under launchd. Re-issue the same wait."""
    deadline = time.time() + max(0, timeout)
    last = None
    while True:
        j = get(job_id)
        if j is None:
            out(f"no such job: {job_id}")
            return 1
        state = j.get("state")
        if state != last:
            if state == "queued":
                pos, n = _position(j)
                out(f"QUEUED {describe(j)}: position {pos} of {n} waiting. The job runs "
                    f"outside this session, under launchd, and survives it.")
            elif state == "running":
                out(f"RUNNING {describe(j)} since {j.get('started_at', '?')} "
                    f"(log: {j.get('log')})")
            last = state
        if state not in ACTIVE:
            tail = _tail(j.get("log"))
            if tail:
                out(f"--- last lines of {j.get('log')} ---\n{tail}\n---")
            rc = j.get("rc")
            if state == "done":
                out(f"DONE {describe(j)} (exit 0)")
                return 0
            out(f"{state.upper()} {describe(j)} (exit {rc}){': ' + j['note'] if j.get('note') else ''}")
            return rc if isinstance(rc, int) and rc != 0 else 1
        if time.time() >= deadline:
            pos, n = _position(j)
            where = f"queued at position {pos} of {n}" if state == "queued" else "running"
            out(f"STILL {where.upper()}: {describe(j)}. This is the queue working, not a "
                f"failure. Do not start it another way. Re-issue:  "
                f"explainer2 wait {j['id']}")
            return RC_STILL_RUNNING
        time.sleep(WAIT_POLL_S)


def submit_and_wait(kind, argv, project=None, label=None, wait_secs=WAIT_DEFAULT_S,
                    no_wait=False, out=print, **kw):
    """What a heavy verb does when it is run from a session."""
    job, created = submit(kind, argv, project=project, label=label, **kw)
    verb = "SUBMITTED" if created else "ALREADY IN THE QUEUE (re-attached, not re-submitted)"
    out(f"{verb}: {describe(job)}")
    if no_wait:
        out(f"Not waiting. Check on it with:  explainer2 wait {job['id']}   or   explainer2 queue")
        return 0
    return wait(job["id"], timeout=wait_secs, out=out)


# ---- status ------------------------------------------------------------------------

def _age(iso):
    try:
        secs = time.time() - time.mktime(time.strptime(iso, "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError):
        return "?"
    if secs < 90:
        return f"{int(secs)}s"
    if secs < 5400:
        return f"{int(secs // 60)}m"
    return f"{int(secs // 3600)}h {int((secs % 3600) // 60)}m"


def _engine_lines():
    """Who holds the engine flock, who is waiting on it, and which admission claims
    are live. A flock PROBE decides held/free; the note inside the file is only a
    label, and reading it as the truth is how a live encode was once called stale."""
    from . import renderlock
    lines = []
    held = False
    try:
        fh = open(renderlock.LOCKFILE, "a+")
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fh, fcntl.LOCK_UN)
        except OSError:
            held = True
        finally:
            fh.close()
    except OSError:
        pass
    note = renderlock._holder() or {}
    if held:
        lines.append(f"ENGINE LOCK: held by {note.get('label', '?')} "
                     f"(pid {note.get('pid', '?')}, since {renderlock._since_text(note)})")
    else:
        lines.append("ENGINE LOCK: free")
    tickets = [t for t in renderlock._read_tickets() if renderlock._pid_alive(t.get("pid"))]
    for t in sorted(tickets, key=lambda t: t.get("seq", 0)):
        lines.append(f"  waiting on the lock: #{t.get('seq')} {t.get('label')} "
                     f"(pid {t.get('pid')}, since {renderlock._since_text(t)})")
    try:
        names = sorted(os.listdir(renderlock.JOBDIR))
    except OSError:
        names = []
    for name in names:
        if not name.endswith(".lock"):
            continue
        p = os.path.join(renderlock.JOBDIR, name)
        try:
            fh = open(p, "a+")
        except OSError:
            continue
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fh, fcntl.LOCK_UN)
        except OSError:                       # held: a live job
            try:
                fh.seek(0)
                d = json.loads(fh.read() or "{}")
            except ValueError:
                d = {}
            lines.append(f"  live {d.get('kind', 'job')} claim: "
                         f"{os.path.basename(str(d.get('project', name)))} (pid {d.get('pid', '?')})")
        finally:
            fh.close()
    return lines


def status_text():
    lines = []
    if not enabled():
        lines.append("RENDER QUEUE: not installed on this machine (verbs run inline).")
    else:
        running = jobs(("running",))
        q = queued()
        lines.append(f"RENDER QUEUE: {len(running)} running, {len(q)} waiting")
        for j in running:
            lines.append(f"  running  {describe(j)}  for {_age(j.get('started_at'))}  log {j.get('log')}")
        for i, j in enumerate(q, 1):
            lines.append(f"  {i:>2}. waiting  {describe(j)}  priority {j.get('priority')}  "
                         f"submitted {_age(j.get('submitted_at'))} ago")
        done = [j for j in jobs() if j.get("state") not in ACTIVE]
        done.sort(key=lambda j: j.get("finished_at", ""), reverse=True)
        for j in done[:5]:
            lines.append(f"  recent   {describe(j)}  {j.get('state')} (exit {j.get('rc')})  "
                         f"{_age(j.get('finished_at'))} ago")
        hb = spool() / "runner_heartbeat"
        try:
            lines.append(f"  runner last active {_age(time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(hb.stat().st_mtime)))} ago")
        except OSError:
            lines.append("  runner has not run yet")
    lines += _engine_lines()
    return "\n".join(lines)


# ---- the runner (launchd; never a Claude session) ----------------------------------

def _notify(title, text):
    if os.environ.get("EXPLAINER_QUEUE_QUIET"):     # tests
        return
    safe = lambda v: str(v).replace("\\", " ").replace('"', "'")
    try:
        subprocess.run(["/usr/bin/osascript", "-e",
                        f'display notification "{safe(text)[:220]}" with title "{safe(title)}"'],
                       capture_output=True, timeout=15)
    except Exception:
        pass


def _proc_start(pid):
    try:
        return subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True,
                              text=True, timeout=15).stdout.strip()
    except Exception:
        return ""


def _recover(log):
    """Jobs left `running` by a runner that died. The runner holds a single-instance
    flock for its whole life, so nothing can legitimately be running when a new one
    starts: kill whatever is left of the old child and put the job back."""
    from . import childproc
    for j in jobs(("running",)):
        pid = j.get("pid")
        if pid and _proc_start(pid) and _proc_start(pid) == j.get("pid_started"):
            log(f"recover: {describe(j)} still has a live child pid {pid}; killing its tree")
            childproc.kill_tree(int(pid))
        if j.get("attempts", 0) < MAX_ATTEMPTS:
            update(j["id"], state="queued", pid=None, note="interrupted; re-queued")
            log(f"recover: re-queued {describe(j)}")
        else:
            update(j["id"], state="failed", rc=-1, finished_at=_now(),
                   note=f"interrupted {MAX_ATTEMPTS}x; giving up")
            log(f"recover: gave up on {describe(j)}")
            _notify("Render queue", f"{j['label']}: interrupted {MAX_ATTEMPTS}x, not retried.")


def _child_env(job):
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("CLAUDE") or k == "EXPLAINER_JOB_CLAIMED")}
    env["PATH"] = PATH_PREPEND + ":" + env.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
    env.update(job.get("env") or {})
    env["EXPLAINER_QUEUE_RUNNER"] = "1"
    env["EXPLAINER_JOB_ID"] = job["id"]
    return env


def _run_one(job, log, state):
    from . import childproc
    Path(job["log"]).parent.mkdir(parents=True, exist_ok=True)
    logf = open(job["log"], "a")
    logf.write(f"[queue] {_now()} start {describe(job)}\n[queue] $ {' '.join(job['argv'])}\n")
    logf.flush()
    try:
        p = subprocess.Popen(["/usr/bin/caffeinate", "-ims"] + job["argv"], cwd=job.get("cwd") or None,
                             env=_child_env(job), start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=logf, stderr=subprocess.STDOUT)
    except OSError as e:
        logf.write(f"[queue] could not start: {e}\n")
        logf.close()
        update(job["id"], state="failed", rc=127, finished_at=_now(), note=f"could not start: {e}")
        _notify("Render queue", f"{job['label']}: could not start ({e}).")
        return
    state["child"] = p
    update(job["id"], state="running", pid=p.pid, pid_started=_proc_start(p.pid),
           started_at=_now(), attempts=job.get("attempts", 0) + 1, note="")
    log(f"started {describe(job)} pid {p.pid}")
    timed_out = False
    try:
        rc = p.wait(timeout=job.get("timeout_s") or FALLBACK_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        timed_out = True
        log(f"TIMEOUT {describe(job)} after {job.get('timeout_s')}s; killing its tree")
        childproc.kill_tree(p.pid)
        try:
            rc = p.wait(timeout=30)
        except Exception:
            rc = -9
    state["child"] = None
    logf.write(f"[queue] {_now()} exit {rc}{' (timed out)' if timed_out else ''}\n")
    logf.close()
    cur = get(job["id"]) or {}
    if cur.get("state") == "cancelled":           # cancel() already recorded the outcome
        update(job["id"], rc=rc)
        log(f"cancelled {describe(job)}")
        return
    if rc == 0 and not timed_out:
        update(job["id"], state="done", rc=0, finished_at=_now())
        log(f"done {describe(job)}")
        return
    note = f"timed out after {job.get('timeout_s')}s" if timed_out else ""
    update(job["id"], state="failed", rc=rc if rc else 1, finished_at=_now(), note=note)
    log(f"FAILED {describe(job)} exit {rc} {note}")
    _notify("Render queue", f"{job['label']} ({job['kind']}) failed, exit {rc}. {note} "
                            f"See {Path(job['log']).name}.")


def run_forever(log=print):
    """Drain the spool, one job at a time, then exit. launchd starts this whenever a
    job is submitted (WatchPaths) and on an interval as a backstop."""
    from . import childproc
    spool().mkdir(parents=True, exist_ok=True)
    lockf = open(spool() / "runner.lock", "a+")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0                                   # another runner is already draining
    state = {"child": None}

    def _terminate(signum, _frame):
        p = state.get("child")
        if p is not None and p.poll() is None:
            log(f"runner caught {signal.Signals(signum).name}; stopping the running job")
            childproc.kill_tree(p.pid)
        for j in jobs(("running",)):               # leave it for the next runner to re-queue
            update(j["id"], note="runner stopped")
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            signal.signal(s, _terminate)
        except ValueError:
            pass                                   # not the main thread (tests)
    _recover(log)
    while True:
        try:
            (spool() / "runner_heartbeat").write_text(_now())
        except OSError:
            pass
        q = queued()
        if not q:
            return 0
        _run_one(q[0], log, state)


# ---- `python -m explainer2.jobqueue exec-locked --label L -- <cmd...>` ------------

def _exec_locked(argv):
    """Run an arbitrary command under the engine flock. This is how an ad-hoc still or
    encode (`explainer2 submit -- npx remotion still …`) serializes against renders in
    the codebases that do not use the spool."""
    from . import childproc, renderlock
    label = "cmd"
    if argv and argv[0] == "--label":
        label, argv = argv[1], argv[2:]
    no_lock = False
    if argv and argv[0] == "--no-lock":
        no_lock, argv = True, argv[1:]
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        print("exec-locked: no command given")
        return 2
    lock = None
    childproc.on_terminate(lambda: renderlock.release(lock))
    childproc.install_handlers(log=print)
    env = dict(os.environ)
    if not no_lock:
        lock = renderlock.acquire(label=label, log=print)
        env[renderlock.HELD_ENV] = "1"      # a child that locks for itself passes through
    try:
        return childproc.run(argv, label=label, env=env).returncode
    except FileNotFoundError as e:
        print(f"exec-locked: {e}")
        return 127
    finally:
        renderlock.release(lock)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "exec-locked":
        sys.exit(_exec_locked(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        sys.exit(run_forever(log=lambda m: print(f"{_now()} {m}", flush=True)))
    print(status_text())
