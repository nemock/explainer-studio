"""AD-LIB CHECK (PRD §5.3) — did the operator say what the script says?

Transcribes each recorded segment locally (mlx-whisper, Metal) and word-diffs it
against the script text:

  drift < 2%   verbatim — keep the script text (cleanest captions)
  2% – 15%     ad-lib   — captions should follow what was actually said;
                          --apply rewrites that segment's text from the ASR
  > 15%        flagged  — re-record (or accept-with-rewrite manually)

Report → work/adlib_report.json. --apply backs up script.json to
script.orig.json before touching it. Forced alignment downstream works with
either text, so this stage is advisory — it never blocks the pipeline.
"""
import difflib
import json
import re

MODEL = "mlx-community/whisper-medium.en-mlx"
MINOR = 0.02
MAJOR = 0.15


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
    return str(n)


def _norm_words(text):
    text = text.lower().replace("%", " percent ")
    text = re.sub(r"(\d),(\d)", r"\1\2", text)          # 1,000 → 1000
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


def run(proj, apply=False, model=MODEL):
    import mlx_whisper
    from .common import effective_segments
    from .voiceover import seg_path

    script = json.loads(proj.script_json.read_text())
    segments = effective_segments(proj, script)
    by_id = {s["id"]: s for s in script["segments"]}

    rows, worst = [], 0.0
    for seg in segments:
        wav = seg_path(proj, seg["id"])
        if not wav.exists():
            rows.append({"id": seg["id"], "status": "not_recorded"})
            continue
        asr = mlx_whisper.transcribe(str(wav), path_or_hf_repo=model)["text"].strip()
        d = _drift(seg["text"], asr)
        worst = max(worst, d)
        status = "verbatim" if d < MINOR else ("adlib" if d < MAJOR else "rerecord")
        rows.append({"id": seg["id"], "status": status, "drift": d,
                     "script_text": seg["text"], "asr_text": asr})
        if apply and status == "adlib" and seg["id"] in by_id:
            by_id[seg["id"]]["text"] = _spell_numbers(asr)
            by_id[seg["id"]]["adlib_applied"] = True

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
