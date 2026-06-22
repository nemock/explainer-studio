"""PROMOTE — pick the next produced video + Short to re-share, and track what's
been promoted, in a global ledger.

Design (operator decision 2026-06-20):
  - A global ledger lives at <projects>/../promotions.json (source of truth) with
    a generated, human-readable PROMOTIONS.md beside it.
  - `promote select` is MECHANICAL: it scans every produced+published video that
    has cut Shorts, cross-references the ledger, and picks the next thing to push.
    Rotation rule: videos NEVER promoted come first, then least-recently-promoted;
    within the chosen video, the least-recently-posted Short. (One Short per run.)
  - It is fine to re-share a Short more than once — that's the point — but each
    re-share needs FRESH caption wording so it doesn't read as a duplicate. The
    selector returns the short's `prior_captions` as a do-not-repeat list.

This module is PURE PYTHON and makes NO LLM calls and NO network calls (PRD §5:
the media/CLI plane never calls an LLM, and the generation-only boundary). The
two steps that aren't mechanical happen OUTSIDE it:
  1. Caption rewording — done by Claude (the operator's subscription), because it
     needs an LLM. The selector hands Claude the do-not-repeat list.
  2. The actual Blotato post — see SKILL/promote flow. `promote log` records it
     afterward so the rotation advances.
"""
import json
import re
import time
from pathlib import Path

# The Shorts platforms we promote across (Blotato account set, per memory).
DEFAULT_PLATFORMS = ["twitter", "bluesky", "threads", "youtube", "instagram", "facebook"]

_YT = re.compile(r"https?://(?:youtu\.be/|www\.youtube\.com/(?:watch\?v=|shorts/))[\w\-]+")
_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def _projects_dir(projects_dir):
    return Path(projects_dir).resolve()


def ledger_path(projects_dir):
    # Global ledger sits beside the projects/ dir (i.e. in explainer-content/).
    return _projects_dir(projects_dir).parent / "promotions.json"


def load_ledger(projects_dir):
    p = ledger_path(projects_dir)
    if p.exists():
        return json.loads(p.read_text())
    return {"schema": "promotions/1", "promotions": []}


def save_ledger(projects_dir, ledger):
    ledger_path(projects_dir).write_text(json.dumps(ledger, indent=2, ensure_ascii=False))


def _resolve_url(proj):
    """Find the published video URL: meta.youtube_url first, then any youtu.be /
    youtube.com link in meta.json or PLAYBOOK.md. None if not published."""
    meta = proj / "package" / "meta.json"
    if meta.exists():
        try:
            data = json.loads(meta.read_text())
        except json.JSONDecodeError:
            data = {}
        if data.get("youtube_url"):
            return data["youtube_url"]
        m = _YT.search(json.dumps(data))
        if m:
            return m.group(0)
    pb = proj / "PLAYBOOK.md"
    if pb.exists():
        m = _YT.search(pb.read_text())
        if m:
            return m.group(0)
    return None


def _shorts_of(proj):
    """Cut Shorts of a video: dirs under shorts/ with a final 9:16 mp4. Returns
    [{slug, title, mp4}] ordered by plan.json when present, else dir name."""
    sdir = proj / "shorts"
    if not sdir.is_dir():
        return []
    titles = {}
    plan = sdir / "plan.json"
    if plan.exists():
        try:
            for c in json.loads(plan.read_text()):
                titles[c.get("slug")] = c.get("title")
        except json.JSONDecodeError:
            pass
    order = list(titles) if titles else None
    found = {}
    for d in sdir.iterdir():
        if not d.is_dir():
            continue
        mp4 = d / "video" / "explainer_9x16.mp4"
        if mp4.exists():
            found[d.name] = {"slug": d.name, "title": titles.get(d.name, d.name),
                             "mp4": str(mp4)}
    if order:
        return [found[s] for s in order if s in found] + \
               [v for k, v in found.items() if k not in order]
    return [found[k] for k in sorted(found)]


