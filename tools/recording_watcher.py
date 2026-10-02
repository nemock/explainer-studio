#!/usr/bin/env python3
"""recording_watcher.py — zero-token replacement for the per-show recording-check
scheduled tasks (2026-07-06).

The old design fired a headless Claude session every 30 minutes per show just to
check whether the operator had finished recording — ~270 sessions/week, ~50k fresh
input tokens each, nearly all no-ops. This watcher is pure Python driven by launchd
(every 5 minutes): it checks the filesystem for free and only spawns a Claude
completion run when a recording is actually DONE and the atomic publish claim is won.

Per cycle, for every enabled show in the config:
  1. Scan the show's outputs dir for a candidate project: dir named YYYY-MM-DD_*,
     date within the show's lookback window, no README.md (published) and no
     SKIPPED.md (intentionally skipped).
  2. `launch_booth.py --status <proj>`:
       DONE     -> `--claim`; if CLAIMED, spawn ONE detached completion session
                   (`caffeinate -ims claude -p <prompt>`), re-stamp the publish
                   lock with the child pid so the 45-min stale-reclaim tracks the
                   real worker, and stop scanning (max one spawn per cycle).
       PENDING  -> operator still recording; nothing to do.
       NOT_OPEN -> booth died. If the project is TODAY's and authoring finished
                   (script.json exists), relaunch the booth — zero tokens.
  3. Log actions to the config's log file. Quiet no-ops stay quiet.

Safety properties preserved from the checker design: the O_EXCL publish claim
(launch_booth.py --claim) still guarantees single completion even if the old cron
checks are accidentally re-enabled; completions are never retried blindly (the
claim's stale-reclaim handles a dead worker); the watcher itself is single-instance
via flock. Config (private, operator-specific) lives outside this public repo.

Studio mode (2026-09-13, explainer2/docs/booth-finish-local-plan.md Phase B). A show
entry with "mode": "studio" is the explainer2 studio itself — deep dives, masterclass
episodes, promos — whose booth a live Claude session opens and whose finish used to be
watched by an in-session waiter that the session reaper killed. Studio candidates are
project dirs under the entry's "project_globs" that have a work/record_done.json newer
than lookback_days; the watcher never opens or relaunches a studio booth (the session
does that) and never spawns a Claude process for it. On DONE it runs the same guards as
the shows (voice_source must be operator, adlib re-record flags, scriptguard,
render-blocked, crash-loop, the render cap), then launches phase1_render.py
--profile studio, which writes work/RESUME.md and deep-links the operator's session
back when the render is done. A studio entry may set "ignore_hours": true, because a
render at 23:00 disturbs nobody and the operator wants it waiting in the morning.

Usage: recording_watcher.py --config /path/to/shows.json [--dry-run] [--force-hours]
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

# The render queue (src/explainer2/jobqueue.py). Phase-1 renders are SUBMITTED to it
# when the config says "use_render_queue": true, so the watcher, every routine and every
# Claude session share one ordered queue. If the module cannot be imported the watcher
# launches phase 1 itself, exactly as it did before 2026-10-01.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
try:
    from explainer2 import jobqueue
except Exception:                                   # noqa: BLE001 - never cost the cycle
    jobqueue = None

DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_")

# Crashloop guard, both phases: a worker that dies in seconds gets relaunched
# every cycle and, being first in the shows list, hogs the one-job-per-cycle slot
# and starves every other show. After this many consecutive launches with no
# completion artifact, skip the project so other shows get the slot, and only
# retry it after the backoff.
#
# Phase 1 (render, artifact work/render_complete.json): 2026-08-07 npx-PATH incident.
# Phase 2 (publish, artifact README.md): 2026-08-14 expired-OAuth incident. The
# headless `claude -p` publish died on auth in ~2s, wrote nothing at all, and so
# looked identical next cycle — 1,000 respawns over six days, and because phase 2
# set `spawned` unconditionally it starved every other show's render behind it
# (FWF 2026-08-17 recorded fine and never got a slot). The pre-existing
# uploads.json check only catches a PARTIAL publish; a zero-progress failure
# sailed straight past it.
CRASHLOOP_AFTER = 3
CRASHLOOP_RETRY_SECS = 30 * 60  # ~every 6th 5-minute cycle
# Phase 1 failing identically this many launches running is a verdict, not a flake:
# stop relaunching and write BLOCKED.md. It was 6 until 2026-10-01, when the fingerprint
# was only "verb:rc" and too coarse to trust sooner. The Teardown that day re-ran the
# same align error six times over two hours before anyone was told. The fingerprint now
# carries the failing STAGE and its error text (phase1_render.record_failure), so three
# identical failures, about fifteen minutes, is evidence enough.
RENDER_BLOCK_AFTER = 3
# A failure in a stage that reads the RECORDING is not a flake at all: the same take
# fails the same way every time, and only the operator at the microphone can fix it.
# Two identical failures there is the verdict, and he is told by text message.
AUDIO_STAGES = ("narrate", "align")
RENDER_BLOCK_AFTER_AUDIO = 2
# ...but never block permanently. A fix landing in the renderer or a SKILL leaves no
# trace the watcher can see, so a block with no way back would need a human even after
# the cause was gone. One probe launch this often re-tests it: the probe clears
# everything if it now passes, and re-blocks if it does not.
RENDER_BLOCK_PROBE_SECS = 6 * 60 * 60

# Ceiling on renders running AT ONCE across every show, overridable per-config
# with "max_concurrent_renders".
#
# The `spawned` flag caps the spawn RATE at one per cycle, which is not the same
# thing: a render runs for ~an hour while cycles come every five minutes, so up
# to twelve can pile up, and each project's publish_lock only excludes a second
# worker on the SAME project. On 2026-08-20 five landed together (FTT,
# ig_carousel, WSC, Teardown, Product-Leadership module-01), two of them holding
# ~1.5 GB of Python plus a chrome-headless-shell tree. Against 31 orphaned
# Claude sessions that drove a 16 GB machine to load 105 with swap exhausted,
# and the renders then made no progress for want of RAM -- starved, not wedged.
# Renders are throughput work: running them one at a time finishes them all
# sooner than running six that are each paging.
DEFAULT_MAX_CONCURRENT_RENDERS = 1


def live_renders(cfg):
    """Count phase-1 render drivers alive right now, across every project.

    Counts OS processes rather than reading each project's publish_lock, so a
    render started outside the watcher (a manual `phase1_render.py`, or one left
    behind by a previous watcher generation) still occupies a slot.
    """
    driver = cfg.get("phase1_driver") or str(
        Path(cfg["launch_booth"]).parent / "phase1_render.py")
    try:
        out = subprocess.run(["ps", "-Ao", "args="], capture_output=True,
                             text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        # Cannot establish the count, so cannot prove there is room. Report the
        # cap to hold off launching rather than risk another pile-up.
        return DEFAULT_MAX_CONCURRENT_RENDERS
    # The driver is spawned under `caffeinate -ims <python> <driver> ...`, so both
    # caffeinate and the python child carry the driver path in their args; count
    # each render once by matching only the python invocation.
    #
    # `explainer2 shorts` jobs count too (2026-08-26). They are heavy in exactly
    # the same way as a phase-1 render — Kokoro in `narrate`, torchaudio MMS_FA
    # plus the whole waveform in `align`, 2.5-3.3 GB apiece — but they never carry
    # the phase-1 driver path, so this function could not see them. On 2026-08-26
    # four of them ran unseen; had a show come ready in that window the watcher
    # would have read "0 renders running" and launched a fifth job on top. Match
    # `explainer2.cli shorts` (the python child) and NOT `bin/explainer2 shorts`
    # (the shell wrapper), so a job is counted exactly once whether or not it was
    # started under caffeinate.
    def _counts(line):
        if "caffeinate" in line:
            return False
        if driver in line:
            return True
        if "explainer2.cli" not in line or "shorts" not in line:
            return False
        # Only a real interpreter invocation counts. A bare substring test also
        # matches any shell whose command line merely MENTIONS the job — a
        # diagnostic `pgrep -f "explainer2.cli shorts"` typed in a Claude session
        # is enough — and an inflated count makes the watcher defer a render that
        # had room to run. Require argv[0] to be a python binary.
        argv0 = line.split(" ", 1)[0].rsplit("/", 1)[-1].lower()
        return argv0.startswith("python")
    return sum(1 for line in out.splitlines() if _counts(line))


def sweep_orphan_browsers(cfg, dry):
    """Kill remotion browser trees whose parent is gone (ppid 1), every cycle.

    A chrome-headless-shell under init is never part of a live render — it only
    gets there when the node driving it has died — so this can never abort work
    (kill_render.orphan_browsers has the full argument). phase1_render.py sweeps
    on its own exit paths; this catches what it cannot: a driver killed with
    SIGKILL, a hand-run render killed in a Claude session, or a browser remotion
    leaked past its 180s connect timeout after the driver had already gone
    (2026-08-31: three trees resident for three days, each a full chrome fleet).
    Zero tokens, one `ps`; runs before the hours window so overnight leftovers
    are gone by morning."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import kill_render
        killed = kill_render.sweep_orphans(
            log=lambda m: log(cfg, f"ORPHAN-SWEEP {m}"), fix=not dry)
        if killed and not dry:
            log(cfg, f"ORPHAN-SWEEP killed {len(killed)} orphaned remotion browser "
                     f"tree(s): {killed}")
    except Exception as e:                  # a sweep failure must never cost the cycle
        log(cfg, f"ORPHAN-SWEEP failed: {e}")


