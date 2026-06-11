"""Dev/production utility: render an HTML file to a PNG at an exact pixel size
via headless Chromium (Playwright). Used for artifact visuals (spreadsheets,
document teardowns, calendars) embedded in decks as `figure` slides, and later
for thumbnails (PRD §5.7).

Usage: python tools/html2png.py <in.html> <out.png> [--width 1600] [--height 900]
"""
import argparse
from pathlib import Path


def render(src, out, width=1600, height=900):
    from playwright.sync_api import sync_playwright
    src, out = Path(src).resolve(), Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height},
                                device_scale_factor=2)  # 2x for crisp text in video
        page.goto(src.as_uri())
        page.wait_for_timeout(250)  # fonts settle
        page.screenshot(path=str(out))
        browser.close()
    return str(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=900)
    a = ap.parse_args()
    print(render(a.src, a.out, a.width, a.height))
