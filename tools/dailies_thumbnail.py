#!/usr/bin/env python3
"""YouTube thumbnail for a Dave Saunders Dailies episode (the daily founder tip and the
five weekday shows), 1280x720.

    bin/explainer2 submit --label thumb --cwd /Volumes/Casima/claudeCode/explainer2 -- \
        ~/myenv/bin/python3.12 tools/dailies_thumbnail.py <project> --render

What it composes, all from the project's own files:
  - the show, from the CTA slide's `mark` in deck.json (mark_fmf.png -> fmf). The theme
    alone cannot say which show it is: Robot Roundup renders on wsc-goldenrod.
  - the colors, from the project's theme in src/explainer2/themes.py.
  - the art: package/thumbnails/thumb_art.png, one cut-paper illustration of THIS
    episode's subject, generated at authoring time from the show's STYLE.md recipe with
    the subject in the right half (no text in it). Without it, the thumbnail falls back
    to the first library set the deck uses, which is on-brand but generic.
  - the headline: `thumbnail_text` on the youtube entry of meta.json's per_platform
    (2-5 words, written through humaner, adding something the title does not say), or
    --text to override.

Writes package/thumbnails/thumb.html, and with --render also thumb.png (2560x1440, which
youtube_upload.py compresses under YouTube's 2 MB cap) plus thumb.json recording what was
used. --render opens a browser, so it runs through the render queue (`explainer2
submit`), never directly from a session.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from explainer2.themes import THEMES  # noqa: E402

PUBLIC = REPO / "remotion" / "public"
FONTS = REPO / "src" / "explainer2" / "assets" / "fonts"

# show code (from the mark filename) -> the name printed on the thumbnail badge
SHOWS = {
    "fwf": "Daily Founder Tip",
    "mmt": "Monday MedTech",
    "ftt": "Founder Tip Tuesday",
    "rrp": "Robot Roundup",
    "ttd": "The Teardown",
    "fmf": "Failure Modes Friday",
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def slides_of(deck):
    return deck.get("slides", []) if isinstance(deck, dict) else deck


def show_code(slides):
    for s in slides:
        m = re.search(r"mark_([a-z]+)\.png", str(s.get("mark") or ""))
        if m:
            return m.group(1)
    raise SystemExit("no show mark in deck.json (the CTA slide's `mark`); "
                     "cannot tell which show this is")


def headline(proj, override):
    if override:
        return override.strip()
    for name in ("package/meta.json", "meta.json"):
        p = proj / name
        if not p.is_file():
            continue
        for e in load(p).get("per_platform") or []:
            if isinstance(e, dict) and e.get("platform") == "youtube" and e.get("thumbnail_text"):
                return e["thumbnail_text"].strip()
    raise SystemExit("no thumbnail_text on the youtube entry of meta.json per_platform, "
                     "and no --text given")


def art_for(proj, slides):
    art = proj / "package" / "thumbnails" / "thumb_art.png"
    if art.is_file():
        return art, "episode"
    for s in slides:
        if s.get("set") and (PUBLIC / s["set"]).is_file():
            return PUBLIC / s["set"], "library-set"
    raise SystemExit("no thumb_art.png and no library set in deck.json to fall back on")


def build_html(text, show_name, mark, art, theme):
    bg, fg, accent = theme["bg"], theme["fg"], theme["accent"]
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  @font-face {{ font-family: "Fraunces"; font-weight: 100 900;
    src: url("{(FONTS / 'fraunces-wght-normal.woff2').as_uri()}") format("woff2"); }}
  @font-face {{ font-family: "Inter"; font-weight: 100 900;
    src: url("{(FONTS / 'inter-wght-normal.woff2').as_uri()}") format("woff2"); }}
  html, body {{ margin: 0; width: 1280px; height: 720px; overflow: hidden; background: {bg}; }}
  .art {{ position: absolute; inset: 0; width: 1280px; height: 720px; object-fit: cover; }}
  .scrim {{ position: absolute; inset: 0;
    background: linear-gradient(90deg, {bg}e6 0%, {bg}b3 32%, {bg}00 48%); }}
  .badge {{ position: absolute; left: 52px; top: 40px; display: flex; align-items: center; gap: 16px; }}
  .badge img {{ width: 78px; height: 78px; object-fit: contain;
    filter: drop-shadow(0 4px 6px rgba(0,0,0,.35)); }}
  .badge span {{ font: 800 22px/1 "Inter", sans-serif; letter-spacing: 3px;
    text-transform: uppercase; color: {fg}; opacity: .92; }}
  .copy {{ position: absolute; left: 56px; top: 150px; width: 600px; height: 470px;
    display: flex; flex-direction: column; justify-content: center; }}
  h1 {{ margin: 0; font: 760 140px/1.0 "Fraunces", serif; letter-spacing: -2px; color: {fg};
    text-shadow: 0 4px 22px rgba(0,0,0,.35); overflow-wrap: break-word; }}
  .bar {{ margin-top: 30px; width: 130px; height: 12px; border-radius: 6px; background: {accent}; }}
</style></head>
<body>
  <img class="art" src="{art.as_uri()}">
  <div class="scrim"></div>
  <div class="badge"><img src="{mark.as_uri()}"><span>{html.escape(show_name)}</span></div>
  <div class="copy"><h1 id="h">{html.escape(text)}</h1><div class="bar"></div></div>
  <script>
    // Fit the headline: largest size (140px down to 64px) that stays within 3 lines and
    // inside the copy column. Deterministic, so a re-render gives the same thumbnail.
    // Measured only after the webfont loads: measuring the fallback serif let
    // "Cutting only buys time" pass at 140px and then wrap to four lines in Fraunces.
    const h = document.getElementById('h');
    const maxH = 470 - 42;
    document.fonts.ready.then(() => {{
      for (let s = 140; s >= 64; s -= 4) {{
        h.style.fontSize = s + 'px';
        const lines = Math.round(h.getBoundingClientRect().height / s);
        if (h.scrollWidth <= 600 && h.scrollHeight <= maxH && lines <= 3) break;
      }}
      document.body.dataset.fitted = '1';
    }});
  </script>
</body></html>"""


