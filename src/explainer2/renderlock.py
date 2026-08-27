"""Machine-global render lock + detached render launcher — serializes the
memory-heavy render+mux stage (headless-Chrome frame capture + ffmpeg encode)
across ALL explainer projects and background routines on this Mac, and launches
renders DETACHED from the calling Claude session so app-suspension can't kill
them mid-encode.

Two concerns, two mechanisms:

1. SERIALIZE — an `fcntl.flock` on a FIXED machine-global lockfile. Every
   codebase that renders imports a copy of this module pointing at the SAME
   `LOCKFILE`, so they serialize across codebases (explainer2 AND v1
   explainer-system, which the CVG routine uses). flock is released by the OS
   when the holder dies — even on SIGKILL — so a crashed render never deadlocks
   the queue. acquire() polls non-blocking so the wait is visible in run.log.

2. SURVIVE — `launch_detached()` runs `media` in its own session
   (`start_new_session=True`, the portable macOS `setsid`) under `caffeinate`,
   so suspending/closing the Claude app leaves the render running. This — not
   the lock — is what kept killing #10/#36/medtech (the render was a child of
   the session). caffeinate blocks OS idle-sleep but NOT task termination.

3. FOREIGN-ENCODE GUARD (added 2026-08-05, after #55) — the flock is
   COOPERATIVE and therefore only covers codebases that import this module.
   Any project that renders without it is invisible to the queue: it never takes
   the lock, so nothing holds it back and nothing tells us it is running. On
   2026-08-05 #55 rendered for 37 minutes alongside waveform-studio's 8-hour
   1440p encode and a daily_beats Remotion render — neither of which took the
   lock at the time — with load average above 90 and ~113 MB free, and produced a
   structurally complete but corrupt h264 bitstream: right duration, right frame
   count, wrong colors, unseekable, NAL errors from the first second. That is
   the PRD's "serialize memory-heavy stages" constraint being broken by projects
   the lock was never wired into.

   So after taking the flock we also wait for any VIDEO ENCODE running outside
   our session to finish. **This is deliberately not the check that was removed
   on 2026-06-21** (see below): that one matched `chrome-headless-shell`, which
   an idle MCP browser also has, so a parked LinkedIn/patchright session looked
   identical to a render and deadlocked the queue. This one matches an ffmpeg
   command line that names a video ENCODER (h264_videotoolbox, libx264, …),
   which only exists while an encode is actually running and which no idle
   browser has. Own-session encodes are excluded by session id, so our own mux
   never blocks us.

   Both named projects have since been wired in: waveform-studio and daily_beats
   vendor this module verbatim and route their encodes through it, and as of
   2026-08-26 daily_beats also holds the lock across its mlx_whisper model load
   (capture_video.transcribe). The guard stays anyway — the flock is still
   cooperative, and the next non-participant is one bare subprocess.run away.
   Keep all three copies byte-identical; a divergent copy is a silent outage.

   Escape hatches, because a guard that cannot be turned off is its own outage:
   `EXPLAINER_FOREIGN_ENCODE_GUARD=0` disables it, and
   `EXPLAINER_FOREIGN_ENCODE_MAX_WAIT=<seconds>` changes the ceiling. On timeout
   it raises with the offending commands named, rather than rendering anyway --
   a loud failure costs one re-run, a silent one costs a corrupt master nobody
   notices until QA.

NOTE: an earlier version also sniffed for a "foreign render" via `pgrep
chrome-headless-shell` — that false-positived on persistent MCP headless
browsers (LinkedIn/patchright) and deadlocked the queue. Removed 2026-06-21.
The cooperative flock is sufficient for codebases that hold it; concern 3 is
what covers the ones that do not.

Usage:
  - media stage loop: acquire() before `render`, release() after `mux`.
  - to start a render that survives the session: `<cli> render <proj>`
    (cmd_render → launch_detached). `<cli> render-status` → status().
"""
import fcntl, json, os, re, signal, subprocess, sys, time

LOCKFILE = "/tmp/explainer-render.lock"   # SHARED across codebases — do not change per-repo
TICKETFILE = "/tmp/explainer-render.tickets"   # SHARED — FIFO fairness, see take_a_ticket()
POLL_SECS = 15
TICKET_POLL_SECS = 1.0                    # cheap: a JSON read + pid liveness check
MAX_WAIT_SECS = 3 * 60 * 60               # 3h ceiling — wait long, but never forever
DEFAULT_STAGES = "render,mux,manifest,qa" # what a detached `render` runs (deck/narrate/align cached)


