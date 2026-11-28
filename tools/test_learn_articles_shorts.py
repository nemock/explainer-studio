#!/usr/bin/env python3
"""`learn articles` and `learn shorts` (2026-11-27): Substack post stats and promote
re-share reach per platform, feeding REPORT.md.

Run:  python3 tools/test_learn_articles_shorts.py

Offline: the Substack, Blotato and YouTube calls are injected, the post-queue rows are
handed in, and every store/report path points at a temp dir.
"""
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from explainer2 import learn  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="learn-articles-test-"))
learn.LEARN_DIR = TMP / "learn"
learn.PERF = learn.LEARN_DIR / "performance.json"
learn.REPORT = learn.LEARN_DIR / "REPORT.md"
learn.ARTICLES = learn.LEARN_DIR / "articles.json"
learn.SHORTS = learn.LEARN_DIR / "shorts.json"
FAILS = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAILS.append(what)


# ---------------- articles ----------------
projects = TMP / "projects"
d = projects / "2026-11-10_80_routers"
(d / "package").mkdir(parents=True)
(d / "package" / "meta.json").write_text(json.dumps({
    "title": "Routers", "youtube_url": "https://youtu.be/AAAAAAAAAAA", "posted": "2026-11-10",
    "substack_post_id": 111}))

posts = [
    {"post_id": 111, "title": "Old Routers Don't All Fail at Once", "post_date": "2026-11-15T01:07:39Z",
     "is_published": True, "views": 128, "opened": 18, "open_rate": 0.2, "signups": 1,
     "subscribes": 0, "unsubscribes": 0, "restacks": 2, "likes": 7},
    {"post_id": 222, "title": "An essay with no video", "post_date": "2026-10-01T10:00:00Z",
     "is_published": True, "views": 30, "open_rate": 0.25, "signups": 3, "unsubscribes": 1},
    {"post_id": 333, "title": "A draft", "post_date": "2026-11-20T10:00:00Z", "is_published": False},
]
check(learn.articles(projects, fetch=lambda: posts) == 0, "articles returns 0 on success")
store = json.loads(learn.ARTICLES.read_text())
check(set(store) == {"111", "222"}, "drafts are left out, published posts stored by id")
check(store["111"]["slug"] == "2026-11-10_80_routers" and store["111"]["video_id"] == "AAAAAAAAAAA",
      "a post is tied to its video through meta.json's substack_post_id")
check(store["222"]["slug"] is None, "a post with no video stays untied")
check(store["111"]["snapshots"][-1]["views"] == 128, "the snapshot keeps the stats")
learn.articles(projects, fetch=lambda: posts)
check(len(json.loads(learn.ARTICLES.read_text())["111"]["snapshots"]) == 1,
      "a same-day re-run updates in place")


def boom():
    raise RuntimeError("substack-mcp not configured")


check(learn.articles(projects, fetch=boom) == 1, "a Substack failure returns 1, no traceback")

# ---------------- shorts ----------------
NOW = datetime(2026, 11, 27, 20, 0, 0)


def row(uid, plat, posted, sub=None, url=None, route="blotato"):
    return {"uid": uid, "episode": uid.split(":")[1], "platform": plat, "route": route,
            "submission_id": sub, "post_url": url, "posted_at": posted,
            "source_asset": "/x/explainer-content/projects/2026-08-12_59_pilots/shorts/"
                            + uid.split(":")[1] + "/video/explainer_9x16.mp4"}


rows = [
    row("p:s1:twitter", "twitter", "2026-11-20T13:00:00.000Z", sub="t1"),
    row("p:s1:facebook", "facebook", "2026-11-20T13:00:00.000Z", sub="f1"),
    row("p:s1:instagram", "instagram", "2026-11-20T13:00:00.000Z", sub="i1"),
    row("p:s2:instagram", "instagram", "2026-11-10T13:00:00.000Z", sub="i2"),
    row("p:s2:twitter", "twitter", "2026-11-27T12:00:00.000Z", sub="t2"),     # too young
    row("p:s1:youtube", "youtube", "2026-11-20T13:00:00.000Z",
        url="https://www.youtube.com/shorts/YYYYYYYYYYY", route="youtube_direct"),
    row("p:s0:twitter", "twitter", "2026-09-01T13:00:00.000Z", sub="t0"),     # old, settles
]
asked = []


def fake_blotato(sid):
    asked.append(sid)
    return {"t1": {"metrics": {"impressionsCount": "62", "likesCount": "1", "repliesCount": "1"}},
            "f1": {"metrics": {"viewsCount": "18", "likesCount": "0"}},
            "t0": {"metrics": {"impressionsCount": "40"}}}.get(sid)


def fake_youtube(ids):
    return {i: {"metrics": {"viewsCount": "250", "likesCount": "4"}} for i in ids}


check(learn.shorts(rows=rows, blotato_fetch=fake_blotato, youtube_fetch=fake_youtube, now=NOW) == 0,
      "shorts returns 0 on success")
st = json.loads(learn.SHORTS.read_text())
check("t2" not in asked, "a post under a day old is not asked yet")
check("t0" in asked, "an old post with no snapshot is fetched once")
check(asked.count("i1") == 1 and "i2" not in asked,
      "an unsynced platform stops after one mature post, so it costs one call")
check(st["_meta"]["no_analytics"] == ["instagram"], "the platform is recorded as having no analytics")
check(st["p:s1:youtube"]["snapshots"][-1]["metrics"]["viewsCount"] == "250",
      "YouTube Shorts views come from the Data API")
check(st["p:s1:twitter"]["project"] == "2026-08-12_59_pilots", "the project is read from the source path")
check(learn._reach({"impressionsCount": "62"}) == 62 and learn._reach({"viewsCount": "9"}) == 9,
      "reach is impressions or views")
check(learn._engagement({"likesCount": "1", "repliesCount": "1"}) == 1,
      "engagement leaves out replies (our own link reply)")
check(learn._reach({}) is None and learn._engagement({}) is None, "no metrics gives None, not 0")

later = datetime(2026, 11, 28, 20, 0, 0)
asked.clear()
learn.shorts(rows=rows, blotato_fetch=fake_blotato, youtube_fetch=fake_youtube, now=later)
check("t0" not in asked and "t1" in asked, "a snapshot taken past 35 days settles the post")

# ---------------- report ----------------
learn.PERF.write_text(json.dumps({"AAAAAAAAAAA": {
    "slug": "2026-11-10_80_routers", "title": "Routers", "posted": "2026-11-10",
    "snapshots": [{"date": "2026-11-27", "source": "ytdlp", "views": 170}]}}))
check(learn.report() == 0, "report runs with both new stores present")
rep = learn.REPORT.read_text()
check("## Articles (Substack)" in rep and "Old Routers" in rep, "report has the article section")
check("Grew the list (signups): An essay with no video (3)" in rep, "the list growers are ranked")
check("Cost subscribers: An essay with no video (1)" in rep, "unsubscribes are surfaced")
check("## Shorts re-shares by platform" in rep and "| youtube |" in rep, "report has the shorts table")
check("No data from instagram" in rep, "a platform with no analytics is called missing, not zero")

print()
print("FAILED: " + "; ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
