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
            data = json.loads(plan.read_text())
            # plan.json is either a bare list of cuts (legacy) or {schema, cuts:[...]}
            cuts = data.get("cuts", []) if isinstance(data, dict) else data
            for c in cuts:
                if isinstance(c, dict):
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
        "short_duration_s": probe_duration(pick["mp4"]),
        "note": "Reword the caption so it differs from prior_captions; keep the URL "
                "as a reply-comment on X/Threads and in the YT description. Bluesky is "
                "LINK-ONLY (no video) and Twitter drops to link-only over "
                f"{TWITTER_VIDEO_MAX_S}s — `promote post` applies both automatically, so "
                "write those captions to read well with the URL inlined at the end.",
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

# Blotato account and Page ids deliberately do NOT live in this file. The post queue's
# routing table owns them and this module reads it. Keeping a local copy is what went
# wrong: the Bluesky connection was remade on 2026-08-19 and its id changed 46447 ->
# 74904, the table was updated, this dict was not, and every Bluesky post it built would
# have been held with "No Bluesky account connected" (fixed 2026-08-26). A plan entry can
# still override one platform via {"account_id": "..."} — see post-direct in run().
TARGETS = "/Volumes/Casima/claudeCode/make_money/post_queue/targets.json"
# Everything explainer2 promotes goes out as Founders Who Finish, so a row for this brand
# wins over the platform's generic "any" row. That is how Facebook picks up its Page id
# (the "Founders Who Finish" Page — Meta's API cannot post to a personal profile).
BRAND = "fwf"
# Platforms that support a threaded reply (used to attach the clickable URL).
THREAD_REPLY = {"twitter", "bluesky", "threads"}
# Platforms we NEVER attach video to — the link goes in the post body instead.
# Bluesky's Blotato video path failed 21 times between 2026-05 and 2026-08 (100s
# upload timeouts, Conflict, Bad Gateway). It is a Blotato-side problem we can't
# fix from here, and every failure was silent, so we stopped attempting it
# (operator decision 2026-08-03).
LINK_ONLY = {"bluesky"}
# X/Twitter free-account native-video cap on this account. Over this, the Short
# is replaced by a text post carrying the video URL.
TWITTER_VIDEO_MAX_S = 120


def _routing(platform):
    """The queue's routing row for one platform — {account_id, page_id, ...} — or {}.

    Read fresh on every call. A cached or copied value is precisely the thing that went
    stale, and the table is a few KB."""
    try:
        rows = json.loads(Path(TARGETS).read_text())
    except Exception as e:
        raise RuntimeError(f"cannot read the post-queue routing table at {TARGETS} "
                           f"({type(e).__name__}: {e}) — it owns every Blotato account id")
    hit = {}
    for want in ("any", BRAND):
        for r in rows:
            if r.get("brand") == want and r.get("platform") == platform:
                hit = r
    return hit


