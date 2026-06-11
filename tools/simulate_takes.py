"""Dev tool: synthesize stand-in operator takes with Kokoro so the operator-voice
path (assemble → cleanup → adlib → align) can be integration-tested without a
human at the mic. Writes voiceover/seg_XXX.wav at 48 kHz mono, exactly like the
recording booth does. NEVER part of production — real projects use `record`.

Usage: python tools/simulate_takes.py <project_dir> [--voice am_michael]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--voice", default="am_michael", help="Kokoro voice for the stand-in")
    args = ap.parse_args()

    from explainer2.project import Project
    from explainer2.media.common import effective_segments
    import torch
    import torchaudio
    from kokoro import KPipeline

    proj = Project.load(args.project_dir)
    script = json.loads(proj.script_json.read_text())
    segments = effective_segments(proj, script)
    proj.voiceover_dir.mkdir(parents=True, exist_ok=True)

    pipe = KPipeline(lang_code="a")
    for seg in segments:
        chunks = []
        for _, _, audio in pipe(seg["text"], voice=args.voice, speed=1):
            a = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
            chunks.append(a.astype(np.float32))
        wav24 = np.concatenate(chunks) if chunks else np.zeros(1, np.float32)
        wav48 = torchaudio.functional.resample(
            torch.from_numpy(wav24).unsqueeze(0), 24000, 48000).squeeze(0).numpy()
        out = proj.voiceover_dir / f"seg_{seg['id']:03d}.wav"
        sf.write(out, wav48, 48000)
        print(f"seg {seg['id']:03d}  {len(wav48)/48000:6.2f}s  {seg['text'][:50]!r}")
    print(f"done: {len(segments)} stand-in takes in {proj.voiceover_dir}")


if __name__ == "__main__":
    main()
