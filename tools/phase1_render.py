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
It is scoped to this project, so a concurrent render of another show is untouched.

Then (2026-09-03) it sweeps every remotion browser already under init (ppid 1),
machine-wide. That sweep used to be an explicit `kill_render.py --sweep-orphans`
on the theory that ppid-1 trees are unattributable. They are, and it does not
matter: a browser only reaches ppid 1 when the node driving it is dead, so it is
never part of a live render and killing it can never abort work. The case the
project-scoped passes cannot see: remotion hits its 180s browser-connect timeout,
rejects WITHOUT killing the browser it spawned `detached`, node exits, and chrome
is already under init when this runs — no ppid link, no --props to match. Three
such trees from the 2026-08-31 daily-founder-tip crash-loop sat resident for
three days. The recording watcher runs the same sweep every cycle for whatever
this driver never gets to see (SIGKILL on the driver, hand-run renders).

`explainer2 media` also refuses to run at all when the recorded audio disagrees
with script.json (scriptguard.py), in which case this exits non-zero with
BLOCKED.md written and no sentinel, so Phase 2 never publishes.

Studio profile (2026-09-13, docs/booth-finish-local-plan.md Phase B). `--profile studio`
runs the explainer2 deep-dive / masterclass / promo chain instead of the booth-show
verbs: one `explainer2 media` (narrate, align, remotion render, manifest, qa under the
render lock), then `explainer2 shorts` when shorts/plan.json exists. No stills, handoff,
validate, or frame_qc: those belong to the studio session's Package step, which needs
copy a human writes. A shorts refusal or failure does NOT fail the run — the long-form
render is the expensive, irreplaceable part — it is recorded in the sentinel and in
work/RESUME.md, which the driver writes for the session to read first when it is
resumed. The driver then posts a macOS notification and, when the booth was opened from
an interactive desktop session (work/booth_origin.json), deep-links that session forward.

Usage: phase1_render.py --explainer <bin> [--profile shows|studio] <project_dir>
"""
import argparse
import hashlib
import json
import os
import re
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
    concurrent render of another show is never touched. The ppid==1 sweep that
    follows is machine-wide but provably harmless: see kill_render.orphan_browsers.
    """
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

    # Orphans (ppid 1) are not "ours" by any link we can still see, but they are
    # provably nobody's: a browser only reaches ppid 1 when the node driving it
    # is dead. On the 2026-08-31 crash-loop remotion hit its 180s browser-connect
    # timeout, threw WITHOUT killing the browser it had spawned detached, node
    # exited, and by the time this ran chrome was already under init — the
    # project-scoped passes above found nothing, and three trees sat for 3 days.
    killed.update(kill_render.sweep_orphans(
        log=lambda m: print(f"[phase1] {m}", flush=True)))

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


_FAIL_RE = re.compile(r"^\d\d:\d\d:\d\d FAIL\s+(\w+):\s*(.*)$")


def failure_detail(proj, since=None):
    """(stage, error text) of the last `FAIL  <stage>: …` line `explainer2 media` wrote
    to work/run.log during THIS launch, or ("", "").

    run.log carries a time of day and no date, so a stale FAIL from an earlier launch is
    ruled out by the file's mtime: if nothing wrote to it since this launch began, there
    is no failure line of ours in it. Numbers are stripped from the text before it is
    fingerprinted, so a message that embeds a count or a pid still matches itself."""
    log = Path(proj) / "work" / "run.log"
    try:
        if since is not None and log.stat().st_mtime < since:
            return "", ""
        lines = log.read_text(errors="replace").splitlines()[-200:]
    except OSError:
        return "", ""
    floor = time.strftime("%H:%M:%S", time.localtime(since)) if since is not None else None
    for line in reversed(lines):
        if floor and re.match(r"^\d\d:\d\d:\d\d ", line) and line[:8] < floor:
            break                                        # written before this launch began
        m = _FAIL_RE.match(line)
        if m:
            return m.group(1), re.sub(r"\d+", "N", m.group(2)).strip()
    return "", ""


