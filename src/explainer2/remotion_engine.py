"""Remotion render engine (motion-playbook.md) — the animated alternative to the deck
engine. Translates an assembled project's data (segments.json + deck.json +
alignment.json + narration.wav) into a Remotion motion spec and renders the final muxed
mp4 via the shared `remotion/` component library. Claude authors specs, not React.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

REMOTION_DIR = Path(__file__).resolve().parents[2] / "remotion"


def _parse_stat(value):
    """Parse a deck stat value ('−$1,000', '$500', '93%') -> (to:float, prefix:str) or None."""
    if not value:
        return None
    s = str(value).replace("−", "-").replace(",", "").strip()
    prefix = "$" if "$" in s else ""
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    if re.search(r"\d\s*[a-zA-Z]", s) and "%" not in s:  # unit-suffixed magnitudes ($500M) — skip
        return None
    return float(m.group(0)), prefix


def _items(slide):
    raw = slide.get("items") or slide.get("steps") or []
    return [(i.get("text") if isinstance(i, dict) else i) for i in raw]


# --- narration-cue resolution (motion-playbook §5's `sync` contract, built 2026-07-04) ---
# A cue is a spoken phrase; resolution turns it into a SCENE-RELATIVE frame number from
# the alignment word timestamps, at spec-build time — so the React side stays a pure
# function of frame. Misses degrade gracefully (proportional fallback + a run.log
# warning), never break a render.
_STOP = {"the", "a", "an", "of", "in", "on", "by", "and", "is", "are", "to", "for",
         "your", "you", "it", "its", "that", "this", "with", "but", "so", "i", "my",
         "we", "he", "she", "why", "can", "be", "as", "at", "or", "if"}


def _norm_word(x):
    return re.sub(r"[^a-z0-9]", "", x.lower())


def _content_key(text):
    """First content word of a label, truncated — tolerant of inflection drift."""
    for tok in str(text).split():
        n = _norm_word(tok)
        if n and n not in _STOP:
            return n[:4]
    toks = str(text).split()
    return _norm_word(toks[0])[:4] if toks else ""


def _resolve_phrase(phrase, segw, s0, fps):
    """Spoken phrase -> scene-relative frame. Tries a consecutive-token match of the
    whole phrase (prefix-tolerant per token), then falls back to the phrase's first
    content word. Returns None if nothing matches."""
    toks = [_norm_word(t) for t in str(phrase).split()]
    toks = [t for t in toks if t]
    if not toks or not segw:
        return None
    wn = [_norm_word(w["word"]) for w in segw]
    for i in range(len(wn) - len(toks) + 1):
        if all(wn[i + j][:5] == toks[j][:5] or wn[i + j].startswith(toks[j]) or toks[j].startswith(wn[i + j])
               for j in range(len(toks))):
            return max(0, int(round((segw[i]["start"] - s0) * fps)))
    key = _content_key(phrase)
    if key:
        for i, w in enumerate(wn):
            if w.startswith(key):
                return max(0, int(round((segw[i]["start"] - s0) * fps)))
    return None


def _monotonic_fill(times, fps=30):
    """Gap-fill None item-times and force a STRICTLY increasing sequence.

    A partially-matched label list (some items sync, some don't) must never hand a
    component a descending or equal interpolate input range — that raised
    'inputRange must be strictly monotonically increasing' and hard-crashed a render
    (#19, StepFlow, frames [749, 294.25]) instead of the playbook's 'misses never
    break a render' fallback. Unmatched items are interpolated between their matched
    neighbors; ties/descents are bumped up by a frame."""
    n = len(times)
    if n == 0 or all(t is None for t in times):
        return times  # nothing matched: let the component even-stagger (already monotonic)
    idx = [i for i, t in enumerate(times) if t is not None]
    out = list(times)
    first = idx[0]
    for i in range(first):                         # leading Nones -> ramp up to the first anchor
        out[i] = int(round(out[first] * (i + 1) / (first + 1)))
    for a, b in zip(idx, idx[1:]):                 # interior Nones -> linear between anchors
        if b - a > 1:
            span = out[b] - out[a]
            for k in range(a + 1, b):
                out[k] = int(round(out[a] + span * (k - a) / (b - a)))
    last = idx[-1]                                 # trailing Nones -> extend by the last gap
    gap = max(1, int(round((out[idx[-1]] - out[idx[-2]]) / (idx[-1] - idx[-2])))) if len(idx) >= 2 else fps // 2
    for i in range(last + 1, n):
        out[i] = out[i - 1] + gap
    for i in range(1, n):                          # final guard: strictly increasing
        if out[i] is None or out[i] <= out[i - 1]:
            out[i] = out[i - 1] + 1
    return out


def _resolve_items(labels, segw, s0, fps):
    """Sequential label list -> per-item scene-relative frames.
    Walks the segment's words FORWARD (a repeated word matches its next occurrence),
    the behavior BuildList's item sync shipped with (#13), then `_monotonic_fill`s
    the result so misses never yield a descending interpolate range."""
    times, wp = [], 0
    for label in labels:
        key, t = _content_key(label), None
        while wp < len(segw):
            if key and _norm_word(segw[wp]["word"]).startswith(key):
                t = segw[wp]["start"]; wp += 1
                break
            wp += 1
        times.append(None if t is None else max(0, int(round((t - s0) * fps))))
    return _monotonic_fill(times, fps)


def _scene_for(slide):
    """Map a deck slide -> (component, fields) per the motion-playbook §6 migration table.
    Unknown -> KineticHeadline (a clean animated headline). `image` fields stay as the
    deck's source path; render() stages them into the public dir."""
    t = slide.get("type")
    kicker = slide.get("kicker", "")
    accent = slide.get("accent", []) or []
    accent2 = slide.get("accent2", []) or []
    headline = slide.get("headline") or slide.get("title") or slide.get("word") or ""

    if t == "hook":
        return "Hero3D", {"kicker": kicker, "headline": headline, "accent": accent,
                          "accentRed": accent2, "shape": slide.get("shape", "ico")}
    if t in ("payoff", "cta"):
        return "CTA", {"kicker": kicker, "headline": headline, "accent": accent,
                       "accentRed": accent2, "subkicker": slide.get("subkicker", "")}
    if t == "punch":
        return "PunchWord", {"word": slide.get("word") or headline, "kicker": kicker,
                             "kind": slide.get("kind", ""), "accent": accent, "accentRed": accent2}
    if t == "define":
        return "DefineTerm", {"kicker": kicker, "term": slide.get("term", ""),
                              "definition": slide.get("definition", ""),
                              "accent": accent, "accentRed": accent2}
    if t == "reframe":
        return "Reframe", {"before": slide.get("before", ""), "after": slide.get("after", "")}
    if t == "quote":
        return "Quote", {"quote": slide.get("quote") or headline,
                         "attribution": slide.get("attribution") or slide.get("source", "")}
    if t == "list":
        return "BuildList", {"kicker": kicker, "items": _items(slide),
                             "title": slide.get("title", ""), "accent": accent, "accentRed": accent2}
    if t in ("steps", "flow"):
        return "StepFlow", {"kicker": kicker, "steps": _items(slide)}
    if t == "sting":
        return "BrandSting", {"title": slide.get("title") or headline, "subtitle": slide.get("subtitle", "")}
    if t == "compare":
        return "SideBySide", {"left": slide.get("left", {}), "right": slide.get("right", {})}
    if t == "schematic":
        # node/edge diagram assembling under narration (motion-playbook §2C). Stage cues
        # (stages[].cue) resolve to fields.stageTimes in build_spec's sync pass.
        return "Schematic", {"kicker": kicker, "nodes": slide.get("nodes", []),
                             "edges": slide.get("edges", []), "stages": slide.get("stages", []),
                             "camera": slide.get("camera", []), "sketch": bool(slide.get("sketch"))}
    if t == "timeline":
        return "Timeline", {"kicker": kicker, "events": slide.get("events", [])}
    if t == "waveform":
        return "Waveform", {"kicker": kicker, "headline": headline, "audio": "narration.wav"}
    if t == "delta":
        return "SideBySide", {
            "left": {"title": slide.get("from_label", ""), "value": slide.get("from", "")},
            "right": {"title": slide.get("to_label", ""), "value": slide.get("to", "")}}
    if t in ("trend", "ranked", "diagram"):
        pts = [p.get("value") if isinstance(p, dict) else p for p in (slide.get("points") or slide.get("bars") or [])]
        return "DrawLine", {"kicker": kicker, "points": pts,
                            "endLabel": slide.get("end_label", ""), "kind": slide.get("kind", "")}
    if t == "waterfall":
        return "Waterfall", {"kicker": kicker, "start": slide.get("start", {}),
                             "steps": slide.get("steps", []), "end": slide.get("end", {})}
    if t == "pictograph":
        return "Pictograph", {"kicker": kicker, "filled": slide.get("filled", 0),
                              "total": slide.get("total", 100), "label": slide.get("label", ""),
                              "kind": slide.get("kind", "")}
    if t in ("ring", "progress"):
        return "Ring", {"kicker": kicker, "value": slide.get("value", 0), "label": slide.get("label", "")}
    if t == "funnel":
        return "Funnel", {"kicker": kicker, "stages": slide.get("stages", [])}
    if t == "statgrid":
        return "StatGrid", {"kicker": kicker, "stats": slide.get("stats", []),
                            "source": slide.get("source", "")}
    if t == "stat":
        parsed = _parse_stat(slide.get("value"))
        if parsed:
            to, prefix = parsed
            return "StatCounter", {"kicker": kicker, "from": 0, "to": to, "prefix": prefix,
                                   "label": slide.get("label", ""), "subkicker": slide.get("subkicker", "")}
        return "KineticHeadline", {"kicker": kicker, "headline": slide.get("value") or headline,
                                   "accent": accent, "accentRed": accent2,
                                   "subkicker": slide.get("subkicker", "")}
    if t == "figure":
        return "Figure", {"kicker": kicker, "image": slide.get("image"),
                          "caption": slide.get("caption", ""), "highlight": slide.get("highlight"),
                          "title": slide.get("title", ""), "accent": accent, "accent2": accent2,
                          "imageFromFrac": slide.get("imageFromFrac", 0),
                          "moves": slide.get("moves", []), "assemble": slide.get("assemble")}
    if t == "footage":
        return "Footage", {"image": slide.get("image"), "headline": headline,
                           "accent": accent, "accent2": accent2}
    if t == "highlight":
        return "KineticHeadline", {"kicker": kicker, "headline": headline,
                                   "accent": slide.get("mark") or accent}
    return "KineticHeadline", {"kicker": kicker, "headline": headline, "accent": accent,
                               "accentRed": accent2, "subkicker": slide.get("subkicker", "")}


def build_spec(sp):
    seg = json.loads((sp.work / "segments.json").read_text())
    fps = sp.fps
    width, height = sp.data["width"], sp.data["height"]
    duration = seg["duration"]
    segs = seg["segments"]
    slides_by_id = {s["id"]: s for s in json.loads(sp.deck_json.read_text())["slides"]}

    scenes = []
    for i, s in enumerate(segs):
        start = s["start"]
        end = segs[i + 1]["start"] if i + 1 < len(segs) else duration
        comp, fields = _scene_for(slides_by_id.get(s["slide"], {}))
        scenes.append({"component": comp, "from": int(round(start * fps)),
                       "durationInFrames": max(1, int(round((end - start) * fps))), "fields": fields})

    words = []
    al = sp.work / "alignment.json"
    if al.exists():
        for w in json.loads(al.read_text()).get("words", []):
            words.append({"word": w["word"], "start": w["start"], "end": w["end"]})

    # --- narration sync: cues, item times, annotations (motion-playbook §5) ---
    # Every resolved frame is SCENE-relative, so the sting shift below (which only
    # moves sc["from"]) never invalidates them.
    warnings = []
    # which field each staggered component syncs (label list -> fields.itemTimes)
    _ITEM_FIELDS = {"BuildList": ("items", lambda f: f.get("items") or []),
                    "StepFlow": ("steps", lambda f: [s.get("title") if isinstance(s, dict) else s
                                                     for s in (f.get("steps") or [])]),
                    "Funnel": ("stages", lambda f: [s.get("label", "") for s in (f.get("stages") or [])]),
                    "Waterfall": ("bars", lambda f: [b.get("label", "") for b in
                                                     ([f.get("start")] + list(f.get("steps") or []) + [f.get("end")])
                                                     if isinstance(b, dict)]),
                    "Timeline": ("events", lambda f: [e.get("label", "") for e in (f.get("events") or [])])}
    for idx, sc in enumerate(scenes):
        if idx >= len(segs):
            continue
        slide = slides_by_id.get(segs[idx]["slide"], {})
        s0 = segs[idx]["start"]
        s1 = segs[idx + 1]["start"] if idx + 1 < len(segs) else duration
        segw = [w for w in words if s0 <= w["start"] < s1]
        sid = segs[idx]["slide"]
        # 1) generic cue map: {"cues": {"name": "spoken phrase", ...}} -> fields.cueFrames
        cf = {}
        for name, phrase in (slide.get("cues") or {}).items():
            f = _resolve_phrase(phrase, segw, s0, fps)
            if f is None:
                warnings.append(f"{sid}: cue '{name}' unmatched (\"{phrase}\") — component falls back")
            else:
                cf[name] = f
        if cf:
            sc["fields"]["cueFrames"] = cf
        # 2) per-item auto-sync for staggered components (each item appears AS it's said;
        #    the BuildList behavior from #13, generalized)
        if sc["component"] in _ITEM_FIELDS:
            labels = _ITEM_FIELDS[sc["component"]][1](sc.get("fields") or {})
            if labels:
                sc["fields"]["itemTimes"] = _resolve_items(labels, segw, s0, fps)
        # 2b) schematic stage cues -> fields.stageTimes (None -> component even-stagger)
        if sc["component"] == "Schematic":
            sts = []
            for st in (sc["fields"].get("stages") or []):
                f = _resolve_phrase(st.get("cue", ""), segw, s0, fps) if st.get("cue") else None
                if st.get("cue") and f is None:
                    warnings.append(f"{sid}: schematic stage cue unmatched (\"{st['cue']}\")")
                sts.append(f)
            if sts:
                sc["fields"]["stageTimes"] = sts
        # 3) figure highlight / tour-move / assemble-piece cues -> cueFrame
        hl = (sc.get("fields") or {}).get("highlight")
        if isinstance(hl, dict) and hl.get("cue"):
            f = _resolve_phrase(hl["cue"], segw, s0, fps)
            if f is None:
                warnings.append(f"{sid}: highlight cue unmatched (\"{hl['cue']}\")")
            else:
                hl["cueFrame"] = f
        dur = sc["durationInFrames"]
        moves = (sc.get("fields") or {}).get("moves") or []
        for mi, mv in enumerate(moves):
            f = _resolve_phrase(mv.get("cue", ""), segw, s0, fps) if mv.get("cue") else None
            if mv.get("cue") and f is None:
                warnings.append(f"{sid}: figure move cue unmatched (\"{mv['cue']}\")")
            mv["cueFrame"] = f if f is not None else int(round(dur * (mi + 1) / (len(moves) + 1)))
        pieces = ((sc.get("fields") or {}).get("assemble") or {}).get("pieces") or []
        for pi, pc in enumerate(pieces):
            f = _resolve_phrase(pc.get("cue", ""), segw, s0, fps) if pc.get("cue") else None
            if pc.get("cue") and f is None:
                warnings.append(f"{sid}: assemble piece cue unmatched (\"{pc['cue']}\")")
            pc["cueFrame"] = f if f is not None else int(round(dur * (pi + 1) / (len(pieces) + 1)))
        # 4) annotations: overlay drawings on any scene; each may carry a cue phrase.
        #    Unresolved/missing cues stagger proportionally through the scene's middle.
        anns = slide.get("annotations") or []
        if anns:
            n, dur = len(anns), sc["durationInFrames"]
            resolved = []
            for ai, a in enumerate(anns):
                a2 = dict(a)
                f = _resolve_phrase(a.get("cue", ""), segw, s0, fps) if a.get("cue") else None
                if a.get("cue") and f is None:
                    warnings.append(f"{sid}: annotation cue unmatched (\"{a['cue']}\") — proportional fallback")
                a2["cueFrame"] = f if f is not None else int(round(dur * (ai + 1) / (n + 1)))
                resolved.append(a2)
            sc["annotations"] = resolved

    # Bookend long-form with the brand sting (motion-playbook §2F). On by default for
    # landscape (deep dives), off for portrait shorts (the hook must open instantly).
    # project.json `sting` overrides. The narration is shifted to start after the intro.
    audio_from = 0
    total = duration
    if sp.data.get("sting", width >= height):
        # Paper-launch sting (motion-playbook §2F, 2026-07-14). Intro plays the full
        # launch+wordmark (~3.5s); outro is the calm finished-mark card (~2.5s). The intro
        # length sets the narration offset — see memory gag-splice-sting-offset (now 3.5s
        # for the explainer2 Remotion engine; v1 stays 2.5s).
        INTRO, OUTRO = 3.5, 2.5
        off = int(round(INTRO * fps))
        for sc in scenes:
            sc["from"] += off
        for w in words:
            w["start"] += INTRO
            w["end"] += INTRO
        scenes.insert(0, {"component": "PaperSting", "from": 0, "durationInFrames": off,
                          "fields": {}})
        scenes.append({"component": "PaperSting", "from": off + int(round(duration * fps)),
                       "durationInFrames": int(round(OUTRO * fps)),
                       "fields": {"outro": True, "subtitle": "davesaunders.net"}})
        audio_from = off
        total = INTRO + duration + OUTRO

    safe_bottom = float(sp.data.get("safe_bottom", 0.12)) + 0.04
    return {
        "width": width, "height": height, "fps": fps,
        "durationInFrames": int(round(total * fps)),
        "audio": "narration.wav", "words": words, "scenes": scenes,
        "captionBottomPx": int(round(height * safe_bottom)),
        "captionFontSize": int(round(height * (0.032 if height >= 1600 else 0.026))),
        "audioFrom": audio_from,
        "_warnings": warnings,
    }


def _stage_images(sp, spec, public):
    """Copy any image referenced by a scene into the public dir, rebasing fields.image to
    the basename. Resolves the deck's path against the project (and, for shorts, the parent)."""
    roots = [sp.dir, sp.dir.parent.parent, sp.dir.parent]  # project, then parent (shorts), then shorts/
    for scene in spec["scenes"]:
        img = (scene.get("fields") or {}).get("image")
        if not img:
            continue
        src = next((r / img for r in roots if (r / img).exists()), None)
        if src is None:
            scene["fields"]["image"] = None  # missing -> component shows headline/caption only
            continue
        dst = Path(img).name
        shutil.copy(src, public / dst)
        scene["fields"]["image"] = dst


def _stage_doodles(spec, public, log):
    """Stage annotation doodles (kind:'doodle', name:'<category>/<name>') from the local
    library into the render's public dir. The library is operator-licensed, gitignored
    media (library/ — use, don't redistribute); staging copies only what a scene
    references, into the project's private work dir. Missing name -> the annotation is
    dropped with a warning, never a broken render."""
    lib = REMOTION_DIR.parent / "library" / "doodles"
    aspects = {}
    mf = lib / "manifest.json"
    if mf.exists():
        for d in json.loads(mf.read_text()).get("doodles", []):
            if d.get("h"):
                aspects[d["name"]] = round(d["w"] / d["h"], 4)
    for scene in spec["scenes"]:
        anns = scene.get("annotations") or []
        if not anns:
            continue
        kept = []
        for a in anns:
            if a.get("kind") != "doodle":
                kept.append(a)
                continue
            name = str(a.get("name", ""))
            src = lib / f"{name}.png"
            if not src.exists():
                log(f"remotion: doodle missing, annotation dropped: {name} "
                    f"(see library/doodles/manifest.json)")
                continue
            dst = "doodle__" + name.replace("/", "_") + ".png"
            if not (public / dst).exists():
                shutil.copy(src, public / dst)
            kept.append({**a, "file": dst, "aspect": a.get("aspect") or aspects.get(name, 1.0)})
        scene["annotations"] = kept


def _apply_music(sp, out, log):
    """Mix the channel music bed UNDER the rendered mp4's existing narration audio.
    Remotion bakes its own audio (narration only), so unlike the deck engine there is
    no separate mux stage to add music — without this the render ships music-less
    (caught 2026-06-24: #12 rendered with a dead-silent intro sting). Mirrors the
    media/mux.py recipe: looped bed at music_gain, amix normalize=0, limiter, video
    copied through (no re-encode). Runs inside the already-held render lock."""
    music = sp.data.get("music")
    if not music:
        return None
    mp = Path(music)
    if not mp.is_absolute():
        mp = sp.dir / music
    if not mp.exists():
        log(f"remotion: music not found, shipping without bed: {music}")
        return None
    gain = float(sp.data.get("music_gain", 0.12))
    tmp = out.with_suffix(".music.mp4")
    fc = (f"[1:a]aloop=loop=-1:size=2000000000,volume={gain},"
          f"aformat=sample_rates=48000:channel_layouts=stereo[bed];"
          f"[0:a][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix];"
          f"[mix]alimiter=limit=0.84:level=false[a]")
    ff = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [ff, "-hide_banner", "-y", "-i", str(out), "-i", str(mp),
           "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", "-shortest", str(tmp)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"remotion music mux failed:\n{r.stderr[-1500:]}")
    tmp.replace(out)
    log(f"remotion: music bed mixed ({mp.name} @ gain {gain})")
    _copy_music_license(mp, sp.dir, log)
    return {"music": mp.name, "gain": gain}


def _copy_music_license(mp, proj_dir, log):
    """Drop a LOCAL copy of the music track's license certificate into the project
    (monetization-readiness, operator directive 2026-07-04). The license lives
    beside the track in library/music/, sharing its Pixabay track id (the trailing
    number), so match on that id rather than the differing name prefixes."""
    import re
    ids = re.findall(r"\d{4,}", Path(mp).stem)
    if not ids:
        return
    tid = ids[-1]
    for lic in sorted(Path(mp).parent.glob("*.txt")):
        if "licen" in lic.name.lower() and tid in lic.name:
            dest = Path(proj_dir) / lic.name
            if not (dest.exists() and dest.read_bytes() == lic.read_bytes()):
                shutil.copy2(lic, dest)
                log(f"remotion: music license copied ({lic.name})")
            return
    log(f"remotion: WARNING no license file found beside music track (id {tid}) — check library/music/")


def render(sp, log=print, frames=None, out=None):
    """Render `sp` via Remotion -> the final muxed mp4. `frames` (e.g. '0-2400') renders a
    range for fast preview. The heavy headless render should be wrapped by the render-lock."""
    if not (REMOTION_DIR / "node_modules").exists():
        raise RuntimeError(
            f"Remotion engine not installed: run `npm install` in {REMOTION_DIR} "
            f"(or use --engine deck). The motion engine needs the Node toolchain.")
    spec = build_spec(sp)
    for w in spec.pop("_warnings", []):
        log(f"remotion: sync WARNING {w}")
    stage = sp.work / "remotion"
    public = stage / "public"
    public.mkdir(parents=True, exist_ok=True)
    shutil.copy(sp.work / "narration.wav", public / "narration.wav")
    _stage_images(sp, spec, public)
    _stage_doodles(spec, public, log)
    # CTA scenes show the brand book cover unless the project opts out with
    # "cta_book": false in project.json (e.g. masterclass modules use no book cover).
    if sp.data.get("cta_book", True) and any(s["component"] == "CTA" for s in spec["scenes"]):
        bc_dir = REMOTION_DIR.parent / "book_cover"
        bc = next(iter(sorted(bc_dir.glob("*.png"))), None) if bc_dir.exists() else None
        if bc:
            shutil.copy(bc, public / "book_cover.png")
            for s in spec["scenes"]:
                if s["component"] == "CTA":
                    s["fields"]["image"] = "book_cover.png"
    props = stage / "props.json"
    props.write_text(json.dumps(spec))

    aspect = sp.data.get("aspect", "9:16").replace(":", "x")
    outdir = sp.dir / "video"
    outdir.mkdir(exist_ok=True)
    out = Path(out) if out else outdir / f"explainer_{aspect}.mp4"

    npx = shutil.which("npx") or "npx"
    cmd = [npx, "remotion", "render", "src/index.ts", "Video", str(out),
           f"--props={props}", f"--public-dir={public}", "--log=error"]
    if frames:
        cmd.append(f"--frames={frames}")
    log(f"remotion: rendering {sp.dir.name} ({len(spec['scenes'])} scenes, {spec['durationInFrames']}f"
        + (f", slice {frames}" if frames else "") + ")")
    r = subprocess.run(cmd, cwd=str(REMOTION_DIR), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"remotion render failed:\n{r.stdout[-1800:]}\n{r.stderr[-1800:]}")
    # Remotion bakes narration-only audio; mix the channel music bed under it (no
    # separate mux stage on this path). Skipped for slice previews (frames set).
    music = None if frames else _apply_music(sp, out, log)
    return {"engine": "remotion", "video": str(out), "scenes": len(spec["scenes"]),
            "duration_s": round(spec["durationInFrames"] / spec["fps"], 2), "music": music}