def render(page, png):
    """Screenshot the page at 2x (2560x1440) once the headline has been fitted.

    Not html2png.render: that waits a fixed 250 ms, and the headline is sized by script
    after the webfont loads, so a screenshot taken on a timer can catch it mid-fit."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        tab = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
        tab.goto(page.as_uri())
        tab.wait_for_selector("body[data-fitted='1']", state="attached", timeout=15000)
        tab.screenshot(path=str(png))
        browser.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--text", help="headline override (else meta.json thumbnail_text)")
    ap.add_argument("--render", action="store_true",
                    help="also write thumb.png (opens a browser: run via explainer2 submit)")
    args = ap.parse_args()

    proj = Path(args.project).resolve()
    slides = slides_of(load(proj / "deck.json"))
    code = show_code(slides)
    if code not in SHOWS:
        raise SystemExit(f"show '{code}' is not a Dailies show")
    theme_key = load(proj / "project.json").get("theme")
    if theme_key not in THEMES:
        raise SystemExit(f"unknown theme '{theme_key}' in project.json")
    mark = next(PUBLIC.glob(f"papercraft-{code}/mark_{code}.png"), None)
    if mark is None:
        raise SystemExit(f"missing show mark remotion/public/papercraft-{code}/mark_{code}.png")
    text = headline(proj, args.text)
    art, art_kind = art_for(proj, slides)

    out = proj / "package" / "thumbnails"
    out.mkdir(parents=True, exist_ok=True)
    page = out / "thumb.html"
    page.write_text(build_html(text, SHOWS[code], mark, art, THEMES[theme_key]), encoding="utf-8")
    record = {"show": code, "theme": theme_key, "text": text,
              "art": str(art), "art_kind": art_kind, "html": str(page)}

    if args.render:
        png = out / "thumb.png"
        render(page, png)
        record["png"] = str(png)
        (out / "thumb.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    if art_kind != "episode":
        print("WARNING: no package/thumbnails/thumb_art.png; used the library set "
              f"{art.name}, which is generic. Generate episode art for a better thumbnail.")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
