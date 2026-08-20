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
    return sum(1 for line in out.splitlines()
               if driver in line and "caffeinate" not in line)


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
                if proj.name.startswith(today) and (proj / "script.json").exists():
                    if dry:
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