# ---- FIFO fairness ------------------------------------------------------------
# flock has no fairness guarantee: on release, whichever waiter the kernel happens
# to wake wins. That is fine when every participant runs one long job, and it is
# NOT fine here. A project rendering a BATCH of short clips releases and
# re-acquires continuously, so it can hold the encoder almost permanently while a
# single long job never gets a turn. On 2026-08-05 #55 sat queued 55 minutes
# behind a ~50-clip daily_beats rebuild without rendering a frame.
#
# So: take a numbered ticket before queueing, and only contend for the flock when
# your ticket is the lowest one still alive. Arrival order, not luck.
#
# DEGRADES SAFELY. The ticket file is advisory and sits BESIDE the flock, which
# remains the actual mutual exclusion. A participant that has not been updated
# still takes the flock and still renders correctly; it simply doesn't queue, so
# it can jump ahead. Updated participants stop starving EACH OTHER regardless.
# That matters because v1 explainer-system is frozen and may not be updatable.
#
# Dead holders cannot wedge the queue: every pass prunes tickets whose pid is
# gone, which covers a crashed or SIGKILLed render exactly as flock does.

def _read_tickets():
    try:
        with open(TICKETFILE) as fh:
            return json.load(fh)
    except Exception:
        return []


def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError):
        return False
    return True


def _rewrite_tickets(mutate):
    """Read-modify-write the ticket list under its own short-lived exclusive lock,
    pruning dead pids on the way through. `mutate(tickets) -> tickets`."""
    fd = open(TICKETFILE + ".guard", "a+")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        tickets = [t for t in _read_tickets() if _pid_alive(t.get("pid"))]
        tickets = mutate(tickets)
        tmp = TICKETFILE + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(tickets, fh)
        os.replace(tmp, TICKETFILE)      # atomic: a reader never sees a partial file
        return tickets
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            fd.close()
        except Exception:
            pass


def take_a_ticket(label):
    """Join the queue. Returns our ticket number."""
    mine = {}

    def _add(tickets):
        seq = max([t.get("seq", 0) for t in tickets] or [0]) + 1
        mine.update({"seq": seq, "pid": os.getpid(), "label": label,
                     "since": time.strftime("%H:%M:%S")})
        return tickets + [mine]

    _rewrite_tickets(_add)
    return mine["seq"]


def drop_ticket(seq):
    if seq is None:
        return
    try:
        _rewrite_tickets(lambda ts: [t for t in ts if t.get("seq") != seq])
    except Exception:
        pass                              # never let queue bookkeeping break a render


def _wait_for_turn(seq, log, deadline):
    """Block until our ticket is the lowest live one."""
    announced = False
    while True:
        tickets = _rewrite_tickets(lambda ts: ts)     # prunes dead pids
        ahead = [t for t in tickets if t.get("seq", 0) < seq]
        if not ahead:
            if announced:
                log("render-lock: our turn")
            return
        if not announced:
            nxt = min(ahead, key=lambda t: t.get("seq", 0))
            log(f"render-lock: queued at ticket #{seq}, {len(ahead)} ahead "
                f"(next: {nxt.get('label')} #{nxt.get('seq')})")
            announced = True
        if time.time() >= deadline:
            raise TimeoutError(f"waited behind {len(ahead)} ticket(s) past the ceiling")
        time.sleep(TICKET_POLL_SECS)

# --- foreign-encode guard (concern 3 in the module docstring) ---------------
# Names of actual video ENCODERS. Present only while an encode is running, and
# absent from an idle headless browser — which is precisely why this does not
# repeat the 2026-06-21 false positive.
_ENCODER_RE = re.compile(
    r"\b(h264_videotoolbox|hevc_videotoolbox|prores_videotoolbox|libx264|libx265|libsvtav1|libvpx-vp9)\b")
FOREIGN_GUARD = os.environ.get("EXPLAINER_FOREIGN_ENCODE_GUARD", "1") != "0"
FOREIGN_MAX_WAIT_SECS = int(os.environ.get("EXPLAINER_FOREIGN_ENCODE_MAX_WAIT", 90 * 60))


