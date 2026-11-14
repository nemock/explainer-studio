#!/usr/bin/env python3
"""Blur-band vertical cut: a 16:9 master wrapped in a 9:16 frame for the portrait-first
feeds (Instagram Reels, TikTok, Threads).

    bin/explainer2 submit --label band --cwd /Volumes/Casima/claudeCode/explainer2 -- \
        /Users/davesaunders/myenv/bin/python3.12 tools/vertical_band.py <project>

The wide video stays sharp and full-width in the middle of a 1080x1920 frame. Above and
below it, an enlarged, blurred, slightly darkened copy of the same video fills the frame,
so the phone screen is never black bars. The episode headline (project.json `title`, or
--headline) sits in the top band for the whole clip, inside Instagram's grid-safe area.

Why (operator, 2026-11-14): landscape is the main format and stays the master for YouTube,
LinkedIn, Facebook and X, but a raw 16:9 file in a Reel or a TikTok plays as a thin strip.
Native-portrait footage (talking-head Beats, the 9:16 Shorts) never goes through this.
Frame 0 of the band cut is frame 0 of the master, which carries the poster frame
(remotion Video.tsx, same date), so the platforms that take the first frame as the cover
still get the hook card. Decision doc:
make_money/routine_changes/2026-11-14-video-covers-and-blur-band.md.

Writes video/explainer_9x16_band.mp4 next to the master (atomically: .partial first, then
renamed after a decode + duration check). This ENCODES VIDEO, so it runs through the
render queue only: phase1_render.py calls it inside the daily's Phase 1 job, and any other
use goes through `explainer2 submit`.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

W, H = 1080, 1920
FONT = "/System/Library/Fonts/Avenir Next.ttc"
FONT_INDEX_BOLD = 0          # Avenir Next Bold in the system collection


def ffbin(name):
    return shutil.which(name) or next(
        (p for p in (f"/opt/homebrew/bin/{name}", f"/usr/local/bin/{name}") if Path(p).exists()),
        name)


def duration(path):
    r = subprocess.run([ffbin("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def headline_png(text, out_png):
    """The top-band headline as a transparent 1080-wide PNG, auto-sized to <= 3 lines."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    def font_at(size):
        try:
            return ImageFont.truetype(FONT, size, index=FONT_INDEX_BOLD)
        except OSError:
            return ImageFont.load_default()

    max_w, band_h = 940, 420
    for size in range(92, 47, -4):
        f = font_at(size)
        words, lines, cur = text.split(), [], ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if f.getlength(trial) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        if len(lines) == 2 and len(words) > 2:
            # Balance a two-line wrap so it never strands one word ("...left with / him").
            splits = [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
            lines = list(min(splits, key=lambda ab: max(f.getlength(ab[0]), f.getlength(ab[1]))))
        line_h = int(size * 1.12)
        if len(lines) <= 3 and line_h * len(lines) <= band_h and all(f.getlength(l) <= max_w for l in lines):
            break
    img = Image.new("RGBA", (W, band_h), (0, 0, 0, 0))
    top = (band_h - line_h * len(lines)) // 2
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd, d = ImageDraw.Draw(shadow), ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        x = (W - f.getlength(line)) / 2
        y = top + i * line_h
        sd.text((x, y + 4), line, font=f, fill=(0, 0, 0, 170))
        d.text((x, y), line, font=f, fill=(255, 255, 255, 255))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    Image.alpha_composite(shadow, img).save(out_png)
    return band_h


def build(src, out, headline=None):
    src, out = Path(src), Path(out)
    partial = out.with_name(out.stem + ".partial" + out.suffix)
    partial.unlink(missing_ok=True)
    fg_h = round(W * 9 / 16 / 2) * 2                 # 608
    fg_y = (H - fg_h) // 2                           # 656
    # Background: shrink, blur, enlarge (cheap and smooth), a touch darker so the sharp
    # middle reads as the subject.
    graph = (f"[0:v]split=2[bgsrc][fgsrc];"
             f"[bgsrc]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,"
             f"boxblur=12:2,scale={W}:{H},eq=brightness=-0.10:saturation=1.05,setsar=1[bg];"
             f"[fgsrc]scale={W}:{fg_h},setsar=1[fg];"
             f"[bg][fg]overlay=0:{fg_y}[base]")
    inputs = [ffbin("ffmpeg"), "-nostdin", "-y", "-i", str(src)]
    tmp = None
    if headline:
        tmp = Path(tempfile.mkdtemp(prefix="band_"))
        png = tmp / "headline.png"
        band_h = headline_png(headline, png)
        # Centre the headline between Instagram's top UI (~220 px) and the video's top edge.
        y = max(200, 220 + (fg_y - 220 - band_h) // 2)
        inputs += ["-i", str(png)]
        graph += f";[base][1:v]overlay=0:{y}[v]"
    else:
        graph += ";[base]null[v]"
    cmd = inputs + ["-filter_complex", graph, "-map", "[v]", "-map", "0:a?",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                    str(partial)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{r.stderr[-1500:]}")
        d_src, d_out = duration(src), duration(partial)
        if not d_out or not d_src or abs(d_src - d_out) > 0.5:
            raise RuntimeError(f"band cut duration {d_out}s does not match master {d_src}s")
        partial.replace(out)
    finally:
        partial.unlink(missing_ok=True)
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", help="project dir (reads video/explainer_16x9.mp4)")
    ap.add_argument("--headline", help="top-band text (default: project.json title)")
    ap.add_argument("--no-headline", action="store_true")
    args = ap.parse_args()
    proj = Path(args.project).resolve()
    src = proj / "video" / "explainer_16x9.mp4"
    if not src.is_file():
        print(f"vertical_band: no 16:9 master at {src}", file=sys.stderr)
        return 2
    text = None
    if not args.no_headline:
        text = args.headline
        if not text:
            try:
                text = json.loads((proj / "project.json").read_text()).get("title")
            except Exception:
                text = None
    out = build(src, proj / "video" / "explainer_9x16_band.mp4", headline=text)
    print(f"vertical_band: wrote {out} ({duration(out):.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
