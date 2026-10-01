"""Dev/production utility: render an HTML file to a PNG at an exact pixel size
via headless Chromium (Playwright). Used for artifact visuals (spreadsheets,
document teardowns, calendars) embedded in decks as `figure` slides, and later
for thumbnails (PRD §5.7).

Usage: python tools/html2png.py <in.html> <out.png> [--width 1600] [--height 900]

The viewport defaults to 1600x900, but a thumbnail card's body is a fixed
1280x720. Render one into the other and the extra 320x180 CSS px come out as a
white L-band down the right edge and along the bottom — a PNG that is still 16:9,
still opens fine, and carries no error. Module 3 of the Product Leadership series
shipped to YouTube that way. So: measure the body box and refuse to write a PNG
whose page does not fill the viewport, unless --allow-underfill says it is
deliberate.
"""
import argparse
import sys
from pathlib import Path


class UnderfilledPage(Exception):
    """The page's body is smaller than the viewport — the PNG would have blank margins."""


def render(src, out, width=1600, height=900, allow_underfill=False):
    from playwright.sync_api import sync_playwright
    src, out = Path(src).resolve(), Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height},
                                device_scale_factor=2)  # 2x for crisp text in video
        page.goto(src.as_uri())
        page.wait_for_timeout(250)  # fonts settle
        box = page.evaluate(
            "() => { const r = document.body.getBoundingClientRect();"
            "        return {w: r.width + r.left, h: r.height + r.top}; }")
        if not allow_underfill and (box["w"] < width - 1 or box["h"] < height - 1):
            browser.close()
            raise UnderfilledPage(
                f"{src.name} lays out {box['w']:.0f}x{box['h']:.0f} CSS px inside a "
                f"{width}x{height} viewport, so the PNG would carry blank margins.\n"
                f"  Pass --width {box['w']:.0f} --height {box['h']:.0f} to match the page "
                f"(thumbnail cards are 1280x720 — see thumbnail-playbook §6),\n"
                f"  or --allow-underfill if the margins are intended.")
        page.screenshot(path=str(out))
        browser.close()
    return str(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--allow-underfill", action="store_true",
                    help="render even though the page does not fill the viewport")
    a = ap.parse_args()
    # Every render on this Mac goes through the machine-global render lock, whatever its
    # length (operator directive 2026-10-01), and this launches headless Chromium. Only
    # the CLI takes the lock, so a caller already holding it can still import render().
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from explainer2 import renderlock
    lock = renderlock.acquire(label=f"html2png:{Path(a.out).name}")
    try:
        print(render(a.src, a.out, a.width, a.height, a.allow_underfill))
    except UnderfilledPage as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(2)
    finally:
        renderlock.release(lock)
