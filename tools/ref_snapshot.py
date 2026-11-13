#!/usr/bin/env python3
"""ref_snapshot.py — check a reference URL and save a full-page screenshot of it, as it was
when it was used, into the project.

Operator request 2026-11-12: every web page used as a reference gets (1) its URL checked and
(2) a picture of the page in the state it was in when it was cited, saved with the project.
Pages change and links rot; the snapshot is the record of what the source said that day.

This is separate from make_money/scripts/webfetch.py on purpose. webfetch is for READING: it
serves a cached archive copy first, which can be days old, and it is shared by every routine.
This is for CITING: it always loads the live page.

  ~/myenv/bin/python3.12 tools/ref_snapshot.py <project_dir> <url> [--claim <wiki-claim-id>]
  ~/myenv/bin/python3.12 tools/ref_snapshot.py <project_dir> <url> --import <file.png|.pdf>
  ~/myenv/bin/python3.12 tools/ref_snapshot.py <project_dir> --list

Writes  <project>/sources/snapshots/<date>_<host>_<slug>.jpg   (a PDF source: the .pdf itself)
and a row in  <project>/sources/snapshots.json  (url, final_url, status, title, captured_at,
file, sha256, method, claim). One snapshot per URL per project; `--again` takes another.
Both are committed with the project in explainer-content (operator 2026-11-12); only the
frame_preview.py copies under sources/snapshots/previews/ are gitignored.

HTML pages load in headless Chromium at 1280 px wide and are captured full length, the same
picture Chrome's own "Capture full size screenshot" makes, saved as JPEG to keep the repo
small. A login wall or bot check can't be captured headless: exit 3, then capture it in
Claude in Chrome (or by hand) and record it with --import.

Exit: 0 saved (or already had one) · 1 usage · 2 failed · 3 needs a real browser ·
4 the URL is dead (404/410/DNS), so it must not be cited as it stands.
"""
import argparse
import hashlib
import io
import json
import re
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0 Safari/537.36")
WALL_HINTS = re.compile(r"just a moment|verify you are human|captcha|access denied|"
                        r"sign in to continue|log in to continue|subscribe to continue", re.I)
MAX_HEIGHT = 30000          # px; a longer page is cut there and the row says so
JPEG_QUALITY = 72


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(url):
    parts = urlsplit(url)
    host = parts.netloc.lower().removeprefix("www.")
    tail = re.sub(r"[^a-z0-9]+", "-", (parts.path + "-" + parts.query).lower()).strip("-")
    return re.sub(r"[^a-z0-9.]+", "-", host), (tail[:60].strip("-") or "home")


def _ledger(proj):
    p = Path(proj) / "sources" / "snapshots.json"
    return p, (json.loads(p.read_text()) if p.exists() else [])


