# Motion Playbook — the Remotion visual-storytelling vocabulary

The animated successor to the deck-playbook. The deck engine gives a catalog of
mostly-static slide types; Remotion turns the visual layer into a **motion-graphics
programming environment** where every pixel is a function of **time, the audio, and
data**. The job of the visual stops being "display the point" and becomes **"perform
the explanation"** — a number *counts* as it's spoken, a chart *builds* on the cue, a
document line *highlights* as it's read, a diagram *assembles* as it's described.

Status (2026-06-24): the **vocabulary + doctrine** below are the standard. The
**Remotion render engine** (a `--engine remotion`, spec-fed component library) is the
next build; the pilots in `experiments/remotion-pilot/` (kinetic hook, document
highlight, synced stat-counter + draining bar) are the proof it works locally and free.

Read this file before authoring any video's motion spec.

---

## 0. The contract (read once)

- **Visuals perform, not decorate.** Every scene's motion must carry meaning — it
  shows the thing the narration is saying. Motion that doesn't explain is noise; cut it.
- **Spec-driven — Claude authors DATA, not bespoke code.** You write a motion spec
  (scenes keyed 1:1 to script segments, like `deck.json`); a fixed, branded component
  library renders it. You pick components and supply fields; you do not hand-write React
  per video. The React templates live in the repo and are touched rarely.
- **Deterministic by construction.** All motion via `useCurrentFrame()` +
  `interpolate()` + `spring()` + `Easing`. **CSS transitions/animations and Tailwind
  animation classes are FORBIDDEN — they do not render.** No `Date.now()`/`Math.random()`
  unseeded (seed off the segment index if you need variation). This IS the project's
  existing determinism hard rule; Remotion enforces it for us.
- **Brand-locked.** The motion system (palette, type, background, spring feel) is fixed.
  Per-video you choose components and feed data — you do not restyle.
- **Dynamic is the NORM, not the exception** (operator directive, 2026-06-24). This is a
  headless, fully-produced channel; viewers expect motion-design energy, and we now have
  the tools to deliver it. Use the **full breadth** of the library — synced data-viz,
  build-on diagrams, compositing, transitions, **3D**, light leaks, the lot — to make
  every video *pop*. There is **no rule against being visually dynamic**; lean in.
  - The only standing guardrails (these are not a cap on energy): (1) **determinism**
    (frame-driven, no CSS animation), (2) **brand cohesion**, (3) **legibility** (text
    always readable; motion never fights the words), (4) **no jank** (smooth springs/
    easing, not stutter), and (5) motion still **serves the story** — spectacle is welcome,
    but it should ride on the explanation, not bury it. Within those, more is the default.

## 1. The brand motion system (the constants)

- **Palette:** navy radial background `#15314a → #0d1428 → #090d1c` (hotspot to edge);
  **red `#ff4d4d`** (negative / alarm / the contrarian accent), **green `#3ddc84`**
  (positive / active word / brand), **white `#f5f7ff`** (body). Numbers use
  `font-variant-numeric: tabular-nums` so counters don't jitter.
- **Type:** heavy display weight (800–900), system stack or a single brand face via
  `@remotion/google-fonts`. Kickers are UPPERCASE + letter-spaced + green.
- **Background:** the navy radial with a slow "breathing" scale (≈1 → 1.06 across the
  scene) so it is never dead-static. Optional faint parallax drift.
- **House motion:** the default entrance is a spring (`{damping: 18}`) or
  `interpolate(..., {easing: Easing.bezier(0.16, 1, 0.3, 1)})`. Use the SAME entrance
  everywhere so the whole video feels like one system. Exits are quick fades.
- **Safe areas:** 9:16 keeps the bottom ~14% clear for captions; 16:9 keeps a lower-third
  band. Captions sit above the safe inset.
- **Loop-safety (shorts):** the last frame should hand back to the first (no hard stop).

## 2. The expression catalog (the vocabulary)

Each entry: **what · when · spec fields · motion · don't.**

### A. Typography & text
- **KineticHook** — the cold open. A punchy headline springs in, accent word in red/green.
  *fields:* `kicker, headline, accent[]`. *Don't* dump the spoken sentence; this is the idea.