def discover(projects_dir):
    """Every video folder, with its url + cut shorts. promotable = url AND shorts."""
    vids = []
    for d in sorted(_projects_dir(projects_dir).iterdir()):
        if not d.is_dir() or not _DATE.match(d.name):
            continue
        url = _resolve_url(d)
        shorts = _shorts_of(d)
        title = ""
        meta = d / "package" / "meta.json"
        pj = d / "project.json"
        for src in (meta, pj):
            if src.exists():
                try:
                    title = json.loads(src.read_text()).get("title", "") or title
                except json.JSONDecodeError:
                    pass
                if title:
                    break
        vids.append({"slug": d.name, "date": _DATE.match(d.name).group(1),
                     "title": title, "url": url, "shorts": shorts,
                     "promotable": bool(url and shorts)})
    return vids


def _history(ledger):
    """Per (video) and (video, short) → list of promotion records, plus captions."""
    by_video, by_short = {}, {}
    for p in ledger["promotions"]:
        by_video.setdefault(p["video_slug"], []).append(p)
        by_short.setdefault((p["video_slug"], p["short_slug"]), []).append(p)
    return by_video, by_short


def select(projects_dir, video=None, short=None):
    ledger = load_ledger(projects_dir)
    by_video, by_short = _history(ledger)
    vids = {v["slug"]: v for v in discover(projects_dir)}
    promotable = [v for v in vids.values() if v["promotable"]]
    if not promotable:
        return {"error": "no promotable videos (need a resolvable URL + cut shorts)"}

    def last_promoted(slug):
        recs = by_video.get(slug, [])
        return max((r["promoted_at"] for r in recs), default=None)

    if video:
        if video not in vids:
            return {"error": f"unknown video {video!r}"}
        chosen = vids[video]
        if not chosen["promotable"]:
            return {"error": f"{video} is not promotable (missing url or shorts)"}
    else:
        # never-promoted first (last is None), then least-recently-promoted; oldest first.
        chosen = sorted(promotable,
                        key=lambda v: (last_promoted(v["slug"]) is not None,
                                       last_promoted(v["slug"]) or "",
                                       v["date"]))[0]

    shorts = chosen["shorts"]
    if short:
        pick = next((s for s in shorts if s["slug"] == short), None)
        if not pick:
            return {"error": f"short {short!r} not found in {chosen['slug']}"}
    else:
        def last_posted(sl):
            recs = by_short.get((chosen["slug"], sl), [])
            return max((r["promoted_at"] for r in recs), default=None)
        pick = sorted(shorts, key=lambda s: (last_posted(s["slug"]) is not None,
                                             last_posted(s["slug"]) or ""))[0]

    short_recs = by_short.get((chosen["slug"], pick["slug"]), [])
    return {
        "video_slug": chosen["slug"],
        "video_title": chosen["title"],
        "video_url": chosen["url"],
        "short_slug": pick["slug"],
        "short_title": pick["title"],
        "short_mp4": pick["mp4"],
        "platforms": DEFAULT_PLATFORMS,
        "scheduling": "next_free_slot",
        "url_comment": chosen["url"],
        "times_video_promoted": len(by_video.get(chosen["slug"], [])),
        "times_short_promoted": len(short_recs),
        "prior_captions": [r.get("caption") for r in short_recs if r.get("caption")],
        "note": "Reword the caption so it differs from prior_captions; keep the URL "
                "as a reply-comment on X/Threads/Bluesky and in the YT description.",
    }


