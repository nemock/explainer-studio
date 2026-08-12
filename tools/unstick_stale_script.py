#!/usr/bin/env python3
"""Recover a project whose script.json changed after the audio was recorded.

This is the tooled version of the manual recovery performed on 2026-08-10, when
`script.json` was edited three minutes after the operator clicked Finish and the
watcher aligned the NEW text against the OLD audio without complaint. The render
guard (`src/explainer2/media/scriptguard.py`) now refuses to render that project
and writes BLOCKED.md; this puts it back into a state the booth can fix.

`--fix` performs exactly the recovery that worked by hand:

  * move each stale `voiceover/seg_NNN.wav` to `seg_NNN.oldtext.bak` — the booth
    then shows those cards as needing a re-record, and BOTH the audio and its
    alternate takes (`seg_NNN.takeN.wav`) are preserved, not deleted
  * move `work/record_done.json` to `record_done.superseded.json` so the watcher
    cannot re-fire Phase 1 on the stale Finish signal
  * clear `work/publish_lock.json` and `work/render_attempts.json`
  * clear a stale `/tmp/explainer-render.lock` note (see tools/kill_render.py)
  * delete the mp4s built from the mismatched audio
  * `--relaunch-booth` reopens the booth on the project's home port

`--accept <ids|all>` is the other resolution: the audio is genuinely still
correct and only the *wording of the script file* changed (numerals spelled out,
punctuation, a typo fix that does not change what is said). It re-stamps those
segments' text records to the current script text instead of throwing takes away.
Use it deliberately — it is an assertion that you listened.

Usage:
  unstick_stale_script.py <project_dir>                      # report only
  unstick_stale_script.py <project_dir> --fix                # do the recovery
  unstick_stale_script.py <project_dir> --fix --relaunch-booth
  unstick_stale_script.py <project_dir> --accept 3,7         # keep those takes
  unstick_stale_script.py <project_dir> --accept all
"""
import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from explainer2.project import Project                      # noqa: E402
from explainer2.media import scriptguard                    # noqa: E402

KILL_RENDER = REPO / "tools" / "kill_render.py"
LAUNCH_BOOTH = REPO / "tools" / "launch_booth.py"


def _free_name(path: Path):
    """A non-clobbering destination — recovery must never overwrite prior evidence."""
    if not path.exists():
        return path
    n = 2
    while True:
        cand = path.with_name(f"{path.stem}{n}{path.suffix}")
        if not cand.exists():
            return cand
        n += 1


def report(proj, rep):
    print(f"project: {proj.dir}")
    print(f"guard:   {'OK' if rep['ok'] else 'BLOCKED'} — {rep['reason']}\n")
    for row in rep["segments"]:
        if row["status"] in ("match", "exempt"):
            continue
        print(f"  segment {row['id']} [{row['status']}] slide={row.get('slide')} "
              f"({row['stem']}.wav)")
        if row["status"] == "stale":
            print(f"      recorded ({row.get('source')}): {row.get('recorded_text', '')[:120]}")
            print(f"      current  script.json     : {row.get('current_text', '')[:120]}")
    print()


def accept(proj, rep, ids):
    """Re-stamp the given segments' text records to the current script text."""
    stale = {r["id"]: r for r in rep["segments"] if r["status"] in ("stale", "unstamped")}
    if ids == ["all"]:
        ids = sorted(stale)
    else:
        ids = [int(i) for i in ids]
    done = []
    for sid in ids:
        row = stale.get(sid)
        if row is None:
            print(f"  segment {sid}: not stale or unstamped — skipped")
            continue
        scriptguard.stamp(proj.voiceover_dir, row["stem"], row["current_text"],
                          seg_id=sid, slide=row.get("slide"), source="operator-accepted")
        done.append(sid)
        print(f"  segment {sid}: accepted — audio kept, text record re-stamped")
    return done


def fix(proj, rep, relaunch=False):
    vdir = proj.voiceover_dir
    work = proj.work
    moved = []

    # 1. stale takes aside (audio + alternate takes preserved)
    for row in rep["segments"]:
        if row["status"] != "stale":
            continue
        wav = vdir / f"{row['stem']}.wav"
        if wav.exists():
            dst = _free_name(vdir / f"{row['stem']}.oldtext.bak")
            wav.rename(dst)
            moved.append(row["id"])
            print(f"  segment {row['id']}: {wav.name} -> {dst.name} (needs a re-record)")
        meta = scriptguard.meta_path(vdir, row["stem"])
        if meta.exists():
            meta.rename(_free_name(vdir / f"{row['stem']}.oldtext.meta.json"))

    # 2. the Finish signal — the watcher must not re-fire Phase 1 on it
    done = work / "record_done.json"
    if done.exists():
        dst = _free_name(work / "record_done.superseded.json")
        done.rename(dst)
        print(f"  work/record_done.json -> {dst.name} (watcher can't re-fire on it)")

    # 3. watcher bookkeeping
    for name in ("publish_lock.json", "render_attempts.json", "render_complete.json"):
        p = work / name
        if p.exists():
            p.unlink()
            print(f"  cleared work/{name}")

    # 4. mp4s built from the mismatched audio
    for mp4 in sorted(list((proj.dir / "video").glob("*.mp4")) + list(work.glob("video_*.mp4"))):
        mp4.unlink()
        print(f"  deleted {mp4.relative_to(proj.dir)} (built from mismatched audio)")

    # 5. stale render-lock note (only touched when the flock is genuinely free)
    subprocess.run([sys.executable, str(KILL_RENDER), "--lock-only", "--fix"])

    # 6. BLOCKED.md has served its purpose once the takes are gone
    if scriptguard.blocked_path(proj).exists():
        scriptguard.blocked_path(proj).unlink()
        print("  removed BLOCKED.md")

    if relaunch:
        print("\nrelaunching the booth…")
        subprocess.run([sys.executable, str(LAUNCH_BOOTH), str(proj.dir)])
    elif moved:
        print(f"\nRe-record segment(s) {moved} in the booth, then click Finish:")
        print(f"  python3 {LAUNCH_BOOTH} '{proj.dir}'")
    return moved


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_dir")
    ap.add_argument("--fix", action="store_true",
                    help="move the stale takes aside and clear the watcher's locks")
    ap.add_argument("--accept", default=None,
                    help="comma list of segment ids (or 'all') whose AUDIO is still "
                         "correct — re-stamps their text record instead of re-recording")
    ap.add_argument("--relaunch-booth", action="store_true", dest="relaunch",
                    help="with --fix: reopen the booth when done")
    args = ap.parse_args()

    proj = Project.load(args.project_dir)
    rep = scriptguard.check(proj)
    report(proj, rep)

    if args.accept:
        accept(proj, rep, [s.strip() for s in args.accept.split(",") if s.strip()])
        rep = scriptguard.check(proj)

    if args.fix:
        fix(proj, rep, relaunch=args.relaunch)
        rep = scriptguard.check(proj)

    if not (args.fix or args.accept):
        if not rep["ok"]:
            print("--fix to move the stale takes aside, or --accept <ids> to keep them")
        return 0 if rep["ok"] else 1

    final = scriptguard.check(proj)
    if final["ok"]:
        scriptguard.clear_blocked(proj)
        print(f"\nguard now OK — {final['reason']}")
        if final["not_recorded"]:
            print(f"(segments {final['not_recorded']} still need recording)")
        return 0
    print(f"\nguard still BLOCKED — {final['reason']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
