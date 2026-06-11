"""Adobe Stock assist (PRD §5.4) — the one allowed subscription, human-in-the-loop.

No API. The flow:
  1. Generation plane writes assets/queue.json: per-scene search suggestions
     ({"slide": "s21", "queries": ["..."], "orientation": "horizontal",
       "note": "...", "status": "pending"}).
  2. `explainer2 assets <dir> open [--slide sNN]` opens stock.adobe.com searches
     in the browser; the operator licenses + downloads into assets/inbox/.
  3. `explainer2 assets <dir> ingest` conforms everything in inbox/:
     video → assets/mezzanine/<slide>__<name>.mp4 (project-size letterboxed,
     bt709, high-bitrate H.264); image → .png. Originals are preserved in
     assets/originals/. License provenance (Adobe Stock asset id parsed from
     the filename) is appended to assets/licenses.json, which manifest v2
     embeds.
  4. Filename convention: prefix a download with the slide id ("s21 city.mp4")
     to auto-assign; otherwise it lands unassigned and `assets status` says so.

Every footage scene keeps a designed deck fallback — a missing asset never
blocks a render (PRD R4).
"""
import json
import re
import subprocess
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
ADOBE_ID = re.compile(r"(?:AdobeStock[_-]?)(\d{6,})", re.I)
SLIDE_PREFIX = re.compile(r"^(s\d{2})[ _-]+", re.I)


def _queue_path(proj):
    return proj.dir / "assets" / "queue.json"


def load_queue(proj):
    p = _queue_path(proj)
    return json.loads(p.read_text()) if p.exists() else []


def save_queue(proj, queue):
    p = _queue_path(proj)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(queue, indent=2))


def cmd_open(proj, slide=None):
    queue = load_queue(proj)
    if not queue:
        return {"error": "no assets/queue.json — author it first (see skill §assets)"}
    opened = []
    for item in queue:
        if slide and item.get("slide") != slide:
            continue
        if item.get("status") == "fulfilled":
            continue
        for q in item.get("queries", [])[:1]:  # first query per scene; more via --slide
            url = f"https://stock.adobe.com/search?k={quote_plus(q)}"
            if item.get("orientation"):
                url += f"&filters%5Borientation%5D={item['orientation']}"
            webbrowser.open(url)
            opened.append({"slide": item.get("slide"), "query": q})
    return {"opened": opened,
            "inbox": str(proj.dir / "assets" / "inbox"),
            "hint": "download into the inbox; prefix filenames with the slide id (e.g. 's21 traffic.mp4')"}


def _probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,width,height,duration", "-of", "json", str(path)],
                       capture_output=True, text=True)
    try:
        streams = json.loads(r.stdout).get("streams", [])
    except json.JSONDecodeError:
        return None
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    return v


def _conform_video(src, dst, w, h):
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
          f"colorspace=all=bt709:iall=bt601-6-625:fast=1")
    subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(src), "-vf", vf,
                    "-an", "-c:v", "h264_videotoolbox", "-b:v", "20M",
                    "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                    str(dst)], check=True, capture_output=True)


def _conform_image(src, dst, w, h):
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")
    subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(src), "-vf", vf,
                    "-frames:v", "1", str(dst)], check=True, capture_output=True)


def cmd_ingest(proj):
    w, h = proj.size
    adir = proj.dir / "assets"
    inbox, mezz, orig = adir / "inbox", adir / "mezzanine", adir / "originals"
    for d in (inbox, mezz, orig):
        d.mkdir(parents=True, exist_ok=True)
    lic_path = adir / "licenses.json"
    licenses = json.loads(lic_path.read_text()) if lic_path.exists() else []
    queue = load_queue(proj)
    by_slide = {item.get("slide"): item for item in queue}

    results = []
    for f in sorted(inbox.iterdir()):
        if f.name.startswith(".") or f.is_dir():
            continue
        ext = f.suffix.lower()
        if ext not in VIDEO_EXT | IMAGE_EXT:
            results.append({"file": f.name, "status": "skipped (unknown type)"})
            continue
        m = SLIDE_PREFIX.match(f.name)
        slide = m.group(1).lower() if m else None
        stem = re.sub(r"[^a-z0-9]+", "-", f.stem.lower()).strip("-")[:48]
        out_name = (f"{slide}__{stem}" if slide else stem)
        try:
            if ext in VIDEO_EXT:
                out = mezz / f"{out_name}.mp4"
                _conform_video(f, out, w, h)
            else:
                out = mezz / f"{out_name}.png"
                _conform_image(f, out, w, h)
        except subprocess.CalledProcessError as e:
            results.append({"file": f.name, "status": f"FAILED conform: {e}"})
            continue
        aid = ADOBE_ID.search(f.name)
        licenses.append({
            "file": str(out.relative_to(proj.dir)), "original_name": f.name,
            "source": "stock.adobe.com" if aid else "operator-supplied",
            "adobe_stock_id": aid.group(1) if aid else None,
            "slide": slide, "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        if slide and slide in by_slide:
            by_slide[slide]["status"] = "fulfilled"
            by_slide[slide]["file"] = str(out.relative_to(proj.dir))
        f.rename(orig / f.name)
        results.append({"file": f.name, "status": "ok", "mezzanine": out.name,
                        "slide": slide or "UNASSIGNED"})
    lic_path.write_text(json.dumps(licenses, indent=2))
    if queue:
        save_queue(proj, queue)
    return {"ingested": results, "licenses": str(lic_path.relative_to(proj.dir))}


def cmd_status(proj):
    queue = load_queue(proj)
    return {"queue": [{"slide": i.get("slide"), "status": i.get("status", "pending"),
                       "file": i.get("file"), "queries": i.get("queries", [])[:1]}
                      for i in queue],
            "pending": sum(1 for i in queue if i.get("status") != "fulfilled")}


def run(proj, action, slide=None):
    if action == "open":
        return cmd_open(proj, slide=slide)
    if action == "ingest":
        return cmd_ingest(proj)
    return cmd_status(proj)
