#!/usr/bin/env python3
"""Tall (1:1 to 4:5) document-excerpt crop for a Short's `image_9x16`, plus the focus
phrase's mark measured in IMAGE space off the crop it writes.

Why (2026-09-25, #69): document `figure` crops are cut wide for the 16:9 long-form (#69's
extractor pads to 2.8:1). A Short's figure mount is at most ~640 px wide on the 1080 px
frame, so the type size is set by how many characters span that width. A full-width court
line is ~80 characters, which is ~6 pt text on a phone however the crop is padded or zoomed.
Only a NARROWER window makes the type larger. So this crop:

  - keeps the page's own line breaks (it rewraps nothing, it only crops the PDF);
  - takes a window narrower than the text column, centred on the focus phrase and clamped
    to the column, so each line shows ~30-45 characters;
  - snaps top and bottom to whole lines (glyph-bounded, as in #69's extract_docshots.py),
    adding lines around the focus until the window reaches the target aspect or --lines
    (default 9), whichever comes first; or exactly the quote's lines with --span. FEWER lines, not more context: a single-spaced
    opinion fills 4:5 with ~17 lines, most of them another paragraph, so the line cap
    usually wins and the canvas is padded to the aspect with white paper instead;
  - paints out any word the window's side edges would slice (--whole-words, the default),
    so every line reads as whole words with a ragged edge rather than "ls in every";
  - pads to the exact aspect, then by --safe, so a gentle `moves_9x16` zoom doesn't clip.

Pair it with a `moves_9x16` tour whose scale stays at or below ~1.15. With NO moves the
Figure falls back to its automatic Ken Burns (scale 1.04 -> 1.22 plus a pan), which needs
--safe 0.76 like the landscape crops.

Usage (flat args; permission-matcher friendly):
  python3 tools/docshot_portrait.py <doc.pdf> <out.png> --focus "typically ten."
      [--focus "second phrase to union"] [--context "phrase that picks the page"]
      [--span "first quoted line" --span "last quoted line"]
      [--ar 0.8] [--width-pt 0] [--lines 9] [--safe 0.84] [--no-whole-words]
      [--marks-json <assets/docshots/marks.json> --name n9_lives_9x16]

Prints one JSON object: image, size, page (1-based), mark {at, w, h} in IMAGE space, and a
suggested_move. The mark is a measurement; you still choose its kind and cue in deck.json,
and you still frame-check the rendered Short (deck-playbook §4b).

Importable too: sys.path.insert(0, "<explainer2>/tools"); from docshot_portrait import portrait_crop
"""
import argparse
import json
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

MIN_W_PT, MAX_W_PT = 200.0, 320.0   # auto window width, in PDF points (~30-50 chars of 12 pt)
OUT_W_PX = 1100                     # render the window at least this wide (crisp at 1080p)


def _txt(ln):
    return "".join(s["text"] for s in ln["spans"]).strip()


def _lines(page):
    """Text lines with glyph-bounded y (baseline -/+ ascent/descent). Stamps (tall/rotated)
    and pleading-paper line numbers (digit-only lines) are dropped, as in extract_docshots."""
    out = []
    for blk in page.get_text("dict")["blocks"]:
        if blk.get("type") != 0:
            continue
        for ln in blk["lines"]:
            if (ln["bbox"][3] - ln["bbox"][1]) >= 40 or not _txt(ln) or _txt(ln).isdigit():
                continue
            y0 = min(s["origin"][1] - 0.80 * s["size"] for s in ln["spans"])
            y1 = max(s["origin"][1] + 0.26 * s["size"] for s in ln["spans"])
            out.append({"x0": ln["bbox"][0], "x1": ln["bbox"][2], "y0": y0, "y1": y1})
    return sorted(out, key=lambda l: l["y0"])


