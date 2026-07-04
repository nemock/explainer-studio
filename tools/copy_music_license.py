#!/usr/bin/env python3
"""Copy the background-music license into a project directory.

Monetization-readiness (operator directive 2026-07-04): every project that uses
a background-music track must carry a LOCAL copy of that track's license
certificate, so the operator can act on all of them if/when the channel enters
the YouTube Partner Program. The music itself lives in the shared
`library/music/` and is referenced by `project.json.music`; this tool copies the
matching `*-license.txt` next to the project.

Matching: the Pixabay track ID is the trailing number in both the mp3 filename
and its license filename (e.g. `...-548620.mp3` <-> `...-548620-license.txt`),
so we match on that ID rather than the (differing) name prefixes.

Usage:
  python3 tools/copy_music_license.py <project_dir>     # one project
  python3 tools/copy_music_license.py --all             # every project under projects/
  python3 tools/copy_music_license.py --all --projects-dir <dir>
"""
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MUSIC_LIB = REPO / "library" / "music"


def _track_id(name: str):
    """Trailing Pixabay-style numeric id, e.g. '...-548620.mp3' -> '548620'."""
    m = re.search(r"(\d{4,})(?=\.[A-Za-z0-9]+$|$)", Path(name).stem + Path(name).suffix)
    # simpler: last run of >=4 digits anywhere in the stem
    ids = re.findall(r"\d{4,}", Path(name).stem)
    return ids[-1] if ids else None


def _license_for(track_path: str):
    """Find the license .txt in the library whose filename carries the same id."""
    tid = _track_id(track_path)
    if not tid:
        return None, None
    for lic in sorted(MUSIC_LIB.glob("*.txt")):
        if "licen" in lic.name.lower() and tid in lic.name:
            return lic, tid
    return None, tid


def copy_for_project(project_dir, log=print):
    proj = Path(project_dir)
    pj = proj / "project.json"
    if not pj.exists():
        log(f"skip {proj.name}: no project.json")
        return False
    try:
        music = json.loads(pj.read_text()).get("music")
    except (OSError, json.JSONDecodeError) as e:
        log(f"skip {proj.name}: bad project.json ({e})")
        return False
    if not music:
        log(f"skip {proj.name}: no music field")
        return False
    lic, tid = _license_for(music)
    if not lic:
        log(f"!! {proj.name}: NO LICENSE found for track id {tid} ({Path(music).name}) — needs manual attention")
        return False
    dest = proj / lic.name
    if dest.exists() and dest.read_bytes() == lic.read_bytes():
        log(f"ok {proj.name}: license already present ({lic.name})")
        return True
    shutil.copy2(lic, dest)
    log(f"COPIED {proj.name}: {lic.name}")
    return True


def main(argv):
    args = argv[1:]
    if not args:
        print(__doc__)
        return 2
    if args[0] == "--all":
        pdir = REPO / "projects"
        if "--projects-dir" in args:
            pdir = Path(args[args.index("--projects-dir") + 1])
        ok = miss = 0
        for pj in sorted(pdir.glob("*/project.json")):
            if copy_for_project(pj.parent):
                ok += 1
            else:
                miss += 1
        print(f"\n{ok} projects have their license; {miss} skipped/unmatched")
        return 0
    return 0 if copy_for_project(args[0]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
