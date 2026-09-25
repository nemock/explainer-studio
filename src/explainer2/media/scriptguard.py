"""SCRIPT/AUDIO STALENESS GUARD — refuse to render when script.json changed after
the operator recorded it.

The failure this exists to prevent (2026-08-10, monday-medtech-weekly, near-miss):

    09:38  voiceover/seg_000.wav recorded  ("A company you've probably never heard of…")
    09:40  voiceover/seg_007.wav recorded  ("So think about that for a second. …")
    09:43  operator clicks Finish -> work/record_done.json
    09:45  script.json EDITED — the agent removed those two phrases at the
           operator's request
    09:48  the launchd recording watcher starts Phase 1 -> `explainer2 media`
    09:48  narrate OK (13 segments) …  align OK, 395 words   <-- NO ERROR

Forced alignment does not fail on a text/audio mismatch. It silently mismaps: it
aligned the NEW script text against the OLD audio, produced clean-looking
timings, and the episode would have published with narration saying two lines the
operator had explicitly asked to remove. Nothing stopped it but a human noticing
the render and killing it by hand.

So: check before rendering, and REFUSE. Not warn — a warning in run.log is
exactly what nobody reads on an unattended run, and the watcher's Phase 2
publishes on its own the moment Phase 1 writes render_complete.json.

Two layers, cheap first:

1. mtime — script.json newer than the newest recorded segment wav. Catches the
   incident exactly, costs a stat() per file, and false-positives on a no-op
   touch or a reformat, so it never blocks on its own.
2. per-segment content hash — the real check. The booth stamps
   `voiceover/<stem>.meta.json` with a hash of the card's text every time it
   saves a take; here we re-hash the segment's CURRENT script.json text and
   compare. This identifies WHICH segments are stale, which is what makes the
   failure actionable (re-record two cards, not the whole session).

Where the "recorded text" comes from, in order of authority:

  meta      voiceover/<stem>.meta.json — written by the booth at save time.
            Exact: the text as the teleprompter showed it for that take.
  adlib     work/adlib_report.json rows carry `script_text` as it read when the
            booth wrote the report (at Finish). Only trusted for segments whose
            wav is OLDER than the report — a take recorded after the report was
            written is not described by it. This is what lets the guard catch
            the 2026-08-10 incident on projects recorded before meta stamping
            existed, and it is verified against that project's own artifacts.
  (none)    unstamped. Falls through to the mtime layer.

Segments carrying `adlib_applied` (set by `explainer2 adlib --apply`, which
rewrites script text to match what was actually SPOKEN) are exempt: there the
text was deliberately conformed to the audio, which is the opposite of this bug.

Shorts hook/outro takes (`voiceover/short_<slug>_{hook,outro}.wav`) get the same
content-hash check against shorts/plan.json (2026-09-25, `_check_shorts`). Their rows
carry `kind: "short"` and their booth card id, and a stale one blocks like a segment.

Escape hatch, because a guard that cannot be turned off is its own outage:
`--allow-stale-script` on the CLI, or EXPLAINER_ALLOW_STALE_SCRIPT=1. Both log
loudly. The supported fix is `tools/unstick_stale_script.py`, which moves the
stale takes aside so the booth asks for them again.
"""
import hashlib
import json
import os
import time
from pathlib import Path

BLOCKED_NAME = "BLOCKED.md"
META_SUFFIX = ".meta.json"

# script.json is rewritten by the booth's inline edit and by adlib --apply, both of
# which touch it legitimately mid-session; a couple of seconds of slack keeps
# filesystem timestamp granularity and a same-second save from reading as an edit.
MTIME_SLACK_S = 2.0


class StaleScriptError(RuntimeError):
    """Raised by enforce() when the recorded audio does not match script.json."""

    def __init__(self, report):
        self.report = report
        super().__init__(report["reason"])


# ---------------------------------------------------------------- hashing / meta

def norm_text(text):
    """Whitespace-normalized text — what actually gets spoken.

    Collapsing runs of whitespace means a reflow or a trailing-space save is not
    a mismatch, while any change to the words is."""
    return " ".join((text or "").split())


def text_hash(text):
    return hashlib.sha256(norm_text(text).encode("utf-8")).hexdigest()


def script_digest(segments):
    """One hash over every segment's id + spoken text.

    Written into work/record_done.json when the operator clicks Finish, and
    recomputed here. Equal digests prove the SPOKEN CONTENT of the script has not
    changed since Finish — which is what makes the mtime layer safe: a no-op
    touch, a reindent, or a reflow moves the mtime but not this."""
    payload = [[s.get("id"), norm_text(s.get("text"))] for s in segments]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def meta_path(vdir, stem):
    return Path(vdir) / f"{stem}{META_SUFFIX}"