def pid_alive(pid):
    """True if a process with this pid currently exists."""
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but owned by someone else
    except (ValueError, TypeError):
        return False
    return True


def read_lock(proj):
    try:
        return json.loads((Path(proj) / "work" / "publish_lock.json").read_text())
    except (OSError, ValueError):
        return None


def write_lock(proj, pid, job=None):
    f = Path(proj) / "work" / "publish_lock.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    rec = {"pid": pid, "ts": time.time()}
    if job:
        rec["job"] = job             # a queued phase-1 has no pid until the runner starts it
    f.write_text(json.dumps(rec))


def use_queue(cfg):
    """Phase 1 goes through the render queue: opted in by config, module importable,
    and the queue installed on this machine."""
    try:
        return bool(cfg.get("use_render_queue")) and jobqueue is not None and jobqueue.enabled()
    except Exception:
        return False


def worker_alive(lk):
    """Is the worker this publish_lock names still in flight? A lock written for a
    queued render carries a job id and is alive while that job is queued or running."""
    if not lk:
        return False
    if lk.get("job") and jobqueue is not None:
        try:
            return jobqueue.job_active(lk["job"])
        except Exception:
            return False
    return pid_alive(lk.get("pid"))


def worker_name(lk):
    return f"render job {lk['job']}" if (lk or {}).get("job") else f"worker pid {(lk or {}).get('pid')}"


def render_done(proj):
    """A finished render OF THE CURRENT RECORDING.

    Existence alone was the test until 2026-10-01, and nothing ever deleted the
    sentinel. So when a publish was blocked or crash-looping and the operator
    re-recorded a card, the new record_done.json made the booth report DONE again, this
    still answered True, and phase 1 was skipped: the watcher would have published the
    render with the OLD audio the moment the block lifted, with no scriptguard in the
    way (that check only runs on the phase-1 branch). A sentinel older than the
    recording it claims to cover is not a render of that recording. The studio branch
    has made the same comparison since 2026-09-13 (studio_rendered)."""
    w = Path(proj) / "work"
    try:
        rendered = (w / "render_complete.json").stat().st_mtime
    except OSError:
        return False
    try:
        return rendered >= (w / "record_done.json").stat().st_mtime
    except OSError:
        return True                  # no Finish marker on disk: nothing to compare against


def attempts_path(proj, kind="render"):
    return Path(proj) / "work" / f"{kind}_attempts.json"


def read_attempts(proj, kind="render"):
    try:
        return json.loads(attempts_path(proj, kind).read_text())
    except (OSError, ValueError):
        return {}


def clear_attempts(proj, kind="render"):
    try:
        attempts_path(proj, kind).unlink()
    except OSError:
        pass


def bump_attempts(proj, kind="render"):
    """Record one more launch of `kind`'s worker. Both phases count separately."""
    att = read_attempts(proj, kind)
    attempts_path(proj, kind).write_text(
        json.dumps({"count": att.get("count", 0) + 1, "ts": time.time()}))


def crashlooping(proj, kind):
    """True if `kind` has burned CRASHLOOP_AFTER launches with no completion
    artifact and is still inside the backoff window. Returns (bool, count)."""
    att = read_attempts(proj, kind)
    n = att.get("count", 0)
    return (n >= CRASHLOOP_AFTER
            and time.time() - att.get("ts", 0) < CRASHLOOP_RETRY_SECS), n


def render_blocked(proj):
    """Phase 1 has died at the SAME verb with the SAME exit code RENDER_BLOCK_AFTER
    launches running. Returns (blocked, fingerprint, reason).

    The crashloop guard below throttles but never gives up, which is correct for a
    flaky render and wrong for a broken one. FWF 2026-08-31 hit a `stills` step asking
    for an aspect the renderer no longer produces: unfixable without a human, identical
    every time, and re-rendering the whole video before failing. It burned 31 launches
    and ~2 hours of compute across 26 hours while the episode sat unpublished, and the
    only trace was a log line nobody was reading. A repeated identical failure is a
    verdict, not a retry candidate — so write BLOCKED.md and stop.

    Three ways back, so a block can never become permanent. A completed render deletes
    render_failure.json; a run that fails somewhere new resets the streak; and every
    RENDER_BLOCK_PROBE_SECS one launch is let through regardless, because a fix landing
    in the renderer or a SKILL leaves no trace here and a block that only a human could
    lift would outlive its own cause. Deleting work/render_failure.json forces the probe
    immediately, which is what BLOCKED.md tells the reader to do."""
    f = Path(proj) / "work" / "render_failure.json"
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError):
        return False, "", ""
    streak = d.get("streak", 0)
    need = RENDER_BLOCK_AFTER_AUDIO if d.get("stage") in AUDIO_STAGES else RENDER_BLOCK_AFTER
    if streak < need:
        return False, "", ""
    if time.time() - d.get("ts", 0) >= RENDER_BLOCK_PROBE_SECS:
        return False, "", ""            # probe window: let one launch re-test it
    where = f"{d.get('verb', '?')} exited {d.get('rc', '?')}"
    if d.get("stage"):
        where += f" at {d['stage']}"
    why = f"{where} on {streak} consecutive phase-1 launches"
    if d.get("detail"):
        why += f": {d['detail']}"
    return True, d.get("fp", ""), why


def failure_stage(proj):
    """(stage, detail) of the last phase-1 failure, when the driver could name them."""
    try:
        d = json.loads((Path(proj) / "work" / "render_failure.json").read_text())
    except (OSError, ValueError):
        return "", ""
    return str(d.get("stage") or ""), str(d.get("detail") or "")


