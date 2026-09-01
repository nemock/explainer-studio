#!/usr/bin/env python3
"""Phase 1 of the recording watcher: the deterministic render, as a real process
instead of a shell one-liner.

The watcher used to launch Phase 1 as

    caffeinate -ims /bin/sh -c 'explainer2 media X && explainer2 stills X && … && printf > render_complete.json'

which had two problems, both hit on 2026-08-10:

  * killing the `/bin/sh` pid reaped the shell and NOTHING else — `npm exec
    remotion render`, `node` and the whole `chrome-headless-shell` tree survived
    reparented to init and kept rendering
  * the render_complete.json sentinel was a `printf` buried in a quoted shell
    string, so the success contract lived in shell quoting

This driver runs the same four verbs in order, keeps each child in its own
process group, and traps SIGTERM/SIGINT/SIGHUP so a kill aimed at Phase 1 takes
the render down with it. It writes work/render_complete.json only when all four
verbs succeed — same contract the watcher's Phase 2 reads.

Reaping (rewritten 2026-08-20 after clearing 12 orphans resident ~3d22h). The
2026-08-10 fix assumed one escaping layer; there are three, and they compound:

    phase1_render.py            pgid A
      └─ npm exec remotion       pgid B   <- npm starts its own group
           └─ node remotion
                ├─ chrome-headless-shell  <- setpgid AGAIN, ignores SIGTERM
                └─ compositor / ffmpeg

Killing pgid A left the whole remotion tree; killing pgid B left chrome; chrome
then re-parented to init, where no ppid walk can find it. Taking one such tree
down by hand needed three separate kills. Worse, an orphan that survives does not
sit idle — 12 of them starved a later render into taking 2h15m for a job that
takes ~9 minutes, which read like a hang and was really CPU contention.

So `_reap()` snapshots descendants BEFORE signalling (the links vanish once the
parents die), then sweeps in a loop — project roots via kill_render.find(), then
any snapshot pid still breathing — until the project is quiet or the budget runs
out. It runs on EVERY exit path: trapped signal, failed verb, and clean success.
It is scoped to this project, so a concurrent render of another show is untouched;
the unattributable ppid==1 sweep stays an explicit `kill_render.py
--sweep-orphans`.

SIGKILL on the driver still cannot be trapped, and that leak is what
`kill_render.py` is for.

`explainer2 media` also refuses to run at all when the recorded audio disagrees
with script.json (scriptguard.py), in which case this exits non-zero with
BLOCKED.md written and no sentinel, so Phase 2 never publishes.

Usage: phase1_render.py --explainer <bin> <project_dir>
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from explainer2 import childproc                              # noqa: E402
import kill_render                                            # noqa: E402

_child = {"proc": None, "proj": None}

REAP_DEADLINE_S = 25.0        # total budget for the sweep loop
REAP_PASS_PAUSE_S = 0.5


def _reap(why):
    """Take down the running verb AND every remotion/chrome process this project
    still owns, sweeping until the project is quiet.

    A single kill_tree() pass is not enough, for two reasons found on 2026-08-20
    while clearing 12 orphans that had been resident for ~3d22h:

      * `npm exec` puts the render in its OWN process group, so the tree is
        pgid(driver) -> pgid(npm) -> chrome, which re-orphans at EVERY layer.
        Taking it down by hand needed three separate kills.
      * chrome-headless-shell RESPAWNS children and ignores SIGTERM. Killing a
        snapshot taken once, before any signal, misses whatever appears after it,
        and once the parent dies the survivors re-parent to init and drop out of
        any ppid walk entirely — which is precisely how they become permanent.

    So: snapshot our descendants BEFORE signalling (while the ppid links still
    exist), then loop — kill the project's roots via kill_render.find(), then any
    snapshot pid still breathing — until nothing is left or the budget runs out.

    Scoped to THIS project on purpose. Attribution is by project path, so a
    concurrent render of another show is never touched; the global ppid==1 sweep
    stays an explicit operator action in kill_render.py --sweep-orphans."""
    proj = _child["proj"]
    p = _child["proc"]
    print(f"[phase1] reaping render tree ({why})", flush=True)

    def _project_hits():
        """kill_render.find(), minus our OWN session.

        find() matches `phase1_render.py <proj>` as a render root, which is us —
        and our caffeinate wrapper carries the same argv, so an unfiltered sweep
        kills the reaper before it finishes reaping. Our session was created with
        start_new_session=True by the watcher, so everything in our own pgid is
        the driver and its wrapper; the verb children and the npm/remotion tree
        each sit in a DIFFERENT pgid and are still fair game."""
        mine = {os.getpid(), os.getppid()}
        own_pgid = os.getpgrp()
        return [h for h in kill_render.find(proj)
                if h["pid"] not in mine and h["pgid"] != own_pgid]

    # Snapshot first: after the parents die these pids are unreachable by ppid.
    doomed = set()
    if p and p.poll() is None:
        kids, _ = childproc.descendants(p.pid)
        doomed.update(kids)
        doomed.add(p.pid)
        childproc.kill_tree(p.pid)
        try:
            p.wait(timeout=10)
        except Exception:
            pass

    if not proj:
        return
    deadline = time.time() + REAP_DEADLINE_S
    killed = set()
    while time.time() < deadline:
        hits = _project_hits()
        for h in hits:
            kids, _ = childproc.descendants(h["pid"])
            doomed.update(kids)
            doomed.add(h["pid"])
        if hits:
            killed.update(kill_render.kill(hits, log=lambda m: print(f"[phase1] {m}",
                                                                     flush=True)))
        # Survivors that re-parented to init are no longer anyone's descendant.
        strays = _running(doomed)
        for q in strays:
            childproc.kill_tree(q)
            killed.add(q)
        if not hits and not strays:
            break
        time.sleep(REAP_PASS_PAUSE_S)

    leftover = _running(doomed) + [h["pid"] for h in _project_hits()]
    if leftover:
        print(f"[phase1] WARNING: {len(leftover)} render process(es) survived the "
              f"sweep: {sorted(set(leftover))} — check `kill_render.py "
              f"--sweep-orphans`", flush=True)
    elif killed:
        print(f"[phase1] reaped {len(killed)} render process(es)", flush=True)


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return True
    return True


def _running(pids):
    """The subset of `pids` genuinely still executing.

    os.kill(pid, 0) on its own is not a liveness test: a killed process whose
    parent has not reaped it stays a ZOMBIE and still answers signal 0. A sweep
    loop built on that spins to its deadline and then reports phantom survivors
    (caught by the reap test, 2026-08-20). Ask ps for state and drop anything
    in Z."""
    pids = list(pids)
    if not pids:
        return []
    try:
        out = subprocess.run(["ps", "-o", "pid=,state=", "-p",
                              ",".join(str(p) for p in pids)],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return [p for p in pids if _alive(p)]     # best effort if ps is unavailable
    live = []
    for line in out.split("\n"):
        f = line.split()
        if len(f) >= 2 and not f[1].startswith("Z"):
            try:
                live.append(int(f[0]))
            except ValueError:
                pass
    return live


def _terminate(signum, _frame):
    """Kill the running verb and every descendant, then die of the same signal."""
    name = signal.Signals(signum).name
    print(f"\n[phase1] caught {name} — stopping the render and its children", flush=True)
    _reap(f"caught {name}")
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


def verb_name(cmd):
    """Short stable name for a verb, for the failure record. explainer2 verbs are
    argv[1]; frame_qc is invoked as `python .../frame_qc.py`, whose argv[1] is an
    absolute path that would differ across checkouts and defeat fingerprinting."""
    if len(cmd) > 1 and cmd[1].endswith(".py"):
        return Path(cmd[1]).stem
    return cmd[1] if len(cmd) > 1 else cmd[0]


def record_failure(proj, verb, rc):
    """Write work/render_failure.json so the watcher can tell a transient crash from
    a verb that can never succeed here.

    `streak` counts CONSECUTIVE launches failing at the same verb with the same exit
    code. That is the signal the watcher blocks on: FWF 2026-08-31 failed at `stills`
    with rc 1 thirty-one times running, each launch re-rendering the video first, and
    nothing in the loop could tell that from a flaky render worth retrying. A run that
    fails somewhere new resets the streak, because that is genuinely new information."""
    f = Path(proj) / "work" / "render_failure.json"
    fp = f"{verb}:{rc}"
    prev = {}
    try:
        prev = json.loads(f.read_text())
    except (OSError, ValueError):
        pass
    streak = prev.get("streak", 0) + 1 if prev.get("fp") == fp else 1
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"fp": fp, "verb": verb, "rc": rc,
                                 "streak": streak, "ts": int(time.time())}))
    except OSError as e:                      # a failure record that cannot be written
        print(f"[phase1] could not write {f}: {e}", flush=True)   # must not mask the
        return 0                                                  # real failure below
    return streak


def clear_failure(proj):
    """Drop a stale failure record once the render gets all the way through."""
    try:
        (Path(proj) / "work" / "render_failure.json").unlink()
    except OSError:
        pass


def run_verb(cmd):
    """Run one explainer2 verb as a child in its OWN process group."""
    print(f"\n[phase1] $ {' '.join(cmd)}", flush=True)
    p = subprocess.Popen(cmd, start_new_session=True)
    _child["proc"] = p
    rc = p.wait()
    _child["proc"] = None
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--explainer", required=True, help="path to the explainer2 CLI")
    args = ap.parse_args()

    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(s, _terminate)

    proj = str(Path(args.project_dir).resolve())
    _child["proj"] = proj                 # _reap needs this from the signal handler
    exp = args.explainer

    # Which aspects this project actually renders. Read ONCE: the stills verb and
    # frame_qc below both key off it, and both must agree with what `media` produced.
    try:
        pj = json.loads((Path(proj) / "project.json").read_text())
        rendered = list(pj.get("aspects") or [pj.get("aspect", "9:16")])
    except Exception as e:                        # a missing/odd project.json must
        print(f"[phase1] cannot read aspects ({e}) — defaulting to 9:16", flush=True)
        rendered = ["9:16"]                       # never take the render down

    # Stills aspect (2026-09-01). This was hardcoded to 4:5. That was silently fine
    # while the renderer emitted 4:5 whatever the config said, so nothing caught it
    # when the 2026-08-30 decision retired the 4:5 cut. Once the renderer started
    # honoring `aspects`, `stills` asked for a video that is no longer produced and
    # exited 1 — phase 1 died BEFORE writing render_complete.json, and the watcher,
    # which has no other success signal, respawned it 31 times on FWF 2026-08-31
    # while the episode never published. Prefer 4:5 where a show still renders it;
    # otherwise take what was actually rendered.
    stills_aspect = "4:5" if "4:5" in rendered else rendered[0]

    verbs = [
        [exp, "media", proj],
        [exp, "stills", proj, "--aspect", stills_aspect],
        [exp, "handoff", proj],
        [exp, "validate", proj],
    ]

    # Framing QC (2026-08-30). `validate` checks manifest/caption STRUCTURE and `qa`
    # checks timing, so neither has ever looked at a pixel. The FWF daily shipped a
    # punch card clipped at both frame edges to six platforms and every gate said ok.
    # frame_qc extracts real frames and blocks on clipped type; a non-zero exit here
    # means no render_complete.json, so Phase 2 never publishes the broken render.
    # It is deliberately narrow (see the tool's docstring) and measured zero false
    # positives across FWF 2026-08-29 and 2026-08-30.
    qc = Path(__file__).resolve().parent / "frame_qc.py"
    if qc.is_file():
        for a in rendered:
            verbs.append([sys.executable, str(qc), proj, "--aspect", a,
                          "--json", str(Path(proj) / "work" /
                                        f"frame_qc_{a.replace(':', 'x')}.json")])
    else:
        print(f"[phase1] frame_qc: {qc} missing — skipping framing QC", flush=True)
    t0 = time.time()
    for cmd in verbs:
        rc = run_verb(cmd)
        if rc != 0:
            streak = record_failure(proj, verb_name(cmd), rc)
            print(f"[phase1] FAILED: {cmd[1]} exited {rc} — no render_complete.json "
                  f"written, Phase 2 will not publish "
                  f"(same failure {streak}x running)", flush=True)
            # A verb that dies (crash, scriptguard refusal, remotion throw) can
            # still leave npm/node/chrome running; without this the failure path
            # leaked a tree that then starved the NEXT render (2026-08-20).
            _reap(f"{cmd[1]} exited {rc}")
            return rc

    clear_failure(proj)          # got all the way through; any prior streak is stale
    sentinel = Path(proj) / "work" / "render_complete.json"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(json.dumps({"ts": int(time.time()),
                                    "wall_clock_s": round(time.time() - t0, 1),
                                    "driver": "phase1_render.py"}))
    print(f"[phase1] OK — wrote {sentinel} in {time.time() - t0:.0f}s", flush=True)
    # Insurance on the happy path too: remotion normally tears its own browsers
    # down, but a chrome that outlived a CLEAN render is exactly the process that
    # goes on to starve the next one. Costs one `ps` when there is nothing to do.
    _reap("render complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
