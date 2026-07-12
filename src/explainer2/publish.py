"""publish.py — hybrid YouTube publish for the PRIMARY long-form video.

The generation pipeline stops at the package (PRD boundary). `publish` is a
SEPARATE, operator-invoked step (like `promote`, but for the main video, not the
Shorts) that pushes the finished package to YouTube via the operator's OWN OAuth
against the official YouTube Data API v3 — no third-party SaaS, no per-token
billing, secrets stay local.

HYBRID: the API sets file + core metadata + ONE thumbnail + playlist + schedule.
It CANNOT do A/B thumbnails, title A/B, end screens, or pinned comments (no public
endpoint) — so those print as a Chrome checklist.

MULTI-CHANNEL (the Blotato model, done locally):
  One Google account (nemock@gmail.com) owns several channels — Dave Saunders
  (@nemock), Waveform (@Waveform-fm), Circumvent, etc. There is NO reliable
  "active channel" over the API either, so we DON'T rely on one. Instead:
    * Each channel gets its OWN token file, bound to that channel at OAuth consent
      (you pick the channel on Google's screen). `publish --authorize <key>`.
    * A registry (~/.config/explainer2/channels.json) records each key's real
      channel id + title + handle, captured at authorize time.
    * Each project declares its target channel: project.json "youtube_channel"
      (falls back to --channel, else "nemock").
    * Before every upload the CHANNEL GUARD confirms the loaded token's real
      channel id == the registry id for that key, and ABORTS on mismatch.
  Net: the Binaural generator's projects target "waveform" and can never leak onto
  the main channel; FWF projects target "nemock" and never touch Waveform.

Dry-run by DEFAULT; --fire uploads. --fire defaults to privacyStatus=private.
The google-api-python-client import is LAZY so dry-run needs no deps/creds.
"""
import json
from pathlib import Path

DEFAULT_CATEGORY_ID = "22"        # People & Blogs (override via meta "category_id")
THUMBNAIL_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_CHANNEL = "nemock"        # the FWF / Dave Saunders main channel
SCOPES = ["https://www.googleapis.com/auth/youtube"]


def _cfg_dir():
    p = Path.home() / ".config" / "explainer2"; p.mkdir(parents=True, exist_ok=True); return p

def _registry_path():   return _cfg_dir() / "channels.json"
def _token_path(key):   return _cfg_dir() / f"token_{key}.json"
def _client_secret():   return _cfg_dir() / "client_secret.json"

def load_registry():
    p = _registry_path()
    return json.loads(p.read_text()) if p.exists() else {}

def _save_registry(reg):
    _registry_path().write_text(json.dumps(reg, indent=2))


def resolve_channel(proj, explicit=None):
    """Which channel does this project publish to? explicit > project.json
    'youtube_channel' > default. Returns a channel KEY (e.g. 'waveform')."""
    if explicit:
        return explicit.lstrip("@")
    return (proj.data.get("youtube_channel") or DEFAULT_CHANNEL).lstrip("@")


def _meta(proj):
    p = proj.dir / "package" / "meta.json"
    if not p.exists():
        raise FileNotFoundError(f"no package/meta.json at {p} — run packaging first")
    return json.loads(p.read_text())


