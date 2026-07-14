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

Status (2026-07-04): the engine is SHIPPED and default, and the **narration-sync
system is implemented** — the §5 `cues` contract, the §2H annotation layer
(hand-drawn arrows/circles/underlines + the operator's CopyDoodles stamps), the
`schematic` guided diagram, and Figure guided tours (`moves`/`assemble`) all render.
Verify new specs against `remotion/motion-lab.json` (still-frame fixture).

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
- **Schematic** (IMPLEMENTED 2026-07-04, deck type `schematic`) — the guided diagram:
  nodes at authored 0-1 positions spring in per **cued stage**, edges draw on
  underneath, and a **camera** drifts/zooms to the active region so the viewer's eye
  is led through the picture as the narration walks it. `sketch: true` gives seeded
  hand-drawn node outlines. Fields: `nodes[{id,label,sub?,x,y,w?,kind?}]`,
  `edges[{from,to,label?,kind?}]`, `stages[{reveal:[ids],cue}]`,
  `camera[{center,zoom,stage}]`. 5–9 nodes max (legibility). Use for anything
  non-linear: org maps, buying chains, system diagrams, decision forks, cycles.
- **StepFlow** — the linear pipeline (idea→MVP→launch→scale); now lands each node on
  its narration cue automatically (auto item-sync, §5).
- **Funnel** — stages narrowing; great for sales/customer math (auto item-synced).
- **Timeline** — events appear along a line in time (auto item-synced).
*Rule:* build in sync with the explanation; never reveal the whole diagram at once.

### H. The annotation layer (IMPLEMENTED 2026-07-04 — hand-drawn, narration-cued)
Any slide can carry `annotations: [...]` — an overlay ON TOP of the scene, drawn in
0-1 FULL-FRAME space, each element firing on a spoken cue. Two families, freely mixed:
- **Vector (rough.js, seeded — true draw-on):** `arrow` (`from`→`to`, auto arrowhead),
  `circle` (`at`+`w`/`h`), `underline` (`at`+`w`), `strike` (`from`→`to`), `box`
  (`at`+`w`/`h`). Options: `color: green|red|white` (default green), `label` (small
  italic tag near the target), `cue: "<spoken phrase>"`.
- **Doodle stamps (`kind: "doodle"`)** — the operator's licensed **CopyDoodles**
  library (real Sharpie scans): `name` from `library/doodles/manifest.json`
  (106 pieces: arrows/ovals/boxes/brackets/bullets/crossouts/lines/misc/numbers/
  shapes), `at`+`w`, `color` tint, `reveal: pop|wipe`, optional `rotate`. Authentic
  hand-drawn character; use for emphasis stamps (check, question marks, starburst,
  circled scribbles). The vector kinds beat doodles for point-to-point geometry;
  doodles beat vectors for personality. LICENSE: the files are gitignored
  (`library/`), staged per-render into the project's private work dir, and must
  never enter a public repo — flattened into rendered video is the permitted use.
*Rules:* one focal annotation at a time; annotations reinforce the narration's exact
words (set `cue` to the phrase being said); keep labels ≥ caption size; on `figure`
slides prefer the figure's own image-space `moves`/`highlight` for document work and
frame-space annotations for editorial arrows.

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
- **PaperSting** — the default FWF intro/outro (2026-07-14). A layered cut-paper "launch":
  the paper D card settles, the cream paper rocket flies in from off-screen trailing a fan
  of mixed-color paper flames and lands into the D to form the mark, then the wordmark
  rises (INTRO ~3.5s). `fields.outro:true` gives the calm finished-mark card + subtitle
  (OUTRO ~2.5s). Assets: `remotion/public/sting_paper_{d,rocket}.png` (Magnific paper-
  stylized from Dave's real D-rocket logo). **The intro length is the narration offset —
  now 3.5s (was 2.5s); see memory [[gag-splice-sting-offset]].** Component:
  `remotion/src/components/PaperSting.tsx`.
- **BrandSting** — the prior wordmark intro/outro (scale-in + light sweep). Retained as a
  fallback; PaperSting is the default the engine inserts.
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

### 4b. The visual-variety floor (QUANTIFIED — added 2026-07-06 after #18)

The doctrine above was not enough: video #18 shipped with **14 of 22 slides
typography-only, zero data-viz, zero footage/figure slides, and zero narration
cues**, and the operator watched it and called it a narrated PowerPoint. The
"dynamic is the norm" language reads as permission; this section is the
REQUIREMENT. Run the census below on every deck before render — a deck that
fails the floor is not ready, exactly like a script that fails the word budget.

**Text-type slides** for this census: `statement`, `reframe`, `punch`, `quote`,
`highlight`, `define`, `list` — anything whose only visual is typography.
Everything else (data-viz, `schematic`, `steps`, `funnel`, `timeline`,
`figure`, `footage`, compare-with-imagery, 3D) is a **performing** slide.

The floor (all MUST pass):

1. **Text-type slides ≤ 40% of the deck**, and **never more than 2 in a row**.
   A third consecutive text card means one of them is really a diagram, a
   number, a document, or footage wearing a text costume — find it.
2. **Every number the narration speaks gets a data-viz slide** (StatCounter /
   BuildBars / DrawLine / Pictograph / Gauge / Waterfall…) with a `cues.land`
   phrase so it lands on the spoken word. A number on a `statement` card is a
   floor violation.
3. **At least one `schematic` or `figure` tour per act** (≈ every 4–5 min).
   These are the teaching core — the beats viewers screenshot.
4. **At least one hero beat** (3D / Hero3D hook, or an equivalent §2G accent)
   in the cold open, AND the biggest motion of the video at the midroll seam.
5. **Annotations on ≥ 1/3 of slides** (vector arrows/circles/underlines or
   doodle stamps), each with a `cue` on the exact spoken phrase. The
   hand-drawn layer is the channel's personality; a bare deck reads corporate.
6. **Narration cues resolve on every deck: a deck with `cues: 0` authored
   fields is a failed deck.** Auto item-sync covers list-ish types, but
   counters, schematics, figures, and annotations need authored phrases.
7. **Footage/`figure` slides wherever the blueprint's visual budget names
   b-roll or artifacts.** If the budget listed five broll scenes and the deck
   has zero `footage` slides, the deck ignored the blueprint.

**The census is one command** — run it and paste the tally into PLAYBOOK §
(deck gate notes):
```
python3 tools/deck_census.py <project_dir>
```
It prints slide-type counts, text-type %, max text run, annotation coverage,
cue count, and PASS/FAIL per rule above. Fix fails before rendering.

## 5. The spec contract (data in, motion out)

- **The authored artifact is `deck.json`** (one slide per script segment — the
  deck-playbook's 1:1 contract). The engine (`remotion_engine.py`) maps each slide
  type to a component and resolves all narration cues at spec-build time. (The
  separate `motion.json` this section originally sketched was never needed.)
- `fields` = that component's data (headline, value, image, items, points…).
- **The sync contract (IMPLEMENTED 2026-07-04).** All cue resolution happens in
  Python against `work/alignment.json`; components receive frame numbers and stay
  pure functions of frame. Four authoring surfaces on any slide:
  1. `"cues": {"<name>": "<spoken phrase>"}` → `fields.cueFrames.<name>`. Known
     names: `land` (StatCounter lands its count on the phrase).
  2. **Auto item-sync** (no authoring needed): `list`/`steps`/`funnel`/`waterfall`/
     `timeline` items each appear AS their label is spoken (first-content-word match,
     walking forward). Even-stagger fallback per item.
  3. `annotations[].cue`, `schematic` `stages[].cue`, `figure` `moves[].cue` /
     `assemble.pieces[].cue` / `highlight.cue` — per-element phrases.
  4. Misses NEVER break a render: proportional fallback + a `sync WARNING` line in
     `work/run.log` (grep it after every render; fix the phrase or accept the fallback).
  Cue phrases must be copied VERBATIM from the segment's script text (they're matched
  against what was actually said — the aligner's words).
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
  Headline · `define`→DefineTerm · `stat`/`statgrid`→StatCounter/StatGrid ·
  `delta`/`compare`→SideBySide · `trend`/`ranked`/`diagram`→DrawLine ·
  `waterfall`→Waterfall · `timeline`→Timeline · `list`→BuildList · `steps`→StepFlow ·
  **`schematic`→Schematic** · `quote`→Quote · `punch`→PunchWord · `reframe`→Reframe ·
  `figure`→Figure (tours/assemble/highlight) · `footage`→Footage · `hook`→Hero3D ·
  `payoff`/`cta`→CTA. The **deck-playbook governs slide-type semantics**; this file
  governs their motion.

## 7. Self-QA checklist (run before rendering a motion spec)

- [ ] **The visual-variety floor passes: `python3 tools/deck_census.py <dir>`**
      (§4b — text-type cap, no 3-in-a-row, numbers as synced data-viz,
      schematic/figure per act, annotation coverage, cues authored).
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
