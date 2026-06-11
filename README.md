# Explainer Studio — a local-first explainer-video studio

> Topic in → YouTube competitive intelligence → retention-engineered script → **your** voice → layered visuals → a packaged deep dive **and** Shorts — entirely on one Mac, with **no SaaS subscriptions in the pipeline**.

<!-- badges: license · stars · (later) release -->

**Status: pre-release / in design.** The PRD lives at [PRD.md](PRD.md). The proven v1, [`video-explainer-system`](https://github.com/nemock/video-explainer-system), remains a separate, production tool — this is a ground-up successor, not an update.

<!-- TODO: hero GIF of Mission Control board + a finished frame -->

---

## Why this exists

The "normal" way to automate explainer videos is to rent four or five cloud services — a voice subscription, a stock-footage plan, an avatar tier, a render-credit meter. [v1](https://github.com/nemock/video-explainer-system) proved you don't need any of them: local TTS (Kokoro), local forced alignment, a headless browser, and ffmpeg produce a finished, captioned, branded video on an M3 Mac, with the LLM being an existing **Claude subscription** — no API key, no per-token billing.

Explainer2 keeps that conviction and asks the next question: not just *"how do I make a video?"* but *"how do I make the video that **wins** — and keeps people watching, and grows a channel?"*

## What it does

1. **Researches YouTube before writing a word.** Give it a topic; it finds comparable videos, scores breakout outliers against their channels' baselines, reverse-engineers their titles, hooks, structure, thumbnails, and descriptions — and identifies the gap they all leave open. You approve the resulting **Blueprint** before scripting starts.
2. **Writes retention-engineered, conversational scripts** — cold-open hook, scheduled open loops and payoffs, re-hook beats, pattern interrupts — flavored by your own voice library, shown to you next to its retention map for editing.
3. **Records in your actual voice.** A built-in browser teleprompter + recorder (per-segment retakes, automatic local audio cleanup, ad-lib-tolerant alignment). Local Kokoro TTS remains the fully-headless fallback.
4. **Builds layered visuals** — animated HTML deck scenes, motion graphics, kinetic word-synced captions, music with auto-ducking, and licensed B-roll via a guided **Adobe Stock** workflow (the one declared subscription exception: it suggests searches, you license and drop files, it ingests and conforms them; every footage scene has a designed fallback).
5. **Emits two formats from one project:** a chapter-marked 16:9 deep dive *and* 9:16 Shorts cut from its strongest beats, each re-hooked and CTA'd toward the long-form.
6. **Packages for monetization:** locally rendered thumbnail candidates, intelligence-ranked titles, SEO-shaped description with chapters and book CTA, tags, pinned comment, end-screen plan — all in a versioned `manifest.json` for any downstream poster. **It never posts.**
7. **Learns from results** (optional): drop in YouTube Studio CSV exports and it builds a local memory of which titles/hooks/structures actually perform on *your* channel, cited by the next Blueprint.

All of it driven from **Mission Control** — a local web GUI where projects move across a board (Intel → Blueprint → Script → Voice → Assets → Compose → Render → Package) with review gates, a recording booth, an asset queue, and a render queue. Every GUI action has a CLI equivalent.

## The stack (local & free)

| Capability | Tool |
|---|---|
| LLM (research, blueprint, script, packaging copy) | **Claude subscription** via Claude Code / Agent SDK — no API key |
| YouTube intelligence | `yt-dlp` (metadata, transcripts, thumbnails — no API quota) |
| Text-to-speech (fallback tier) | Kokoro-82M, local |
| Your voice | Browser teleprompter/recorder + local ffmpeg cleanup chain |
| Word-level timing | torchaudio forced alignment (Apple-Silicon-native) |
| Ad-lib transcription | Whisper, local |
| Visuals | HTML/CSS/JS layer stack, deterministic, captured via headless Chrome |
| Encode | ffmpeg + VideoToolbox (hardware) |
| Stock footage | **Your stock.adobe.com membership** — guided, human-in-the-loop (the one exception) |

Target machine: Apple Silicon (developed on an M3 / 16 GB). No CUDA, no cloud render.

## Quick start

```bash
# TODO once Phase 0 lands
git clone https://github.com/nemock/explainer-studio && cd explainer-studio
./setup.sh                     # checks deps: python, ffmpeg, playwright, yt-dlp, kokoro, claude
explainer2 studio              # launches Mission Control at localhost, opens Chrome
# — or headless —
explainer2 new "why vector databases forget" --tier auto --format 9:16
```

## Documentation

- [PRD.md](PRD.md) — full product spec, architecture, risks, build phases
- docs/PIPELINE.md — stage-by-stage reference *(TODO)*
- docs/MISSION-CONTROL.md — GUI guide *(TODO)*
- docs/INTELLIGENCE.md — how the YouTube Blueprint engine works *(TODO)*
- docs/RECORDING.md — the booth, mic setup, cleanup chain *(TODO)*

## Boundaries (choices, not gaps)

- **No posting/scheduling** — output is a packaged directory + manifest; pair with your own poster.
- **No avatars, no voice cloning, no photoreal generative video** — your real voice is the premium tier.
- **No cloud anything** — single operator, single Mac, files on disk.
- **v1 untouched** — this project never reads from or writes into `video-explainer-system`.

## License

MIT *(TODO: add LICENSE)*

---

*Built as a Claude Code project. Generation-only — this tool never posts to social platforms.*