# ------------------------------------------------------------------ planning
def build_plan(proj, channel, privacy="private", when=None):
    """Pure: derive the exact API payload + browser checklist. No network/deps."""
    meta = _meta(proj)
    reg = load_registry()
    chan = reg.get(channel)
    warnings, notes = [], []
    if not chan:
        warnings.append(f"channel '{channel}' not authorized yet — run "
                        f"`explainer2 publish --authorize --channel {channel}` before --fire")

    video_rel = meta.get("video", "video/explainer_16x9.mp4")
    video_path = (proj.dir / video_rel).resolve()
    if not video_path.exists():
        warnings.append(f"video file missing: {video_path}")

    title = meta.get("title") or (meta.get("titles_ranked") or [""])[0]
    title_ab = meta.get("title_ab") or []
    alt_title = title_ab[1] if len(title_ab) > 1 and title_ab[1] != title else None

    thumbs = meta.get("thumbnails") or {}
    thumb_a, thumb_b = thumbs.get("a"), thumbs.get("b")
    thumb_a_path = (proj.dir / "package" / thumb_a).resolve() if thumb_a else None
    if thumb_a_path and thumb_a_path.exists():
        sz = thumb_a_path.stat().st_size
        if sz > THUMBNAIL_MAX_BYTES:
            notes.append(f"thumbnail A is {sz/1_048_576:.1f}MB (>2MB) — will be auto-compressed "
                         f"to a <2MB JPEG at upload")
    elif thumb_a:
        warnings.append(f"thumbnail A not found: {thumb_a_path}")

    body = {
        "snippet": {
            "title": title,
            "description": meta.get("description", ""),
            "tags": meta.get("tags", []),
            "categoryId": str(meta.get("category_id", DEFAULT_CATEGORY_ID)),
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": bool(meta.get("made_for_kids", False)),
        },
    }
    if when:
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = when

    return {
        "project": proj.dir.name,
        "target_channel": {"key": channel,
                           "title": (chan or {}).get("title"),
                           "handle": (chan or {}).get("handle"),
                           "id": (chan or {}).get("id"),
                           "authorized": bool(chan)},
        "video_file": str(video_path),
        "api_will_set": {
            "title": title,
            "description_chars": len(meta.get("description", "")),
            "tags": meta.get("tags", []),
            "categoryId": body["snippet"]["categoryId"],
            "privacyStatus": body["status"]["privacyStatus"],
            "publishAt": body["status"].get("publishAt"),
            "madeForKids": body["status"]["selfDeclaredMadeForKids"],
            "playlist": meta.get("playlist"),
            "thumbnail_A": str(thumb_a_path) if thumb_a_path else None,
        },
        "browser_todo": _browser_checklist(meta, thumb_b, alt_title, chan or {"handle": channel}),
        "notes": notes,
        "warnings": warnings,
        "_body": body,
    }


def _browser_checklist(meta, thumb_b, alt_title, chan):
    handle = chan.get("handle") or "the target channel"
    todo = []
    if thumb_b:
        todo.append(f"A/B THUMBNAILS: thumbnail A is set by the API; open Test & Compare, "
                    f"add variant B (package/{thumb_b}), and start the test.")
    if alt_title:
        todo.append(f"TITLE A/B (optional): add the alternate title to Test & Compare — "
                    f"\"{alt_title}\"")
    todo.append("END SCREEN: add subscribe + a video element (Best for viewer) over the last ~20s.")
    pc = meta.get("pinned_comment")
    if pc:
        todo.append(f"PINNED COMMENT: VERIFY the active channel is {handle} (photo avatar, "
                    f"verified badge) before posting, then post + pin:\n    \"{pc}\"")
    todo.append("AI-USE / altered-content: no API field; default 'No' is correct — confirm only.")
    return todo


# ------------------------------------------------------------------ API layer (lazy)
def _flow_imports():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        return InstalledAppFlow, Request, Credentials, build
    except ImportError as e:
        raise SystemExit(
            "publish --fire/--authorize needs the Google client libs. One-time:\n"
            "  ~/myenv/bin/pip install google-api-python-client google-auth-oauthlib\n"
            f"(import error: {e})")


