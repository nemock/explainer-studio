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


def _scene_for(slide):
    """Map a deck slide -> (component, fields) per the motion-playbook §6 migration table.
    Unknown -> KineticHeadline (a clean animated headline). `image` fields stay as the
    deck's source path; render() stages them into the public dir."""
    t = slide.get("type")
    kicker = slide.get("kicker", "")
    accent = slide.get("accent", []) or []
    headline = slide.get("headline") or slide.get("title") or slide.get("word") or ""

    if t == "hook":
        return "Hero3D", {"kicker": kicker, "headline": headline, "accent": accent,
                          "shape": slide.get("shape", "ico")}
    if t in ("payoff", "cta"):
        return "CTA", {"kicker": kicker, "headline": headline, "accent": accent,
                       "subkicker": slide.get("subkicker", "")}
    if t == "punch":
        return "PunchWord", {"word": slide.get("word") or headline, "kicker": kicker,
                             "kind": slide.get("kind", "")}
    if t == "reframe":
        return "Reframe", {"before": slide.get("before", ""), "after": slide.get("after", "")}
    if t == "quote":
        return "Quote", {"quote": slide.get("quote") or headline,
                         "attribution": slide.get("attribution") or slide.get("source", "")}
    if t == "list":
        return "BuildList", {"kicker": kicker, "items": _items(slide)}
    if t in ("steps", "flow"):
        return "StepFlow", {"kicker": kicker, "steps": _items(slide)}
    if t == "sting":
        return "BrandSting", {"title": slide.get("title") or headline, "subtitle": slide.get("subtitle", "")}
    if t == "compare":
        return "SideBySide", {"left": slide.get("left", {}), "right": slide.get("right", {})}
    if t == "timeline":
        return "Timeline", {"kicker": kicker, "events": slide.get("events", [])}
    if t == "delta":
        return "SideBySide", {
            "left": {"title": slide.get("from_label", ""), "value": slide.get("from", "")},
            "right": {"title": slide.get("to_label", ""), "value": slide.get("to", "")}}
    if t in ("stat", "statgrid"):
        parsed = _parse_stat(slide.get("value"))
        if parsed:
            to, prefix = parsed
            return "StatCounter", {"kicker": kicker, "from": 0, "to": to,
                                   "prefix": prefix, "label": slide.get("label", "")}
        return "KineticHeadline", {"kicker": kicker, "headline": slide.get("value") or headline, "accent": accent}
    if t == "figure":
        return "Figure", {"kicker": kicker, "image": slide.get("image"),
                          "caption": slide.get("caption", ""), "highlight": slide.get("highlight")}
    if t == "footage":
        return "Footage", {"image": slide.get("image"), "headline": headline, "accent": accent}
    if t == "highlight":
        return "KineticHeadline", {"kicker": kicker, "headline": headline,
                                   "accent": slide.get("mark") or accent}
    return "KineticHeadline", {"kicker": kicker, "headline": headline, "accent": accent,
                               "accentRed": slide.get("accent2", [])}


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

    safe_bottom = float(sp.data.get("safe_bottom", 0.12)) + 0.04
    return {
        "width": width, "height": height, "fps": fps,
        "durationInFrames": int(round(duration * fps)),
        "audio": "narration.wav", "words": words, "scenes": scenes,
        "captionBottomPx": int(round(height * safe_bottom)),
        "captionFontSize": int(round(height * (0.032 if height >= 1600 else 0.026))),
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


def render(sp, log=print, frames=None, out=None):
    """Render `sp` via Remotion -> the final muxed mp4. `frames` (e.g. '0-2400') renders a
    range for fast preview. The heavy headless render should be wrapped by the render-lock."""
    if not (REMOTION_DIR / "node_modules").exists():
        raise RuntimeError(
            f"Remotion engine not installed: run `npm install` in {REMOTION_DIR} "
            f"(or use --engine deck). The motion engine needs the Node toolchain.")
    spec = build_spec(sp)
    stage = sp.work / "remotion"
    public = stage / "public"
    public.mkdir(parents=True, exist_ok=True)
    shutil.copy(sp.work / "narration.wav", public / "narration.wav")
    _stage_images(sp, spec, public)
    # CTA scenes show the brand book cover (a fixed asset, reused every video)
    if any(s["component"] == "CTA" for s in spec["scenes"]):
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
    return {"engine": "remotion", "video": str(out), "scenes": len(spec["scenes"]),
            "duration_s": round(spec["durationInFrames"] / spec["fps"], 2)}
