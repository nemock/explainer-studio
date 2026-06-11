"""Thin wrappers around the yt-dlp binary. Every call is a subprocess; failures
return None/[] so a single dead video never kills a sweep (PRD R1)."""
import json
import subprocess
import urllib.request
from pathlib import Path

YTDLP = "yt-dlp"
TIMEOUT_S = 120


def _ytdlp_json(args, timeout=TIMEOUT_S):
    cmd = [YTDLP, "--no-warnings", "--ignore-config", "-J"] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def search(query, n=15):
    """Flat search → list of {id,title,channel,channel_id,duration,view_count,url}."""
    data = _ytdlp_json(["--flat-playlist", f"ytsearch{n}:{query}"])
    out = []
    for e in (data or {}).get("entries", []) or []:
        if not e or e.get("id") is None:
            continue
        out.append({
            "id": e["id"],
            "title": e.get("title") or "",
            "channel": e.get("channel") or e.get("uploader") or "",
            "channel_id": e.get("channel_id"),
            "duration_s": e.get("duration"),
            "view_count": e.get("view_count"),
            "url": f"https://www.youtube.com/watch?v={e['id']}",
            "query": query,
        })
    return out


def channel_recent_views(channel_id, min_age_days=14):
    """View counts of a channel's recent uploads, via the channel RSS feed
    (one cheap GET; yt-dlp's flat channel-tab entries don't carry view_count).
    Skips uploads younger than min_age_days — their views are still accumulating
    and would bias the median low."""
    if not channel_id:
        return []
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            feed = r.read().decode("utf-8", "replace")
    except OSError:
        return []
    import re
    import time as _time
    cutoff = _time.time() - min_age_days * 86400
    views = []
    for entry in re.findall(r"<entry>(.*?)</entry>", feed, re.S):
        pub = re.search(r"<published>(\d{4})-(\d{2})-(\d{2})", entry)
        if pub:
            y, mo, d = (int(g) for g in pub.groups())
            if _time.mktime((y, mo, d, 0, 0, 0, 0, 0, -1)) > cutoff:
                continue
        m = re.search(r'views="(\d+)"', entry)
        if m and int(m.group(1)) > 0:
            views.append(int(m.group(1)))
    return views


def video_metadata(video_id, max_comments=12):
    """Full single-video metadata incl. description, tags, chapters, top comments."""
    data = _ytdlp_json([
        "--skip-download", "--write-comments",
        "--extractor-args",
        f"youtube:comment_sort=top;max_comments={max_comments},{max_comments},0,0",
        f"https://www.youtube.com/watch?v={video_id}",
    ], timeout=180)
    if not data:
        return None
    comments = [{"text": (c.get("text") or "")[:500],
                 "likes": c.get("like_count") or 0}
                for c in (data.get("comments") or [])[:max_comments]]
    return {
        "id": data["id"],
        "title": data.get("title") or "",
        "channel": data.get("channel") or "",
        "channel_id": data.get("channel_id"),
        "channel_follower_count": data.get("channel_follower_count"),
        "upload_date": data.get("upload_date"),
        "duration_s": data.get("duration"),
        "view_count": data.get("view_count"),
        "like_count": data.get("like_count"),
        "comment_count": data.get("comment_count"),
        "description": (data.get("description") or "")[:3000],
        "tags": data.get("tags") or [],
        "chapters": [{"title": c.get("title"), "start_s": c.get("start_time")}
                     for c in (data.get("chapters") or [])],
        "thumbnail_url": data.get("thumbnail"),
        "comments": comments,
    }


def download_transcript(video_id, dest_dir: Path):
    """Auto-caption transcript → plain text with [m:ss] markers each ~30s.
    Returns the txt path or None."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_tpl = str(dest_dir / f"{video_id}.%(ext)s")
    cmd = [YTDLP, "--no-warnings", "--ignore-config", "--skip-download",
           "--write-auto-subs", "--write-subs", "--sub-langs", "en.*,en",
           "--sub-format", "json3", "-o", out_tpl,
           f"https://www.youtube.com/watch?v={video_id}"]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return None
    sub = next(iter(dest_dir.glob(f"{video_id}*.json3")), None)
    if not sub:
        return None
    try:
        events = json.loads(sub.read_text()).get("events", [])
    except (json.JSONDecodeError, OSError):
        return None
    words, last_mark = [], -30.0
    for ev in events:
        t = (ev.get("tStartMs") or 0) / 1000.0
        for seg in ev.get("segs") or []:
            w = (seg.get("utf8") or "").replace("\n", " ").strip()
            if not w:
                continue
            if t - last_mark >= 30.0:
                words.append(f"\n[{int(t // 60)}:{int(t % 60):02d}]")
                last_mark = t
            words.append(w)
    if not words:
        return None
    txt = dest_dir / f"{video_id}.txt"
    txt.write_text(" ".join(words).strip())
    for leftover in dest_dir.glob(f"{video_id}*.json3"):
        leftover.unlink()
    return str(txt)


def download_thumbnail(url, dest: Path):
    if not url:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            dest.write_bytes(r.read())
        return str(dest)
    except OSError:
        return None
