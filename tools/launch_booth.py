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
                                                        # PENDING only for a booth that
                                                        # identifies as THIS project
  python3 tools/launch_booth.py --claim <project_dir>    # CLAIMED / LOCKED — atomically claim completion so concurrent/resumed fires can't double-post
  python3 tools/launch_booth.py --stop                   # stop any running booth

Tab opening (operator directive, 2026-07-04): a booth the operator can't see
isn't open. On a successful start — including the idempotent "already open for
this project" path — the launcher pops the booth URL as a Chrome tab via
macOS `open` (`open -a "Google Chrome" <url>`, falling back to plain `open`).
That's a fire-and-forget OS handoff: no browser automation, no control over
the tab, just the tab appearing. Best-effort — a failed `open` never fails
the launch (the URL is still printed). `--status` and `--wait` never open
anything; pass --no-open for headless/testing launches.

Port: each routine family gets its own stable "home" port (see FAMILY_HOME),
so a booth tab always serves its own routine's script and Chrome remembers the
mic grant per origin. Chrome scopes the mic grant to the exact origin, so a
stable per-routine port also means at most one mic re-grant, ever. If a family's
home port is already held (a same-family project, or an overflow), the launcher
falls back to the next free port in the 8765..8794 pool rather than failing an
unattended fire. The chosen URL is printed and recorded in <project>/work/booth_port.

The Finish signal: the booth writes <project>/work/record_done.json when the operator
clicks "Finish & render". Run `--wait` as a harness-tracked background task right after
launching the booth; it returns the moment that file appears, so the harness notifies the
agent that recording is done. The sentinel is durable, so even if the waiter dies (app
suspend), the signal isn't lost: re-run `--wait`, `--status`, or just check for the file.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORKSPACE = Path("/Volumes/Casima/claudeCode")
BASE_PORT = 8765
NUM_PORTS = 30                                    # booth port pool: 8765..8794
ALL_PORTS = range(BASE_PORT, BASE_PORT + NUM_PORTS)
LOG = Path("/tmp/explainer-booth.log")

# Per-routine "home" port so each routine's booth keeps its own origin. Two goals:
# (1) a stray booth tab from a DIFFERENT routine can never end up serving this
# routine's script (the :8765 collision of 2026-07-22, where a Who-Signs-the-Check
# tab served an ISO 14971 masterclass deck), and (2) Chrome scopes the mic grant to
# the origin, so a stable per-routine port means Chrome re-asks for the mic at most
# once, ever, instead of every time the shared :8765 bounced to a fallback.
# Key = the path segment directly under the workspace root (the routine family).
# Residual (accepted): routines that SHARE a family dir (the two ig_carousel dailies)
# or run two projects in one day (explainer deep dives) still contend within their
# one home port and fall through to the free-port scan in start().
FAMILY_HOME = {
    "Monday MedTech":         8765,
    "Founder_Tip_Tuesday":    8766,
    "Who Signs The Check":    8767,
    "The Teardown":           8768,
    "Failure Modes Friday":   8769,
    "ig_carousel":            8770,   # daily founder tip AND daily beats both write here
    "explainer-content":      8771,   # explainer2 deep dives / studio
    "ISO_14971_Masterclass":  8772,
    "waveform-studio":        8773,
}
_HASH_BASE = 8780                                 # unlisted families hash into 8780..8794


def _family(project):
    """The routine family: the first path segment under the workspace root
    (e.g. 'Who Signs The Check', 'ig_carousel', 'ISO_14971_Masterclass')."""
    try:
        return Path(project).resolve().relative_to(WORKSPACE).parts[0]
    except (ValueError, IndexError):
        return Path(project).resolve().parent.name


def _preferred_port(project):
    """Stable home port for this project's routine family. Known families get an
    explicit port; anything else hashes deterministically into 8780..8794 so it
    still keeps a consistent origin without stepping on the explicit assignments."""
    fam = _family(project)
    if fam in FAMILY_HOME:
        return FAMILY_HOME[fam]
    span = BASE_PORT + NUM_PORTS - _HASH_BASE      # width of the hash band
    h = int(hashlib.sha1(fam.encode()).hexdigest(), 16)
    return _HASH_BASE + (h % span)


def _pids_on_port(port):
    out = subprocess.run(["/usr/sbin/lsof", "-ti", f"tcp:{port}"],
                         capture_output=True, text=True).stdout.split()
    return [int(p) for p in out if p.strip()]


def _booth_ports_in_use():
    return [p for p in ALL_PORTS if _pids_on_port(p)]


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
        print(f"no booth running on {BASE_PORT}-{max(ALL_PORTS)}")
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


def _project_title(proj):
    """The project's title, or '' if it has none. Used to tell 'this booth is not ours'
    apart from 'we have no way to tell', which matter differently in status()."""
    try:
        return str(json.loads((proj / "project.json").read_text()).get("title", ""))
    except Exception:
        return ""


def _booth_serves_project(port, proj):
    """Does the booth on `port` belong to THIS project? Checked by title match on
    the served page (cheap, no new endpoint). Best-effort: False on any error."""
    try:
        title = _project_title(proj)
        page = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2).read().decode()
        return bool(title) and title in page
    except Exception:
        return False


