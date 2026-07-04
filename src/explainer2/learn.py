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
  report         rewrite REPORT.md from the latest snapshots.

One snapshot per (date, source) — re-running a verb the same day updates in
place instead of appending duplicates.
"""
import csv
import json
import re
import statistics
from datetime import date, datetime
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
        out.append({
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
    for k in ("slug", "title", "url", "duration_s", "ab_test"):
        e[k] = v[k]
    if v.get("posted"):                 # don't clobber a backfilled date with None
        e["posted"] = v["posted"]
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
    L.append("| video | posted | age d | views | views/day | vs median | CTR % | avg view % |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|")
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
        L.append(f"| {name}{tag} | {r['posted']} | {r['age'] or '—'} | {_fmt(r['views'])} "
                 f"| {_fmt(r['vpd'], 1)} | {_fmt(rel, 2) + 'x' if rel else '—'} "
                 f"| {_fmt(r['ctr'], 1)} | {_fmt(r['avp'], 0)} |")
    L.append("")

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

    LEARN_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L))
    print(f"report → {REPORT}  ({len(rows)} videos, median {_fmt(med, 1)} views/day)")
    return 0