- **KineticCaptions** — word-synced caption window (TikTok-style), active word in green,
  driven by the alignment JSON. **Baseline on every scene** (long-form and shorts).
- **BuildHeadline** — a key line revealed word-by-word in time with delivery.
- **Reframe** — `before → after` with the old phrase struck/dissolving into the new
  (e.g., "execution solved" → "execution **moved**"). One focal idea.
- **PunchWord** — one giant word, max energy. Reserve for the midroll seam / the turn.
- **Quote** — verbatim line + attribution reveal. For sourced quotes (book, named expert).
- **LowerThird** — name/title chip. Credibility beat, on-screen source attributions.

### B. Data-viz (synced to the spoken number — never invent a figure)
- **StatCounter** — counts up/down to the figure, color by sign, **lands on the cue word**
  (e.g., −$1,000 hitting on "into the red"). *fields:* `from, to, prefix/suffix, cueWord`.
- **BuildBars / BarRace** — bars grow on; ranked comparisons reorder.
- **DrawLine** — a line chart drawn on via stroke reveal. Trends, and the *plummet*
  (Lucent $80 → 52¢, a valuation crash) — decline animated is gut-punch.
- **Ring / Donut** — sweeps to a percentage.
- **Waterfall** — builds step-by-step (revenue → costs → runway).
- **Delta / Compare** — `from → to` with a change badge.
- **Pictograph** — X-of-Y dots filling ("42 of 100 startups…").
- **Gauge / Drain** — a depleting bar (runway burning down; the Project Vend balance).
*Rule:* tie the key moment to the alignment cue; tabular-nums; figures trace to wiki/intel.

### C. Diagrams & process (build-on — the teaching core)
- **StepFlow** — nodes assemble and arrows draw, one node per beat (idea→MVP→launch→scale).
- **DecisionTree / Branch** — a fork resolving as you explain the choice.
- **Funnel** — stages narrowing; great for sales/customer math.
- **Timeline** — events appear along a line in time (AI-winter cycles; a company history).
- **Cycle** — a loop diagram (the hype cycle; a flywheel).
*Rule:* build in sync with the explanation; never reveal the whole diagram at once.

### D. Document & evidence (the #38 lane, generalized)
- **DocReveal** — scroll a real page/screenshot.
- **DocZoomAnnotate** — pan/zoom to a line + highlight-wipe / underline / circle / redact.
  The generalized version of the #38 marker; the document IS the proof.
- **SideBySide** — claim vs. reality / headline vs. fine print, animating in.
- **CodeType / Terminal** — typed code or terminal output (AI/tech beats).
*Rule:* short fair-use excerpts, cited on-screen; crop tight (see deck-playbook §4b).

### E. Media & compositing (the safe replacement for hand-rolled ffmpeg B-roll)
- **Footage** — full-bleed licensed B-roll with deterministic Ken Burns.
- **Cutaway** — B-roll over a window inside the scene (before/after framing).
- **PiP** — picture-in-picture.
- **MaskReveal** — shape/wipe reveal of footage or image.
- **BeforeAfterSlider** — a wipe between two states.
*Note:* use `@remotion/media` `<Video>` / `<OffthreadVideo>`. **This retires the raw
`ffmpeg` motion-splice** that OOM-killed renders twice (2026-06-23) — compositing becomes
a deterministic Remotion layer, not a fragile hand-rolled pass.
*Looping:* the **Footage** component uses `<Video muted loop>` (not `<OffthreadVideo>`) so a
B-roll clip shorter than its segment loops instead of freezing on the last frame.
`OffthreadVideo` has no `loop` prop (Remotion 4.0.401) — looping it would need a
`<Loop durationInFrames>` wrapper fed by async `getVideoMetadata` + `delayRender`, a render-
stall risk for unattended encodes. Don't "correct" footage back to `OffthreadVideo` (fixed
2026-06-26). The Self-QA "`OffthreadVideo` for clips" guidance still holds for the rare
full-bleed shot.

### F. Transitions & connective tissue
- **Motivated transitions** (`@remotion/transitions`): fade / slide / wipe / clockWipe /
  shared-element. Use to *connect related beats*; hard-cut between unrelated ones.
