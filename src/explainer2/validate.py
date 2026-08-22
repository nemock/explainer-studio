# VENDORED_FROM: nemock/video-explainer-system @ d593aa41dc32d04e3b714b4731b1763f6e31843e (src/explainer/validate.py) — copied 2026-06-10; diverges freely (v1 is frozen).
"""VALIDATE — check that an output dir's manifest is a complete, consumable handoff
contract (PRD §9) before a downstream poster touches it. Read-only."""
import json
import re

from . import contenttypes

_PKG_DESC = {"meta.json": "upload metadata: title/description/chapters/tags",
             "article.md": "written companion (article-playbook)",
             "linkedin.md": "social-share copy (SKILL §8c)"}


def _package_issues(proj):
    """The Package-step deliverables (SKILL §8). These are authored by the generation
    plane, NOT by any media stage, so nothing else enforces they exist — which is how
    package/linkedin.md slipped through on #16 (2026-07-04). The required set is
    per-content-type (contenttypes.py; unknown types get the strictest set). Skips a
    project that never entered Package (no package/ dir yet)."""
    pkg = proj.dir / "package"
    if not pkg.exists():
        return ["package/ missing — the Package step (meta/thumbnails/article/linkedin) has not run"]
    files, thumbnails = contenttypes.package_requirements(proj.content_type)
    out = []
    for name in files:
        if not (pkg / name).exists():
            out.append(f"package/{name} missing — {_PKG_DESC.get(name, name)}")
    if thumbnails:
        tdir = pkg / "thumbnails"
        for t in ("thumb_a.png", "thumb_b.png"):
            if not (tdir / t).exists():
                out.append(f"package/thumbnails/{t} missing — two thumbnails are standard (a = live, b = promo reuse; A/B testing retired 2026-07-26)")
    return out


def _mmss(s):
    """'12:34' or '1:02:03' -> seconds, or None."""
    m = re.fullmatch(r"(?:(\d+):)?(\d?\d):(\d\d)", str(s).strip())
    if not m:
        return None
    h, mm, ss = m.groups()
    return int(h or 0) * 3600 + int(mm) * 60 + int(ss)


def _linkedin_issues(text):
    """SKILL §8c: THREE hook-first options, each a standalone paste carrying the video
    URL, each with 3-5 hashtags."""
    out = []
    opts = re.split(r"^## Option\b", text, flags=re.M)[1:]
    if len(opts) != 3:
        out.append(f"package/linkedin.md has {len(opts)} option(s), SKILL §8c requires 3")
    for i, body in enumerate(opts, 1):
        body = body.split("\n---")[0]
        # a real link, or the documented placeholder for a not-yet-public video
        if not re.search(r"https?://\S+|<URL>", body):
            out.append(f"package/linkedin.md option {i} carries no video URL — each option is a "
                       f"standalone paste and needs the link inside it (SKILL §8c)")
        n = len(re.findall(r"(?<![\w#])#\w+", body))
        if not 3 <= n <= 5:
            out.append(f"package/linkedin.md option {i} has {n} hashtags, SKILL §8c wants 3-5")
    return out


def _meta_issues(meta, manifest):
    """The fields an upload actually consumes, plus the chapter list — invented chapter
    timestamps shipped on #50 (2026-08-03) with the last one past the end of the video."""
    out = []
    for field in ("title", "description", "tags"):
        if not meta.get(field):
            out.append(f"package/meta.json '{field}' is empty — the upload consumes it directly")
    chapters = re.findall(r"^((?:\d+:)?\d?\d:\d\d)\s+\S", meta.get("description", ""), flags=re.M)
    if chapters:
        secs = [_mmss(c) for c in chapters]
        if secs[0] != 0:
            out.append(f"package/meta.json first chapter is {chapters[0]}, YouTube requires 00:00")
        dur = _mmss(meta.get("duration")) or _mmss((manifest.get("status") or {}).get("duration"))
        if dur:
            past = [c for c, s in zip(chapters, secs) if s is not None and s >= dur]
            if past:
                out.append(f"package/meta.json chapter(s) {', '.join(past)} start at or past the "
                           f"video's {meta.get('duration')} runtime")
        if any(a is not None and b is not None and b <= a for a, b in zip(secs, secs[1:])):
            out.append("package/meta.json chapter timestamps are not strictly increasing")
    return out


