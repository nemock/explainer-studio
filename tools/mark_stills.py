#!/usr/bin/env python3
"""mark_stills.py — verify figure marks against REAL RENDERED FRAMES.

Replaces the PIL-on-raw-art contact sheet as the mark QC (motion-playbook §2H). That
sheet drew the authored coordinates onto the raw PNG — so it could never catch a bad
coordinate, because it verified the numbers with the same numbers. On #56 the operator
caught three circles missing their subjects in the rendered video after that sheet had
"passed" them. A calibration render proved the RENDERER honest (a mark authored at a
crosshair lands on the crosshair, through the Ken Burns); every miss was an eyeballed
coordinate. Two rules follow, and this tool enforces the second:

  1. AUTHOR from measurement: locate the subject's pixels in the art (green cluster,
     navy cluster in a region) and set `at` from the measured centroid. Never eyeball.
  2. VERIFY on rendered frames: this tool renders each mark-carrying scene through the
     real engine + real spec at the moment its last mark has finished drawing, and
     tiles the frames into work/mark_stills.png. LOOK at every tile: name the thing
     each circle sits on. "Roughly there" at thumbnail size is how misses shipped.

Usage:  python3 tools/mark_stills.py <project_dir>
Writes: <project_dir>/work/mark_stills.png  (+ per-scene frames in work/mark_stills/)

Prereq: narrate+align have run (build_spec needs work/segments.json + alignment).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from explainer2.project import Project           # noqa: E402
from explainer2 import remotion_engine as E      # noqa: E402

REMO = Path(__file__).resolve().parents[1] / "remotion"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.strip())
    pdir = Path(sys.argv[1]).resolve()
    proj = Project.load(pdir)
    spec = E.build_spec(proj)

    outdir = pdir / "work" / "mark_stills"
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)

    # public dir staged like render(): shared libraries symlinked, project art copied in
    pub = outdir / "public"
    pub.mkdir()
    for entry in (REMO / "public").iterdir():
        os.symlink(entry, pub / entry.name)
    for f in (pdir / "assets" / "imagegen").glob("*.png"):
        # unlink first: the loop above symlinked EVERY shared asset into pub, so if a
        # project image shares a basename with one, shutil.copy would follow the symlink
        # and write through to remotion/public instead of replacing the link — polluting
        # the shared dir, and leaving pub serving a symlink that Remotion 404s on. Caught
        # 2026-08-14 when a still-test had leaked project art into the shared dir.
        (pub / f.name).unlink(missing_ok=True)
        shutil.copy(f, pub / f.name)

    targets = []
    for sc in spec["scenes"]:
        fields = sc.get("fields") or {}
        if not fields.get("marks"):
            continue
        fields = json.loads(json.dumps(fields))  # deep copy
        if str(fields.get("image", "")).startswith("assets/imagegen/"):
            fields["image"] = fields["image"].split("/")[-1]
        dur = sc["durationInFrames"]
        last_cue = max((m.get("cueFrame") or 0) for m in fields["marks"])
        frame = min(dur - 3, last_cue + 40)  # all marks fully drawn
        targets.append((sc["component"], fields, dur, int(frame)))

    print(f"{len(targets)} mark-carrying scenes")
    tiles = []
    for i, (comp, fields, dur, frame) in enumerate(targets):
        props = {"width": 1920, "height": 1080, "fps": spec["fps"],
                 "durationInFrames": dur, "audio": "", "words": [],
                 "scenes": [{"component": comp, "from": 0,
                             "durationInFrames": dur, "fields": fields}],
                 "captionBottomPx": 194, "captionFontSize": 28, "audioFrom": 0,
                 "theme": spec.get("theme", ""), "captionAccent": ""}
        pf = outdir / f"props_{i:02d}.json"
        pf.write_text(json.dumps(props))
        out = outdir / f"mark_{i:02d}.png"
        r = subprocess.run(["npx", "remotion", "still", "Video", str(out),
                            f"--props={pf}", f"--frame={frame}",
                            f"--public-dir={pub}", "--log=error"],
                           cwd=REMO, capture_output=True, text=True)
        label = Path(fields.get("image") or comp).stem
        print(f"  {i:02d} {label:<22} frame {frame}: {'ok' if r.returncode == 0 else 'FAIL'}")
        if r.returncode == 0:
            tiles.append((label, out))
        else:
            print(r.stderr[-500:])

    from PIL import Image, ImageDraw
    CW = 620
    CH = int(CW * 1080 / 1920)
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (CW + 8) + 8, rows * (CH + 20) + 8), (20, 20, 24))
    d = ImageDraw.Draw(sheet)
    for i, (label, f) in enumerate(tiles):
        x = 8 + (i % cols) * (CW + 8)
        y = 8 + (i // cols) * (CH + 20)
        sheet.paste(Image.open(f).convert("RGB").resize((CW, CH)), (x, y))
        d.text((x + 2, y + CH + 4), f"{i:02d} {label}", fill=(255, 255, 255))
    final = pdir / "work" / "mark_stills.png"
    sheet.save(final)
    print(f"\n{final}")


if __name__ == "__main__":
    main()
