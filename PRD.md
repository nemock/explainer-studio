# Product Requirements Document — **Explainer Studio** (`explainer-studio`; working name "explainer2")

### A local-first explainer-video *studio*: YouTube competitive intelligence → retention-engineered script → your voice → layered visuals → deep dive + Shorts → monetization-ready package. All on one Mac, no SaaS subscriptions in the pipeline.

- **Status:** **Phase 0 shipped** (2026-06-10: vendored v1 core, manifest 2.0, parity render passed). **Phase 1 shipped** (2026-06-10: intel engine — yt-dlp sweep, RSS-based outlier scoring, deep pull; first Blueprint generated, see [docs/examples/blueprint-first-saas-customers.md](docs/examples/blueprint-first-saas-customers.md)). **Phase 2 shipped** (2026-06-10: native cleanup chain, ad-lib ASR drift check with number normalization, booth upgrades — waveform/read-time/retake history/retention cues, script/2 schema with retention map; full voice path integration-tested with simulated takes — 9:51 narration, 1,451 words aligned, captions emitted. Methodology codified for any-model operation in [skills/explainer2/](skills/explainer2/SKILL.md)). **Phase 3 shipped** (Adobe Stock assist — watched `assets/inbox/` + conform/ingest pipeline, 2026-06-10; deterministic layered B-roll render demonstrated — e.g. project #13 mixes deck scenes and licensed footage). **Phase 5 shipped** (Shorts cutter 2026-06-11; thumbnail engine — brand-template cutout + illustrative composed scenes; description/chapters/CTA/manifest + per-platform handoff; written article companion; **Learn feedback loop 2026-07-03** — `learn refresh/ingest/report`, yt-dlp public stats + YouTube Studio CSV → `channel/learn/` performance memory + REPORT.md, cited by the blueprint playbook when ranking titles; see §5.8). **Phase 4 (Mission Control GUI) is not yet built** — the same review gates run from the CLI for now. **Beyond the original plan:** the default render path is now a **Remotion motion-graphics engine** (`--engine remotion`, 2026-06-24); an operator-invoked **`promote`** command re-shares already-published Shorts via Blotato (2026-06-20, §N1 — dry-run by default); and the recording booth shipped its **Booth 2.0** upgrade (2026-07-03, all five batches — Focus Mode teleprompter with Enter-chained takes, per-take audio QC + room tone, live Whisper drift badges, take manager, slide previews/ON-AIR stagecraft, hot script reload + inline edit; see §5.3 and [docs/booth-upgrade-plan.md](docs/booth-upgrade-plan.md)) and became the **shared booth for every voiced channel** — the v1-based daily/weekly skills call this repo's launcher at the routine level, with v1's code untouched. The v1 [`video-explainer-system`](https://github.com/nemock/video-explainer-system) stays untouched and in production.
- **Author:** Dave Saunders (with Claude Code)
- **Date:** 2026-06-10
- **Working directory:** `/Volumes/Casima/claudeCode/explainer2`
- **Target machine:** Apple **M3 iMac, 16 GB unified memory, Metal (no CUDA)** — same verified budget rules as v1: serialize memory-heavy stages, budget against unified memory, VideoToolbox for encode.

---

## 1. Why a v2, and why a separate project

v1 proved the thesis: a topic goes in, a finished narrated, captioned, branded, multi-aspect MP4 comes out, with **zero paid SaaS in the generation path** — Kokoro TTS, torchaudio forced alignment, Playwright frame capture, ffmpeg, and a Claude *subscription* (no metered API key). It works, it's in daily use, and it stays as-is.

But v1 is a **generation pipeline**. It answers "how do I make a video about X?" It does not answer the questions that actually decide whether a channel grows:

1. **"What should this video *be*?"** — v1 starts from the operator's framing. It never looks at what already wins on YouTube for this topic: which titles get clicked, which hooks hold viewers, what the top performers cover and — more importantly — what they *miss*.
2. **"Will people keep watching?"** — v1 has a hook spec and a pacing QA, but no systematic retention engineering: open loops, re-hooks, payoff scheduling, pattern interrupts.
3. **"Does it look like one designed deck?"** — because it *is* one designed deck. There's no B-roll layer, no licensed footage, no visual variety beyond the template family.
4. **"Does it make money?"** — v1 stops at a manifest. No thumbnail engine, no SEO-shaped description, no chapters, no midroll-aware structure, no book CTA strategy, no feedback loop from published performance.
5. **"Is it pleasant to operate?"** — v1 is a CLI/skill. Fine for the author; a real *studio* wants a dashboard: see every project's stage, review a script, hit record, watch the render queue, approve the package.

Explainer2 is the studio built around the proven v1 media core. **Separate repo, separate output dirs, zero shared state** — v1 keeps running in production while v2 grows.

### The constraint that defines the product (unchanged from v1, hardened)

**No SaaS subscriptions required to operate** — with exactly **one declared exception: the operator's existing stock.adobe.com membership**, used as a *human-in-the-loop asset source*, never as an API dependency. The LLM is the operator's existing Claude subscription (via Claude Code / the Claude Agent SDK's subscription auth) — **no API key, no per-token billing.** Everything else runs on the M3: TTS, alignment, rendering, encoding, image work, even YouTube research.

---

## 2. Goals & non-goals

### Goals

- **G1 — Intelligence before generation.** Given a topic, the system researches YouTube itself: finds comparable videos, scores them as outliers vs. their channel baselines, reverse-engineers titles/hooks/structure/descriptions/thumbnails, and produces a **Blueprint** — a competitive brief that says *what our video should be and why*, including the gap none of the top performers fill. Operator approves the Blueprint before a word of script is written.
- **G2 — Retention-engineered, conversational scripts.** Scripts written to be *spoken by Dave*, in Dave's voice (talk-time library carries over), with an explicit **retention map**: cold-open hook, open loops, re-hook beats every 25–40 s, payoff scheduling, pattern interrupts, and a structured ending that feeds the next video. The retention map is a first-class artifact the operator can see and edit.
- **G3 — Operator voice as the default for flagship content.** A built-in browser **recording booth** (teleprompter + per-segment record/re-record + waveform + local audio cleanup) so the narration is Dave's actual voice. Kokoro remains the fully-headless fallback tier. Audio-first architecture preserved: real voice or TTS, same align → compose → render path.
- **G4 — Layered visuals, not just a deck.** The composition model becomes **deck base + B-roll layer + motion-graphics layer + kinetic captions + music/SFX bed**. B-roll comes from (a) the operator's Adobe Stock membership via a guided search-and-drop workflow, (b) locally generated stills/diagrams with motion (Ken Burns, parallax), and (c) the v1-style animated deck scenes. Visual variety is planned per-scene at Blueprint time.
- **G5 — One project, two formats.** A single research/script project emits **both** a long-form deep dive (16:9, 8–25 min, chapter-marked, midroll-aware) **and** a set of **Shorts** (9:16, 30–60 s) cut from its strongest beats — the content-pyramid model. Shorts carry CTAs pointing at the long-form and the channel.
- **G6 — Monetization-ready packaging.** Every project ships with: thumbnail candidates (rendered locally by the same HTML engine), title candidates ranked against the Blueprint's intelligence, an SEO-shaped description with chapters and the **book CTA (davesaunders.net)**, tags, pinned-comment text, and end-screen plan. Long-form structure respects the 8-minute midroll threshold by design, never by padding.
- **G7 — A real GUI: Mission Control.** A local web app (served from the Mac, opened in Chrome) showing every project as a card moving through stages — Intel → Blueprint → Script → Voice → Assets → Compose → Render → Package — with review/approve gates, the recording booth, the Adobe Stock asset queue, render progress, and the final package preview. Claude is reached through the **subscription** (Claude Agent SDK / Claude Code headless), never an API key.
- **G8 — Learn from what you publish.** An optional, zero-subscription analytics loop: ingest YouTube Studio CSV exports (and public stats via yt-dlp) to record which titles/hooks/structures actually performed, feeding a local "what works" memory that the Blueprint engine consults on the next project.

### Non-goals

- **N1 — No posting/scheduling *from the generation pipeline*.** The media/generation path stops at a packaged, labeled output directory + manifest, and never auto-posts a freshly produced video (first-publish stays human-in-the-loop — the YouTube upload tag-team, and a downstream poster like blotato-crosspost for the launch Shorts). **Declared exception (operator decision 2026-06-20): the `promote` command may post directly.** It re-shares the Shorts of *already-published* videos to social via Blotato to keep the back catalogue circulating — operator-invoked, one auto-rotated Short per run (never-promoted videos first, then least-recently-promoted), dry-run by default with `--fire` to publish, every send tracked in a global promotions ledger (`promotions.json` / `PROMOTIONS.md`). Caption wording for each re-share is a Claude generation step (so re-shares don't read as duplicates); the Blotato call itself is plain network I/O in the CLI, authenticated by the operator's existing Blotato key (read from env or the MCP config, never stored in the repo). This does not change the generation boundary for *producing* a video — only the back-catalogue re-share is allowed to post.
- **N2 — No talking-head avatars, no voice cloning, no photoreal generative video.** Dave's real recorded voice is the premium tier; the visual language is designed motion graphics + licensed footage.
- **N3 — No modification of v1.** v1 stays in production. v2 may *copy* proven v1 code (Kokoro wrapper, aligner, capture/mux) into its own tree, but never imports from or writes into the v1 project.
- **N4 — No cloud rendering, hosting, or multi-user anything.** One operator, one Mac.
- **N5 — No scraping that violates platform ToS for redistribution.** YouTube intelligence is metadata/transcript *analysis* for editorial decisions; competitor video/thumbnail files are referenced for study, never republished.

---

## 3. The operator's loop (key scenarios)

- **S1 — "Make me a deep dive on X."** Operator types a topic into Mission Control. Intel runs (~minutes, unattended), Blueprint card appears: "Top 12 comparable videos, 3 outliers, here's why they win, here's the gap, here are 5 title candidates and the recommended angle." Operator tweaks the angle, approves. Script appears for review with its retention map. Operator approves, clicks **Record** — Chrome opens the teleprompter, Dave reads it segment by segment. Asset stage proposes per-scene visuals; for six scenes it suggests Adobe Stock searches, opening each search in a tab; Dave licenses and drops files into the project's asset bin, which ingests/transcodes them automatically. Compose + render run unattended. Package card shows three thumbnails, the description, chapters, and the Shorts cut list. Operator approves; output directory is ready for upload.
- **S2 — "Quick Short, fully headless."** Topic in, `tier: auto` — Kokoro voice, deck-only visuals, no stock footage, 45 s vertical, packaged with title/description. The v1 experience, upgraded with Intel-informed titling.
- **S3 — "Cut Shorts from last week's deep dive."** Operator opens a finished project, picks (or accepts) the suggested strongest beats; the system re-renders those segments at 9:16 with re-hooked openings and a long-form CTA.
- **S4 — "What's working?"** Operator drops the monthly YouTube Studio CSV export onto the Learn page. The system updates its local performance memory and shows: which title patterns over/under-performed, hook retention vs. structure, CTA click-through notes. Next Blueprint cites this memory.

---

## 4. Architecture

### 4.1 The three planes

```
┌─────────────────────────────────────────────────────────────┐
│  MISSION CONTROL (local web app, FastAPI + HTML/JS, Chrome) │
│  project board · review gates · recording booth ·           │
│  asset bin · render queue · package preview · learn page    │
└──────────────┬──────────────────────────────┬───────────────┘
               │ generation requests          │ job control
┌──────────────▼───────────────┐  ┌───────────▼───────────────┐
│  GENERATION PLANE (Claude)   │  │  MEDIA PLANE (pure Python) │
│  via Claude Agent SDK using  │  │  zero LLM calls, runs      │
│  the SUBSCRIPTION (no key):  │  │  unattended:               │
│  · YouTube intel synthesis   │  │  · yt-dlp metadata fetch   │
│  · research + fact wiki      │  │  · Kokoro TTS              │
│  · blueprint + retention map │  │  · audio cleanup (ffmpeg)  │
│  · script + scene direction  │  │  · forced alignment        │
│  · asset search queries      │  │  · asset ingest/transcode  │
│  · package copy (titles,     │  │  · deck build + compositor │
│    description, thumbnails)  │  │  · Playwright frame capture│
│  · QA judgments              │  │  · ffmpeg mux (VideoToolbox)│
└──────────────────────────────┘  └────────────────────────────┘
```

The v1 architectural rule carries over and gets sharper: **Claude touches only the generation plane.** Every media-plane stage is deterministic Python that runs unattended. Mission Control orchestrates both and is itself dumb — it queues jobs and renders state from each project's manifest.

### 4.2 Claude through the subscription (G7 hard requirement)

The GUI does **not** call the Anthropic API with a key. It drives the **Claude Agent SDK**, which runs on top of the locally installed, already-logged-in Claude Code — inheriting **subscription auth**. Practically: Mission Control's backend spawns headless Claude Code sessions (`claude -p` / Agent SDK `query()`) per generation task, with each task's prompt + tools scoped to its stage. Rate limits are the subscription's; cost is $0 marginal. If the SDK/CLI is unavailable, generation stages pause with a clear "Claude not reachable" state — media-plane stages keep working.

### 4.3 Project layout

```
explainer2/
├── app/                    # Mission Control: FastAPI server + static UI
│   ├── server.py
│   ├── ui/                 # board, review pages, learn page (plain HTML/JS)
│   └── booth/              # teleprompter + MediaRecorder recording booth
├── core/
│   ├── intel/              # yt-dlp recon, outlier scoring, blueprint inputs
│   ├── research/           # fact wiki (carries v1 wiki format forward)
│   ├── script/             # retention map + script schema, talk-time reader
│   ├── voice/              # kokoro wrapper, cleanup chain, forced alignment
│   ├── assets/             # Adobe Stock queue, ingest watcher, transcode, local image gen (optional)
│   ├── compose/            # layered timeline: deck + b-roll + captions + audio bed
│   ├── render/             # Playwright capture, ffmpeg mux, multi-format
│   ├── package/            # thumbnails, titles, description, chapters, manifest
│   └── learn/              # YouTube Studio CSV ingest, performance memory
├── projects/<date>_<slug>/ # one dir per video project (see §10)
├── library/                # brand kits, music beds, SFX, talk-time link, fonts
└── skills/explainer2/      # Claude Code skill: /explainer2 CLI entry (GUI-optional)
```

---

## 5. Feature specs

### 5.1 YouTube Intelligence Engine (`core/intel`) — the headline new capability

**Input:** topic string (+ optional seed URLs of videos the operator admires).
**Tooling:** `yt-dlp` only — no YouTube API key, no quota, no subscription. It provides search (`ytsearchN:`), full metadata JSON (title, description, view/like/comment counts, duration, upload date, tags, chapters), auto-captions (the transcript), and thumbnails.

**Pipeline (media plane fetches, generation plane judges):**

1. **Sweep.** Multi-query search (topic, synonyms, question forms, "explained", "deep dive") → ~30–60 candidate videos, deduped. Filter: explainer-shaped (not vlogs/news), ≥ 90 days old preferred for stable stats, mix of durations.
2. **Outlier scoring.** For each candidate's channel, fetch recent-upload stats; compute **views ÷ channel median** — a 40× outlier on a small channel teaches more than an absolute view count on MrBeast. Keep top ~12 with at least 3 high-outlier picks.
3. **Deep pull.** For finalists: transcript (auto-subs), thumbnail image, chapter list, full description.
4. **Reverse-engineering (Claude, subscription).**
   - **Titles:** pattern classes across winners (curiosity gap, negative framing, numbered, "vs", outcome promise), word-count and capitalization norms.
   - **Hooks:** first 30 s of each transcript — what claim/visual/question opens; time-to-value.
   - **Structure:** chapters + transcript segmentation → typical beat order, where lulls happen, where comments say people clicked away or got hooked (top comments are in the metadata pull).
   - **Thumbnails:** Claude vision on the downloaded images — composition, text-on-image, face/no-face, color contrast.
   - **Descriptions/SEO:** keyword placement, link patterns, chapter usage.
   - **The gap:** what the top performers all skip, get wrong, or leave shallow — that's our angle.
5. **Output: `blueprint.md` + `blueprint.json`** — competitive table, the gap statement, recommended angle, 5 ranked title candidates, hook strategy, target duration & format(s), per-scene visual style budget (how many stock-footage scenes vs. deck scenes), and the retention map skeleton. **Operator gate:** Blueprint must be approved in Mission Control before scripting.

The intel pull is cached per topic for 14 days so re-runs are instant.

### 5.2 Retention-engineered scripting (`core/script`)

The script schema gains a **retention map** alongside the prose:

- **Cold open (0–5 s):** the gap-derived claim or question; never "hi, welcome back."
- **Open loops:** 1–3 promises made early ("at the end I'll show you the one mistake…") with their **payoff beats scheduled** and tracked — every loop opened must close, and the QA stage verifies this structurally.
- **Re-hooks:** a curiosity reset every 25–40 s (short-form) / at every chapter boundary + mid-chapter for long-form ("but here's where it gets weird").
- **Pattern interrupts:** the scene plan must change visual mode (deck → footage → diagram → figure) at least every N seconds; the compositor enforces this.
- **Midroll-aware structure (long-form):** natural chapter boundaries land such that an 8-min+ video has clean midroll seams; depth comes from the research wiki (v1's "deepen, don't pad" gate carries over verbatim).
- **Ending:** no "outro decay" — the last 15 s pivots directly into the CTA stack (book → next video) while the payoff is still landing.
- **Voice:** conversational register, written-to-be-spoken (contractions, short sentences, direct address), flavored by the **talk-time library** (quote verbatim, adapt positions, never fabricate — v1.1 rules carry over).

Mission Control shows the script side-by-side with its retention map and a **live read-time estimate per segment**; the operator edits before recording.

### 5.3 Recording booth (`app/booth`) — operator voice, first-class

Carries v1.1 §18 forward as a core feature, upgraded:

- Browser teleprompter, **per-segment** record / re-record / playback, waveform display, retake history; segments POST directly into the project's `audio/raw/`.
- **Cleanup chain** (local ffmpeg: rumble/denoise/de-ess/EQ/compress/two-pass loudnorm to −14 LUFS) runs automatically per segment — the VocalEnhancer recipe, vendored into `core/voice`.
- **Ad-lib tolerance:** local Whisper ASR on each take → diff vs. script. Small drift: captions follow what Dave *actually said*. Large drift: flag the segment for re-record or accept-with-rewrite.
- **Kokoro fallback per segment:** any segment can be left to Kokoro (e.g. a pronunciation-heavy aside), and tiers can mix — though flagship videos default to all-operator.

**Booth 2.0 — shipped 2026-07-03** (operator-approved slate; build plan + batch log in [docs/booth-upgrade-plan.md](docs/booth-upgrade-plan.md), refined live during the first real session):

- **Focus Mode teleprompter.** One card full-screen; `Space` = 3-2-1 countdown into record; **`Enter` mid-record accepts the take and rolls straight into the next card** (quick "GO" beat) — one key between cards. Enter never silently navigates an unrecorded card; the chain parks safely on already-recorded cards. Click a card in list view to set the focus target. Long cards auto-shrink and scroll (no clipping).
- **In-booth quality gates.** Per-take audio QC on save (peak/clipping, level, duration vs. the ~150 wpm target → green/amber/red chips); a 3-s **room-tone check** rates the noise floor before recording; live pace readout; a session **wrap report** (`work/booth_session.json`) on Finish.
- **The ear.** A serialized local-Whisper worker badges every take *verbatim / ad-lib N% / re-record* with a word-level diff modal, minutes-fresh while the operator is still in the chair; it **defers while a render holds the machine render lock** (16 GB budget). On Finish the booth writes `work/adlib_report.json` from these in-session results — **the standalone `adlib` stage is retired to a fallback** (2026-07-03: run it only when the report is missing or has `unchecked` segments). A **take manager** lists archived takes and can promote any of them back to primary (archive numbering is collision-safe).
- **Script agility.** `/segments` hot-reloads the script from disk (no booth restart to pick up edits) and cards are **editable inline** — edits write back to `script.json` (or `shorts/plan.json` for hook/outro cards) with a one-time per-session backup.
- **Stagecraft.** ON-AIR recording state (red glow, live waveform behind the text), per-card **slide mini-previews** from `deck.json`, mic picker with an always-on level bar, continuity playback (hear the tail of the previous card, then roll).
- **One booth, every channel.** `tools/launch_booth.py` is the shared entry point: detached + `caffeinate`d launches, `--wait` (durable Finish sentinel), `--status` (DONE/PENDING/NOT_OPEN for scheduled checker tasks), port auto-fallback when :8765 is busy, and schema-tolerant project loading — the v1-based daily/weekly skills (Founder Tip Tuesday, Monday MedTech, the daily founder tip) record through this booth via routine-level adoption, **with zero changes to v1's code** (N3 holds).

### 5.4 Adobe Stock assist (`core/assets`) — the one subscription, used the right way

Not an API integration. A **guided human-in-the-loop workflow** that respects how Dave actually licenses assets:

1. At Asset stage, each scene marked `visual: footage` gets 2–3 Claude-written **search query suggestions** (with duration/orientation/color hints).
2. Mission Control lists them as an **asset queue**; clicking one opens `stock.adobe.com` search in a Chrome tab with the query prefilled.
3. Dave licenses/downloads as usual; the project's `assets/inbox/` is a **watched folder** — anything dropped there is auto-ingested: probed, transcoded to mezzanine (ProRes proxy or high-bitrate H.264), cropped/reframed per target aspect, color-tagged bt709, and **matched to its scene** (the queue tracks which search it came from; ambiguous drops get a one-click assignment in the UI).
4. License provenance recorded per asset in the manifest (Adobe Stock asset ID parsed from filename where present) — the AI-disclosure/provenance discipline from v1 extends to licensed media.
5. **Every footage scene has a designed fallback** (deck/diagram treatment), so skipping the stock step never blocks a render.

### 5.5 Layered compositor (`core/compose` + `core/render`)

v1 rendered one deck. v2 renders a **layer stack**, still deterministic, still HTML-based (one renderer to rule them all):

- **Layer 0 — base:** deck scene (v1 engine, carried forward) *or* full-bleed B-roll clip *or* Ken Burns/parallax still.
- **Layer 1 — motion graphics:** lower thirds, callouts, animated diagrams, progress bar (a retention device for long-form).
- **Layer 2 — kinetic captions:** word-synced from alignment, per-platform safe zones.
- **Audio:** narration + music bed (auto-duck under voice) + transition SFX from a vetted local library.
- B-roll playback inside the capture page uses pre-extracted frame sequences or `<video>` elements driven by the **virtual clock** (CDP), preserving v1's determinism guarantee: same project → same frames.
- **Render economics on 16 GB:** stages stay serialized; long-form renders chunk per chapter and concat (the local `deepdive` skill already proved conform→concat→validate on this machine). Target: 20-min 1080p deep dive renders unattended in well under an hour.

### 5.6 Dual-format emission (G5)

A project declares `formats: [deepdive_16x9, shorts_9x16]`. After the long-form master is composed, the **Shorts cutter** proposes 3–5 beats scored by hook-worthiness (a self-contained claim + payoff inside 45 s), re-renders each at 9:16 with a fresh 2-s cold open and an end-card CTA → "full breakdown on the channel." Shorts inherit all alignment/caption data — no re-recording.

### 5.7 Packaging & monetization (`core/package`)

- **Thumbnails:** 3 candidates rendered by the same HTML engine (1280×720 PNG) from thumbnail templates informed by the Blueprint's thumbnail analysis — large text ≤ 4 words, high contrast, brand-consistent. (Optional later: local image-gen backgrounds via MLX/Draw Things — strictly optional, never in the critical path.)
- **Titles:** the Blueprint's 5 candidates re-ranked post-script; operator picks in the UI.
- **Description:** SEO-shaped first 2 lines, chapter timestamps (from the retention map), **book CTA block (davesaunders.net) always present**, channel links, AI-disclosure line for TTS-tier videos.
- **Tags, pinned-comment text, end-screen plan** (what to point the end-screen slots at).
- **Manifest v2:** versioned JSON carrying everything above + per-asset license provenance + per-format file list. Downstream poster contract preserved from v1.

### 5.8 Learn loop (`core/learn`) — optional, zero-subscription

**Shipped 2026-07-03** as `src/explainer2/learn.py` + `bin/explainer2 learn {refresh,ingest,report}`:

- `learn refresh` — public stat snapshots (views/likes/comments) via yt-dlp for every project whose `package/meta.json` carries a `youtube_url`; backfills missing `posted` dates from YouTube's own upload date. Unattended, no auth.
- `learn ingest --csv <export>` — a manually-downloaded **YouTube Studio CSV** (free, no API) layers in the private metrics: impressions, CTR, average view duration, watch hours, subscribers. Robust case-insensitive header mapping; skips the Total row and untracked IDs.
- Store: `channel/learn/performance.json` — per-video title/posted/duration/deterministic title features + dated snapshots, one per (date, source), same-day re-runs update in place. **Lives behind the `channel/` symlink in the private content repo — analytics never land in the public code repo.**
- `learn report` — rewrites `channel/learn/REPORT.md`: per-video views/day vs. channel median, breakout/laggard lists, and title-feature aggregates (question / number / second person / negation / two-part). The blueprint playbook (§7) reads and cites it before ranking titles — as a tiebreaker, never a veto. (First real report, 2026-07-03: negation titles at ~2× the median of non-negation — the PRD's imagined example turned out to be roughly true.)

---

## 6. Mission Control (the GUI) — scope and stack

- **Stack:** FastAPI + vanilla HTML/JS served at `localhost`, opened in Chrome. Reuses the team's (Dave + Claude's) strongest medium — the same HTML/CSS/JS muscle that builds the decks builds the UI. No Electron/Tauri build complexity in v2.0; a menu-bar wrapper is a later nicety.
- **Pages:** Board (project cards × stages, with review gates as buttons) · Blueprint review · Script review (prose + retention map + read-time) · Recording booth · Asset queue/bin · Render queue (progress, logs) · Package preview (thumbnails/titles/description picker) · Learn.
- **Jobs:** a simple SQLite-backed queue; media-plane jobs run as subprocesses with progress files; generation-plane jobs run as headless Claude sessions. Everything restartable; project state lives in the project dir, not the server.
- **CLI parity:** every GUI action has a CLI verb (`explainer2 intel|blueprint|script|record|assets|compose|render|package <project>`), so the system remains scriptable/schedulable and the GUI is never load-bearing.

---

## 7. Content tiers

| Tier | Voice | Visuals | Formats | Mode |
|---|---|---|---|---|
| **Auto Short** | Kokoro | deck-only | 9:16 | fully headless (v1 parity + Intel titling) |
| **Standard** | Kokoro or operator | deck + a few stock scenes | 9:16 and/or 16:9 | light review gates |
| **Flagship deep dive** | **operator** | full layer stack, stock B-roll, chapters, progress bar | 16:9 master + Shorts cuts | full review gates: Blueprint → Script → Record → Package |

---

## 8. Risks & mitigations

| # | Risk | Mitigation |
|---|---|---|
| R1 | **yt-dlp breakage / YouTube changes** | Pin + auto-update yt-dlp; intel degrades gracefully (cached blueprints, manual seed URLs); intel is advisory, never blocks generation. |
| R2 | **Subscription-auth headless Claude changes behavior** | Isolate behind one adapter in `core/`; CLI fallback is interactive Claude Code with the `/explainer2` skill. |
| R3 | **16 GB ceiling with B-roll transcode + Chrome + ffmpeg** | Hard serialization; mezzanine proxies at 1080p; chapter-chunked renders; never hold more than one chapter's frames on disk uncompressed. |
| R4 | **Stock-footage scenes stall the pipeline waiting on the human** | Every footage scene has a deck fallback; render can proceed `--without-pending-assets` and the scene list shows what was substituted. |
| R5 | **Retention features become formulaic** | Retention map is a *plan the operator edits*, not an auto-stamp; Learn loop measures whether the devices actually work on this channel. |
| R6 | **Scope: GUI swallows the project** | Mission Control v2.0 is read-state + buttons + two custom pages (booth, asset queue). No realtime frameworks, no auth, no design system. CLI parity keeps it honest. |
| R7 | **Copying v1 code forks bugs** | Vendored modules (kokoro, align, capture, mux) copied once with a `VENDORED_FROM` header noting v1 commit; divergence is expected and fine — v1 is frozen, not shared. |
| R8 | **ToS/compliance on competitor analysis** | Metadata/transcript analysis for editorial judgment only; no republication of competitor media; thumbnails fetched for private study; manifest carries AI-disclosure + license provenance. |

---

## 9. Build phases

- **Phase 0 — Skeleton + vendored core (week 1).** Repo scaffold, project-dir schema, manifest v2, vendor v1's narrate/align/capture/mux modules, CLI entry. *Accept:* v1-parity headless Short renders end-to-end in the new tree. **✓ Shipped (2026-06-10).**
- **Phase 1 — Intelligence Engine.** yt-dlp sweep → outlier scoring → deep pull → Blueprint generation via subscription Claude. *Accept:* topic in, approved-quality `blueprint.md` out, for 3 real topics on Dave's content calendar. **✓ Shipped (2026-06-10).**
- **Phase 2 — Retention scripting + recording booth.** Script schema with retention map; teleprompter/recorder with cleanup + ad-lib ASR alignment. *Accept:* Dave records a full script in his voice and the system produces aligned, captioned narration with zero external apps. **✓ Shipped (2026-06-10).**
- **Phase 3 — Layered compositor + Adobe Stock assist.** Asset queue, watched-folder ingest, layer-stack renderer with deterministic B-roll. *Accept:* S1 scenario — a video mixing deck scenes and licensed footage renders deterministically. **✓ Shipped (asset assist 2026-06-10; deterministic mixed deck+footage render demonstrated).**
- **Phase 4 — Mission Control.** Board, gates, render queue, package preview wired over the existing CLI verbs. *Accept:* a full Flagship project run start-to-finish without touching a terminal. **○ Planned (not built — the review gates run from the CLI in the meantime).**
- **Phase 5 — Dual-format + packaging + Learn.** Shorts cutter, thumbnail engine, description/chapters/CTA package, CSV ingest. *Accept:* one real deep dive published to the channel with its Shorts, fully packaged by the system; first Learn report generated 30 days later. **✅ Complete — Shorts cutter (2026-06-11), thumbnail engine, the description/chapters/CTA/manifest package, and Learn (2026-07-03: yt-dlp refresh + Studio CSV ingest + REPORT.md, first real report generated same day) are all shipped.**

**Beyond the original plan** (additions made after the phase ladder was drawn): a default **Remotion motion-graphics engine** (`--engine remotion`, 2026-06-24) now drives the visual layer (the legacy deck engine remains as `--engine deck`); a written **article companion** ships with each package; **illustrative composed thumbnails** are now the *standard* (operator directive 2026-06-29: a composed scene with the operator in it — ideally opposite a "foil" character — beats the plain cutout template, which remains the fallback); the operator-invoked **`promote`** command (2026-06-20, §N1) re-shares already-published Shorts via Blotato (dry-run by default); **Booth 2.0** shipped all five upgrade batches in one day (2026-07-03, §5.3) and the booth became the **shared recorder for the v1-based daily/weekly channels** via routine-level adoption (v1 code untouched); and the standing **music bed** switched to an upbeat presentation track (2026-06-29) — which also stopped triggering the benign-but-recurring Content ID match the old café bed produced at upload.

Each phase ends shippable; the system is useful from Phase 1 onward (Blueprints alone improve the current v1 workflow).

---

## 10. Project directory contract

```
projects/2026-06-10_topic-slug/
├── intel/            # candidates.json, transcripts/, thumbs/, blueprint.{md,json}
├── wiki/             # sourced facts (v1 format)
├── script/           # script.json (prose + retention map + scene plan)
├── audio/            # raw/ takes, cleaned/, narration.wav, alignment.json
├── assets/           # inbox/ (watched), mezzanine/, licenses.json
├── deck/             # HTML scenes + compositor timeline
├── video/            # deepdive_16x9.mp4, shorts/*.mp4, captions/
├── package/          # thumbnails/, description.md, titles.json, chapters, end-screen plan
└── manifest.json     # versioned; the only file a downstream tool needs
```

---

## 11. Open questions (decide during Phase 0–1)

1. Mezzanine codec for stock B-roll on this machine: ProRes proxy (big, fast) vs. high-bitrate H.264 (small, slower seeks) — benchmark both on a real 20-min project.
2. Whisper flavor for ad-lib ASR: `mlx-whisper` (Metal-native) vs. `openai-whisper` small — pick by speed/accuracy on Dave's recorded voice.
3. Local image-gen for thumbnail backgrounds (Draw Things / MLX Flux-schnell on 16 GB): worth the memory pressure, or HTML-composed thumbnails are enough? Default: HTML-only until proven otherwise.
4. Music: vetted local library only, or experiment with local MusicGen-small for bespoke beds? Default: library only.
5. ~~Repo name on GitHub~~ — **decided 2026-06-10: `explainer-studio`** (https://github.com/nemock/explainer-studio, public). Product name "Explainer Studio"; local dir and CLI/package stay `explainer2`.

---

*Generation-only at the boundary for producing a video (the pipeline never auto-posts a new video). Declared exception (2026-06-20): the operator-invoked `promote` command re-shares already-published Shorts directly via Blotato, tracked in a promotions ledger. One declared subscription exception for assets: stock.adobe.com, human-in-the-loop. LLM access exclusively via the operator's Claude subscription. v1 remains untouched and in production.*
