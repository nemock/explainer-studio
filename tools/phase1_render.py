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
from explainer2 import childproc                              # noqa: E402

_child = {"proc": None}


def _terminate(signum, _frame):
    """Kill the running verb and every descendant, then die of the same signal.

    kill_tree, not killpg: chrome-headless-shell leaves the render's process
    group, so a group-only kill leaves the browser fleet behind (2026-08-10)."""
    name = signal.Signals(signum).name
    print(f"\n[phase1] caught {name} — stopping the render and its children", flush=True)
    p = _child["proc"]
    if p and p.poll() is None:
        childproc.kill_tree(p.pid)
        p.wait()
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


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
    exp = args.explainer
    verbs = [
        [exp, "media", proj],
        [exp, "stills", proj, "--aspect", "4:5"],
        [exp, "handoff", proj],
        [exp, "validate", proj],
    ]
    t0 = time.time()
    for cmd in verbs:
        rc = run_verb(cmd)
        if rc != 0:
            print(f"[phase1] FAILED: {cmd[1]} exited {rc} — no render_complete.json "
                  f"written, Phase 2 will not publish", flush=True)
            return rc

    sentinel = Path(proj) / "work" / "render_complete.json"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(json.dumps({"ts": int(time.time()),
                                    "wall_clock_s": round(time.time() - t0, 1),
                                    "driver": "phase1_render.py"}))
    print(f"[phase1] OK — wrote {sentinel} in {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
