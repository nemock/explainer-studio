"""substack.py — post the companion article to Substack as a DRAFT, with the video embedded.

Operator request 2026-11-11: once a deep dive is uploaded and `package/meta.json` carries
its `youtube_url`, the article goes to Substack as a draft the operator reads through and
publishes by hand. This is a close-out step, operator-invoked like `publish` and `promote`.
It NEVER publishes: no code path here calls `publish_draft`, and the draft's audience,
email and comment settings are left at Substack's defaults for the operator to set.

What it builds, from `package/article.md`:
  * title    <- front matter `title`
  * subtitle <- front matter `dek`
  * body     <- the markdown, converted to Substack's ProseMirror document, with a YouTube
                embed (`youtube2`) placed right BEFORE THE FIRST SUBHEADING, so a reader
                gets the opening paragraphs first and then the video. That is where the
                operator has always put it by hand (#79's post is the reference). An article
                with no subheading gets the embed after its third paragraph.
  * quotes   <- straight quotes and apostrophes in the title, subtitle and body are curled
                (operator 2026-11-14), matching what Substack's editor does as you type.
  * tags     <- front matter `substack_tags` (a list), or `--tag` on the command line.
                Tags must already exist on the publication unless `--allow-new-tags`:
                Substack creates a tag on first use, so a typo would become a junk tag.

HOW IT TALKS TO SUBSTACK: through the same `substack-mcp` server Claude Code uses, spawned
over stdio with the command, args and env recorded in ~/.claude.json `mcpServers.substack`.
One source of credentials, and a body that never passes through a model's hands: the
document goes to the server as JSON straight from this file, validated by the server
against its own schema.

Dry-run by DEFAULT (writes `package/substack_draft.json` and reports the plan, including the
publication's tag list); `--fire` creates the draft, tags it, reads it back to verify the
embed position, and records `substack_draft_id` + `substack_draft_url` in meta.json. A second
`--fire` refuses while meta.json records a draft, unless `--redraft`.
"""
import json
import os
import re
import select
import subprocess
import time
from pathlib import Path

PUBLICATION_FALLBACK = "https://nemock.substack.com"
CLAUDE_CONFIG = Path.home() / ".claude.json"
PAYLOAD_NAME = "substack_draft.json"
NO_HEADING_FALLBACK_PARAGRAPHS = 3
# Longest `dek` (sent as the Substack subtitle) the dry run lets through. EMPIRICAL, not a
# published figure: on 2026-11-12 a 321-character subtitle made `create_draft_post` fail with
# a bare "400 Bad Request", and the same draft went through with a 202-character one. Substack
# documents no subtitle limit and substack-mcp enforces none, so this is a conservative cap
# between the two observations. Raise it only on evidence of a longer subtitle succeeding.
SUBTITLE_MAX_CHARS = 250


# ----------------------------------------------------------------------------- article

