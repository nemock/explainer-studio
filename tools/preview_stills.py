#!/usr/bin/env python3
"""preview_stills.py — look at every slide as the engine will draw it, BEFORE anything is
encoded. The standard still check: run it before the booth and again before any re-render.

Why it exists (MedDevice Cyber Guide episode 3, 2026-11-10). The pre-booth stills showed
every document box that later cut through its letters, but they were read at contact-sheet
size, where a box grazing a line looks like a box around it. A re-render then went out on
tightened boxes without anyone looking at a still at all, and cut through the text. The
frames were available before both renders; the check was in the wrong place and at the
wrong size. This tool makes the check one command, at a size that can be read, and leaves
a stamp (work/preview/preview_check.json) that tools/rerender.py looks for.

What it renders, through the real engine and the real spec (remotion_engine.build_spec):
  - one still per slide, near the END of its scene (every cued reveal and mark has fired),
    with the burned-in captions on, so a caption over a subject shows up here too;
  - for every slide that carries figure `marks`, frame `annotations` or `pageText`, a
    detail crop (detail_sNN.jpg) of exactly what they draw: the same frame is rendered
    again without them, the two are diffed, and the crop is the changed region plus a
    margin, enlarged up to 3x when small. These are the images to READ for marks: there,
    a box that touches the line above, or an edge through a letter, is visible. A slide
    whose marks change nothing on the frame is reported as MARKS NOT VISIBLE. The
    contact sheet is for layout only;
  - a contact sheet of every slide (sheet_N.jpg, nine per sheet) and the phone test on
    the same stills (work/preview/phone_sheet.png, the logic of tools/phone_sheet.py).

Timing:
  - real     work/segments.json + work/alignment.json exist (after narrate+align): the
             stills land where the video will. Required before a re-render.
  - standin  before the booth: each card's words spread at 2.55 words a second (Dave's
             ~154 wpm). Layout, type and mark POSITIONS are exact; cue timing is not.

Usage:  python3 tools/preview_stills.py <project_dir> [--slides s05,s24]
Writes: <project_dir>/work/preview/  (sNN.png pipeline inputs, never Read them;
        sheet_N.jpg, detail_*.jpg, phone_sheet.png + its preview, preview_check.json)
Read:   the sheet JPEGs, every detail JPEG, and the phone sheet's preview (SKILL hard
        rule 9: never the full-res sNN.png).
Exit:   0 rendered every still asked for; 1 some failed (named); 75 still queued/running.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from explainer2.project import Project           # noqa: E402
from explainer2 import remotion_engine as E      # noqa: E402
from explainer2 import renderlock                # noqa: E402
from explainer2 import jobqueue                  # noqa: E402
from explainer2 import childproc                 # noqa: E402

REMO = ROOT / "remotion"
WPS = 2.55          # stand-in speaking rate (words a second)
END_PAD = 12        # frames before a scene's end: every reveal has fired, no transition yet
CHECK_NAME = "preview_check.json"


def deck_sha(pdir):
    return hashlib.sha256((Path(pdir) / "deck.json").read_bytes()).hexdigest()


class _StandIn:
    """The project with `work` pointed at the preview's own stand-in timeline, so
    build_spec reads it and the real work/ is never touched."""

    def __init__(self, proj, work):
        self._p, self._work = proj, work

    @property
    def work(self):
        return self._work

    def __getattr__(self, name):
        return getattr(self._p, name)


def standin_timeline(pdir, work):
    script = json.loads((pdir / "script.json").read_text())["segments"]
    segs, words, t = [], [], 0.0
    for seg in script:
        toks = seg["text"].split() or ["."]
        dur = max(1.0, len(toks) / WPS)
        for k, w in enumerate(toks):
            a = t + dur * k / len(toks)
            words.append({"word": w, "start": round(a, 3),
                          "end": round(a + dur / len(toks) * 0.9, 3)})
        segs.append({"id": seg["id"], "slide": seg["slide"], "text": seg["text"],
                     "start": round(t, 3), "end": round(t + dur, 3)})
        t += dur
    work.mkdir(parents=True, exist_ok=True)
    (work / "segments.json").write_text(json.dumps(
        {"sample_rate": 48000, "duration": round(t, 3), "segments": segs}))
    (work / "alignment.json").write_text(json.dumps({"words": words}))


def stage_public(sp, spec, pub):
    """The render's public dir: every shared library linked in, then project media copied
    over it the way render() copies it (_stage_images / _stage_doodles / _stage_chibi)."""
    if pub.exists():
        shutil.rmtree(pub)
    pub.mkdir(parents=True)
    for entry in (REMO / "public").iterdir():
        os.symlink(entry, pub / entry.name)
    # A project file that shares a basename with a shared asset must REPLACE the link, not
    # write through it into remotion/public (the 2026-08-14 leak mark_stills.py guards).
    for sc in spec["scenes"]:
        f = sc.get("fields") or {}
        vals = [f.get(k) for k in ("image", "bottomImage", "set", "video", "mark", "badge")]
        vals += [p.get("image") for p in (f.get("props") or []) if isinstance(p, dict)]
        for v in vals:
            if isinstance(v, str) and v and not v.startswith(("papercraft", "chibi/")):
                link = pub / Path(v).name
                if link.is_symlink():
                    link.unlink()
    E._stage_images(sp, spec, pub)
    E._stage_doodles(spec, pub, print)
    E._stage_chibi(spec, pub, print)


def slide_frames(spec, segs, fps):
    """slide id -> (scene, frame near its end). A scene is found by the frame its segment's
    midpoint falls in, so intro offsets and scene fitting need no special case."""
    off = int(spec.get("audioFrom") or 0)
    out = {}
    for s in segs:
        mid = off + int(round((s["start"] + s["end"]) / 2 * fps))
        sc = next((x for x in spec["scenes"]
                   if x["from"] <= mid < x["from"] + x["durationInFrames"]), None)
        if sc is None or s["slide"] in out:
            continue
        out[s["slide"]] = (sc, sc["from"] + max(0, sc["durationInFrames"] - END_PAD))
    return out


def wants_detail(sc):
    f = sc.get("fields") or {}
    # nodeAnnotations: a schematic's `target` annotations, which build_spec moves into the
    # schematic's own fields so they ride its camera
    return bool(f.get("marks") or f.get("nodeAnnotations") or sc.get("annotations")
                or f.get("pageText"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--slides", help="comma-separated slide ids (default: every slide)")
    a = ap.parse_args()
    pdir = Path(a.project).resolve()
    proj = Project.load(pdir)
    # Every still launches headless Chrome, so this is a render: from a session it goes
    # to the render queue and this process only waits for it (CLAUDE.md rule 9).
    if jobqueue.should_route():
        argv = [sys.executable, str(Path(__file__).resolve()), str(pdir)]
        if a.slides:
            argv += ["--slides", a.slides]
        sys.exit(jobqueue.submit_and_wait("preview_stills", argv, project=str(pdir),
                                          label=f"preview_stills:{pdir.name}"))
    childproc.install_handlers(log=print)

    out = pdir / "work" / "preview"
    real = (pdir / "work" / "segments.json").exists() and \
        (pdir / "work" / "alignment.json").exists()
    if real:
        sp, timing = proj, "real"
    else:
        standin_timeline(pdir, out / "work")
        sp, timing = _StandIn(proj, out / "work"), "standin"
    sha = deck_sha(pdir)
    spec = E.build_spec(sp)
    for w in spec.pop("_warnings", []):
        print("warning:", w)
    spec["audio"] = ""
    fps = spec.get("fps", 30)
    segs = json.loads((sp.work / "segments.json").read_text())["segments"]
    frames = slide_frames(spec, segs, fps)
    want = [x.strip() for x in a.slides.split(",")] if a.slides else list(frames)
    missing = [x for x in want if x not in frames]
    if missing:
        sys.exit(f"preview_stills: no scene for {', '.join(missing)}")

    # A --slides run replaces only its own slides' files, so the crops of a full run stay
    # readable beside a re-check of the two slides that were fixed.
    out.mkdir(parents=True, exist_ok=True)
    for sid in want:
        for name in (f"{sid}.png", f"detail_{sid}.jpg", f"bare_{sid}.png"):
            (out / name).unlink(missing_ok=True)
    for old in out.glob("sheet_*.jpg"):
        old.unlink()
    pub = out / "public"
    stage_public(sp, spec, pub)
    props = out / "props.json"
    props.write_text(json.dumps(spec))
    print(f"{len(want)} slides, {timing} timing, deck {sha[:12]}")

    done, failed, bare = [], [], {}
    lock = renderlock.acquire(proj, label=f"preview_stills:{pdir.name}")
    try:
        # Bundle once and point every still at the bundle: `remotion still src/index.ts`
        # re-bundles per call (about 30 s of a 32 s still on episode 3's 30 slides).
        bundle = out / "bundle"
        shutil.rmtree(bundle, ignore_errors=True)
        r = childproc.run(["npx", "remotion", "bundle", "src/index.ts",
                           f"--out-dir={bundle}", f"--public-dir={pub}", "--log=error"],
                          label="preview_bundle", cwd=REMO, capture_output=True, text=True)
        if r.returncode == 0 and (bundle / "index.html").exists():
            serve = [str(bundle)]
        else:
            print("bundle failed, rendering from source (slower):", (r.stderr or "")[-300:])
            serve = ["src/index.ts", f"--public-dir={pub}"]

        def still(png, props_file, frame, label):
            cmd = ["npx", "remotion", "still", serve[0], "Video", str(png),
                   f"--props={props_file}", f"--frame={frame}", "--log=error"] + serve[1:]
            r = childproc.run(cmd, label=label, cwd=REMO, capture_output=True, text=True)
            if r.returncode != 0:
                print((r.stderr or "")[-500:])
            return r.returncode == 0 and png.exists()

        for sid in want:
            sc, frame = frames[sid]
            ok = still(out / f"{sid}.png", props, frame, f"preview_{sid}")
            print(f"  {sid:<5} {sc['component']:<22} frame {frame}: {'ok' if ok else 'FAIL'}")
            (done if ok else failed).append(sid)
            if ok and wants_detail(sc):
                # The same frame with this slide's marks, annotations and pageText taken
                # out: the difference between the two is exactly what they draw, which is
                # where the detail crop goes.
                twin = json.loads(json.dumps(spec))
                tsc = next(x for x in twin["scenes"] if x["from"] == sc["from"])
                tsc.pop("annotations", None)
                for k in ("marks", "marks_9x16", "nodeAnnotations", "pageText"):
                    (tsc.get("fields") or {}).pop(k, None)
                tp = out / f"props_bare_{sid}.json"
                tp.write_text(json.dumps(twin))
                if still(out / f"bare_{sid}.png", tp, frame, f"preview_bare_{sid}"):
                    bare[sid] = out / f"bare_{sid}.png"
                tp.unlink()
    finally:
        renderlock.release(lock)
        shutil.rmtree(out / "bundle", ignore_errors=True)

    from PIL import Image, ImageChops, ImageDraw
    details, unseen = [], []
    for sid in done:
        if sid not in bare:
            continue
        im = Image.open(out / f"{sid}.png").convert("RGB")
        diff = ImageChops.difference(im, Image.open(bare[sid]).convert("RGB")).convert("L")
        box = diff.point(lambda v: 255 if v > 40 else 0).getbbox()
        bare[sid].unlink()
        if box is None:
            # authored, yet nothing on this frame changed: off-frame, hidden, or not drawn
            unseen.append(sid)
            continue
        pad = 48
        x0, y0 = max(0, box[0] - pad), max(0, box[1] - pad)
        x1, y1 = min(im.width, box[2] + pad), min(im.height, box[3] + pad)
        crop = im.crop((x0, y0, x1, y1))
        # small type gets enlarged so an edge through a letter is visible; never past 3x
        s = max(1.0, min(3.0, 1100 / crop.width, 800 / crop.height))
        if s > 1.0:
            crop = crop.resize((round(crop.width * s), round(crop.height * s)), Image.LANCZOS)
        f = out / f"detail_{sid}.jpg"
        crop.save(f, quality=90)
        details.append(str(f))

    sheets = []
    TW, TH = 640, 360
    for n in range(0, len(done), 9):
        sheet = Image.new("RGB", (TW * 3, TH * 3), (30, 30, 34))
        d = ImageDraw.Draw(sheet)
        for k, sid in enumerate(done[n:n + 9]):
            x, y = (k % 3) * TW, (k // 3) * TH
            sheet.paste(Image.open(out / f"{sid}.png").convert("RGB").resize((TW, TH)), (x, y))
            d.rectangle([x, y, x + 64, y + 22], fill=(0, 0, 0))
            d.text((x + 6, y + 5), sid, fill=(255, 255, 0))
        f = out / f"sheet_{n // 9 + 1}.jpg"
        sheet.save(f, quality=85)
        sheets.append(str(f))

    phone_preview = None
    if done:
        from explainer2 import phonesheet
        from frame_preview import make_preview
        report = phonesheet.build_sheet([out / f"{s}.png" for s in done], out,
                                        phonesheet.art_slides(pdir / "deck.json"))
        phone_preview = str(make_preview(out / "phone_sheet.png", None, 1200))
        flagged = [r for r in report if r["verdict"] != "ok"]
        print(f"phone test (advisory): {len(flagged)} of {len(report)} flagged"
              + (": " + ", ".join(f"{r['slide']} {r['verdict']}" for r in flagged)
                 if flagged else ""))

    (out / CHECK_NAME).write_text(json.dumps({
        "deck_sha": sha, "timing": timing, "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "complete": not a.slides and not failed,
        "slides": done, "failed": failed, "details": details, "marks_unseen": unseen},
        indent=1))

    print("\nREAD every one of these (previews and crops, never the sNN.png):")
    for f in sheets:
        print(f"  sheet   {f}")
    for f in details:
        print(f"  detail  {f}")
    if phone_preview:
        print(f"  phone   {phone_preview}")
    print("For each detail crop, name what every mark sits on and check that no edge "
          "touches a letter or the line above.")
    if unseen:
        print(f"MARKS NOT VISIBLE on the checked frame (authored, but nothing drew): "
              f"{', '.join(unseen)}. Look at those slides before anything else.")
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
