"""SHORTS CUTTER (PRD §5.6) — derive 9:16 Shorts from a finished deep dive.

The BODY of each cut reuses the parent's cleaned operator narration (no
re-synthesis): a cut names parent segment ids, and the cutter slices that audio
out of work/narration.wav. But short-form is its own ecosystem, so each cut also
gets a **separately-recorded native hook and outro** (recorded in the SAME booth
session — see recorder.py + shorts-playbook.md). Those live in the parent's
voiceover/ as `short_<slug>_{hook,outro}.wav`. A lifted long-form segment alone
underperforms as a Short (starts mid-context, long-form pacing); the recorded
hook/outro are what make it native.

Per cut the cutter:
  1. PREPENDS the recorded hook (3–8s, the first words ARE the hook) + a hook slide,
  2. slices + re-assembles the named parent segments (the standalone payoff),
  3. APPENDS the recorded spoken outro. Default `ending: "loop"` — the outro loops
     back into the hook for invisible replays (replays count as views); set
     `ending: "bridge"` to drive to the long-form via the CTA end-card instead.
  4. runs align → deck → render → mux → manifest, strictly serialized (16 GB rule).

If a hook/outro line has no recording yet, the cut still renders (without it) and a
warning is logged — so a partially-recorded plan never blocks. A cut with no
`hook`/`outro` at all behaves like the legacy cutter (lift + silent CTA end-card).

Plan file (authored at the SCRIPT stage so the booth records the hooks):
  shorts/plan.json — see shorts-playbook.md for the full schema. Minimal cut:
  {"slug": "...", "title": "...", "segments": [13],
   "hook": "spoken hook line", "hook_headline": "ON-SCREEN HOOK",
   "outro": "spoken outro that loops back to the hook", "ending": "loop"}
"""
import json
import time

import numpy as np
import soundfile as sf

from .project import Project, ASPECTS
from . import deckbuild, manifest
from .media import align, render, mux

GAP = 0.18        # inter-segment silence, matches the narrate stages
CTA_TAIL = 3.2    # silent end-card hold (seconds) — legacy fallback when no spoken outro
OUTRO_TAIL = 0.35 # tiny hold after the spoken outro so the last word isn't clipped on loop


def _log(msg):
    print(f"shorts: {msg}", flush=True)


def _read_clip(path, target_sr, ref_rms=None):
    """Read a recorded hook/outro clip as mono float32 at target_sr, loudness-matched to
    the parent narration so it doesn't jump in volume next to the cleaned body audio."""
    a, s = sf.read(str(path), dtype="float32", always_2d=True)
    a = a.mean(axis=1)
    if s != target_sr and len(a) > 1:  # resample (rare — booth + narrate are both 48k)
        n = int(round(len(a) * target_sr / s))
        a = np.interp(np.linspace(0, len(a), n, endpoint=False),
                      np.arange(len(a)), a).astype(np.float32)
    if ref_rms:
        cur = float(np.sqrt(np.mean(a ** 2))) if len(a) else 0.0
        if cur > 1e-6:
            a = np.clip(a * min(4.0, ref_rms / cur), -1.0, 1.0).astype(np.float32)
    return a


def _hook_slide(cut):
    return {"id": "shook", "type": "hook",
            "kicker": cut.get("hook_kicker", ""),
            "headline": cut.get("hook_headline") or cut.get("hook", ""),
            "accent": cut.get("hook_accent", []),
            "transition": "pop"}


def _cta_slide(cut):
    return {"id": "endcard", "type": "payoff",
            "kicker": cut.get("cta_kicker", "the full breakdown is on the channel"),
            "headline": cut.get("cta_headline", "Watch the full video"),
            "accent": cut.get("cta_accent", []),
            "subkicker": cut.get("cta_subkicker", "davesaunders.net"),
            "transition": "rise"}


def _outro_slide(cut, ending):
    """Loop (default): echo the hook visual so the end flows back into the start.
    Bridge: the CTA end-card, to eject the viewer toward the long-form."""
    if ending == "bridge":
        return _cta_slide(cut)
    return {"id": "soutro", "type": "payoff",
            "headline": cut.get("outro_headline") or cut.get("hook_headline") or cut.get("outro", ""),
            "accent": cut.get("hook_accent", []),
            "transition": "rise"}


