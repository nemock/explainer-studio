"""Heavy-child process management — run renders/encodes in their own process GROUP
and take them down with us.

The bug this exists for (2026-08-10): a Phase-1 render was killed by hand and kept
rendering. The watcher starts Phase 1 as `caffeinate -ims /bin/sh -c '<verbs>'`;
killing the `/bin/sh` parent reaped only the shell. `npm exec remotion render`, its
`node` child and the whole `chrome-headless-shell` tree survived, reparented to
init, and kept writing frames — while the render lock's recorded pid was already
dead, which is the known stale-holder hang.

Two mechanisms, because there are two ways a render gets killed:

1. `spawn()` / `run()` put each heavy child in its OWN session (`setsid`), so its
   pid is also its process-group id. `kill_tree()` then kills that group AND
   walks the ppid links, because a group kill alone is not sufficient here:
   `chrome-headless-shell` calls setpgid and leaves the render's process group,
   so signalling the group reaps npm/node/compositor and leaves the browser
   fleet running (verified on a live render, 2026-08-10). Tracked in a registry
   for (2).
2. `install_handlers()` traps SIGTERM/SIGINT/SIGHUP in the parent, kills every
   tracked child group, runs the caller's cleanup (release the render lock), and
   then re-raises the signal so the exit status is honest.

SIGKILL cannot be trapped — nothing here saves a `kill -9`. For that, and for a
kill aimed at the shell/caffeinate wrapper rather than at us,
`tools/kill_render.py` group-kills the whole Phase-1 session and sweeps orphans.
"""
import os
import signal
import subprocess
import threading
import time

_live = {}                    # pgid -> label
_lock = threading.Lock()
_cleanup = []                 # callables run once, on a trapped termination
_installed = False

TERM_GRACE_S = 8.0            # chrome-headless-shell wants a moment to unwind


def _track(pgid, label):
    with _lock:
        _live[pgid] = label


def _untrack(pgid):
    with _lock:
        _live.pop(pgid, None)


def untrack(pgid):
    """Stop tracking a child that has exited (callers using spawn() directly)."""
    _untrack(pgid)


def _proc_table():
    """[(pid, ppid, pgid)] for every process, or [] if ps is unavailable."""
    try:
        out = subprocess.run(["ps", "-Ao", "pid=,ppid=,pgid="],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return []
    rows = []
    for line in out.split("\n"):
        f = line.split()
        if len(f) >= 3:
            try:
                rows.append((int(f[0]), int(f[1]), int(f[2])))
            except ValueError:
                pass
    return rows


def descendants(root_pid):
    """Every process under root_pid, by parent link.

    A process-group kill is not enough on its own: `chrome-headless-shell` calls
    setpgid and leaves the render's group, so `killpg(remotion_pgid)` reaps npm,
    node and the compositor but leaves the whole browser fleet running (observed
    directly, 2026-08-10). Walking ppid catches it; the snapshot is taken BEFORE
    any signal, because once the parents die the links are gone."""
    kids = {}
    pgids = {}
    for pid, ppid, pgid in _proc_table():
        kids.setdefault(ppid, []).append(pid)
        pgids[pid] = pgid
    seen, stack = [], [root_pid]
    while stack:
        pid = stack.pop()
        for child in kids.get(pid, []):
            if child not in seen:
                seen.append(child)
                stack.append(child)
    return seen, pgids


def kill_tree(pid, grace=TERM_GRACE_S):
    """Take down a heavy child and EVERYTHING under it: its process group, the
    groups its descendants escaped into, and any straggler by pid."""
    kids, pgids = descendants(pid)
    groups, pids = {pgids.get(pid, pid)}, [pid] + kids
    for k in kids:
        groups.add(pgids.get(k, k))

    def _signal(sig):
        for g in groups:
            try:
                os.killpg(g, sig)
            except (ProcessLookupError, PermissionError, OSError):
                pass
        for p in pids:
            try:
                os.kill(p, sig)
            except (ProcessLookupError, PermissionError, OSError):
                pass

    _signal(signal.SIGTERM)
    deadline = time.time() + grace
    while time.time() < deadline:
        if not any(_alive(p) for p in pids):
            return True
        time.sleep(0.2)
    _signal(signal.SIGKILL)
    return True


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return True
    return True


def kill_all(log=None):
    """Take down every tracked heavy child group."""
    with _lock:
        pending = list(_live.items())
    for pgid, label in pending:
        if log:
            log(f"childproc: killing {label} (pid {pgid}) and every descendant")
        kill_tree(pgid)
        _untrack(pgid)
    return [label for _, label in pending]


def spawn(cmd, label="child", **kw):
    """Popen in a fresh session so the whole tree is one killable group."""
    kw["start_new_session"] = True
    p = subprocess.Popen(cmd, **kw)
    _track(p.pid, label)       # setsid makes the child its own group leader
    return p


def run(cmd, label="child", capture_output=False, text=False, check=False,
        timeout=None, **kw):
    """`subprocess.run` for a heavy child: own process group, tracked for the
    duration, untracked on exit. Same return contract as subprocess.run."""
    if capture_output:
        kw.setdefault("stdout", subprocess.PIPE)
        kw.setdefault("stderr", subprocess.PIPE)
    p = spawn(cmd, label=label, text=text, **kw)
    try:
        out, err = p.communicate(timeout=timeout)
    except BaseException:
        kill_tree(p.pid)
        p.wait()
        raise
    finally:
        _untrack(p.pid)
    cp = subprocess.CompletedProcess(cmd, p.returncode, out, err)
    if check:
        cp.check_returncode()
    return cp


def on_terminate(fn):
    """Register a cleanup (e.g. release the render lock) for trapped signals."""
    _cleanup.append(fn)


def install_handlers(log=None):
    """Trap termination so a killed render cleans up its children and its lock.

    Idempotent. Re-raises the signal with the default handler so the process
    still dies of what killed it (128+signo), rather than exiting 0."""
    global _installed
    if _installed:
        return
    _installed = True

    def handler(signum, _frame):
        name = signal.Signals(signum).name
        if log:
            log(f"childproc: caught {name} — killing render children and cleaning up")
        try:
            kill_all(log=log)
        finally:
            for fn in _cleanup:
                try:
                    fn()
                except Exception:
                    pass
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            signal.signal(s, handler)
        except (ValueError, OSError):
            pass           # not the main thread / signal unavailable — best effort
