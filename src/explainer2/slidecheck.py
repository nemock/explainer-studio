"""slidecheck.py — does every rendered slide actually SHOW something?

Added 2026-08-12 after two published episodes shipped slides with nothing on them.
FMF 2026-08-07 s3 and MMT 2026-08-10 s4/s6/s9 authored their content in `value`/`label`/
`stats`, the Cvg scene map dropped those fields on the floor, and the slides rendered as a
set with a kicker and an empty card. Nothing in the chain noticed: deck_census only
measured the MIX of slide types, `validate` only checked that files existed on disk, and
`qa` measures pacing. Every gate we had could pass a video with a blank card in it.

The check runs against the BUILT SPEC (`work/remotion/props.json`), not deck.json, which
is the point. deck.json is what the author wrote; the spec is what Remotion was actually
handed. The bug lived in the translation between them, so only the spec can see it.

Two checks, deliberately different in kind:

  blank    — EXACT, and it blocks. A scene whose component prints text and was given none
             renders an empty card. There is no judgement call here and no false positive.
  overlong — ADVISORY. Text past what the smallest type step can fit will overrun its box.
             This is one number rather than a copy of the TSX tier table, because a copy
             would drift out of step with Circumvent.tsx the first time either moved.
"""

# Components that draw their own visual and legitimately carry no text.
_DRAWS = {
    "Figure", "Footage", "Schematic", "Timeline", "Waveform", "DrawLine", "Pictograph",
    "Ring", "Funnel", "Waterfall", "Hero3D", "BrandSting", "KeepCard", "PaperPopCard",
    "PaperStairs", "PaperCounter", "StatCounter",
}

# Any of these carrying content means the scene has something to show.
#
# `kicker` and `subkicker` are deliberately NOT here, and this is the whole check. The
# kicker is a small label ABOVE the headline; a scene carrying only a kicker is exactly
# the blank card we are hunting. FMF 2026-08-07 s3 shipped with
# kicker="reported by Boston Scientific, as of March 18, 2026" and headline="" — so a
# version of this list that counted the kicker would have passed the very slide it was
# written to catch. (It did, on the first draft. The test case is in the suite.)
_TEXT_KEYS = ("headline", "word", "term", "definition", "quote", "attrib", "label",
              "title", "mark", "image")
_LIST_KEYS = ("items", "steps", "stats", "points", "events", "nodes")
_PAIR_KEYS = ("left", "right")

# A headline longer than this cannot fit its box even at the smallest type step. Derived
# from the 4:5 block box (the binding aspect), with margin. The step table itself lives in
# Circumvent.tsx `SceneType` and is deliberately NOT duplicated here.
HEADLINE_CEILING = 420


def _has_content(fields):
    for k in _TEXT_KEYS:
        v = fields.get(k)
        if isinstance(v, str) and v.strip():
            return True
    for k in _LIST_KEYS:
        v = fields.get(k)
        if isinstance(v, (list, tuple)) and any(
                (x if isinstance(x, str) else " ".join(str(y) for y in (x or {}).values())).strip()
                for x in v):
            return True
    for k in _PAIR_KEYS:
        v = fields.get(k)
        if isinstance(v, dict) and any(str(x).strip() for x in v.values()):
            return True
    return False


def check_spec(spec):
    """(blank, overlong) — lists of human-readable findings for a built Remotion spec."""
    blank, overlong = [], []
    for i, scene in enumerate(spec.get("scenes") or []):
        comp = scene.get("component", "?")
        fields = scene.get("fields") or {}
        if comp not in _DRAWS and not _has_content(fields):
            blank.append(f"scene {i} ({comp}) would render with nothing on it")
        h = fields.get("headline")
        if isinstance(h, str) and len(h) > HEADLINE_CEILING:
            overlong.append(
                f"scene {i} ({comp}) headline is {len(h)} chars, past the {HEADLINE_CEILING} "
                f"ceiling — it will overrun the frame at any type size; split the slide")
    return blank, overlong


def run(proj):
    """Read the project's built spec and check it. Missing spec is not an error here —
    validate already reports a missing render."""
    import json
    p = proj.work / "remotion" / "props.json"
    if not p.exists():
        return [], []
    try:
        return check_spec(json.loads(p.read_text()))
    except (ValueError, OSError) as e:
        return [f"could not read the built spec to check slides: {e}"], []