def _service(key, interactive):
    """Authenticated client for channel `key`. interactive=True runs the consent
    flow (used by --authorize); otherwise it only reuses/refreshes a cached token."""
    InstalledAppFlow, Request, Credentials, build = _flow_imports()
    cs, tok = _client_secret(), _token_path(key)
    if not cs.exists():
        raise SystemExit(f"no OAuth client_secret at {cs} — create a Google Cloud OAuth "
                         f"client (Desktop), download it there.")
    creds = Credentials.from_authorized_user_file(str(tok), SCOPES) if tok.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif interactive:
            creds = InstalledAppFlow.from_client_secrets_file(str(cs), SCOPES).run_local_server(port=0)
        else:
            raise SystemExit(f"channel '{key}' not authorized — run "
                             f"`explainer2 publish --authorize --channel {key}` first.")
        tok.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def _thumb_for_upload(path):
    """Return a path to a <2MB thumbnail. If `path` is already under the limit,
    return it unchanged; otherwise write a resized (<=1280x720) JPEG to the
    scratch dir, stepping quality down until it fits. Falls back to the original
    if Pillow isn't available (YouTube will then reject it — surfaced as a warning)."""
    p = Path(path)
    if p.stat().st_size <= THUMBNAIL_MAX_BYTES:
        return str(p), None
    try:
        from PIL import Image
    except ImportError:
        return str(p), "Pillow not installed; could not auto-compress thumbnail (>2MB)"
    img = Image.open(p).convert("RGB")
    img.thumbnail((1280, 720))
    out = _cfg_dir() / f"_thumb_{p.stem}.jpg"
    for q in (90, 85, 80, 72, 65, 55):
        img.save(out, "JPEG", quality=q, optimize=True)
        if out.stat().st_size <= THUMBNAIL_MAX_BYTES:
            return str(out), None
    return str(out), f"thumbnail still {out.stat().st_size/1_048_576:.1f}MB after max compression"


def _video_id_from_meta(proj):
    """Pull the video id out of meta.json's youtube_url (youtu.be/<id> or watch?v=<id>)."""
    import re
    url = _meta(proj).get("youtube_url") or ""
    m = re.search(r"(?:youtu\.be/|[?&]v=)([A-Za-z0-9_-]{6,})", url)
    return m.group(1) if m else None


def set_privacy(video_id=None, project_dir=None, channel=None, privacy="private", when=None):
    """Change the privacy of an ALREADY-uploaded video (the 'validate unlisted, then
    flip public' pattern). Same channel guard as --fire: verifies the loaded token's
    real channel id against the registry before touching the video. Target the video
    by --video-id or by a project dir whose meta.json carries youtube_url."""
    from .project import Project
    proj = None
    if project_dir:
        proj = Project.load(project_dir)
        channel = channel or None
        key = resolve_channel(proj, explicit=channel)
        video_id = video_id or _video_id_from_meta(proj)
    else:
        key = (channel or DEFAULT_CHANNEL).lstrip("@")
    if not video_id:
        return {"aborted": True, "reason": "no video id (pass --video-id, or a project dir "
                "whose package/meta.json has youtube_url)"}
    reg = load_registry()
    if key not in reg:
        return {"aborted": True, "reason": f"channel '{key}' not authorized",
                "fix": f"explainer2 publish --authorize --channel {key}"}
    yt = _service(key, interactive=False)
    live = _channel_of(yt)
    if not live or live["id"] != reg[key]["id"]:
        return {"aborted": True, "reason": "channel guard: token no longer matches registry",
                "expected": reg[key], "got": live}
    cur = yt.videos().list(part="status", id=video_id).execute().get("items", [])
    if not cur:
        return {"aborted": True, "reason": f"video {video_id} not found on channel '{key}' "
                f"({live['title']}) — wrong channel or wrong id?"}
    old = cur[0]["status"]
    # send only writable status fields; publishAt only valid with privacyStatus=private
    status = {"privacyStatus": "private" if when else privacy}
    for f in ("selfDeclaredMadeForKids", "license", "embeddable", "publicStatsViewable"):
        if f in old:
            status[f] = old[f]
    if "selfDeclaredMadeForKids" not in status and "madeForKids" in old:
        status["selfDeclaredMadeForKids"] = old["madeForKids"]
    if when:
        status["publishAt"] = when
    yt.videos().update(part="status", body={"id": video_id, "status": status}).execute()
    return {"ok": True, "video_id": video_id, "channel": live,
            "privacyStatus": status["privacyStatus"], "publishAt": status.get("publishAt")}


def _backfill_meta(proj, url):
    """Close the loop: write youtube_url + posted date into package/meta.json."""
    import datetime
    p = proj.dir / "package" / "meta.json"
    meta = json.loads(p.read_text())
    meta["youtube_url"] = url
    meta["posted"] = datetime.date.today().isoformat()
    p.write_text(json.dumps(meta, indent=2))
    return str(p)