- **ChapterMarker / SectionDivider** — at beat boundaries (the chapter list).
- **BrandSting** — a short FWF intro/outro animation, built once, reused every video.
- **Background drift / parallax** — ambient life under everything.

### G. Accents & ecosystem (use them — this is where videos *pop*)
Reach for these freely; they are a big part of "dynamic is the norm" (§0).
- **3D** (`@remotion/three` / React Three Fiber) — **a hero tool, not a rarity.** Rotating
  objects, depth, a 3D chart or globe, a title in space, parallax camera moves. Use it for
  cold opens, the midroll seam, and any "wow" beat. (Watch the M3/16GB budget — keep scenes
  reasonable; see §6.)
- **Lottie** (`@remotion/lottie`) — designer-made icon/motion assets.
- **AudioWaveform** (`visualizeAudio`) — voice-reactive bars/rings on hooks & transitions.
- **MotionBlur** (`@remotion/motion-blur`) — on fast moves, for that produced feel.
- **LightLeaks** (`@remotion/light-leaks`) — warmth/flares across transitions.
- **HTML-in-canvas / shaders, GIFs, MapLibre flyovers, text-animation kits** — all fair game
  (load the matching sub-rule from the `remotion` skill on demand).
- **Confetti / particles** — fine for genuine payoffs; just keep them legible and on-brand.

## 3. Choosing the expression — content → vocabulary

| When the narration is… | Reach for |
|---|---|
| saying a number / stat | StatCounter, BuildBars, Gauge/Drain, Pictograph |
| a trend, decline, or crash | DrawLine (draw-on / plummet) |
| a process / framework / steps | StepFlow, Funnel, DecisionTree |
| a claim vs. the reality | SideBySide, Reframe |
| quoting a document | DocZoomAnnotate, SideBySide, Quote |
| a story across time / an era | Timeline |
| a checklist / saveable rubric | BuildList (numbered reveal) |
| a verbatim line from a person | Quote + LowerThird |
| establishing credibility / a source | LowerThird |
| an anecdote with footage | Footage, Cutaway, PiP |
| the cold open | KineticHook |
| the midroll seam / the turn | PunchWord + a major transition |
| every scene, underneath | KineticCaptions + background drift |

## 4. Energy & cadence (how to raise dynamics without jank)

