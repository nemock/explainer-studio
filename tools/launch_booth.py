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

Booth 2.0 Batch 3 (docs/booth-upgrade-plan.md): this launcher is now the SHARED
entry point for every voiced channel — the explainer2 deep dives AND the v1-based
daily skills (Founder Tip Tuesday, Monday MedTech, daily founder tip). It takes
any project dir with a project.json + script.json + voiceover/ (v1 script/1 and
v2 script/2 both render; optional fields degrade gracefully). v1's code is
frozen and untouched — routines simply call THIS script instead of v1's
`record-open`/`record-status`.

Usage:
  python3 tools/launch_booth.py <project_dir>            # start detached, wait for READY, pop the tab
  python3 tools/launch_booth.py --no-open <project_dir>  # same, but don't open a browser tab
  python3 tools/launch_booth.py --wait <project_dir>     # block until the green Finish button
  python3 tools/launch_booth.py --status <project_dir>   # DONE / PENDING / NOT_OPEN (instant)
  python3 tools/launch_booth.py --stop                   # stop any running booth

Tab opening (operator directive, 2026-07-04): a booth the operator can't see
isn't open. On a successful start — including the idempotent "already open for
this project" path — the launcher pops the booth URL as a Chrome tab via
macOS `open` (`open -a "Google Chrome" <url>`, falling back to plain `open`).
That's a fire-and-forget OS handoff: no browser automation, no control over
the tab, just the tab appearing. Best-effort — a failed `open` never fails
the launch (the URL is still printed). `--status` and `--wait` never open
anything; pass --no-open for headless/testing launches.

Port: 8765 fixed (Chrome scopes the mic grant to the exact origin). If 8765 is
already held by ANOTHER project's booth, the launcher auto-falls back to the
next free port (8766..8770) rather than failing an unattended routine fire —
same trade v1's recordlock makes (a one-click mic re-grant on the new origin).
The chosen URL is printed and recorded in <project>/work/booth_port.

The Finish signal: the booth writes <project>/work/record_done.json when the operator
clicks "Finish & render". Run `--wait` as a harness-tracked background task right after
launching the booth; it returns the moment that file appears, so the harness notifies the
agent that recording is done. The sentinel is durable, so even if the waiter dies (app
suspend), the signal isn't lost: re-run `--wait`, `--status`, or just check for the file.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE_PORT = 8765
FALLBACK_PORTS = range(8765, 8771)
LOG = Path("/tmp/explainer-booth.log")


def _pids_on_port(port):
    out = subprocess.run(["/usr/sbin/lsof", "-ti", f"tcp:{port}"],
                         capture_output=True, text=True).stdout.split()
    return [int(p) for p in out if p.strip()]


def _booth_ports_in_use():
    return [p for p in FALLBACK_PORTS if _pids_on_port(p)]


def _project_port(project):
    """The port this project's booth was last launched on (work/booth_port)."""
    f = Path(project) / "work" / "booth_port"
    try:
        return int(f.read_text().strip())
    except (OSError, ValueError):
        return None


def stop():
    ports = _booth_ports_in_use()
    if not ports:
        print(f"no booth running on {BASE_PORT}-{max(FALLBACK_PORTS)}")
        return
    for port in ports:
        for pid in _pids_on_port(port):
            subprocess.run(["/bin/kill", "-TERM", str(pid)])
        print(f"stopped booth on :{port}")


def _pop_tab(url):
    """Open the booth URL as a tab in the operator's Chrome via macOS `open`.
    Fire-and-forget: no automation, no tab control — the OS hands the URL to
    the browser and we're done. Never fails the launch."""
    try:
        r = subprocess.run(["/usr/bin/open", "-a", "Google Chrome", url],
                           capture_output=True, timeout=15)
        if r.returncode != 0:  # Chrome missing/renamed — default browser instead
            subprocess.run(["/usr/bin/open", url], capture_output=True, timeout=15)
        print(f"booth tab opened -> {url}")
    except Exception as e:
        print(f"could not open a browser tab ({e}); open it yourself: {url}")


def _booth_serves_project(port, proj):
    """Does the booth on `port` belong to THIS project? Checked by title match on
    the served page (cheap, no new endpoint). Best-effort: False on any error."""
    try:
        title = str(json.loads((proj / "project.json").read_text()).get("title", ""))
        page = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2).read().decode()
        return bool(title) and title in page
    except Exception:
        return False


