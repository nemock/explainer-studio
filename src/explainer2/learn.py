"""Learn — the channel performance feedback loop (PRD Phase 5, final piece).

Data lives in channel/learn/ — a symlink into the PRIVATE explainer-content
repo, so analytics never land in the public explainer-studio repo.

  performance.json  one entry per published deep dive:
      {video_id: {slug, title, url, posted, duration_s, features: {...},
                  snapshots: [{date, source, views, ...}]}}
  REPORT.md         the digest the blueprint playbook reads before ranking
                    titles and thumbnails.

Verbs (wired in cli.py):
  refresh        yt-dlp public stats (views/likes/comments) for every project
                 whose package/meta.json has youtube_url + posted. No auth,
                 runs unattended.
  ingest --csv   a YouTube Studio "Content" export adds the private metrics
                 (impressions, CTR, avg view duration, watch hours, subs)
                 that yt-dlp cannot see. Operator downloads the CSV by hand —
                 no API, no SaaS (PRD hard constraint).
  retention      the share of viewers still watching at 0:30 and 1:00, from the YouTube
                 Analytics audience-retention curve, on the channel token `publish`
                 already holds (2026-11-27; script-playbook §4.1's 30-second contract).
  articles       Substack stats for every published post (views, opens, signups, restacks)
                 into articles.json, tied to videos by meta.json's substack_post_id.
  shorts         reach and engagement of every `promote` re-share, per platform, into
                 shorts.json: Blotato's post analytics, YouTube's Data API for the direct
                 Shorts uploads (2026-11-27).
  report         rewrite REPORT.md from the latest snapshots.

One snapshot per (date, source) — re-running a verb the same day updates in
place instead of appending duplicates.
"""
import csv
import json
import re
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path

from .intel.ytfetch import _ytdlp_json

REPO = Path(__file__).resolve().parents[2]
LEARN_DIR = REPO / "channel" / "learn"
PERF = LEARN_DIR / "performance.json"
REPORT = LEARN_DIR / "REPORT.md"

MIN_AGE_DAYS = 3          # younger videos are flagged, not compared
BREAKOUT = 1.5            # x channel median views/day
LAGGARD = 0.5


# ---------------- discovery ----------------

def _video_id(url):
    m = re.search(r"(?:youtu\.be/|watch\?v=|/shorts/)([A-Za-z0-9_-]{11})", url or "")
    return m.group(1) if m else None


def _dur_s(text):
    """'9:32' or '1:02:07' → seconds."""
    if not text:
        return None
    parts = [int(p) for p in str(text).split(":")]
    s = 0
    for p in parts:
        s = s * 60 + p
    return s


def title_features(title):
    """Deterministic title features for the what-works aggregates. No LLM."""
    t = title or ""
    low = t.lower()
    return {
        "words": len(t.split()),
        "question": "?" in t,
        "number": bool(re.search(r"\d", t)),
        "second_person": bool(re.search(r"\byou(r|'re)?\b", low)),
        "negation": bool(re.search(r"\b(not|never|stop|don't|wrong|no)\b", low)),
        "two_part": bool(re.search(r"[.?!:—]\s+\S", t.rstrip(".?!"))),
        "first_person": bool(re.search(r"\b(i|my|i'm|i've)\b", low)),
    }