def foreign_encodes():
    """Video encodes running OUTSIDE this process's session.

    Own-session processes are excluded, so our own render/mux never blocks us:
    `launch_detached` starts the render with start_new_session=True, and every
    ffmpeg it spawns inherits that session id.
    """
    try:
        out = subprocess.run(["ps", "-Ao", "pid=,sid=,command="],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return []          # never let a failed probe block a render
    try:
        mine = os.getsid(0)
    except Exception:
        mine = None
    found = []
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        pid, sid, cmd = parts
        if not _ENCODER_RE.search(cmd):
            continue
        try:
            if mine is not None and int(sid) == mine:
                continue   # our own pipeline
            if int(pid) == os.getpid():
                continue
        except ValueError:
            pass
        found.append((pid, cmd))
    return found


def _wait_for_foreign_encodes(log=print):
    """Hold here until no foreign encode is running. Raises on timeout rather
    than rendering into contention, because the failure mode we are avoiding is
    a corrupt master that looks complete."""
    if not FOREIGN_GUARD:
        return
    waited, announced = 0, False
    while True:
        found = foreign_encodes()
        if not found:
            if announced:
                log("render-lock: foreign encodes finished — starting render")
            return
        if not announced:
            try:
                load = f"{os.getloadavg()[0]:.0f}"
            except Exception:
                load = "?"
            log(f"render-lock: {len(found)} video encode(s) running outside the lock "
                f"(load {load}) — waiting so we don't corrupt the master")
            for _pid, cmd in found[:3]:
                log(f"render-lock:   pid {_pid}: {cmd[:110]}")
            announced = True
        if waited >= FOREIGN_MAX_WAIT_SECS:
            names = "; ".join(f"pid {p}: {c[:70]}" for p, c in found[:3])
            raise TimeoutError(
                f"foreign video encode still running after {FOREIGN_MAX_WAIT_SECS // 60} min "
                f"({names}). Rendering now risks a corrupt master (see #55, 2026-08-05). "
                f"Wait for it, or set EXPLAINER_FOREIGN_ENCODE_GUARD=0 to override.")
        time.sleep(POLL_SECS)
        waited += POLL_SECS


def _blocking_flock(fd, timeout_secs):
    """Wait in the kernel for the lock instead of polling for it.

    Why (2026-08-05, #55): the original loop polled every POLL_SECS. A project
    running a long BATCH of short encodes releases and immediately re-acquires,
    so a 15-second poller loses that race essentially every time. #55 sat queued
    for 55 minutes without rendering a frame while daily_beats worked through a
    ~50-clip catalog rebuild, cycling the lock past us repeatedly.

    flock() has no FIFO guarantee, but a waiter blocked IN the call is woken by
    the kernel the moment the holder releases, which beats a poller that will not
    look again for another 15 seconds. This is a one-sided fix: it changes only
    how WE wait, needs no cooperation from the other projects, and leaves the
    semantics of the lock itself untouched.
    """
    def _timed_out(_signum, _frame):
        raise TimeoutError("render lock wait timed out")

    old = signal.signal(signal.SIGALRM, _timed_out)
    signal.alarm(max(1, int(timeout_secs)))
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def acquire(proj=None, label=None, log=print):
    """Block until the render engine is free, then return the held lock fd.
    Pass the result to release() after mux."""
    label = label or (os.path.basename(str(getattr(proj, "dir", ""))) or "render")
    fd = open(LOCKFILE, "a+")

    # Join the FIFO queue and wait for our turn before contending for the flock,
    # so arrival order decides rather than which waiter the kernel happens to wake.
    seq = None
    try:
        seq = take_a_ticket(label)
        _wait_for_turn(seq, log, time.time() + MAX_WAIT_SECS)
    except TimeoutError:
        drop_ticket(seq)
        try: fd.close()
        except Exception: pass
        raise
    except Exception:
        seq = None            # queue bookkeeping must never block a render

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        try:
            fd.seek(0); held = fd.read().strip()
        except Exception:
            held = ""
        log(f"render-lock: engine busy ({held or 'another project'}) — queued, waiting…")
        try:
            _blocking_flock(fd, MAX_WAIT_SECS)
        except TimeoutError:
            drop_ticket(seq)
            try: fd.close()
            except Exception: pass
            raise TimeoutError(
                f"render lock not acquired after {MAX_WAIT_SECS // 60} min ({held})")
        announced = True
    else:
        announced = False
    # We hold the real lock now, so leave the queue. Dropping here rather than at
    # release() means a render that dies mid-encode cannot leave a ticket wedging
    # everyone behind it — the flock is the exclusion, the ticket was only the turn.
    drop_ticket(seq)
    try:
        fd.seek(0); fd.truncate()
        fd.write(json.dumps({"pid": os.getpid(), "label": label, "since": time.strftime("%H:%M:%S")}))
        fd.flush()
    except Exception:
        pass
    if announced:
        log("render-lock: engine free — acquired")
    # Hold the flock while we wait, so other explainer renders queue behind us
    # rather than racing into the same contention.
    try:
        _wait_for_foreign_encodes(log=log)
    except Exception:
        release(fd)
        raise
    return fd


def release(fd):
    if fd is None:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        fd.close()  # closing the fd also releases the flock
    except Exception:
        pass


# ---- job admission control ----------------------------------------------------
# The flock above serializes STAGES. It does not stop a whole JOB from starting,
# and on 2026-08-26 that distinction cost a machine. A Claude session forked at
# 21:11:44Z; both halves stayed live, and 3.5 minutes later each independently ran
# the same `for mod in (module-02, module-01): Popen(... shorts ...)` launcher.
# Four detached jobs, two of them on the SAME cut. The render lock did its job
# perfectly — one render at a time — while four torch heaps (Kokoro + MMS_FA,
# 2.5-3.3 GB apiece) sat on top of each other and tripped the macOS out-of-memory
# dialog on a 16 GB Mac. Serializing the work does not help if N copies of the
# work are resident at once.
#
# So: a job claims an admission slot before it does anything expensive. Two gates,
# both cheap and both fail-safe:
#   1. PER-PROJECT — one job of a given kind per project directory. This alone
#      would have blocked the duplicate module-02 launch.
#   2. MACHINE-WIDE — a ceiling on total live jobs across every project.
# flock is released by the OS on death (even SIGKILL), so a crashed job never
# wedges the gate and no stale-pid reaping is needed.
JOBDIR = "/tmp/explainer-jobs"
MAX_CONCURRENT_JOBS = 2          # total heavy explainer jobs resident at once


def _job_lock_path(project_dir, kind):
    safe = re.sub(r"[^A-Za-z0-9]+", "_", str(project_dir).strip("/"))[-120:]
    return os.path.join(JOBDIR, f"{kind}-{safe}.lock")


def _live_claims():
    """Count job lockfiles currently held. A lock we can take is a dead holder's."""
    live = 0
    try:
        names = os.listdir(JOBDIR)
    except OSError:
        return 0
    for name in names:
        if not name.endswith(".lock"):
            continue
        p = os.path.join(JOBDIR, name)
        try:
            fh = open(p, "a+")
        except OSError:
            continue
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fh, fcntl.LOCK_UN)   # nobody held it — stale file, not a job
        except OSError:
            live += 1                        # held by a living process
        finally:
            fh.close()
    return live


