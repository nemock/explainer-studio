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
# optional). Since 2026-08-07 the presenter is a LAYER on every scene rather than a prop
# on a few: author `chibi` on a deck slide to pick that scene's pose, otherwise the engine
# rotates one in (_assign_chibi). Personal shows only — never Circumvent. Override the
# root with $EXPLAINER_CHIBI_DIR (e.g. to point at a future v3).
CHIBI_DIR = Path(os.environ.get(
    "EXPLAINER_CHIBI_DIR",
    "/Volumes/Casima/claudeCode/dave_chibi_character/v2/poses_normalized_tight"))

# Presenter rotation (operator directive 2026-08-07). Dave's vision is a chibi on EVERY
# slide, not a cameo on one or two: "if the chibis are only on one or two slides, then they
# don't actually make sense at all." So the engine assigns a pose to every scene — an
# authored `chibi` on the deck slide wins, otherwise it rotates this pool.
#
# The pool is deliberately NEUTRAL. An emotional pose that contradicts the beat is worse
# than a calm one, so joy/anger/despair stay opt-in per slide; these read as "presenting,
# listening, thinking" and sit under any line. He stands at the RIGHT of the frame, so
# asymmetric poses here are the ones that gesture toward the content (viewer's left) or
# read symmetrically — the library's other pointing poses aim the wrong way from that side
# (the character library's own README warns that this model mirrors handedness freely).
CHIBI_ROTATION = (
    "01-presenting-right",      # open palm toward the content
    "36-talking-hands",
    "05-thinking",
    "29-leaning-on-edge",
    "08-presenting-both-hands",
    "43-deadpan",
    "27-holding-coffee-mug",
    "54-signature-brow",
    "12-counting-one",
    "04-arms-crossed",
)

# DEEP DIVES ONLY (operator decision 2026-08-10). The presenter shipped 2026-08-07 for
# the six personal shows as well, but every one of them renders portrait-only
# (9:16 + 4:5), where the presenter is skipped — so it never actually appeared on any of
# them, and the docs telling authors to place it were writing dead JSON. Rather than
# leave that as an accident of geometry, the six worlds are blocked outright until the
# operator settles how a stand-in should work in a vertical frame ("still experimenting
# with their use; restrict to the deep dives for now"). Cut & Bond and the navy ISO world
# are other looks entirely and were never on this list; a project may opt those in.
# Themes ALLOWED to opt in. Being on this list no longer switches the presenter on by
# itself (2026-09-10) — a project must also set "presenter": {"enabled": true}.
CHIBI_THEMES = ("nemock-deep-dive",)

# Themes that never carry Dave's stand-in. A hard rule, not a default: a project file
# cannot switch these on with "presenter": {"enabled": true}.
#   circumvent           — a SEPARATE BRAND (2026-08-06 brand lock). Permanent.
#   the six show worlds  — PAUSED 2026-08-10 pending a portrait design (see above).
#                          To re-enable one, move it back into CHIBI_THEMES.
#   plg-guide            — the Product Leadership Operator's Guide. Operator, 2026-08-11:
#                          "keep the chibi characters out of this video project." A hard
#                          block rather than mere absence from CHIBI_THEMES, because
#                          absence is a default and this is a decision — twelve modules
#                          built across many sessions is exactly where a default gets
#                          flipped by someone who did not know it was deliberate.
CHIBI_NEVER = ("circumvent", "fwf", "mmt-tangerine", "ftt-study",
               "wsc-goldenrod", "ttd-indigo", "fmf-alarm", "plg-guide")

# Which way a pose GESTURES, in viewer terms — only poses with confirmed visual evidence
# (the operator's #56 screenshot, the contact sheet, rendered stills). Everything absent
# is neutral and never flipped. Do NOT infer facing from a filename: the pose model
# mirrors handedness freely and the library README warns "presenting-right" may present
# left. The operator's rule this serves (2026-08-07): the presenter must be part of the
# action — a pose pointing off-frame "just looks randomly chosen". So a directional pose
# is seated on the side that aims its gesture AT the content, or mirrored so it does.
CHIBI_FACING = {
    "01-presenting-right": "left",     # open palm sweeps to the viewer's left (stills)
    "07-presenting-left": "right",
    "11-pointing-side": "right",       # points viewer-right (operator screenshot, #56)
    "26-carrying-heavy-box": "left",   # walks/leans viewer-left (contact sheet + still)
    "28-walking-side": "left",
    "29-leaning-on-edge": "left",      # the ledge he leans on is at his viewer-left
}


def _chibi_side(slide):
    """Pick the emptier bottom corner for the presenter, per scene. Only schematics put
    authored content low enough to collide (nodes reach y 0.65); everything else keeps
    its lower corners quiet by composition, so the default corner is fine."""
    if slide.get("type") != "schematic":
        return None
    left = right = 0.0
    for n in slide.get("nodes", []):
        if n.get("y", 0) < 0.42:      # above the presenter's band entirely
            continue
        x, w = n.get("x", 0.5), n.get("w", 0.2)
        left += max(0.0, min(x + w / 2, 0.32) - (x - w / 2))
        right += max(0.0, (x + w / 2) - max(x - w / 2, 0.68))
    if left == right:
        return None
    return "left" if left < right else "right"


def _assign_chibi(scenes, slides_by_id, seg_slides, data, log):
    """Put a presenter pose on every scene. Returns the `presenter` spec block (or None).

    OFF BY DEFAULT EVERYWHERE (operator directive 2026-09-10). Opt IN per project with
    "presenter": {"enabled": true} in project.json; tune the size with "charHeightFrac"
    (brand spec 0.18-0.22 of frame height, the CHARACTER's height rather than the pose
    canvas, which carries transparent padding).

    It used to default ON for every theme in CHIBI_THEMES, which meant a deep dive got a
    chibi in the corner of every scene unless someone remembered to switch it off. Dave,
    seeing it in #59's first render: "Suppress the chibi and re-render... completely
    suppress it from automatic use. If I explicitly add it, there should probably be a
    flag that allows it, but it is not a default style."

    The reason this is a DEFAULT change rather than another per-project opt-out: the
    ON-CAMERA-COLD-OPEN spec already excluded the presenter while the chibi experiment is
    unsettled, and #59 still rendered fifteen minutes of video with one in frame, because
    the exclusion lived in prose and the default lived in code. A default beats a document
    every time. CHIBI_THEMES is now the list of themes ALLOWED to opt in; CHIBI_NEVER
    still hard-blocks, and a project file cannot override it.
    """
    cfg = dict(data.get("presenter") or {})
    theme = data.get("theme", "")
    if theme in CHIBI_NEVER:
        if cfg.get("enabled"):
            log(f"remotion: the chibi presenter is not available on the {theme} theme — skipped "
                f"(deep dives only; see CHIBI_NEVER)")
        return None
    portrait = data["height"] > data["width"]
    if not cfg.get("enabled"):
        return None                      # opt-in only; silence is OFF
    if theme not in CHIBI_THEMES:
        log(f"remotion: chibi presenter requested but the {theme} theme is not in "
            f"CHIBI_THEMES — skipped")
        return None
    if portrait:
        # 9:16 has no width to give away; the lane would eat a third of the frame.
        log("remotion: chibi presenter requested on a portrait render — skipped")
        return None

    # Resolve authored poses FIRST so the rotation can dodge its neighbours on both
    # sides. Without the look-ahead, a rotated pose can land on the same pose the next
    # slide authored, and a pose held across a cut reads as a frozen frame rather than
    # as a presenter who moved.
    authored = []
    for i in range(len(scenes)):
        slide = slides_by_id.get(seg_slides[i], {}) if i < len(seg_slides) else {}
        pose = slide.get("chibi")
        if pose:
            pose = str(pose)
            if pose.startswith("chibi/"):
                pose = pose[len("chibi/"):]
        authored.append(pose or None)

    rot = 0
    prev = None
    for i, scene in enumerate(scenes):
        pose = authored[i]
        if not pose:
            nxt = authored[i + 1] if i + 1 < len(authored) else None
            for _ in range(len(CHIBI_ROTATION)):
                cand = CHIBI_ROTATION[rot % len(CHIBI_ROTATION)]
                rot += 1
                if cand != prev and cand != nxt:
                    pose = cand
                    break
            else:  # pool too small to dodge both — take the next rather than stall
                pose = CHIBI_ROTATION[rot % len(CHIBI_ROTATION)]
                rot += 1
        scene["chibi"] = "chibi/" + pose
        slide = slides_by_id.get(seg_slides[i], {}) if i < len(seg_slides) else {}

        # Corner + facing (operator directive 2026-08-07 v2): authored side wins, then
        # the emptier corner, then — for a directional pose — the side that aims its
        # gesture at the content. Seating beats mirroring (no mirrored hair/wardrobe),
        # so flip only when the density choice forces the pose onto its off-side.
        facing = CHIBI_FACING.get(pose)
        side = slide.get("chibiSide") or _chibi_side(slide)
        if not side:
            side = ("left" if facing == "right" else "right") if facing else "right"
        scene["chibiSide"] = side
        # Schematics fill their corners with auto-sized post-its, so the presenter drops
        # to the bottom of the brand size range there; still-checked 2026-08-07.
        if slide.get("type") == "schematic":
            scene["chibiH"] = 0.17
        if "chibiFlip" in slide:
            if slide["chibiFlip"]:
                scene["chibiFlip"] = True
        elif facing == side:  # gesture aims off-frame from this corner — mirror it
            scene["chibiFlip"] = True
        prev = pose
    # 0.22 = the top of the brand spec's 18-22%. At 0.18 he reads as a sticker in a
    # 16:9 frame rather than a person presenting, and these decks carry enough empty
    # cream that the content has the width to give.
    return {"enabled": True, "charHeightFrac": float(cfg.get("charHeightFrac", 0.22))}


