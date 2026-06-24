# Explainer Studio — a local-first explainer-video studio

> Topic in → YouTube competitive intelligence → retention-engineered script → **your** voice → layered motion graphics → a packaged deep dive **and** Shorts — entirely on one Mac, with **no SaaS subscriptions in the pipeline**.

<!-- badges: license · stars · (later) release -->

**Status: working / in active use.** It produces finished, packaged videos end-to-end on an Apple-Silicon Mac. [PRD.md](PRD.md) is the source of truth for scope and build phases. The proven v1, [`video-explainer-system`](https://github.com/nemock/video-explainer-system), remains a separate production tool — this is a ground-up successor whose media core was vendored once from v1 and has since diverged.

<!-- TODO: hero GIF of Mission Control board + a finished frame -->

---

## Why this exists

The "normal" way to automate explainer videos is to rent four or five cloud services — a voice subscription, a stock-footage plan, an avatar tier, a render-credit meter. [v1](https://github.com/nemock/video-explainer-system) proved you don't need any of them: local TTS (Kokoro), local forced alignment, a headless browser, and ffmpeg produce a finished, captioned, branded video on an M3 Mac, with the LLM being an existing **Claude subscription** — no API key, no per-token billing.

Explainer Studio keeps that conviction and asks the next question: not just *"how do I make a video?"* but *"how do I make the video that **wins** — and keeps people watching, and grows a channel?"*

## What it does

1. **Researches YouTube before writing a word.** Give it a topic; it finds comparable videos, scores breakout outliers against their channels' baselines, reverse-engineers their titles, hooks, structure, thumbnails, and descriptions — and identifies the gap they all leave open. You approve the resulting **Blueprint** before scripting starts.
2. **Writes retention-engineered, conversational scripts** — cold-open hook, scheduled open loops and payoffs, re-hook beats, pattern interrupts — flavored by your own voice library, shown to you next to its retention map for editing.
3. **Records in your actual voice.** A built-in browser teleprompter + recorder (per-segment retakes, automatic local audio cleanup, ad-lib-tolerant alignment). Local Kokoro TTS remains the fully-headless fallback.
4. **Builds layered motion graphics** — a deterministic **Remotion** component library (stat cards, comparisons, timelines, diagrams, 3D, kinetic word-synced captions), music with auto-ducking, and licensed B-roll via a guided **Adobe Stock** workflow (the one declared subscription exception: it suggests searches, you license and drop files, it ingests and conforms them; every footage scene has a designed fallback).
5. **Emits two formats from one project:** a chapter-marked 16:9 deep dive *and* 9:16 Shorts cut from its strongest beats, each re-hooked and CTA'd toward the long-form.
6. **Packages for monetization:** locally rendered thumbnail candidates, intelligence-ranked titles, SEO-shaped description with chapters and book CTA, tags, pinned comment, end-screen plan — all in a versioned `manifest.json` for any downstream poster. **It never posts.**
7. **Learns from results** (optional): drop in YouTube Studio CSV exports and it builds a local memory of which titles/hooks/structures actually perform on *your* channel, cited by the next Blueprint.

All of it driven from **Mission Control** — a local web GUI where projects move across a board with review gates, a recording booth, an asset queue, and a render queue. Every GUI action has a CLI equivalent (`bin/explainer2 <command>`).

## The stack (local & free)

| Capability | Tool |
|---|---|
| LLM (research, blueprint, script, packaging copy) | **Claude subscription** via Claude Code / Agent SDK — no API key |
| YouTube intelligence | `yt-dlp` (metadata, transcripts, thumbnails — no API quota) |
| Text-to-speech (fallback tier) | Kokoro-82M, local |
| Your voice | Browser teleprompter/recorder + local ffmpeg cleanup chain |
| Word-level timing | torchaudio forced alignment (Apple-Silicon-native) |
| Ad-lib transcription | Whisper, local |
| Motion graphics (default engine) | **Remotion** (React/TS), rendered headless — deterministic via `useCurrentFrame`/`interpolate`/seeded RNG |
| Legacy visuals (`--engine deck`) | HTML/CSS/JS layer stack, captured via headless Chrome |
| Encode | ffmpeg + VideoToolbox (hardware) |
| Thumbnail headshot cutout | `rembg` (local U²-Net) |
| Stock footage | **Your stock.adobe.com membership** — guided, human-in-the-loop (the one exception) |

Target machine: Apple Silicon (developed on an M3 / 16 GB). No CUDA, no cloud render.

## Dependencies

Everything the pipeline depends on runs **locally** and is **free** (the one declared exception is the operator's existing stock.adobe.com membership, which is human-in-the-loop and never an API dependency). There is no cloud render, no per-token billing, and no SaaS in the critical path.

**System tools** (install once via Homebrew / nvm):

- **Python ≥ 3.12** — the pipeline runs on the shared `~/myenv` interpreter, which already holds the verified multi-GB torch/Kokoro/Playwright stack. `bin/explainer2` wraps it; no install into the venv is needed.
- **ffmpeg** (with VideoToolbox) — audio cleanup, hardware encode, mux. `brew install ffmpeg`.
- **Node.js ≥ 20 + npm** — for the Remotion motion engine. `brew install node` or nvm.
- **yt-dlp** — YouTube intelligence (metadata/transcripts only; no API key). `brew install yt-dlp`.

**Python packages** (pinned in [pyproject.toml](pyproject.toml), already present in `~/myenv`):

`kokoro` · `torch` / `torchaudio` · `soundfile` · `numpy` · `playwright` · `pymupdf` · `yt-dlp` · `rembg`

**Node packages** (the Remotion engine — `cd remotion && npm install`):

`remotion` + `@remotion/cli` / `media-utils` / `three` / `transitions` · `react` / `react-dom` · `@react-three/fiber` + `three` (3D scenes) · `zod` (spec schema). Versions pinned in [remotion/package.json](remotion/package.json).

**LLM** — your **Claude subscription** through Claude Code / the Agent SDK (subscription auth). Never an API key, never per-token billing. Claude touches only the *generation* stages (intel synthesis, blueprint, script, packaging copy, QA judgments); the media path (narrate → align → compose → render → mux) is pure Python with **zero LLM calls** and runs unattended.

## Render robustness (RAM-aware, multi-project-safe)

The render+mux stage — headless frame capture plus an ffmpeg encode — is the one memory-heavy part of the pipeline, and on a 16 GB machine two of them at once means an OOM kill mid-write. Two mechanisms in [`src/explainer2/renderlock.py`](src/explainer2/renderlock.py) keep it honest:

- **RAM-aware serialization.** Memory-heavy stages are serialized by design — never Kokoro *and* headless capture *and* ffmpeg at the same time — so the encode fits the unified-memory budget instead of fighting it.
- **A machine-global render lock.** An `fcntl.flock` on a fixed lockfile (`/tmp/explainer-render.lock`) is shared across **every** explainer project *and* across codebases (this repo **and** the production v1). Start as many renders as you like, whenever you like — they queue and auto-start one at a time, so concurrent renders never kill each other. The OS releases the lock if a holder dies (even on `SIGKILL`), so a crashed render can't deadlock the queue. `bin/explainer2 render-status` shows who holds the lock and every live render.
- **Detached, suspend-proof launches.** Heavy renders launch in their own session under `caffeinate`, so suspending or closing the Claude app (or going AFK) leaves the encode running to completion instead of killing it mid-frame.

Hard rule for contributors: never invoke a heavy ffmpeg encode raw — route it through `renderlock.run_locked(...)` so it serializes against scheduled renders.

## Quick start

```bash
git clone https://github.com/nemock/explainer-studio && cd explainer-studio

# 1. Node side: install the Remotion motion engine
cd remotion && npm install && cd ..

# 2. Python side: the media stack lives in the shared ~/myenv interpreter
#    (torch / Kokoro / Playwright already installed there). bin/explainer2 wraps it.

# Run any pipeline stage via the wrapper:
bin/explainer2 scaffold "why vector databases forget"   # new project dir
bin/explainer2 intel <project-dir>                       # YouTube intelligence sweep
#   → Claude authors the Blueprint, script, deck.json, and shorts plan (see the SKILL)
bin/explainer2 record <project-dir>                      # open the booth, record in your voice
bin/explainer2 media --only narrate,align <project-dir>  # light media stages (foreground)
bin/explainer2 render <project-dir>                       # heavy render — launches DETACHED
bin/explainer2 render-status                              # render-queue view
```

The end-to-end procedure, gates, and hard rules are written down in the skill (below) — the project is built to be run by any Claude model, so the methodology lives in the repo, not in any one session.

## Documentation

The analytical methodology is documented as a **skill + playbooks** so the pipeline is reproducible by any operator (human or model):

- [PRD.md](PRD.md) — full product spec, architecture, risks, build phases
- [skills/explainer2/SKILL.md](skills/explainer2/SKILL.md) — the pipeline procedure, gates, and hard rules
- [skills/explainer2/references/blueprint-playbook.md](skills/explainer2/references/blueprint-playbook.md) — intel sweep → Blueprint
- [skills/explainer2/references/script-playbook.md](skills/explainer2/references/script-playbook.md) — retention engineering + voice rules
- [skills/explainer2/references/spoken-humanizer.md](skills/explainer2/references/spoken-humanizer.md) — the pre-booth spoken-language pass
- [skills/explainer2/references/motion-playbook.md](skills/explainer2/references/motion-playbook.md) — the Remotion motion engine
- [skills/explainer2/references/deck-playbook.md](skills/explainer2/references/deck-playbook.md) — the legacy deck engine
- [skills/explainer2/references/thumbnail-playbook.md](skills/explainer2/references/thumbnail-playbook.md) · [article-playbook.md](skills/explainer2/references/article-playbook.md) · [shorts-playbook.md](skills/explainer2/references/shorts-playbook.md) — packaging
- [docs/examples/](docs/examples/) — a worked Blueprint example

## Boundaries (choices, not gaps)

- **No posting/scheduling** — output is a packaged directory + manifest; pair with your own poster.
- **No avatars, no voice cloning, no photoreal generative video** — your real voice is the premium tier.
- **No cloud anything** — single operator, single Mac, files on disk.
- **v1 untouched** — this project never reads from or writes into `video-explainer-system`.

## License

[MIT](LICENSE).

---

*Built as a Claude Code project. Generation-only — this tool never posts to social platforms.*
