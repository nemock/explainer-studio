# VENDORED_FROM: nemock/video-explainer-system @ d593aa41dc32d04e3b714b4731b1763f6e31843e (src/explainer/media/align.py) — copied 2026-06-10; diverges freely (v1 is frozen).
"""ALIGN — torchaudio MMS_FA forced alignment (Apple-Silicon-native) -> word
timestamps, timeline.json, and captions.srt/.vtt. The WhisperX replacement."""
import json, re, time


def _norm(tok):
    return re.sub(r"[^a-z]", "", tok.lower())


def _ts(t, sep=","):
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def run(proj):
    import torch, torchaudio
    from .. import lexicon
    data = json.loads((proj.work / "segments.json").read_text())
    segs, duration = data["segments"], data["duration"]
    lex = lexicon.load(proj.dir, (proj.brand or {}).get("lexicon"))

    device = "cpu"  # reliable + fast for short clips; MPS is a later optimization
    bundle = torchaudio.pipelines.MMS_FA
    model = bundle.get_model().to(device)
    tokenizer = bundle.get_tokenizer()
    aligner = bundle.get_aligner()

    wav, sr = torchaudio.load(str(proj.work / "narration.wav"))
    if wav.size(0) > 1:
        wav = wav.mean(0, keepdim=True)
    if sr != bundle.sample_rate:
        wav = torchaudio.functional.resample(wav, sr, bundle.sample_rate)
    sr = bundle.sample_rate

    # PER-SEGMENT alignment (16 GB rule). wav2vec2 self-attention is quadratic
    # in sequence length: one forward pass over a 9-minute narration peaked at
    # ~26 GB and got the process killed (2026-06-11). Segment boundaries are
    # exact (assembly wrote them), so align each 10–25 s slice independently
    # and offset the timestamps — flat memory, same output contract.
    words = []
    t0 = time.time()
    pad = int(0.05 * sr)  # tolerate boundary rounding at the slice tail
    for seg in segs:
        # spoken tokens (acronyms expanded to letters), but remember which
        # display token each group belongs to, so captions show "MCP" while
        # the audio said "M C P".
        descriptors, transcript = [], []
        for disp, stoks in lexicon.expand(seg["text"], lex):
            norm_stoks = [s for s in (_norm(x) for x in stoks) if s]
            if not norm_stoks:
                continue
            descriptors.append((disp, seg["slide"], len(norm_stoks)))
            transcript.extend(norm_stoks)
        if not transcript:
            continue
        s0 = max(0, int(seg["start"] * sr))
        s1 = min(wav.size(1), int(seg["end"] * sr) + pad)
        chunk = wav[:, s0:s1]
        with torch.inference_mode():
            emission, _ = model(chunk.to(device))
            token_spans = aligner(emission[0], tokenizer(transcript))
        ratio = chunk.size(1) / emission.size(1)

        def t_of(f):
            return float(f) * ratio / sr + seg["start"]

        idx = 0
        for disp, slide, n in descriptors:
            group = token_spans[idx:idx + n]
            idx += n
            words.append({"word": disp, "slide": slide,
                          "start": round(t_of(group[0][0].start), 3),
                          "end": round(t_of(group[-1][-1].end), 3)})
        del emission, token_spans, chunk
    align_s = time.time() - t0
    proj.write_json(proj.work / "alignment.json", {"sample_rate": sr, "words": words})

    # contiguous slide windows (a slide is always on screen)
    w, h = proj.size
    slides = []
    for i, seg in enumerate(segs):
        start = seg["start"]
        end = segs[i + 1]["start"] if i + 1 < len(segs) else duration
        slides.append({"id": seg["slide"], "start": round(start, 3), "end": round(end, 3)})
    proj.write_json(proj.work / "timeline.json",
                    {"fps": proj.fps, "width": w, "height": h, "duration": round(duration, 3),
                     "slides": slides, "words": words})

    # captions: one cue per segment
    srt, vtt = [], ["WEBVTT", ""]
    for i, seg in enumerate(segs):
        sw = [x for x in words if x["slide"] == seg["slide"]]
        if not sw:
            continue
        a, b = sw[0]["start"], sw[-1]["end"]
        srt.append(f"{i+1}\n{_ts(a)} --> {_ts(b)}\n{seg['text']}\n")
        vtt.append(f"{_ts(a,'.')} --> {_ts(b,'.')}\n{seg['text']}\n")
    (proj.captions_dir / "captions.srt").write_text("\n".join(srt))
    (proj.captions_dir / "captions.vtt").write_text("\n".join(vtt))

    metrics = {"align_s": round(align_s, 2), "words": len(words), "audio_s": round(duration, 2)}
    proj.write_json(proj.work / "metrics_align.json", metrics)
    return metrics
