"""Remotion render engine (motion-playbook.md) — the animated alternative to the deck
engine. Given an assembled cut project (narration.wav + segments.json + deck.json +
alignment.json), it builds a DATA motion spec, stages the audio, and renders the final
muxed mp4 via the shared `remotion/` component library. Claude authors specs (the
deck/segments), never React.

Determinism, brand, and the component catalog live in remotion/ + motion-playbook.md.
This module only TRANSLATES our existing per-segment data into a Remotion props spec and
shells out to `npx remotion render`.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

REMOTION_DIR = Path(__file__).resolve().parents[2] / "remotion"


def _parse_stat(value):
    """Best-effort parse of a deck stat value (e.g. '−$1,000', '93%', '$500') into
    (to:float, prefix:str). Returns None if it isn't a clean number we can count."""
    if not value:
        return None
    s = str(value).replace("−", "-").replace(",", "").strip()
    prefix = "$" if "$" in s else ""
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    # bail on unit-suffixed magnitudes ($500M, 2.3x) — the counter can't show the unit cleanly yet
    if re.search(r"\d\s*[a-zA-Z%]", s) and "%" not in s:
        return None
    return float(m.group(0)), prefix


def _scene_for(slide):
    """Map a deck slide -> (component, fields). The three core components for Step 1;
    everything else falls back to the captions-led TalkingScene (motion-playbook §6 map)."""
    t = slide.get("type")
    headline = slide.get("headline") or slide.get("title") or slide.get("word") or ""
    kicker = slide.get("kicker", "")
    accent = slide.get("accent", []) or []
    if t == "hook":
        return "KineticHook", {"kicker": kicker, "headline": headline, "accent": accent}
    if t in ("payoff", "cta"):
        return "KineticHook", {"kicker": kicker, "headline": headline, "accent": accent}
    if t in ("stat", "statgrid"):
        parsed = _parse_stat(slide.get("value"))
        if parsed:
            to, prefix = parsed
            return "StatCounter", {"kicker": kicker, "from": 0, "to": to,
                                   "prefix": prefix, "label": slide.get("label", "")}
    # statement / quote / list / compare / figure / footage / reframe / punch ... -> captions-led
    if t == "quote":
        headline = slide.get("quote") or headline
    return "TalkingScene", {"kicker": kicker, "headline": headline, "accent": accent}


def build_spec(sp):
    """Build the Remotion props spec from an assembled cut project `sp`."""
    seg = json.loads((sp.work / "segments.json").read_text())
    fps = sp.fps
    width, height = sp.data["width"], sp.data["height"]
    duration = seg["duration"]
    segs = seg["segments"]
    slides_by_id = {s["id"]: s for s in json.loads(sp.deck_json.read_text())["slides"]}

    # scenes hold from their segment start until the NEXT segment start (covers inter-seg gaps)
    scenes = []
    for i, s in enumerate(segs):
        start = s["start"]
        end = segs[i + 1]["start"] if i + 1 < len(segs) else duration
        comp, fields = _scene_for(slides_by_id.get(s["slide"], {}))
        scenes.append({
            "component": comp,
            "from": int(round(start * fps)),
            "durationInFrames": max(1, int(round((end - start) * fps))),
            "fields": fields,
        })

    words = []
    al = sp.work / "alignment.json"
    if al.exists():
        for w in json.loads(al.read_text()).get("words", []):
            words.append({"word": w["word"], "start": w["start"], "end": w["end"]})

    safe_bottom = float(sp.data.get("safe_bottom", 0.12)) + 0.04  # lift captions a touch above the bar
    return {
        "width": width, "height": height, "fps": fps,
        "durationInFrames": int(round(duration * fps)),
        "audio": "narration.wav",
        "words": words,
        "scenes": scenes,
        "captionBottomPx": int(round(height * safe_bottom)),
        "captionFontSize": int(round(height * 0.032)),
    }


def render(sp, log=print):
    """Render `sp` via Remotion to <sp>/video/explainer_<aspect>.mp4. Returns a result dict.
    The heavy headless-Chrome+ffmpeg render should be wrapped by the caller's render-lock."""
    spec = build_spec(sp)
    stage = sp.work / "remotion"
    public = stage / "public"
    public.mkdir(parents=True, exist_ok=True)
    shutil.copy(sp.work / "narration.wav", public / "narration.wav")
    props = stage / "props.json"
    props.write_text(json.dumps(spec))

    aspect = sp.data.get("aspect", "9:16").replace(":", "x")
    outdir = sp.dir / "video"
    outdir.mkdir(exist_ok=True)
    out = outdir / f"explainer_{aspect}.mp4"

    npx = shutil.which("npx") or "npx"
    cmd = [npx, "remotion", "render", "src/index.ts", "Video", str(out),
           f"--props={props}", f"--public-dir={public}", "--log=error"]
    log(f"remotion: rendering {sp.dir.name} ({len(spec['scenes'])} scenes, {spec['durationInFrames']}f)")
    r = subprocess.run(cmd, cwd=str(REMOTION_DIR), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"remotion render failed:\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return {"engine": "remotion", "video": str(out), "scenes": len(spec["scenes"]),
            "duration_s": round(spec["durationInFrames"] / spec["fps"], 2)}
