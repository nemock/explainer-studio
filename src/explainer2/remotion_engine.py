"""Remotion render engine (motion-playbook.md) — the animated alternative to the deck
engine. Translates an assembled project's data (segments.json + deck.json +
alignment.json + narration.wav) into a Remotion motion spec and renders the final muxed
mp4 via the shared `remotion/` component library. Claude authors specs, not React.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

REMOTION_DIR = Path(__file__).resolve().parents[2] / "remotion"

# Chibi presenter library (the operator's cartoon stand-in; locked into the brand system
# 2026-08-06 — make_money/routine_changes/2026-08-06-video-brand-system-palettes-locked.md).
# The library lives OUTSIDE this public repo and is staged per-reference at render time,
# same doctrine as library/doodles: private media — use, don't redistribute, never commit
# poses here. Deck refs are "chibi/<pose>" (pose = a filename in the library, ".png"
# optional), normally on a Cutout/props image so the presenter sits in a bottom corner at
# 18–22% frame height with pose cuts on scene changes. Personal shows only — never
# Circumvent. Override the root with $EXPLAINER_CHIBI_DIR (e.g. to point at a future v3).
CHIBI_DIR = Path(os.environ.get(
    "EXPLAINER_CHIBI_DIR",
    "/Volumes/Casima/claudeCode/dave_chibi_character/v2/poses_normalized_tight"))


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
    return [((i.get("text") or i.get("title")) if isinstance(i, dict) else i) for i in raw]


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


def _papercraft_scene(slide, t, kicker, accent, headline):
    """The PAPERCRAFT style map (papercraft-motion-spec.md §7 / migration note §3):
    deck TYPES render as the Paper* family on the nemock-deep-dive theme. Returns
    None for types not yet migrated — they fall through to the classic map, so
    decks never break mid-migration."""
    if t in ("statement", "highlight"):
        return "PaperStatement", {"kicker": kicker, "headline": headline, "accent": accent,
                                  "subkicker": slide.get("subkicker", "")}
    if t == "quote":
        return "PaperStatement", {"headline": slide.get("quote") or headline,
                                  "attrib": slide.get("attribution") or slide.get("source", "")}
    if t == "define":
        return "PaperDefine", {"kicker": kicker, "term": slide.get("term", ""),
                               "definition": slide.get("definition", "")}
    if t == "punch":
        return "PaperPunch", {"word": slide.get("word") or headline, "kicker": kicker,
                              "kind": slide.get("kind", "")}
    if t == "compare":
        return "PaperCompare", {"kicker": kicker, "left": slide.get("left", {}),
                                "right": slide.get("right", {})}
    if t == "delta":
        return "PaperCompare", {"kicker": kicker,
                                "left": {"title": slide.get("from_label", ""), "value": slide.get("from", "")},
                                "right": {"title": slide.get("to_label", ""), "value": slide.get("to", "")}}
    if t in ("steps", "flow"):
        return "PaperSteps", {"kicker": kicker, "steps": _items(slide)}
    if t == "list":
        return "PaperList", {"kicker": kicker, "title": slide.get("title", ""), "items": _items(slide)}
    if t in ("trend", "ranked"):
        pts = [p.get("value") if isinstance(p, dict) else p for p in (slide.get("points") or slide.get("bars") or [])]
        if pts:
            return "PaperStairs", {"kicker": kicker, "points": pts,
                                   "endLabel": slide.get("end_label", ""), "kind": slide.get("kind", "")}
    if t in ("ring", "progress"):
        return "PaperCounter", {"kicker": kicker, "value": slide.get("value", 0),
                                "suffix": "%", "label": slide.get("label", "")}
    if t == "keepcard":
        return "PaperPopCard", {"image": slide.get("image"),
                                "label": slide.get("label") or headline, "sub": slide.get("sub")}
    if t in ("payoff", "cta"):
        return "PaperBookCTA", {"kicker": kicker, "headline": headline, "accent": accent,
                            "subkicker": slide.get("subkicker", "")}
    if t == "hook" and (slide.get("set") or slide.get("beats")):
        return "PaperSetHook", {"set": slide.get("set"), "props": slide.get("props", []),
                                "beats": slide.get("beats", []), "kicker": kicker,
                                "headline": headline, "accent": accent}
    return None


def _circumvent_scene(slide, t, kicker, accent, headline):
    """CIRCUMVENT style map. Every deck type resolves to a Cvg* scene so no slide can
    fall through to a card. `set`, `props`, `anchor`, `band` and `align` pass straight
    through from the deck; `set`/`props[].image` paths under papercraft-circumvent/ are
    staged wholesale by render()."""
    common = {
        "set": slide.get("set"),
        "anchor": slide.get("anchor"),
        "props": slide.get("props") or [],
        "kicker": kicker,
        "accent": accent,
        "headline": headline,
        "align": slide.get("align", "left"),
        "band": slide.get("band", "top"),
        "subkicker": slide.get("subkicker", ""),
    }
    if t == "punch":
        return "CvgPunch", {**common, "word": slide.get("word") or headline,
                            "kind": slide.get("kind", "")}
    if t == "list":
        return "CvgList", {**common, "items": _items(slide), "title": slide.get("title", "")}
    if t in ("compare", "delta"):
        left = slide.get("left") or {"title": slide.get("from_label", ""), "value": slide.get("from", "")}
        right = slide.get("right") or {"title": slide.get("to_label", ""), "value": slide.get("to", "")}
        return "CvgCompare", {**common, "left": left, "right": right}
    if t in ("steps", "flow"):
        return "CvgSteps", {**common, "steps": _items(slide),
                            "stepImages": slide.get("step_images") or []}
    if t == "define":
        return "CvgDefine", {**common, "term": slide.get("term", ""),
                             "definition": slide.get("definition", "")}
    if t == "quote":
        return "CvgScene", {**common, "headline": slide.get("quote") or headline,
                            "attrib": slide.get("attribution") or slide.get("source", "")}
    # statement / hook / payoff / highlight / anything else: type on the set.
    return "CvgScene", common


def _scene_for(slide, theme=""):
    """Map a deck slide -> (component, fields) per the motion-playbook §6 migration table.
    Unknown -> KineticHeadline (a clean animated headline). `image` fields stay as the
    deck's source path; render() stages them into the public dir.
    `theme` selects the STYLE: nemock-deep-dive routes through the papercraft map
    first (classic components remain the fallback for unmigrated types)."""
    # Direct-component escape hatch: a slide may name its Remotion component + fields
    # explicitly, bypassing the type map. The Cut & Bond paper channel authors its decks
    # this way (component: "PaperAtom", fields: {...}) so its paper components never need
    # entries here. The component must be registered in Video.tsx's REGISTRY.
    if slide.get("component"):
        return slide["component"], (slide.get("fields") or {})
    t = slide.get("type")
    kicker = slide.get("kicker", "")
    accent = slide.get("accent", []) or []
    accent2 = slide.get("accent2", []) or []
    headline = slide.get("headline") or slide.get("title") or slide.get("word") or ""

    # Papercraft style map. nemock-deep-dive (Dave's book/davesaunders.net deep dives) and
    # brg-deep-dive (the Base Reality Group series, added 2026-07-26) both render the Paper*
    # family; they differ by ink/accent (ink.tsx) and by their stings, not by the type map.
    # wte-guide (the waste-to-fuel Operator's Guide, 2026-07-29) joins the family: the
    # operator asked for heavy paper-craft throughout, in the BRG palette.
    # Circumvent gets its OWN scene family (2026-07-30). The shared Paper* components
    # print every line on a rounded cream card over a gradient table, which reads as a UI
    # panel pasted onto the generated paper art. Cvg* scenes drop the card: the set fills
    # the frame, cut-outs stand in it, type sits on the paper. Checked BEFORE the shared
    # papercraft map so it wins for this theme only.
    if theme == "circumvent":
        cvg = _circumvent_scene(slide, t, kicker, accent, headline)
        if cvg:
            return cvg

    # brg-deep-dive is DELIBERATELY not here (2026-08-01). The Paper* family paints its own
    # PaperTable ground, and PaperTable's key light bakes a hardcoded near-black surround, so
    # on a cream BRG world ~13 slides dropped to a navy desk while figures/schematics stayed
    # cream — two backdrop systems in one video. Retuning PaperTable for a light ground would
    # touch the FWF/nemock world that is already in use, which the theme-isolation rule
    # forbids. The classic map keeps every substrate that matters here (Figure's paper mount +
    # tape, Schematic's PaperNote post-its, StatCounter's paper meter are all classic-map
    # components gated on ink.paper) and renders them on the cream PaperBackground.
    # BRG keeps PaperHook (below) and BRGPaperSting.
    if theme in ("nemock-deep-dive", "wte-guide", "circumvent"):
        pc = _papercraft_scene(slide, t, kicker, accent, headline)
        if pc:
            return pc

    if t == "hook":
        # Hook cold-open is THEME-KEYED (fix 2026-07-15). PaperHook (2026-07-14) applies
        # ONLY to the paper worlds — nemock-deep-dive (Dave's deep dives) and cut-bond (Cut &
        # Bond). Midnight-themed projects (the ISO 14971 series, and every deck before the
        # change) keep the Hero3D rotating wireframe sphere, their consistent brand. Do NOT
        # make PaperHook unconditional again: it leaks the paper rebrand into the midnight series.
        if theme in ("cut-bond", "nemock-deep-dive", "brg-deep-dive", "wte-guide", "circumvent"):
            return "PaperHook", {"image": slide.get("image"), "kicker": kicker,
                                 "headline": headline, "accent": accent,
                                 # `stage` is the fallback when a hook has no bespoke art
                                 "stage": slide.get("stage")}
        return "Hero3D", {"kicker": kicker, "headline": headline,
                          "accent": accent, "accentRed": accent2}
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
    if t == "keepcard":
        return "KeepCard", {"image": slide.get("image"),
                            "label": slide.get("label") or headline,
                            "sub": slide.get("sub")}
    if t == "figure":
        return "Figure", {"kicker": kicker, "image": slide.get("image"),
                          "caption": slide.get("caption", ""), "highlight": slide.get("highlight"),
                          "title": slide.get("title", ""), "accent": accent, "accent2": accent2,
                          "imageFromFrac": slide.get("imageFromFrac", 0),
                          "moves": slide.get("moves", []), "assemble": slide.get("assemble"),
                          "marks": slide.get("marks", [])}
    if t == "footage":
        return "Footage", {"image": slide.get("image"), "headline": headline,
                           "accent": accent, "accent2": accent2,
                           "marks": slide.get("marks", []), "fit": slide.get("fit")}
    if t == "highlight":
        return "KineticHeadline", {"kicker": kicker, "headline": headline,
                                   "accent": slide.get("mark") or accent}
    return "KineticHeadline", {"kicker": kicker, "headline": headline, "accent": accent,
                               "accentRed": accent2, "subkicker": slide.get("subkicker", ""),
                               # opt-in papercraft stage scene (PaperStage): whiteboard /
                               # projector / presentation / easel. Absent -> the poster card.
                               "stage": slide.get("stage")}


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
        slide = slides_by_id.get(s["slide"], {})
        comp, fields = _scene_for(slide, theme=sp.data.get("theme", ""))
        sc = {"component": comp, "from": int(round(start * fps)),
              "durationInFrames": max(1, int(round((end - start) * fps))), "fields": fields}
        # act-boundary tear (papercraft-motion-spec.md §4): the scene reveals behind a
        # parting torn seam instead of the cross-fade. Author: "transition": "tear".
        if slide.get("transition") == "tear":
            sc["tear"] = True
        scenes.append(sc)

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
                    "Timeline": ("events", lambda f: [e.get("label", "") for e in (f.get("events") or [])]),
                    # Papercraft equivalents — same per-item narration sync
                    "PaperList": ("items", lambda f: f.get("items") or []),
                    "PaperSteps": ("steps", lambda f: [s.get("title") if isinstance(s, dict) else s
                                                       for s in (f.get("steps") or [])])}
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
        # 3b) figure image-space MARKS (circle/arrow/underline on the art, ride the Ken Burns)
        marks = (sc.get("fields") or {}).get("marks") or []
        for ki, mk in enumerate(marks):
            f = _resolve_phrase(mk.get("cue", ""), segw, s0, fps) if mk.get("cue") else None
            if mk.get("cue") and f is None:
                warnings.append(f"{sid}: figure mark cue unmatched (\"{mk['cue']}\")")
            mk["cueFrame"] = f if f is not None else int(round(dur * (ki + 1) / (len(marks) + 1)))
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
    # `wte-guide` (the waste-to-fuel Operator's Guide) carries NO brand bumper at all: its
    # CTA is like-and-subscribe only — no book, no site wordmark, no cross-brand mark
    # (operator direction 2026-07-29). Enforced here rather than left to each module's
    # `"sting": false` so a forgotten flag can never leak FWF branding into a safety-training
    # video — the exact failure mode the ISO 14971 series hit repeatedly.
    # `circumvent` likewise carries NO brand bumper (operator direction 2026-07-30). It is a
    # Circumvent Global company video with no CTA; it ends on its own circumventglobal.com card.
    # Without this guard it fell through to the legacy `else` below and stamped FOUNDERS WHO
    # FINISH / davesaunders.net onto the end of a Circumvent film — the same cross-brand leak
    # this block already guards wte-guide against.
    _NO_STING = ("wte-guide", "circumvent")
    if sp.data.get("theme") not in _NO_STING and sp.data.get("sting", width >= height):
        # The sting is THEME-KEYED (branding isolation, operator direction 2026-07-15).
        # Each channel owns its brand; nothing here is a global default.
        #   nemock-deep-dive (Dave's deep dives) -> paper-launch PaperSting + davesaunders.net
        #   cut-bond         (Cut & Bond)         -> paper-launch PaperSting, its own wordmark
        #                     (blank default; Cut & Bond is portrait shorts, so sting is off anyway)
        #   brg-deep-dive    (Base Reality Group)  -> BRGPaperSting (BRG's OWN indigo D+rocket
        #                     mark) + baserealitygroup.com. NOT PaperSting: that is Dave's
        #                     personal/book mark, and BRG is a separate brand (2026-07-26).
        #   midnight / other (ISO 14971 series, everything pre-paper) -> the legacy wordmark
        #                     bumper (BrandSting). Do NOT let the paper rebrand leak here.
        theme = sp.data.get("theme", "")
        if theme == "brg-deep-dive":
            INTRO, OUTRO = 3.0, 2.5
            wm = "baserealitygroup.com"
            intro_comp, intro_fields = "BRGPaperSting", {"wordmark": wm}
            outro_comp = "BRGPaperSting"
            outro_fields = {"outro": True, "wordmark": wm}
        elif theme in ("cut-bond", "nemock-deep-dive"):
            # Paper-launch sting (motion-playbook §2F). Intro plays the full launch+wordmark
            # (~3.5s); outro is the calm finished-mark card (~2.5s). The intro length sets the
            # narration offset — see memory gag-splice-sting-offset (3.5s for this engine).
            INTRO, OUTRO = 3.5, 2.5
            wm = "davesaunders.net" if theme == "nemock-deep-dive" else ""
            intro_comp, intro_fields = "PaperSting", ({"wordmark": wm} if wm else {})
            outro_comp = "PaperSting"
            outro_fields = {"outro": True, "wordmark": wm} if wm else {"outro": True}
        else:
            # Legacy wordmark bumper — the midnight brand (masterclass + every pre-paper deck).
            INTRO, OUTRO = 2.5, 2.0
            intro_comp, intro_fields = "BrandSting", {"title": "FOUNDERS WHO FINISH"}
            outro_comp = "BrandSting"
            outro_fields = {"title": "FOUNDERS WHO FINISH", "subtitle": "davesaunders.net"}
        off = int(round(INTRO * fps))
        for sc in scenes:
            sc["from"] += off
        for w in words:
            w["start"] += INTRO
            w["end"] += INTRO
        scenes.insert(0, {"component": intro_comp, "from": 0, "durationInFrames": off,
                          "fields": intro_fields})
        scenes.append({"component": outro_comp, "from": off + int(round(duration * fps)),
                       "durationInFrames": int(round(OUTRO * fps)),
                       "fields": outro_fields})
        audio_from = off
        total = INTRO + duration + OUTRO

    safe_bottom = float(sp.data.get("safe_bottom", 0.12)) + 0.04
    # Cut & Bond seats captions LOW in the bottom third (operator 2026-07-16: the default
    # left them crowding the illustration, with the bottom third empty). The animation is
    # pushed up in Video.tsx (larger content inset) to match. Other themes are unchanged.
    cap_frac = 0.13 if sp.data.get("theme") == "cut-bond" else safe_bottom
    return {
        "width": width, "height": height, "fps": fps,
        "durationInFrames": int(round(total * fps)),
        "audio": "narration.wav", "words": words, "scenes": scenes,
        "captionBottomPx": int(round(height * cap_frac)),
        "captionFontSize": int(round(height * (0.032 if height >= 1600 else 0.026))),
        "audioFrom": audio_from,
        # Visual world: '' (navy studio) or 'paper' (Cut & Bond off-white). Set in project.json.
        "theme": sp.data.get("theme", ""),
        # Optional caption active-word color (e.g. an element's category accent).
        "captionAccent": sp.data.get("captionAccent", ""),
        "_warnings": warnings,
    }


def _stage_images(sp, spec, public):
    """Copy any media asset referenced by a scene into the public dir, rebasing the field to
    the basename. Resolves the deck's path against the project (and, for shorts, the parent).
    Handles every asset-bearing field a component may use (e.g. Cut & Bond's `bottomImage`
    decorative prop on ElementStat, and `video` for its PaperFootage live-action window)."""
    roots = [sp.dir, sp.dir.parent.parent, sp.dir.parent]  # project, then parent (shorts), then shorts/
    # `set` = Papercraft Motion backdrop (papercraft-motion-spec.md §8). Paths under
    # papercraft/ are shared brand set dressing staged wholesale by render() — leave
    # them un-rebased so staticFile('papercraft/...') resolves.
    ASSET_FIELDS = ("image", "bottomImage", "set", "video")

    def _stage_one(img):
        # chibi/ refs are staged from the private pose library by _stage_chibi (which runs
        # after this pass) — leave them untouched here or they'd be dropped as missing.
        if not img or str(img).startswith(("papercraft/", "papercraft-circumvent/", "chibi/")):
            return img
        src = next((r / img for r in roots if (r / img).exists()), None)
        if src is None:
            return None  # missing -> component shows headline/caption only
        dst = Path(img).name
        shutil.copy(src, public / dst)
        return dst

    for scene in spec["scenes"]:
        fields = scene.get("fields") or {}
        for key in ASSET_FIELDS:
            if fields.get(key):
                fields[key] = _stage_one(fields[key])
        for prop in (fields.get("props") or []):
            if isinstance(prop, dict) and prop.get("image"):
                prop["image"] = _stage_one(prop["image"])


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


def _stage_chibi(spec, public, log):
    """Stage chibi presenter poses (deck refs "chibi/<pose>") from the operator's private
    pose library into the render's public dir, rebasing each ref to its staged basename.
    See the CHIBI_DIR note at the top of this module. Missing pose -> ref dropped with a
    warning, never a broken render (matches the doodle library's degrade)."""
    def _one(ref):
        name = str(ref)[len("chibi/"):]
        if name.endswith(".png"):
            name = name[:-4]
        src = CHIBI_DIR / f"{name}.png"
        if not src.exists():
            log(f"remotion: chibi pose missing, ref dropped: {name} (looked in {CHIBI_DIR})")
            return None
        dst = "chibi__" + name.replace("/", "_") + ".png"
        if not (public / dst).exists():
            shutil.copy(src, public / dst)
        return dst

    for scene in spec["scenes"]:
        fields = scene.get("fields") or {}
        for key in ("image", "bottomImage"):
            if str(fields.get(key) or "").startswith("chibi/"):
                fields[key] = _one(fields[key])
        for prop in (fields.get("props") or []):
            if isinstance(prop, dict) and str(prop.get("image") or "").startswith("chibi/"):
                prop["image"] = _one(prop["image"])


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
    # Brand static assets that components load via staticFile (NOT via a deck fields.image)
    # must be copied into the fresh render public dir. The PaperSting sting loads these.
    for _name in ("sting_paper_d.png", "sting_paper_rocket.png"):
        _src = REMOTION_DIR / "public" / _name
        if _src.exists():
            shutil.copy(_src, public / _name)
    # BRGPaperSting's mark (brg-deep-dive world) — BRG's own logo, staged from the PROJECT's
    # brand dir so each BRG project stays self-contained. Missing -> the sting still renders
    # (wordmark only), never a broken image.
    # Shorts render as sub-projects under <parent>/shorts/<slug>/, which have no brand dir of
    # their own, so a project-dir-only lookup silently dropped BRG's mark from every Short and
    # the sting fell back to wordmark-only (caught on #50's Shorts). Walk the same roots
    # _stage_images uses: the project, then the shorts parent.
    _brg_mark = next((r / "brand" / "brg-sting-mark.png"
                      for r in (sp.dir, sp.dir.parent.parent, sp.dir.parent)
                      if (r / "brand" / "brg-sting-mark.png").exists()), None)
    if _brg_mark:
        shutil.copy(_brg_mark, public / "brg_sting_mark.png")
    elif sp.data.get("theme") == "brg-deep-dive":
        log("remotion: WARNING brg-deep-dive sting mark missing "
            "(expected <project>/brand/brg-sting-mark.png) — sting renders wordmark-only")
    # Papercraft Motion shared set dressing (papercraft-motion-spec.md §8): staged as a
    # directory so deck `set`/`props` refs like "papercraft/desk_wide_a.jpg" resolve.
    _pcraft = REMOTION_DIR / "public" / "papercraft"
    if _pcraft.exists():
        shutil.copytree(_pcraft, public / "papercraft", dirs_exist_ok=True)
    # Circumvent's own library (sequestered from the FWF world, 2026-07-30). Staged the
    # same way so deck refs like "papercraft-circumvent/sets/set_ranch.png" resolve.
    _cvg = REMOTION_DIR / "public" / "papercraft-circumvent"
    if _cvg.exists():
        shutil.copytree(_cvg, public / "papercraft-circumvent", dirs_exist_ok=True)
    # Blank paper substrates (papercraft-substrate-plan.md). Unlike the two libraries above
    # these are never named in a deck — components pick a substrate internally — so they
    # must be staged unconditionally or PaperNote renders nothing.
    for _lib in ("papercraft-notes", "papercraft-cards", "papercraft-fixings",
                 "papercraft-grounds", "papercraft-stages"):
        _sub = REMOTION_DIR / "public" / _lib
        if _sub.exists():
            shutil.copytree(_sub, public / _lib, dirs_exist_ok=True)
    _stage_images(sp, spec, public)
    _stage_doodles(spec, public, log)
    _stage_chibi(spec, public, log)
    # CTA scenes show the brand book cover unless the project opts out with
    # "cta_book": false in project.json (e.g. masterclass modules use no book cover).
    # wte-guide never shows the book: like-and-subscribe is its only CTA (2026-07-29).
    _cta_book = sp.data.get("cta_book", True) and sp.data.get("theme") != "wte-guide"
    if _cta_book and any(s["component"] in ("CTA", "PaperBookCTA") for s in spec["scenes"]):
        bc_dir = REMOTION_DIR.parent / "book_cover"
        bc = next(iter(sorted(bc_dir.glob("*.png"))), None) if bc_dir.exists() else None
        if bc:
            shutil.copy(bc, public / "book_cover.png")
            for s in spec["scenes"]:
                if s["component"] in ("CTA", "PaperBookCTA"):
                    s["fields"]["image"] = "book_cover.png"
    props = stage / "props.json"
    props.write_text(json.dumps(spec))

    aspect = sp.data.get("aspect", "9:16").replace(":", "x")
    outdir = sp.dir / "video"
    outdir.mkdir(exist_ok=True)
    out = Path(out) if out else outdir / f"explainer_{aspect}.mp4"

    npx = shutil.which("npx") or "npx"
    cmd = [npx, "remotion", "render", "src/index.ts", "Video", str(out),
           f"--props={props}", f"--public-dir={public}", "--log=error",
           "--timeout=300000"]  # generous delayRender timeout (slow disk I/O tolerance)
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

    # PROVE the master decodes before calling this a success. A returncode of 0 is
    # not evidence of a good file: #55 (2026-08-05) rendered "successfully" under
    # encoder contention and produced a structurally perfect, corrupt bitstream that
    # only surfaced when the music mux choked on it. Fail loudly here rather than
    # hand a broken master to packaging. Slice previews are skipped (no full file).
    if not frames:
        from . import qa as _qa
        errs = _qa.decode_check(out)
        if errs:
            raise RuntimeError(
                f"render produced a file that does not decode cleanly "
                f"({len(errs)} error(s) in the first 90s) — treating as a FAILED render, "
                f"not a warning. First: {errs[0][:160]}\n"
                f"This is the #55 failure mode (encoder contention -> corrupt h264). "
                f"Check for other encodes running and re-render.")
        log("render: decode check clean (no bitstream errors in the first 90s)")

    return {"engine": "remotion", "video": str(out), "scenes": len(spec["scenes"]),
            "duration_s": round(spec["durationInFrames"] / spec["fps"], 2),
            "music": music, "decode_check": "clean"}