def discover(projects_dir):
    """Published deep dives from projects/*/package/meta.json. `posted` is
    often missing on older close-outs — refresh backfills it from yt-dlp's
    upload_date, so a youtube_url alone is enough here."""
    out = []
    for mf in sorted(Path(projects_dir).glob("*/package/meta.json")):
        try:
            meta = json.loads(mf.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        vid = _video_id(meta.get("youtube_url"))
        if not vid:
            continue
        try:
            pj = json.loads((mf.parents[1] / "project.json").read_text())
        except (OSError, json.JSONDecodeError):
            pj = {}
        out.append({
            "channel": (pj.get("youtube_channel") or "nemock").lstrip("@"),
            "video_id": vid,
            "slug": mf.parents[1].name,
            "title": meta.get("title", ""),
            "url": meta["youtube_url"],
            "posted": meta.get("posted"),
            "duration_s": _dur_s(meta.get("duration")),
            "ab_test": bool(meta.get("ab_test")),
        })
    return out


# ---------------- store ----------------

def load_perf():
    if PERF.exists():
        return json.loads(PERF.read_text())
    return {}


def save_perf(perf):
    LEARN_DIR.mkdir(parents=True, exist_ok=True)
    PERF.write_text(json.dumps(perf, indent=2))


def _upsert_snapshot(entry, snap):
    """One snapshot per (date, source): same-day re-runs update in place."""
    snaps = entry.setdefault("snapshots", [])
    for i, s in enumerate(snaps):
        if s.get("date") == snap["date"] and s.get("source") == snap["source"]:
            snaps[i] = snap
            return
    snaps.append(snap)
    snaps.sort(key=lambda s: (s.get("date", ""), s.get("source", "")))


def _sync_entry(perf, v):
    e = perf.setdefault(v["video_id"], {})
    for k in ("slug", "title", "url", "ab_test", "channel"):
        e[k] = v.get(k)
    # Don't clobber a backfilled value with None. meta.json rarely carries a duration, so
    # this used to wipe the one refresh fetched from YouTube, and only refresh's own
    # backfill hid it; `learn retention` (2026-11-27) found it, 33 videos with no duration.
    for k in ("posted", "duration_s"):
        if v.get(k):
            e[k] = v[k]
    e["features"] = title_features(v["title"])
    return e


# ---------------- refresh (yt-dlp public stats) ----------------

def refresh(projects_dir):
    vids = discover(projects_dir)
    if not vids:
        print("no published videos found (meta.json needs youtube_url + posted)")
        return 1
    perf = load_perf()
    today = date.today().isoformat()
    ok = fail = 0
    for v in vids:
        e = _sync_entry(perf, v)
        data = _ytdlp_json(["--skip-download", v["url"]])
        if not data:
            fail += 1
            print(f"  ! {v['slug']}: yt-dlp fetch failed")
            continue
        if not e.get("posted") and data.get("upload_date"):
            ud = str(data["upload_date"])          # YYYYMMDD from yt-dlp
            e["posted"] = f"{ud[:4]}-{ud[4:6]}-{ud[6:8]}"
        if not e.get("duration_s") and data.get("duration"):
            e["duration_s"] = int(data["duration"])
        _upsert_snapshot(e, {
            "date": today, "source": "ytdlp",
            "views": data.get("view_count"),
            "likes": data.get("like_count"),
            "comments": data.get("comment_count"),
        })
        ok += 1
        print(f"  {v['slug']}: {data.get('view_count', '?')} views")
    save_perf(perf)
    print(f"refresh: {ok} snapshotted, {fail} failed → {PERF}")
    return 0 if ok else 1


# ---------------- retention (YouTube Analytics API, 2026-11-27) ----------------
#
# The first-minute check. Across nine deep dives 25-50% of viewers had left by ~0:30, and
# script-playbook §4.1's 30-second contract ends: "the learn loop's 30 s / 60 s watch
# ratio is how we find out whether it worked". yt-dlp and the Studio CSV can't see a
# retention curve; the Analytics API can, on the token `publish` already holds.

RET_POINTS = (30, 60)          # seconds into the video
CONTRACT_DATE = "2026-11-27"   # script-playbook §4.1 landed; later uploads were written to it
RET_MIN_VIEWS = 100            # below this a retention point is noise; reported, but flagged


def _watch_ratio_at(curve, t_s, duration_s):
    """Share of viewers still watching `t_s` seconds in, from an Analytics curve
    [(elapsedVideoTimeRatio, audienceWatchRatio), ...] (ratios in 0.01 steps). Linear
    interpolation between the two buckets around t/duration. None when the video is shorter
    than t, or the curve doesn't reach that far."""
    if not curve or not duration_s or t_s >= duration_s:
        return None
    x = t_s / duration_s
    pts = sorted(curve)
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return None


def _fetch_curve(ya, vid, start):
    r = ya.reports().query(ids="channel==MINE", startDate=start, endDate=date.today().isoformat(),
                           dimensions="elapsedVideoTimeRatio", filters=f"video=={vid}",
                           metrics="audienceWatchRatio").execute()
    return [(float(a), float(b)) for a, b in r.get("rows") or []]


def retention(projects_dir, fetch=None):
    """Snapshot the 0:30 and 1:00 watch ratio for every published deep dive.
    `fetch(channel, video_id, start_date) -> curve` is injectable for tests."""
    vids = discover(projects_dir)
    if not vids:
        print("no published videos found")
        return 1
    perf = load_perf()
    today = date.today().isoformat()
    clients = {}

    def default_fetch(channel, vid, start):
        if channel not in clients:
            from .publish import analytics_service
            clients[channel] = analytics_service(channel)
        return _fetch_curve(clients[channel], vid, start)

    fetch = fetch or default_fetch
    ok = empty = fail = 0
    for v in vids:
        e = _sync_entry(perf, v)
        dur = e.get("duration_s")
        if not dur:
            print(f"  ! {v['slug']}: no duration yet (run `learn refresh` first)")
            fail += 1
            continue
        try:
            curve = fetch(e.get("channel") or "nemock", v["video_id"],
                          e.get("posted") or "2026-01-01")
        except SystemExit as ex:           # publish's "not authorized" exits this way
            print(f"  ! {v['slug']}: {ex}")
            fail += 1
            continue
        except Exception as ex:            # noqa: BLE001 - one video must not stop the rest
            print(f"  ! {v['slug']}: analytics query failed ({type(ex).__name__}: {ex})")
            fail += 1
            continue
        if not curve:
            empty += 1                     # too few views for YouTube to report a curve
            continue
        snap = {"date": today, "source": "analytics"}
        for t in RET_POINTS:
            w = _watch_ratio_at(curve, t, dur)
            snap[f"ret{t}"] = None if w is None else round(100.0 * w, 1)
        _upsert_snapshot(e, snap)
        ok += 1
        print(f"  {v['slug']}: 0:30 {snap['ret30']}%  1:00 {snap['ret60']}%")
    save_perf(perf)
    print(f"retention: {ok} snapshotted, {empty} with no curve yet, {fail} failed → {PERF}")
    return 0 if ok else 1


# ---------------- articles (Substack post stats, 2026-11-27) ----------------
#
# The companion article is the second half of every close-out (article-playbook), and until
# now nothing looked at how it did. The Substack MCP's get_post_stats ranks every post by
# views, opens, signups and restacks; the post id ties it to a video through the
# `substack_post_id` that `content substack --write` records in meta.json.

ARTICLES = LEARN_DIR / "articles.json"
ARTICLE_FIELDS = ("views", "opened", "open_rate", "signups", "subscribes", "unsubscribes",
                  "likes", "comments", "restacks", "shares", "estimated_value")


def _article_links(projects_dir):
    """{substack post id: (project slug, youtube id)} from meta.json."""
    out = {}
    for mf in sorted(Path(projects_dir).glob("*/package/meta.json")):
        try:
            meta = json.loads(mf.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if meta.get("substack_post_id"):
            out[int(meta["substack_post_id"])] = (mf.parents[1].name,
                                                  _video_id(meta.get("youtube_url")))
    return out


STATS_PAGE = 20    # the tool advertises 100, but Substack answers 400 above 20 (2026-11-27)


def _all_post_stats(sub):
    import time
    posts, offset = [], 0
    while True:
        if offset:
            time.sleep(2)              # Substack answers 429 to a quick run of reads
        page = sub.call("get_post_stats", order_by="post_date", limit=STATS_PAGE, offset=offset)
        batch = page.get("posts") or []
        posts.extend(batch)
        offset += len(batch)
        if not batch or offset >= (page.get("total") or 0):
            return posts


def articles(projects_dir, fetch=None):
    """Snapshot every published Substack post's stats into articles.json.
    `fetch() -> [post stats]` is injectable for tests."""
    if fetch is None:
        def fetch():
            from .substack import SubstackMcp
            with SubstackMcp() as sub:
                return _all_post_stats(sub)
    try:
        posts = fetch()
    except Exception as ex:                # noqa: BLE001 - say what failed, don't trace
        print(f"articles: Substack stats unavailable ({type(ex).__name__}: {ex})")
        return 1
    links = _article_links(projects_dir)
    store = json.loads(ARTICLES.read_text()) if ARTICLES.exists() else {}
    today = date.today().isoformat()
    n = 0
    for p in posts:
        if not p.get("is_published", True) or not p.get("post_id"):
            continue
        pid = int(p["post_id"])
        e = store.setdefault(str(pid), {})
        e["title"] = p.get("title", "")
        e["posted"] = (p.get("post_date") or "")[:10]
        slug, vid = links.get(pid, (None, None))
        e["slug"], e["video_id"] = slug, vid
        _upsert_snapshot(e, {"date": today, "source": "substack",
                             **{k: p.get(k) for k in ARTICLE_FIELDS}})
        n += 1
    LEARN_DIR.mkdir(parents=True, exist_ok=True)
    ARTICLES.write_text(json.dumps(store, indent=2))
    tied = sum(1 for e in store.values() if e.get("slug"))
    print(f"articles: {n} posts snapshotted ({tied} tied to a video) → {ARTICLES}")
    return 0 if n else 1


# ---------------- shorts (re-share stats per platform, 2026-11-27) ----------------
#
# `promote` re-shares a Short every day to up to seven networks through the post queue,
# and nothing read back what happened. Blotato's REST API has GET /v2/posts/{id}/analytics
# on the submission id the queue keeps; YouTube Shorts go direct, so their views come from
# the Data API. Measured on the first run: Blotato returns X (impressions), Facebook
# (views) and Bluesky (engagement only, no reach); Instagram, Threads, TikTok and LinkedIn
# answer "not yet synced" even weeks later. Those are reported as no data, never as zero.

SHORTS = LEARN_DIR / "shorts.json"
POSTQ_DB = Path("/Volumes/Casima/claudeCode/make_money/post_queue/postq.db")
BLOTATO_DIR = Path("/Volumes/Casima/claudeCode/make_money/post_queue")
PROMOTE_ROUTINE = "explainer2-promote-daily"
SHORTS_MIN_AGE_H = 26        # Blotato syncs about a day after the post goes live
SHORTS_FINAL_D = 35          # Blotato stops re-fetching about a month in; so do we
REACH_KEYS = ("impressionsCount", "viewsCount")     # X | Facebook, YouTube
ENGAGE_KEYS = ("likesCount", "commentsCount", "savesCount", "twitterRetweetsCount",
               "twitterQuotesCount", "blueskyRepostsCount", "blueskyQuotesCount")
# Replies are left out of engagement on purpose: on X and Bluesky the first reply is our
# own link to the full video (promote's additional_posts), so every post starts at 1.


def _promote_rows(db_path=POSTQ_DB):
    import sqlite3
    c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(
            "SELECT uid, episode, platform, route, submission_id, post_url, source_asset, "
            "COALESCE(scheduled_at, updated_at) AS posted_at FROM post "
            "WHERE routine = ? AND status = 'published'", (PROMOTE_ROUTINE,))]
    finally:
        c.close()


def _project_of(source_asset):
    m = re.search(r"/projects/([^/]+)/shorts/", source_asset or "")
    return m.group(1) if m else None


def _reach(metrics):
    for k in REACH_KEYS:
        if metrics.get(k) not in (None, ""):
            return int(metrics[k])
    return None


def _engagement(metrics):
    vals = [int(metrics[k]) for k in ENGAGE_KEYS if metrics.get(k) not in (None, "")]
    return sum(vals) if vals else None


def _blotato_fetch(submission_id):
    """-> metrics dict, or None when Blotato has not synced this post (404)."""
    import sys
    if str(BLOTATO_DIR) not in sys.path:
        sys.path.insert(0, str(BLOTATO_DIR))
    import blotato
    try:
        out = blotato._request("GET", f"/posts/{submission_id}/analytics", timeout=60)
    except blotato.BlotatoError as ex:
        if ex.status == 404:
            return None
        raise
    return {"metrics": out.get("metrics") or {}, "fetched_at": out.get("lastFetchedAt")}


def _youtube_views(video_ids):
    from .publish import _service
    yt = _service("nemock", False)
    out = {}
    ids = sorted(video_ids)
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="statistics", id=",".join(ids[i:i + 50])).execute()
        for item in r.get("items") or []:
            s = item.get("statistics") or {}
            out[item["id"]] = {"metrics": {"viewsCount": s.get("viewCount"),
                                           "likesCount": s.get("likeCount"),
                                           "commentsCount": s.get("commentCount")},
                               "fetched_at": datetime.utcnow().isoformat() + "Z"}
    return out


