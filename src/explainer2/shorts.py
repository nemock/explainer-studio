"""SHORTS CUTTER (PRD §5.6) — derive 9:16 Shorts from a finished deep dive.

No re-recording, no re-synthesis: each cut reuses the parent's cleaned
operator narration. A cut is a list of parent segment ids; the cutter

  1. slices those segments out of the parent's work/narration.wav (exact
     boundaries from work/segments.json) and re-assembles them with the
     standard inter-segment gap + a silent tail for the end-card,
  2. builds a derived project under <parent>/shorts/<slug>/ (9:16, parent
     music bed, subset deck slides + a CTA end-card slide),
  3. runs align → deck → render → mux → manifest in-process, per short,
     strictly serialized (16 GB rule — and align is already per-segment).

Plan file (generation-plane authored): shorts/plan.json
  [{"slug": "funnel-math", "title": "...", "segments": [0,4,5,6],
    "cta_headline": "...", "cta_subkicker": "..."}, ...]

Non-contiguous segment lists are fine — that's the point (cut the promise
stack out of a hook, jump straight to the payoff).
"""
import json
import time

import numpy as np
import soundfile as sf

from .project import Project, ASPECTS
from . import deckbuild, manifest
from .media import align, render, mux

GAP = 0.18        # inter-segment silence, matches the narrate stages
CTA_TAIL = 3.2    # silent end-card hold (seconds)


def _log(msg):
    print(f"shorts: {msg}", flush=True)


def build_derived(parent: Project, cut):
    """Create the derived project dir + narration/segments/deck/project files."""
    pseg = json.loads((parent.work / "segments.json").read_text())
    by_id = {s["id"]: s for s in pseg["segments"]}
    pdeck = json.loads(parent.deck_json.read_text())
    slides_by_id = {s["id"]: s for s in pdeck["slides"]}

    sdir = parent.dir / "shorts" / cut["slug"]
    sdir.mkdir(parents=True, exist_ok=True)

    wav, sr = sf.read(str(parent.work / "narration.wav"), dtype="float32", always_2d=True)
    mono = wav.mean(axis=1)
    gap = np.zeros(int(sr * GAP), dtype=np.float32)

    parts, segs, slides, cursor = [], [], [], 0.0
    for new_id, pid in enumerate(cut["segments"]):
        ps = by_id[pid]
        a, b = int(ps["start"] * sr), int(ps["end"] * sr)
        audio = mono[a:b]
        dur = len(audio) / sr
        segs.append({"id": new_id, "slide": ps["slide"], "text": ps["text"],
                     "start": round(cursor, 4), "end": round(cursor + dur, 4)})
        slides.append(dict(slides_by_id[ps["slide"]]))
        parts.append(audio)
        parts.append(gap)
        cursor += dur + GAP

    # silent CTA end-card: a real segment window (empty text → no captions,
    # align skips it) so the timeline gives the final slide its hold.
    segs.append({"id": len(segs), "slide": "endcard", "text": "",
                 "start": round(cursor, 4), "end": round(cursor + CTA_TAIL, 4)})
    slides.append({"id": "endcard", "type": "payoff",
                   "kicker": cut.get("cta_kicker", "the full breakdown is on the channel"),
                   "headline": cut.get("cta_headline", "Watch the full video"),
                   "accent": cut.get("cta_accent", []),
                   "subkicker": cut.get("cta_subkicker", "davesaunders.net"),
                   "transition": "rise"})
    parts.append(np.zeros(int(sr * CTA_TAIL), dtype=np.float32))

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
    return sp, duration


def run(parent_dir, plan_path=None, only=None):
    parent = Project.load(parent_dir)
    plan_path = plan_path or (parent.dir / "shorts" / "plan.json")
    plan = json.loads(open(plan_path).read())
    results = {}
    for cut in plan:
        if only and cut["slug"] != only:
            continue
        t0 = time.time()
        sp, duration = build_derived(parent, cut)
        _log(f"{cut['slug']}: {duration:.1f}s, {len(cut['segments'])} segments — rendering")
        for name, fn in (("align", align.run), ("deck", deckbuild.run),
                         ("render", render.run), ("mux", mux.run),
                         ("manifest", manifest.run)):
            r = fn(sp)
            _log(f"{cut['slug']}: {name} ok {json.dumps(r)[:100]}")
        results[cut["slug"]] = {
            "dir": str(sp.dir), "duration_s": round(duration, 1),
            "video": str(sp.dir / "video" / "explainer_9x16.mp4"),
            "wall_clock_s": round(time.time() - t0, 1)}
    return results