def _channel_of(yt):
    resp = yt.channels().list(part="snippet", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        return None
    c = items[0]
    return {"id": c["id"], "title": c["snippet"]["title"],
            "handle": c["snippet"].get("customUrl", "")}


def authorize(key):
    """Bind channel `key` to a token by running consent (pick the channel on Google's
    screen) and record its real id/title/handle in the registry."""
    yt = _service(key, interactive=True)
    chan = _channel_of(yt)
    if not chan:
        return {"ok": False, "reason": "no channel returned for this token"}
    reg = load_registry(); reg[key] = chan; _save_registry(reg)
    return {"ok": True, "channel_key": key, "bound_to": chan,
            "token": str(_token_path(key)),
            "note": f"'{key}' now permanently targets {chan['title']} ({chan['handle']}). "
                    f"Set project.json \"youtube_channel\": \"{key}\" on projects for this channel."}


# ------------------------------------------------------------------ entry point
def run(project_dir=None, fire=False, privacy="private", when=None,
        channel=None, do_authorize=False):
    # --authorize is project-independent
    if do_authorize:
        key = (channel or DEFAULT_CHANNEL).lstrip("@")
        return authorize(key)

    from .project import Project
    proj = Project.load(project_dir)
    key = resolve_channel(proj, explicit=channel)
    plan = build_plan(proj, key, privacy=privacy, when=when)

    if not fire:
        out = {k: v for k, v in plan.items() if k != "_body"}
        out["dry_run"] = True
        out["note"] = ("DRY RUN. Re-run with --fire to upload. --fire defaults to "
                       "privacyStatus=private; pass --privacy public to go live.")
        return out

    if plan["warnings"]:
        return {"aborted": True, "reason": "warnings present (fix or override)",
                "warnings": plan["warnings"]}

    reg = load_registry()
    if key not in reg:
        return {"aborted": True, "reason": f"channel '{key}' not authorized",
                "fix": f"explainer2 publish --authorize --channel {key}"}

    yt = _service(key, interactive=False)
    live = _channel_of(yt)
    # CHANNEL GUARD: exact channel-ID match against the registry — the hard stop.
    if not live or live["id"] != reg[key]["id"]:
        return {"aborted": True, "reason": "channel guard: token no longer matches registry",
                "expected": reg[key], "got": live,
                "fix": f"re-authorize: explainer2 publish --authorize --channel {key}"}

    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(plan["video_file"], chunksize=-1, resumable=True)
    ins = yt.videos().insert(part="snippet,status", body=plan["_body"], media_body=media)
    resp = None
    while resp is None:
        _s, resp = ins.next_chunk()
    vid = resp["id"]
    result = {"video_id": vid, "youtube_url": f"https://youtu.be/{vid}",
              "uploaded_to": live, "set_via_api": ["title/description/tags/category/privacy/madeForKids"],
              "browser_todo": plan["browser_todo"], "warnings": []}

    ta = plan["api_will_set"]["thumbnail_A"]
    if ta and Path(ta).exists():
        upload_thumb, tw = _thumb_for_upload(ta)
        if tw:
            result["warnings"].append(tw)
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(upload_thumb)).execute()
            tag = Path(ta).name + ("" if upload_thumb == ta else " (auto-compressed)")
            result["set_via_api"].append(f"thumbnail A ({tag})")
        except Exception as e:
            result["warnings"].append(f"thumbnail set failed: {e}")

    pl_name = plan["api_will_set"]["playlist"]
    if pl_name:
        try:
            pls = yt.playlists().list(part="snippet", mine=True, maxResults=50).execute()
            pid = next((p["id"] for p in pls.get("items", [])
                        if p["snippet"]["title"].strip().lower() == pl_name.strip().lower()), None)
            if pid:
                yt.playlistItems().insert(part="snippet", body={"snippet": {
                    "playlistId": pid,
                    "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
                result["set_via_api"].append(f"playlist '{pl_name}'")
            else:
                result["warnings"].append(f"playlist '{pl_name}' not found on this channel")
        except Exception as e:
            result["warnings"].append(f"playlist add failed: {e}")

    result["meta_backfilled"] = _backfill_meta(proj, result["youtube_url"])
    return result