def stamp(vdir, stem, text, seg_id=None, slide=None, source="booth"):
    """Record the text a take was recorded against, beside its wav.

    Called by the booth on every successful /save (and as a Finish-time backfill
    for takes whose ASR drift confirms they match the current text)."""
    p = meta_path(vdir, stem)
    p.write_text(json.dumps({
        "id": seg_id, "slide": slide, "stem": stem,
        "text": norm_text(text), "text_sha256": text_hash(text),
        "recorded_at": time.time(), "source": source,
    }, indent=2, ensure_ascii=False) + "\n")
    return p


def read_meta(vdir, stem):
    try:
        return json.loads(meta_path(vdir, stem).read_text())
    except (OSError, ValueError):
        return None


def move_meta(vdir, stem, new_stem):
    """Follow a wav rename (archive_take / promote_take) so a take's text record
    never ends up attached to a different take's audio."""
    src, dst = meta_path(vdir, stem), meta_path(vdir, new_stem)
    if src.exists():
        src.replace(dst)
        return dst
    return None


def drop_meta(vdir, stem):
    meta_path(vdir, stem).unlink(missing_ok=True)


# ---------------------------------------------------------------- the check

def _adlib_recorded_text(proj):
    """{seg_id: text} from work/adlib_report.json, plus the report's mtime.

    The report's `script_text` is the script as it read when the booth wrote the
    report. A wav recorded AFTER that is not described by it, so the caller
    gates each lookup on the wav's mtime."""
    p = proj.work / "adlib_report.json"
    try:
        rep = json.loads(p.read_text())
        mtime = p.stat().st_mtime
    except (OSError, ValueError):
        return {}, None
    out = {}
    for row in rep.get("segments", []):
        if row.get("script_text") is not None and row.get("id") is not None:
            out[row["id"]] = row["script_text"]
    return out, mtime


def check(proj):
    """Compare every recorded segment's audio against script.json's current text.

    Returns a report dict; `ok` False means: do not render."""
    from .common import effective_segments
    from .voiceover import seg_path

    report = {
        "ok": True, "reason": "", "voice_source": proj.voice_source,
        "checked_at": time.time(), "segments": [],
        "stale": [], "unstamped": [], "not_recorded": [], "exempt": [],
        "mtime_suspect": False, "script_mtime": None, "newest_audio_mtime": None,
        "script_unchanged_since_finish": False,
    }

    if proj.voice_source != "operator":
        # Kokoro re-synthesizes from script.json on every narrate, so the audio
        # cannot disagree with the script.
        report["reason"] = "kokoro voice — audio is regenerated from the script every run"
        return report

    script = json.loads(proj.script_json.read_text())
    segments = effective_segments(proj, script)
    applied = {s.get("id") for s in script.get("segments", []) if s.get("adlib_applied")}
    adlib_text, adlib_mtime = _adlib_recorded_text(proj)

    try:
        report["script_mtime"] = proj.script_json.stat().st_mtime
    except OSError:
        pass

    # Did the booth's Finish record a digest, and does it still match? If so the
    # spoken content is untouched since the operator finished, whatever the mtime
    # says — that is what keeps a no-op touch or a reformat from blocking.
    try:
        finish = json.loads((proj.work / "record_done.json").read_text())
    except (OSError, ValueError):
        finish = {}
    if finish.get("script_digest"):
        report["script_unchanged_since_finish"] = (
            finish["script_digest"] == script_digest(segments))

    newest_audio = None
    for seg in segments:
        sid = seg["id"]
        stem = f"seg_{sid:03d}"
        wav = seg_path(proj, sid)
        row = {"id": sid, "slide": seg.get("slide"), "stem": stem,
               "current_text": norm_text(seg.get("text"))}
        if not wav.exists():
            row["status"] = "not_recorded"
            report["not_recorded"].append(sid)
            report["segments"].append(row)
            continue
        wav_mtime = wav.stat().st_mtime
        row["audio_mtime"] = wav_mtime
        newest_audio = wav_mtime if newest_audio is None else max(newest_audio, wav_mtime)

        if sid in applied:
            # adlib --apply rewrote this text FROM the audio; they agree by construction.
            row["status"] = "exempt"
            row["source"] = "adlib_applied"
            report["exempt"].append(sid)
            report["segments"].append(row)
            continue

        meta = read_meta(proj.voiceover_dir, stem)
        recorded_text = source = None
        if meta and meta.get("text_sha256"):
            recorded_text, source = meta.get("text", ""), f"meta:{meta.get('source', 'booth')}"
        elif sid in adlib_text and adlib_mtime is not None and wav_mtime <= adlib_mtime:
            recorded_text, source = adlib_text[sid], "adlib_report"

        if recorded_text is None:
            row["status"] = "unstamped"
            report["unstamped"].append(sid)
        elif text_hash(recorded_text) == text_hash(row["current_text"]):
            row["status"] = "match"
            row["source"] = source
        else:
            row["status"] = "stale"
            row["source"] = source
            row["recorded_text"] = norm_text(recorded_text)
            report["stale"].append(sid)
        report["segments"].append(row)

    # The mtime layer is about script.json, so it weighs long-form segments only.
    seg_unstamped = list(report["unstamped"])
    _check_shorts(proj, report)

    report["newest_audio_mtime"] = newest_audio
    if report["script_mtime"] and newest_audio:
        report["mtime_suspect"] = report["script_mtime"] > newest_audio + MTIME_SLACK_S

    if report["stale"]:
        report["ok"] = False
        report["reason"] = (
            f"{len(report['stale'])} card(s) were recorded against different text than "
            f"script.json / shorts/plan.json now says: {report['stale']}")
    elif (report["mtime_suspect"] and seg_unstamped
            and not report["script_unchanged_since_finish"]):
        report["ok"] = False
        report["reason"] = (
            f"script.json was modified after the last recording "
            f"({_ago(report['script_mtime'], newest_audio)}) and {len(seg_unstamped)} "
            f"recorded segment(s) carry no recorded-text record to check against: "
            f"{seg_unstamped}")
    elif report["mtime_suspect"]:
        report["reason"] = (
            "script.json is newer than the audio, but its spoken content is unchanged "
            "(every stamped segment matches"
            + (", and the Finish digest still matches" if report["script_unchanged_since_finish"] else "")
            + ") — a reformat or a no-op save, not a content change")
    else:
        report["reason"] = "audio matches script.json" + (
            " and shorts/plan.json" if any(r.get("kind") == "short" for r in report["segments"])
            else "")
    return report