def _parse_stat(value):
    """Parse a deck stat value ('−$1,000', '$500', '93%') -> (to:float, prefix:str,
    suffix:str) or None when the value is not a plain magnitude.

    FULL MATCH, not a search (2026-09-14). This used to `re.search` the first number out
    of the string and only refuse when a letter followed a digit, so anything numeric-ish
    and letter-free was accepted and then rendered as that first number alone. A scan of
    all 445 decks on this machine found 93 stat slides shipping a truncated value:
    '6:48' drew `6` while the narration said six forty-eight, '40–86%' drew `40`, 'Q2 2026'
    drew `2`, 'ASTM D975' drew `975`, 'June 30, 2026' drew `30`, '8 / 8' drew `8`. A range,
    a timecode, a date and a part number are not magnitudes and there is no honest counter
    form for them — they belong in the headline treatment, which draws the authored string
    verbatim (the fall-through both callers already have).

    The suffix comes back too: the callers passed `prefix` but never `%`, so every
    percentage authored as a `stat` lost its sign on screen — 111 slides across the
    catalog, '85%' drawn as `85`."""
    if not value:
        return None
    s = str(value).replace("−", "-").replace(",", "").strip()
    if not re.fullmatch(r"-?\$?\d+(?:\.\d+)?%?", s):
        return None
    # Take the sign from the string, not from the number match: on "-$1000" the `$` sits
    # between the sign and the digits, so a `-?\d+` search skips past the minus and the
    # value came back POSITIVE — on the very example this docstring advertises.
    num = float(re.search(r"\d+(?:\.\d+)?", s).group(0))
    return (-num if s.startswith("-") else num), ("$" if "$" in s else ""), ("%" if "%" in s else "")


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
    decks never break mid-migration.

    `props` pass through on EVERY paper type (2026-08-07). Until then only the map's
    "hook" branch forwarded them, so a prop authored on any other slide was silently
    dropped — the deck looked right and rendered without it. Every Paper* component now
    renders them through PaperProps (bottom-corner cut-outs); the Cvg* family has taken
    props on every type since it was written, and this brings the paper family level.
    Set dressing only — the chibi presenter is a separate global layer (_assign_chibi)."""
    comp = _papercraft_component(slide, t, kicker, accent, headline)
    if not comp:
        return None
    name, fields = comp
    fields.setdefault("props", slide.get("props") or [])
    return name, fields


def _papercraft_component(slide, t, kicker, accent, headline):
    """deck type -> (Paper* component, fields). See _papercraft_scene, its only caller."""
    if t == "statement":
        return "PaperStatement", {"kicker": kicker, "headline": headline, "accent": accent,
                                  "subkicker": slide.get("subkicker", "")}
    if t == "highlight":
        # A highlight names the words it pops in `mark` (deck-playbook §Text slides), and
        # the classic branch below has always read it first. This one passed `accent` alone
        # until 2026-09-26, so every highlight authored the documented way rendered in plain
        # ink: Product Leadership modules 1, 3, 4 and 6 (14 slides), 12 on the deep dives.
        return "PaperStatement", {"kicker": kicker, "headline": headline,
                                  "accent": slide.get("mark") or accent,
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
        # `title` is the header between the kicker and the trays, its `accent` words coloured
        # the way a Figure's persistent title colours them. Until 2026-09-26 this passed
        # kicker/left/right only and PaperCompare never read a title, so 16 Product
        # Leadership compares (module 5: 5, module 6: 11) and 5 on #55 rendered without
        # their line, e.g. module 6's "Scoring the thing your strategy is built on".
        return "PaperCompare", {"kicker": kicker, "title": slide.get("title", ""),
                                "accent": accent, "left": slide.get("left", {}),
                                "right": slide.get("right", {})}
    if t == "delta":
        # Same component, same header line: a delta's `title` + `accent` pass through as a
        # compare's do (2026-09-26; #55 s08 s63 and #56 s37 had lost theirs). Its `kind` and
        # `change` badge still have no paper rendering, so the dropped-field guard refuses them.
        return "PaperCompare", {"kicker": kicker, "title": slide.get("title", ""), "accent": accent,
                                "left": {"title": slide.get("from_label", ""), "value": slide.get("from", "")},
                                "right": {"title": slide.get("to_label", ""), "value": slide.get("to", "")}}
    # The last four types with no papercraft equivalent (2026-08-12). reframe gets a real
    # component because the beat IS a sentence changing; the other three reuse components
    # that already say the right thing on paper, rather than inventing near-duplicates.
    if t == "reframe":
        return "PaperReframe", {"kicker": kicker, "before": slide.get("before", ""),
                                "strike": slide.get("strike", ""), "after": slide.get("after", "")}
    if t == "statgrid":
        return "PaperList", {"kicker": kicker, "title": slide.get("title", ""),
                             "items": [f'{x.get("value","")}  {x.get("label","")}'.strip()
                                       for x in (slide.get("stats") or [])]}
    if t == "timeline":
        return "PaperSteps", {"kicker": kicker,
                              "steps": [f'{e.get("date","")} — {e.get("label","")}'.strip(" —")
                                        for e in (slide.get("events") or [])]}
    if t == "stat":
        # PaperCounter does ARITHMETIC on `value` (value / 10 for the chip count, then
        # value * progress), so it needs a number. Handing it the deck's raw string made
        # "2.3M" / 10 -> NaN -> `inputRange must contain only finite numbers`, which is a
        # hard render abort, not a bad-looking slide. The classic `stat` branch has always
        # parsed first; this one was added 2026-08-14 without it and took #57's render down.
        # Unparseable magnitudes ("2.3M", "$500M") return None here exactly as they do in
        # the classic map, and fall through to the headline treatment — there is no honest
        # counter form for a number the parser cannot read.
        parsed = _parse_stat(slide.get("value"))
        if not parsed:
            return None
        to, prefix, suffix = parsed
        return "PaperCounter", {"kicker": kicker, "value": to, "prefix": prefix,
                                "suffix": suffix, "label": slide.get("label", "")}
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
                                "headTop": slide.get("head_top"),
                                "beats": slide.get("beats", []), "kicker": kicker,
                                "headline": headline, "accent": accent}
    return None


# Themes rendered by the Cvg scene family (set-driven, type on the world's paper scrim).
# circumvent pioneered it (2026-07-30); the six personal-show worlds joined 2026-08-06.
_CVG_STYLE_THEMES = ("circumvent", "fwf", "mmt-tangerine", "ftt-study",
                     "wsc-goldenrod", "ttd-indigo", "fmf-alarm")

# SHOW TITLE PANEL (2026-09-03, operator request — decision doc
# make_money/routine_changes/2026-09-03-show-title-panels.md). The six personal-show
# worlds carry NO wordmark bumper (see _NO_STING below: a bumper is another brand's
# mark, and the branding-isolation rule keeps it off them), so until this table every
# episode opened cold on its hook and was identifiable only by the kicker. This is the
# show's OWN name card: its locked paper mark, the owning brand as kicker, the show
# name, "with Dave Saunders". Rendered by CvgTitle inside the show's world tokens, so
# the colours match the episode by construction. Circumvent is deliberately absent —
# it is a client brand with its own open and close. Held 2.4 s (operator: keep it at
# 2.4). Opt out per project with `"title_panel": false` in project.json.
SHOW_TITLE_SECONDS = 2.4
_SHOW_TITLE = {
    "fwf": {"mark": "papercraft-fwf/mark_fwf.png", "kicker": "Founders Who Finish",
            "title": "Daily\nFounder Tip", "sub": "with Dave Saunders"},
    "mmt-tangerine": {"mark": "papercraft-mmt/mark_mmt.png", "kicker": "Base Reality Group",
                      "title": "Monday\nMedTech", "sub": "with Dave Saunders"},
    "ftt-study": {"mark": "papercraft-ftt/mark_ftt.png", "kicker": "Base Reality Group",
                  "title": "Founder Tip\nTuesday", "sub": "with Dave Saunders"},
    "wsc-goldenrod": {"mark": "papercraft-wsc/mark_wsc.png", "kicker": "Base Reality Group",
                      "title": "Who Signs\nthe Check", "sub": "Wednesdays with Dave Saunders"},
    # The Teardown's world accent is a deep orange; the panel takes the locked
    # safety orange (#F2762E) so the kicker and strip read on the indigo ground.
    "ttd-indigo": {"mark": "papercraft-ttd/mark_ttd.png", "kicker": "Base Reality Group",
                   "title": "The\nTeardown", "sub": "Thursdays with Dave Saunders",
                   "accent": "#F2762E"},
    "fmf-alarm": {"mark": "papercraft-fmf/mark_fmf.png", "kicker": "Base Reality Group",
                  "title": "Failure Modes\nFriday", "sub": "with Dave Saunders"},
}


def intro_offset_s(sp):
    """Seconds of intro (title panel or brand sting) ahead of the narration in the
    LAST render of this project, read back from the staged Remotion props. Every tool
    that maps timeline seconds onto the rendered mp4 (stills, qa, tools/frame_qc.py)
    must add this: the timeline is narration time, the mp4 is narration time plus the
    intro. 0.0 when nothing has been rendered yet or the project has no intro."""
    props = sp.work / "remotion" / "props.json"
    try:
        d = json.loads(props.read_text())
    except (OSError, ValueError):
        return 0.0
    fps = float(d.get("fps") or 30)
    return float(d.get("audioFrom") or 0) / fps


# Per-theme closing wordmark, used ONLY as the last-resort fill for a content-less
# `cta`/`payoff` slide (see _cta_fallback). Same brand-per-theme mapping the outro sting
# uses below — kept in step with it, never a global default (branding-isolation rule).
_CTA_WORDMARK = {
    "brg-deep-dive": "baserealitygroup.com",
    "brg-paper": "baserealitygroup.com",
    "nemock-deep-dive": "davesaunders.net",
    "fwf": "davesaunders.net",
    "circumvent": "circumventglobal.com",
}


def _cta_fallback(theme, log=None):
    """Headline for a `cta`/`payoff` slide that carries no text of its own.

    The deck-playbook documents `cta` as "brand-driven (pulls DECK.brand.cta.*)", which is
    true of the LEGACY deck engine. Remotion has no such plumbing: it maps cta -> CTA /
    PaperBookCTA, both of which print `fields.headline` and render an EMPTY card when it is
    blank. #50 shipped that way — a field-less `cta` closed the video with ~25s of bare
    background, past deck-census, past validate, past publish, because nothing on the
    Remotion path ever asserted the closing card had content. This makes the type behave the
    way the playbook already promises, so an under-specified close degrades to a branded end
    card instead of dead air. It is a NET, not a licence to omit the fields: deck_census
    fails the deck outright (see _empty_cta_slides there), and the fill is logged.
    """
    wm = _CTA_WORDMARK.get(theme or "", "")
    headline = wm or "Subscribe."
    if log:
        log(f"[cta] closing slide had no headline — filled with {headline!r} "
            f"(theme={theme or 'default'!r}). Author a headline on the cta/payoff slide.")
    return headline


_CVG_CONTENT_FIELDS = ("value", "label", "term", "definition", "quote", "word",
                       "before", "after", "end_label", "sub", "title")


def _cvg_salvage(slide):
    """Last-resort text for a Cvg slide that would otherwise render empty. Sweeps the
    content-bearing deck fields and the common list containers, in authoring order, and
    returns a single printable string. Deliberately dumb: it exists so an unhandled type
    degrades to readable type-on-a-set instead of a blank frame, not to lay anything out."""
    parts = []
    for f in _CVG_CONTENT_FIELDS:
        v = slide.get(f)
        if v is None:
            continue
        v = str(v).strip()
        if v and v not in parts:
            parts.append(v)
    for row in (slide.get("items") or slide.get("steps") or slide.get("stats")
                or slide.get("stages") or slide.get("events") or []):
        if isinstance(row, dict):
            row = " ".join(str(row.get(k)).strip() for k in ("label", "date", "title", "value")
                           if row.get(k) is not None)
        row = str(row).strip()
        if row and row not in parts:
            parts.append(row)
    return " ".join(parts).strip()


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
    # stat / statgrid: the Cvg family has no counter or grid component, and until
    # 2026-08-12 both fell through to CvgScene, which prints ONLY `headline` — so the
    # figure and its label were dropped and the slide rendered as a set with a kicker
    # and nothing else. It shipped that way twice (FMF 2026-08-07 s3 lost "4 deaths,
    # 2,557 serious injuries"; MMT 2026-08-10 s4/s6/s9), past deck_census, past
    # validate, past publish, because the census treats `stat` as a type that draws
    # its own figure — true of the classic StatCounter, false here. Compose the
    # authored numbers into text the Cvg components already print. Same doctrine as
    # _cta_fallback: never silently drop authored content.
    if t == "stat":
        value = str(slide.get("value") or "").strip()
        label = str(slide.get("label") or "").strip()
        text = " ".join(x for x in (value, label) if x)
        return "CvgScene", {**common, "headline": text or headline,
                            "accent": accent or ([value] if value else [])}
    if t == "statgrid":
        items = [": ".join(x for x in (str(s.get("value", "")).strip(),
                                       str(s.get("label", "")).strip()) if x)
                 for s in (slide.get("stats") or []) if isinstance(s, dict)]
        items = [i for i in items if i]
        return "CvgList", {**common, "items": items or _items(slide),
                           "title": slide.get("title", ""), "ordered": False}
    # reframe: the beat where a sentence changes. Until 2026-08-20 this type had NO branch
    # here and fell through to the CvgScene catch-all, which prints only `headline` — so
    # before/strike/after were dropped and the slide held the frame with a kicker and
    # nothing else. TTD 2026-08-13 s8 was blocked for exactly that (~5.9s of empty card on
    # the episode's pivot beat). Third type the catch-all has swallowed, after stat and
    # statgrid on 2026-08-12: add a branch for any new deck type, never a fall-through.
    if t == "reframe":
        return "CvgReframe", {**common, "before": slide.get("before", "") or headline,
                              "strike": slide.get("strike", ""),
                              "after": slide.get("after", "")}
    # ring / progress: FOURTH type the catch-all swallowed (MMT 2026-08-24 s9 — 13.6s of
    # empty corridor while Dave narrated "about twelve percent of eligible patients
    # currently get a thrombectomy", the number the whole story was built on). The type is
    # legal in both other families (PaperCounter line ~384, Ring line ~664), so nothing
    # upstream complained. The `%` suffix matches PaperCounter's `suffix: "%"`, and is
    # skipped when the author already wrote one.
    if t in ("ring", "progress"):
        raw = slide.get("value")
        value = "" if raw is None else str(raw).strip()
        if value and not value.endswith("%"):
            value = f"{value}%"
        label = str(slide.get("label") or "").strip()
        text = " ".join(x for x in (value, label) if x)
        return "CvgScene", {**common, "headline": text or headline,
                            "accent": accent or ([value] if value else [])}
    # The remaining classic data-viz types. Each carries its content in fields CvgScene
    # never prints, so each was a blank card waiting for the deck that reached for it.
    # Composed into components the Cvg family already has rather than left to fall through.
    if t == "pictograph":
        filled, total = slide.get("filled"), slide.get("total")
        head = f"{filled} of {total}" if filled is not None and total is not None else ""
        label = str(slide.get("label") or "").strip()
        text = " ".join(x for x in (head, label) if x)
        return "CvgScene", {**common, "headline": text or headline,
                            "accent": accent or ([head] if head else [])}
    if t in ("funnel", "waterfall", "timeline", "diagram", "trend", "ranked"):
        rows = (slide.get("stages") or slide.get("events") or slide.get("bars")
                or slide.get("points") or slide.get("steps") or [])
        items = []
        for r in rows:
            if isinstance(r, dict):
                left = str(r.get("label") or r.get("date") or r.get("title") or "").strip()
                right = str(r.get("value") if r.get("value") is not None else "").strip()
                items.append(": ".join(x for x in (left, right) if x))
            elif r is not None:
                items.append(str(r).strip())
        items = [i for i in items if i]
        if t == "waterfall":
            for edge in ("start", "end"):
                e = slide.get(edge) or {}
                if isinstance(e, dict) and (e.get("label") or e.get("value") is not None):
                    row = ": ".join(x for x in (str(e.get("label") or "").strip(),
                                                str(e.get("value") if e.get("value") is not None else "").strip()) if x)
                    items.insert(0, row) if edge == "start" else items.append(row)
        if items:
            return "CvgList", {**common, "items": items,
                               "title": slide.get("title", ""), "ordered": False}
        tail = str(slide.get("end_label") or slide.get("label") or "").strip()
        return "CvgScene", {**common, "headline": tail or headline}
    if t == "keepcard":
        return "CvgScene", {**common, "headline": slide.get("label") or headline,
                            "subkicker": slide.get("sub") or common["subkicker"]}
    if t == "quote":
        return "CvgScene", {**common, "headline": slide.get("quote") or headline,
                            "attrib": slide.get("attribution") or slide.get("source", "")}
    if t == "cta":
        # Centered end card (operator layout direction 2026-08-06): one-line headline,
        # brand mark centered beneath, correct in BOTH aspects. `mark` may come from a
        # dedicated deck field or the first props image (older decks).
        mark = slide.get("mark") or next(
            (p.get("image") for p in (slide.get("props") or []) if isinstance(p, dict) and p.get("image")), None)
        return "CvgCta", {**common, "props": [], "mark": mark}
    # statement / hook / payoff / highlight / anything else: type on the set.
    #
    # LAST RESORT (2026-08-24). Enumerating branches has now failed four times in the same
    # way — stat, statgrid, reframe, ring — because a type is legal upstream, carries its
    # content in fields CvgScene does not print, and renders as a set with a kicker and
    # nothing else. Every fix so far added the one missing branch and left the shape of the
    # bug intact. This net closes the shape: if the slide would print NOTHING, salvage
    # whatever authored content it has rather than emitting a blank card. Adding a proper
    # branch above is still the right fix for any type that deserves real layout; this only
    # guarantees the failure is legible instead of silent.
    if not str(headline).strip():
        salvage = _cvg_salvage(slide)
        if salvage:
            return "CvgScene", {**common, "headline": salvage}
    return "CvgScene", common


def _scene_for(slide, theme="", warn=None):
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

    # The on-camera cold open (references/paper-world/ON-CAMERA-COLD-OPEN.md). Mapped
    # ABOVE the theme dispatch because the paper set is an asset, not a palette: the
    # component composites real footage behind a cut hole in whatever plate it is given.
    # `screen` is the measured rect of that hole — author it from tools/key_screen.py's
    # sidecar JSON, never by eye. `startAtSec` and `pullBack` are filled in by build_spec.
    if t == "oncamera":
        # `patches` was missing from this list until 2026-08-14 and #57 rendered with the
        # camera's watermark still showing: the deck authored it, the component supported
        # it, and the type map dropped it in between with no warning. Exactly the failure
        # this file's own notes describe for figure `title` and for `source_url` — an
        # authored field lost in the mapping, where nothing errors and the census still
        # passes. The still-tests missed it because they passed fields to the component
        # directly and never went through _scene_for.
        return "PaperMonitor", {"set": slide.get("set") or "papercraft/desk_monitor.png",
                                "video": slide.get("video"),
                                "screen": slide.get("screen"),
                                "screenWidthFrac": slide.get("screen_width_frac"),
                                "pullBackSecs": slide.get("pull_back_secs"),
                                "patches": slide.get("patches") or [],
                                "bleed": slide.get("bleed")}

    accent = slide.get("accent", []) or []
    accent2 = slide.get("accent2", []) or []
    headline = slide.get("headline") or slide.get("title") or slide.get("word") or ""

    # A closing card with nothing to print renders an EMPTY frame on every Remotion path
    # (CTA, PaperBookCTA and CvgCta all just print fields.headline). Fill it here — above the
    # Cvg / papercraft / classic dispatch — so no route can emit a blank close. See
    # _cta_fallback for why the type is under-specified in the first place.
    if t in ("cta", "payoff") and not headline:
        headline = _cta_fallback(theme, log=warn)

    # Papercraft style map. nemock-deep-dive (Dave's book/davesaunders.net deep dives) and
    # brg-deep-dive (the Base Reality Group series, added 2026-07-26) both render the Paper*
    # family; they differ by ink/accent (ink.tsx) and by their stings, not by the type map.
    # wte-guide (the waste-to-fuel Operator's Guide, 2026-07-29) joins the family: the
    # operator asked for heavy paper-craft throughout, in the BRG palette.
    # Circumvent gets its OWN scene family (2026-07-30). The shared Paper* components
    # print every line on a rounded cream card over a gradient table, which reads as a UI
    # panel pasted onto the generated paper art. Cvg* scenes drop the card: the set fills
    # the frame, cut-outs stand in it, type sits on the paper. Checked BEFORE the shared
    # papercraft map so it wins for these themes only.
    # 2026-08-06: the Cvg family is now the SHARED renderer for all six personal-show
    # worlds (video brand system cutover) — world tokens in brands/papercraft.ts +
    # ink.tsx carry each show's palette; the scene code is common. Adding a show =
    # tokens + a theme key, never a new scene family.
    if theme in _CVG_STYLE_THEMES:
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
    # plg-guide joined 2026-08-12 (operator: "every slide composed with magnific-papercraft
    # elements"). It is a light world like brg-deep-dive, but the blocker recorded above is
    # now clearable: the lightTint/lightSurround tokens landed 2026-08-07, six days AFTER
    # that exclusion, and PAPER_PLG uses them so the table is the same #f5f0eb cream the
    # figures and schematics already sit on. One backdrop, not two.
    if theme in ("nemock-deep-dive", "wte-guide", "circumvent", "plg-guide"):
        pc = _papercraft_scene(slide, t, kicker, accent, headline)
        if pc:
            return pc

    if t == "hook":
        # Hook cold-open is THEME-KEYED (fix 2026-07-15). PaperHook (2026-07-14) applies
        # ONLY to the paper worlds — nemock-deep-dive (Dave's deep dives) and cut-bond (Cut &
        # Bond). Midnight-themed projects (the ISO 14971 series, and every deck before the
        # change) keep the Hero3D rotating wireframe sphere, their consistent brand. Do NOT
        # make PaperHook unconditional again: it leaks the paper rebrand into the midnight series.
        # plg-guide added 2026-08-26. It was in the papercraft list above but not this
        # one, and the gap only showed on a hook with no `set`/`beats` — every LONG-FORM
        # hook has a set, so _papercraft_component caught them all and this branch was
        # never reached. Shorts build their hook slide from the plan (`_hook_slide`), which
        # has no set, so the first Short cut for this series opened on the Hero3D wireframe
        # in STUDIO GREEN — the exact off-brand leak `accent2 == accent` exists to prevent,
        # on the one frame that decides whether a Short gets watched.
        if theme in ("cut-bond", "nemock-deep-dive", "brg-deep-dive", "wte-guide",
                     "circumvent", "plg-guide"):
            return "PaperHook", {"image": slide.get("image"), "kicker": kicker,
                                 "headline": headline, "accent": accent,
                                 # `stage` is the fallback when a hook has no bespoke art
                                 "stage": slide.get("stage")}
        return "Hero3D", {"kicker": kicker, "headline": headline,
                          "accent": accent, "accentRed": accent2}
    if t in ("payoff", "cta"):
        return "CTA", {"kicker": kicker, "headline": headline, "accent": accent,
                       "accentRed": accent2, "subkicker": slide.get("subkicker", ""),
                       "badge": slide.get("badge") or ""}
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
            to, prefix, suffix = parsed
            return "StatCounter", {"kicker": kicker, "from": 0, "to": to, "prefix": prefix,
                                   "suffix": suffix,
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
                          "marks": slide.get("marks", []),
                          # set by shorts._portrait_slide on a portrait variant only, so the
                          # marks' viewBox takes the image's shape (FigureMarks, Media.tsx)
                          "imageAspect": slide.get("imageAspect"),
                          # type rendered ON the page (FigurePageType). Generated paper art
                          # has no text, so a document slide needs this to say anything.
                          "pageText": slide.get("pageText")}
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


# FIGURE MARK FIELD CONTRACT (2026-09-23). FigMark in remotion/src/components/Media.tsx
# reads `at` for circle/box/underline and `from`/`to` for arrow/strike, and puts any point
# it cannot find at the image centre. So a mark authored with the other kind's fields never
# errors. It draws in the wrong place, or not at all:
#   strike as at+w        Product Leadership module 6, first render: five zero-length lines
#                         at the centre that drew nothing, on slides the census counted as
#                         annotated
#   underline as from/to  modules 3 (s15 s22 s33 s35 s67 s70) and 4 (s42), both published:
#                         module 3's video shows a stray line across the middle of the
#                         figure on s15 and s33
# deck_census, slidecheck, qa and validate passed all twelve. build_spec therefore REFUSES a
# mark its kind cannot draw, and the render reports it the way scriptguard and timelineguard
# report theirs: BLOCKED-MARKS.md in the project, a non-zero exit, nothing downstream.
# `w`/`h` stay optional because FigMark defaults them; only the geometry that decides WHERE
# a mark lands is enforced. Keep this table in step with FigMark, where an absent kind is a
# circle.
MARK_FIELDS = {"circle": ("at",), "box": ("at",), "underline": ("at",),
               "arrow": ("from", "to"), "strike": ("from", "to")}

# ANNOTATION CONTRACT (2026-09-24). Frame-space `annotations` break the same way.
# AnnotateOverlay (remotion/src/components/Annotate.tsx) reads the same geometry per kind,
# plus `at` for a doodle stamp, and puts a point it cannot find at the FRAME centre. Two
# failures are quieter than FigMark's: a kind outside this table, an absent one included,
# matches no branch there and draws NOTHING (FigMark would draw a circle), and a `color`
# outside its palette has no ink at all, so the mark is invisible (FigMark falls back to the
# accent). On published renders, past every check:
#   strike as at+w        #67 s14 s29: meant to cross out "90%" and "Absolute"; nothing drew
#   underline as from/to  #48 s11 s12 s14 s21 and its trust-it-less Short: lines at the frame
#                         centre, one through a headline, two through a viewer quote
#   color amber / navy    ISO 14971 modules 9-12 and two of their Shorts (24), #48 s11 s13 (2):
#                         nothing drew (s11 is also an underline without `at`)
# Amber became a real ink the same day (operator, 2026-09-24: BRAND.amber, deepened on paper,
# in both colorsFor and FigMark), so those 24 draw from their next render; navy is refused.
# The same _mark_problems checks both layers (_MARK_LAYERS below). Keep ANNOTATION_FIELDS in
# step with useRoughPaths and DoodleAnn, and ANNOTATION_COLORS with colorsFor.
ANNOTATION_FIELDS = {**MARK_FIELDS, "doodle": ("at",)}
ANNOTATION_COLORS = ("green", "red", "white", "amber")
MARKS_BLOCKED_NAME = "BLOCKED-MARKS.md"

# What each layer's renderer does with what it is given, keyed by the deck field. `default`
# is the kind an absent `kind` becomes (None: an absent kind draws nothing). `colors` is the
# palette a `color` must come from (None: any colour draws, because FigMark falls back to
# the accent).
_MARK_LAYERS = {
    "marks": {"fields": MARK_FIELDS, "default": "circle", "space": "image",
              "renderer": "FigureMarks", "unknown": "it renders as a circle", "colors": None},
    "annotations": {"fields": ANNOTATION_FIELDS, "default": None, "space": "frame",
                    "renderer": "AnnotateOverlay", "unknown": "nothing appears",
                    "colors": ANNOTATION_COLORS},
}


class MalformedMarkError(RuntimeError):
    """Raised by build_spec when a figure/footage mark breaks MARK_FIELDS, or a slide's
    frame-space annotation breaks ANNOTATION_FIELDS or ANNOTATION_COLORS."""

    def __init__(self, problems):
        self.problems = problems
        n = len(problems)
        super().__init__(
            f"{n} figure mark/annotation problem{'s' if n != 1 else ''}: "
            f"{'each' if n != 1 else 'it'} would draw in the wrong place or not at all — "
            f"refusing to render:\n  " + "\n  ".join(problems))


def _is_point(v):
    return (isinstance(v, (list, tuple)) and len(v) == 2
            and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in v))


def _mark_problems(sid, marks, key="marks"):
    """One line per entry of a slide's `marks` (the default) or `annotations` (key=
    "annotations") that its renderer cannot draw where it was authored, naming the slide,
    the entry's index and the field. Empty when every entry will draw where it was
    authored. The rules per layer are _MARK_LAYERS."""
    layer = _MARK_LAYERS[key]
    fields, space, renderer = layer["fields"], layer["space"], layer["renderer"]
    if not isinstance(marks, list):
        return [f"{sid}: `{key}` must be a list of mark objects, got {type(marks).__name__}"]
    out = []
    for i, mk in enumerate(marks):
        where = f"{sid}: {key}[{i}]"
        if not isinstance(mk, dict):
            out.append(f"{where} is not a mark object: {mk!r}")
            continue
        kind = mk.get("kind") or layer["default"]
        need = fields.get(kind) if isinstance(kind, str) else None
        if need is None:
            what = f"has kind {kind!r}" if kind else "has no `kind`"
            out.append(f"{where} {what}, which {renderer} does not draw ({layer['unknown']}); "
                       f"use one of {', '.join(fields)}")
            continue
        missing = [f for f in need if f not in mk]
        if missing:
            if need == ("at",):
                why = (f"it draws at `at` [x, y] (+ `w`/`h`), so without it the mark lands on "
                       f"the {space} centre")
                if "from" in mk or "to" in mk:
                    why += "; `from`/`to` are read only by arrow and strike"
            elif len(missing) == 2:
                why = (f"it draws from `from` [x, y] to `to` [x, y], never `at`+`w`; as "
                       f"authored it is a zero-length line at the {space} centre and draws "
                       f"nothing")
            else:
                why = (f"it draws from `from` [x, y] to `to` [x, y]; the missing end snaps to "
                       f"the {space} centre")
            out.append(f"{where} {kind} is missing "
                       f"{' and '.join(f'`{f}`' for f in missing)} — {why}")
        for f in need:
            if f in mk and not _is_point(mk[f]):
                out.append(f"{where} {kind} `{f}` must be an [x, y] pair of numbers (0-1 of "
                           f"the {space}), got {mk[f]!r}")
        # A falsy colour is the default ink, as `a.color || 'green'` reads it.
        color = mk.get("color")
        if layer["colors"] and color and color not in layer["colors"]:
            out.append(f"{where} {kind} has color {color!r}, which {renderer} has no ink for, "
                       f"so it draws invisible; use {', '.join(layer['colors'])} or leave "
                       f"it out")
    return out


# DROPPED-FIELD CONTRACT (2026-09-26). The mark failure one layer up: a field authored in
# deck.json that the type map never hands to its component. Nothing errors, deck_census
# passes, the render succeeds, and the words are simply not on screen. Found on the Product
# Leadership series, published:
#   compare `title` + `accent`  modules 5 and 6 (16 slides), 5 more on #55.
#                               The map passed {kicker, left, right} and PaperCompare never
#                               read a title, so module 6 lost lines like "Scoring the thing
#                               your strategy is built on".
#   highlight `mark`            modules 1, 3, 4 and 6 (14), 12 more on the deep dives. The
#                               map passed `accent` only, so the marked words were plain ink.
# The same shape as figure `title` without imageFromFrac (2026-07-28), `source_url`
# (2026-08-12), oncamera `patches` (2026-08-14) and hook `marks` (#55), each fixed for its
# one field. This closes the shape for the paper family: build_spec REFUSES a slide whose
# Paper* component never receives one of its authored fields, and the render reports it the
# way the mark guard does (BLOCKED-FIELDS.md, a non-zero exit, nothing downstream).
#
# There is no table to keep in step: _dropped_field_problems asks the type map itself. A
# field is received when taking it away, or changing it, changes what _scene_for emits.
# That covers fallbacks too (a quote's `headline` is never shown while `quote` is set,
# unless the two say the same words) and a value equal to its default (an oncamera `set`
# naming the default monitor is still read). The guard sees what a component RECEIVES;
# whether the component then draws it is the component's side, which is why PaperCompare
# had to learn `title` the same day.
FIELDS_BLOCKED_NAME = "BLOCKED-FIELDS.md"

# Read by something other than the type map, so a slide that carries them is not dropping
# them: the slide's identity; build_spec's own passes (cue phrases, frame-space annotations,
# the universal citation line, the tear transition); and _assign_chibi's presenter poses.
# shorts._portrait_slide reads every `*_9x16` twin, checked by suffix below.
_READ_OUTSIDE_TYPE_MAP = ("id", "type", "cues", "annotations", "source", "source_url",
                          "transition", "chibi", "chibiSide", "chibiFlip")


class DroppedFieldError(RuntimeError):
    """Raised by build_spec when a slide carries a field its Paper* component never
    receives (the DROPPED-FIELD CONTRACT above)."""

    def __init__(self, problems):
        self.problems = problems
        n = len(problems)
        what = ("1 authored field never reaches its paper component: it would" if n == 1 else
                f"{n} authored fields never reach their paper components: each would")
        super().__init__(f"{what} be missing from the video — refusing to render:\n  "
                         + "\n  ".join(problems))


class _Probe:
    """A value no deck field can equal: what _perturbed leaves where a value was."""


def _perturbed(v):
    """`v` with the same shape and a different value."""
    if isinstance(v, bool):
        return not v
    if isinstance(v, (int, float)):
        return v + 1
    if isinstance(v, str):
        return v + chr(0x2063)       # INVISIBLE SEPARATOR: not whitespace, so .strip() keeps it
    if isinstance(v, list):
        return v + [_Probe()]
    if isinstance(v, dict):
        return {**v, "_probe": _Probe()}
    return _Probe()


def _dropped_field_problems(sid, slide, theme=""):
    """One line per field authored on `slide` that its Paper* component never receives,
    naming the slide, the field and the component. Empty for any other component, for a
    slide that names its component directly (its `fields` are the component's own), and
    when every authored field arrives. The rule is the DROPPED-FIELD CONTRACT above."""
    if not isinstance(slide, dict) or slide.get("component"):
        return []

    def emit(s):
        # no-op warn: each probe would otherwise log the cta fallback again
        return _scene_for(s, theme=theme, warn=lambda _m: None)

    base = emit(slide)
    if not base[0].startswith("Paper"):
        return []

    def received(k, v):
        if emit({kk: vv for kk, vv in slide.items() if kk != k}) != base:
            return True              # taking it away changes the scene
        try:
            return emit({**slide, k: _perturbed(v)}) != base   # so does changing it
        except Exception:            # the map did arithmetic or a lookup on it: read
            return True

    got, dropped = [], []
    for k, v in slide.items():
        if k in _READ_OUTSIDE_TYPE_MAP or k.endswith("_9x16") or v in (None, "", [], {}):
            continue
        (got if received(k, v) else dropped).append(k)
    # A field shadowed by one carrying the same value is a duplicate, not a drop: a punch
    # with `word` and `headline` both "Focus." still says "Focus." (the word wins).
    return [f"{sid}: `{k}` is authored on this {slide.get('type') or 'untyped'} slide, but "
            f"{base[0]} never receives it, so it would not appear on screen"
            for k in dropped if not any(slide[k] == slide[g] for g in got)]


def build_spec(sp):
    seg = json.loads((sp.work / "segments.json").read_text())
    fps = sp.fps
    width, height = sp.data["width"], sp.data["height"]
    duration = seg["duration"]
    segs = seg["segments"]
    slides_by_id = {s["id"]: s for s in json.loads(sp.deck_json.read_text())["slides"]}

    # Declared before the scene loop so _scene_for can report a fallback it had to apply
    # (e.g. a content-less closing card). Surfaced as spec["_warnings"] and logged by
    # _render_one, same as every sync warning collected below.
    warnings = []
    mark_problems = []
    field_problems = []
    scenes = []
    for i, s in enumerate(segs):
        start = s["start"]
        end = segs[i + 1]["start"] if i + 1 < len(segs) else duration
        slide = slides_by_id.get(s["slide"], {})
        comp, fields = _scene_for(slide, theme=sp.data.get("theme", ""),
                                  warn=warnings.append)
        # Only marks the type map passed through can draw, so those are the ones checked
        # (MARK_FIELDS above). Annotations draw over ANY scene (step 4 below), so every
        # rendered slide's are checked (ANNOTATION_FIELDS). Collected across the whole deck
        # and raised once, below.
        mark_problems += _mark_problems(s["slide"], fields.get("marks") or [])
        mark_problems += _mark_problems(s["slide"], slide.get("annotations") or [],
                                        "annotations")
        # And every authored field the type map never hands to a Paper* component
        # (DROPPED-FIELD CONTRACT above). Raised after the marks, so a deck with both is
        # blocked on its marks first; deck_census lists both at once, before narrate.
        field_problems += _dropped_field_problems(s["slide"], slide, sp.data.get("theme", ""))
        sc = {"component": comp, "from": int(round(start * fps)),
              "durationInFrames": max(1, int(round((end - start) * fps))), "fields": fields}

        # UNIVERSAL CITATION PASSTHROUGH (operator directive 2026-08-12: "we cite our
        # sources, so URLs… we'll put them at the bottom of the screen").
        #
        # Before this, `source` was mapped by exactly ONE slide type (statgrid) and
        # `source_url` by none at all. A `figure`, `quote` or `compare` slide could carry
        # a citation in deck.json and it was silently dropped at spec-build — the deck
        # author would never know. Both fields now ride through for every type, and
        # components/SourceLine.tsx renders them once at the Video level, capped so a long
        # URL cannot climb into the caption band.
        for _k in ("source", "source_url"):
            if slide.get(_k):
                sc["fields"].setdefault(_k, slide[_k])
        # act-boundary tear (papercraft-motion-spec.md §4): the scene reveals behind a
        # parting torn seam instead of the cross-fade. Author: "transition": "tear".
        if slide.get("transition") == "tear":
            sc["tear"] = True
        scenes.append(sc)
    if mark_problems:
        raise MalformedMarkError(mark_problems)
    if field_problems:
        raise DroppedFieldError(field_problems)

    words = []
    al = sp.work / "alignment.json"
    if al.exists():
        for w in json.loads(al.read_text()).get("words", []):
            words.append({"word": w["word"], "start": w["start"], "end": w["end"]})

    # --- narration sync: cues, item times, annotations (motion-playbook §5) ---
    # Every resolved frame is SCENE-relative, so the sting shift below (which only
    # moves sc["from"]) never invalidates them.
    # Paper* corner props are a LANDSCAPE affordance. In portrait the content card fills
    # the width and the captions own the lower third, so there is no corner left to stand
    # in — a prop lands on the slide's own text (verified with 9:16 stills, 2026-08-07).
    # Drop them with a warning rather than paint over the content; the hook keeps its own
    # (it positions props inside the set planes), and Cvg* scenes compose portrait
    # themselves. Runs while scenes are still 1:1 with segments.
    if height > width:
        for i, sc in enumerate(scenes):
            if (sc["component"].startswith("Paper") and sc["component"] != "PaperSetHook"
                    and sc["fields"].get("props")):
                sc["fields"].pop("props")
                warnings.append(f"{segs[i]['slide']}: props dropped — the Paper* corner prop "
                                f"layer is landscape-only (portrait has no free corner)")
    # ONE CONTINUOUS TAKE ACROSS THE COLD OPEN. The deck is 1:1 with script segments, so
    # a 30-second on-camera open is several scenes — and each <Video> would otherwise
    # restart the same file, making Dave jump back to his first word on every slide.
    # Each scene therefore plays its own slice: startAtSec = this scene's narration start
    # minus the start of the run it belongs to. The LAST scene of a run gets pullBack,
    # which is the spec's no-cut exit (the camera retreats to the full desk instead).
    _run_start = None
    for i, sc in enumerate(scenes):
        if sc["component"] != "PaperMonitor":
            _run_start = None
            continue
        if _run_start is None:
            _run_start = segs[i]["start"]
        sc["fields"]["startAtSec"] = round(segs[i]["start"] - _run_start, 3)
        nxt = scenes[i + 1]["component"] if i + 1 < len(scenes) else None
        if nxt != "PaperMonitor":
            sc["fields"]["pullBack"] = True
        if not sc["fields"].get("video"):
            warnings.append(f"{segs[i]['slide']}: on-camera scene has no `video` — the "
                            f"monitor renders as a blank paper screen until the take is wired up")

    # Presenter poses, assigned while scenes are still 1:1 with segments — the sting
    # scenes are inserted further down and would break the index alignment.
    presenter = _assign_chibi(scenes, slides_by_id, [s["slide"] for s in segs],
                              sp.data, warnings.append)
    # Real Dave is ON SCREEN in these scenes. A chibi Dave standing beside the monitor
    # puts two versions of the same person in one frame — excluded by operator directive
    # 2026-08-12, and excluded here rather than left to the deck author to remember.
    for sc in scenes:
        if sc["component"] == "PaperMonitor":
            sc.pop("chibi", None)
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
            # NARRATIVE-ORDER GUARD (operator-caught, #56): a circle drawn before the
            # thing it circles exists reads as nonsense. On a schematic, nothing exists
            # before the first stage reveals, so any annotation resolving earlier is a
            # defect by construction. (An annotation can still fire before its SPECIFIC
            # target's later stage — this guard only catches the unambiguous case.)
            if slide.get("type") == "schematic" and slide.get("stages"):
                first_cue = slide["stages"][0].get("cue", "")
                f0 = _resolve_phrase(first_cue, segw, s0, fps) if first_cue else None
                if f0 is not None:
                    for a2 in resolved:
                        if a2["cueFrame"] < f0:
                            warnings.append(
                                f"{sid}: annotation fires at frame {a2['cueFrame']} but the "
                                f"schematic's first reveal is at {f0} — it draws on empty "
                                f"canvas. Recue it after its subject appears.")

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
    # The six personal-show worlds likewise end on their own CTA card (brand system
    # 2026-08-06); the legacy BrandSting would stamp the wrong brand on five of them.
    # plg-guide joins wte-guide here (2026-08-11). Both are like-and-subscribe-only
    # Operator's Guide series on the personal channel with no spoken site CTA, so neither
    # wants a wordmark bumper. Without this entry plg-guide falls to the legacy `else`
    # below and gets FOUNDERS WHO FINISH / davesaunders.net stamped on a series that is
    # explicitly not the book brand — the same cross-brand leak guarded against above.
    # `sting` takes three values (the third added 2026-09-11, operator directive):
    #   true / omitted on landscape -> intro AND outro
    #   false                       -> neither
    #   "outro"                     -> OUTRO ONLY; the opening bumper is dropped.
    # Dave, on #59: "I'd like to remove the opening slide with the rocket ship landing. I
    # think it's just creating too much dead air, and given the nature of YouTube viewers
    # these days, it's too much of an opportunity to switch off." That reasoning is about
    # the OPENING only — a closing wordmark costs no retention, because the video is over —
    # so it gets its own value rather than forcing `false` and silently dropping the brand
    # mark he did not ask to lose.
    _NO_STING = ("wte-guide", "plg-guide") + _CVG_STYLE_THEMES
    _sting = sp.data.get("sting", width >= height)
    _intro_on = bool(_sting) and _sting != "outro"
    if sp.data.get("theme") not in _NO_STING and _sting:
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
        if not _intro_on:
            INTRO = 0.0                      # "outro": narration starts at t=0
        off = int(round(INTRO * fps))
        for sc in scenes:
            sc["from"] += off
        for w in words:
            w["start"] += INTRO
            w["end"] += INTRO
        if _intro_on:
            scenes.insert(0, {"component": intro_comp, "from": 0, "durationInFrames": off,
                              "fields": intro_fields})
        scenes.append({"component": outro_comp, "from": off + int(round(duration * fps)),
                       "durationInFrames": int(round(OUTRO * fps)),
                       "fields": outro_fields})
        audio_from = off
        total = INTRO + duration + OUTRO

    # Show title panel for the six personal-show worlds (see _SHOW_TITLE). Intro only —
    # these shows end on their own authored CTA card, so there is no outro. Same
    # mechanics as the bumper above: every scene and word shifts by the panel length
    # and the narration starts after it (audioFrom). The panel's `mark` ref is picked
    # up by the papercraft-<show> staging scan in _render_one like any deck ref.
    _title = _SHOW_TITLE.get(sp.data.get("theme", ""))
    if _title and sp.data.get("title_panel", True):
        INTRO = SHOW_TITLE_SECONDS
        off = int(round(INTRO * fps))
        for sc in scenes:
            sc["from"] += off
        for w in words:
            w["start"] += INTRO
            w["end"] += INTRO
        scenes.insert(0, {"component": "CvgTitle", "from": 0, "durationInFrames": off,
                          "fields": dict(_title)})
        audio_from = off
        total = INTRO + duration

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
        # Burned-in captions on/off. project.json `"captions": false` disables them —
        # added for the longform sleep format, where a karaoke bar would fight the
        # point of the video. Default stays on for every existing project.
        "showCaptions": bool(sp.data.get("captions", True)),
        # Chibi presenter layer (None when off) — see _assign_chibi.
        **({"presenter": presenter} if presenter else {}),
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
    # "badge" = the CTA corner badge (like/subscribe). Without it here the file is never
    # copied into public/ and staticFile() 404s at render time.
    ASSET_FIELDS = ("image", "bottomImage", "set", "video", "mark", "badge")

    def _stage_one(img):
        # chibi/ refs are staged from the private pose library by _stage_chibi (which runs
        # after this pass) — leave them untouched here or they'd be dropped as missing.
        # "papercraft-" covers EVERY per-show library (papercraft-circumvent and the six
        # 2026-08-06 show worlds), which render() stages wholesale when referenced —
        # matching only the circumvent library here nulled every papercraft-<show> ref
        # and crashed Cutout with staticFile(null) (caught by the cutover smoke tests).
        if not img or str(img).startswith(("papercraft/", "papercraft-", "chibi/")):
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
        # The presenter layer (_assign_chibi -> scene["chibi"]) is the ONLY legitimate
        # route for a pose. A chibi ref authored as set dressing — in `props` or as a
        # slide `image` — is dropped here (deck-playbook §4c-ii: "Never author a
        # `chibi/...` ref as a prop"). Enforced in the engine 2026-08-10: until then
        # this path still staged them, so decks written against the pre-2026-08-07 docs
        # rendered Dave as a PROP, at prop scale and prop baseline, standing in the set
        # as furniture. That is how the stand-in kept shipping on the portrait shows
        # even though the presenter layer skips portrait (5 decks: FMF 08-07 and four
        # FWF dailies 08-07..08-10). Dropping is safe — the scene renders without it.
        for key in ("image", "bottomImage"):
            if str(fields.get(key) or "").startswith("chibi/"):
                log(f"remotion: chibi ref dropped from `{key}` — the presenter is an "
                    f"automatic layer, never set dressing ({fields[key]})")
                fields[key] = None
        props = fields.get("props")
        if props:
            kept = []
            for prop in props:
                if isinstance(prop, dict) and str(prop.get("image") or "").startswith("chibi/"):
                    log(f"remotion: chibi ref dropped from `props` — the presenter is an "
                        f"automatic layer, never a prop ({prop['image']})")
                    continue
                kept.append(prop)
            fields["props"] = kept
        # scene-level presenter pose (every scene carries one; see _assign_chibi)
        if str(scene.get("chibi") or "").startswith("chibi/"):
            staged = _one(scene["chibi"])
            if staged:
                scene["chibi"] = staged
            else:
                scene.pop("chibi", None)


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
    # Loop the bed at the DEMUXER (-stream_loop), not with the aloop filter: aloop
    # buffers `size` samples in memory to replay them, which is fine for a 3-minute
    # shorts bed but blew up with "Error while filtering: Invalid argument" on the
    # first longform render (66-minute bed, ~190M samples/channel) — caught
    # 2026-08-24 on alchemy ep1, where the mux died at 58:15 after a completed
    # 2.5-hour render. -stream_loop replays the input itself, buffers nothing, and
    # behaves identically for short beds.
    fc = (f"[1:a]volume={gain},"
          f"aformat=sample_rates=48000:channel_layouts=stereo[bed];"
          f"[0:a][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix];"
          f"[mix]alimiter=limit=0.84:level=false[a]")
    ff = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [ff, "-hide_banner", "-y", "-i", str(out), "-stream_loop", "-1", "-i", str(mp),
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
    """Render every aspect listed in project.json `aspects` (falling back to the primary
    `aspect`), one final muxed mp4 per aspect. The `aspects` list was a deck-engine
    feature this engine silently ignored — the CVG pilot (2026-08-06) shipped its 4:5 by
    hand-flipping project.json, which this loop retires. A `frames` slice or explicit
    `out` path constrains the pass to the primary aspect only (previews don't need every
    cut). sp.data is restored even on failure so a crashed pass can't leave the project
    file's dims flipped on disk-reload paths."""
    aspects = list(sp.data.get("aspects") or [sp.data.get("aspect", "9:16")])
    if frames or out:
        aspects = [sp.data.get("aspect", "9:16")]
    orig = {k: sp.data.get(k) for k in ("aspect", "width", "height")}
    from .project import ASPECTS as _DIMS
    results = []
    try:
        for a in aspects:
            w, h = _DIMS.get(a, (orig["width"], orig["height"]))
            sp.data.update({"aspect": a, "width": w, "height": h})
            results.append(_render_one(sp, log=log, frames=frames, out=out))
    finally:
        sp.data.update({k: v for k, v in orig.items() if v is not None})
    if len(results) == 1:
        return results[0]
    combined = dict(results[0])
    combined["video"] = [r["video"] for r in results]
    combined["aspects_rendered"] = aspects
    return combined


def _marks_blocked_text(sp, problems):
    n = len(problems)
    L = [f"# BLOCKED: malformed figure marks or annotations ({sp.dir.name})", "",
         f"**{n} problem{'s' if n != 1 else ''} with the figure `marks` or frame-space "
         f"`annotations` in `deck.json`.** Each would draw in the wrong place or not at all.", "",
         "`FigureMarks` (`remotion/src/components/Media.tsx`, image space) and `AnnotateOverlay`",
         "(`remotion/src/components/Annotate.tsx`, frame space) read `at` for circle, box and",
         "underline and `from`/`to` for arrow and strike, and put any point they cannot find at",
         "the centre. The render would NOT fail: a `strike` authored as `at`+`w` draws nothing,",
         "and an `underline` authored as `from`/`to` draws a stray line across the middle. An",
         "annotation fails more quietly still: a kind the overlay does not know, or no `kind`,",
         f"draws nothing, and so does a `color` outside {', '.join(ANNOTATION_COLORS)}.", "",
         "## To fix", ""]
    L += [f"- {p}" for p in problems]
    L += ["", "## The contract", "",
          "| kind | draws from | optional |", "|---|---|---|",
          "| `circle`, `box` | `at`: [x, y] | `w`, `h` |",
          "| `underline` | `at`: [x, y], just below the subject | `w` |",
          "| `arrow`, `strike` | `from`: [x, y] and `to`: [x, y] | |",
          "| `doodle` (annotations only) | `at`: [x, y] | `w`, `rotate` |", "",
          "Coordinates are 0-1 of the image for `marks` and of the frame for `annotations`",
          f"(motion-playbook §2H). An annotation's `color` is one of "
          f"{', '.join(ANNOTATION_COLORS)}, or left",
          "out. A mark with no `kind` is a circle; an annotation with no `kind` draws nothing.", "",
          "## Fix", ""]
    if sp.data.get("derived_from"):
        # shorts.build_derived puts each cut at <parent>/shorts/<slug> and rewrites its deck
        # from the parent's on every run, so the fix belongs in the parent.
        L += [f"This is a Short. Its slides are copied from the parent project "
              f"`{sp.data['derived_from']}` on every Shorts run, so fix them in the "
              f"parent's `deck.json` (or in the script that builds it), then re-cut. A "
              f"slide that carries `marks_9x16` shows those in a Short instead of "
              f"`marks`, so fix that field:", "",
              "```bash",
              f"/Volumes/Casima/claudeCode/explainer2/bin/explainer2 shorts "
              f"'{sp.dir.parent.parent}' --only {sp.dir.name}",
              "```", ""]
    else:
        L += ["Fix them in `deck.json` (or in the script that builds it), then render:", "",
              "```bash",
              f"/Volumes/Casima/claudeCode/explainer2/bin/explainer2 render '{sp.dir}'",
              "```", "",
              "If the recording watcher launched this render, it relaunches phase 1 by itself",
              "on its retry schedule once the deck is fixed.", ""]
    L += ["The next render whose marks and annotations all pass deletes this file.", ""]
    return "\n".join(L)


def _fields_blocked_text(sp, problems):
    n = len(problems)
    L = [f"# BLOCKED: authored fields that never reach the screen ({sp.dir.name})", "",
         f"**{n} field{'s' if n != 1 else ''} in `deck.json` that the slide's paper component "
         f"never receives.** Each would be missing from the video.", "",
         "`_papercraft_component` (`src/explainer2/remotion_engine.py`) builds each Paper*",
         "component's fields from the slide, and a field it does not pass along is dropped",
         "without a warning. The render would NOT fail: the slide renders, minus that line.",
         "Product Leadership module 6 shipped eleven compare slides without their titles",
         "this way (motion-playbook §2H; the DROPPED-FIELD CONTRACT comment above",
         "`_dropped_field_problems`).", "",
         "## To fix", ""]
    L += [f"- {p}" for p in problems]
    L += ["", "## Each field is one of three cases", "",
          "1. **It should be on screen, and this slide type has a field that shows it.** Move",
          "   the words there (deck-playbook §2 lists each type's fields), or change the slide",
          "   to a type that shows what it is saying.",
          "2. **It should be on screen, and no field of this type shows it.** That is an engine",
          "   change, not a deck edit: pass it in `_papercraft_component` and draw it in the",
          "   component under `remotion/src/components/`. Ask the operator before making it.",
          "3. **It was never meant to be seen** (a leftover, or a field from the legacy deck",
          "   engine). Delete it from the slide.", "",
          "## Fix", ""]
    if sp.data.get("derived_from"):
        L += [f"This is a Short. Its slides are copied from the parent project "
              f"`{sp.data['derived_from']}` on every Shorts run, so fix them in the "
              f"parent's `deck.json` (or in the script that builds it), then re-cut:", "",
              "```bash",
              f"/Volumes/Casima/claudeCode/explainer2/bin/explainer2 shorts "
              f"'{sp.dir.parent.parent}' --only {sp.dir.name}",
              "```", ""]
    else:
        L += ["Fix them in `deck.json` (or in the script that builds it), then render:", "",
              "```bash",
              f"/Volumes/Casima/claudeCode/explainer2/bin/explainer2 render '{sp.dir}'",
              "```", "",
              "If the recording watcher launched this render, it relaunches phase 1 by itself",
              "on its retry schedule once the deck is fixed.", ""]
    L += ["The next render whose authored fields all reach their components deletes this "
          "file.", ""]
    return "\n".join(L)


def _build_spec_guarded(sp, log=print):
    """build_spec for a real render. A malformed mark or annotation, or an authored field no
    paper component receives, is refused the way the media guards refuse: BLOCKED-MARKS.md
    or BLOCKED-FIELDS.md in the project naming every one, a BLOCKED log line, and the error
    re-raised so the render stage fails and nothing downstream runs. A build that passes a
    check deletes that check's file, so a fixed deck never looks blocked."""
    blocked = sp.dir / MARKS_BLOCKED_NAME
    fields_blocked = sp.dir / FIELDS_BLOCKED_NAME

    def clear(path, guard, why):
        if path.exists():
            path.unlink()
            log(f"{guard}: previous {path.name} cleared — {why}")

    try:
        spec = build_spec(sp)
    except MalformedMarkError as e:
        blocked.write_text(_marks_blocked_text(sp, e.problems))
        log(f"marks-guard: BLOCKED — {len(e.problems)} figure mark/annotation problem(s); "
            f"wrote {blocked.name} — refusing to render")
        raise
    except DroppedFieldError as e:
        # build_spec raises this only once every mark has passed
        clear(blocked, "marks-guard", "every figure mark and annotation will draw")
        fields_blocked.write_text(_fields_blocked_text(sp, e.problems))
        log(f"fields-guard: BLOCKED — {len(e.problems)} authored field(s) no paper component "
            f"receives; wrote {fields_blocked.name} — refusing to render")
        raise
    clear(blocked, "marks-guard", "every figure mark and annotation will draw")
    clear(fields_blocked, "fields-guard", "every authored field reaches its component")
    return spec


def _render_one(sp, log=print, frames=None, out=None):
    """Render `sp` via Remotion -> the final muxed mp4. `frames` (e.g. '0-2400') renders a
    range for fast preview. The heavy headless render should be wrapped by the render-lock."""
    if not (REMOTION_DIR / "node_modules").exists():
        raise RuntimeError(
            f"Remotion engine not installed: run `npm install` in {REMOTION_DIR} "
            f"(or use --engine deck). The motion engine needs the Node toolchain.")
    spec = _build_spec_guarded(sp, log)
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
    # Per-show papercraft libraries (papercraft-circumvent since 2026-07-30; the six
    # personal-show libraries since 2026-08-06). Staged wholesale, but ONLY the libraries
    # this deck actually references — copying all of them into every render's public dir
    # would grow with each new show for no benefit.
    _lib_refs = set()
    for _scene in spec["scenes"]:
        _f = _scene.get("fields") or {}
        for _v in [_f.get(k) for k in ("image", "bottomImage", "set", "video", "mark")] + \
                  [p.get("image") for p in (_f.get("props") or []) if isinstance(p, dict)]:
            if isinstance(_v, str) and _v.startswith("papercraft-"):
                _lib_refs.add(_v.split("/", 1)[0])
    for _lib_name in sorted(_lib_refs):
        _lib_dir = REMOTION_DIR / "public" / _lib_name
        if _lib_dir.exists():
            shutil.copytree(_lib_dir, public / _lib_name, dirs_exist_ok=True)
        else:
            log(f"remotion: WARNING deck references {_lib_name}/ but "
                f"remotion/public/{_lib_name} does not exist — those refs will 404")
    # Blank paper substrates (papercraft-substrate-plan.md). Unlike the two libraries above
    # these are never named in a deck — components pick a substrate internally — so they
    # must be staged unconditionally or PaperNote renders nothing.
    # papercraft-plg/ joins this list for the SAME reason (2026-08-14): its elements are
    # chosen inside the component via the world's elementDir token, never named in a deck
    # field, so the _lib_refs scan above cannot see them. It was staged only into the repo's
    # remotion/public — which is what `remotion still` reads — so every still looked right
    # while the real render, which builds its own per-project public dir, 404'd on the
    # warning triangle and DIED. Stills are not proof that a render will stage.
    for _lib in ("papercraft-notes", "papercraft-cards", "papercraft-fixings",
                 "papercraft-grounds", "papercraft-stages", "papercraft-plg"):
        _sub = REMOTION_DIR / "public" / _lib
        if _sub.exists():
            shutil.copytree(_sub, public / _lib, dirs_exist_ok=True)
    _stage_images(sp, spec, public)
    _stage_doodles(spec, public, log)
    _stage_chibi(spec, public, log)
    # CTA scenes show the brand book cover unless the project opts out with
    # "cta_book": false in project.json (e.g. masterclass modules use no book cover).
    # Some THEMES forbid it outright, because the no-book rule is a series-standing
    # branding decision and not a per-project preference. Keep this tuple in step with
    # the `_NO_STING` tuple below — a theme that wants no wordmark bumper almost always
    # wants no book cover either, for the same reason.
    #   wte-guide  2026-07-29 — like-and-subscribe is its only CTA.
    #   plg-guide  2026-08-26 — same rule, written down in the series outline §6 ("CTA:
    #     Like-and-subscribe ONLY. No book, no newsletter, no site CTA in the spoken
    #     script or on any card") and §7 ("no book cover (cta_book: false)"). It was
    #     enforced by hand in module 1's project.json and module 2 was scaffolded without
    #     it, so the book cover rendered onto the final card of a series that is
    #     explicitly not the book brand. A standing decision that only holds when someone
    #     remembers to retype it into each project file is not a standing decision.
    _NO_BOOK_CTA = ("wte-guide", "plg-guide")
    _cta_book = (sp.data.get("cta_book", True)
                 and sp.data.get("theme") not in _NO_BOOK_CTA)
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

    # Resolve npx robustly: under launchd (the recording watcher's Phase-1 renders) the
    # minimal PATH carries neither Homebrew nor /usr/local, and a bare "npx" crashed every
    # watcher render on 2026-08-07 (crashloop starved FMF for 3 hours). PATH first, then
    # the two standard install locations.
    npx = shutil.which("npx") or next(
        (p for p in ("/usr/local/bin/npx", "/opt/homebrew/bin/npx") if Path(p).exists()), "npx")
    cmd = [npx, "remotion", "render", "src/index.ts", "Video", str(out),
           f"--props={props}", f"--public-dir={public}", "--log=error",
           "--timeout=300000"]  # generous delayRender timeout (slow disk I/O tolerance)
    # RAM/CPU ceiling (2026-08-26). Left unbounded, Remotion takes ~half the cores
    # for concurrency and runs an UNBOUNDED frame cache — the compositor payload
    # observed during the out-of-memory incident read
    # "maximum_frame_cache_size_in_bytes": null. That is a render that expands to
    # fill whatever is free, on a machine the operator is using at the same time.
    # Operator directive: a background render must never make the Mac unusable
    # interactively, even at the cost of a longer render. Both knobs are
    # overridable for a big-iron or unattended-overnight run.
    conc = os.environ.get("EXPLAINER_REMOTION_CONCURRENCY", "2")
    cache_mb = int(os.environ.get("EXPLAINER_REMOTION_FRAME_CACHE_MB", "512"))
    cmd += [f"--concurrency={conc}",
            f"--offthreadvideo-cache-size-in-bytes={cache_mb * 1024 * 1024}"]
    if frames:
        cmd.append(f"--frames={frames}")
    log(f"remotion: rendering {sp.dir.name} ({len(spec['scenes'])} scenes, {spec['durationInFrames']}f"
        + (f", slice {frames}" if frames else "") + ")")
    # Own process group (childproc): `npm exec remotion render` forks node and a whole
    # chrome-headless-shell tree, and on 2026-08-10 that tree survived its parent being
    # killed and kept rendering as an orphan. One killable group instead.
    from . import childproc
    r = childproc.run(cmd, label=f"remotion:{sp.dir.name}", cwd=str(REMOTION_DIR),
                      capture_output=True, text=True)
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