def _save_ledger(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")


def _out_path(proj, url, ext):
    host, tail = _slug(url)
    d = Path(proj) / "sources" / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    stem = f"{datetime.now().strftime('%Y-%m-%d')}_{host}_{tail}"
    p, n = d / f"{stem}.{ext}", 2
    while p.exists():
        p, n = d / f"{stem}-{n}.{ext}", n + 1
    return p


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _head(url):
    """(status, final_url, content_type) without a browser, so a PDF is recognized and a
    dead link is reported before Chromium spends time on it."""
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.geturl(), r.headers.get("Content-Type", ""), r.read(64 * 1024 * 1024)
    except urllib.error.HTTPError as e:
        return e.code, url, e.headers.get("Content-Type", "") if e.headers else "", b""
    except (urllib.error.URLError, OSError) as e:
        return None, url, str(e), b""


def capture_html(url, out):
    from playwright.sync_api import sync_playwright
    from PIL import Image
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True,
                              args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, user_agent=UA,
                            locale="en-US")
        page = ctx.new_page()
        resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass                                 # busy pages never go idle; capture anyway
        # Scroll once to the bottom and back so lazy-loaded images render, as a reader saw it.
        page.evaluate("""async () => { for (let y = 0; y < document.body.scrollHeight;
            y += 800) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); }
            window.scrollTo(0, 0); }""")
        page.wait_for_timeout(800)
        status = resp.status if resp else None
        title = page.title()
        final = page.url
        text = page.inner_text("body")[:4000] if page.query_selector("body") else ""
        png = page.screenshot(full_page=True)
        b.close()
    img = Image.open(io.BytesIO(png)).convert("RGB")
    truncated = img.height > MAX_HEIGHT
    if truncated:
        img = img.crop((0, 0, img.width, MAX_HEIGHT))
    img.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
    walled = bool(WALL_HINTS.search(title) or (len(text) < 600 and WALL_HINTS.search(text)))
    return {"status": status, "final_url": final, "title": title,
            "height_px": img.height, "truncated": truncated, "walled": walled}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("project_dir")
    ap.add_argument("url", nargs="?")
    ap.add_argument("--claim", help="research-wiki claim_id this source supports")
    ap.add_argument("--import", dest="imported", help="record a screenshot/PDF captured by hand")
    ap.add_argument("--again", action="store_true", help="take another snapshot of a URL")
    ap.add_argument("--list", action="store_true", help="print this project's snapshots")
    a = ap.parse_args()

    proj = Path(a.project_dir)
    if not (proj / "project.json").exists():
        print(f"not a project dir: {proj}"); return 1
    ledger_path, rows = _ledger(proj)
    if a.list:
        for r in rows:
            print(f"{r['captured_at'][:10]}  {r.get('status')}  {r['url']}\n            {r['file']}")
        return 0
    if not a.url:
        print("need a URL (or --list)"); return 1

    have = [r for r in rows if r["url"] == a.url]
    if have and not a.again and not a.imported:
        print(json.dumps({"already": True, **have[-1]}, indent=2)); return 0

    row = {"url": a.url, "claim": a.claim, "captured_at": _now()}
    if a.imported:
        src = Path(a.imported)
        if not src.exists():
            print(f"no such file: {src}"); return 1
        out = _out_path(proj, a.url, src.suffix.lstrip(".").lower() or "png")
        shutil.copy2(src, out)
        row.update({"method": "import", "status": None, "final_url": a.url, "title": None})
    else:
        status, final, ctype, body = _head(a.url)
        # Python's own certificate check can fail on a live site (a missing local CA
        # bundle); that says nothing about the page, so let Chromium decide.
        cert_only = status is None and "CERTIFICATE_VERIFY_FAILED" in ctype
        if cert_only:
            ctype = ""
        if status in (404, 410) or (status is None and not cert_only):
            print(json.dumps({"dead": True, "url": a.url, "status": status,
                              "detail": ctype if status is None else None}, indent=2))
            return 4
        if "pdf" in ctype.lower() or (body[:5] == b"%PDF-"):
            out = _out_path(proj, a.url, "pdf")
            out.write_bytes(body)
            row.update({"method": "pdf", "status": status, "final_url": final, "title": None})
        else:
            out = _out_path(proj, a.url, "jpg")
            try:
                info = capture_html(a.url, out)
            except Exception as e:                         # noqa: BLE001
                print(json.dumps({"failed": True, "url": a.url, "error": str(e)[:400]}, indent=2))
                return 2
            row.update({"method": "chromium", **info})
            if info["walled"] or (info["status"] or 0) in (401, 403, 429):
                row["needs_browser"] = True
                rows.append({**row, "file": str(out.relative_to(proj)), "sha256": _sha(out)})
                _save_ledger(ledger_path, rows)
                print(json.dumps({"needs_browser": True, **row, "file": str(out.relative_to(proj)),
                                  "next": "the headless capture shows a wall or block. Open the "
                                          "page in Claude in Chrome, capture it full size, then "
                                          "re-run with --import <file>"}, indent=2))
                return 3
    row.update({"file": str(out.relative_to(proj)), "sha256": _sha(out),
                "bytes": out.stat().st_size})
    rows.append(row)
    _save_ledger(ledger_path, rows)
    print(json.dumps(row, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