def start(project, open_tab=True):
    proj = Path(project).resolve()
    if not (proj / "project.json").exists() or not (proj / "script.json").exists():
        print(f"not a bookable project (need project.json + script.json): {proj}")
        return 1
    # Shorts-plan preflight (added 2026-07-28 after #52 opened the booth with no
    # shorts/plan.json, so the operator recorded the main script and none of the
    # native Short hooks/outros, and had to come back for a second session).
    # The recorder builds its card list from script.json + shorts/plan.json, so a
    # missing plan silently yields a main-script-only booth. Deep dives are supposed
    # to record their Shorts in the SAME sitting (shorts-playbook: every cut gets a
    # separately-recorded native hook + outro). Warn loudly; never block — a
    # deliberate no-Shorts run is legitimate.
    try:
        _ctype = json.loads((proj / "project.json").read_text()).get("content_type", "")
    except Exception:
        _ctype = ""
    if _ctype == "deepdive" and not (proj / "shorts" / "plan.json").exists():
        print("WARNING: no shorts/plan.json — this booth will show the main script ONLY.")
        print("         The native Short hooks/outros will NOT be recordable in this session.")
        print("         Author shorts/plan.json first (shorts-playbook) unless you intend no Shorts.")
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

    pref = _preferred_port(proj)
    ordered = [pref] + [p for p in ALL_PORTS if p != pref]
    port = next((cand for cand in ordered if not _pids_on_port(cand)), None)
    if port is None:
        print(f"no free booth port in {BASE_PORT}-{max(ALL_PORTS)}; run --stop first")
        return 1
    if port != pref:
        print(f"note: home port :{pref} busy (another booth) — using :{port}; "
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
    # A LISTENER IS NOT A BOOTH (fixed 2026-08-13). This used to report PENDING for any
    # process holding a pool port. With no work/booth_port yet it scanned the whole
    # 8765..8794 pool, so an unrelated server on a pool port answered for us — a Daily
    # Beats archive on 8770 made a project that had never been recorded report PENDING.
    # Unattended checkers read that as "booth already open" and wait instead of launching.
    # start() has always confirmed identity before reusing a port; status() now does too.
    port = _project_port(proj)
    if port and _pids_on_port(port):
        # We wrote work/booth_port ourselves, so a listener there is already good evidence.
        # The title check upgrades it; accept when the project has no title to check with,
        # rather than regressing an untitled project to NOT_OPEN.
        if _booth_serves_project(port, proj) or not _project_title(proj):
            print(f"PENDING http://127.0.0.1:{port}/")
            return 0
    # No recorded port, or it is no longer ours: scan the pool, but accept ONLY a port
    # that positively identifies as this project's booth.
    for cand in ALL_PORTS:
        if cand != port and _pids_on_port(cand) and _booth_serves_project(cand, proj):
            print(f"PENDING http://127.0.0.1:{cand}/")
            return 0
    print("NOT_OPEN")
    return 0


def claim(project):
    """Atomically claim the render+publish pipeline for a finished recording so
    that two checker fires (or one that suspended and resumed) can't BOTH run
    Steps 8-11 and double-post. Prints one of:

      CLAIMED           -> this fire won the race; proceed through completion.
      LOCKED done       -> a README already exists; the week is fully published.
                           (Nothing to do; STOP.)
      LOCKED <holder>   -> another fire is mid-completion right now; back off.

    The lock is work/publish_lock.json, created with O_CREAT|O_EXCL so exactly
    one caller can win even under concurrent fires. It self-heals: once the
    winner writes PROJ/README.md the week is done, and any later caller short-
    circuits on the README check before ever touching the lock. A stale lock
    (holder pid gone, no README) older than max_age_s is reclaimed so a fire
    that died mid-completion can't wedge the week forever."""
    proj = Path(project).resolve()
    if (proj / "README.md").exists():
        print("LOCKED done"); return 0
    lock = proj / "work" / "publish_lock.json"
    max_age_s = 45 * 60  # a completion run is minutes; 45m means the holder died
    payload = json.dumps({"pid": os.getpid(), "ts": time.time()})
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        try:
            prev = json.loads(lock.read_text())
        except (OSError, ValueError):
            prev = {}
        pid, ts = prev.get("pid"), prev.get("ts", 0)
        alive = pid is not None and _pid_alive(pid)
        if alive or (time.time() - ts) < max_age_s:
            print("LOCKED", pid if pid is not None else "unknown"); return 0
        # stale: the previous holder is gone and it's been too long — reclaim it.
        lock.write_text(payload)
        print("CLAIMED"); return 0
    with os.fdopen(fd, "w") as fh:
        fh.write(payload)
    print("CLAIMED"); return 0


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


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
    elif len(sys.argv) == 3 and sys.argv[1] == "--claim":
        sys.exit(claim(sys.argv[2]))
    elif len(sys.argv) == 3 and sys.argv[1] == "--no-open":
        sys.exit(start(sys.argv[2], open_tab=False))
    elif len(sys.argv) == 2 and not sys.argv[1].startswith("-"):
        sys.exit(start(sys.argv[1]))
    else:
        print(__doc__)
        sys.exit(2)
