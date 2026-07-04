# VENDORED_FROM: nemock/video-explainer-system @ d593aa41dc32d04e3b714b4731b1763f6e31843e (src/explainer/validate.py) — copied 2026-06-10; diverges freely (v1 is frozen).
"""VALIDATE — check that an output dir's manifest is a complete, consumable handoff
contract (PRD §9) before a downstream poster touches it. Read-only."""
import json


def _package_issues(proj):
    """The Package-step deliverables (SKILL §8). These are authored by the generation
    plane, NOT by any media stage, so nothing else enforces they exist — which is how
    package/linkedin.md slipped through on #16 (2026-07-04). A complete handoff needs
    all of them. Skips a project that never entered Package (no package/ dir yet)."""
    pkg = proj.dir / "package"
    if not pkg.exists():
        return ["package/ missing — the Package step (meta/thumbnails/article/linkedin) has not run"]
    out = []
    for name, desc in (("meta.json", "upload metadata: title/description/chapters/tags"),
                       ("article.md", "written companion (article-playbook)"),
                       ("linkedin.md", "social-share copy (SKILL §8c)")):
        if not (pkg / name).exists():
            out.append(f"package/{name} missing — {desc}")
    tdir = pkg / "thumbnails"
    for t in ("thumb_a.png", "thumb_b.png"):
        if not (tdir / t).exists():
            out.append(f"package/thumbnails/{t} missing — the A/B thumbnail pair is standard")
    return out


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

    status = m.get("status", {})
    if status.get("ready_for_post") and issues:
        issues.append("ready_for_post=true but the above issues exist — inconsistent")

    ok = not issues
    proj.write_json(proj.work / "validate.json", {"ok": ok, "issues": issues})
    return {"ok": ok, "issues": issues}