JOB_ENV = "EXPLAINER_JOB_CLAIMED"   # inherited by children — see claim_job()


class _Passthrough:
    """Returned by claim_job() when this process is already inside a claimed job.
    It owns no slot, so release_job() on it is a no-op."""
    __slots__ = ()


def claim_job(project_dir, kind="shorts", log=print, wait=False):
    """Admission slot for one whole heavy job. Returns a handle to hold for the
    job's lifetime, or None when the job must not start.

    Release with `release_job()`, NOT `release()` — the slot carries an env flag
    that release_job clears.

    HOLD THE RETURNED HANDLE in a variable that outlives the job. It is the open
    file whose flock IS the slot: let it be garbage-collected and the file closes,
    the flock drops, and the slot silently disappears while the job runs on. So
    `claim = claim_job(...)`, never `if claim_job(...):` — the latter reads as
    working code and gates nothing.

    Two distinct refusals, deliberately treated differently:

    * SAME PROJECT, same kind -> always refused, never waited for. A second job on
      the same project is a duplicate, and waiting only repeats the identical work
      later. This is the gate that would have stopped the 2026-08-26 incident,
      where a forked session launched two jobs against the same module.
    * MACHINE-WIDE CAP -> refused, or waited out when `wait=True`. Unattended
      routines pass wait=True: hard-failing a scheduled run because two other jobs
      happened to be resident drops a day's output, and the wait is nearly free
      because callers claim BEFORE importing their models. A queued process is a
      bare interpreter, not a resident 3 GB heap. That ordering is the whole
      reason waiting is safe here; do not claim after an import.

    Nested claims pass through. A job that shells out to a sibling script would
    otherwise have its own child refused on the parent's key — daily_beats alone
    has five such spawns (extract_shorts -> transcribe_clip, caption_shorts ->
    caption_clips, ...). The env flag is inherited across fork/exec, which is
    exactly the scope wanted: "this process tree already holds a slot."
    """
    if os.environ.get(JOB_ENV):
        return _Passthrough()
    os.makedirs(JOBDIR, exist_ok=True)
    path = _job_lock_path(project_dir, kind)
    fh = open(path, "a+")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        log(f"REFUSED: a `{kind}` job is already running for {project_dir} "
            f"(admission lock {path}). Not starting a second one.")
        return None
    deadline = time.time() + MAX_WAIT_SECS
    waited = 0
    while True:
        # Count under a guard so two simultaneous starters cannot both see room.
        guard = open(os.path.join(JOBDIR, ".admission.guard"), "a+")
        try:
            fcntl.flock(guard, fcntl.LOCK_EX)
            live = _live_claims()      # includes the claim we already hold
            if live <= MAX_CONCURRENT_JOBS:
                break
        finally:
            release(guard)
        if not wait:
            release(fh)
            log(f"REFUSED: {live - 1} heavy explainer job(s) already running "
                f"(cap {MAX_CONCURRENT_JOBS}). Not starting `{kind}` for "
                f"{project_dir}; re-run when the queue drains.")
            return None
        if time.time() > deadline:
            release(fh)
            log(f"REFUSED: waited {MAX_WAIT_SECS}s for an admission slot and the "
                f"queue never drained (cap {MAX_CONCURRENT_JOBS}). Giving up on "
                f"`{kind}` for {project_dir} rather than waiting forever.")
            return None
        if waited % 20 == 0:           # first pass, then every ~5 min
            log(f"admission: {live - 1} job(s) ahead (cap {MAX_CONCURRENT_JOBS}) "
                f"— `{kind}` queued, waiting…")
        waited += 1
        time.sleep(POLL_SECS)
    os.environ[JOB_ENV] = "1"          # inherited by every child this job spawns
    try:
        fh.seek(0); fh.truncate()
        fh.write(json.dumps({"pid": os.getpid(), "kind": kind,
                             "project": str(project_dir),
                             "since": time.strftime("%H:%M:%S")}))
        fh.flush()
    except Exception:
        pass                            # diagnostics only; the flock is the gate
    return fh


