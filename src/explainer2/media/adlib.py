"""AD-LIB CHECK (PRD §5.3) — did the operator say what the script says?

Transcribes each recorded segment locally (mlx-whisper, Metal) and word-diffs it
against the script text:

  drift < 2%   verbatim — keep the script text (cleanest captions)
  over 2%      ad-lib   — captions should follow what was actually said;
                          --apply rewrites that segment's text from the ASR
  rerecord     only when the transcript shows the script's words are not in the take
               (rerecord_confirmed). Drift alone never asks the operator to go back to
               the mic: "rerecord" holds the render and texts his phone.
  approved     the operator ticked "Approve take" in the booth for this exact take
               (work/take_approvals.json): his ear outranks the transcript, so it is
               never a re-record and never --apply'd (2026-11-25).

Report → work/adlib_report.json. --apply backs up script.json to
script.orig.json before touching it. Forced alignment downstream works with
either text, so this stage is advisory — it never blocks the pipeline.

Transcripts → work/drift_transcripts.json, one per take, keyed by stem and the wav's
identity. The booth starts empty on a relaunch and writes the whole report at Finish, so
without this a re-record of one card followed by a quick Finish reported every card
`unchecked`, erased the first pass and left nothing holding the render (#81, 2026-11-03).
A transcript is stored rather than a verdict: the verdict is recomputed from the card's
current text, so an edit between sessions cannot leave a stale one behind.
"""
import difflib
import json
import os
import re
import time
from pathlib import Path

MODEL = "mlx-community/whisper-medium.en-mlx"
TRANSCRIPTS = "drift_transcripts.json"
MINOR = 0.02
MAJOR = 0.15
# A re-record is confirmed by words missing from the take, never by drift alone. Operator,
# 2026-11-03: "I should not be alerted to re-record a card until it is verified as
# necessary." Of the 93 cards the catalog's 295 reports held at or over MAJOR, these two
# rules keep only the takes that really lost their words (tools/test_adlib_flags.py).
MISSING_RUN_WORDS = 8       # a contiguous run of script words absent from the transcript...
MISSING_RUN_SHARE = 1 / 3   # ...that is at least this share of the card (a cut-off take)
MIN_MATCH_SHARE = 0.4       # or too little of the card matched at all (a wrong card)
MIN_MATCH_WORDS = 4         # too few words to judge below this ("Expired." / "All expired.")


