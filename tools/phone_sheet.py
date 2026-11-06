#!/usr/bin/env python3
"""phone_sheet.py — run the phone test on demand. The logic is src/explainer2/phonesheet.py;
every render already runs it from qa, so reach for this after changing frames by hand or to
sheet an older render.

Usage:
    python3 tools/phone_sheet.py <project_dir>            # frames from video/*.mp4 (queued)
    python3 tools/phone_sheet.py <project_dir> --frames <dir_of_sNN.png>   # no decode

Writes work/phone_sheet.png, its preview (Read THAT, SKILL hard rule 9) and
work/phone_sheet.json. Exit 0 always unless it could not run (2): the fill check advises.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--frames", help="use existing sNN.png frames from this dir (no decode)")
    a = ap.parse_args()
    pdir = Path(a.project).resolve()
    from explainer2 import phonesheet
    if a.frames:
        frames = sorted(Path(a.frames).resolve().glob("s[0-9]*.png"))
        report = phonesheet.build_sheet(frames, pdir / "work") if frames else []
    else:
        from explainer2 import jobqueue
        # decoding a long master launches ffmpeg per slide: a render-class job, so from a
        # session it goes through the queue like every other one (CLAUDE.md rule 9)
        if jobqueue.should_route():
            sys.exit(jobqueue.submit_and_wait(
                "phone_sheet", [sys.executable, str(Path(__file__).resolve()), str(pdir)],
                project=str(pdir), label=f"phone_sheet:{pdir.name}"))
        from explainer2.project import Project
        from explainer2.remotion_engine import intro_offset_s
        proj = Project.load(pdir)
        video = proj.video_dir / f"explainer_{proj.aspect.replace(':', 'x')}.mp4"
        if not video.exists():
            sys.exit(f"phone_sheet: no {video.name} in {proj.video_dir}")
        slides = json.loads((pdir / "work" / "timeline.json").read_text())["slides"]
        report = phonesheet.run_for_render(video, slides, intro_offset_s(proj), pdir / "work")
    if not report:
        print("phone_sheet: no frames found", file=sys.stderr)
        sys.exit(2)

    from frame_preview import make_preview
    dst = pdir / "work" / "phone_sheet.png"
    flagged = [r for r in report if r["verdict"] != "ok"]
    for r in flagged:
        print(f"  {r['verdict']:<8} {r['slide']}  content box {r['bbox']:.0%} of the band, "
              f"edge-dense {r['ink']:.0%}")
    print(f"phone sheet: {dst}\npreview:     {make_preview(dst, None, 1200)}")
    print(f"fill check (advisory): {len(flagged)} of {len(report)} slides flagged")


if __name__ == "__main__":
    main()