def _check_shorts(proj, report):
    """Shorts hook/outro takes against shorts/plan.json (2026-09-25).

    The booth records each cut's hook and outro as `voiceover/short_<slug>_<role>.wav`
    and stamps them exactly like segments, but the text lives in shorts/plan.json, not
    script.json, and nothing read those stamps. On 2026-09-25 (#69) a hook was rewritten
    after Finish and the `shorts` stage would have rendered the old hook audio under the
    new hook captions.

    Card ids and stems come from the booth's own card builder, so `--accept 40` means
    the card the booth shows as "Card 41". Only a stamped take can be stale; an
    unstamped one is reported but does not block. Unstamped Short takes come from
    projects recorded before stamping began (2026-08-10), which have already shipped,
    and the mtime layer is about script.json."""
    from ..recorder import _load_segments
    try:
        cards, _ = _load_segments(proj)
    except (OSError, ValueError, KeyError):
        return
    for card in cards:
        if not card.get("plan_slug"):
            continue
        stem = card["clip"]
        row = {"id": card["id"], "kind": "short", "slide": card.get("slide"), "stem": stem,
               "plan_slug": card["plan_slug"], "plan_role": card["plan_role"],
               "current_text": norm_text(card.get("text"))}
        wav = Path(proj.voiceover_dir) / f"{stem}.wav"
        if not wav.exists():
            row["status"] = "not_recorded"
            report["not_recorded"].append(card["id"])
            report["segments"].append(row)
            continue
        row["audio_mtime"] = wav.stat().st_mtime
        meta = read_meta(proj.voiceover_dir, stem)
        if not (meta and meta.get("text_sha256")):
            row["status"] = "unstamped"
            report["unstamped"].append(card["id"])
        elif text_hash(meta.get("text", "")) == text_hash(row["current_text"]):
            row["status"] = "match"
            row["source"] = f"meta:{meta.get('source', 'booth')}"
        else:
            row["status"] = "stale"
            row["source"] = f"meta:{meta.get('source', 'booth')}"
            row["recorded_text"] = norm_text(meta.get("text", ""))
            report["stale"].append(card["id"])
        report["segments"].append(row)


def _ago(newer, older):
    try:
        d = int(newer - older)
    except (TypeError, ValueError):
        return "?"
    return f"{d // 60}m{d % 60:02d}s later" if d >= 60 else f"{d}s later"


def _stamp_line(ts):
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
    except (TypeError, ValueError):
        return "?"


# ---------------------------------------------------------------- BLOCKED.md

def blocked_path(proj):
    return proj.dir / BLOCKED_NAME