def build_derived(parent: Project, cut):
    """Create the derived project dir + narration/segments/deck/project files.
    Returns (Project, duration_s, warnings[])."""
    pseg = json.loads((parent.work / "segments.json").read_text())
    by_id = {s["id"]: s for s in pseg["segments"]}
    pdeck = json.loads(parent.deck_json.read_text())
    slides_by_id = {s["id"]: s for s in pdeck["slides"]}

    sdir = parent.dir / "shorts" / cut["slug"]
    sdir.mkdir(parents=True, exist_ok=True)
    vdir = parent.voiceover_dir

    wav, sr = sf.read(str(parent.work / "narration.wav"), dtype="float32", always_2d=True)
    mono = wav.mean(axis=1)
    ref_rms = float(np.sqrt(np.mean(mono ** 2))) if len(mono) else None
    gap = np.zeros(int(sr * GAP), dtype=np.float32)

    parts, segs, slides, cursor, warnings = [], [], [], 0.0, []

    def add(audio, text, slide):
        nonlocal cursor
        dur = len(audio) / sr
        segs.append({"id": len(segs), "slide": slide["id"], "text": text,
                     "start": round(cursor, 4), "end": round(cursor + dur, 4)})
        slides.append(slide)
        parts.append(audio)
        cursor += dur

    # 1) HOOK — recorded native opener, prepended (short-form: the first words ARE the hook)
    if cut.get("hook"):
        hk = vdir / f"short_{cut['slug']}_hook.wav"
        if hk.exists():
            add(_read_clip(hk, sr, ref_rms), cut["hook"], _hook_slide(cut))
            parts.append(gap); cursor += GAP
        else:
            warnings.append(f"hook not recorded ({hk.name}) — shipping without the native hook")

    # 2) BODY — lifted parent segments (the standalone payoff). Non-contiguous is fine.
    for pid in cut["segments"]:
        ps = by_id[pid]
        a, b = int(ps["start"] * sr), int(ps["end"] * sr)
        add(mono[a:b], ps["text"], dict(slides_by_id[ps["slide"]]))
        parts.append(gap); cursor += GAP

    # 3) OUTRO — recorded spoken outro (default loops back to the hook). Falls back to the
    #    legacy SILENT CTA end-card when there's no outro line/recording.
    ending = cut.get("ending", "loop")
    outro_done = False
    if cut.get("outro"):
        ow = vdir / f"short_{cut['slug']}_outro.wav"
        if ow.exists():
            add(_read_clip(ow, sr, ref_rms), cut["outro"], _outro_slide(cut, ending))
            parts.append(np.zeros(int(sr * OUTRO_TAIL), dtype=np.float32))
            cursor += OUTRO_TAIL
            outro_done = True
        else:
            warnings.append(f"outro not recorded ({ow.name}) — using the silent end-card")
    if not outro_done:
        # legacy silent end-card: empty text → align skips it, the slide just holds.
        slide = _cta_slide(cut)
        segs.append({"id": len(segs), "slide": slide["id"], "text": "",
                     "start": round(cursor, 4), "end": round(cursor + CTA_TAIL, 4)})
        slides.append(slide)
        parts.append(np.zeros(int(sr * CTA_TAIL), dtype=np.float32))
        cursor += CTA_TAIL

    narration = np.concatenate(parts)
    duration = len(narration) / sr

    proj_data = {"title": cut["title"], "slug": cut["slug"],
                 "aspect": "9:16", "aspects": ["9:16"],
                 "width": ASPECTS["9:16"][0], "height": ASPECTS["9:16"][1],
                 "fps": parent.fps, "voice": parent.voice,
                 "voice_source": parent.voice_source, "language": "en",
                 "theme": parent.data.get("theme", "midnight"),
                 "safe_bottom": 0.18,  # Shorts UI overlays sit higher than feed players
                 "derived_from": parent.dir.name,
                 "parent_segments": cut["segments"]}
    for k in ("music", "music_gain"):
        if parent.data.get(k) is not None:
            proj_data[k] = parent.data[k]

    sp = Project(sdir, proj_data)
    sp.write_json(sp.project_json, proj_data)
    sp.write_json(sp.deck_json, {"title": cut["title"], "slides": slides})
    sp.write_json(sp.script_json, {"schema": "script/2", "title": cut["title"],
                                   "segments": [s for s in segs if s["text"]]})
    sf.write(sp.work / "narration.wav", narration, sr)
    sp.write_json(sp.work / "segments.json",
                  {"sample_rate": sr, "duration": round(duration, 4), "segments": segs})
    return sp, duration, warnings


def run(parent_dir, plan_path=None, only=None):
    parent = Project.load(parent_dir)
    plan_path = plan_path or (parent.dir / "shorts" / "plan.json")
    plan = json.loads(open(plan_path).read())
    results = {}
    for cut in plan:
        if only and cut["slug"] != only:
            continue
        t0 = time.time()
        sp, duration, warnings = build_derived(parent, cut)
        for w in warnings:
            _log(f"{cut['slug']}: WARNING — {w}")
        _log(f"{cut['slug']}: {duration:.1f}s, {len(cut['segments'])} segments — rendering")
        for name, fn in (("align", align.run), ("deck", deckbuild.run),
                         ("render", render.run), ("mux", mux.run),
                         ("manifest", manifest.run)):
            r = fn(sp)
            _log(f"{cut['slug']}: {name} ok {json.dumps(r)[:100]}")
        results[cut["slug"]] = {
            "dir": str(sp.dir), "duration_s": round(duration, 1),
            "video": str(sp.dir / "video" / "explainer_9x16.mp4"),
            "warnings": warnings,
            "wall_clock_s": round(time.time() - t0, 1)}
    return results