def _article_issues(text):
    """article-playbook §3/§5. Returns (issues, advisories): front matter and the humanizer
    gate are structural and block; the word band is written "~1,800-2,500" in the playbook,
    so it advises rather than blocks. A deliberate variant declares `length_variant:`."""
    out, advise = [], []
    if not text.startswith("---"):
        out.append("package/article.md has no front-matter block (article-playbook §3)")
        return out, advise
    fm, _, body = text[3:].partition("---")
    if not re.search(r"^humanized:\s*true\s*$", fm, flags=re.M):
        out.append("package/article.md front matter is not `humanized: true` — the mandatory "
                   "humanizer pass is the step's gate (article-playbook §5)")
    if not re.search(r"^length_variant:", fm, flags=re.M):
        n = len(re.findall(r"\b[\w'$%]+\b", body))
        if not 1800 <= n <= 2500:
            advise.append(f"package/article.md is {n} words, outside the faithful-companion band of "
                       f"1800-2500 (article-playbook §3). Deliberate variant? add "
                       f"`length_variant: <condensed|expanded>` to the front matter")
    return out, advise


def _package_content_issues(proj, manifest):  # -> (issues, advisories)
    """Existence is not compliance. _package_issues only asks whether the four files are
    THERE; these read what is in them. Added 2026-08-03 after #50 shipped a linkedin.md
    with one option and no link, and a meta.json whose invented chapters ran past the end
    of the video — validate returned ok on both."""
    pkg = proj.dir / "package"
    files, _ = contenttypes.package_requirements(proj.content_type)
    out, advise = [], []
    if "linkedin.md" in files and (pkg / "linkedin.md").exists():
        out += _linkedin_issues((pkg / "linkedin.md").read_text())
    if "article.md" in files and (pkg / "article.md").exists():
        a_iss, a_adv = _article_issues((pkg / "article.md").read_text())
        out += a_iss; advise += a_adv
    if "meta.json" in files and (pkg / "meta.json").exists():
        try:
            out += _meta_issues(json.loads((pkg / "meta.json").read_text()), manifest)
        except json.JSONDecodeError as e:
            out.append(f"package/meta.json is not valid JSON: {e}")
    return out, advise


def run(proj):
    issues = []
    mp = proj.dir / "manifest.json"
    if not mp.exists():
        return {"ok": False, "issues": ["manifest.json missing — run `explainer media` first"]}
    m = json.loads(mp.read_text())

    if not m.get("schema_version"):
        issues.append("missing schema_version")
    if not m.get("ai_disclosure"):
        issues.append("missing ai_disclosure block")
    # NOTE: deck/index.html is a deck-engine intermediate, NOT a handoff deliverable,
    # and the remotion (default) engine never produces it — so it is not required.
    # The rendered video (checked below) is the real artifact.

    vids = m.get("video", {})
    if not vids:
        issues.append("no video outputs in manifest")
    for asp, rel in vids.items():
        if not (proj.dir / rel).exists():
            issues.append(f"video file missing on disk: {rel}")
    for kind in ("srt", "vtt"):
        rel = m.get("captions", {}).get(kind)
        if rel and not (proj.dir / rel).exists():
            issues.append(f"caption file missing: {rel}")

    for pp in m.get("per_platform", []):
        plat = pp.get("platform", "?")
        asp = pp.get("aspect")
        if asp and asp not in vids:
            issues.append(f"per_platform '{plat}' wants aspect {asp} which was not rendered")
        if not pp.get("caption"):
            issues.append(f"per_platform '{plat}' has no caption")

    issues += _package_issues(proj)
    content_issues, advisories = _package_content_issues(proj, m)
    issues += content_issues

    # Does every slide actually show something? Checked against the BUILT SPEC, because
    # the 2026-08-12 blank-slide bug lived in the deck -> spec translation and was
    # invisible to every gate that read deck.json. See slidecheck.py.
    from . import slidecheck
    blank, overlong = slidecheck.run(proj)
    issues += blank
    advisories += overlong

    status = m.get("status", {})
    if status.get("ready_for_post") and issues:
        issues.append("ready_for_post=true but the above issues exist — inconsistent")

    ok = not issues
    result = {"ok": ok, "issues": issues}
    if advisories:                      # never affect `ok` — worth reading, not worth blocking
        result["advisories"] = advisories
    proj.write_json(proj.work / "validate.json", result)
    return result