def log(projects_dir, record):
    """Append a promotion record and regenerate PROMOTIONS.md.
    Required keys: video_slug, short_slug. Recommended: platforms, caption,
    url_comment, scheduled_time, blotato_post_ids."""
    for k in ("video_slug", "short_slug"):
        if not record.get(k):
            raise ValueError(f"record missing required key {k!r}")
    record.setdefault("promoted_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
    ledger = load_ledger(projects_dir)
    ledger["promotions"].append(record)
    save_ledger(projects_dir, ledger)
    write_markdown(projects_dir, ledger)
    return {"logged": record, "total_promotions": len(ledger["promotions"]),
            "ledger": str(ledger_path(projects_dir))}


def status(projects_dir):
    ledger = load_ledger(projects_dir)
    by_video, by_short = _history(ledger)
    rows = []
    for v in discover(projects_dir):
        recs = by_video.get(v["slug"], [])
        rows.append({"slug": v["slug"], "promotable": v["promotable"],
                     "has_url": bool(v["url"]), "shorts": len(v["shorts"]),
                     "times_promoted": len(recs),
                     "last_promoted": max((r["promoted_at"] for r in recs), default=None)})
    nxt = select(projects_dir)
    return {"videos": rows, "total_promotions": len(ledger["promotions"]),
            "next_up": None if "error" in nxt else
                       {"video": nxt["video_slug"], "short": nxt["short_slug"]}}


def write_markdown(projects_dir, ledger=None):
    ledger = ledger or load_ledger(projects_dir)
    by_video, by_short = _history(ledger)
    lines = ["# Promotions ledger",
             "",
             f"_Generated from promotions.json — {len(ledger['promotions'])} promotions total. "
             "Do not edit by hand._",
             "",
             "| Video | Shorts | Times promoted | Last promoted |",
             "|---|---|---|---|"]
    for v in discover(projects_dir):
        recs = by_video.get(v["slug"], [])
        last = max((r["promoted_at"] for r in recs), default="—")
        mark = "" if v["promotable"] else " _(not promotable)_"
        lines.append(f"| {v['slug']}{mark} | {len(v['shorts'])} | {len(recs)} | {last} |")
    lines += ["", "## Recent promotions", ""]
    for p in sorted(ledger["promotions"], key=lambda r: r.get("promoted_at", ""), reverse=True)[:30]:
        plats = ",".join(p.get("platforms", []))
        lines.append(f"- {p.get('promoted_at','?')} — **{p['video_slug']}** / "
                     f"{p['short_slug']} → {plats}")
    out = _projects_dir(projects_dir).parent / "PROMOTIONS.md"
    out.write_text("\n".join(lines) + "\n")
    return str(out)


# --- Direct Blotato posting (operator chose "CLI posts directly", 2026-06-20) ---
# This is a NETWORK call, not an LLM call — fine in the CLI. Caption wording is
# still a Claude generation step (it lands in the plan we post). The Blotato key
# is read from env BLOTATO_API_KEY, falling back to the MCP config (the key you
# already have); it is never written into the repo.

API_BASE = "https://backend.blotato.com/v2"

# Connected Blotato account IDs (Dave's channels, per memory 2026-06-19). Verify
# with the Blotato MCP `list_accounts` if posts 401 — IDs can change. A plan may
# override any of these per platform via {"account_id": "..."}.
DEFAULT_ACCOUNTS = {
    "twitter": "16563", "bluesky": "46447", "threads": "6021",
    "instagram": "41992", "youtube": "34001", "facebook": "37963",
}
# Facebook posts to a Page, not the profile: Blotato requires the Page's id
# (a subaccount of account 37963) on the post target. "Founders Who Finish" Page,
# connected 2026-06-22. Verify with the Blotato MCP `list_accounts` if posts 400.
DEFAULT_FACEBOOK_PAGE_ID = "1216556091535160"
# Platforms that support a threaded reply (used to attach the clickable URL).
THREAD_REPLY = {"twitter", "bluesky", "threads"}


def _api_key():
    import os
    k = os.environ.get("BLOTATO_API_KEY")
    if k:
        return k
    cfg_path = Path.home() / ".claude.json"
    if cfg_path.exists():
        def find(o):
            if isinstance(o, dict):
                for kk, vv in o.items():
                    if kk.lower() == "blotato-api-key" and isinstance(vv, str):
                        return vv
                    r = find(vv)
                    if r:
                        return r
            return None
        k = find(json.loads(cfg_path.read_text()))
        if k:
            return k
    raise RuntimeError("no Blotato API key (set BLOTATO_API_KEY or configure the blotato MCP)")


def _http(method, path, body=None, headers=None):
    import urllib.request
    url = path if path.startswith("http") else f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    h = {"blotato-api-key": _api_key(), "Content-Type": "application/json",
         "Accept": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read().decode("utf-8", "replace")
        return r.status, (json.loads(raw) if raw.strip() else {})


def upload_media(local_path):
    """Presigned upload of a local file → returns the public Blotato media URL."""
    import urllib.request
    fn = Path(local_path).name
    _, pres = _http("POST", "/media/uploads", {"filename": fn})
    put = urllib.request.Request(pres["presignedUrl"], data=Path(local_path).read_bytes(),
                                 method="PUT", headers={"Content-Type": "application/octet-stream"})
    urllib.request.urlopen(put, timeout=600)
    return pres["publicUrl"]


def _build_post_body(entry, media_urls, scheduled):
    """Construct the POST /v2/posts body for one platform entry.
    entry: {platform, account_id?, caption, url_comment?, extra?{...}}."""
    platform = entry["platform"]
    content = {"text": entry["caption"], "mediaUrls": media_urls, "platform": platform}
    if entry.get("url_comment") and platform in THREAD_REPLY:
        content["additionalPosts"] = [{"text": entry["url_comment"], "mediaUrls": []}]
    target = {"targetType": platform}
    # platform-specific fields. Blotato wants routing/required metadata on target
    # (YouTube's title/privacyStatus/…; Facebook's pageId) and content attributes
    # on content (e.g. mediaType=reel for IG and FB).
    extra = dict(entry.get("extra", {}))
    if platform == "youtube":
        target.update(extra)
    elif platform == "facebook":
        page = extra.pop("pageId", None) or DEFAULT_FACEBOOK_PAGE_ID
        if page:
            target["pageId"] = page
        content.update(extra)  # e.g. mediaType=reel
    else:
        content.update(extra)
    body = {"post": {"accountId": entry.get("account_id") or DEFAULT_ACCOUNTS.get(platform),
                     "content": content, "target": target}}
    if scheduled == "next_free_slot":
        body["post"]["useNextFreeSlot"] = True
    elif scheduled:
        body["scheduledTime"] = scheduled
    return body


def post_plan(projects_dir, plan, dry_run=True):
    """Fire a promotion plan. plan = {video_slug, short_slug, video_url, short_mp4,
    scheduled, posts:[{platform, caption, url_comment?, account_id?, extra?}]}.
    Uploads the mp4 once, reuses the URL across platforms, creates each post, and
    logs every successful platform to the ledger. dry_run prints payloads only."""
    scheduled = plan.get("scheduled", "next_free_slot")
    results = []
    media_urls = []
    if not dry_run:
        media_urls = [upload_media(plan["short_mp4"])]
    else:
        media_urls = ["<uploaded at fire time>"]
    for entry in plan["posts"]:
        body = _build_post_body(entry, media_urls, scheduled)
        if dry_run:
            results.append({"platform": entry["platform"], "dry_run": True, "body": body})
            continue
        try:
            status, resp = _http("POST", "/posts", body)
            pid = resp.get("postSubmissionId") or resp.get("id")
            results.append({"platform": entry["platform"], "status": status,
                            "post_submission_id": pid})
            log(projects_dir, {
                "video_slug": plan["video_slug"], "short_slug": plan["short_slug"],
                "video_url": plan.get("video_url"), "platforms": [entry["platform"]],
                "caption": entry["caption"], "url_comment": entry.get("url_comment"),
                "scheduled_time": scheduled, "blotato_post_ids": {entry["platform"]: pid},
            })
        except Exception as e:
            results.append({"platform": entry["platform"], "error": f"{type(e).__name__}: {e}"})
    return {"dry_run": dry_run, "results": results}


def run(projects_dir, action, video=None, short=None, record=None, plan=None, fire=False):
    if action == "select":
        return select(projects_dir, video=video, short=short)
    if action == "status":
        return status(projects_dir)
    if action == "log":
        if not record:
            raise ValueError("log needs --record <json file>")
        rec = json.loads(Path(record).read_text())
        return log(projects_dir, rec)
    if action == "report":
        return {"markdown": write_markdown(projects_dir)}
    if action == "post":
        if not plan:
            raise ValueError("post needs --plan <json file>")
        return post_plan(projects_dir, json.loads(Path(plan).read_text()), dry_run=not fire)
    raise ValueError(f"unknown action {action!r}")
