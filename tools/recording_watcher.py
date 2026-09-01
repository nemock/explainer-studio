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
# Phase 1 failing at the same verb with the same rc this many launches running is a
# verdict, not a flake: stop relaunching and write BLOCKED.md. With the backoff above
# that is ~3 hours, against the 26 hours and 31 launches FWF 2026-08-31 burned.
RENDER_BLOCK_AFTER = 6
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


def write_lock(proj, pid):
    f = Path(proj) / "work" / "publish_lock.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"pid": pid, "ts": time.time()}))


def render_done(proj):
    return (Path(proj) / "work" / "render_complete.json").exists()


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
    if streak < RENDER_BLOCK_AFTER:
        return False, "", ""
    if time.time() - d.get("ts", 0) >= RENDER_BLOCK_PROBE_SECS:
        return False, "", ""            # probe window: let one launch re-test it
    return True, d.get("fp", ""), (f"{d.get('verb', '?')} exited {d.get('rc', '?')} on "
                                   f"{streak} consecutive phase-1 launches")


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


def publish_blocked(proj):
    """A prior publish run hit the Step-8 validate gate, wrote BLOCKED.md, and
    exited cleanly — no README, so the crashloop guard keeps respawning it on
    backoff forever. The verdict is deterministic: re-spawning an LLM run on an
    unchanged work/validate.json re-derives the identical block (the 2026-08-24
    MMT episode burned 14 publish runs this way). Skip the spawn until
    validate.json actually changes. Returns (blocked, fingerprint, reason)."""
    bl = proj / "BLOCKED.md"
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


def candidates(show):
    """Newest-first unpublished project dirs within the lookback window."""
    root = Path(show["outputs_dir"])
    if not root.exists():
        return []
    cutoff = date.today() - timedelta(days=show.get("lookback_days", 7))
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
        if d < cutoff or d > date.today():
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


def booth(cfg, verb, proj):
    """Run launch_booth.py <verb-ish>; returns (first_token, full_output)."""
    cmd = [cfg["python"], cfg["launch_booth"]] + verb + [str(proj)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    out = (r.stdout or "").strip()
    return out.split()[0] if out else "", out


def completion_prompt(show, proj):
    return (
        f"You are the {show['id']} recording-PUBLISH run, spawned by the zero-token "
        f"recording watcher (com.brg.recording-watcher). The watcher has ALREADY "
        f"verified the booth reports DONE, has "
        f"ALREADY rendered the video deterministically (media + stills 4:5 + handoff + "
        f"validate all completed — see work/render_complete.json and the rendered "
        f"files under video/, stills/, handoff.json, manifest.json), and this run "
        f"HOLDS the atomic publish claim (work/publish_lock.json) — do NOT run --claim "
        f"again; proceed directly.\n\n"
        f"Project directory: {proj}\n\n"
        f"Read {show['skill']} in full, then execute ONLY the PUBLISH portion of its "
        f"completion path — {show['completion_steps']} — starting AFTER render/gate. "
        f"The render is DONE: do NOT run `explainer media`, `explainer stills`, "
        f"`explainer handoff`, or `explainer validate` again (re-rendering would waste "
        f"20+ minutes and can hit the Bash time cap — that is exactly the failure this "
        f"two-phase flow fixes). Read the ALREADY-generated manifest.json/handoff.json "
        f"for durations, captions, and the length gate, then do the rest: any deck "
        f"build/push the SKILL specifies, ENQUEUE to the local post queue "
        f"(build_publish_payloads.py --emit-queue-spec, then postq.py enqueue --spec; "
        f"never blotato_create_post, no slots, no scheduledTime — see "
        f"make_money/post_queue/ENQUEUE.md), and "
        f"write README + uploads.json + ledger append. Never re-source, re-scaffold, or "
        f"re-author script.json/deck.json/meta.json. If a step fails, stop and leave "
        f"the error visible; do not switch toolchains to route around it."
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
    child = subprocess.Popen(
        ["/usr/bin/caffeinate", "-ims", cfg["python"], driver,
         str(proj), "--explainer", cfg["explainer_bin"]],
        cwd=cfg["claude_cwd"], env=render_env(cfg), start_new_session=True,
        stdout=render_log.open("w"), stderr=subprocess.STDOUT)
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


def run(cfg, dry):
    spawned = False
    for show in cfg["shows"]:
        if not show.get("enabled", True):
            continue
        for proj in candidates(show):
            state, full = booth(cfg, ["--status"], proj)
            if state == "PENDING":
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
                if lk and pid_alive(lk.get("pid")):
                    log(cfg, f"{show['id']}: {proj.name} DONE, worker pid "
                             f"{lk.get('pid')} still active — backing off")
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
                        continue
                    ok, why = script_guard_ok(cfg, proj)
                    if not ok:
                        log(cfg, f"BLOCKED {show['id']}: {proj.name} — script.json changed "
                                 f"after recording; NOT rendering. {why} "
                                 f"(see {proj / 'BLOCKED.md'}; recover with "
                                 f"tools/unstick_stale_script.py)")
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
                    running = live_renders(cfg)
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
                        log(cfg, f"{show['id']}: booth was NOT_OPEN for today's "
                                 f"{proj.name} — relaunched (takes persist)")
                break
            log(cfg, f"{show['id']}: unexpected booth status '{full}' for {proj.name}")
            break
    return spawned


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-hours", action="store_true",
                    help="run even outside the configured hours window")
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    if not args.force_hours and not within_hours(cfg):
        return
    # single instance (flock auto-releases on exit/crash)
    lockf = open(cfg.get("instance_lock", "/tmp/recording-watcher.lock"), "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return  # another cycle still running (e.g. slow subprocess) — skip
    run(cfg, args.dry_run)


if __name__ == "__main__":
    main()