def portrait_crop(pdf, out, focus, context=(), ar=0.8, width_pt=0.0, safe=0.84,
                  whole_words=True, max_lines=9, spans=()):
    doc = fitz.open(str(pdf))
    page = None
    for p in doc:
        if all(p.search_for(ph) for ph in list(focus) + list(context) + list(spans)):
            page = p
            break
    if page is None:
        raise SystemExit(f"no page carries every focus/context phrase: {list(focus) + list(context)}")

    fr = None                        # the focus: first hit of each phrase, unioned
    for ph in focus:
        r = page.search_for(ph)[0]
        fr = r if fr is None else fr | r

    # The text column: lines that share x with the focus, within ~a screen of it.
    near = [l for l in _lines(page) if abs(l["y0"] - fr.y0) < 300]
    col = [l for l in near if l["x1"] > fr.x0 and l["x0"] < fr.x1]
    if not col:
        raise SystemExit("no text lines found around the focus")
    col_x0, col_x1 = min(l["x0"] for l in col), max(l["x1"] for l in col)

    w = width_pt or min(MAX_W_PT, max(MIN_W_PT, fr.width * 1.6))
    w = min(w, col_x1 - col_x0 + 8)
    if w < fr.width + 8:
        raise SystemExit(f"window {w:.0f}pt is narrower than the focus ({fr.width:.0f}pt); "
                         f"pass a larger --width-pt or a shorter --focus")
    cx = (fr.x0 + fr.x1) / 2
    x0 = min(max(cx - w / 2, col_x0 - 4), col_x1 + 4 - w)
    lines = [l for l in near if l["x1"] > x0 and l["x0"] < x0 + w]   # lines the window shows

    # Whole lines, grown outward from the focus line(s) until the target height is reached.
    def _ov(l):
        a, b = max(l["y0"], fr.y0), min(l["y1"], fr.y1)
        return max(0.0, b - a) / max(1e-6, l["y1"] - l["y0"])
    hit = [i for i, l in enumerate(lines) if _ov(l) >= 0.5]
    if not hit:
        raise SystemExit("the focus sits on no detected text line")
    i0, i1 = min(hit), max(hit)
    if spans:   # the quote's own lines, exactly: every line a --span phrase touches
        # the hit nearest the focus, per phrase: "company." occurs all over a page
        sr = [min(page.search_for(ph), key=lambda r: abs(r.y0 - fr.y0)) for ph in spans]
        span_y0, span_y1 = min(r.y0 for r in sr), max(r.y1 for r in sr)
        on = [i for i, l in enumerate(lines)
              if min(l["y1"], span_y1) - max(l["y0"], span_y0) >= 0.5 * (l["y1"] - l["y0"])]
        i0, i1 = min(on + [i0]), max(on + [i1])
    target_h = w / ar
    grow_up = True
    while not spans and i1 - i0 + 1 < max_lines:
        cand = [(i0 - 1, i1)] if grow_up else [(i0, i1 + 1)]
        cand += [(i0, i1 + 1)] if grow_up else [(i0 - 1, i1)]
        for a, b in cand:
            if 0 <= a and b < len(lines) and lines[b]["y1"] - lines[a]["y0"] + 6 <= target_h:
                i0, i1 = a, b
                break
        else:
            break
        grow_up = not grow_up
    # 3 pt of air, but never past the midpoint to a neighbouring line: single-spaced
    # opinions leave ~2 pt between glyph boxes, and a flat pad showed the next line's tops.
    y0 = lines[i0]["y0"] - 3
    if i0 > 0:
        y0 = max(y0, (lines[i0 - 1]["y1"] + lines[i0]["y0"]) / 2)
    y1 = lines[i1]["y1"] + 3
    if i1 + 1 < len(lines):
        y1 = min(y1, (lines[i1]["y1"] + lines[i1 + 1]["y0"]) / 2)
    clip = fitz.Rect(x0, y0, x0 + w, y1) & page.rect

    zoom = max(3.0, OUT_W_PX / clip.width)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    if whole_words:
        d = ImageDraw.Draw(im)
        mp = max(3, int(round(0.9 * zoom)))   # word boxes run short of the ink (#69: a stray tick)
        for wx0, wy0, wx1, wy1, *_ in page.get_text("words"):
            if wy1 < clip.y0 or wy0 > clip.y1 or wx1 < clip.x0 or wx0 > clip.x1:
                continue
            if wx0 < clip.x0 - 0.5 or wx1 > clip.x1 + 0.5:   # sliced by a side edge
                d.rectangle([(max(wx0, clip.x0) - clip.x0) * zoom - mp,
                             (max(wy0, clip.y0) - clip.y0) * zoom - 2,
                             (min(wx1, clip.x1) - clip.x0) * zoom + mp,
                             (min(wy1, clip.y1) - clip.y0) * zoom + 2], fill="white")

    w0, h0 = im.size
    if w0 / h0 > ar:
        W1, H1 = w0, int(round(w0 / ar))
    else:
        W1, H1 = int(round(h0 * ar)), h0
    W, H = int(round(W1 / safe)), int(round(H1 / safe))
    ox, oy = (W - w0) // 2, (H - h0) // 2
    canvas = Image.new("RGB", (W, H), "white")
    canvas.paste(im, (ox, oy))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)

    # Mark: the focus rect in IMAGE space, with the same 1.10 x 1.25 breathing room the
    # landscape extractor uses (1.1 in y when the focus spans lines).
    px = lambda x: ((x - clip.x0) * zoom + ox) / W
    py = lambda y: ((y - clip.y0) * zoom + oy) / H
    hm = 1.25 if len(focus) == 1 else 1.1
    # ...but never taller than the line pitch for a one-line focus. On a single-spaced
    # opinion (#69 n9_lives, ~14.7 pt pitch, ~13 pt line box) 1.25x put the rough box's top
    # and bottom strokes through the neighbouring lines. On a tall image the stroke also
    # wobbles more vertically (FigureMarks stretches a 16:9 viewBox), so leave it air.
    fh = fr.height * hm
    tops = sorted(l["y0"] for l in lines)
    gaps = sorted(b - a for a, b in zip(tops, tops[1:]) if b - a > 1)
    if len(focus) == 1 and gaps:
        fh = min(fh, 0.9 * gaps[len(gaps) // 2])
    mark = {"at": [round(px((fr.x0 + fr.x1) / 2), 4), round(py((fr.y0 + fr.y1) / 2), 4)],
            "w": round(min(0.92, fr.width * zoom * 1.10 / W), 4),
            "h": round(min(0.80, fh * zoom / H), 4)}
    # The zoom that fills the mount with the text's width (1/safe), centred in x so neither
    # ragged edge is cut, and in y on the focus, held where the view stays on the canvas.
    z = round(1 / safe, 2)
    ymv = round(min(max(mark["at"][1], 0.5 / z), 1 - 0.5 / z), 4)
    return {"image": str(out), "size": [W, H], "page": page.number + 1,
            "lines": i1 - i0 + 1, "window_pt": round(clip.width, 1), "mark": mark,
            "suggested_move": {"to": {"x": 0.5, "y": ymv, "scale": z}}}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pdf")
    ap.add_argument("out")
    ap.add_argument("--focus", action="append", required=True,
                    help="phrase to ring; repeat to union a phrase that wraps a line")
    ap.add_argument("--context", action="append", default=[],
                    help="extra phrase that must be on the same page (picks the page)")
    ap.add_argument("--ar", type=float, default=0.8, help="width/height, 0.8 (4:5) to 1.0")
    ap.add_argument("--width-pt", type=float, default=0.0,
                    help="window width in PDF points (default: focus x1.6, clamped 200-320)")
    ap.add_argument("--safe", type=float, default=0.84)
    ap.add_argument("--span", action="append", default=[],
                    help="phrase(s) whose lines ARE the crop (first..last), like the landscape "
                         "extractor's spans; overrides --lines growth")
    ap.add_argument("--lines", type=int, default=9,
                    help="most lines to show; short of the aspect, the canvas is padded instead")
    ap.add_argument("--no-whole-words", dest="whole_words", action="store_false")
    ap.add_argument("--marks-json", default=None, help="merge the mark into this file")
    ap.add_argument("--name", default=None, help="key for --marks-json (default: out stem)")
    a = ap.parse_args()
    if not 0.5 <= a.ar <= 1.25:
        sys.exit("--ar is width/height; a portrait docshot wants 0.8 (4:5) to 1.0 (1:1)")
    r = portrait_crop(a.pdf, a.out, a.focus, a.context, a.ar, a.width_pt, a.safe, a.whole_words,
                      a.lines, a.span)
    if a.marks_json:
        mp = Path(a.marks_json)
        allm = json.loads(mp.read_text()) if mp.exists() else {}
        allm[a.name or Path(a.out).stem] = r["mark"]
        mp.write_text(json.dumps(allm, indent=2))
    print(json.dumps(r))


if __name__ == "__main__":
    main()
