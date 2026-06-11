"""Audio cleanup for operator voiceover (PRD §5.3) — native ffmpeg chain.

Two-tier: voiceover.py prefers the local VocalEnhancer skill (adaptive analysis:
hum detection, per-file EQ) when it exists on this machine; this module is the
self-sufficient fallback vendored into the repo so a fresh clone still ships
broadcast-level narration. Static chain, two-pass loudnorm to -14 LUFS:

  highpass 80 Hz (rumble) → afftdn (broadband denoise) → deesser →
  presence EQ (+2 dB @ 3 kHz) → gentle compression → loudnorm (measured 2-pass)
"""
import json
import subprocess

PREFILTER = ("highpass=f=80,"
             "afftdn=nf=-25,"
             "deesser,"
             "equalizer=f=3000:t=q:w=1:g=2,"
             "acompressor=threshold=-18dB:ratio=3:attack=10:release=150")
TARGET = {"I": -14.0, "TP": -1.5, "LRA": 11.0}


def _measure(src):
    """Pass 1: loudnorm measurement on the prefiltered signal."""
    af = (f"{PREFILTER},loudnorm=I={TARGET['I']}:TP={TARGET['TP']}:LRA={TARGET['LRA']}"
          f":print_format=json")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af", af,
                        "-f", "null", "-"], capture_output=True, text=True)
    # loudnorm prints its JSON block at the end of stderr
    tail = r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1]
    try:
        return json.loads(tail)
    except json.JSONDecodeError:
        return None


def clean(src, out, sr=48000):
    """Full chain + measured two-pass loudnorm. Returns a method tag."""
    m = _measure(src)
    if m:
        ln = (f"loudnorm=I={TARGET['I']}:TP={TARGET['TP']}:LRA={TARGET['LRA']}"
              f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
              f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
              f":offset={m['target_offset']}:linear=true")
        method = "explainer2-chain:2pass"
    else:
        ln = f"loudnorm=I={TARGET['I']}:TP={TARGET['TP']}:LRA={TARGET['LRA']}"
        method = "explainer2-chain:1pass"
    subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(src),
                    "-af", f"{PREFILTER},{ln}", "-ar", str(sr), "-ac", "1", str(out)],
                   check=True, capture_output=True)
    return method
