#!/usr/bin/env python3
"""substack_curl_drafts.py — curl the quotes and apostrophes in drafts already on Substack.

Operator request 2026-11-14: drafts posted before `substack` learned to curl (commit ce8a341)
went up with straight quotes and apostrophes, and fixing them by hand in the editor is slow.
This reads each draft as it is NOW on Substack, so any edits the operator made in the editor
are kept, curls only the text with substack.curl_tree (code and bare-URL links stay literal,
link hrefs are never touched), and writes the body back. Title and subtitle are curled too.
It never publishes.

  ~/myenv/bin/python3.12 tools/substack_curl_drafts.py                 # dry run: what would change
  ~/myenv/bin/python3.12 tools/substack_curl_drafts.py --fire          # write the changed drafts
  ... --skip-title "Microsoft"   # leave out a draft the operator has open (repeatable)
  ... --only 224816805           # just one draft id (repeatable)

Before any write, the draft as read is saved to
explainer-content/channel/substack_backups/<date>/<id>.json, so a bad write can be undone.
A draft whose text is already curly is not touched.
"""
import argparse
import copy
import json
import sys
import time
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from explainer2 import substack  # noqa: E402

BACKUPS = REPO / "channel" / "substack_backups"
STRAIGHT = ("'", '"')


def _body(d):
    b = d.get("draft_body") or d.get("body")
    if isinstance(b, str):
        try:
            b = json.loads(b)
        except ValueError:
            return None
    return b if isinstance(b, dict) else None


def _texts(nodes, out):
    for n in nodes or []:
        if n.get("type") == "text" and not substack._is_literal(n):
            out.append(n.get("text") or "")
        elif n.get("type") != "code_block":
            _texts(n.get("content"), out)
    return out


def _straight_count(body, title, subtitle):
    joined = "".join(_texts(body.get("content"), [])) + (title or "") + (subtitle or "")
    return sum(joined.count(c) for c in STRAIGHT)


def _drafts(sub):
    out, offset = [], 0
    while True:
        page = sub.call("list_posts", status="drafts", limit=50, offset=offset)
        posts = page.get("posts") if isinstance(page, dict) else page
        posts = posts or []
        out.extend(posts)
        if len(posts) < 50:
            return out
        offset += 50
        time.sleep(2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--fire", action="store_true", help="write the changes (default: dry run)")
    ap.add_argument("--skip-title", action="append", default=[],
                    help="skip drafts whose title contains this text (case-insensitive)")
    ap.add_argument("--only", action="append", type=int, default=[], help="just these draft ids")
    a = ap.parse_args()

    report = {"fire": a.fire, "changed": [], "unchanged": [], "skipped": [], "failed": []}
    backup_dir = BACKUPS / date.today().isoformat()
    with substack.SubstackMcp() as sub:
        drafts = _drafts(sub)
        for p in drafts:
            pid = p.get("id")
            title = p.get("draft_title") or p.get("title") or ""
            if a.only and pid not in a.only:
                continue
            if any(s.lower() in title.lower() for s in a.skip_title):
                report["skipped"].append({"id": pid, "title": title})
                continue
            time.sleep(2)
            try:
                d = sub.call("get_draft", draft_id=pid)
            except substack.McpError as e:
                report["failed"].append({"id": pid, "title": title, "error": str(e)[:300]})
                continue
            body = _body(d)
            if body is None:
                report["failed"].append({"id": pid, "title": title, "error": "no readable body"})
                continue
            old_t, old_s = d.get("draft_title") or "", d.get("draft_subtitle") or ""
            before = _straight_count(body, old_t, old_s)
            if before == 0:
                report["unchanged"].append({"id": pid, "title": title})
                continue
            new_body = substack.curl_tree([copy.deepcopy(body)])[0]
            new_t, new_s = substack.curl(old_t)[0], substack.curl(old_s)[0]
            after = _straight_count(new_body, new_t, new_s)
            row = {"id": pid, "title": title, "straight_marks": before, "left_after": after}
            if not a.fire:
                report["changed"].append(row)
                continue
            backup_dir.mkdir(parents=True, exist_ok=True)
            (backup_dir / f"{pid}.json").write_text(json.dumps(d, indent=2, ensure_ascii=False))
            try:
                time.sleep(2)
                sub.call("set_post_body", draft_id=pid, body=new_body)
                if (new_t, new_s) != (old_t, old_s):
                    time.sleep(2)
                    sub.call("update_draft", draft_id=pid, draft_title=new_t,
                             draft_subtitle=new_s)
                time.sleep(2)
                back = sub.call("get_draft", draft_id=pid)
                rb = _body(back)
                row["left_after"] = (_straight_count(rb, back.get("draft_title"),
                                                     back.get("draft_subtitle"))
                                     if rb else "unreadable")
                report["changed"].append(row)
            except substack.McpError as e:
                row["error"] = str(e)[:400]
                report["failed"].append(row)
    report["counts"] = {k: len(v) for k, v in report.items() if isinstance(v, list)}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