def shorts(projects_dir=None, rows=None, blotato_fetch=None, youtube_fetch=None, now=None):
    """Snapshot reach and engagement for every published promote re-share into shorts.json.
    The fetchers and rows are injectable for tests."""
    import time
    rows = _promote_rows() if rows is None else rows
    blotato_fetch = blotato_fetch or _blotato_fetch
    youtube_fetch = youtube_fetch or _youtube_views
    now = now or datetime.utcnow()
    store = json.loads(SHORTS.read_text()) if SHORTS.exists() else {}
    today = now.date().isoformat()

    def age_h(r):
        try:
            return (now - datetime.strptime(r["posted_at"][:19], "%Y-%m-%dT%H:%M:%S")
                    ).total_seconds() / 3600
        except (TypeError, ValueError):
            return None

    def entry(r):
        e = store.setdefault(r["uid"], {})
        e.update({"short": r["episode"], "project": _project_of(r["source_asset"]),
                  "platform": r["platform"], "url": r["post_url"],
                  "posted": (r["posted_at"] or "")[:10]})
        return e

    def settled(e, r):
        # Final once we hold a snapshot taken more than SHORTS_FINAL_D days after posting.
        last = _latest(e)
        if not last:
            return False
        final = date.fromisoformat(r["posted_at"][:10]) + timedelta(days=SHORTS_FINAL_D)
        return last.get("date", "") >= final.isoformat()

    mature = [r for r in rows if (age_h(r) or 0) >= SHORTS_MIN_AGE_H]
    counts = {"snapshotted": 0, "unsynced": 0, "settled": 0, "failed": 0}
    unsynced_platforms = set()

    # YouTube: one batched Data API read for every direct upload.
    yt_rows = {}
    for r in mature:
        if r["route"] == "youtube_direct":
            vid = _video_id(r["post_url"])
            if vid:
                yt_rows[vid] = r
    if yt_rows:
        try:
            got = youtube_fetch(set(yt_rows))
        except (Exception, SystemExit) as ex:       # noqa: BLE001
            print(f"  ! YouTube stats unavailable ({type(ex).__name__}: {ex})")
            got = {}
            counts["failed"] += len(yt_rows)
        for vid, data in got.items():
            r = yt_rows[vid]
            _upsert_snapshot(entry(r), {"date": today, "source": "youtube", **data})
            counts["snapshotted"] += 1

    # Blotato: newest first per platform, so a platform that never syncs costs one call.
    blot = sorted((r for r in mature if r["route"] != "youtube_direct" and r["submission_id"]),
                  key=lambda r: r["posted_at"], reverse=True)
    synced_once = set()
    for r in blot:
        e = entry(r)
        plat = r["platform"]
        if plat in unsynced_platforms:
            counts["unsynced"] += 1
            continue
        if settled(e, r):
            counts["settled"] += 1
            continue
        try:
            data = blotato_fetch(r["submission_id"])
        except Exception as ex:                       # noqa: BLE001
            print(f"  ! {r['uid']}: Blotato analytics failed ({ex})")
            counts["failed"] += 1
            if "429" in str(ex):
                print("  ! Blotato rate limit; stopping here, the rest next run")
                break
            continue
        if data is None:
            counts["unsynced"] += 1
            # A mature post that never synced on a platform that has never synced in this
            # run: Blotato does not collect it. Skip the rest of that platform.
            if plat not in synced_once and (age_h(r) or 0) >= 72:
                unsynced_platforms.add(plat)
            continue
        synced_once.add(plat)
        _upsert_snapshot(e, {"date": today, "source": "blotato", **data})
        counts["snapshotted"] += 1
        time.sleep(0.15)

    meta = store.setdefault("_meta", {})
    meta["no_analytics"] = sorted(unsynced_platforms)
    meta["updated"] = today
    LEARN_DIR.mkdir(parents=True, exist_ok=True)
    SHORTS.write_text(json.dumps(store, indent=2))
    print(f"shorts: {counts['snapshotted']} snapshotted, {counts['settled']} settled, "
          f"{counts['unsynced']} not synced by Blotato, {counts['failed']} failed"
          + (f"; no analytics from {', '.join(sorted(unsynced_platforms))}"
             if unsynced_platforms else "") + f" → {SHORTS}")
    return 0 if counts["snapshotted"] or counts["settled"] else 1