def start(project, open_tab=True):
    proj = Path(project).resolve()
    if not (proj / "project.json").exists() or not (proj / "script.json").exists():
        print(f"not a bookable project (need project.json + script.json): {proj}")
        return 1
    # idempotency (v1 record-open parity): if a live booth already serves THIS
    # project, report it instead of opening a duplicate on a fallback port —
    # but still pop the tab: re-running the launcher means "get me the booth".
    for cand in _booth_ports_in_use():
        if _booth_serves_project(cand, proj):
            print(f"booth already open for this project -> http://127.0.0.1:{cand}/")
            if open_tab:
                _pop_tab(f"http://127.0.0.1:{cand}/")
            return 0
    # marker semantics: --status says DONE iff work/record_done.json exists, so a
    # fresh launch must clear a stale one BEFORE the checker can ever see it. The
    # recorder clears it too, but do it here to close the launch->ready window.
    (proj / "work").mkdir(exist_ok=True)
    (proj / "work" / "record_done.json").unlink(missing_ok=True)

    port = None
    for cand in FALLBACK_PORTS:
        if not _pids_on_port(cand):
            port = cand
            break
    if port is None:
        print(f"no free booth port in {BASE_PORT}-{max(FALLBACK_PORTS)}; run --stop first")
        return 1
    if port != BASE_PORT:
        print(f"note: :{BASE_PORT} busy (another booth) — using :{port}; "
              f"Chrome will re-ask for the mic once on the new origin")

    env = dict(os.environ, EXPLAINER_RECORDER_PORT=str(port))
    url = f"http://127.0.0.1:{port}/"
    cmd = ["/usr/bin/caffeinate", "-ims",
           str(REPO / "bin" / "explainer2"), "record", str(proj), "--no-open"]
    with open(LOG, "ab") as lf:
        lf.write(f"\n=== booth launch {time.strftime('%Y-%m-%d %H:%M:%S')} :{port} {proj}\n".encode())
        p = subprocess.Popen(
            cmd, cwd=str(REPO), stdout=lf, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True, env=env,
        )
    # wait for the server to answer before returning
    for _ in range(40):
        time.sleep(0.5)
        try:
            urllib.request.urlopen(url, timeout=1)
            (proj / "work" / "booth_port").write_text(str(port))
            print(f"booth READY (detached, caffeinated) pid={p.pid} -> {url}")
            print(f"log: {LOG}")
            if open_tab:
                _pop_tab(url)
            return 0
        except Exception:
            if p.poll() is not None:
                print(f"booth exited early (code {p.returncode}); see {LOG}")
                return 1
    print(f"booth started pid={p.pid} but did not answer in 20s; check {LOG}")
    return 1


def status(project):
    """Instant, script-friendly state for the routine checker tasks.
    Prints one of: DONE <json> | PENDING <url> | NOT_OPEN. Mirrors v1
    record-status semantics: DONE is durable (survives booth exit)."""
    proj = Path(project).resolve()
    marker = proj / "work" / "record_done.json"
    if marker.exists():
        print("DONE", marker.read_text().strip())
        return 0
    port = _project_port(proj)
    ports = [port] if port else list(FALLBACK_PORTS)
    for cand in ports:
        if cand and _pids_on_port(cand):
            print(f"PENDING http://127.0.0.1:{cand}/")
            return 0
    print("NOT_OPEN")
    return 0


def wait(project, max_seconds=6 * 3600):
    """Block until the booth's Finish sentinel appears, then print it and return 0.
    Returns 2 if the booth process disappears before finishing (crash / early stop)."""
    proj = Path(project).resolve()
    marker = proj / "work" / "record_done.json"
    for i in range(max_seconds):
        if marker.exists():
            print("RECORD FINISHED:", marker.read_text()); return 0
        # every ~5s, check the booth is still alive; if it's gone with no marker, stop waiting
        if i % 5 == 0 and i > 2 and not _booth_ports_in_use():
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
    elif len(sys.argv) == 3 and sys.argv[1] == "--status":
        sys.exit(status(sys.argv[2]))
    elif len(sys.argv) == 3 and sys.argv[1] == "--no-open":
        sys.exit(start(sys.argv[2], open_tab=False))
    elif len(sys.argv) == 2 and not sys.argv[1].startswith("-"):
        sys.exit(start(sys.argv[1]))
    else:
        print(__doc__)
        sys.exit(2)
