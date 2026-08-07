# VENDORED_FROM: nemock/video-explainer-system @ d593aa41dc32d04e3b714b4731b1763f6e31843e (src/explainer/stills.py) — copied 2026-06-10; diverges freely (v1 is frozen).
"""STILLS — export one PNG per slide from the rendered deck, for repurposing/reference
(carousel re-use, thumbnails, decks, blog). Renders deck/index.html via Playwright and
drives renderAt(t) to each slide's *settled* moment (past the intro motion), then
screenshots. Read-only w.r.t. the pipeline; requires the deck + timeline, so run it
after `explainer media` (or at least the deck + align stages)."""
import json
import subprocess
from playwright.sync_api import sync_playwright


def _settled_t(s, duration):
    """A slide's *settled* moment: past the intro motion, before the next slide."""
    win = s["end"] - s["start"]
    t = s["start"] + min(win * 0.6, max(0.8, win - 0.2))
    return max(s["start"], min(t, duration - 0.01))


def _run_remotion(proj, aspect, timeline):
    """Remotion-engine path (2026-08-06): there is no deck/index.html to drive — the
    engine writes the final mp4 directly — so extract each slide's settled frame from
    the rendered video with ffmpeg instead. Caught by the cutover compatibility check:
    the v1 Playwright path hard-fails on Remotion projects, and stills sits mid-chain
    in the recording watcher's Phase 1, so that failure would have wedged every booth
    show. Single-frame decodes are trivial — no render lock needed."""
    slides, duration = timeline["slides"], timeline["duration"]
    video = proj.dir / "video" / f"explainer_{aspect.replace(':', 'x')}.mp4"
    if not video.exists():
        raise FileNotFoundError(
            f"stills (remotion path): {video} not found — render this aspect first")
    out = proj.dir / "stills"
    out.mkdir(exist_ok=True)
    for f in out.glob("*.png"):
        f.unlink()
    written = []
    for i, s in enumerate(slides, 1):
        name = f"slide_{i:02d}_{s['id']}.png"
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", f"{_settled_t(s, duration):.3f}",
             "-i", str(video), "-frames:v", "1", str(out / name)],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"stills frame extract failed for {name}: {r.stderr[-400:]}")
        written.append(name)
    return {"aspect": aspect, "count": len(written), "dir": "stills",
            "files": written, "engine": "remotion"}


def run(proj, aspect=None):
    timeline = json.loads((proj.work / "timeline.json").read_text())
    slides = timeline["slides"]
    duration = timeline["duration"]
    aspect = aspect or proj.aspect
    if not (proj.deck_dir / "index.html").exists():
        return _run_remotion(proj, aspect, timeline)
    w, h = proj.size_for(aspect)
    deck_url = (proj.deck_dir / "index.html").as_uri()
    out = proj.dir / "stills"
    out.mkdir(exist_ok=True)
    for f in out.glob("*.png"):
        f.unlink()

    written = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb", "--hide-scrollbars", "--disable-gpu"])
        page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        page.goto(deck_url)
        page.wait_for_function("window.__deckReady === true")
        page.evaluate("tl => { window.TIMELINE = tl; }", timeline)
        for i, s in enumerate(slides, 1):
            win = s["end"] - s["start"]
            # settle past the intro transition, before the next slide takes over
            t = s["start"] + min(win * 0.6, max(0.8, win - 0.2))
            t = max(s["start"], min(t, duration - 0.01))
            page.evaluate("t => window.renderAt(t)", t)
            name = f"slide_{i:02d}_{s['id']}.png"
            page.screenshot(path=str(out / name), clip={"x": 0, "y": 0, "width": w, "height": h})
            written.append(name)
        page.close()
        browser.close()

    return {"aspect": aspect, "count": len(written), "dir": "stills", "files": written}
