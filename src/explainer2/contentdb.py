"""contentdb.py — a SQLite index of every video project: what it's about and where it went.

Operator request 2026-11-11: one place to ask "have we covered this before?" and "is this
one on YouTube / Substack / LinkedIn yet?" without grepping the projects tree.

THE PROJECT DIRS STAY THE SOURCE OF TRUTH. The database (`channel/content.db`, in the
private explainer-content repo, gitignored) is an index rebuilt from them by `sync`, so it
cannot drift from them and losing it costs nothing. Anything learned from outside (a
Substack post's URL, a LinkedIn post) is written into the project's `package/meta.json`
first and then indexed:

  meta.json key            written by
  ----------------------   ---------------------------------------------------
  youtube_url, posted      `publish --fire`
  substack_draft_id/_url   `substack --fire`
  substack_post_id/_url,   `content substack` (matches Substack posts to videos by
  substack_published_at      the embedded YouTube id, then by exact title)
  linkedin_url,            by hand for now (future: a LinkedIn step)
  linkedin_posted

Where each indexed field comes from:
  title       meta.json `title` (the YouTube title), else blueprint `approved_title`,
              else project.json `title`
  topic, question, angle   intel/blueprint.json
  premise     article.md front matter `dek` (the one-line standfirst)
  subject     the one-liner in channel/CATALOG.md
  keywords    blueprint `seo.keywords` + meta.json `tags`, de-duplicated
  posted      meta.json `posted`, else CATALOG.md's Posted column
Full-text search (`content search`) covers title, topic, question, angle, premise,
subject, keywords and the article body.
"""
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROJECTS = REPO / "projects"
CATALOG = REPO / "channel" / "CATALOG.md"
DB = REPO / "channel" / "content.db"

SCHEMA = """
DROP TABLE IF EXISTS videos;
DROP TABLE IF EXISTS videos_fts;
CREATE TABLE videos (
    number                INTEGER PRIMARY KEY,
    slug                  TEXT NOT NULL,
    project_dir           TEXT NOT NULL,
    created               TEXT,
    content_type          TEXT,
    theme                 TEXT,
    youtube_channel       TEXT,
    title                 TEXT,
    working_title         TEXT,
    topic                 TEXT,
    question              TEXT,
    angle                 TEXT,
    premise               TEXT,
    subject               TEXT,
    keywords              TEXT,     -- JSON list
    produced              INTEGER NOT NULL DEFAULT 0,
    youtube_url           TEXT,
    youtube_id            TEXT,
    youtube_posted        TEXT,
    catalog_status        TEXT,
    shorts                TEXT,     -- JSON list of {slug, title}
    has_article           INTEGER NOT NULL DEFAULT 0,
    article_title         TEXT,
    substack_status       TEXT NOT NULL DEFAULT 'none',   -- none | draft | published
    substack_draft_id     INTEGER,
    substack_draft_url    TEXT,
    substack_post_id      INTEGER,
    substack_url          TEXT,
    substack_published_at TEXT,
    substack_also         TEXT,     -- JSON list: later posts of the same video
    has_linkedin_copy     INTEGER NOT NULL DEFAULT 0,
    linkedin_url          TEXT,
    linkedin_posted       TEXT,
    synced_at             TEXT NOT NULL
);
CREATE VIRTUAL TABLE videos_fts USING fts5(
    number UNINDEXED, title, topic, question, angle, premise, subject, keywords, article
);
"""

_NUM = re.compile(r"^\d{4}-\d{2}-\d{2}_(\d+)_(.+)$")


