"""TIMELINE GUARD — refuse to render a video against a timeline built from
different audio than what is on disk right now.

THE BUG THIS EXISTS TO PREVENT (2026-08-12, Plan to Market promo)
-----------------------------------------------------------------
`explainer2 render <project>` launches `--only render,mux,manifest,qa`. It does
NOT run `align`. So after an operator re-records a card in the booth, calling
`render` builds the video against the PREVIOUS run's `work/timeline.json`.

Nothing errors. The render succeeds, the QA stage passes, `ready_for_post` comes
back true, and the mp4 is wrong: every slide boundary and caption cue after the
re-recorded card is offset by the difference in take length, and the tail of the
narration is cut off by however much longer the new audio is.

Caught by luck. The render announced the same frame count as the previous run
(3263f) while the new take was ~2.4s longer; the correct count after realigning
was 3335f. Had that not been noticed, the promo would have shipped desynced.

`scriptguard.py` does NOT catch this. It compares the *script text* against the
text each take was recorded from, and in this scenario those agree perfectly —
the operator recorded exactly the current words. What changed is the *audio*, and
nothing downstream was checking that the timeline still described it.

HOW IT WORKS
------------
`align` stamps `work/timeline_audio.json` with a fingerprint of the segment takes
it consumed (per-file size + mtime, which changes whenever the booth writes a new
take). Before any stage that reads the timeline, `enforce()` recomputes that
fingerprint from what is on disk and refuses if it differs.

The guard is deliberately silent when the run includes `align`, because that run
is about to rebuild the timeline and blocking it would be circular.

LEGACY PROJECTS: a project aligned before this module existed has no stamp. It
falls back to comparing mtimes (any take newer than `timeline.json` is stale).
That is weaker but still catches the real failure, and it never silently passes a
project it could not check — an unstamped project says so in the log.
"""
import hashlib
import json
import os
import time
from pathlib import Path

STAMP_NAME = "timeline_audio.json"

# Stages that read work/timeline.json. Rendering or packaging any of these
# against a stale timeline produces a wrong artifact rather than an error.
TIMELINE_CONSUMERS = {"deck", "render", "mux", "manifest", "qa"}

# mtime comparisons get a small grace window so that same-second writes during a
# single pipeline run (align writes the timeline, something touches a take) do
# not read as an edit. Mirrors scriptguard's tolerance for filesystem
# timestamp granularity.
MTIME_GRACE_S = 2.0


class StaleTimelineError(RuntimeError):
    def __init__(self, report):
        self.report = report
        super().__init__(report["reason"])


def stamp_path(proj):
    return proj.work / STAMP_NAME


def _script_segment_ids(proj):
    try:
        data = json.loads((proj.dir / "script.json").read_text())
    except Exception:
        return []
    return [s.get("id") for s in data.get("segments", []) if s.get("id") is not None]


def fingerprint(proj):
    """Describe the segment audio currently on disk.

    Size catches a different take (a different reading is a different length).
    mtime_ns catches the rare re-record that lands on an identical byte count.
    Both come from the take files the booth writes, NOT from work/narration.wav —
    narration.wav is written by `narrate`, so on a render-only run it is stale in
    exactly the same way the timeline is and would falsely agree with it.
    """
    files = []
    for sid in _script_segment_ids(proj):
        p = proj.voiceover_dir / f"seg_{sid:03d}.wav"
        if p.exists():
            st = p.stat()
            files.append({"stem": p.stem, "size": st.st_size, "mtime_ns": st.st_mtime_ns})
        else:
            files.append({"stem": p.stem, "size": None, "mtime_ns": None})
    blob = "\n".join(f"{f['stem']}:{f['size']}:{f['mtime_ns']}" for f in files)
    return {"digest": hashlib.sha256(blob.encode()).hexdigest(), "files": files}


def stamp(proj):
    """Record the audio `align` just consumed. Called at the end of align.run()."""
    fp = fingerprint(proj)
    fp["stamped_at"] = time.time()
    proj.write_json(stamp_path(proj), fp)
    return fp


def _newest_take_mtime(proj):
    newest = 0.0
    for sid in _script_segment_ids(proj):
        p = proj.voiceover_dir / f"seg_{sid:03d}.wav"
        if p.exists():
            newest = max(newest, p.stat().st_mtime)
    return newest


