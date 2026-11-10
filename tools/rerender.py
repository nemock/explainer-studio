#!/usr/bin/env python3
"""rerender.py — hand a recorded project back to the watcher for a fresh render.

The sanctioned way to say "I fixed something that is not the script; render it again".
Use it after a deck.json fix or a renderer fix on a project whose recording is fine.

Why it exists (2026-10-01). A publish run that hit a failed gate had no way forward
except to write BLOCKED.md and stop, and no way back in for whoever fixed the cause:
the done-markers the watcher keys on (render_complete.json, the publish lock, the
attempt counters, the block files) each had to be cleared by hand, in the right
combination, and every session that tried wrote its own recipe. One daily episode sat
blocked for two days over a compare slide authored with the wrong field names. This
tool supersedes those markers in one step, so the watcher sees a recorded project with
no render and does what it always does: phase 1 through the render queue, the gates,
then a fresh publish run.

It never renders anything itself, and it refuses when:
  * the project is already published (README.md) or partly published (uploads.json)
  * script.json no longer matches the recording (that needs the booth, not a render)
  * a render or publish worker for this project is still running
  * it has already been used twice for this recording (a third identical retry is a
    verdict: write BLOCKED.md and stop)
  * the deck draws figure marks or annotations and the current deck.json has not been
    seen on rendered stills (2026-11-10): run tools/preview_stills.py <dir> --slides
    <changed>, read its crops, then run this again. That refusal does not use a try.

Usage: rerender.py <project_dir> --reason "<what was fixed>" [--explainer <bin>]
                   [--skip-stills-check "<why>"]
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from explainer2 import jobqueue                               # noqa: E402

MAX_PER_RECORDING = 2
# Moved aside (kept, under work/superseded/<stamp>/): the evidence of the old render.
SUPERSEDE = ("work/render_complete.json", "work/publish_block.json", "work/validate.json",
             "BLOCKED.md")
# Studio projects are judged "rendered" by these too (recording_watcher.studio_rendered).
SUPERSEDE_STUDIO = ("manifest.json", "work/results.json", "work/RESUME.md")
# Deleted: counters and one-shot notification markers that describe the old attempt.
CLEAR = ("work/render_failure.json", "work/render_attempts.json", "work/publish_attempts.json",
         "work/publish_lock.json", "work/publish_blocked_notified",
         "work/render_blocked_notified", "work/watcher_skip.json",
         "work/operator_alert_render.json", "work/operator_alert_publish.json")


def _json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return {}


def _pid_alive(pid):
    import os
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError, TypeError):
        return False
    return True


def _stills_problem(proj):
    """Why the current deck has not been seen on rendered stills, or "" when it has (or
    draws no marks or annotations). Either proof will do: work/preview/preview_check.json
    from tools/preview_stills.py for this exact deck.json at real timing, or the figure-mark
    sheet from tools/mark_stills.py written after the last deck change."""
    import hashlib
    deck_p = proj / "deck.json"
    deck = _json(deck_p)
    slides = deck.get("slides") or []
    if not any(s.get("marks") or s.get("marks_9x16") or s.get("annotations") for s in slides):
        return ""
    chk = _json(proj / "work" / "preview" / "preview_check.json")
    sha = hashlib.sha256(deck_p.read_bytes()).hexdigest()
    if chk.get("deck_sha") == sha and chk.get("timing") == "real" and chk.get("slides"):
        return ""
    ms = proj / "work" / "mark_stills.png"
    if ms.exists() and ms.stat().st_mtime >= deck_p.stat().st_mtime:
        return ""
    if chk.get("deck_sha") == sha:
        return "the stills of this deck were rendered on stand-in timing, before align."
    return ("the current deck.json's marks and annotations have not been seen on rendered "
            "stills (no stills of this deck, and no mark sheet newer than its last change).")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_dir")
    ap.add_argument("--reason", required=True, help="what was fixed (recorded in the project)")
    ap.add_argument("--explainer", default=str(Path(__file__).resolve().parent.parent / "bin" / "explainer2"))
    ap.add_argument("--skip-stills-check", metavar="WHY", default="",
                    help="hand back without fresh stills of the current deck (logged with WHY)")
    ap.add_argument("--operator-approved", metavar="QUOTE", default="",
                    help="the operator's own words approving a re-render past the limit "
                         "(interactive sessions only; logged). Never from a routine.")
    args = ap.parse_args()
    proj = Path(args.project_dir).resolve()
    work = proj / "work"

    def refuse(msg, rc=1):
        print(f"REFUSED: {msg}")
        return rc

    if not (proj / "project.json").exists():
        return refuse(f"{proj} is not a project (no project.json)")
    pj = _json(proj / "project.json")
    done = work / "record_done.json"
    if pj.get("voice_source") != "operator" or not done.exists():
        return refuse("this is not a recorded, watcher-managed project. For a Kokoro project "
                      "queue the render yourself:  explainer2 render <dir> --only "
                      "narrate,align,render,manifest,qa", 2)
    if (proj / "README.md").exists():
        return refuse("README.md exists: this episode is already published")
    if (proj / "uploads.json").exists():
        return refuse("uploads.json exists: a publish got partway. Re-rendering now risks a "
                      "second upload of a different file. This needs a human decision.")
    lk = _json(work / "publish_lock.json")
    if (lk.get("job") and jobqueue.job_active(lk["job"])) or (lk.get("pid") and _pid_alive(lk["pid"])):
        return refuse("a render or publish worker for this project is still running "
                      "(see `explainer2 queue`). Wait for it, or cancel it first.")

    # The recording must still match the script. If it does not, no render can fix it.
    r = subprocess.run([args.explainer, "media", str(proj), "--recheck"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print((r.stdout or r.stderr).strip()[-600:])
        return refuse("script.json does not match the recorded audio. Re-record the changed "
                      "card(s) in the booth, or accept the takes with tools/unstick_stale_script.py.")

    stamp_rec = done.stat().st_mtime
    led = _json(work / "rerender.json")
    if led.get("record_done_mtime") != stamp_rec:
        led = {"record_done_mtime": stamp_rec, "count": 0, "history": []}
    # The operator can approve one more after looking at what is wrong (2026-11-10, episode 3:
    # "Fix them", for a third render with document highlights). Interactive only; the quote
    # is logged. A routine never passes this.
    if led["count"] >= MAX_PER_RECORDING and not args.operator_approved:
        return refuse(f"already re-rendered {led['count']}x for this recording "
                      f"({'; '.join(h['reason'] for h in led['history'])}). A third try is not "
                      f"a fix. Write BLOCKED.md with what is still wrong and stop.")

    # Stills before a re-render (2026-11-10). A fixed deck is only proven fixed on a frame:
    # MedDevice Cyber Guide episode 3's first re-render shipped document boxes tightened by
    # numbers alone, and every one cut through its text. When the deck draws marks or
    # annotations, ask for stills of THIS deck at real timing before handing it back.
    stills = _stills_problem(proj)
    if stills and not args.skip_stills_check:
        return refuse(
            f"{stills}\n  Render stills of the current deck and READ the crops it prints first "
            f"(it queues itself; exit 75 = still running, run the `explainer2 wait` it prints):\n"
            f"    python3 {Path(__file__).resolve().parent / 'preview_stills.py'} {proj} "
            f"--slides <the slides you changed>\n"
            f"  then run this command again. This refusal does not use up one of the "
            f"{MAX_PER_RECORDING} re-renders. Only if no stills can be rendered: "
            f"--skip-stills-check \"<why>\".")

    studio = pj.get("content_type") in ("deepdive", "masterclass", "promo")
    aside = work / "superseded" / time.strftime("%Y%m%d-%H%M%S")
    moved, cleared = [], []
    for rel in SUPERSEDE + (SUPERSEDE_STUDIO if studio else ()):
        src = proj / rel
        if src.exists():
            aside.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(aside / rel.replace("/", "__")))
            moved.append(rel)
    for rel in CLEAR:
        src = proj / rel
        if src.exists():
            src.unlink()
            cleared.append(rel)

    led["count"] += 1
    entry = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "reason": args.reason}
    if stills:
        entry["stills_check_skipped"] = args.skip_stills_check
    if led["count"] > MAX_PER_RECORDING:
        entry["operator_approved"] = args.operator_approved
    led["history"].append(entry)
    (work / "rerender.json").write_text(json.dumps(led, indent=1))
    with (work / "run.log").open("a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} rerender: handed back to the watcher "
                f"({args.reason}); superseded {', '.join(moved) or 'nothing'}\n")

    print(f"OK: {proj.name} handed back to the recording watcher (re-render "
          f"{led['count']} of {MAX_PER_RECORDING} for this recording).")
    print(f"  superseded -> {aside if moved else '(nothing to move)'}: {', '.join(moved) or '-'}")
    print(f"  cleared: {', '.join(cleared) or '-'}")
    print("  Next: on its next 5-minute cycle the watcher queues phase 1 (render, stills, "
          "handoff, validate, frame_qc), then starts a fresh publish run if the gates pass.")
    print("  Booth shows are only processed inside the watcher's hours window; a studio "
          "project is picked up at any hour. Watch it with:  explainer2 queue")
    print("  Do not render it yourself, and do not run this again unless the next gate "
          "fails for a different reason.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
