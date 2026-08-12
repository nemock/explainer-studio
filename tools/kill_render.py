#!/usr/bin/env python3
"""Kill a render — the WHOLE tree — and leave no stale render lock behind.

Why this exists (2026-08-10): the recording watcher's Phase 1 runs as
`caffeinate -ims /bin/sh -c '<explainer2 verbs>'` in its own session. Killing the
`/bin/sh` pid by hand reaped only the shell. `npm exec remotion render`, its
`node` child and the entire `chrome-headless-shell` tree survived, reparented to
init, and kept rendering frames for a video nobody wanted — while
`/tmp/explainer-render.lock` still carried a note naming a pid that was already
dead (the known stale-holder hang).

A process cannot be made to die when a *parent* is killed on macOS (there is no
PDEATHSIG), so the supported way to stop a render is to signal the process GROUP,
which is what this does:

  1. Find every live `explainer2 … cli media <project>` process and every remotion
     render whose --props points into this project.
  2. SIGTERM their process groups, wait, then SIGKILL the stragglers.
  3. Verify nothing remotion/chrome-shaped is left for this project.
  4. Clear the render lock's note if it names a dead pid and the flock is free.

`explainer2 media` also traps SIGTERM/SIGINT/SIGHUP itself (childproc.py) and
kills its own render children, so signalling the group is belt and braces.

Usage:
  kill_render.py <project_dir>            # report what would be killed
  kill_render.py <project_dir> --fix      # actually kill it
  kill_render.py --lock-only              # just clear a stale lock note
"""
import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from explainer2 import childproc                              # noqa: E402

LOCKFILE = "/tmp/explainer-render.lock"   # renderlock.LOCKFILE (shared, fixed)
REMOTION_CHROME = "remotion/node_modules/.remotion/chrome-headless-shell"


def _ps():
    """[(pid, ppid, pgid, command)] for every process on the machine."""
    try:
        out = subprocess.run(["ps", "-Ao", "pid=,ppid=,pgid=,command="],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return []
    rows = []
    for line in out.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) < 4:
            continue
        try:
            rows.append((int(parts[0]), int(parts[1]), int(parts[2]), parts[3]))
        except ValueError:
            continue
    return rows


def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except (ProcessLookupError, ValueError, TypeError):
        return False
    except PermissionError:
        return True
    return True


def _arg_at(cmd, pos, value):
    """True if `value` sits at `pos` as a WHOLE argument (bounded by a space or the
    end of the line), rather than merely as a prefix of a longer path."""
    if not cmd.startswith(value, pos):
        return False
    end = pos + len(value)
    return end == len(cmd) or cmd[end] == " "


def _why(cmd, proj, props):
    """Why `cmd` is a render of `proj`, or None.

    Matched on the RAW command line with exact adjacency, NOT on cmd.split().
    Until 2026-08-12 this tokenised the line and compared the project path against
    a single token, which silently never matched FOUR OF THE FIVE booth shows:
    "Failure Modes Friday", "Monday MedTech", "The Teardown" and "Who Signs The
    Check" all contain spaces, `ps` joins argv with spaces, and a path with spaces
    is therefore indistinguishable from separate arguments. Only
    Founder_Tip_Tuesday ever matched. Caught live on 2026-08-12: the tool reported
    "no render processes found" against a running FMF render and the caller's
    manual kill left ten orphaned chrome-headless-shell processes — the exact
    residue this tool exists to prevent.

    Adjacency preserves the original safety property. A command that merely
    MENTIONS the driver and the path somewhere on its line (a grep, an editor,
    this tool's own invocation) does not match, because the path must sit
    immediately after the verb and end on an argument boundary.
    """
    for driver in ("explainer2.cli", "explainer.cli"):
        marker = f"{driver} media "
        i = cmd.find(marker)
        if i != -1 and _arg_at(cmd, i + len(marker), proj):
            return "media"
    marker = "phase1_render.py "
    i = cmd.find(marker)
    if i != -1 and _arg_at(cmd, i + len(marker), proj):
        return "phase1"
    marker = "--props="
    i = cmd.find(marker)
    if i != -1 and _arg_at(cmd, i + len(marker), props):
        return "remotion"                         # npx/node render of THIS project
    return None


