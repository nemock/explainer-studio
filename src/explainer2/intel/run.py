"""Intel pipeline: sweep → outlier scoring → deep pull → intel.json (PRD §5.1).

Stages are idempotent: each writes a JSON artifact into <project>/intel/ and is
skipped on re-run if the artifact exists and is younger than CACHE_DAYS. The
output intel.json is the synthesis input for the generation plane (Claude),
which writes blueprint.md / blueprint.json. No LLM calls happen here.
"""
import json
import statistics
import time
from pathlib import Path

from . import ytfetch

CACHE_DAYS = 14
MIN_DURATION_S = 60
MAX_DURATION_S = 3600
MAX_BASELINE_CHANNELS = 18
HOOK_CHARS = 1200          # transcript head exposed directly in intel.json
PAUSE_S = 0.5              # politeness gap between yt-dlp calls


def _fresh(path: Path) -> bool:
    return path.exists() and (time.time() - path.stat().st_mtime) < CACHE_DAYS * 86400


def _log(msg):
    print(f"intel: {msg}", flush=True)


def default_queries(topic):
    t = topic.strip().rstrip("?")
    return [t, f"{t} explained", f"how to {t}" if not t.lower().startswith("how") else f"{t} step by step"]


def sweep(intel_dir: Path, queries, per_query=15):
    out = intel_dir / "candidates.json"
    if _fresh(out):
        _log(f"sweep cached ({out.name})")
        return json.loads(out.read_text())
    seen, candidates = set(), []
    for q in queries:
        _log(f"search: {q!r}")
        for c in ytfetch.search(q, n=per_query):
            if c["id"] in seen:
                continue
            seen.add(c["id"])
            d = c.get("duration_s")
            if d is not None and not (MIN_DURATION_S <= d <= MAX_DURATION_S):
                continue
            candidates.append(c)
        time.sleep(PAUSE_S)
    candidates.sort(key=lambda c: c.get("view_count") or 0, reverse=True)
    out.write_text(json.dumps(candidates, indent=2))
    _log(f"sweep: {len(candidates)} unique candidates")
    return candidates


def score_outliers(intel_dir: Path, candidates, max_finalists=12):
    out = intel_dir / "outliers.json"
    if _fresh(out):
        _log(f"outliers cached ({out.name})")
        return json.loads(out.read_text())
    # one baseline fetch per channel, costliest first by candidate views
    medians, fetched = {}, 0
    for c in candidates:
        ch = c.get("channel_id")
        if not ch or ch in medians or fetched >= MAX_BASELINE_CHANNELS:
            continue
        views = ytfetch.channel_recent_views(ch)
        medians[ch] = statistics.median(views) if views else None
        fetched += 1
        _log(f"baseline {fetched}/{MAX_BASELINE_CHANNELS}: {c['channel']!r} "
             f"median={medians[ch] and int(medians[ch])}")
        time.sleep(PAUSE_S)
    scored = []
    for c in candidates:
        med = medians.get(c.get("channel_id"))
        v = c.get("view_count") or 0
        c = dict(c)
        c["channel_median_views"] = med
        c["outlier_score"] = round(v / med, 2) if (med and med > 0) else None
        scored.append(c)
    # rank: outlier score first (unknown last), views as tiebreaker
    scored.sort(key=lambda c: (c["outlier_score"] or 0, c.get("view_count") or 0),
                reverse=True)
    finalists = scored[:max_finalists]
    out.write_text(json.dumps({"scored": scored, "finalist_ids": [f["id"] for f in finalists]},
                              indent=2))
    _log(f"outliers: top score {finalists and finalists[0]['outlier_score']}, "
         f"{len(finalists)} finalists")
    return {"scored": scored, "finalist_ids": [f["id"] for f in finalists]}


def deep_pull(intel_dir: Path, finalist_ids):
    fin_dir = intel_dir / "finalists"
    results = []
    for i, vid in enumerate(finalist_ids, 1):
        vdir = fin_dir / vid
        meta_p = vdir / "meta.json"
        if _fresh(meta_p):
            _log(f"deep {i}/{len(finalist_ids)}: {vid} cached")
            results.append(json.loads(meta_p.read_text()))
            continue
        vdir.mkdir(parents=True, exist_ok=True)
        meta = ytfetch.video_metadata(vid)
        if not meta:
            _log(f"deep {i}/{len(finalist_ids)}: {vid} FAILED metadata — skipped")
            continue
        meta["transcript_path"] = ytfetch.download_transcript(vid, vdir)
        meta["thumb_path"] = ytfetch.download_thumbnail(meta.get("thumbnail_url"),
                                                        vdir / "thumb.jpg")
        meta_p.write_text(json.dumps(meta, indent=2))
        _log(f"deep {i}/{len(finalist_ids)}: {meta['title'][:60]!r} "
             f"transcript={'yes' if meta['transcript_path'] else 'NO'}")
        results.append(meta)
        time.sleep(PAUSE_S)
    return results


def assemble(intel_dir: Path, topic, queries, outliers, finalists):
    by_id = {c["id"]: c for c in outliers["scored"]}
    items = []
    for m in finalists:
        sc = by_id.get(m["id"], {})
        hook = ""
        if m.get("transcript_path") and Path(m["transcript_path"]).exists():
            hook = Path(m["transcript_path"]).read_text()[:HOOK_CHARS]
        items.append({
            "id": m["id"], "url": f"https://www.youtube.com/watch?v={m['id']}",
            "title": m["title"], "channel": m["channel"],
            "subscribers": m.get("channel_follower_count"),
            "upload_date": m.get("upload_date"), "duration_s": m.get("duration_s"),
            "view_count": m.get("view_count"), "like_count": m.get("like_count"),
            "comment_count": m.get("comment_count"),
            "channel_median_views": sc.get("channel_median_views"),
            "outlier_score": sc.get("outlier_score"),
            "tags": m.get("tags", [])[:20], "chapters": m.get("chapters", []),
            "description_head": m.get("description", "")[:800],
            "top_comments": m.get("comments", [])[:8],
            "transcript_hook": hook,
            "transcript_path": m.get("transcript_path"),
            "thumb_path": m.get("thumb_path"),
        })
    intel = {"schema": "intel/1", "topic": topic, "queries": queries,
             "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
             "finalists": items,
             "next": "Generation plane: read finalists (+ transcripts/thumbs by path), "
                     "write blueprint.md + blueprint.json per PRD §5.1."}
    (intel_dir / "intel.json").write_text(json.dumps(intel, indent=2))
    return intel


def run(project_dir, topic, queries=None, max_finalists=12, per_query=15):
    intel_dir = Path(project_dir) / "intel"
    intel_dir.mkdir(parents=True, exist_ok=True)
    queries = queries or default_queries(topic)
    t0 = time.time()
    candidates = sweep(intel_dir, queries, per_query=per_query)
    if not candidates:
        return {"error": "sweep found no candidates — check yt-dlp / network"}
    outliers = score_outliers(intel_dir, candidates, max_finalists=max_finalists)
    finalists = deep_pull(intel_dir, outliers["finalist_ids"])
    intel = assemble(intel_dir, topic, queries, outliers, finalists)
    return {"intel": str(intel_dir / "intel.json"),
            "candidates": len(candidates), "finalists": len(intel["finalists"]),
            "with_transcript": sum(1 for f in intel["finalists"] if f["transcript_path"]),
            "wall_clock_s": round(time.time() - t0, 1)}
