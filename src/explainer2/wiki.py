# VENDORED_FROM: nemock/video-explainer-system @ d593aa41dc32d04e3b714b4731b1763f6e31843e (src/explainer/wiki.py) — copied 2026-06-10; diverges freely (v1 is frozen).
"""Atomized knowledge wiki (PRD §8.5) — minimal Phase 1: source + source-fact
nodes with provenance, plus a grep-able INDEX.md. Project-local under wiki/.
operator-take nodes + talk-time mirroring arrive in Phase 3."""
import re, json, hashlib
from datetime import date
from pathlib import Path

TYPES = {"source", "source-fact", "topic"}


def slugify(s, maxlen=48):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return (s[:maxlen]).strip("-") or "node"


def _wiki_dir(root):
    p = Path(root) / "wiki"
    p.mkdir(exist_ok=True)
    return p


def add_node(root, ntype, name, body, **frontmatter):
    if ntype not in TYPES:
        raise ValueError(f"unknown node type: {ntype}")
    wiki = _wiki_dir(root)
    sub = wiki / ntype
    sub.mkdir(exist_ok=True)
    slug = slugify(name)
    # disambiguate collisions deterministically by content hash
    h = hashlib.sha1((name + body).encode()).hexdigest()[:6]
    fname = f"{slug}-{h}.md"
    fm = {"name": slug, "type": ntype, "created": date.today().isoformat(), **frontmatter}
    lines = ["---"]
    for k, v in fm.items():
        lines.append(f"{k}: {json.dumps(v) if not isinstance(v, str) else v}")
    lines += ["---", "", body.strip(), ""]
    (sub / fname).write_text("\n".join(lines))
    rebuild_index(root)
    return str((sub / fname).relative_to(root))


# --- research wiki (references/research-wiki.md, operator directive 2026-08-12) ---
# Facts do NOT live under the Phase-1 project-local wiki/ tree above. They are
# topic-scoped under explainer-content/research/<topic>/<claim>.md so a fact verified
# for one video is available to the next. The node shape below IS the spec; the fields
# are what let a later session tell a primary from a ring of blogs citing each other.

TIERS = ("PRIMARY", "SECONDARY-DIRECT", "SECONDARY-SUMMARY", "INACCESSIBLE")
STATUS_PREFIXES = ("VERIFIED at primary", "VERIFIED (direct quote, named outlet)",
                   "NOT VERIFIED", "RETRACTED")


def add_claim(research_root, topic, claim_id, body, status, source, url,
              source_date, tier, retrieved=None):
    """Write one fact node to explainer-content/research/<topic>/<claim>.md.

    Deterministic filename, so re-running with the same claim_id UPDATES the node
    rather than appending a hash-suffixed duplicate. A knowledge base wants one file
    per claim, not one per time somebody happened to run the command.
    """
    if not topic:
        raise ValueError("a fact node needs --topic; it is the directory the node lives in")
    if tier not in TIERS:
        raise ValueError(f"tier must be one of {', '.join(TIERS)} (got {tier!r})")
    if not status or not status.startswith(STATUS_PREFIXES):
        raise ValueError("status must start with one of: " + " | ".join(STATUS_PREFIXES))
    if not body.strip():
        raise ValueError("a fact node with no body records nothing")

    topic_dir = Path(research_root) / slugify(topic)
    topic_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(claim_id)
    fm = {
        "claim_id": slug,
        "status": status,
        "source": source,
        "url": url,
        "source_date": source_date,
        "retrieved": retrieved or date.today().isoformat(),
        "tier": tier,
    }
    lines = ["---"] + [f"{k}: {v}" for k, v in fm.items()] + ["---", "", body.strip(), ""]
    node = topic_dir / f"{slug}.md"
    node.write_text("\n".join(lines))
    rebuild_research_index(research_root)
    return str(node)


def rebuild_research_index(research_root):
    root = Path(research_root)
    by_topic = {}
    for md in sorted(root.rglob("*.md")):
        if md.name == "INDEX.md":
            continue
        meta, in_fm = {}, False
        for line in md.read_text().splitlines():
            if line.strip() == "---":
                if in_fm:
                    break
                in_fm = True
                continue
            if in_fm and ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
        by_topic.setdefault(md.parent.name, []).append((md, meta))
    out = ["# Research wiki index", "",
           "One file per verified claim, topic-scoped for reuse across videos.",
           "`tier` is the field that earns its keep: SECONDARY-SUMMARY means an outlet",
           "summarizing another outlet.", ""]
    for topic in sorted(by_topic):
        out.append(f"## {topic}")
        out.append("")
        for md, meta in sorted(by_topic[topic], key=lambda t: t[0]):
            rel = md.relative_to(root)
            out.append(f"- [{meta.get('claim_id', md.stem)}]({rel}) — "
                       f"**{meta.get('tier', '?')}** — {meta.get('status', '?')}")
        out.append("")
    (root / "INDEX.md").write_text("\n".join(out) + "\n")
    return sum(len(v) for v in by_topic.values())


def rebuild_index(root):
    wiki = _wiki_dir(root)
    rows = []
    for md in sorted(wiki.rglob("*.md")):
        if md.name == "INDEX.md":
            continue
        first = ""
        for line in md.read_text().splitlines():
            if line and not line.startswith("---") and ":" not in line[:12]:
                first = line.strip()
                break
        rows.append(f"- [{md.stem}]({md.relative_to(wiki)}) — {first[:90]}")
    (wiki / "INDEX.md").write_text("# Wiki index\n\n" + "\n".join(rows) + "\n")
    return len(rows)