def alert_operator(cfg, proj, marker, fp, text):
    """Tell the OPERATOR, by text message, about something only he can fix.

    For one situation only (operator, 2026-10-01): the pipeline is held up because he
    has to act in person, which in practice means re-recording a card. A desktop
    notification on a locked screen was the whole alert before this, and a daily episode
    sat blocked for two days without him knowing. It is NOT for permission prompts,
    renders that should be working in the background, or anything a routine or a Claude
    session can fix: those stay as notifications and log lines.

    The command is private config ("operator_alert_cmd"), because this repo is public
    and the recipient is not. Once per (marker, fingerprint), like notify_once.
    Returns True when it fired."""
    cmd = cfg.get("operator_alert_cmd")
    f = Path(proj) / "work" / marker
    tries = 0
    try:
        prev = json.loads(f.read_text())
        if prev.get("fp") == fp:
            if prev.get("sent") or prev.get("tries", 0) >= 3:
                return False                 # delivered, or given up on after 3 cycles
            tries = prev.get("tries", 0)
    except (OSError, ValueError, AttributeError):
        pass

    def _mark(sent):
        try:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps({"fp": fp, "sent": sent, "tries": tries + 1,
                                     "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}))
        except OSError:
            pass

    if not cmd:
        log(cfg, f"OPERATOR-ALERT (no operator_alert_cmd configured): {text}")
        tries = 2                            # nothing to retry
        _mark(False)
        return False
    try:
        r = subprocess.run(list(cmd) + [text], capture_output=True, text=True, timeout=60)
        ok, err = r.returncode == 0, (r.stderr or r.stdout or "").strip()[:200]
    except Exception as e:                   # noqa: BLE001
        ok, err = False, str(e)
    _mark(ok)
    if ok:
        log(cfg, f"OPERATOR-ALERT sent: {text}")
        return True
    log(cfg, f"OPERATOR-ALERT FAILED (try {tries + 1} of 3: {err}): {text}")
    # Never let a broken text channel hide the block: fall back to the desktop.
    safe = lambda v: str(v).replace("\\", " ").replace('"', "'")
    subprocess.run(["/usr/bin/osascript", "-e",
                    f'display notification "{safe(text)[:200]}" with title "NEEDS YOU"'],
                   check=False, capture_output=True)
    return False


def alert_if_recording_fault(cfg, show, proj, fp):
    """A render blocked in a stage that reads the recording (narrate, align) is a fault
    in a take: text the operator. A block anywhere else is the pipeline's problem and
    stays a notification."""
    stage, detail = failure_stage(proj)
    if stage not in AUDIO_STAGES:
        return
    alert_operator(cfg, proj, "operator_alert_render.json", fp,
                   f"{show['id']} {Path(proj).name}: the render keeps failing at {stage}"
                   f"{' (' + detail[:140] + ')' if detail else ''}. That stage reads your "
                   f"recording, so a card most likely needs re-recording. Open the booth "
                   f"for this episode and check the takes; nothing publishes until then.")


def alert_stale_script(cfg, show, proj, why):
    """script.json no longer matches what was recorded. Only the operator can settle
    it: re-record the changed cards, or accept the takes (unstick_stale_script.py)."""
    fp = hashlib.sha256((why or "").encode()).hexdigest()[:16]
    alert_operator(cfg, proj, "operator_alert_script.json", fp,
                   f"{show['id']} {Path(proj).name}: the script changed after you "
                   f"recorded it, so it will not render. Re-record the changed card(s) "
                   f"in the booth. {(why or '')[:160]}")


def alert_if_publish_needs_operator(cfg, show, proj, fp):
    """A publish run that blocked for something only the operator can do says so in
    work/publish_block.json ("needs_operator": true, "operator_action": "...")."""
    try:
        d = json.loads((Path(proj) / "work" / "publish_block.json").read_text())
    except (OSError, ValueError):
        return
    if not d.get("needs_operator"):
        return
    action = str(d.get("operator_action") or d.get("reason") or "see BLOCKED.md")[:260]
    alert_operator(cfg, proj, "operator_alert_publish.json", fp,
                   f"{show['id']} {Path(proj).name}: publishing is held until you act. {action}")


def write_render_blocked_md(cfg, show, proj, fp, why):
    """Write BLOCKED.md for a stuck render, once per distinct failure fingerprint.

    Never clobbers a BLOCKED.md written by another guard (the script-staleness check
    or a publish-gate block): those name a different problem and a human is already
    being pointed at them. Only a BLOCKED.md this function wrote gets rewritten, and
    only when the fingerprint moves."""
    bl = Path(proj) / "BLOCKED.md"
    marker = "<!-- render-blocked -->"
    if bl.exists():
        try:
            head = bl.read_text()
        except OSError:
            return
        if marker not in head:
            return                       # someone else's block; leave it alone
        if fp and fp in head:
            return                       # already written for this exact failure
    logdir = Path(cfg["logs_dir"])
    try:                                 # newest render log for this show, for the tail
        logs = sorted(logdir.glob(f"{show['id']}_*_render.log"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        tail = "".join(logs[0].read_text(errors="replace").splitlines(True)[-25:]) \
            if logs else "(no render log found)"
        logname = logs[0].name if logs else "(none)"
    except OSError as e:
        tail, logname = f"(could not read render log: {e})", "(none)"
    try:
        bl.write_text(
            f"{marker}\n"
            f"# BLOCKED — phase 1 render is failing identically\n\n"
            f"**Show:** {show['id']}\n"
            f"**Project:** {Path(proj).name}\n"
            f"**Failure:** {why}\n"
            f"**Fingerprint:** `{fp}`\n\n"
            f"The watcher stopped relaunching phase 1 for this project. Each launch was "
            f"re-running the full render before dying at the same step, so retrying "
            f"costs compute and changes nothing. A human needs to look at it.\n\n"
            f"## Last 25 lines of `{logname}`\n\n"
            f"```\n{tail}\n```\n\n"
            f"## Recovering\n\n"
            f"Fix the cause, then either wait or force it:\n\n"
            f"- **Wait.** The watcher lets one probe launch through every "
            f"{RENDER_BLOCK_PROBE_SECS // 3600}h. If it gets through, phase 1 deletes "
            f"`work/render_failure.json`, this file goes away, and publishing resumes "
            f"with no further steps.\n"
            f"- **Force it now.** Delete `work/render_failure.json` and the next cycle "
            f"relaunches immediately. (Deleting this file alone does nothing — the "
            f"failure record is what the watcher reads.)\n\n"
            f"If the probe fails the same way again, this file comes back with a higher "
            f"streak. Nothing publishes for this project until a render completes.\n")
    except OSError as e:
        log(cfg, f"could not write {bl}: {e}")


def notify_render_blocked_once(cfg, show, proj, fp, why):
    """One macOS notification per distinct render failure, not per cycle."""
    marker = Path(proj) / "work" / "render_blocked_notified"
    try:
        if marker.exists() and marker.read_text().strip() == fp:
            return
        marker.write_text(fp)
    except OSError:
        pass  # notification still worth attempting
    subprocess.run([
        "/usr/bin/osascript", "-e",
        f'display notification "{show["id"]}: render blocked — {why[:120]}. '
        f'Nothing will publish until it is fixed." '
        f'with title "Recording watcher"',
    ], check=False)


def publish_block_file(proj):
    """Honour a work/publish_block.json written by a publish run that blocked for a
    reason `explainer2 validate` does not test. Returns (blocked, fingerprint, reason).

    Schema: {"watch": "<path relative to proj>", "was": "<that file's exact text>",
             "reason": "..."}. The block holds while `watch` still reads as `was`;
    anything that rewrites it (a re-render rewrites work/render_complete.json)
    retires the block with no human in the loop. `was` is the literal text rather
    than a digest so that a run writing this file by hand can fill it in without
    hashing anything. A missing or unreadable watch file reads as changed, so a
    half-written block fails open rather than parking the project forever."""
    f = proj / "work" / "publish_block.json"
    try:
        d = json.loads(f.read_text())
        watched = (proj / d["watch"]).read_text()
    except (OSError, ValueError, KeyError):
        return False, "", ""
    if watched != d["was"]:
        return False, "", ""             # the artifact moved; re-test the gate
    fp = hashlib.sha256(watched.encode()).hexdigest()[:16]
    return True, fp, str(d.get("reason", "publish gate (non-validate)"))[:300]


def publish_blocked(proj):
    """A prior publish run hit the Step-8 validate gate, wrote BLOCKED.md, and
    exited cleanly — no README, so the crashloop guard keeps respawning it on
    backoff forever. The verdict is deterministic: re-spawning an LLM run on an
    unchanged work/validate.json re-derives the identical block (the 2026-08-24
    MMT episode burned 14 publish runs this way). Skip the spawn until
    validate.json actually changes. Returns (blocked, fingerprint, reason).

    Not every publish gate is a validate gate. Robot Roundup's 180 s Shorts wall
    lives only in SKILL prose — `--min-length` is the only length the toolchain
    knows — so rrp-2026-09-23 blocked at 180.37 s with validate.json reading
    {"ok": true}, and this guard read that BLOCKED.md as stale. A publish run that
    blocks for a reason validate cannot see drops work/publish_block.json naming
    the artifact its verdict was read off; while that artifact is unchanged the
    verdict is unchanged, so the spawn is skipped. Re-rendering rewrites the
    artifact and the block lifts on its own — the same way back render_failure
    has, so a block can never outlive its cause."""
    bl = proj / "BLOCKED.md"
    if bl.exists():
        pb, fp, why = publish_block_file(proj)
        if pb:
            return True, fp, why
    vj = proj / "work" / "validate.json"
    if not bl.exists() or not vj.exists():
        return False, "", ""
    try:
        raw = vj.read_text()
        v = json.loads(raw)
    except (OSError, ValueError):
        return False, "", ""
    if v.get("ok"):
        return False, "", ""  # gate passes now; stale BLOCKED.md — let phase 2 run
    fp = hashlib.sha256(raw.encode()).hexdigest()[:16]
    why = "; ".join(str(i) for i in v.get("issues", []))[:300]
    return True, fp, why


def notify_publish_blocked_once(cfg, show, proj, fp, why):
    """One macOS notification per distinct validate verdict, not per cycle."""
    marker = proj / "work" / "publish_blocked_notified"
    try:
        if marker.exists() and marker.read_text().strip() == fp:
            return
        marker.write_text(fp)
    except OSError:
        pass  # notification still worth attempting
    subprocess.run([
        "/usr/bin/osascript", "-e",
        f'display notification "{show["id"]}: publish blocked at the validate gate '
        f'({why[:120]}). Fix the deck/renderer, then the watcher resumes on its own." '
        f'with title "Recording watcher"',
    ], check=False)


def log(cfg, msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line)
    lf = Path(cfg["log_file"])
    lf.parent.mkdir(parents=True, exist_ok=True)
    if lf.exists() and lf.stat().st_size > 2_000_000:  # crude rotation
        lf.rename(lf.with_suffix(".log.1"))
    with lf.open("a") as f:
        f.write(line + "\n")


def within_hours(cfg):
    now = datetime.now().strftime("%H:%M")
    return cfg["hours"]["start"] <= now <= cfg["hours"]["end"]


STUCK_MAX_DAYS = 30


def stuck(proj):
    """True if a guard has parked this project: a render_failure.json (deterministic
    render block) or a BLOCKED.md (render block, script/audio staleness, publish gate).

    Such a project must stay visible PAST the lookback window. Every block promises
    a way back — "delete render_failure.json", "a probe gets through every 6h",
    "run unstick_stale_script.py" — and every one of those needs the watcher to still
    be looking. FTT 2026-09-01 was repaired on 09-13, twelve days old; the watcher had
    stopped considering it on 09-08 (lookback 6), so the fix would never have launched
    and BLOCKED.md's recovery text was false. MMT 2026-09-07 was one morning from the
    same fate. See routine_changes/2026-09-13-mmt-meta-per-platform-dict-shape.md."""
    return ((Path(proj) / "work" / "render_failure.json").exists()
            or (Path(proj) / "BLOCKED.md").exists())


def last_activity(proj):
    """Newest mtime across work/ and its direct children (the pipeline's scratch:
    takes, alignment, render markers, failure records), or the project dir's own.

    Once a human clears a block, the markers stuck() keys on are gone, and the
    project is back to being an ordinary old directory — still unpublished, still
    outside the window, and phase 2 would never be spawned for it (FTT 2026-09-01,
    repaired 09-13 twelve days old). Recent activity is the honest signal that a
    project is in flight: a render just ran, a booth just wrote takes, a failure
    record was just rewritten. Abandoned projects go quiet and age out on their own;
    the four FWF dailies of 2026-08-14..17, recorded and never published, have not
    been touched since August and must stay out."""
    p = Path(proj)
    w = p / "work"
    try:
        ts = [p.stat().st_mtime]
        if w.is_dir():
            ts.append(w.stat().st_mtime)
            ts.extend(c.stat().st_mtime for c in w.iterdir())
        return max(ts)
    except OSError:
        return 0.0


def candidates(show):
    """Newest-first unpublished project dirs within the lookback window — plus, up to
    STUCK_MAX_DAYS old, any project that is stuck (see stuck()) or has had pipeline
    activity inside the window (see last_activity()), so a block or a recovery never
    silently outlives the window. The ceiling exists because a stuck project is
    probed with a full render every RENDER_BLOCK_PROBE_SECS; a block nobody fixes for
    a month should stop costing renders and become a human's problem via BLOCKED.md."""
    root = Path(show["outputs_dir"])
    if not root.exists():
        return []
    today = date.today()
    lookback = timedelta(days=show.get("lookback_days", 7))
    cutoff = today - lookback
    stuck_cutoff = today - timedelta(days=STUCK_MAX_DAYS)
    active_since = time.time() - lookback.total_seconds()
    out = []
    for p in root.iterdir():
        if not p.is_dir():
            continue
        m = DATE_RE.match(p.name)
        if not m:
            continue
        try:
            d = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if d > today:
            continue
        if d < cutoff:
            if d < stuck_cutoff:
                continue
            if not (stuck(p) or last_activity(p) >= active_since):
                continue
        if (p / "README.md").exists() or (p / "SKIPPED.md").exists():
            continue
        out.append((d, p))
    return [p for _, p in sorted(out, reverse=True)]


# How long the scaffold's originating sentinel suppresses the NOT_OPEN safety net.
# Authoring a booth show runs 5-10 minutes (research, humaner, deck); 45 minutes is
# the same stale window launch_booth --claim already uses, so the two agree. A run
# that dies mid-authoring costs at most one expiry plus one 5-minute cycle before
# the safety net takes over.
ORIGINATING_TTL_S = 45 * 60


# The three files a run authors before it opens a booth. All six watched shows write
# the same set (verified 2026-08-25 across ig_carousel, Monday MedTech, FTT, WSC, TTD,
# FMF outputs), and `explainer2 validate` needs all three later anyway.
AUTHORED_FILES = ("script.json", "deck.json", "meta.json")


def unauthored(proj):
    """Which of AUTHORED_FILES are missing — empty tuple means the project is bookable.

    Second half of the 2026-08-25 fix, and the one that covers the crash case the
    originating sentinel cannot: once the sentinel's 45 minutes expire, a project
    abandoned mid-authoring looks exactly like a healthy one whose routine forgot to
    open the booth. The safety net would then open a booth on a stub or half-written
    script.json and ask Dave to record it. Requiring the full authored set means the
    net only ever fires on work a run actually finished.
    Origin: make_money/routine_changes/2026-08-25-booth-originating-sentinel.md"""
    return tuple(f for f in AUTHORED_FILES if not (proj / f).exists())


def originating_hold(proj):
    """(still_authoring, age_seconds) for a project's work/originating.json.

    `explainer2 scaffold` writes the sentinel and tools/launch_booth.py clears it the
    moment the booth is opened for real, so its presence means a live run owns the
    project and has NOT reached its booth step yet. Opening a booth underneath that
    run gives the operator a second Chrome tab and, worse, a booth built from a
    half-authored script.json (FTT 2026-08-25, MMT 2026-08-24, and four earlier
    shows). Expire it so a crashed run cannot disable the safety net for good.
    Origin: make_money/routine_changes/2026-08-25-booth-originating-sentinel.md"""
    f = proj / "work" / "originating.json"
    try:
        age = time.time() - f.stat().st_mtime
    except OSError:
        return False, 0            # no sentinel: nothing owns this project
    return age < ORIGINATING_TTL_S, int(age)


# How often a still-alive booth also gets a line in watcher.log. The heartbeat FILE
# is rewritten on every poll — that is what bounds a death to one cycle — but a booth
# waiting all day would otherwise push everything else out of a log that rotates at
# 2 MB, so the human-readable line is throttled to hourly.
HEARTBEAT_LOG_EVERY_S = 60 * 60


def beat_booth(proj):
    """Record that this project's booth answered PENDING on this poll.

    Returns True when the caller should ALSO write a line to watcher.log: the first
    sighting, or HEARTBEAT_LOG_EVERY_S since the last logged one.

    The file is forensic rather than operational. When a booth later dies,
    last_alive() names the last poll that saw it, which bounds the death to one
    cycle. Before this existed, diagnosing the 2026-09-02 FWF disappearance meant
    inferring the window from which log lines were ABSENT — the booth was known
    alive at 09:44 only because runningboardd happened to mention its pid, and the
    upper bound came from the watcher NOT having logged a relaunch at 09:57.
    Origin: make_money/routine_changes/2026-09-02-booth-death-forensics.md"""
    f = proj / "work" / "booth_heartbeat.json"
    now = time.time()
    prev = {}
    try:
        prev = json.loads(f.read_text())
    except Exception:
        pass                      # no prior beat, or a truncated write: treat as first
    say = (now - float(prev.get("last_logged") or 0)) >= HEARTBEAT_LOG_EVERY_S
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({
            "state": "PENDING",
            "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "epoch": now,
            "last_logged": now if say else (prev.get("last_logged") or now),
        }))
    except OSError:
        return False              # a heartbeat is diagnostics; never break the cycle
    return say


def last_alive(proj):
    """'HH:MM:SS (Nm Ns ago)' for the last poll that saw this booth, or None."""
    try:
        hb = json.loads((proj / "work" / "booth_heartbeat.json").read_text())
        age = int(time.time() - float(hb["epoch"]))
    except Exception:
        return None
    return f"{hb.get('at')} ({age // 60}m{age % 60:02d}s ago)"


def exit_reason(proj):
    """The booth's own account of why it exited, when recorder.py could stamp one.

    Absent for SIGKILL and for a hard machine stop, which is exactly why last_alive()
    exists alongside it: the two together distinguish 'died and said why' from 'was
    killed outright', and that distinction is the whole diagnosis."""
    try:
        e = json.loads((proj / "work" / "booth_exit.json").read_text())
    except Exception:
        return None
    return f"{e.get('reason')} at {e.get('at')}"


def booth(cfg, verb, proj):
    """Run launch_booth.py <verb-ish>; returns (first_token, full_output)."""
    cmd = [cfg["python"], cfg["launch_booth"]] + verb + [str(proj)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, OSError) as e:
        # Uncaught until 2026-10-01: one hung --status on 2026-09-30 raised out of the
        # whole cycle and every show after it in the config was skipped.
        return "ERROR", f"launch_booth {' '.join(verb) or '(launch)'} did not answer: {e}"
    out = (r.stdout or "").strip()
    return out.split()[0] if out else "", out


def completion_prompt(show, proj):
    return (
        f"You are the {show['id']} recording-PUBLISH run, spawned by the zero-token "
        f"recording watcher (com.brg.recording-watcher). The watcher has ALREADY "
        f"verified the booth reports DONE, has "
        f"ALREADY rendered the video deterministically (media + stills + handoff + "
        f"validate + frame_qc all completed — see work/render_complete.json and the "
        f"rendered files under video/, stills/, handoff.json, manifest.json), and this "
        f"run HOLDS the atomic publish claim (work/publish_lock.json) — do NOT run "
        f"--claim again; proceed directly.\n\n"
        f"Project directory: {proj}\n\n"
        f"Read {show['skill']} in full, then execute ONLY the PUBLISH portion of its "
        f"completion path — {show['completion_steps']} — starting AFTER render/gate.\n\n"
        f"RENDERING IS NOT YOUR JOB. The render is done and the watcher owns it. Never "
        f"run a render, encode, still or Shorts command in this run: not `explainer2 "
        f"media`, `render`, `stills`, `shorts`, `handoff` or `validate`, not "
        f"`mark_stills.py`, not `npx remotion`, not `ffmpeg`. Every render on this "
        f"machine goes through the render queue, and a publish run has nothing to "
        f"submit to it. If an output is missing or the gate failed, that is a BLOCK "
        f"(below), not something to re-render around.\n\n"
        f"Read the ALREADY-generated manifest.json/handoff.json for durations, "
        f"captions, and the length gate, then do the rest: any deck build/push the "
        f"SKILL specifies, ENQUEUE to the local post queue (build_publish_payloads.py "
        f"--emit-queue-spec, then postq.py enqueue --spec; never blotato_create_post, "
        f"no slots, no scheduledTime — see make_money/post_queue/ENQUEUE.md), and "
        f"write README + uploads.json + ledger append. Never re-source, re-scaffold, or "
        f"re-author script.json/meta.json. If a step fails, stop and leave the error "
        f"visible; do not switch toolchains to route around it.\n\n"
        f"IF YOU MUST BLOCK: write BLOCKED.md saying exactly what is wrong, and write "
        f"work/publish_block.json as "
        f'{{"watch": "work/render_complete.json", "was": "<the exact current text of '
        f'that file>", "reason": "<one line>"}} so the watcher stops respawning this '
        f"run until a new render replaces that file. Then decide who can clear it:\n"
        f"- ONLY DAVE, IN PERSON (a card must be re-recorded: a clipped, missing or "
        f"wrong take, or a script that runs over a hard length limit and needs a cut "
        f"he has to re-voice): also add "
        f'"needs_operator": true and "operator_action": "<what he must do, with booth '
        f'card numbers>" to publish_block.json. The watcher texts him. Use this for '
        f"nothing else.\n"
        f"- A DECK-ONLY DEFECT (a slide authored with the wrong field names, a slide "
        f"that would render empty, a layout slip) where script.json and the recording "
        f"are fine: fix deck.json, then run "
        f"`{Path(__file__).resolve().parent / 'rerender.py'} {proj} --reason \"<what "
        f"you fixed>\"` ONCE and stop. That hands the project back to the watcher, "
        f"which re-renders through the queue, re-runs the gates and starts a fresh "
        f"publish run. Do not write BLOCKED.md in that case, and never edit "
        f"script.json: the audio is already recorded against it."
    )


def render_env(cfg):
    """launchd's PATH carries neither Homebrew nor /usr/local; ffmpeg and npx need both."""
    env = dict(os.environ)
    prepend = cfg.get("render_path_prepend")
    if prepend:
        env["PATH"] = prepend + ":" + env.get("PATH", "")
    return env


def script_guard_ok(cfg, proj):
    """`explainer2 media --recheck`: does the recorded audio still match script.json?

    Cheap (no stages run). Returns (ok, message). This is the same guard Phase 1
    enforces in-process — checking it here keeps a blocked project from burning a
    Phase-1 launch every cycle and tripping the crashloop backoff, and lets a
    resolved block clear itself (--recheck deletes BLOCKED.md when it passes)."""
    try:
        r = subprocess.run([cfg["explainer_bin"], "media", str(proj), "--recheck"],
                           capture_output=True, text=True, timeout=180,
                           env=render_env(cfg), cwd=cfg["claude_cwd"])
    except Exception as e:
        return True, f"guard check failed to run ({e}) — Phase 1 will check in-process"
    if r.returncode == 0:
        return True, ""
    out = (r.stdout or r.stderr or "").strip()
    # the guard prints its own log lines before the JSON verdict; report the reason only
    i = out.find("{")
    if i >= 0:
        try:
            return False, json.loads(out[i:]).get("reason", "")[:400]
        except ValueError:
            pass
    return False, out.replace("\n", " ")[:400]


def launch_render(cfg, show, proj):
    """Phase 1: run the long deterministic render as a DETACHED OS process (no Bash
    time cap), writing work/render_complete.json on success. Returns the pid, or None
    on dry-run.

    Driven by tools/phase1_render.py rather than a `/bin/sh -c 'A && B'` one-liner:
    the shell reaped only itself when killed, leaving the remotion/chrome tree
    rendering as orphans (2026-08-10). The driver traps termination and kills the
    render's process group."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logdir = Path(cfg["logs_dir"]); logdir.mkdir(parents=True, exist_ok=True)
    render_log = logdir / f"{show['id']}_{stamp}_render.log"
    driver = cfg.get("phase1_driver") or str(
        Path(cfg["launch_booth"]).parent / "phase1_render.py")
    argv = [cfg["python"], driver, str(proj), "--explainer", cfg["explainer_bin"]]
    studio = show.get("mode") == "studio"
    if studio:
        argv += ["--profile", "studio"]
    # The render queue: one ordered queue for the watcher, the routines and every
    # session, run by its own launchd agent. A recorded booth-show episode outranks a
    # long studio render, so a six-minute daily no longer waits two hours behind one
    # (2026-10-01). Any failure to submit falls back to launching it here.
    if use_queue(cfg):
        try:
            job, created = jobqueue.submit(
                "phase1", argv, project=str(proj), label=f"{show['id']}:{Path(proj).name}",
                priority=show.get("render_priority",
                                  jobqueue.PRI_STUDIO if studio else jobqueue.PRI_SHOW),
                cwd=cfg["claude_cwd"], log_path=str(render_log))
            write_lock(proj, None, job=job["id"])
            if created:
                bump_attempts(proj, "render")
            log(cfg, f"RENDER (phase 1) {'queued' if created else 'already queued'} for "
                     f"{show['id']}: {proj} (job {job['id']}, log {render_log})")
            return job["id"]
        except Exception as e:                       # noqa: BLE001
            log(cfg, f"QUEUE-SUBMIT failed for {show['id']} ({type(e).__name__}: {e}); "
                     f"launching phase 1 directly")
    child = subprocess.Popen(
        ["/usr/bin/caffeinate", "-ims"] + argv, cwd=cfg["claude_cwd"], env=render_env(cfg),
        start_new_session=True, stdout=render_log.open("w"), stderr=subprocess.STDOUT)
    write_lock(proj, child.pid)  # hold the claim for the render's lifetime
    bump_attempts(proj, "render")
    log(cfg, f"RENDER (phase 1) launched for {show['id']}: {proj} "
             f"(pid {child.pid}, log {render_log})")
    return child.pid


def spawn_completion(cfg, show, proj, dry):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logdir = Path(cfg["logs_dir"]); logdir.mkdir(parents=True, exist_ok=True)
    prompt_file = logdir / f"{show['id']}_{stamp}_prompt.txt"
    out_file = logdir / f"{show['id']}_{stamp}_completion.log"
    prompt_file.write_text(completion_prompt(show, proj))
    cmd = ["/usr/bin/caffeinate", "-ims", cfg["claude_bin"], "-p", prompt_file.read_text(),
           "--output-format", "text"]
    if dry:
        log(cfg, f"[DRY-RUN] would spawn PUBLISH for {show['id']}: {proj} "
                 f"(log -> {out_file})")
        return None
    child = subprocess.Popen(
        cmd, cwd=cfg["claude_cwd"], start_new_session=True,
        stdout=out_file.open("w"), stderr=subprocess.STDOUT)
    # Re-stamp the publish lock with the publish worker's pid so a later cycle
    # sees the live publisher (pid_alive) and backs off until the README lands.
    try:
        write_lock(proj, child.pid)
    except OSError as e:
        log(cfg, f"WARNING: could not re-stamp publish lock for {proj}: {e}")
    bump_attempts(proj, "publish")
    log(cfg, f"PUBLISH (phase 2) spawned for {show['id']}: {proj} (pid {child.pid}, "
             f"log {out_file})")
    return child.pid


def notify_once(proj, marker, fp, title, text):
    """One macOS notification per distinct (marker, fingerprint), not per cycle.
    Returns True when it fired. The marker lives in work/ so it travels with the
    project and is cleared naturally when the situation changes (new fingerprint)."""
    f = Path(proj) / "work" / marker
    try:
        if f.exists() and f.read_text().strip() == fp:
            return False
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(fp)
    except OSError:
        pass
    safe = lambda v: str(v).replace("\\", " ").replace('"', "'")
    subprocess.run(["/usr/bin/osascript", "-e",
                    f'display notification "{safe(text)[:200]}" with title "{safe(title)}"'],
                   check=False, capture_output=True)
    return True


def log_skip(cfg, proj, key, msg, every=HEARTBEAT_LOG_EVERY_S):
    """Log a skip decision for a DONE studio project without flooding the log.

    A new decision (a different `key`) is logged at once; the same decision again at
    most every `every` seconds, or never again when `every` is None. Before 2026-09-30
    two studio skips were silent, and #70 sat unrendered for two hours with nothing in
    watcher.log to say the watcher had even looked at it. The marker lives in work/
    beside notify_once's, so it travels with the project."""
    f = Path(proj) / "work" / "watcher_skip.json"
    now = time.time()
    try:
        prev = json.loads(f.read_text())
    except Exception:
        prev = {}
    if prev.get("key") == key and (
            every is None or now - float(prev.get("at") or 0) < every):
        return
    log(cfg, msg)
    try:
        f.write_text(json.dumps({"key": key, "at": now}))
    except OSError:
        pass                     # the log line is written; the throttle is a nicety


def studio_candidates(show):
    """Studio project dirs with a Finish sentinel inside the lookback, newest Finish
    first. A project is a dir with project.json + script.json; SKIPPED.md opts out.
    Dates come from the sentinel's mtime, not the dir name: masterclass episodes are
    named module-NN and have no date to parse."""
    import glob as _glob
    cutoff = time.time() - show.get("lookback_days", 3) * 86400
    out = []
    for pattern in show.get("project_globs", []):
        for d in _glob.glob(pattern):
            p = Path(d)
            if not (p.is_dir() and (p / "project.json").exists()
                    and (p / "script.json").exists()):
                continue
            if (p / "SKIPPED.md").exists():
                continue
            done = p / "work" / "record_done.json"
            try:
                m = done.stat().st_mtime
            except OSError:
                continue
            if m >= cutoff:
                out.append((m, p))
    return [p for _, p in sorted(out, reverse=True)]


def studio_rendered(proj):
    """Somebody already rendered THIS recording — skip it.

    Not just the driver's own render_complete.json: a session that renders by hand
    (`media --only narrate,align` then `render`) never writes that sentinel, and on the
    first live cycle (2026-09-13 13:14) the watcher queued Product Leadership module-05
    for a second full render two days after its session had produced video/ and a
    manifest. So any media output newer than record_done.json counts: work/results.json
    (every `media` run ends by writing it), the root manifest.json, or a rendered mp4
    under video/. A re-record after a render produces a newer record_done.json, so the
    project comes back for another Phase 1 — right, because the timeline changed.

    Only artifacts written AFTER a render finished count (2026-09-30). A bare mp4 under
    video/ used to count too, but the encoder writes that file while it renders, so a
    render killed partway leaves a partial mp4 newer than record_done.json. #70
    claude-nine-loops was stopped with kill_render.py at 14:20 to fix deck.json; the
    partial mp4 read as "rendered", the project was skipped without a log line for two
    hours, and module-07 took the render slot at 15:42. results.json counts only when
    its media run got through `render` (`media --only narrate,align` writes one too).

    Returns a short description of the evidence (truthy), or "" if there is none."""
    try:
        done = (proj / "work" / "record_done.json").stat().st_mtime
    except OSError:
        return ""
    for f in (proj / "work" / "render_complete.json", proj / "manifest.json",
              proj / "work" / "results.json"):
        try:
            m = f.stat().st_mtime
            if m < done:
                continue
            if f.name == "results.json" and "render" not in json.loads(f.read_text()):
                continue
        except (OSError, ValueError, AttributeError, TypeError):
            continue
        return (f"{f.relative_to(proj)} "
                f"({datetime.fromtimestamp(m).strftime('%Y-%m-%d %H:%M:%S')})")
    return ""


def run_studio(cfg, show, dry, spawned):
    """One cycle of the studio branch. Returns the updated `spawned` flag.

    Mirrors the shows' DONE path minus everything that assumes an unattended routine:
    no PENDING heartbeat, no NOT_OPEN relaunch (the session owns the booth), no phase-2
    Claude spawn (the operator resumes the session; RESUME.md is the handoff)."""
    for proj in studio_candidates(show):
        evidence = studio_rendered(proj)
        if evidence:                                     # done for this recording
            log_skip(cfg, proj, f"rendered:{evidence}",
                     f"STUDIO-RENDERED {show['id']}: {proj.name} — {evidence} is newer "
                     f"than work/record_done.json; not rendering again", every=None)
            continue
        lk = read_lock(proj)
        if worker_alive(lk):                             # our own render, in flight
            log_skip(cfg, proj, f"worker:{lk.get('job') or lk.get('pid')}",
                     f"{show['id']}: {proj.name} DONE, {worker_name(lk)} "
                     f"still active — backing off")
            continue
        try:
            pj = json.loads((proj / "project.json").read_text())
        except Exception:
            pj = {}
        # voice_source guard. scaffold defaults to kokoro; if nobody flipped it, `media`
        # would synthesize TTS over the operator's real takes (memory: caught on #37).
        # An unattended render is exactly where nobody would notice.
        if pj.get("voice_source") != "operator":
            fp = f"voice_source:{pj.get('voice_source')}"
            if notify_once(proj, "studio_voice_notified", fp, "Recording watcher",
                           f"{proj.name}: recorded, but project.json voice_source is "
                           f"'{pj.get('voice_source')}', not operator — NOT rendering."):
                log(cfg, f"STUDIO-VOICE {show['id']}: {proj.name} DONE but voice_source="
                         f"{pj.get('voice_source')!r}; not rendering over real takes")
            continue
        # deck.json is what the remotion engine renders. The SKILL puts the deck before
        # the booth, but the operator may record first and the session author the deck
        # after (#67, 2026-09-13: the first live studio cycle ran narrate + align for
        # three minutes and then died at render on the missing file, and would have
        # retried every cycle). Wait for the deck; say so once.
        if not (proj / "deck.json").exists():
            if notify_once(proj, "studio_deck_notified", "no-deck", "Recording watcher",
                           f"{proj.name}: recording finished, but there is no deck.json "
                           f"yet — the render starts as soon as the deck is authored."):
                log(cfg, f"STUDIO-NODECK {show['id']}: {proj.name} DONE but no deck.json; "
                         f"waiting for the session to author the deck")
            continue
        # adlib re-record flags: the booth's live drift check said a card needs the mic
        # again. The session used to judge these after the waiter fired; unattended,
        # the safe call is to hold the render and say so once.
        try:
            adlib = json.loads((proj / "work" / "adlib_report.json").read_text())
        except Exception:
            adlib = {}
        flagged = adlib.get("rerecord") or []
        if flagged:
            cards = ", ".join(str(int(i) + 1) for i in flagged)     # booth card numbers
            fp = f"rerecord:{cards}"
            if notify_once(proj, "studio_rerecord_notified", fp, "Recording watcher",
                           f"{proj.name}: booth flagged card(s) {cards} for re-record — "
                           f"render on hold until they are re-recorded or accepted."):
                log(cfg, f"STUDIO-RERECORD {show['id']}: {proj.name} cards {cards} "
                         f"flagged; not rendering (relaunch the booth, or render by hand)")
            if not dry:
                alert_operator(cfg, proj, "operator_alert_rerecord.json", fp,
                               f"{proj.name}: the booth flagged card(s) {cards} for "
                               f"re-record. The render is on hold until you re-record "
                               f"them or accept the takes.")
            continue
        if spawned:
            log(cfg, f"{show['id']}: {proj.name} DONE but work was already started "
                     f"this cycle — next cycle picks it up")
            return spawned
        rblocked, rfp, rwhy = render_blocked(proj)
        if rblocked:
            log(cfg, f"RENDER-BLOCKED {show['id']}: {proj.name} — {rwhy}; NOT relaunching "
                     f"phase 1 (see {proj / 'BLOCKED.md'})")
            if not dry:
                write_render_blocked_md(cfg, show, proj, rfp, rwhy)
                notify_render_blocked_once(cfg, show, proj, rfp, rwhy)
                alert_if_recording_fault(cfg, show, proj, rfp)
            continue
        ok, why = script_guard_ok(cfg, proj)
        if not ok:
            log(cfg, f"BLOCKED {show['id']}: {proj.name} — script.json changed after "
                     f"recording; NOT rendering. {why} (see {proj / 'BLOCKED.md'})")
            if not dry:
                alert_stale_script(cfg, show, proj, why)
            continue
        looping, n = crashlooping(proj, "render")
        if looping:
            log(cfg, f"RENDER-CRASHLOOP {show['id']}: {proj.name} phase-1 launched {n}x "
                     f"with no render_complete.json — retrying after backoff")
            continue
        # With the queue, order and concurrency belong to the queue: a submitted job
        # waits its turn as a small JSON file, not as a resident process, so there is
        # nothing for a cap to protect.
        cap = cfg.get("max_concurrent_renders", DEFAULT_MAX_CONCURRENT_RENDERS)
        running = 0 if use_queue(cfg) else live_renders(cfg)
        if running >= cap:
            log(cfg, f"RENDER-CAP {show['id']}: {proj.name} ready to render but {running} "
                     f"render(s) already running (cap {cap}) — deferring to a later cycle")
            continue
        if dry:
            log(cfg, f"[DRY-RUN] {show['id']}: {proj.name} DONE, no render yet — would "
                     f"launch RENDER (phase 1, studio profile)")
        else:
            if lk:          # a render was started here before and did not finish
                log(cfg, f"STUDIO-RELAUNCH {show['id']}: {proj.name} — earlier phase-1 "
                         f"worker pid {lk.get('pid')} is gone and left no completed "
                         f"render for this recording; relaunching")
            launch_render(cfg, show, proj)
        spawned = True
    return spawned


def run_show(cfg, show, dry, spawned):
    """One cycle for one booth show. Returns the updated `spawned` flag."""
    for proj in candidates(show):
        state, full = booth(cfg, ["--status"], proj)
        if state == "PENDING":
            # Booth is up and waiting. Stamp the heartbeat every poll so a later
            # death is bounded to one cycle; log hourly so the trail is readable.
            if beat_booth(proj):
                log(cfg, f"{show['id']}: booth alive for {proj.name} "
                         f"(waiting for the operator)")
            break  # operator mid-recording; nothing to do for this show
        if state == "DONE":
            if spawned:
                log(cfg, f"{show['id']}: {proj.name} DONE but work was already "
                         f"started this cycle — next cycle picks it up")
                break
            # Mutual exclusion: the publish_lock pid is the live render (phase 1)
            # or publish (phase 2) worker. Single-instance flock (main) means no
            # concurrent watcher cycle, so a simple liveness check is sufficient
            # and avoids launch_booth --claim's slow 45-min stale rule between the
            # two phases.
            lk = read_lock(proj)
            if worker_alive(lk):
                log(cfg, f"{show['id']}: {proj.name} DONE, {worker_name(lk)} "
                         f"still active — backing off")
                break
            if render_done(proj):
                clear_attempts(proj, "render")  # render completed; counter is stale
                # Phase 2: render finished; publish. Guard against re-posting if a
                # prior publish got partway (uploads.json written, README not yet).
                if (proj / "uploads.json").exists():
                    log(cfg, f"{show['id']}: {proj.name} render done + uploads.json "
                             f"present but no README — prior publish partial; NOT "
                             f"auto-retrying (double-post risk), needs review")
                    break
                # Deterministic validate-gate block: a completed publish run left
                # BLOCKED.md and validate.json still fails identically. No LLM
                # spawn will change the verdict — skip (zero cost) until the
                # fingerprint moves, and tell Dave once per distinct block.
                blocked, fp, why = publish_blocked(proj)
                if blocked:
                    log(cfg, f"PUBLISH-BLOCKED {show['id']}: {proj.name} — validate "
                             f"gate failing unchanged ({fp}); NOT spawning phase 2. "
                             f"{why} (see {proj / 'BLOCKED.md'})")
                    notify_publish_blocked_once(cfg, show, proj, fp, why)
                    if not dry:
                        alert_if_publish_needs_operator(cfg, show, proj, fp)
                    continue
                # ...and against a publish that dies before writing anything at
                # all (expired OAuth, missing bin), which the uploads.json check
                # above cannot see. `continue`, not `break`, so the doomed project
                # yields this cycle's slot instead of starving every other show.
                looping, n = crashlooping(proj, "publish")
                if looping:
                    log(cfg, f"PUBLISH-CRASHLOOP {show['id']}: {proj.name} phase-2 "
                             f"spawned {n}x with no README — skipping so other shows "
                             f"get this cycle's slot; retrying after backoff. Check "
                             f"the newest {show['id']}_*_completion.log for the cause")
                    continue
                if dry:
                    log(cfg, f"[DRY-RUN] {show['id']}: {proj.name} render done — "
                             f"would spawn PUBLISH (phase 2)")
                else:
                    spawn_completion(cfg, show, proj, dry)
                spawned = True
            else:
                # Phase 1: no render yet (or a prior render died before completing);
                # launch the detached render. launch_render writes the lock.
                #
                # First: does the audio still match script.json? An edit landing
                # between the last take and Phase 1 aligns the new text onto the old
                # audio SILENTLY and publishes it (2026-08-10). Blocked projects need
                # a human at the booth, so don't spend the cycle's slot on them.
                # Deterministic render block: phase 1 has died at the same verb
                # with the same exit code RENDER_BLOCK_AFTER launches running.
                # Retrying re-renders the whole video to reach an identical
                # failure, so stop and put a human on it.
                #
                # Checked BEFORE the script guard on purpose. script_guard_ok runs
                # `media --recheck`, whose scriptguard.clear_blocked() unlinks
                # BLOCKED.md unconditionally when the audio and script.json agree —
                # it cannot tell its own block from anyone else's. Running it first
                # would delete this block every cycle and we would rewrite it every
                # cycle. Skipping it here also saves a subprocess on a project that
                # is going nowhere until a human intervenes.
                rblocked, rfp, rwhy = render_blocked(proj)
                if rblocked:
                    log(cfg, f"RENDER-BLOCKED {show['id']}: {proj.name} — {rwhy}; "
                             f"NOT relaunching phase 1 (see {proj / 'BLOCKED.md'})")
                    if not dry:
                        write_render_blocked_md(cfg, show, proj, rfp, rwhy)
                        notify_render_blocked_once(cfg, show, proj, rfp, rwhy)
                        alert_if_recording_fault(cfg, show, proj, rfp)
                    continue
                ok, why = script_guard_ok(cfg, proj)
                if not ok:
                    log(cfg, f"BLOCKED {show['id']}: {proj.name} — script.json changed "
                             f"after recording; NOT rendering. {why} "
                             f"(see {proj / 'BLOCKED.md'}; recover with "
                             f"tools/unstick_stale_script.py)")
                    if not dry:
                        alert_stale_script(cfg, show, proj, why)
                    break
                looping, n = crashlooping(proj, "render")
                if looping:
                    log(cfg, f"RENDER-CRASHLOOP {show['id']}: {proj.name} phase-1 "
                             f"launched {n}x with no render_complete.json "
                             f"— skipping so other shows get this cycle's slot; "
                             f"retrying after backoff")
                    continue
                # Global concurrency cap. Unlike the per-project publish_lock
                # this counts renders across ALL shows, so a slow render does
                # not accumulate company while it works. `continue` rather than
                # `break`: a cheap phase-2 publish on another project may still
                # use this cycle, and `spawned` stays False so nothing is lost.
                cap = cfg.get("max_concurrent_renders",
                              DEFAULT_MAX_CONCURRENT_RENDERS)
                running = 0 if use_queue(cfg) else live_renders(cfg)   # see run_studio
                if running >= cap:
                    log(cfg, f"RENDER-CAP {show['id']}: {proj.name} ready to render "
                             f"but {running} render(s) already running (cap {cap}) "
                             f"— deferring to a later cycle")
                    continue
                if dry:
                    log(cfg, f"[DRY-RUN] {show['id']}: {proj.name} DONE, no render "
                             f"yet — would launch RENDER (phase 1)")
                else:
                    launch_render(cfg, show, proj)
                spawned = True
            break
        if state == "NOT_OPEN":
            today = date.today().isoformat()
            if proj.name.startswith(today):
                held, age = originating_hold(proj)
                missing = unauthored(proj)
                if held:
                    log(cfg, f"{show['id']}: {proj.name} NOT_OPEN but a run is still "
                             f"authoring it (originating.json, {age // 60}m old) "
                             f"— leaving the booth to the routine")
                elif missing:
                    log(cfg, f"NOT-READY {show['id']}: {proj.name} NOT_OPEN, no "
                             f"originating hold, but missing {', '.join(missing)} "
                             f"— a booth here would ask Dave to read a half-authored "
                             f"script, so none was opened. A run died mid-author; "
                             f"finish or delete the project.")
                elif dry:
                    log(cfg, f"[DRY-RUN] would relaunch booth for {show['id']}: {proj}")
                else:
                    booth(cfg, [], proj)  # full launcher: detached booth + Chrome tab pop
                    # Say what is known about the death in the same line as the
                    # relaunch. Before 2026-09-02 this line was the ONLY record
                    # that a booth had died, and it carried neither when nor why.
                    seen, why = last_alive(proj), exit_reason(proj)
                    detail = "".join([
                        f"; last seen alive {seen}" if seen else
                        "; no heartbeat on file (booth predates this build,"
                        " or died before its first poll)",
                        f"; booth reported {why}" if why else
                        "; booth stamped no exit (SIGKILL or a hard stop)",
                    ])
                    log(cfg, f"{show['id']}: booth was NOT_OPEN for today's "
                             f"{proj.name} — relaunched (takes persist){detail}")
                    # The beat just reported belongs to the booth that died. Drop
                    # it so a second death cannot be dated from the first booth's
                    # heartbeat; the new booth writes its own on the next poll.
                    (proj / "work" / "booth_heartbeat.json").unlink(missing_ok=True)
            break
        log(cfg, f"{show['id']}: unexpected booth status '{full}' for {proj.name}")
        break
    return spawned


def run(cfg, dry, in_hours=True):
    spawned = False
    for show in cfg["shows"]:
        if not show.get("enabled", True):
            continue
        if not in_hours and not show.get("ignore_hours"):
            continue
        # One show's trouble must not cost the others their cycle. Until 2026-10-01 a
        # single exception anywhere in this loop (a hung booth --status, an unreadable
        # project dir) ended the whole cycle, and every show listed after it was
        # starved for as long as the fault lasted.
        try:
            if show.get("mode") == "studio":
                spawned = run_studio(cfg, show, dry, spawned)
            else:
                spawned = run_show(cfg, show, dry, spawned)
        except Exception as e:                       # noqa: BLE001
            log(cfg, f"WATCHER-ERROR {show.get('id')}: {type(e).__name__}: {e} — skipped "
                     f"this show for this cycle; the others still run")
    return spawned


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-hours", action="store_true",
                    help="run even outside the configured hours window")
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    # single instance (flock auto-releases on exit/crash)
    lockf = open(cfg.get("instance_lock", "/tmp/recording-watcher.lock"), "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return  # another cycle still running (e.g. slow subprocess) — skip
    sweep_orphan_browsers(cfg, args.dry_run)   # before the hours gate, on purpose
    # The hours window is per show now: a studio entry with ignore_hours renders at
    # night; everything else still sleeps outside the window.
    run(cfg, args.dry_run, in_hours=args.force_hours or within_hours(cfg))


if __name__ == "__main__":
    main()