- **A motion beat at least every ~15–25s of script time** — an entrance, a build, or a
  transition. This is what kills the "visual dead air during speech" QA warning that flat
  decks trigger (e.g., #38's 39s of dead air came from static cards).
- **Biggest motion at the midroll seam** (PunchWord or a major transition) — the energy peak.
- **Sync to narration wherever a cue exists.** The alignment JSON is the conductor:
  counters land on the number, highlights wipe on the phrase, nodes light on the name.
- **One focal motion at a time.** Lead the eye; don't animate everything at once.
- **Spring/easing discipline.** No linear, robotic moves — use the house spring/bezier.
- **Motion should carry the explanation** — but on this channel the default is MORE, not
  less. A scene that's just static text + captions is the floor, not the goal; give it a
  build, a 3D element, a transition, a reactive accent. "Could this beat be more alive?" is
  the question to keep asking.
- **The bar is "make it pop"** (operator directive 2026-06-24). Push the dynamism; the only
  brakes are the five guardrails in §0 (determinism, brand, legibility, no jank, serves the
  story). Don't self-censor energy for fear of "too much" — fear flat.

## 5. The spec contract (data in, motion out)

- A video's motion is a **`motion.json`** — `scenes[]` keyed 1:1 to script segments
  (`id` matches the script `slide`), each `{id, component, fields, sync?}`. Same 1:1
  discipline as `deck.json`.
- `fields` = that component's data (headline, value, image, items, points…).
- `sync` = optional cue word/time the component lands its key moment on; defaults to the
  alignment JSON for that segment.
- **Duration is computed**, not hand-set: `calculateMetadata` derives `durationInFrames`
  from the narration audio (Mediabunny / get-audio-duration). Never hardcode frame counts.
- **Determinism:** `useCurrentFrame`/`interpolate`/`spring` only; no CSS animation; no
  unseeded random/time.
- **Validation:** each component's props are a **Zod schema** so a bad spec fails loudly,
  early — not as a silent broken render.
- **Assets** under `public/` (or the project assets), referenced via `staticFile()`.

## 6. Pipeline integration

- **Remotion is the DEFAULT engine (2026-06-24).** `shorts`, `media`, and `render` all
  default to `--engine remotion`; the deck engine is the `--engine deck` fallback (and the
  reference for slide-type semantics). Both consume the same 1:1 data spec, so a project
  renders either way. Remotion needs the Node toolchain (`npm install` in `remotion/`); the
  engine raises a clear error if it's missing.
- **Render discipline unchanged.** The heavy encode still goes through the render-lock and
  launches **detached + caffeinated** (SKILL §7) — Remotion's headless-Chrome+ffmpeg render
  is exactly the kind of heavy job those rules exist for. Modest concurrency on the M3/16GB;
  `OffthreadVideo` for clips; jpeg frames.
- **Per-scene fallback:** a scene with no Remotion component falls back to its deck slide,
  so a render never breaks on a missing template.
- **Captions:** kinetic captions render from the alignment JSON; the `.srt`/`.vtt` sidecar
  still ships for YouTube.
- **Deck-type → motion-component map** (the migration table): `statement`→KineticHook/
  Headline · `stat`/`statgrid`→StatCounter · `delta`/`compare`→Delta/SideBySide ·
  `diagram`/`ranked`→BuildBars · `trend`→DrawLine · `waterfall`→Waterfall ·
  `timeline`→Timeline · `list`/`steps`→BuildList/StepFlow · `quote`→Quote ·
  `punch`→PunchWord · `reframe`→Reframe · `figure`→DocZoomAnnotate · `footage`→Footage/
  Cutaway · `payoff`/`cta`→BrandSting. Until the engine ships, the **deck-playbook governs**.

## 7. Self-QA checklist (run before rendering a motion spec)

- [ ] Every scene has a clear motion ROLE (performs the point; not decoration).
- [ ] Synced to narration where a cue exists; counters land on the spoken number.
- [ ] Brand constants only (palette / type / bg / house spring); nothing off-brand.
- [ ] No dead air: no scene static for its whole duration during speech; a motion beat
      ≤ every ~20s.
- [ ] Transitions are motivated; the biggest motion is at the midroll seam.
- [ ] Shorts are loop-safe; the 9:16 / 16:9 safe zones are respected.
- [ ] Determinism: `useCurrentFrame`/`interpolate`/`spring` only; NO CSS animation/Tailwind
      animation; no unseeded random/time.
- [ ] Figures trace to wiki/intel; no invented numbers; fair-use docs cited.
- [ ] Performance within M3/16GB (`OffthreadVideo` for clips; modest concurrency). *Footage
      is the exception — it uses `<Video loop>` so short B-roll loops; see §E.*
- [ ] One-frame `npx remotion still` check on the key frames before the full render.

## 8. Authoring procedure

1. Read this file, the approved `script.json`, the alignment JSON, and the blueprint's
   visual budget.
2. For each script segment, choose a component from §2 via the §3 content→vocabulary map.
3. Write `motion.json` (DATA — components + fields + sync), 1:1 with the script.
4. Still-check the key frames (`npx remotion still <comp> --frame=N`).
5. Render via the Remotion engine (render-lock + detached, SKILL §7).
6. QA against §7; fix; at most one re-render cycle.

## Appendix — technical guardrails (from the Remotion best-practices skill)

- Animate with `useCurrentFrame()` + `interpolate()` + `Easing`/`spring()`. **CSS
  transitions/animations and Tailwind animation classes do not render — never use them.**
- Assets in `public/`, referenced via `staticFile()`. `<Img>` for images; `<Video>` /
  `<OffthreadVideo>` and `<Audio>` from `@remotion/media`.
- Use `<Sequence from/durationInFrames>` for timing (`layout="none"` for inline content).
- `calculateMetadata` for data-driven duration/dimensions/props; **Zod** for typed params.
- Fonts via `@remotion/google-fonts`. Preview in `npx remotion studio`; single-frame
  sanity via `npx remotion still`.
- Sub-rules available in the `remotion` skill (load on demand): transitions, audio-
  visualization, lottie, 3d, maps, text-animations, timing, captions, videos.