def split_front_matter(text):
    """Return (front_matter_dict, body_markdown). The article's front matter is simple YAML."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    import yaml
    raw = text[3:end]
    try:
        fm = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        # Older articles carry an unquoted dek with a colon in it, which is not valid YAML.
        fm = {}
        for ln in raw.splitlines():
            k, sep, v = ln.partition(":")
            if sep and re.fullmatch(r"[a-z_]+", k.strip()):
                v = v.strip()
                fm[k.strip()] = v[1:-1] if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'" else v
        fm["humanized"] = str(fm.get("humanized", "")).lower() == "true"
    return (fm if isinstance(fm, dict) else {}), text[end + 4:].lstrip("\n")


def strip_leading_h1(body):
    """Some articles repeat the title as a leading `# H1`, and Substack already shows the
    title. Return (h1_text_or_None, body_without_it)."""
    m = re.match(r"\A\s*#\s+([^\n]*)\n+", body)
    return (m.group(1).strip(), body[m.end():]) if m else (None, body)


def video_id(url):
    """youtu.be/<id>, youtube.com/watch?v=<id>, /shorts/<id>, /embed/<id>, or a bare id."""
    url = (url or "").strip()
    for pat in (r"youtu\.be/([A-Za-z0-9_-]{11})", r"[?&]v=([A-Za-z0-9_-]{11})",
                r"/(?:shorts|embed|live)/([A-Za-z0-9_-]{11})"):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url
    return None


# ----------------------------------------------------------------- inline markdown

_URL_RE = re.compile(r"https?://[^\s<>()\[\]*]+")
_TRAILING_PUNCT = ".,;:!?'\""


def _text(s, marks):
    node = {"type": "text", "text": s}
    if marks:
        node["marks"] = [dict(m) for m in marks]
    return node


def _close(s, i, delim):
    """Index of the closing `delim` for an emphasis opened just before i, or -1."""
    j = i
    while True:
        j = s.find(delim, j)
        if j < 0:
            return -1
        if s[j - 1] == "\\":
            j += 1
            continue
        if delim == "*" and s.startswith("**", j):   # a bold run inside an italic run
            k = s.find("**", j + 2)
            if k < 0:
                return -1
            j = k + 2
            continue
        if j > i and not s[j - 1].isspace():
            return j
        j += len(delim)


def inline(s, marks=()):
    """Markdown inline -> list of ProseMirror text nodes. Handles **bold**, *italic*,
    _italic_, `code`, [text](url), bare http(s) URLs and backslash escapes."""
    out, buf, i, n = [], [], 0, len(s)

    def flush():
        if buf:
            out.append(_text("".join(buf), marks))
            buf.clear()

    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n and not s[i + 1].isalnum():
            buf.append(s[i + 1]); i += 2; continue
        if c == "`":
            j = s.find("`", i + 1)
            if j > i:
                flush(); out.append(_text(s[i + 1:j], list(marks) + [{"type": "code"}]))
                i = j + 1; continue
        if c == "[":
            m = re.match(r"\[([^\]]+)\]\(([^)\s]+)\)", s[i:])
            if m:
                flush()
                link = {"type": "link", "attrs": {"href": m.group(2)}}
                out.extend(inline(m.group(1), list(marks) + [link]))
                i += m.end(); continue
        if s.startswith("**", i) and i + 2 < n and not s[i + 2].isspace():
            j = s.find("**", i + 2)
            if j > i + 2:
                flush(); out.extend(inline(s[i + 2:j], list(marks) + [{"type": "strong"}]))
                i = j + 2; continue
        if c in "*_" and i + 1 < n and not s[i + 1].isspace() and s[i + 1] != c:
            # `_` only at a word boundary, so snake_case and URLs stay literal
            if c == "*" or i == 0 or not s[i - 1].isalnum():
                j = _close(s, i + 1, c)
                if j > 0 and (c == "*" or j + 1 >= n or not s[j + 1].isalnum()):
                    flush(); out.extend(inline(s[i + 1:j], list(marks) + [{"type": "em"}]))
                    i = j + 1; continue
        if c == "h" and not any(m["type"] == "link" for m in marks):
            m = _URL_RE.match(s, i)
            if m and (i == 0 or not s[i - 1].isalnum()):
                url = m.group(0).rstrip(_TRAILING_PUNCT)
                flush()
                out.append(_text(url, list(marks) + [{"type": "link", "attrs": {"href": url}}]))
                i += len(url); continue
        buf.append(c); i += 1
    flush()
    return out


# ------------------------------------------------------------------ curly quotes
#
# Operator, 2026-11-14: a draft posted through this tool arrived with straight quotes and
# apostrophes throughout, where Substack's own editor curls them as you type. So the draft
# is curled here, on its way out, rather than relying on how a session typed article.md
# (which may be either). Code and bare URLs are left alone; a link's href is an attribute,
# not text, so it is never touched.

_OPEN_AFTER = set(" \t\n([{<—–-/“‘")


def curl(text, prev=""):
    """Straight -> curly quotes and apostrophes. `prev` is the character before `text`
    (from the previous text node in the same block), so a quote that opens in one node and
    closes in the next still pairs. Returns (curled, last_char)."""
    out = []
    for k, c in enumerate(text):
        before = out[-1] if out else prev
        if c == '"':
            c = "“" if (before == "" or before in _OPEN_AFTER) else "”"
        elif c == "'":
            nxt = text[k + 1] if k + 1 < len(text) else ""
            if before == "" or before in _OPEN_AFTER:
                # '90s and 'em are apostrophes even at a word's start
                c = "’" if nxt.isdigit() else "‘"
            else:
                c = "’"
        out.append(c)
    s = "".join(out)
    return s, (s[-1] if s else prev)


def _is_literal(node):
    marks = node.get("marks") or []
    if any(m.get("type") == "code" for m in marks):
        return True
    return any(m.get("type") == "link" and (m.get("attrs") or {}).get("href") == node.get("text")
               for m in marks)


def curl_tree(nodes):
    """Curl every text node in a ProseMirror node list, in place, block by block."""
    prev = ""
    for node in nodes:
        if node.get("type") == "text":
            if _is_literal(node):
                prev = (node.get("text") or prev)[-1:]
            else:
                node["text"], prev = curl(node.get("text", ""), prev)
        elif node.get("type") != "code_block":
            curl_tree(node.get("content") or [])
            prev = ""
    return nodes


def _para(text):
    content = inline(text.strip())
    return {"type": "paragraph", "content": content} if content else {"type": "paragraph"}


# ------------------------------------------------------------------ block markdown

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^\s{0,3}[-*+]\s+(.*)$")
_ORDERED = re.compile(r"^\s{0,3}(\d+)[.)]\s+(.*)$")
_HR = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")


def _table_rows(lines):
    rows = []
    for ln in lines:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue                       # the |---|---| separator row
        rows.append(cells)
    return rows


def blocks(md, warnings):
    """Markdown -> list of top-level ProseMirror nodes."""
    lines = md.replace("\r\n", "\n").split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]
        if not ln.strip():
            i += 1; continue
        if ln.lstrip().startswith("```"):
            lang = ln.strip()[3:].strip()
            j, code = i + 1, []
            while j < n and not lines[j].lstrip().startswith("```"):
                code.append(lines[j]); j += 1
            node = {"type": "highlighted_code_block",
                    "content": [{"type": "text", "text": "\n".join(code)}]}
            if lang:
                node["attrs"] = {"language": lang.lower()}
            out.append(node); i = j + 1; continue
        m = _HEADING.match(ln)
        if m:
            level = max(2, len(m.group(1)))   # the post title is the only level-1 heading
            out.append({"type": "heading", "attrs": {"level": level},
                        "content": inline(m.group(2).strip())})
            i += 1; continue
        if _HR.match(ln):
            out.append({"type": "horizontal_rule"}); i += 1; continue
        if ln.lstrip().startswith(">"):
            j, inner = i, []
            while j < n and lines[j].lstrip().startswith(">"):
                inner.append(re.sub(r"^\s*>\s?", "", lines[j])); j += 1
            content = blocks("\n".join(inner), warnings)
            content = [c for c in content
                       if c["type"] in ("paragraph", "bullet_list", "ordered_list")] \
                or [{"type": "paragraph"}]
            out.append({"type": "blockquote", "content": content}); i = j; continue
        if ln.lstrip().startswith("|"):
            j = i
            while j < n and lines[j].lstrip().startswith("|"):
                j += 1
            rows = _table_rows(lines[i:j])
            warnings.append(f"table at line {i + 1} has no Substack equivalent; converted to a "
                            "bulleted list (header row in bold). Check it in the editor.")
            if rows:
                out.append({"type": "paragraph", "content": inline(
                    "**" + " · ".join(c for c in rows[0] if c) + "**")})
                out.append({"type": "bullet_list", "content": [
                    {"type": "list_item", "content": [_para(" · ".join(c for c in r if c))]}
                    for r in rows[1:]]})
            i = j; continue
        if _BULLET.match(ln) or _ORDERED.match(ln):
            ordered = bool(_ORDERED.match(ln)) and not _BULLET.match(ln)
            items, j = [], i
            start = int(_ORDERED.match(ln).group(1)) if ordered else 1
            while j < n and lines[j].strip():
                mb, mo = _BULLET.match(lines[j]), _ORDERED.match(lines[j])
                if (mo if ordered else mb):
                    if lines[j].startswith(("    ", "\t")):
                        warnings.append(f"nested list item at line {j + 1} flattened")
                    items.append((mo.group(2) if ordered else mb.group(1)).strip())
                elif mb or mo:
                    break                                  # the list type changed
                elif items:
                    items[-1] += " " + lines[j].strip()     # wrapped continuation line
                j += 1
            node = {"type": "ordered_list" if ordered else "bullet_list",
                    "content": [{"type": "list_item", "content": [_para(t)]} for t in items]}
            if ordered and start != 1:
                node["attrs"] = {"order": start}
            out.append(node); i = j; continue
        j, para = i, []
        while j < n and lines[j].strip() and not (
                _HEADING.match(lines[j]) or _HR.match(lines[j])
                or lines[j].lstrip().startswith((">", "```", "|"))
                or (j > i and (_BULLET.match(lines[j]) or _ORDERED.match(lines[j])))):
            para.append(lines[j].strip()); j += 1
        out.append(_para(" ".join(para))); i = j
    return out


def insert_video(content, vid):
    """Put the youtube2 node before the first subheading; return its index."""
    node = {"type": "youtube2", "attrs": {"videoId": vid, "startTime": None, "endTime": None}}
    first_heading = next((k for k, b in enumerate(content) if b["type"] == "heading"), None)
    paras = [k for k, b in enumerate(content) if b["type"] == "paragraph"]
    if first_heading == 0:
        idx, where = 0, "at the top (the article opens on a subheading)"
    elif first_heading is not None:
        idx, where = first_heading, "before the first subheading"
    elif len(paras) >= NO_HEADING_FALLBACK_PARAGRAPHS:
        idx = paras[NO_HEADING_FALLBACK_PARAGRAPHS - 1] + 1
        where = f"after paragraph {NO_HEADING_FALLBACK_PARAGRAPHS} (the article has no subheading)"
    else:
        idx, where = len(content), "at the end (the article is too short to place it earlier)"
    content.insert(idx, node)
    return idx, where


def _plain(node):
    if node.get("type") == "text":
        return node.get("text", "")
    return "".join(_plain(c) for c in node.get("content", []) or [])


# ---------------------------------------------------------------------- the payload

def _meta_path(proj):
    return Path(proj) / "package" / "meta.json"


def _meta(proj):
    p = _meta_path(proj)
    return json.loads(p.read_text()) if p.exists() else {}


def build_payload(proj, youtube_url=None, tags=None):
    """Read the package and build the draft payload. Returns (payload, problems, warnings)."""
    proj = Path(proj)
    problems, warnings = [], []
    art = proj / "package" / "article.md"
    if not art.exists():
        return None, [f"no article at {art}"], warnings
    fm, body = split_front_matter(art.read_text())
    h1, body = strip_leading_h1(body)
    title = str(fm.get("title") or h1 or "").strip()
    subtitle = str(fm.get("dek") or "").strip()
    if not title:
        problems.append("article.md front matter has no `title`")
    if not subtitle:
        warnings.append("article.md front matter has no `dek`; the draft will have no subtitle")
    elif len(subtitle) > SUBTITLE_MAX_CHARS:
        problems.append(f"article.md `dek` is {len(subtitle)} characters; Substack rejects a "
                        f"subtitle that long with a bare 400. Cut it to {SUBTITLE_MAX_CHARS} or "
                        "fewer (article-playbook §3)")
    if not fm.get("humanized"):
        problems.append("article.md is not marked `humanized: true`; run the humaner pass first "
                        "(SKILL §8b)")
    if "<URL>" in body:
        problems.append("article.md still has a `<URL>` placeholder; put the live link in first")

    url = youtube_url or _meta(proj).get("youtube_url")
    vid = video_id(url)
    if not vid:
        problems.append("no YouTube URL: package/meta.json has no `youtube_url` (run `publish "
                        "--fire` first) and none was passed with --youtube-url")

    if tags is None:
        tags = fm.get("substack_tags") or []
    if isinstance(tags, str):
        tags = [tags]
    tags = [str(t).strip() for t in tags if str(t).strip()]
    if not tags:
        problems.append("no tags: add `substack_tags: [\"...\"]` to article.md front matter "
                        "(3 to 6, picked from the publication's tags; article-playbook §3) or pass --tag")

    title, subtitle = curl(title)[0], curl(subtitle)[0]
    content = curl_tree(blocks(body, warnings))
    embed = None
    if vid:
        idx, where = insert_video(content, vid)
        before = [_plain(b)[:80] for b in content[max(0, idx - 1):idx]]
        after = [_plain(b)[:80] for b in content[idx + 1:idx + 2]]
        embed = {"video_id": vid, "index": idx, "where": where,
                 "paragraphs_before": sum(1 for b in content[:idx] if b["type"] == "paragraph"),
                 "after_text": before[0] if before else None,
                 "before_text": after[0] if after else None}
    counts = {}
    for b in content:
        counts[b["type"]] = counts.get(b["type"], 0) + 1
    payload = {"title": title, "subtitle": subtitle, "tags": tags, "youtube_url": url,
               "embed": embed, "node_counts": counts,
               "body": {"type": "doc", "content": content}}
    return payload, problems, warnings


# ------------------------------------------------------------- MCP stdio client

class McpError(RuntimeError):
    pass


def _server_config():
    if not CLAUDE_CONFIG.exists():
        raise McpError(f"{CLAUDE_CONFIG} not found; the substack MCP server config lives there")
    cfg = json.loads(CLAUDE_CONFIG.read_text()).get("mcpServers", {}).get("substack")
    if not cfg or not cfg.get("command"):
        raise McpError("no `substack` stdio server under mcpServers in ~/.claude.json")
    return cfg


class SubstackMcp:
    """Minimal MCP client: newline-delimited JSON-RPC over the server's stdin/stdout."""

    def __init__(self, timeout=90):
        cfg = _server_config()
        env = dict(os.environ)
        env.update(cfg.get("env") or {})
        self.publication_url = (cfg.get("env") or {}).get("SUBSTACK_PUBLICATION_URL") \
            or PUBLICATION_FALLBACK
        self.timeout = timeout
        self._id = 0
        self.proc = subprocess.Popen([cfg["command"], *cfg.get("args", [])], env=env,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self._request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "explainer2", "version": "1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, msg):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def _request(self, method, params):
        self._id += 1
        rid = self._id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            ready, _, _ = select.select([self.proc.stdout], [], [], 1.0)
            if not ready:
                if self.proc.poll() is not None:
                    raise McpError(f"substack MCP server exited (code {self.proc.returncode})")
                continue
            line = self.proc.stdout.readline()
            if not line:
                raise McpError("substack MCP server closed its output")
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get("id") != rid:
                continue                       # a notification or a stray reply
            if "error" in msg:
                raise McpError(f"{method}: {msg['error'].get('message')}")
            return msg.get("result") or {}
        raise McpError(f"{method}: no reply within {self.timeout}s")

    def call(self, tool, **arguments):
        # Substack answers 429 to a quick run of calls; back off and retry rather than fail
        # halfway through a backfill or between creating a draft and tagging it.
        for wait in (0, 15, 45, 90, 180):
            time.sleep(wait)
            res = self._request("tools/call", {"name": tool, "arguments": arguments})
            text = "".join(c.get("text", "") for c in res.get("content", [])
                           if c.get("type") == "text")
            if not (res.get("isError") and "429" in text):
                break
        if res.get("isError"):
            raise McpError(f"{tool}: {text[:600]}")
        try:
            return json.loads(text)
        except ValueError:
            return {"text": text}

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ------------------------------------------------------------------------- run

def _editor_url(pub_url, draft_id):
    return f"{pub_url.rstrip('/')}/publish/post/{draft_id}"


def _record(proj, draft_id, url, tags):
    p = _meta_path(proj)
    meta = _meta(proj)
    meta["substack_draft_id"] = draft_id
    meta["substack_draft_url"] = url
    meta["substack_tags"] = tags
    p.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")


def _verify(sub, draft_id, payload):
    """Read the draft back: title, subtitle, and the embed sitting where it was put."""
    d = sub.call("get_draft", draft_id=draft_id)
    # Compare the fields themselves. Searching a json.dumps of the draft missed any title or
    # subtitle with a quote mark or a non-ASCII character (#36's dek, #83's "31×"), because
    # dumps escapes them.
    text = json.dumps(d, ensure_ascii=False)
    problems = []
    if payload["title"] and (d.get("draft_title") or "").strip() != payload["title"]:
        problems.append(f"title read back as {d.get('draft_title')!r}")
    if payload["subtitle"] and (d.get("draft_subtitle") or "").strip() != payload["subtitle"]:
        problems.append(f"subtitle read back as {d.get('draft_subtitle')!r}")
    body = d.get("draft_body") or d.get("body")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except ValueError:
            body = None
    if isinstance(body, dict):
        content = body.get("content") or []
        at = [k for k, b in enumerate(content) if b.get("type") == "youtube2"]
        want = payload["embed"]["index"]
        if at != [want]:
            problems.append(f"embed read back at {at}, expected [{want}]")
    elif payload["embed"]["video_id"] not in text:
        problems.append("youtube embed not found on the draft as read back")
    tags = sub.call("get_post_tags", post_id=draft_id)
    have = {t.get("name", "").strip().lower() for t in tags.get("tags", [])}
    missing = [t for t in payload["tags"] if t.lower() not in have]
    if missing:
        problems.append(f"tags missing on the draft: {missing}")
    return problems


def run(project_dir, fire=False, youtube_url=None, tags=None, redraft=False,
        allow_new_tags=False):
    proj = Path(project_dir)
    payload, problems, warnings = build_payload(proj, youtube_url=youtube_url, tags=tags)
    result = {"project": str(proj), "fire": fire, "problems": problems, "warnings": warnings}
    if payload is None:
        result["aborted"] = True
        return result
    out = proj / "package" / PAYLOAD_NAME
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    result.update({"payload": str(out), "title": payload["title"],
                   "subtitle": payload["subtitle"], "tags": payload["tags"],
                   "embed": payload["embed"], "node_counts": payload["node_counts"]})

    meta = _meta(proj)
    if meta.get("substack_draft_id") and not redraft:
        problems.append(f"meta.json already records Substack draft {meta['substack_draft_id']} "
                        f"({meta.get('substack_draft_url')}); pass --redraft to make another")
    chan = (json.loads((proj / "project.json").read_text()).get("youtube_channel")
            if (proj / "project.json").exists() else None)
    if chan and chan != "nemock":
        warnings.append(f"project targets YouTube channel '{chan}', not nemock; the Substack "
                        "publication is Founders Who Finish. Confirm this belongs there.")

    try:
        with SubstackMcp() as sub:
            known = sub.call("list_publication_tags").get("tags", [])
            names = {t["name"].strip().lower(): t["name"].strip() for t in known}
            result["publication_tags"] = sorted(names.values(), key=str.lower)
            new = [t for t in payload["tags"] if t.lower() not in names]
            if new:
                (warnings if allow_new_tags else problems).append(
                    f"tags not on the publication yet: {new}"
                    + ("; they will be created" if allow_new_tags
                       else "; fix the spelling or pass --allow-new-tags"))
            dupes = sub.call("list_posts", status="drafts", search=payload["title"],
                             limit=5).get("posts", [])
            same = [p["id"] for p in dupes
                    if (p.get("draft_title") or p.get("title") or "").strip() == payload["title"]]
            if same and not redraft:
                problems.append(f"Substack already has a draft with this title: {same}; "
                                "pass --redraft to make another")

            result["ready"] = not problems
            if not fire or problems:
                result["aborted"] = bool(problems) and fire
                result["next"] = ("fix the problems above" if problems else
                                  "re-run with --fire to create the draft")
                return result

            made = sub.call("create_draft_post", title=payload["title"],
                            subtitle=payload["subtitle"], body=json.dumps(payload["body"]))
            draft_id = made.get("draft_id")
            if not draft_id:
                raise McpError(f"create_draft_post returned no draft_id: {made}")
            url = _editor_url(sub.publication_url, draft_id)
            _record(proj, draft_id, url, payload["tags"])     # recorded before anything else can fail
            result.update({"draft_id": draft_id, "draft_url": url})
            from . import contentdb
            result["content_index"] = contentdb.refresh_quietly()
            result["tagged"] = [sub.call("add_tag_to_post", post_id=draft_id, tag_name=t,
                                         create_if_missing=allow_new_tags)
                                .get("tag", {}).get("name", t) for t in payload["tags"]]
            result["verify_problems"] = _verify(sub, draft_id, payload)
            result["published"] = False
            result["next"] = ("read it through in the Substack editor, then publish it there "
                              "yourself; this tool never publishes")
            if result["verify_problems"]:
                result["aborted"] = True
            return result
    except McpError as e:
        problems.append(f"substack: {e}")
        result["aborted"] = True
        return result