def record_failure(proj, verb, rc, since=None):
    """Write work/render_failure.json so the watcher can tell a transient crash from
    a verb that can never succeed here.

    `streak` counts CONSECUTIVE launches failing at the same verb with the same exit
    code. That is the signal the watcher blocks on: FWF 2026-08-31 failed at `stills`
    with rc 1 thirty-one times running, each launch re-rendering the video first, and
    nothing in the loop could tell that from a flaky render worth retrying. A run that
    fails somewhere new resets the streak, because that is genuinely new information."""
    f = Path(proj) / "work" / "render_failure.json"
    stage, detail = failure_detail(proj, since)
    # The fingerprint names the failing STAGE and its error (2026-10-01). "media:1" alone
    # covered every way `media` can fail, so the watcher could not tell one broken take
    # failing identically from six different flakes, and waited for six before it spoke.
    fp = f"{verb}:{rc}"
    if stage:
        fp += f":{stage}:{hashlib.sha1(detail.encode()).hexdigest()[:10]}"
    prev = {}
    try:
        prev = json.loads(f.read_text())
    except (OSError, ValueError):
        pass
    streak = prev.get("streak", 0) + 1 if prev.get("fp") == fp else 1
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"fp": fp, "verb": verb, "rc": rc, "stage": stage,
                                 "detail": detail[:300],
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


def _read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}


def studio_announce(proj, title, text):
    """Notification + deep link back to the originating desktop session (same handoff
    recorder.py makes at Finish). Best-effort; never raises."""
    origin = _read_json(Path(proj) / "work" / "booth_origin.json")
    name = origin.get("name")
    if name:
        text = f"{text} Resume session {name}."
    safe = lambda v: str(v).replace("\\", " ").replace('"', "'")
    try:
        subprocess.run(["/usr/bin/osascript", "-e",
                        f'display notification "{safe(text)}" with title "{safe(title)}"'],
                       capture_output=True, timeout=15)
    except Exception:
        pass
    sid = origin.get("session_id")
    if sid and origin.get("kind") == "interactive" and origin.get("entrypoint") == "claude-desktop":
        try:
            subprocess.run(["/usr/bin/open", f"claude://code/continue?session={sid}"],
                           capture_output=True, timeout=15)
        except Exception:
            pass


def write_resume_md(proj, wall_s, shorts_note):
    """work/RESUME.md: the handoff the resumed session reads FIRST (SKILL §6/§7).

    Everything a session used to re-derive after the waiter fired — what rendered, what
    QA said, what the booth flagged, what is left — in one file, so a fresh or resumed
    session can pick up cold without re-running twenty minutes of render."""
    proj = Path(proj)
    pj = _read_json(proj / "project.json")
    done = _read_json(proj / "work" / "record_done.json")
    adlib = _read_json(proj / "work" / "adlib_report.json")
    # The booth writes the report just before record_done.json, so one older than that
    # by minutes belongs to an earlier session. Reading a missing or stale report as
    # "none" is how module 6 of the Product Leadership series showed a clean drift check
    # that never ran (2026-09-23).
    rep_p, done_p = proj / "work" / "adlib_report.json", proj / "work" / "record_done.json"
    adlib_fresh = bool(adlib) and not (done_p.exists() and rep_p.exists()
                                       and rep_p.stat().st_mtime < done_p.stat().st_mtime - 120)
    results = _read_json(proj / "work" / "results.json")
    origin = _read_json(proj / "work" / "booth_origin.json")
    exit_ = _read_json(proj / "work" / "booth_exit.json")
    qa = results.get("qa") or {}
    warnings = qa.get("warnings") if isinstance(qa, dict) else None
    if warnings is None and isinstance(qa, dict):
        warnings = [f"{k}: {v}" for k, v in qa.items()]
    lines = [
        "<!-- written by tools/phase1_render.py --profile studio; the recording watcher -->",
        f"# RESUME — {pj.get('title', proj.name)}",
        "",
        f"Recording finished {exit_.get('at', '(unknown time)')}; Phase 1 rendered by the "
        f"launchd recording watcher in {wall_s:.0f}s with zero tokens.",
        "",
        "## Already done — do NOT re-run",
        "",
        "- `explainer2 media`: narrate, align, render (remotion), manifest, qa "
        "— details in `work/results.json`, video under `video/`.",
        f"- `explainer2 shorts`: {shorts_note}",
        "",
        "## Recording",
        "",
        f"- cards recorded: {len(done.get('recorded', []))} of {done.get('segments', '?')}"
        + (f"; missing: {done.get('missing')}" if done.get("missing") else ""),
        (f"- adlib re-record flags: {adlib.get('rerecord') or 'none'}"
         + (f"; unchecked: {adlib.get('unchecked')}" if adlib.get("unchecked") else "")
         + (f"; worst drift {adlib.get('worst_drift'):.2f}" if isinstance(adlib.get("worst_drift"), (int, float)) else "")
         if adlib_fresh else
         "- adlib report: NONE for this session, so the drift check did not run. "
         "Run `bin/explainer2 adlib <dir>` before trusting the takes."),
        "",
        "## QA (from `work/results.json`)",
        "",
    ]
    if warnings:
        lines += [f"- {w}" for w in warnings]
    else:
        lines += ["- no QA warnings recorded"]
    lines += [
        "",
        "## Next (skills/explainer2/SKILL.md)",
        "",
        "1. §7: read the QA warnings above; fix what is fixable. Re-render only if you "
        "changed something (`bin/explainer2 render <dir>`; align first if any take changed).",
        "2. §7b: review `work/adlib_report.json` — noise vs real drift.",
        "3. §8 Package: run the `humaner` skill first, then article, share copy, thumbnail, "
        "validate. Shorts: if the line above says deferred or failed, run "
        "`bin/explainer2 shorts <dir>` yourself.",
        "",
        f"Origin session: {origin.get('name') or '(none recorded)'}"
        + (f" ({origin.get('session_id')})" if origin.get("session_id") else ""),
        "",
    ]
    (proj / "work" / "RESUME.md").write_text("\n".join(lines))