def _load(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return {}


def _youtube_id(url):
    from .substack import video_id
    return video_id(url) if url else None


def _catalog_rows():
    """`#` -> {subject, status, url, posted} from CATALOG.md's Published / Made table."""
    rows = {}
    if not CATALOG.exists():
        return rows
    for ln in CATALOG.read_text().splitlines():
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 7 or not cells[0].isdigit():
            continue
        rows[int(cells[0])] = {"subject": re.sub(r"\*\*", "", cells[3]).strip() or None,
                               "status": re.sub(r"\*\*", "", cells[4]).strip() or None,
                               "url": cells[5] if "youtu" in cells[5] else None,
                               "posted": cells[6] if re.match(r"\d{4}-\d{2}-\d{2}", cells[6])
                               else None}
    return rows


def project_row(d, catalog):
    """Everything the index knows about one project dir, or None if it isn't a numbered one."""
    m = _NUM.match(d.name)
    if not m:
        return None
    number, slug = int(m.group(1)), m.group(2)
    proj = _load(d / "project.json")
    meta = _load(d / "package" / "meta.json")
    bp = _load(d / "intel" / "blueprint.json")
    cat = catalog.get(number, {})

    fm, article_body = {}, ""
    art = d / "package" / "article.md"
    if art.exists():
        from .substack import split_front_matter, strip_leading_h1
        fm, body = split_front_matter(art.read_text())
        h1, article_body = strip_leading_h1(body)
        fm.setdefault("title", h1)

    keywords = []
    for k in list((bp.get("seo") or {}).get("keywords") or []) + list(meta.get("tags") or []):
        if isinstance(k, str) and k.strip() and k.strip().lower() not in \
                {x.lower() for x in keywords}:
            keywords.append(k.strip())

    youtube_url = meta.get("youtube_url") or (f"https://{cat['url']}" if cat.get("url")
                                              and not cat["url"].startswith("http")
                                              else cat.get("url"))
    if meta.get("substack_post_id") or meta.get("substack_url"):
        sub_status = "published"
    elif meta.get("substack_draft_id"):
        sub_status = "draft"
    else:
        sub_status = "none"
    video_dir = d / "video"
    produced = video_dir.is_dir() and any(video_dir.glob("*.mp4"))
    return {
        "number": number, "slug": slug, "project_dir": d.name,
        "created": d.name[:10], "content_type": proj.get("content_type"),
        "theme": proj.get("theme"), "youtube_channel": proj.get("youtube_channel") or "nemock",
        "title": meta.get("title") or bp.get("approved_title") or proj.get("title"),
        "working_title": proj.get("title"),
        "topic": bp.get("topic"), "question": bp.get("question"), "angle": bp.get("angle"),
        "premise": fm.get("dek"), "subject": cat.get("subject"),
        "keywords": json.dumps(keywords, ensure_ascii=False),
        "produced": int(produced),
        "youtube_url": youtube_url, "youtube_id": _youtube_id(youtube_url),
        "youtube_posted": meta.get("posted") or cat.get("posted"),
        "catalog_status": cat.get("status"),
        "shorts": json.dumps(meta.get("shorts") or [], ensure_ascii=False),
        "has_article": int(art.exists()), "article_title": fm.get("title"),
        "substack_status": sub_status,
        "substack_draft_id": meta.get("substack_draft_id"),
        "substack_draft_url": meta.get("substack_draft_url"),
        "substack_post_id": meta.get("substack_post_id"),
        "substack_url": meta.get("substack_url"),
        "substack_published_at": meta.get("substack_published_at"),
        "substack_also": json.dumps(meta.get("substack_also") or [], ensure_ascii=False),
        "has_linkedin_copy": int((d / "package" / "linkedin.md").exists()),
        "linkedin_url": meta.get("linkedin_url"), "linkedin_posted": meta.get("linkedin_posted"),
        "_article": article_body,
    }


def connect(db=DB):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return con


def sync(db=DB, projects=PROJECTS):
    """Rebuild the whole index from the project dirs. Returns a short summary."""
    catalog = _catalog_rows()
    rows = [r for r in (project_row(d, catalog) for d in sorted(Path(projects).iterdir())
                        if d.is_dir()) if r]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    con = connect(db)
    with con:
        con.executescript(SCHEMA)
        for r in rows:
            article = r.pop("_article")
            r["synced_at"] = now
            cols = ", ".join(r)
            con.execute(f"INSERT INTO videos ({cols}) VALUES ({', '.join('?' * len(r))})",
                        list(r.values()))
            con.execute("INSERT INTO videos_fts (number, title, topic, question, angle, premise,"
                        " subject, keywords, article) VALUES (?,?,?,?,?,?,?,?,?)",
                        (r["number"], r["title"], r["topic"], r["question"], r["angle"],
                         r["premise"], r["subject"], " ".join(json.loads(r["keywords"])),
                         article))
    summary = con.execute("""SELECT count(*) videos, sum(produced) produced,
        sum(youtube_url IS NOT NULL) on_youtube, sum(has_article) articles,
        sum(substack_status='published') substack_published,
        sum(substack_status='draft') substack_drafts,
        sum(linkedin_url IS NOT NULL) on_linkedin FROM videos""").fetchone()
    con.close()
    return {"db": str(db), **dict(summary)}


def refresh_quietly():
    """Re-sync after a verb changed a meta.json. The index is a convenience: a failure here
    is reported, never allowed to fail the upload or draft that called it."""
    try:
        return sync()
    except Exception as e:                      # noqa: BLE001 — see docstring
        return {"error": f"content index not refreshed ({e}); run `explainer2 content sync`"}


def search(query, limit=10, db=DB):
    """Full-text search, best match first. `query` is FTS5 syntax: words, "phrases", OR, NOT."""
    con = connect(db)
    try:
        rows = con.execute("""SELECT v.number, v.title, v.premise, v.youtube_url,
                v.substack_status, snippet(videos_fts, -1, '[', ']', '…', 12) AS hit
            FROM videos_fts JOIN videos v ON v.number = videos_fts.number
            WHERE videos_fts MATCH ? ORDER BY bm25(videos_fts, 0, 10, 6, 4, 4, 5, 4, 8, 1)
            LIMIT ?""", (query, limit)).fetchall()
    except sqlite3.OperationalError:
        # Plain words with punctuation FTS5 can't parse: search them as one phrase.
        rows = con.execute("""SELECT v.number, v.title, v.premise, v.youtube_url,
                v.substack_status, snippet(videos_fts, -1, '[', ']', '…', 12) AS hit
            FROM videos_fts JOIN videos v ON v.number = videos_fts.number
            WHERE videos_fts MATCH ? ORDER BY rank LIMIT ?""",
                           ('"' + query.replace('"', "") + '"', limit)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def show(number, db=DB):
    con = connect(db)
    r = con.execute("SELECT * FROM videos WHERE number = ?", (number,)).fetchone()
    con.close()
    if not r:
        return None
    out = dict(r)
    out["keywords"] = json.loads(out["keywords"] or "[]")
    out["shorts"] = json.loads(out["shorts"] or "[]")
    out["substack_also"] = json.loads(out["substack_also"] or "[]")
    return out


def status(db=DB):
    """One line per video: where it is posted."""
    con = connect(db)
    rows = con.execute("""SELECT number, title, produced, youtube_url IS NOT NULL AS youtube,
            substack_status, linkedin_url IS NOT NULL AS linkedin
        FROM videos ORDER BY number""").fetchall()
    con.close()
    return [dict(r) for r in rows]


# ------------------------------------------------------------ Substack matching

def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower().replace("’", "'")).strip()


FIRST_VIDEO_DATE = "2026-06-10"   # #01; a post older than this can't be a video's article


def _post_video_ids(sub, post):
    """YouTube ids a published post embeds. The cover image names the video when Substack
    took it from the embed; only otherwise is the body fetched, paced, because Substack
    answers 429 to a quick run of reads."""
    from .substack import McpError
    m = re.search(r"/image/youtube/[^/]*/([A-Za-z0-9_-]{11})", post.get("cover_image") or "")
    if m:
        return {m.group(1)}
    if (post.get("post_date") or "")[:10] < FIRST_VIDEO_DATE:
        return set()
    ids = set()
    time.sleep(2)                       # pace the body reads; call() backs off on a 429
    body = sub.call("get_reader_post", post_id=post["id"]).get("body_html") or ""
    ids.update(re.findall(r"youtube2-([A-Za-z0-9_-]{11})", body))
    ids.update(re.findall(r"youtube(?:-nocookie)?\.com/embed/([A-Za-z0-9_-]{11})", body))
    return ids


def match_substack(write=False, projects=PROJECTS):
    """Match the publication's posts to video projects and (with write=True) record the
    Substack facts in each project's meta.json. Published posts match by the YouTube id they
    embed (or their cover image), then by exact title against the article or YouTube title.
    Drafts are matched by `substack_draft_id` already in meta.json, then the same way."""
    from .substack import SubstackMcp, split_front_matter, strip_leading_h1
    vids, titles = {}, {}
    for d in sorted(Path(projects).iterdir()):
        m = _NUM.match(d.name)
        meta_p = d / "package" / "meta.json"
        if not m or not meta_p.exists():
            continue
        meta = _load(meta_p)
        yid = _youtube_id(meta.get("youtube_url"))
        if yid:
            vids[yid] = d
        for t in (meta.get("title"),):
            if t:
                titles[_norm(t)] = d
        art = d / "package" / "article.md"
        if art.exists():
            fm, body = split_front_matter(art.read_text())
            t = fm.get("title") or strip_leading_h1(body)[0]
            if t:
                titles[_norm(t)] = d

    matched, unmatched, changes = [], [], []
    with SubstackMcp() as sub:
        pub_url = sub.publication_url.rstrip("/")
        posts = []
        for status in ("published", "drafts"):
            offset = 0
            while True:
                # 50, not the schema's 100: Substack answers 400 Bad Request above that.
                page = sub.call("list_posts", status=status, limit=50, offset=offset)
                batch = page.get("posts", [])
                posts += [dict(p, _status=status) for p in batch]
                offset += len(batch)
                if not batch or offset >= page.get("total", 0):
                    break
        for p in posts:
            title = p.get("title") or p.get("draft_title") or ""
            d, how = None, None
            ids = _post_video_ids(sub, p) if p["_status"] == "published" else set()
            for i in ids:
                if i in vids:
                    d, how = vids[i], f"embeds {i}"
                    break
            if d is None and _norm(title) in titles:
                d, how = titles[_norm(title)], "title"
            if d is None:
                unmatched.append({"id": p["id"], "status": p["_status"], "title": title,
                                  "video_ids": sorted(ids)})
                continue
            matched.append({"project": d.name, "status": p["_status"], "post_id": p["id"],
                            "title": title, "how": how,
                            "url": f"{pub_url}/p/{p['slug']}" if p["_status"] == "published"
                            else f"{pub_url}/publish/post/{p['id']}",
                            "date": (p.get("post_date") or "")[:10] or None,
                            "_ts": p.get("post_date") or "", "_dir": d})

    # One video can have more than one post (#42 has two). The earliest published one is
    # THE post; any later ones are kept in `substack_also` so nothing is overwritten.
    by_dir = {}
    for m in matched:
        by_dir.setdefault(m["_dir"], []).append(m)
    for d, ms in by_dir.items():
        meta_p = d / "package" / "meta.json"
        meta = _load(meta_p)
        new = {}
        pubs = sorted((m for m in ms if m["status"] == "published"), key=lambda m: m["_ts"])
        if pubs:
            new.update({"substack_post_id": pubs[0]["post_id"], "substack_url": pubs[0]["url"],
                        "substack_published_at": pubs[0]["date"]})
            if len(pubs) > 1:
                new["substack_also"] = [m["url"] for m in pubs[1:]]
        drafts = [m for m in ms if m["status"] == "drafts"]
        if drafts and not pubs:
            new.update({"substack_draft_id": drafts[0]["post_id"],
                        "substack_draft_url": drafts[0]["url"]})
        diff = {k: v for k, v in new.items() if meta.get(k) != v}
        for m in ms:
            m["changes"] = diff
        if diff:
            changes.append(d.name)
            if write:
                meta.update(diff)
                meta_p.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    for m in matched:
        m.pop("_dir"); m.pop("_ts")
    return {"write": write, "posts_seen": len(posts), "matched": matched,
            "projects_changed": changes, "unmatched": unmatched}
