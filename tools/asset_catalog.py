#!/usr/bin/env python3
"""asset_catalog.py — one index across every papercraft asset library.

WHY THIS EXISTS (2026-08-09, operator direction). Magnific-built paper assets are
generated per world and recorded in that world's own `provenance.json`. That is fine for
provenance and disclosure, and useless for the question that actually costs money:

    "have we already built one of these?"

Thirteen libraries, twelve provenance files, no way to search across them. The result is
paying to regenerate a paper coffee mug that already exists two directories over, and a
growing pile of assets nobody remembers. Reusable assets are only reusable if they are
findable.

So: this tool indexes every library, makes them searchable by role, and reports which
assets decks actually use. Run `search` BEFORE generating anything.

    asset_catalog.py index                      refresh the catalog
    asset_catalog.py search coffee mug          do we already have one?
    asset_catalog.py search --library fwf desk  scope to one world
    asset_catalog.py audit                      drift: orphans, missing files, no provenance
    asset_catalog.py usage --days 60            what decks reference, and what sits idle
    asset_catalog.py show papercraft-fwf        everything in one library

The catalog is DERIVED — regenerate it, never hand-edit it. `provenance.json` stays the
source of truth for what an asset is and how it was made.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PUBLIC = Path("/Volumes/Casima/claudeCode/explainer2/remotion/public")
CATALOG = Path("/Volumes/Casima/claudeCode/explainer2/library/asset_catalog.json")
WATCHER_SHOWS = Path("/Volumes/Casima/claudeCode/make_money/recording_watcher/shows.json")
EXTRA_OUTPUTS = [Path("/Volumes/Casima/claudeCode/cvg-explainer/outputs")]

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
# provenance dicts keep their assets under one or more of these keys
ASSET_KEYS = ("assets", "sets", "props", "marks")


# --------------------------------------------------------------------------- index

def _libraries() -> list[Path]:
    return sorted(p for p in PUBLIC.glob("papercraft*") if p.is_dir())


def _load_provenance(lib: Path) -> dict:
    f = lib / "provenance.json"
    if not f.is_file():
        return {}
    try:
        d = json.loads(f.read_text())
    except ValueError:
        return {}
    return d if isinstance(d, dict) else {"assets": d}


def _disk_images(lib: Path) -> list[str]:
    out = []
    for p in sorted(lib.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMAGE_EXT:
            out.append(str(p.relative_to(lib)))
    return out


def build_index() -> dict:
    libs = {}
    for lib in _libraries():
        prov = _load_provenance(lib)
        entries = {}
        for key in ASSET_KEYS:
            for a in prov.get(key, []) or []:
                if not isinstance(a, dict) or not a.get("file"):
                    continue
                rel = a["file"]
                entries[rel] = {
                    "file": rel,
                    "ref": f"{lib.name}/{rel}",          # how a deck references it
                    "kind": key.rstrip("s"),
                    "role": a.get("role", ""),
                    "creation": a.get("creation", ""),
                    "cutout_creation": a.get("cutout_creation", ""),
                    "on_disk": (lib / rel).is_file(),
                }
        disk = _disk_images(lib)
        for rel in disk:
            if rel not in entries:
                entries[rel] = {"file": rel, "ref": f"{lib.name}/{rel}", "kind": "unrecorded",
                                "role": "", "creation": "", "cutout_creation": "", "on_disk": True}
        libs[lib.name] = {
            "library": lib.name,
            "has_provenance": bool(prov),
            "world": prov.get("world", ""),
            "style": prov.get("style", ""),
            "style_anchor": prov.get("style_anchor", {}),
            "recipe_for_additions": prov.get("recipe_for_additions", ""),
            "assets": sorted(entries.values(), key=lambda e: (e["kind"], e["file"])),
        }
    libs["episode-art"] = _episode_art()
    return {"generated": datetime.now().astimezone().isoformat(timespec="seconds"),
            "public_root": str(PUBLIC), "libraries": libs}


def _episode_art() -> dict:
    """Per-episode Magnific art (`<proj>/assets/imagegen/`) as a pseudo-library.

    Daily one-off art is legitimate and encouraged, but until now it lived only inside the
    episode that commissioned it, so nothing generated yesterday could be found today. That
    is the expensive half of the reuse problem: the sets Circumvent made for a landfill and
    a cornfield are perfectly good assets that no later episode can see. Indexing them here
    makes a one-off a candidate for reuse without moving any files.
    """
    entries = {}
    for root in _outputs_roots():
        for proj in sorted(root.iterdir()):
            art = proj / "assets" / "imagegen"
            if not (proj.is_dir() and art.is_dir()):
                continue
            prompts = {}
            prov = art / "provenance.json"
            if prov.is_file():
                try:
                    for r in json.loads(prov.read_text()):
                        if isinstance(r, dict) and r.get("file"):
                            prompts[Path(r["file"]).name] = r.get("prompt") or ""
                except ValueError:
                    pass
            for p in sorted(art.iterdir()):
                if not (p.is_file() and p.suffix.lower() in IMAGE_EXT):
                    continue
                ref = f"{proj.name}/assets/imagegen/{p.name}"
                entries[ref] = {
                    "file": ref, "ref": ref, "kind": "episode",
                    # the generation prompt is the only description a one-off ever gets,
                    # so it doubles as the searchable role text
                    "role": (prompts.get(p.name, "") or "")[:240],
                    "creation": "", "cutout_creation": "", "on_disk": True,
                    "episode": proj.name, "path": str(p),
                }
    return {"library": "episode-art", "has_provenance": True,
            "world": "Per-episode one-off Magnific art, indexed across every show's outputs. "
                     "Reuse candidates: copy into a world library and record it there.",
            "style": "", "style_anchor": {}, "recipe_for_additions": "",
            "assets": sorted(entries.values(), key=lambda e: e["file"])}


def load_catalog(rebuild: bool = False) -> dict:
    if rebuild or not CATALOG.is_file():
        cat = build_index()
        CATALOG.parent.mkdir(parents=True, exist_ok=True)
        CATALOG.write_text(json.dumps(cat, indent=2) + "\n")
        return cat
    return json.loads(CATALOG.read_text())


def _all_assets(cat: dict, library: str = "") -> list[dict]:
    out = []
    for name, lib in cat["libraries"].items():
        if library and library not in name:
            continue
        for a in lib["assets"]:
            out.append({**a, "library": name})
    return out


# --------------------------------------------------------------------------- usage

def _outputs_roots() -> list[Path]:
    roots = []
    try:
        cfg = json.loads(WATCHER_SHOWS.read_text())
        roots = [Path(s["outputs_dir"]) for s in cfg.get("shows", []) if s.get("outputs_dir")]
    except (OSError, ValueError):
        pass
    return [r for r in roots + EXTRA_OUTPUTS if r.is_dir()]


DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def _deck_refs(deck: dict) -> list[str]:
    """Every library asset a deck references: set backdrops, props, and the CTA mark."""
    refs = []
    for s in deck.get("slides", []) or []:
        for key in ("set", "mark", "image"):
            v = s.get(key)
            if isinstance(v, str) and v:
                refs.append(v)
        for p in s.get("props", []) or []:
            if isinstance(p, dict) and p.get("image"):
                refs.append(p["image"])
    return refs


def collect_usage(days: int | None = None) -> dict:
    cutoff = (date.today() - timedelta(days=days)).isoformat() if days else None
    usage: dict[str, list[str]] = {}
    episodes = 0
    for root in _outputs_roots():
        for proj in sorted(root.iterdir()):
            if not proj.is_dir():
                continue
            m = DATE_RE.match(proj.name)
            if not m or (cutoff and m.group(1) < cutoff):
                continue
            deck_f = proj / "deck.json"
            if not deck_f.is_file():
                continue
            try:
                deck = json.loads(deck_f.read_text())
            except ValueError:
                continue
            episodes += 1
            for ref in _deck_refs(deck):
                # Episode art is referenced project-relatively ("assets/imagegen/x.png");
                # the catalog keys it by project so two shows' one-offs never collide.
                if ref.startswith("assets/"):
                    ref = f"{proj.name}/{ref}"
                usage.setdefault(ref, []).append(f"{m.group(1)} {proj.name}")
    return {"episodes_scanned": episodes, "usage": usage}


# --------------------------------------------------------------------------- commands

def cmd_index(args) -> int:
    cat = load_catalog(rebuild=True)
    n = sum(len(l["assets"]) for l in cat["libraries"].values())
    print(f"indexed {len(cat['libraries'])} libraries, {n} assets -> {CATALOG}")
    for name, lib in cat["libraries"].items():
        flag = "" if lib["has_provenance"] else "   [NO provenance.json]"
        print(f"  {name:24} {len(lib['assets']):3} assets{flag}")
    return 0


def cmd_search(args) -> int:
    cat = load_catalog()
    terms = [t.lower() for t in args.terms]
    if not terms:
        print("search: give at least one term")
        return 1
    hits = []
    for a in _all_assets(cat, args.library):
        hay = f"{a['library']} {a['file']} {a['role']}".lower()
        score = sum(1 for t in terms if t in hay)
        if score:
            hits.append((score, a))
    if not hits:
        print(f"NO MATCH for {' '.join(terms)}")
        print("Nothing in the libraries covers this — generating a new asset is justified.")
        print("Record it in the world's provenance.json, then re-run `asset_catalog.py index`.")
        return 0
    hits.sort(key=lambda h: (-h[0], h[1]["library"], h[1]["file"]))
    print(f"{len(hits)} match(es) for {' '.join(terms)} — REUSE before generating:\n")
    for score, a in hits[: args.limit]:
        miss = "" if a["on_disk"] else "  [MISSING ON DISK]"
        print(f"  {a['ref']}{miss}")
        if a["role"]:
            print(f"      {a['role']}")
    return 0


def cmd_show(args) -> int:
    cat = load_catalog()
    lib = cat["libraries"].get(args.library)
    if not lib:
        near = [n for n in cat["libraries"] if args.library in n]
        print(f"no library '{args.library}'" + (f"; did you mean {near}?" if near else ""))
        return 1
    print(f"# {lib['library']}")
    if lib["world"]:
        print(f"\n{lib['world']}\n")
    for a in lib["assets"]:
        print(f"  [{a['kind']:11}] {a['file']}")
        if a["role"]:
            print(f"                {a['role']}")
    if lib["recipe_for_additions"]:
        print(f"\nrecipe for additions:\n  {lib['recipe_for_additions']}")
    return 0


def cmd_audit(args) -> int:
    cat = load_catalog(rebuild=True)
    no_prov, missing, unrecorded = [], [], []
    for name, lib in cat["libraries"].items():
        if not lib["has_provenance"]:
            no_prov.append(name)
        for a in lib["assets"]:
            if not a["on_disk"]:
                missing.append(a["ref"])
            elif a["kind"] == "unrecorded":
                unrecorded.append(a["ref"])
    print("# asset audit\n")
    print(f"libraries with no provenance.json ({len(no_prov)}):")
    for n in no_prov:
        print(f"  {n}")
    print(f"\nprovenance entries with no file on disk ({len(missing)}):")
    for r in missing:
        print(f"  {r}")
    print(f"\nfiles on disk with no provenance entry ({len(unrecorded)}):")
    for r in unrecorded:
        print(f"  {r}")
    print("\nUnrecorded files are the real risk: an asset nobody can trace is an asset "
          "nobody will reuse, and it has no disclosure record.")
    return 2 if (no_prov or missing or unrecorded) else 0


def cmd_usage(args) -> int:
    cat = load_catalog()
    u = collect_usage(args.days)
    counts = {ref: len(eps) for ref, eps in u["usage"].items()}
    known = {a["ref"]: a for a in _all_assets(cat)}
    window = f"last {args.days}d" if args.days else "all time"
    print(f"# deck usage ({window}, {u['episodes_scanned']} episodes with a deck.json)\n")

    used = sorted(((c, r) for r, c in counts.items()), reverse=True)
    print("most-used references:")
    for c, r in used[: args.limit]:
        tag = "" if r in known else "   [not a catalog asset]"
        print(f"  {c:3}x  {r}{tag}")

    idle = sorted(ref for ref in known if ref not in counts and known[ref]["kind"] != "unrecorded")
    print(f"\ncatalogued assets never referenced in this window ({len(idle)}):")
    for r in idle:
        role = known[r]["role"]
        print(f"  {r}" + (f"\n      {role}" if role else ""))
    print("\nIdle assets are reuse candidates, not waste — check here before paying for a new one.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("index", help="rebuild the catalog from every library's provenance + disk")
    s.set_defaults(func=cmd_index)

    s = sub.add_parser("search", help="find an existing asset BEFORE generating a new one")
    s.add_argument("terms", nargs="*")
    s.add_argument("--library", default="", help="restrict to libraries matching this substring")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("show", help="list one library in full")
    s.add_argument("library")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("audit", help="orphans, missing files, libraries with no provenance")
    s.set_defaults(func=cmd_audit)

    s = sub.add_parser("usage", help="what decks actually reference, and what sits idle")
    s.add_argument("--days", type=int, default=None)
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_usage)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