def probe_duration(path):
    """Video length in seconds via ffprobe, or None if unreadable."""
    import subprocess
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        return float(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else None
    except (ValueError, OSError, subprocess.SubprocessError):
        return None


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


def _build_post_body(entry, media_urls, scheduled, duration_s=None):
    """Construct the POST /v2/posts body for one platform entry.
    entry: {platform, account_id?, caption, url_comment?, extra?{...}}.

    LINK FALLBACK: platforms in LINK_ONLY, and Twitter when the Short runs past
    TWITTER_VIDEO_MAX_S, get NO media — the video URL is inlined in the post body
    instead. Both used to be left to the operator/LLM to notice, which meant they
    never happened: Blotato accepts the post and the platform rejects it minutes
    later, after the run has ended."""
    platform = entry["platform"]
    route = _routing(platform)
    link_only = platform in LINK_ONLY or (
        platform == "twitter" and duration_s is not None and duration_s > TWITTER_VIDEO_MAX_S
    )
    text = entry["caption"]
    if link_only:
        url = entry.get("url_comment") or ""
        if url and url not in text:
            text = f"{text}\n\n{url}" if text else url
    content = {"text": text,
               "mediaUrls": [] if link_only else media_urls,
               "platform": platform}
    if not link_only and entry.get("url_comment") and platform in THREAD_REPLY:
        content["additionalPosts"] = [{"text": entry["url_comment"], "mediaUrls": []}]
    target = {"targetType": platform}
    # platform-specific fields. Blotato wants routing/required metadata on target
    # (YouTube's title/privacyStatus/…; Facebook's pageId) and content attributes
    # on content (e.g. mediaType=reel for IG and FB).
    extra = dict(entry.get("extra", {}))
    if platform == "youtube":
        target.update(extra)
    elif platform == "facebook":
        page = extra.pop("pageId", None) or route.get("page_id")
        if page:
            target["pageId"] = page
        content.update(extra)  # e.g. mediaType=reel
    else:
        content.update(extra)
    account = entry.get("account_id") or route.get("account_id")
    if not account:
        raise RuntimeError(f"no Blotato account for {platform!r}: {TARGETS} has no row for "
                           f"brand {BRAND!r} or 'any', and the plan set no account_id")
    body = {"post": {"accountId": account, "content": content, "target": target}}
    if scheduled == "next_free_slot":
        body["post"]["useNextFreeSlot"] = True
    elif scheduled:
        body["scheduledTime"] = scheduled
    return body


POSTQ = "/Volumes/Casima/claudeCode/make_money/post_queue/postq.py"


def enqueue_plan(projects_dir, plan, dry_run=True):
    """Hand a promotion plan to the LOCAL post queue instead of posting it.

    Blotato stopped being the system of record on 2026-08-08 — its 200-post workspace cap
    is shared across every brand and repeatedly cost whole fan-outs. The local queue owns
    the schedule now and tops Blotato up a few hours at a time. See
    make_money/post_queue/ENQUEUE.md.

    This does NOT upload, schedule, or post. It writes a spec and makes one call; the
    dispatcher uploads from media_local and places each post, and reconcile records the
    live URLs. Link-only and over-length handling stay declarative here, exactly as
    _build_post_body computed them, so nothing about the caption rules changes."""
    import subprocess, tempfile

    duration_s = probe_duration(plan["short_mp4"])
    posts = []
    for entry in plan["posts"]:
        platform = entry["platform"]
        link_only = platform in LINK_ONLY or (
            platform == "twitter" and duration_s is not None and duration_s > TWITTER_VIDEO_MAX_S
        )
        post = {"platform": platform, "text": entry["caption"]}
        if link_only:
            url = entry.get("url_comment") or ""
            if url and url not in post["text"]:
                post["text"] = f"{post['text']}\n\n{url}" if post["text"] else url
        else:
            post["media_local"] = [plan["short_mp4"]]
            if entry.get("url_comment") and platform in THREAD_REPLY:
                post["additional_posts"] = [{"text": entry["url_comment"], "mediaUrls": []}]
        extra = dict(entry.get("extra", {}))
        extra.pop("pageId", None)      # resolved from brand by the queue
        if extra:
            post["target"] = extra
        # YouTube needs no route override: the queue's default for this account is
        # `youtube_direct`, which the dispatcher now implements. Direct is preferred over
        # the transport regardless of length — it returns the watch URL immediately, which
        # is what the X link fallback and the link-only Bluesky post are waiting on.
        posts.append(post)

    spec = {"routine": "explainer2-promote-daily",
            "episode": plan.get("short_slug") or plan.get("video_slug"),
            "source_asset": plan["short_mp4"],
            "posts": posts}

    if dry_run:
        return {"dry_run": True, "spec": spec, "duration_s": duration_s}

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(spec, fh)
        spec_path = fh.name
    out = subprocess.run(["python3", POSTQ, "enqueue", "--spec", spec_path],
                         capture_output=True, text=True)
    ok = out.returncode == 0
    if ok:
        log(projects_dir, {
            "video_slug": plan["video_slug"], "short_slug": plan["short_slug"],
            "video_url": plan.get("video_url"),
            "platforms": [e["platform"] for e in plan["posts"]],
            "caption": plan["posts"][0]["caption"] if plan["posts"] else "",
            "scheduled_time": "local-queue", "blotato_post_ids": {},
        })
    return {"enqueued": ok, "stdout": out.stdout, "stderr": out.stderr, "spec": spec}


def post_plan(projects_dir, plan, dry_run=True):
    """Fire a promotion plan. plan = {video_slug, short_slug, video_url, short_mp4,
    scheduled, posts:[{platform, caption, url_comment?, account_id?, extra?}]}.
    Uploads the mp4 once, reuses the URL across platforms, creates each post, and
    logs every successful platform to the ledger. dry_run prints payloads only."""
    scheduled = plan.get("scheduled", "next_free_slot")
    results = []
    media_urls = []
    duration_s = probe_duration(plan["short_mp4"])
    if not dry_run:
        media_urls = [upload_media(plan["short_mp4"])]
    else:
        media_urls = ["<uploaded at fire time>"]
    for entry in plan["posts"]:
        body = _build_post_body(entry, media_urls, scheduled, duration_s)
        if dry_run:
            results.append({"platform": entry["platform"], "dry_run": True,
                            "link_only": body["post"]["content"]["mediaUrls"] == [],
                            "duration_s": duration_s, "body": body})
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
        # Since the 2026-08-08 cutover this hands the plan to the local queue rather than
        # posting to Blotato directly. post_plan() is kept for manual/emergency use.
        return enqueue_plan(projects_dir, json.loads(Path(plan).read_text()), dry_run=not fire)
    if action == "post-direct":
        if not plan:
            raise ValueError("post-direct needs --plan <json file>")
        return post_plan(projects_dir, json.loads(Path(plan).read_text()), dry_run=not fire)
    raise ValueError(f"unknown action {action!r}")