_ONES = ("zero one two three four five six seven eight nine ten eleven twelve "
         "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = "zero ten twenty thirty forty fifty sixty seventy eighty ninety".split()


def _num_words(n):
    """Digits → words so '500' diffs equal to 'five hundred' (whisper writes
    numerals; scripts spell numbers out). Wrong numbers still surface as drift."""
    if n < 20:
        return _ONES[n]
    if n < 100:
        t, r = divmod(n, 10)
        return _TENS[t] + ((" " + _ONES[r]) if r else "")
    if n < 1000:
        h, r = divmod(n, 100)
        return _ONES[h] + " hundred" + ((" " + _num_words(r)) if r else "")
    if n < 1_000_000:
        th, r = divmod(n, 1000)
        return _num_words(th) + " thousand" + ((" " + _num_words(r)) if r else "")
    if n < 1_000_000_000:
        m, r = divmod(n, 1_000_000)
        return _num_words(m) + " million" + ((" " + _num_words(r)) if r else "")
    return str(n)


def _norm_words(text):
    # Apostrophes are never audible, so they can't be drift: "Meridian's" transcribed as
    # "meridians" scored 0.33 on a three-word card and flagged a clean take for
    # re-record (2026-09-23), which parks the watcher's render. Deleted, not spaced,
    # so contractions stay one token; the curly form goes too.
    text = text.lower().replace("'", "").replace("’", "").replace("%", " percent ")
    # 1,234,567 → 1234567, but digits read one at a time stay apart: "1,2,3,4,5,6,7" came
    # out as 12 34 56 7 and scored a clean take at 16% drift (#81 card 11, 2026-11-03).
    text = re.sub(r"(?<![\d,])\d{1,3}(?:,\d{3})+(?![\d,])",
                  lambda m: m.group().replace(",", ""), text)
    text = re.sub(r"[^a-z0-9' ]", " ", text)
    out = []
    for tok in text.split():
        if tok.isdigit():
            out.extend(_num_words(int(tok)).split())
        else:
            out.append(tok)
    return out


def _spell_numbers(text):
    """ASR writes digits ('100', '30-day', '5%'); the pipeline invariant is
    spelled-out numbers (the aligner drops non-letter tokens, which would erase
    numbers from the kinetic captions). Convert before applying ASR text."""
    text = re.sub(r"(\d),(\d)", r"\1\2", text)
    text = re.sub(r"(\d+)\s*%", r"\1 percent", text)
    return re.sub(r"\d+", lambda m: _num_words(int(m.group())), text)


def _drift(script_text, asr_text):
    a, b = _norm_words(script_text), _norm_words(asr_text)
    if not a and not b:
        return 0.0
    return round(1.0 - difflib.SequenceMatcher(None, a, b).ratio(), 4)


def rerecord_confirmed(script_text, asr_text):
    """(True, why) when the transcript shows the take does not hold the card's words.

    Drift is the wrong evidence for this: spoken initialisms ("F-D-A" / "FDA"), contractions,
    decimals and misheard names all score high against a clean take. Missing words are what
    a re-record fixes, and a recognizer that mishears a word still leaves the words around it."""
    a, b = _norm_words(script_text), _norm_words(asr_text)
    if not a:
        return False, ""
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    run = max((i2 - i1 for tag, i1, i2, _, _ in matcher.get_opcodes()
               if tag in ("delete", "replace")), default=0)
    matched = sum(m.size for m in matcher.get_matching_blocks())
    if run >= MISSING_RUN_WORDS and run >= MISSING_RUN_SHARE * len(a):
        return True, f"{run} of {len(a)} script words in a row are not in the take"
    if len(a) >= MIN_MATCH_WORDS and matched < MIN_MATCH_SHARE * len(a):
        return True, f"only {matched} of {len(a)} script words are in the take"
    return False, ""


def classify(drift, script_text, asr_text):
    """verbatim / adlib / rerecord: the one place a card earns the re-record flag."""
    if drift < MINOR:
        return "verbatim"
    if drift >= MAJOR and rerecord_confirmed(script_text, asr_text)[0]:
        return "rerecord"
    return "adlib"


def take_sig(wav):
    """What makes a recording THIS take: nanosecond mtime and size, or None if it is gone."""
    try:
        st = Path(wav).stat()
    except OSError:
        return None
    return [st.st_mtime_ns, st.st_size]


APPROVALS = "take_approvals.json"


def load_approvals(work):
    """{stem: {"sig": [...], "at": ts}} — takes the operator approved in the booth.

    Operator, 2026-11-25: "There have been a couple times where the voice dictation didn't
    quite understand me, but it turned out I did record it correctly." An approval is his
    ruling that THIS take says the card, whatever a transcript heard. It is keyed to the
    take's identity, so a new take (or a promoted older one) is unapproved until he says
    otherwise."""
    try:
        data = json.loads((Path(work) / APPROVALS).read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def is_approved(work, wav, approvals=None):
    entry = (load_approvals(work) if approvals is None else approvals).get(Path(wav).stem)
    sig = take_sig(wav)
    return bool(isinstance(entry, dict) and sig and entry.get("sig") == sig)


def set_approval(work, wav, on):
    """Approve (on=True) or withdraw approval of the take on disk now. False if no take."""
    sig = take_sig(wav)
    if on and not sig:
        return False
    path = Path(work) / APPROVALS
    data = load_approvals(work)
    if on:
        data[Path(wav).stem] = {"sig": sig, "at": time.time()}
    else:
        data.pop(Path(wav).stem, None)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)
    return True


def load_transcripts(work):
    try:
        data = json.loads((Path(work) / TRANSCRIPTS).read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def saved_transcript(transcripts, wav):
    """The stored transcript if it describes the take on disk now, else None."""
    entry = transcripts.get(Path(wav).stem)
    sig = take_sig(wav)
    if not (isinstance(entry, dict) and sig and entry.get("sig") == sig):
        return None
    return entry.get("asr_text")


def save_transcript(work, wav, sig, asr):
    """Keep one take's transcript. Bookkeeping: a failure here costs a re-transcribe later,
    so it must never break a recording session."""
    path = Path(work) / TRANSCRIPTS
    try:
        data = load_transcripts(work)
        data[Path(wav).stem] = {"sig": sig, "asr_text": asr}
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        os.replace(tmp, path)
    except OSError:
        pass


def run_unchecked(proj, model=MODEL):
    """Check only the takes the report has no verdict for, and fill them in.

    The render pipeline's first step (phase1_render --profile studio), for cards still
    `unchecked` at Finish: a take finished seconds before the button, or a whisper that
    deferred behind a render. Rows that already hold a verdict for the take on disk are left
    exactly as they are, so nothing checked is transcribed again and a clean report is not
    rewritten. A take whisper cannot read stays `unchecked`; only words missing from a real
    transcript can flag a card, because a flag holds the render and texts the operator."""
    from .. import renderlock
    from ..recorder import DRIFT_TIMEOUT_S, _load_segments, _transcribe_isolated
    from . import scriptguard

    path = proj.work / "adlib_report.json"
    try:
        report = json.loads(path.read_text())
        written = path.stat().st_mtime_ns
    except (OSError, ValueError):
        report, written = {}, 0
    old = {r.get("id"): r for r in report.get("segments", [])}
    vdir = proj.voiceover_dir
    segs, stem = _load_segments(proj)
    saved = load_transcripts(proj.work)

    def row_for(seg, wav, asr):
        d = _drift(seg["text"], asr)
        status = "approved" if is_approved(proj.work, wav) else classify(d, seg["text"], asr)
        row = {"id": seg["id"], "status": status, "drift": d, "asr_text": asr}
        # scriptguard reads a row's script_text as what the take was recorded against, for
        # takes with no text stamp. This runs after Finish and would only be repeating the
        # script back to it, so an unstamped take does not get to vouch for itself here.
        if scriptguard.read_meta(vdir, wav.stem):
            row["script_text"] = seg["text"]
        return row

    rows, todo = [], []
    for seg in segs:
        sid = seg["id"]
        wav = vdir / f"{stem[sid]}.wav"
        prev = old.get(sid) or {}
        sig = take_sig(wav)
        if not sig:
            rows.append({"id": sid, "status": "not_recorded"})
        elif prev.get("status") not in (None, "unchecked", "not_recorded") and sig[0] <= written:
            rows.append(prev)
        elif saved_transcript(saved, wav) is not None:
            rows.append(row_for(seg, wav, saved_transcript(saved, wav)))
        else:
            todo.append((len(rows), seg, wav))
            rows.append({"id": sid, "status": "unchecked"})

    lock = renderlock.acquire(proj) if todo else None
    try:
        for i, seg, wav in todo:
            sig = take_sig(wav)
            try:
                asr = _transcribe_isolated(str(wav), model, DRIFT_TIMEOUT_S)
            except Exception as e:                       # noqa: BLE001 - includes a timeout
                print(f"adlib: card {seg['id'] + 1} stays unchecked: {str(e)[:200]}", flush=True)
                continue
            save_transcript(proj.work, wav, sig, asr)
            rows[i] = row_for(seg, wav, asr)
    finally:
        renderlock.release(lock)

    unchecked = [r["id"] for r in rows if r["status"] == "unchecked"]
    flagged = [r["id"] for r in rows if r["status"] == "rerecord"]
    filled = {**report, "model": report.get("model", model), "segments": rows,
              "worst_drift": max((r.get("drift", 0.0) for r in rows), default=0.0),
              "rerecord": flagged, "unchecked": unchecked,
              "applied": report.get("applied", [])}
    if filled != report:
        proj.write_json(path, filled)
    return {"transcribed": len(todo) - sum(1 for i, _, _ in todo if rows[i]["status"] == "unchecked"),
            "unchecked": unchecked, "rerecord": flagged, "report": "work/adlib_report.json"}


def run(proj, apply=False, model=MODEL):
    import mlx_whisper
    from .common import effective_segments
    from .voiceover import seg_path

    script = json.loads(proj.script_json.read_text())
    segments = effective_segments(proj, script)
    by_id = {s["id"]: s for s in script["segments"]}

    rows, worst = [], 0.0
    # 2026-10-01: the mlx-whisper transcription loop takes the render lock (was unlocked).
    from .. import renderlock
    lock = renderlock.acquire(proj)
    try:
        for seg in segments:
            wav = seg_path(proj, seg["id"])
            if not wav.exists():
                rows.append({"id": seg["id"], "status": "not_recorded"})
                continue
            sig = take_sig(wav)
            asr = mlx_whisper.transcribe(str(wav), path_or_hf_repo=model)["text"].strip()
            save_transcript(proj.work, wav, sig, asr)
            d = _drift(seg["text"], asr)
            worst = max(worst, d)
            status = ("approved" if is_approved(proj.work, wav)
                      else classify(d, seg["text"], asr))
            rows.append({"id": seg["id"], "status": status, "drift": d,
                         "script_text": seg["text"], "asr_text": asr})
            if apply and status == "adlib" and seg["id"] in by_id:
                by_id[seg["id"]]["text"] = _spell_numbers(asr)
                by_id[seg["id"]]["adlib_applied"] = True
    finally:
        renderlock.release(lock)

    flagged = [r["id"] for r in rows if r.get("status") == "rerecord"]
    applied = [r["id"] for r in rows if r.get("status") == "adlib"] if apply else []
    if apply and applied:
        backup = proj.dir / "script.orig.json"
        if not backup.exists():
            backup.write_text(proj.script_json.read_text())
        proj.write_json(proj.script_json, script)

    report = {"model": model, "segments": rows, "worst_drift": worst,
              "rerecord": flagged, "applied": applied}
    proj.write_json(proj.work / "adlib_report.json", report)
    return {"checked": sum(1 for r in rows if "drift" in r), "worst_drift": worst,
            "rerecord": flagged, "applied": applied,
            "report": "work/adlib_report.json"}
