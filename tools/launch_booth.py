#!/usr/bin/env python3
"""Launch the recording booth DETACHED so it survives the operator going AFK.

The problem this fixes (operator directive, 2026-06-23, said more than once):
launching `explainer2 record` as a harness-tracked background task means the
server dies when the machine/app suspends while the operator is away — which
freezes the booth UI mid-record (the Stop button stops responding because its
backend is gone). There is no reason for the operator's own server to stop.

The fix: start the booth under `caffeinate -ims` (block idle/display/system
sleep for the life of the server) AND in a brand-new session
(`start_new_session=True`, the setsid equivalent) so it is fully detached from
the launching shell and the Claude Code harness process group. It keeps running
until explicitly killed (see --stop), no matter who walks away.

Usage:
  python3 tools/launch_booth.py <project_dir>          # start detached, wait for READY
  python3 tools/launch_booth.py --wait <project_dir>   # block until the green Finish button
  python3 tools/launch_booth.py --stop                 # stop any running booth on the port

Then reload http://localhost:8765/ in the browser.

The Finish signal: the booth writes <project>/work/record_done.json when the operator
clicks "Finish & render". Run `--wait` as a harness-tracked background task right after
launching the booth; it returns the moment that file appears, so the harness notifies the
agent that recording is done. The sentinel is durable, so even if the waiter dies (app
suspend), the signal isn't lost: re-run `--wait` or just check for the file.
"""
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PORT = 8765
URL = f"http://127.0.0.1:{PORT}/"
LOG = Path("/tmp/explainer-booth.log")


def _pids_on_port():
    out = subprocess.run(["/usr/sbin/lsof", "-ti", f"tcp:{PORT}"],
                         capture_output=True, text=True).stdout.split()
    return [int(p) for p in out if p.strip()]


def stop():
    pids = _pids_on_port()
    if not pids:
        print(f"no booth running on :{PORT}")
        return
    for pid in pids:
        subprocess.run(["/bin/kill", "-TERM", str(pid)])
    print(f"stopped booth pid(s) {pids} on :{PORT}")


def start(project):
    if _pids_on_port():
        print(f"booth already running on :{PORT}; run --stop first")
        return 1
    cmd = ["/usr/bin/caffeinate", "-ims",
           str(REPO / "bin" / "explainer2"), "record", project, "--no-open"]
    with open(LOG, "ab") as lf:
        lf.write(f"\n=== booth launch {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n".encode())
        p = subprocess.Popen(
            cmd, cwd=str(REPO), stdout=lf, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True,
        )
    # wait for the server to answer before returning
    for _ in range(40):
        time.sleep(0.5)
        try:
            urllib.request.urlopen(URL, timeout=1)
            print(f"booth READY (detached, caffeinated) pid={p.pid} -> {URL}")
            print(f"log: {LOG}")
            return 0
        except Exception:
            if p.poll() is not None:
                print(f"booth exited early (code {p.returncode}); see {LOG}")
                return 1
    print(f"booth started pid={p.pid} but did not answer in 20s; check {LOG}")
    return 1


def wait(project, max_seconds=6 * 3600):
    """Block until the booth's Finish sentinel appears, then print it and return 0.
    Returns 2 if the booth process disappears before finishing (crash / early stop)."""
    marker = Path(project) / "work" / "record_done.json"
    for i in range(max_seconds):
        if marker.exists():
            print("RECORD FINISHED:", marker.read_text()); return 0
        # every ~5s, check the booth is still alive; if it's gone with no marker, stop waiting
        if i % 5 == 0 and i > 2 and not _pids_on_port():
            if marker.exists():
                print("RECORD FINISHED:", marker.read_text()); return 0
            print("booth exited WITHOUT a finish marker (crashed or stopped early)"); return 2
        time.sleep(1)
    print(f"waiter timed out after {max_seconds}s with no Finish"); return 3


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--stop":
        stop()
    elif len(sys.argv) == 3 and sys.argv[1] == "--wait":
        sys.exit(wait(sys.argv[2]))
    elif len(sys.argv) == 2:
        sys.exit(start(sys.argv[1]))
    else:
        print(__doc__)
        sys.exit(2)
