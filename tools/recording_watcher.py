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
import shlex
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_")


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
        f"build/push the SKILL specifies, publish via Blotato useNextFreeSlot, and "
        f"write README + uploads.json + ledger append. Never re-source, re-scaffold, or "
        f"re-author script.json/deck.json/meta.json. If a step fails, stop and leave "
        f"the error visible; do not switch toolchains to route around it."
    )


def launch_render(cfg, show, proj):
    """Phase 1: run the long deterministic render as a DETACHED OS process (no Bash
    time cap), writing work/render_complete.json on success. Returns the pid, or None
    on dry-run. PATH gets render_path_prepend (ffmpeg lives in /opt/homebrew/bin, which
    is not on the minimal launchd PATH)."""
    exp = cfg["explainer_bin"]
    q = shlex.quote
    p = q(str(proj))
    rc = q(str(Path(proj) / "work" / "render_complete.json"))
    script = (
        f"{q(exp)} media {p} && "
        f"{q(exp)} stills {p} --aspect 4:5 && "
        f"{q(exp)} handoff {p} && "
        f"{q(exp)} validate {p} && "
        f'printf \'{{"ts": %s}}\' "$(date +%s)" > {rc}'
    )
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logdir = Path(cfg["logs_dir"]); logdir.mkdir(parents=True, exist_ok=True)
    render_log = logdir / f"{show['id']}_{stamp}_render.log"
    env = dict(os.environ)
    prepend = cfg.get("render_path_prepend")
    if prepend:
        env["PATH"] = prepend + ":" + env.get("PATH", "")
    child = subprocess.Popen(
        ["/usr/bin/caffeinate", "-ims", "/bin/sh", "-c", script],
        cwd=cfg["claude_cwd"], env=env, start_new_session=True,
        stdout=render_log.open("w"), stderr=subprocess.STDOUT)
    write_lock(proj, child.pid)  # hold the claim for the render's lifetime
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
                    # Phase 2: render finished; publish. Guard against re-posting if a
                    # prior publish got partway (uploads.json written, README not yet).
                    if (proj / "uploads.json").exists():
                        log(cfg, f"{show['id']}: {proj.name} render done + uploads.json "
                                 f"present but no README — prior publish partial; NOT "
                                 f"auto-retrying (double-post risk), needs review")
                        break
                    if dry:
                        log(cfg, f"[DRY-RUN] {show['id']}: {proj.name} render done — "
                                 f"would spawn PUBLISH (phase 2)")
                    else:
                        spawn_completion(cfg, show, proj, dry)
                    spawned = True
                else:
                    # Phase 1: no render yet (or a prior render died before completing);
                    # launch the detached render. launch_render writes the lock.
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