def find(project_dir):
    """Root processes of this project's render (descendants are handled by
    kill_tree, which walks ppid — chrome-headless-shell escapes the group)."""
    proj = str(Path(project_dir).resolve())
    props = os.path.join(proj, "work", "remotion", "props.json")
    hits = []
    for pid, ppid, pgid, cmd in _ps():
        if pid == os.getpid():
            continue
        why = _why(cmd, proj, props)
        if why:
            hits.append({"pid": pid, "ppid": ppid, "pgid": pgid, "why": why,
                         "cmd": cmd[:160]})
    return hits


def orphan_browsers():
    """Remotion browser trees whose parent is gone (ppid 1).

    These cannot be attributed to a project — their argv carries no project path —
    so they are only ever reported/killed as a separate, explicit sweep. This is
    the exact residue of the 2026-08-10 kill: six chrome-headless-shell processes
    still resident 26 minutes after the render that spawned them was killed."""
    return [{"pid": pid, "ppid": ppid, "pgid": pgid, "cmd": cmd[:120]}
            for pid, ppid, pgid, cmd in _ps()
            if REMOTION_CHROME in cmd and ppid == 1]


def kill(hits, log=print):
    """Kill each root and everything under it (group + ppid walk)."""
    for h in hits:
        log(f"killing {h['why']} pid {h['pid']} (group {h['pgid']}) and its descendants")
        childproc.kill_tree(h["pid"])
    return [h["pid"] for h in hits]


def lock_is_free():
    """True if nothing actually holds the flock right now."""
    try:
        fd = open(LOCKFILE, "a+")
    except OSError:
        return True
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return True
    except BlockingIOError:
        return False
    finally:
        fd.close()


def clear_stale_lock(fix=False, log=print):
    """Blank the lockfile NOTE when it names a dead pid and the flock is free.

    The flock itself is released by the kernel when its holder dies, so the note
    is the only thing that can go stale — and a stale note is what made a waiting
    render look permanently blocked on 2026-06-22."""
    p = Path(LOCKFILE)
    if not p.exists():
        log("render lock: no lockfile")
        return False
    try:
        note = json.loads(p.read_text() or "{}")
    except (OSError, ValueError):
        note = {}
    pid = note.get("pid")
    free = lock_is_free()
    if not free:
        log(f"render lock: HELD (note: {note.get('label', '?')} pid {pid}) — leaving alone")
        return False
    if pid and _pid_alive(pid):
        log(f"render lock: free, note pid {pid} still alive — leaving alone")
        return False
    if not pid:
        log("render lock: free, no stale note")
        return False
    log(f"render lock: free but note names dead pid {pid} ({note.get('label', '?')}) — "
        f"{'clearing' if fix else 'would clear'}")
    if fix:
        p.write_text("")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_dir", nargs="?")
    ap.add_argument("--fix", action="store_true", help="actually kill (default: report only)")
    ap.add_argument("--lock-only", action="store_true",
                    help="skip process killing; only clear a stale render-lock note")
    ap.add_argument("--sweep-orphans", action="store_true",
                    help="also kill remotion browser trees whose parent is gone "
                         "(machine-wide; not attributable to one project)")
    args = ap.parse_args()

    if args.lock_only:
        clear_stale_lock(fix=args.fix)
        return 0
    if not args.project_dir:
        ap.error("project_dir is required (or pass --lock-only)")

    hits = find(args.project_dir)
    if not hits:
        print("no render processes found for this project")
    for h in hits:
        print(f"  pid {h['pid']} (group {h['pgid']}, {h['why']}): {h['cmd']}")

    orphans = orphan_browsers()
    if orphans:
        print(f"\n{len(orphans)} orphaned remotion browser process(es) (ppid 1) on this Mac:")
        for o in orphans[:8]:
            print(f"  pid {o['pid']} (group {o['pgid']}): {o['cmd']}")
        if not args.sweep_orphans:
            print("  --sweep-orphans to kill these too (machine-wide, not project-scoped)")

    if (hits or (orphans and args.sweep_orphans)) and not args.fix:
        print("\n--fix to kill what is listed above")
        return 1
    if hits:
        kill(hits)
        time.sleep(1)
        left = find(args.project_dir)
        if left:
            print(f"WARNING: {len(left)} process(es) still alive:")
            for h in left:
                print(f"  pid {h['pid']}: {h['cmd']}")
        else:
            print("all render processes for this project are gone")
    if orphans and args.sweep_orphans and args.fix:
        for o in orphans:
            childproc.kill_tree(o["pid"])
        print(f"swept {len(orphans)} orphaned browser tree(s)")
    clear_stale_lock(fix=args.fix)
    return 0


if __name__ == "__main__":
    sys.exit(main())
