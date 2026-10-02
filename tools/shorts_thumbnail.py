#!/usr/bin/env python3
"""shorts_thumbnail.py: vertical (9:16) thumbnails for the Shorts cut from a deep dive or
masterclass module.

One base image per video, three thumbnails: every cut in shorts/plan.json shares
package/thumbnails/shorts/base_9x16.png (the main thumbnail's scene, regenerated tall in
Magnific so Dave keeps the same look) and gets its own headline from its plan entry:

    "thumbnail_text": "RABBIT FIRST",                         band, 1-4 words
    "thumbnail_sub":  "They set out to show it *didn't plan ahead*."  sub line; *x* = accent

Each cut also gets its own band color and alignment, so the three read as one set but can
be told apart side by side. Colors follow the project's theme (STYLES): the deep-dive
template (thumbnail-playbook §2), or a series' own card.

Layout QA is mechanical, not just a look: the page measures every text box after the fit,
and this script fails the cut if a box leaves the safe zone (the Shorts shelf lays the title
over the bottom of the image) or touches Dave's face (found with OpenCV on the base). Then
look at the contact sheet, a preview, never the full-res files (SKILL hard rule 9).

    shorts_thumbnail.py <project>            write the HTML pages only
    shorts_thumbnail.py <project> --render   also render <slug>.jpg + qa.json + sheet.jpg
                                             (opens a browser: run it through
                                             `explainer2 submit`, with the ~/myenv python)
"""
import argparse
import json
import sys
from pathlib import Path

W, H = 1080, 1920
SAFE = {"left": 54, "right": W - 54, "top": 96, "bottom": int(H * 0.75)}
FACE_PAD = 28
MIN_BAND_PX = 110          # below these the text is unreadable in the channel's Shorts grid,
MIN_SUB_PX = 60            # where a thumbnail shows about 210 px wide

# Per series look, keyed by project.json theme. A series with its own thumbnail card gets
# its own entry here, so its Shorts match its long-form card (Product Leadership's rust
# bands and navy sub on cream, Product_Leadership_Operators_Guide/CLAUDE.md). Variants are
# (band background, band text, sub accent, alignment), one per cut, in plan order.
DEEP_DIVE = {
    "scrim": "linear-gradient(180deg, rgba(4,8,20,.6) 0%, rgba(4,8,20,.3) 30%, rgba(4,8,20,0) 46%)",
    "sub": "#f5f7ff", "sub_shadow": "0 3px 20px rgba(0,0,0,.95)",
    "variants": [("#ff4d4d", "#ffffff", "#3ddc84", "left"),
                 ("#3ddc84", "#08121f", "#ff6b6b", "center"),
                 ("#f5f7ff", "#e8343a", "#3ddc84", "right")],
}
STYLES = {
    "midnight": DEEP_DIVE, "nemock-deep-dive": DEEP_DIVE, "brg-deep-dive": DEEP_DIVE,
    "plg-guide": {
        "scrim": "linear-gradient(180deg, rgba(245,240,235,.95) 0%, rgba(245,240,235,.7) 30%, rgba(245,240,235,0) 48%)",
        "sub": "#1b2b4b", "sub_shadow": "0 2px 10px rgba(245,240,235,.9)",
        "variants": [("#a8481f", "#ffffff", "#a8481f", "left"),
                     ("#a8481f", "#ffffff", "#a8481f", "center"),
                     ("#a8481f", "#ffffff", "#a8481f", "right")],
    },
}


def face_box(base):
    """Largest frontal face in the base, in page px (the base is laid out object-fit: cover)."""
    import cv2
    img = cv2.imread(str(base))
    if img is None:
        raise SystemExit(f"cannot read {base}")
    ih, iw = img.shape[:2]
    scale = max(W / iw, H / ih)
    ox, oy = (iw * scale - W) / 2, (ih * scale - H) / 2
    small = cv2.resize(img, (int(iw * scale), int(ih * scale)))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(120, 120))
    if len(faces) == 0:
        raise SystemExit("no face found in the base: the face check cannot run, so nothing renders")
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    # the detector's box stops at the brows; extend up to cover the hair
    return {"left": int(x - ox), "top": int(y - oy - 0.35 * h),
            "right": int(x - ox + w), "bottom": int(y - oy + h)}