def write_blocked(proj, report):
    """Name the specific stale segments and both texts, then leave the file where
    the operator (and the next agent to open this project) will see it."""
    L = [f"# BLOCKED — {proj.dir.name}", "",
         f"`explainer2` refused to render at {_stamp_line(report['checked_at'])}.", "",
         f"**{report['reason']}**", "",
         "The recorded narration does not say what `script.json` (or, for a Short card,",
         "`shorts/plan.json`) now says. Forced",
         "alignment does not fail on a mismatch — it silently mismaps the new text onto",
         "the old audio and the episode publishes saying the old words. See",
         "`src/explainer2/media/scriptguard.py` for the incident this guard came from.", ""]

    if report["script_mtime"] and report["newest_audio_mtime"]:
        L += ["| | |", "|---|---|",
              f"| newest recording | {_stamp_line(report['newest_audio_mtime'])} |",
              f"| `script.json` edited | {_stamp_line(report['script_mtime'])} |", ""]

    stale_rows = [r for r in report["segments"] if r["status"] == "stale"]
    if stale_rows:
        L += ["## Stale cards", ""]
        for r in stale_rows:
            if r.get("kind") == "short":
                head = (f"### Short card {r['id']} (booth Card {r['id'] + 1}, `{r.get('slide')}`, "
                        f"`voiceover/{r['stem']}.wav`)")
                src = f"`shorts/plan.json` `{r['plan_slug']}.{r['plan_role']}`"
            else:
                head = f"### segment {r['id']} (slide `{r.get('slide')}`, `voiceover/{r['stem']}.wav`)"
                src = "`script.json`"
            L += [head, "",
                  f"Recorded text (source: `{r.get('source')}`) — this is what the audio says:", "",
                  "```", r.get("recorded_text", ""), "```", "",
                  f"Current {src} text — this is what the video would claim:", "",
                  "```", r.get("current_text", ""), "```", ""]

    if report["unstamped"] and not report["ok"] and not stale_rows:
        L += ["## Unverifiable segments", "",
              "These segments are recorded but carry no record of the text they were",
              "recorded against (no `voiceover/<stem>.meta.json`, and `work/adlib_report.json`",
              "predates their audio or is missing), so the guard cannot prove they are current:", "",
              *[f"- segment {r['id']}" for r in report["segments"]
                if r["status"] == "unstamped" and r.get("kind") != "short"], ""]

    L += ["## Recovery", "",
          "Move the stale takes aside so the booth asks for them again (the audio is",
          "preserved as `<stem>.oldtext.bak`; a Short card's old-text alternate takes move",
          "aside with it), clear the watcher's locks, and relaunch the booth:", "",
          "```bash",
          f"python3 /Volumes/Casima/claudeCode/explainer2/tools/unstick_stale_script.py "
          f"'{proj.dir}' --fix --relaunch-booth",
          "```", "",
          "If the audio is genuinely still correct and only the wording of the script was",
          "reformatted (numerals spelled out, punctuation), accept it instead of re-recording:", "",
          "```bash",
          f"python3 /Volumes/Casima/claudeCode/explainer2/tools/unstick_stale_script.py "
          f"'{proj.dir}' --accept {','.join(str(i) for i in report['stale']) or 'all'}",
          "```", "",
          "Then re-check (this deletes this file when it passes):", "",
          "```bash",
          f"/Volumes/Casima/claudeCode/explainer2/bin/explainer2 media '{proj.dir}' --recheck",
          "```", ""]

    p = blocked_path(proj)
    p.write_text("\n".join(L))
    proj.write_json(proj.work / "script_guard.json", report)
    return p


def clear_blocked(proj):
    """Remove a BLOCKED.md left by an earlier run once the project checks clean —
    otherwise a resolved block would sit there forever looking unresolved."""
    p = blocked_path(proj)
    existed = p.exists()
    p.unlink(missing_ok=True)
    return existed


# ---------------------------------------------------------------- enforcement

def allow_override(flag=False):
    return bool(flag) or os.environ.get("EXPLAINER_ALLOW_STALE_SCRIPT", "") == "1"


def enforce(proj, log=print, allow_stale=False):
    """Run the check and raise StaleScriptError unless it passes (or is overridden).

    Returns the report on success."""
    report = check(proj)
    if report["ok"]:
        if clear_blocked(proj):
            log("script-guard: previous BLOCKED.md cleared — audio and script.json agree")
        if report["mtime_suspect"]:
            log(f"script-guard: {report['reason']}")
        return report
    if allow_override(allow_stale):
        log(f"script-guard: OVERRIDDEN — rendering anyway. {report['reason']}")
        report["overridden"] = True
        proj.write_json(proj.work / "script_guard.json", report)
        return report
    path = write_blocked(proj, report)
    log(f"script-guard: BLOCKED — {report['reason']}")
    log(f"script-guard: wrote {path.name} — refusing to render (nothing downstream will run)")
    raise StaleScriptError(report)