def release_job(claim):
    """Release an admission slot taken by claim_job(). Safe on None and on the
    pass-through handle a nested claim returns."""
    if claim is None or isinstance(claim, _Passthrough):
        return                          # owns no slot; the outer claim does
    os.environ.pop(JOB_ENV, None)
    release(claim)


def run_locked(cmd, label="ffmpeg", log=print, **run_kwargs):
    """Run a heavy encode subprocess (ffmpeg splice, post-mux re-encode, B-roll
    or SV-clip compositing) UNDER the machine-global render lock, so it
    serializes against scheduled explainer/explainer2 renders instead of
    fighting them for the 16 GB budget.

    HARD RULE: never invoke ffmpeg raw for an encode/render now that this exists.
    Route every hand-rolled heavy ffmpeg through here. (On 2026-06-23 a raw
    B-roll splice overlapped Founder Tip Tuesday's render and got OOM-killed
    mid-write — exactly what the lock exists to prevent.)

    Blocks until the lock frees (logs 'queued, waiting'), runs `cmd`, and
    releases on success OR failure. Returns the CompletedProcess. Run the CALLER
    backgrounded so the lock wait can't trip a foreground timeout."""
    fd = acquire(label=label, log=log)
    try:
        return subprocess.run(cmd, **run_kwargs)
    finally:
        release(fd)


# ---- detached launch + status -------------------------------------------------

def _media_pid_for(project_dir):
    """pid of a live `media` python process for this project dir, or None
    (idempotency guard so we never double-encode the same project)."""
    base = os.path.basename(os.path.normpath(project_dir))
    try:
        out = subprocess.run(["pgrep", "-f", f"cli media .*{base}"],
                             capture_output=True, text=True)
    except Exception:
        return None
    me = os.getpid()
    for tok in out.stdout.split():
        try:
            pid = int(tok)
        except ValueError:
            continue
        if pid != me:
            return pid
    return None