def check(proj):
    """Return a report on whether work/timeline.json still describes the audio."""
    tl = proj.work / "timeline.json"
    if not tl.exists():
        return {"ok": True, "state": "no_timeline",
                "reason": "no timeline.json yet — nothing to be stale against"}

    sp = stamp_path(proj)
    if not sp.exists():
        # Legacy project: aligned before this guard existed. Fall back to mtimes.
        newest = _newest_take_mtime(proj)
        if newest and newest > tl.stat().st_mtime + MTIME_GRACE_S:
            return {"ok": False, "state": "stale_by_mtime", "changed": [],
                    "reason": ("a recorded take is newer than timeline.json, so the timeline "
                               "was built from different audio (this project predates the "
                               "timeline stamp, so the check is by timestamp)")}
        return {"ok": True, "state": "unstamped",
                "reason": ("timeline.json has no audio stamp (aligned before the timeline "
                           "guard existed); timestamps look consistent but this run could "
                           "not be proven current — the next align will stamp it")}

    try:
        recorded = json.loads(sp.read_text())
    except Exception as e:
        return {"ok": True, "state": "unreadable_stamp",
                "reason": f"could not read {STAMP_NAME} ({e}); not blocking on it"}

    current = fingerprint(proj)
    if current["digest"] == recorded.get("digest"):
        return {"ok": True, "state": "match",
                "reason": "timeline.json was built from the audio currently on disk"}

    was = {f["stem"]: (f["size"], f["mtime_ns"]) for f in recorded.get("files", [])}
    changed = []
    for f in current["files"]:
        before = was.get(f["stem"])
        now = (f["size"], f["mtime_ns"])
        if before is None:
            changed.append({"stem": f["stem"], "what": "new segment, not in the aligned set"})
        elif before != now:
            if before[0] != now[0]:
                delta = (now[0] or 0) - (before[0] or 0)
                changed.append({"stem": f["stem"],
                                "what": f"re-recorded ({delta:+d} bytes of audio)"})
            else:
                changed.append({"stem": f["stem"], "what": "re-recorded (same length)"})
    for stem in was:
        if stem not in {f["stem"] for f in current["files"]}:
            changed.append({"stem": stem, "what": "take removed since align"})

    n = len(changed)
    return {"ok": False, "state": "stale", "changed": changed,
            "reason": (f"{n} segment take{'s' if n != 1 else ''} changed since the last align, "
                       f"so timeline.json describes different audio than what will be rendered")}


# ---------------------------------------------------------------- enforcement

def allow_override(flag=False):
    return bool(flag) or os.environ.get("EXPLAINER_ALLOW_STALE_TIMELINE", "") == "1"


def applies_to(only):
    """Does this run touch a stage that reads the timeline, without rebuilding it?

    `only` is the parsed --only set, or None for a full pipeline run. A full run
    includes align, so it is always fine.
    """
    if not only:
        return False
    if "align" in only:
        return False  # this run is rebuilding the timeline; nothing to guard
    return bool(set(only) & TIMELINE_CONSUMERS)


def _blocked_text(proj, report):
    L = [f"# BLOCKED: timeline is stale ({proj.dir.name})", "",
         f"**{report['reason']}**", "",
         "Rendering now would produce a video whose slide boundaries and captions",
         "drift out of sync with the narration, and whose tail is cut off if the new",
         "audio is longer. The render would NOT fail — it would succeed and be wrong.", ""]
    if report.get("changed"):
        L += ["## What changed since the last align", ""]
        L += [f"- `{c['stem']}` — {c['what']}" for c in report["changed"]]
        L += [""]
    L += ["## Fix", "",
          "Rebuild the timeline from the current audio, then render:", "",
          "```bash",
          f"/Volumes/Casima/claudeCode/explainer2/bin/explainer2 media '{proj.dir}' --only narrate,align",
          f"/Volumes/Casima/claudeCode/explainer2/bin/explainer2 render '{proj.dir}'",
          "```", "",
          "`render` alone is not enough: it runs only render,mux,manifest,qa and",
          "never re-aligns. That is the whole reason this guard exists.", "",
          "## Override (you almost never want this)", "",
          "```bash",
          f"EXPLAINER_ALLOW_STALE_TIMELINE=1 /Volumes/Casima/claudeCode/explainer2/bin/explainer2 render '{proj.dir}'",
          "```", ""]
    return "\n".join(L)


def enforce(proj, only=None, log=print, allow_stale=False):
    """Raise StaleTimelineError if this run would read a timeline built from
    different audio. No-op when the run rebuilds the timeline itself."""
    if not applies_to(only):
        return None
    report = check(proj)
    if report["ok"]:
        if report["state"] in ("unstamped", "unreadable_stamp"):
            log(f"timeline-guard: {report['reason']}")
        return report
    if allow_override(allow_stale):
        log(f"timeline-guard: OVERRIDDEN — rendering anyway. {report['reason']}")
        report["overridden"] = True
        return report
    p = Path(proj.dir) / "BLOCKED-TIMELINE.md"
    p.write_text(_blocked_text(proj, report))
    log(f"timeline-guard: BLOCKED — {report['reason']}")
    for c in report.get("changed", []):
        log(f"timeline-guard:   {c['stem']} — {c['what']}")
    log(f"timeline-guard: wrote {p.name} — refusing to render (run align first)")
    raise StaleTimelineError(report)


def clear_blocked(proj):
    p = Path(proj.dir) / "BLOCKED-TIMELINE.md"
    existed = p.exists()
    p.unlink(missing_ok=True)
    return existed