# ---------------- ingest (YouTube Studio CSV) ----------------

# canonical field -> substrings matched against lowercased CSV headers
_CSV_MAP = [
    ("video_id", ("content",)),
    ("views", ("views",)),
    ("impressions", ("impressions",)),          # exact-ish; CTR handled first
    ("ctr_pct", ("click-through", "click through")),
    ("avg_view", ("average view duration",)),
    ("watch_hours", ("watch time",)),
    ("subs", ("subscribers",)),
]


def _map_headers(fieldnames):
    m = {}
    for h in fieldnames or []:
        hl = h.lower().strip()
        for key, needles in _CSV_MAP:
            if key in m:
                continue
            if any(n in hl for n in needles):
                # "impressions click-through rate" must not claim "impressions"
                if key == "impressions" and ("click" in hl or "rate" in hl):
                    continue
                m[key] = h
                break
    return m


def _num(x):
    try:
        return float(str(x).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def ingest(csv_path):
    path = Path(csv_path)
    if not path.exists():
        print(f"no such file: {path}")
        return 1
    with path.open(newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        cols = _map_headers(rd.fieldnames)
        if "video_id" not in cols:
            print(f"can't find the video-id column ('Content') in: {rd.fieldnames}")
            return 1
        rows = list(rd)
    perf = load_perf()
    today = date.today().isoformat()
    hit = skipped = 0
    for r in rows:
        vid = (r.get(cols["video_id"]) or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
            skipped += 1            # the Total row and any malformed lines
            continue
        if vid not in perf:
            skipped += 1            # a Short or a video we don't track
            continue
        snap = {"date": today, "source": "studio"}
        if "views" in cols:
            snap["views"] = _num(r.get(cols["views"]))
        if "impressions" in cols:
            snap["impressions"] = _num(r.get(cols["impressions"]))
        if "ctr_pct" in cols:
            snap["ctr_pct"] = _num(r.get(cols["ctr_pct"]))
        if "avg_view" in cols:
            snap["avg_view_s"] = _dur_s(r.get(cols["avg_view"]))
        if "watch_hours" in cols:
            snap["watch_hours"] = _num(r.get(cols["watch_hours"]))
        if "subs" in cols:
            snap["subs"] = _num(r.get(cols["subs"]))
        _upsert_snapshot(perf[vid], snap)
        hit += 1
    save_perf(perf)
    print(f"ingest: {hit} videos updated, {skipped} rows skipped → {PERF}")
    return 0 if hit else 1


# ---------------- report ----------------

def _latest(entry, source=None):
    snaps = entry.get("snapshots", [])
    if source:
        snaps = [s for s in snaps if s.get("source") == source]
    return snaps[-1] if snaps else None


def _age_days(posted, today):
    try:
        return max(1, (today - datetime.strptime(posted, "%Y-%m-%d").date()).days)
    except ValueError:
        return None


def _fmt(n, nd=0):
    if n is None:
        return "—"
    return f"{n:,.{nd}f}"


def _first_minute_section(rows):
    """Did the 30-second contract (script-playbook §4.1, 2026-11-27) move the first minute?
    Compares videos posted before it with those posted after, counting only videos with
    enough views for a retention point to mean anything."""
    solid = [r for r in rows if r["ret30"] is not None and (r["views"] or 0) >= RET_MIN_VIEWS]
    if not solid:
        return []
    L = ["## The first minute", "",
         f"Share still watching at 0:30 and 1:00, videos with ≥{RET_MIN_VIEWS} views. "
         f"The 30-second contract (script-playbook §4.1) applies to scripts written from "
         f"{CONTRACT_DATE}; compare the two groups once the second has a few videos.", ""]
    for label, grp in (("before the contract", [r for r in solid if r["posted"] < CONTRACT_DATE]),
                       ("written to the contract", [r for r in solid if r["posted"] >= CONTRACT_DATE])):
        if not grp:
            L.append(f"- **{label}**: no videos yet")
            continue
        r30 = statistics.median(r["ret30"] for r in grp)
        r60s = [r["ret60"] for r in grp if r["ret60"] is not None]
        r60 = statistics.median(r60s) if r60s else None
        L.append(f"- **{label}** ({len(grp)} videos): median {_fmt(r30, 0)}% at 0:30, "
                 f"{_fmt(r60, 0)}% at 1:00")
    worst = sorted(solid, key=lambda r: r["ret30"])[:3]
    L.append("")
    L.append("Weakest openings (lowest at 0:30): "
             + "; ".join(f"{(r['title'] or r['slug'])[:50]} ({_fmt(r['ret30'], 0)}%)" for r in worst))
    L.append("")
    return L


def _articles_section(perf):
    """Which companion articles were read, and which grew the list."""
    if not ARTICLES.exists():
        return []
    store = json.loads(ARTICLES.read_text())
    rows = []
    for pid, e in store.items():
        s = _latest(e, "substack")
        if s:
            rows.append({**s, "pid": pid, "title": e.get("title", ""), "posted": e.get("posted", ""),
                         "slug": e.get("slug"), "video_id": e.get("video_id")})
    if not rows:
        return []
    views = [r["views"] for r in rows if r.get("views") is not None]
    rates = [r["open_rate"] for r in rows if r.get("open_rate") is not None]
    signups = sum(r.get("signups") or 0 for r in rows)
    L = ["## Articles (Substack)", "",
         f"{len(rows)} published posts: median {_fmt(statistics.median(views) if views else None)} "
         f"views, median open rate {_fmt(100 * statistics.median(rates) if rates else None)}%, "
         f"{signups} signups in all (`learn articles`).", ""]
    tied = sorted((r for r in rows if r["slug"]), key=lambda r: r["posted"], reverse=True)
    if tied:
        L += ["Companion articles, newest first, beside their video:", "",
              "| article | posted | views | open % | signups | restacks | video views/day |",
              "|---|---|---:|---:|---:|---:|---:|"]
        today = date.today()
        for r in tied[:15]:
            v = perf.get(r["video_id"] or "", {})
            pub = _latest(v, "ytdlp") or {}
            age = _age_days(v.get("posted", ""), today) if v.get("posted") else None
            vpd = (pub["views"] / age) if (pub.get("views") and age) else None
            name = r["title"] if len(r["title"]) <= 55 else r["title"][:52] + "…"
            L.append(f"| {name} | {r['posted']} | {_fmt(r.get('views'))} "
                     f"| {_fmt(100 * r['open_rate'] if r.get('open_rate') is not None else None)} "
                     f"| {r.get('signups') or 0} | {r.get('restacks') or 0} | {_fmt(vpd, 1)} |")
        L.append("")
    growers = sorted((r for r in rows if (r.get("signups") or 0) + (r.get("subscribes") or 0)),
                     key=lambda r: -((r.get("signups") or 0) + (r.get("subscribes") or 0)))[:5]
    if growers:
        L.append("Grew the list (signups): " + "; ".join(
            f"{r['title'][:50]} ({r.get('signups') or 0})" for r in growers))
        L.append("")
    lost = [r for r in rows if (r.get("unsubscribes") or 0) > 0]
    if lost:
        L.append("Cost subscribers: " + "; ".join(
            f"{r['title'][:50]} ({r['unsubscribes']})" for r in
            sorted(lost, key=lambda r: -r["unsubscribes"])[:5]))
        L.append("")
    return L


def _shorts_section():
    """Re-shared Shorts: reach and engagement per platform, and the Shorts that travelled."""
    if not SHORTS.exists():
        return []
    store = json.loads(SHORTS.read_text())
    meta = store.pop("_meta", {})
    by_plat, by_short = {}, {}
    for e in store.values():
        p = by_plat.setdefault(e.get("platform", "?"), {"posts": 0, "reach": [], "eng": []})
        p["posts"] += 1
        s = _latest(e)
        if not s:
            continue
        m = s.get("metrics") or {}
        reach, eng = _reach(m), _engagement(m)
        if reach is not None:
            p["reach"].append(reach)
        if eng is not None:
            p["eng"].append(eng)
        k = (e.get("project"), e.get("short"))
        by_short.setdefault(k, 0)
        by_short[k] += reach or 0
    if not any(p["reach"] or p["eng"] for p in by_plat.values()):
        return []
    L = ["## Shorts re-shares by platform", "",
         "Every `promote` re-share since 2026-08-09 (`learn shorts`). Reach is X impressions, "
         "or views on Facebook and YouTube. Engagement is likes, comments, saves and reposts; "
         "replies are left out because the first one is our own link to the full video.", "",
         "| platform | posts | with data | median reach | total reach | median engagement |",
         "|---|---:|---:|---:|---:|---:|"]
    for plat, p in sorted(by_plat.items(), key=lambda kv: -sum(kv[1]["reach"])):
        have = max(len(p["reach"]), len(p["eng"]))
        L.append(f"| {plat} | {p['posts']} | {have} "
                 f"| {_fmt(statistics.median(p['reach'])) if p['reach'] else '—'} "
                 f"| {_fmt(sum(p['reach'])) if p['reach'] else '—'} "
                 f"| {_fmt(statistics.median(p['eng']), 1) if p['eng'] else '—'} |")
    L.append("")
    nodata = sorted(set(meta.get("no_analytics") or [])
                    | {pl for pl, p in by_plat.items() if not (p["reach"] or p["eng"])})
    if nodata:
        L.append(f"*No data from {', '.join(nodata)}: Blotato does not collect analytics "
                 f"there. That is missing data, not zero views.*")
        L.append("")
    top = sorted(((k, v) for k, v in by_short.items() if v), key=lambda kv: -kv[1])[:5]
    if top:
        L.append("Shorts that travelled furthest (total reach, all platforms): " + "; ".join(
            f"{short} from {(proj or '?')[:24]} ({_fmt(v)})" for (proj, short), v in top))
        L.append("")
    return L


def report():
    perf = load_perf()
    if not perf:
        print("no performance data yet — run `learn refresh` first")
        return 1
    today = date.today()
    rows = []
    for vid, e in perf.items():
        pub = _latest(e, "ytdlp") or {}
        stu = _latest(e, "studio") or {}
        ana = _latest(e, "analytics") or {}
        views = stu.get("views") or pub.get("views")
        age = _age_days(e.get("posted", ""), today)
        vpd = (views / age) if (views and age) else None
        avp = None
        if stu.get("avg_view_s") and e.get("duration_s"):
            avp = 100.0 * stu["avg_view_s"] / e["duration_s"]
        rows.append({
            "vid": vid, "slug": e.get("slug", ""), "title": e.get("title", ""),
            "posted": e.get("posted", ""), "age": age, "views": views,
            "vpd": vpd, "likes": pub.get("likes"), "comments": pub.get("comments"),
            "ctr": stu.get("ctr_pct"), "avp": avp,
            "ret30": ana.get("ret30"), "ret60": ana.get("ret60"),
            "young": age is not None and age < MIN_AGE_DAYS,
            "features": e.get("features", {}),
        })
    rows.sort(key=lambda r: -(r["vpd"] or 0))
    mature = [r for r in rows if r["vpd"] and not r["young"]]
    med = statistics.median([r["vpd"] for r in mature]) if mature else None

    L = []
    L.append("# Channel performance report")
    L.append("")
    L.append(f"Generated {today.isoformat()} from {len(rows)} published deep dives. "
             f"Views/day channel median: **{_fmt(med, 1)}**. "
             "Read this before ranking titles or thumbnails (blueprint playbook §7).")
    L.append("")
    L.append("| video | posted | age d | views | views/day | vs median | CTR % | avg view % "
             "| at 0:30 % | at 1:00 % |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        rel = (r["vpd"] / med) if (r["vpd"] and med) else None
        tag = ""
        if r["young"]:
            tag = " *(young)*"
        elif rel and rel >= BREAKOUT:
            tag = " **▲**"
        elif rel is not None and rel <= LAGGARD:
            tag = " ▽"
        name = r["title"] or r["slug"]
        if len(name) > 60:
            name = name[:57] + "…"
        thin = "†" if (r["ret30"] is not None and (r["views"] or 0) < RET_MIN_VIEWS) else ""
        L.append(f"| {name}{tag} | {r['posted']} | {r['age'] or '—'} | {_fmt(r['views'])} "
                 f"| {_fmt(r['vpd'], 1)} | {_fmt(rel, 2) + 'x' if rel else '—'} "
                 f"| {_fmt(r['ctr'], 1)} | {_fmt(r['avp'], 0)} "
                 f"| {_fmt(r['ret30'], 0)}{thin} | {_fmt(r['ret60'], 0)}{thin} |")
    L.append("")
    if any(r["ret30"] is not None for r in rows):
        L.append(f"*0:30 / 1:00 = share of viewers still watching at that point (YouTube "
                 f"Analytics audience retention, `learn retention`). † = under {RET_MIN_VIEWS} "
                 f"views, so the point is noise.*")
        L.append("")
    L.extend(_first_minute_section(rows))

    ups = [r for r in mature if med and r["vpd"] / med >= BREAKOUT]
    downs = [r for r in mature if med and r["vpd"] / med <= LAGGARD]
    if ups:
        L.append("## Breakouts (≥1.5x median views/day)")
        L.extend(f"- **{r['title']}** — {_fmt(r['vpd'], 1)} views/day ({_fmt(r['vpd'] / med, 1)}x)"
                 for r in ups)
        L.append("")
    if downs:
        L.append("## Laggards (≤0.5x median views/day)")
        L.extend(f"- {r['title']} — {_fmt(r['vpd'], 1)} views/day" for r in downs)
        L.append("")

    L.append("## Title features vs performance")
    L.append("")
    L.append("Median views/day with vs without each deterministic title feature "
             "(only shown when both groups have ≥3 mature videos — correlation, not causation, "
             "on a small channel; treat as a tiebreaker, never a veto):")
    L.append("")
    any_feat = False
    for feat in ("question", "number", "second_person", "negation", "two_part", "first_person"):
        w = [r["vpd"] for r in mature if r["features"].get(feat)]
        wo = [r["vpd"] for r in mature if not r["features"].get(feat)]
        if len(w) >= 3 and len(wo) >= 3:
            any_feat = True
            L.append(f"- **{feat.replace('_', ' ')}**: with {_fmt(statistics.median(w), 1)} "
                     f"({len(w)} videos) vs without {_fmt(statistics.median(wo), 1)} ({len(wo)})")
    if not any_feat:
        L.append("- not enough mature videos on both sides of any feature yet")
    L.append("")

    if not any(r["ctr"] is not None for r in rows):
        L.append("*(No YouTube Studio CSV ingested yet — impressions/CTR/avg-view-duration "
                 "columns will fill in after `learn ingest --csv <export>`.)*")
        L.append("")
    L.extend(_articles_section(perf))
    L.extend(_shorts_section())

    LEARN_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L))
    print(f"report → {REPORT}  ({len(rows)} videos, median {_fmt(med, 1)} views/day)")
    return 0