def band_lines(text):
    """Split a band longer than ~11 characters into two balanced lines."""
    words = text.split()
    if len(text) <= 11 or len(words) < 2:
        return [text]
    best = min(range(1, len(words)),
               key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    return [" ".join(words[:best]), " ".join(words[best:])]


def sub_html(sub, accent):
    parts = sub.split("*")
    return "".join(f'<span style="color:{accent}">{p}</span>' if i % 2 else p
                   for i, p in enumerate(parts))


def build_html(base_rel, cut, style, variant, face):
    bg, fg, accent, align = variant
    bands = "".join(f'<div class="band">{line}</div>' for line in band_lines(cut["thumbnail_text"]))
    sub = sub_html(cut.get("thumbnail_sub", ""), accent)
    limit = face["top"] - FACE_PAD
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
  * {{ margin:0; box-sizing:border-box; }}
  body {{ width:{W}px; height:{H}px; overflow:hidden; position:relative; background:#090d1c;
    font-family:-apple-system,"Helvetica Neue",Arial,sans-serif; }}
  .base {{ position:absolute; inset:0; width:{W}px; height:{H}px; object-fit:cover; }}
  .scrim {{ position:absolute; inset:0; background:{style['scrim']}; }}
  .text {{ position:absolute; left:{SAFE['left'] + 16}px; right:{W - SAFE['right'] + 16}px;
    top:{SAFE['top'] + 70}px; text-align:{align}; z-index:2; }}
  .band {{ display:inline-block; background:{bg}; color:{fg}; font-weight:900;
    letter-spacing:-.02em; padding:.04em .22em; border-radius:.12em; line-height:1.04;
    box-shadow:0 18px 70px rgba(0,0,0,.45); white-space:nowrap; }}
  .band + .band {{ margin-top:.12em; }}
  .bands {{ display:flex; flex-direction:column;
    align-items:{ {'left': 'flex-start', 'center': 'center', 'right': 'flex-end'}[align] }; }}
  .sub {{ margin-top:40px; font-weight:900; color:{style['sub']}; line-height:1.16;
    text-shadow:{style['sub_shadow']}; }}
</style></head><body>
  <img class="base" src="{base_rel}">
  <div class="scrim"></div>
  <div class="text"><div class="bands">{bands}</div><div class="sub">{sub}</div></div>
<script>
document.fonts.ready.then(() => {{
  const text = document.querySelector('.text'), bands = [...document.querySelectorAll('.band')],
        sub = document.querySelector('.sub'), maxW = text.clientWidth, limit = {limit};
  let bandPx = 260, subPx = 88;
  const apply = () => {{ bands.forEach(b => b.style.fontSize = bandPx + 'px');
                         sub.style.fontSize = subPx + 'px'; }};
  apply();
  while (bandPx > 80 && bands.some(b => b.getBoundingClientRect().width > maxW)) {{ bandPx -= 4; apply(); }}
  while (text.getBoundingClientRect().bottom > limit && (bandPx > 80 || subPx > 40)) {{
    if (subPx > 64) subPx -= 2; else bandPx -= 4;
    apply();
  }}
  // center the block in the wall between the safe top and the face
  const r0 = text.getBoundingClientRect(), roomTop = {SAFE['top']};
  text.style.top = Math.max(roomTop, roomTop + (limit - roomTop - r0.height) / 2) + 'px';
  const box = el => {{ const r = el.getBoundingClientRect();
    return {{left: r.left, top: r.top, right: r.right, bottom: r.bottom}}; }};
  document.body.dataset.boxes = JSON.stringify({{
    band_px: bandPx, sub_px: subPx, boxes: [...bands, sub].map(box) }});
  document.body.dataset.fitted = '1';
}});
</script>
</body></html>
"""


def check(measure, face):
    problems = []
    if measure["band_px"] < MIN_BAND_PX:
        problems.append(f"band shrank to {measure['band_px']}px (min {MIN_BAND_PX}): headline too long")
    if measure["sub_px"] < MIN_SUB_PX:
        problems.append(f"sub shrank to {measure['sub_px']}px (min {MIN_SUB_PX}): sub line too long")
    for b in measure["boxes"]:
        if (b["left"] < SAFE["left"] or b["right"] > SAFE["right"]
                or b["top"] < SAFE["top"] or b["bottom"] > SAFE["bottom"]):
            problems.append(f"text box {b} leaves the safe zone {SAFE}")
        if not (b["right"] < face["left"] - FACE_PAD or b["left"] > face["right"] + FACE_PAD
                or b["bottom"] < face["top"] - FACE_PAD or b["top"] > face["bottom"] + FACE_PAD):
            problems.append(f"text box {b} overlaps the face {face}")
    return problems


def render(pages, out_dir):
    from playwright.sync_api import sync_playwright
    measures = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        tab = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for slug, page in pages:
            tab.goto(page.as_uri())
            tab.wait_for_selector("body[data-fitted='1']", state="attached", timeout=15000)
            measures[slug] = json.loads(tab.evaluate("document.body.dataset.boxes"))
            tab.screenshot(path=str(out_dir / f"{slug}.jpg"), type="jpeg", quality=90)
        browser.close()
    return measures


def contact_sheet(out_dir, slugs):
    from PIL import Image
    tiles = [Image.open(out_dir / f"{s}.jpg").resize((360, 640)) for s in slugs]
    sheet = Image.new("RGB", (len(tiles) * 380 + 20, 680), "#222")
    for i, t in enumerate(tiles):
        sheet.paste(t, (20 + i * 380, 20))
    sheet.save(out_dir / "sheet.jpg", quality=88)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()

    proj = Path(args.project).resolve()
    out_dir = proj / "package" / "thumbnails" / "shorts"
    base = out_dir / "base_9x16.png"
    if not base.exists():
        raise SystemExit(f"no vertical base at {base} (thumbnail-playbook §10 makes it)")
    cuts = json.loads((proj / "shorts" / "plan.json").read_text())
    missing = [c["slug"] for c in cuts if not c.get("thumbnail_text")]
    if missing:
        raise SystemExit(f"plan.json cuts without thumbnail_text: {missing}")

    theme = json.loads((proj / "project.json").read_text()).get("theme")
    style = STYLES.get(theme)
    if style is None:
        print(f"WARNING: no Shorts style for theme {theme!r}; using the deep-dive colors. If this "
              f"series has its own thumbnail card, add it to STYLES (thumbnail-playbook §10).")
        style = DEEP_DIVE
    face = face_box(base)
    pages = []
    for i, cut in enumerate(cuts):
        page = out_dir / f"{cut['slug']}.html"
        variant = style["variants"][i % len(style["variants"])]
        page.write_text(build_html(base.name, cut, style, variant, face))
        pages.append((cut["slug"], page))
        print("wrote", page)
    if not args.render:
        return 0

    measures = render(pages, out_dir)
    qa = {"face": face, "safe": SAFE, "cuts": {}}
    failed = False
    for slug, m in measures.items():
        problems = check(m, face)
        failed |= bool(problems)
        qa["cuts"][slug] = {"file": f"{slug}.jpg", **m, "problems": problems}
        print(f"{slug}: band {m['band_px']}px, sub {m['sub_px']}px, "
              + ("OK" if not problems else "FAIL\n  " + "\n  ".join(problems)))
    (out_dir / "qa.json").write_text(json.dumps(qa, indent=2) + "\n")
    contact_sheet(out_dir, [s for s, _ in pages])
    print("sheet", out_dir / "sheet.jpg")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
