#!/usr/bin/env python3
"""Give an already-rendered video a poster frame: replace frame 0 with a real cover.

    bin/explainer2 submit --label posterize --cwd /Volumes/Casima/claudeCode/explainer2 -- \
        /Users/davesaunders/myenv/bin/python3.12 tools/posterize.py --all-shorts
    bin/explainer2 submit ... -- /Users/davesaunders/myenv/bin/python3.12 tools/posterize.py <video.mp4> [--cover card.jpg]

Every render made before 2026-11-14 opens on bare paper while the hook card fades in, and
Instagram, Threads and Facebook use frame 0 as the cover. New renders carry a poster frame
from the engine (remotion Video.tsx); this backfills the old ones without a re-render.

Frame 0 becomes, in order of preference:
  1. --cover, or for a Short the vertical card tools/shorts_thumbnail.py already made
     (<project>/package/thumbnails/shorts/<slug>.jpg) — designed as a cover;
  2. otherwise the video's own frame at --at seconds (default 0.5: the hook card is up and
     the first caption has not appeared yet).
Every other frame and the audio are untouched (audio is stream-copied).

Safe to re-run: a video whose frame 0 is already not blank is skipped. The original is
kept beside it as <name>.preposter.mp4, and the new file replaces the original only after
its duration matches. This ENCODES VIDEO: render queue only.
Decision doc: make_money/routine_changes/2026-11-14-video-covers-and-blur-band.md.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECTS = Path("/Volumes/Casima/claudeCode/explainer-content/projects")
sys.path.insert(0, "/Volumes/Casima/claudeCode/make_money/post_queue")
import covers  # noqa: E402  (flatness + frame-0 decode, shared with the dispatcher guard)


def ff(name):
    return shutil.which(name) or f"/opt/homebrew/bin/{name}"


def probe(path, entry):
    r = subprocess.run([ff("ffprobe"), "-v", "error", "-select_streams", "v:0",
                        "-show_entries", entry, "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return r.stdout.strip().split("\n")[0].strip(",")   # csv output can end with a comma


def duration(path):
    r = subprocess.run([ff("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def shorts_card(video):
    try:
        card = video.parents[3] / "package" / "thumbnails" / "shorts" / f"{video.parents[1].name}.jpg"
        return card if card.is_file() else None
    except IndexError:
        return None


def posterize(video, cover=None, at=0.5, force=False):
    video = Path(video)
    f0 = covers.first_frame(video)
    if f0 and covers.flatness(f0) >= covers.BLANK_STD and not force:
        return "skip (frame 0 already has content)"
    w, h = [x for x in probe(video, "stream=width,height").split(",") if x][:2]
    fps = probe(video, "stream=r_frame_rate")
    cover = Path(cover) if cover else shorts_card(video)
    tmp = Path(tempfile.mkdtemp(prefix="poster_"))
    try:
        if cover is None:
            cover = tmp / "frame.png"
            subprocess.run([ff("ffmpeg"), "-nostdin", "-v", "error", "-y", "-ss", str(at),
                            "-i", str(video), "-frames:v", "1", str(cover)], check=True)
        out = tmp / video.name
        graph = (f"[1:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
                 f"setsar=1,format=yuv420p[c];"
                 f"[0:v][c]overlay=0:0:enable='eq(n,0)':eof_action=pass[v]")
        cmd = [ff("ffmpeg"), "-nostdin", "-v", "error", "-y", "-i", str(video),
               "-loop", "1", "-framerate", fps, "-t", "1", "-i", str(cover),
               "-filter_complex", graph, "-map", "[v]", "-map", "0:a?",
               "-c:v", "libx264", "-preset", "faster", "-crf", "18", "-pix_fmt", "yuv420p",
               "-c:a", "copy", "-movflags", "+faststart", str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            return f"FAILED ffmpeg: {r.stderr[-400:]}"
        d0, d1 = duration(video), duration(out)
        if not d0 or not d1 or abs(d0 - d1) > 0.2:
            return f"FAILED duration {d1} != {d0}"
        new0 = covers.first_frame(out)
        if not new0 or covers.flatness(new0) < covers.BLANK_STD:
            return "FAILED new frame 0 is still blank"
        keep = video.with_name(video.stem + ".preposter" + video.suffix)
        if not keep.exists():
            shutil.copy2(video, keep)
        shutil.move(str(out), str(video))
        return f"ok (cover: {cover.name if cover.parent != tmp else f'frame@{at}s'})"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="*")
    ap.add_argument("--all-shorts", action="store_true",
                    help="every <project>/shorts/*/video/explainer_9x16.mp4")
    ap.add_argument("--cover", help="image to use as frame 0 (single video only)")
    ap.add_argument("--at", type=float, default=0.5)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    videos = [Path(v) for v in args.videos]
    if args.all_shorts:
        videos += sorted(PROJECTS.glob("*/shorts/*/video/explainer_9x16.mp4"))
    if not videos:
        ap.error("no videos given")
    counts = {"ok": 0, "skip": 0, "FAILED": 0}
    for i, v in enumerate(videos, 1):
        res = posterize(v, args.cover if len(videos) == 1 else None, args.at, args.force)
        counts[res.split()[0]] = counts.get(res.split()[0], 0) + 1
        print(f"[{i}/{len(videos)}] {v}: {res}", flush=True)
    print(f"posterize: {counts}")
    return 1 if counts.get("FAILED") else 0


if __name__ == "__main__":
    sys.exit(main())