def run_studio(proj, exp, t0):
    """The studio chain. Returns the exit code; writes the sentinel on success."""
    rc = run_verb([exp, "media", proj])
    if rc != 0:
        streak = record_failure(proj, "media", rc, since=t0)
        print(f"[phase1] FAILED: media exited {rc} — no render_complete.json written "
              f"(same failure {streak}x running)", flush=True)
        _reap(f"media exited {rc}")
        if streak == 1:                # later identical failures: the watcher's
            studio_announce(proj, "Render failed",   # render-blocked notice covers them
                            f"{Path(proj).name}: media exited {rc}. "
                            f"See the watcher's render log.")
        return rc
    shorts_note = "no shorts/plan.json — nothing to cut"
    if (Path(proj) / "shorts" / "plan.json").exists():
        src = run_verb([exp, "shorts", proj])
        if src == 0:
            shorts_note = "cut OK — see shorts/"
        else:
            # Admission refused (another job holds the engine) or a real failure.
            # Either way the long-form is done; the session cuts the Shorts itself.
            shorts_note = (f"NOT cut (exited {src}) — run `bin/explainer2 shorts <dir>` "
                           f"after checking `render-status`")
            print(f"[phase1] shorts exited {src} — long-form is complete, recording "
                  f"the Shorts as deferred", flush=True)
            _reap(f"shorts exited {src}")
    clear_failure(proj)
    wall = time.time() - t0
    sentinel = Path(proj) / "work" / "render_complete.json"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(json.dumps({"ts": int(time.time()), "wall_clock_s": round(wall, 1),
                                    "driver": "phase1_render.py", "profile": "studio",
                                    "shorts": shorts_note}))
    try:
        write_resume_md(proj, wall, shorts_note)
    except Exception as e:                       # the handoff note must never undo a
        print(f"[phase1] could not write RESUME.md: {e}", flush=True)   # finished render
    print(f"[phase1] OK — wrote {sentinel} in {wall:.0f}s", flush=True)
    _reap("render complete")
    studio_announce(proj, "Render finished",
                    f"{_read_json(Path(proj) / 'project.json').get('title', Path(proj).name)}"
                    f" rendered in {wall / 60:.0f} min. Read work/RESUME.md.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--explainer", required=True, help="path to the explainer2 CLI")
    ap.add_argument("--profile", default="shows", choices=["shows", "studio"],
                    help="shows = booth-show verbs (default); studio = explainer2 deep "
                         "dive / masterclass / promo chain (media + shorts, RESUME.md)")
    args = ap.parse_args()

    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(s, _terminate)

    proj = str(Path(args.project_dir).resolve())
    _child["proj"] = proj                 # _reap needs this from the signal handler
    exp = args.explainer
    if args.profile == "studio":
        return run_studio(proj, exp, time.time())

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
            streak = record_failure(proj, verb_name(cmd), rc, since=t0)
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
