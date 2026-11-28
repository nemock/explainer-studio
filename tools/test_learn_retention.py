#!/usr/bin/env python3
"""`learn retention` (2026-11-27): the 0:30 / 1:00 watch ratio from YouTube Analytics.

Run:  python3 tools/test_learn_retention.py

It exists because script-playbook §4.1's 30-second contract ends "the learn loop's 30 s /
60 s watch ratio is how we find out whether it worked", and until now nothing recorded it.
Offline: the Analytics call is injected, and the store/report paths point at a temp dir.
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from explainer2 import learn  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="learn-retention-test-"))
learn.LEARN_DIR = TMP / "learn"
learn.PERF = learn.LEARN_DIR / "performance.json"
learn.REPORT = learn.LEARN_DIR / "REPORT.md"
FAILS = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAILS.append(what)


# A straight-line curve: watch ratio falls from 1.0 at the start to 0.0 at the end.
line = [(i / 100, 1 - i / 100) for i in range(1, 101)]
check(abs(learn._watch_ratio_at(line, 30, 300) - 0.9) < 1e-9, "0:30 of a 5:00 video reads 10% in")
check(abs(learn._watch_ratio_at(line, 45, 600) - 0.925) < 1e-9, "a point between buckets interpolates")
check(learn._watch_ratio_at(line, 60, 50) is None, "a video shorter than the point gives None")
check(learn._watch_ratio_at([], 30, 300) is None, "no curve gives None")

# Two published projects: one before the contract, one written to it, one with no curve.
projects = TMP / "projects"


def project(slug, vid, posted, channel=None, duration="10:00"):
    d = projects / slug
    (d / "package").mkdir(parents=True)
    (d / "package" / "meta.json").write_text(json.dumps({
        "title": slug, "youtube_url": f"https://youtu.be/{vid}", "posted": posted,
        "duration": duration}))
    (d / "project.json").write_text(json.dumps({"youtube_channel": channel} if channel else {}))


project("old-one", "AAAAAAAAAAA", "2026-11-01")
project("new-one", "BBBBBBBBBBB", "2026-11-28", channel="nemock")
project("tiny-one", "CCCCCCCCCCC", "2026-11-20")
calls = []


def fake_fetch(channel, vid, start):
    calls.append((channel, vid, start))
    if vid == "CCCCCCCCCCC":
        return []                                  # too few views: YouTube returns nothing
    drop = 0.5 if vid == "AAAAAAAAAAA" else 0.2    # the new video holds better
    return [(i / 100, 1 - drop - (1 - drop) * i / 100) for i in range(1, 101)]


rc = learn.retention(projects, fetch=fake_fetch)
perf = json.loads(learn.PERF.read_text())
check(rc == 0, "retention exits 0 when any video was snapshotted")
check(("nemock", "AAAAAAAAAAA", "2026-11-01") in calls, "the curve is queried from the posted date")
a = learn._latest(perf["AAAAAAAAAAA"], "analytics")
check(a and a["ret30"] == 47.5 and a["ret60"] == 45.0, f"0:30 and 1:00 recorded as percentages ({a})")
check(learn._latest(perf["CCCCCCCCCCC"], "analytics") is None, "no curve, no snapshot")
learn.retention(projects, fetch=fake_fetch)
check(len([s for s in perf["AAAAAAAAAAA"]["snapshots"]]) == 1 and
      len(json.loads(learn.PERF.read_text())["AAAAAAAAAAA"]["snapshots"]) == 1,
      "a same-day re-run updates the snapshot instead of appending")

# A duration fetched by refresh must survive a later sync from a meta.json that lacks one.
perf["AAAAAAAAAAA"]["duration_s"] = 777
learn._sync_entry(perf, {"video_id": "AAAAAAAAAAA", "slug": "old-one", "title": "old-one",
                         "url": "u", "posted": None, "duration_s": None, "ab_test": False})
check(perf["AAAAAAAAAAA"]["duration_s"] == 777 and perf["AAAAAAAAAAA"]["posted"] == "2026-11-01",
      "a sync with no duration or date keeps the ones already known")

# The report: columns, the † for thin videos, the before/after section.
for vid, views in (("AAAAAAAAAAA", 500), ("BBBBBBBBBBB", 300)):
    learn._upsert_snapshot(perf[vid], {"date": "2026-11-29", "source": "ytdlp", "views": views})
learn.save_perf(perf)
learn.report()
rep = learn.REPORT.read_text()
check("at 0:30 %" in rep and "at 1:00 %" in rep, "REPORT.md has the 0:30 and 1:00 columns")
check("## The first minute" in rep, "REPORT.md has the first-minute section")
check("before the contract** (1 videos): median 48% at 0:30" in rep or
      "before the contract** (1 videos): median 47% at 0:30" in rep,
      "the older video is counted before the contract")
check("written to the contract** (1 videos)" in rep, "the newer video is counted after it")

perf["BBBBBBBBBBB"]["snapshots"][-1]["views"] = 40
learn.save_perf(perf)
learn.report()
check("†" in learn.REPORT.read_text(), "a video under the view floor is flagged †")

print()
if FAILS:
    print(f"{len(FAILS)} FAILED")
    sys.exit(1)
print("all passed")