def launch_detached(project_dir, only=None, engine="deck", log=print):
    """Start `media --only <stages>` in its own session under caffeinate, so it
    outlives the calling Claude session. Returns a small status dict. The flock
    in cmd_media still serializes it against any other render. `engine` selects the
    deck (default) or remotion render path (motion-playbook.md)."""
    only = only or DEFAULT_STAGES
    project_dir = os.path.abspath(project_dir)
    base = os.path.basename(project_dir)
    existing = _media_pid_for(project_dir)
    if existing:
        log(f"render: already running for {base} (pid {existing}) — not relaunching")
        return {"status": "already_running", "pid": existing, "project": base}
    work = os.path.join(project_dir, "work")
    os.makedirs(work, exist_ok=True)
    # structured progress lands in run.log (cmd_media writes it); raw child
    # stdout/stderr go to render.out so the two don't interleave/duplicate.
    with open(os.path.join(work, "run.log"), "a") as rl:
        rl.write(f"{time.strftime('%H:%M:%S')} render: detached launch (--only {only}, engine {engine})\n")
    outf = open(os.path.join(work, "render.out"), "a")
    pkg = __name__.rsplit(".", 1)[0]          # "explainer2" or "explainer"
    cmd = ["caffeinate", "-i", sys.executable, "-m", f"{pkg}.cli",
           "media", project_dir, "--only", only, "--engine", engine]
    p = subprocess.Popen(cmd, stdout=outf, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True,
                         env=os.environ.copy())
    log(f"render: launched DETACHED for {base} (pid {p.pid}) — survives session suspension; "
        f"watch {os.path.join('work', 'run.log')}")
    return {"status": "launched", "pid": p.pid, "project": base, "only": only,
            "out": os.path.join(work, "render.out")}


def _holder():
    """Current lockfile holder note + whether that pid is actually alive."""
    try:
        with open(LOCKFILE) as f:
            data = json.loads(f.read() or "{}")
    except Exception:
        return None
    pid = data.get("pid")
    alive = False
    if pid:
        try:
            os.kill(int(pid), 0); alive = True
        except Exception:
            alive = False
    data["alive"] = alive
    return data


def _running_media():
    """[{pid, etime, dir, project}] for each live media render (deduped per project)."""
    try:
        out = subprocess.run(["ps", "-ax", "-o", "pid=,etime=,command="],
                             capture_output=True, text=True)
    except Exception:
        return []
    seen, rows = set(), []
    for line in out.stdout.splitlines():
        if "cli media" not in line or "pgrep" in line:
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid, etime, cmd = parts
        toks = cmd.split()
        if toks and "caffeinate" in toks[0]:   # keep the python proc, drop its caffeinate wrapper
            continue
        pdir = ""
        if "media" in toks:
            i = toks.index("media")
            if i + 1 < len(toks):
                pdir = toks[i + 1]
        base = os.path.basename(pdir.rstrip("/")) if pdir else "?"
        if base in seen:
            continue
        seen.add(base)
        rows.append({"pid": int(pid), "etime": etime, "dir": pdir, "project": base})
    return rows


def _last_log(project_dir):
    try:
        with open(os.path.join(project_dir, "work", "run.log")) as f:
            tail = [l.strip() for l in f if l.strip()]
        return tail[-1] if tail else "(no log)"
    except Exception:
        return "(no log)"


def status():
    """Human-readable render-queue view: who holds the lock + every live render."""
    h = _holder()
    if h and h.get("alive"):
        head = f"LOCK held by: {h.get('label', '?')} (pid {h['pid']}, since {h.get('since', '?')})"
    elif h and h.get("pid"):
        head = f"LOCK free (stale note: {h.get('label', '?')}, pid {h['pid']} not alive)"
    else:
        head = "LOCK free"
    procs = _running_media()
    lines = [head]
    if procs:
        lines.append(f"{len(procs)} render(s) live:")
        for p in procs:
            lines.append(f"  • {p['project']} (pid {p['pid']}, up {p['etime']}) — {_last_log(p['dir'])}")
    else:
        lines.append("no renders running")
    return "\n".join(lines)
