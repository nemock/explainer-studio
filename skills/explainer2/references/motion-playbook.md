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
- **KineticCaptions** — word-synced, **paged** caption block (TikTok-style), active word in
  green, driven by the alignment JSON. **Baseline on every scene** (long-form and shorts).
  A static block of up to 6 words shows at once; the highlight walks across it *in place*,
  then the whole block swaps to the next page (one discrete swap every ~2-3s). Two grouping
  rules in `buildPages`: (1) never exceed `MAX_WORDS` (6); (2) never span a sentence — break
  after any word ending in `.`/`!`/`?`, so a page never mixes two sentences. *Changed 2026-07-21
  from a continuously-sliding window* (`start = active − 2`), which recomputed every frame and
  kept every word marching; a viewer called it jittery/"epilepsy-inducing." The swap is a hard
  cut (no fade — a fade re-introduces the motion we removed); during pauses the current page
  holds. *Don't* revert to the sliding window. See `remotion/src/components/Captions.tsx`.
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
  **Paper-world styling (2026-07-18, Dave):** on the paper themes the Schematic
  auto-renders nodes as **colored post-it notes** (four colors cycled by node index,
  navy ink, a turned-up dog-ear corner, a hand-placed tilt + real drop shadow) and edges
  as **hand-drawn navy Sharpie lines** — the old cream cards + near-white dashed edges had
  no contrast on the cream page. No authoring change needed; it keys off the theme
  (`ink.paper`) so the midnight brand is untouched. Engine: `Schematic.tsx`.
  **Notes auto-size to their text (2026-07-28, Dave, #52).** Node height used to be a
  fixed formula that ignored text length, so any label/sub that wrapped past two lines
  **overflowed the note** (caught on #52's "It matches them against a playbook" + its
  sub). Height is now computed from the estimated wrapped-line count at the node's own
  width, so long labels simply get a taller note. Two new optional fields:
  - **`h`** — explicit height override, frame-height fraction. Wins over everything.
  - **`shape: "square"`** — a chunky, real-post-it square note (height forced to at
    least the node's width). Real post-its are square; there is usually plenty of empty
    canvas, so **when a node carries a lot of text, prefer a BIGGER note over shrinking
    the text**. Dave's directive: "we've got plenty of blank space… we're not in any
    danger of having larger objects for putting text into."
  Authoring guidance: widen `w` generously (0.22–0.30 is fine) and spread nodes across
  the canvas rather than crowding them into one band. If a schematic looks empty in the
  middle, that is a sign the notes are too small, not that you need more nodes.
  **When the nodes are PEERS, pin the color and the size (2026-08-12, plg-guide module 1).**
  The post-it color cycles by node INDEX, which quietly says "these are four different
  kinds of thing." That is right for an org map and wrong for a set — the four decisions
  in the plg-guide spine came out yellow/blue/pink/green and read as four unrelated
  boxes. New optional field:
  - **`pastel`** — `"yellow"|"blue"|"pink"|"green"`, pins the note color. Wins over both
    the `kind` mapping and the index cycle. Author a set as one color with the ACTIVE
    node in a second color; that is what a person highlighting one card in a stack
    actually looks like, and it survives the camera moving between stages.

  Size is the same trap. `shape: "square"` on a SUBSET makes those nodes visibly bigger
  than the rest, so peers stop looking like peers — apply it to all of them or none. And
  a bare `w` around 0.19 asks the substrate library for a wide torn *strip*: four of those
  are thin slivers floating in an empty frame. For a row of peers, `w: 0.205` +
  `shape: "square"` on every node fills the middle band properly.
  **`sketch: true` DEFEATS the post-it treatment on paper themes (caught 2026-07-29, #53).**
  `Schematic.tsx` computes `const note = ink.paper && !fields.sketch`, so setting `sketch`
  forces `background: 'rgba(9,13,28,.72)'` — a dark translucent card with white text, which
  on a cream page is off-brand and reads like the midnight theme leaked in. It renders, the
  census passes, nothing warns. **On the paper themes, do not set `sketch`.** It remains
  valid on `midnight`. (#52's schematics were right precisely because they never set it.)
  **Keep the bottom row clear of the caption band.** Captions occupy roughly y 0.78–0.87 in
  16:9, so a node centred below ~y 0.70 gets its `sub` line covered by the caption chip.
  Put lower nodes at **y ≤ 0.65** and check a late-in-segment still, not just an early one —
  an early frame hides the problem because the bottom node has not revealed yet.
- **StepFlow** — the linear pipeline (idea→MVP→launch→scale); now lands each node on
  its narration cue automatically (auto item-sync, §5).
- **Funnel** — stages narrowing; great for sales/customer math (auto item-synced).
- **Timeline** — events appear along a line in time (auto item-synced).
*Rule:* build in sync with the explanation; never reveal the whole diagram at once.

### G2. The chibi presenter (IMPLEMENTED 2026-08-07 — on EVERY scene, automatic)

> **SCOPE, 2026-08-10 — DEEP DIVES ONLY.** The presenter now runs on the
> `nemock-deep-dive` theme and nothing else. The six personal-show worlds (`fwf`,
> `mmt-tangerine`, `ftt-study`, `wsc-goldenrod`, `ttd-indigo`, `fmf-alarm`) are in
> `CHIBI_NEVER` — a hard block a project file cannot switch on — until the operator
> settles how a stand-in should work in a vertical frame. Everything below describes
> the deep-dive behavior. See
> `make_money/routine_changes/2026-08-10-booth-show-chibi-and-props-doc-correction.md`.

Dave's cartoon stand-in stands beside the content on **every slide** of a landscape
deep-dive render. This is automatic — the engine assigns a pose to every scene, so a
deck needs no authoring at all to get it. Operator directive: *"if the chibis are only on
one or two slides, then they don't actually make sense at all."*

- **You may author `"chibi": "<pose-filename>"` on any slide** to pick that scene's pose
  (no `chibi/` prefix needed, `.png` optional). Everything you don't author takes the
  engine's neutral rotation. Optional `"chibiFlip": true` mirrors him.
- **Author a pose where the beat has a specific attitude** — thumbs-up on a concession,
  counting-three on a three-part definition, weighing-options at a which-half turn. Leave
  the rest alone: the rotation is deliberately neutral because a pose that contradicts the
  line is worse than a calm one.
- **Poses that point must point at the content.** He stands at the frame's RIGHT, so an
  asymmetric pose has to gesture toward the viewer's LEFT. Don't trust the filenames — the
  character model mirrors handedness freely (its own README says so). Look at a contact
  sheet before picking one.
- **He is the top layer**, above the scene, the annotations and the captions: the viewer
  reads him as Dave presenting, not as scene furniture.
- **He can never cover anything**, because the content layer is scaled out of his lane and
  the captions reserve it too. That is a layout guarantee, so you do not need to design
  around him — but note every slide's content is ~19% narrower than the full frame, which
  is why schematics should still spread across the canvas rather than crowd the right.
- **Per project:** `"presenter": {"enabled": false}` in `project.json` opts out;
  `"charHeightFrac"` (0.18–0.22, default 0.22) tunes his size.
- **Never on Circumvent** (separate brand, hard rule), **never on the six personal-show
  worlds** (paused 2026-08-10, see the scope note above), and **skipped on portrait** — a
  9:16 lane would eat a third of the frame, so Shorts are unaffected.
- **Never as set dressing.** A `chibi/...` ref in `props` (or in a slide `image`) is
  dropped by `_stage_chibi` with a `run.log` warning. Before 2026-08-10 that path staged
  the pose and rendered him as a PROP — which is how the stand-in kept appearing on the
  portrait shows even though this layer skips portrait. The presenter layer is the only
  route to a pose.

Engine: `ChibiPresenter.tsx` + `_assign_chibi` in `remotion_engine.py`. Full rationale in
`make_money/routine_changes/2026-08-07-chibi-presenter-on-every-slide.md`.

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

**Figure `title` ALWAYS renders (fixed 2026-07-28).** A figure's `title` used to render
*only* when `imageFromFrac` was also set; authored without it, the headline was silently
discarded — no warning, census still passed, render still succeeded, the line just never
appeared. It cost real editorial copy on several videos (7 of 9 image slides on #52,
including that video's central claim) before a still-check caught it. Now:
- **`title` + `imageFromFrac`** → *phased*: the title holds the frame alone, then the image
  reveals under it. Use when the title is a **claim** and the image is its **evidence**.
- **`title` alone** → a persistent header between the kicker and the image, for the whole
  scene. Reading order: **kicker → title → image → caption**.
Both are legitimate; pick by whether the line is a claim to state first or a label to sit above.

**Overlay-occlusion rule (operator-caught 2026-07-28, #52).** Anything drawn OVER an image —
the hook's headline banner, `marks`, a `moves` zoom — must be checked against **what is actually
underneath it**, by opening the image, not by guessing coordinates. Two failures in one video:
a hook whose only meaningful element (a question mark) sat exactly where the banner is pinned,
and a zoom+circle aimed at decorative line-art with no text to mark. Specifically: **`hook`
slides render the image full-bleed with the label block pinned at ~7% from the top, so the
image's meaningful content must live BELOW roughly the top 28%** — pick art whose top band is
texture, not meaning.

**Image-space figure `marks` (IMPLEMENTED 2026-07-17) — callouts that RIDE the Ken Burns.**
`annotations` are a FRAME-space overlay: they sit over the whole scene and do NOT move
with a `figure`/`footage` Ken Burns, so a frame-space circle on a panning/zooming subject
DRIFTS OFF it (looks sloppy). To point at something INSIDE the paper art — the robot's
head, the rookie's face, a chart — author a **`marks`** array on the `figure`/`footage`
slide instead. Each mark renders inside the image's own moving container, so it stays
locked on its subject as the shot moves. Same hand-drawn kinds and cue contract as
annotations, but coords are **0-1 of the IMAGE** (not the frame):
`marks: [{kind: circle|arrow|underline|box|strike, at:[x,y] (circle/box/underline) or
from/to (arrow/strike), w?, h?, color?: green|red|white, cue: "<verbatim phrase>"}]`.
Measure `at` off the actual generated image (open it and read the subject's fraction).
Rule of thumb: **anything you'd circle/point-at ON the art → `marks`; editorial marks on
stable text (a headline, a caption) → frame-space `annotations`.** `marks` count toward the
§4b annotation-coverage floor. Engine: `FigureMarks` in `remotion/src/components/Media.tsx`,
cue-resolved in `remotion_engine.py` (like `moves`).

**`underline`/`strike` need a LINEAR SUBJECT that exists in the art (operator-caught
2026-07-29, #53 — the fourth repeat of this class of error).** Underline is a *text* device.
Our generated paper art contains **no text by construction**: the STYLE.md recipe ends with
"no text, no words, no logos". So an underline on a generated figure usually has nothing to
underline and renders as a red or green bar floating on blank paper. Two consequences:
- **Default to `circle`, `box` and `arrow` on generated art.** Those point at *objects*, and
  objects are what the art contains. Reach for `underline` only when the image genuinely has
  a linear element to trace (a drawn highlighter stroke, a ruled line you mean to single out,
  a wire). #53's one valid underline rides an actual green marker stroke.
- **A mark can never reach the caption or the title.** Those are engine-drawn in FRAME space,
  outside the image container; image-space `marks` live inside it and cannot touch them. If
  the point you want to make is about the caption text, make it with `accent` colouring on the
  title instead.
- **Don't add a second mark just to look thorough.** One focal mark that lands beats two where
  the second has no subject. The annotation-coverage floor counts *slides*, not marks, so
  dropping a bogus second mark costs nothing.

**A DOCUMENT FIGURE MUST CARRY ITS WORDS — use `pageText` (2026-08-14, operator-caught).**
The "no text, no words, no logos" clause is a constraint on the GENERATOR, not on the slide:
Magnific bakes garbled, misspelled, uneditable type, so the art stays blank and **Remotion
renders the words**. That second half existed for notes, cards and schematics and was
missing for figures, so a document slide had nowhere to put its sentence — the title
rendered above the mount and the page itself stayed empty. Dave's verdict on the result:
*"You've drawn this nice paper card that clearly should have something rendered on it."*

```jsonc
"pageText": {"text": "the equivalent work of 700 full-time agents",
             "at": [0.51, 0.385], "w": 0.42, "size": 0.036, "accent": ["equivalent"]}
```

Image-space like `marks`, inside the same moving container, so it rides the Ken Burns. Let
it wrap — a quoted line reads better balanced over two lines than crammed onto one.

- **Never bake decoration in place of the words.** #57 asked the generator for a green
  highlighter stroke *so there would be something to underline*, then authored an
  `underline` on top of it: two green lines, neither underlining anything, over a blank
  page. Leave the page blank, set the type on it, and let a baked stroke sit UNDER the
  type as its underline — which is the only thing a stroke is for.
- **If the beat is "the document says X", X goes on the page.** A `title` above the mount
  saying the same words is a duplicate; drop one.
- **Then the mark has a subject.** #57's red box captioned "That figure is an average" was
  drawn around empty paper until the line it referred to was actually set on the page.

**The standing check before any figure ships:** for each mark, name out loud the thing in the
image it sits on. If the answer is "the empty area below X" or "roughly where the text is",
it is wrong. Open the PNG and look. **And if the slide's point is something the document
says, check the document says it** — on the page, not in a caption above it.

**`hook` slides DROP `marks` — do not author them there (found 2026-08-12, #57).**
`_scene_for` maps `hook` to `PaperHook` with exactly `{image, kicker, headline, accent,
stage}`. A `marks` array on a hook slide is discarded at spec-build: no error, no warning,
and `deck_census.py` still counts the slide toward the annotation floor because it only
looks for the *authored* key. So a deck can pass the floor while showing one fewer callout
than it claims. #55's cold-open circle on `hook_it_works.png` never rendered, and nobody
noticed for ten days. Two consequences:

- **Put the cold open's callout on slide 2 instead.** The hook is a full-bleed art card with
  a pinned label block; it does not need a ring on top of it anyway.
- **Never satisfy the annotation floor with a hook slide.** Count only `figure`/`footage`
  `marks` and `schematic` `annotations` — those are the two paths that actually render.

Same failure class as the `figure`-`title`-without-`imageFromFrac` bug above and the
`source`/`source_url` passthrough gap: an authored field silently dropped by the type map,
where the absence of a warning reads as success.

**SUPERSEDED 2026-08-08 (#56): the PIL-on-raw-art contact sheet is DEAD as a verification
method. Author marks from MEASUREMENT; verify on RENDERED FRAMES.** The #55 contact sheet
below could never catch a bad coordinate, because it drew the authored numbers onto the raw
art — it verified the numbers with the same numbers, plus the same eyeball that authored
them. On #56 three circles "passed" that sheet and still missed their subjects on Dave's
screen. A calibration render (crosshair image + mark authored at the crosshair) proved the
RENDERER is honest through the Ken Burns; every miss was an eyeballed coordinate. The two
rules now:

1. **Author `at` from measured pixels, never by eye.** Segment the subject in the art
   (the green cluster, the navy cluster inside a region) with ~10 lines of numpy and set
   the mark from the measured centroid/bbox. On #56 the ONE measured mark landed dead-on
   in every frame; eyeballed ones missed by up to 0.14.
2. **Verify with `python3 tools/mark_stills.py <project_dir>`** (after narrate+align).
   It renders every mark-carrying scene through the real engine at the frame where its
   last mark has finished drawing and tiles the REAL frames into `work/mark_stills.png`.
   Read every tile and name the thing each mark sits on. This is the gate; a raw-art
   sheet is not.

**Narrative order is part of mark correctness (same ruling).** A circle must never draw
before the thing it circles exists — on #56 a schematic annotation fired on the segment's
first phrase, drawing a ring on empty canvas before any note had revealed ("why would you
draw a circle before the thing even exists?"). The engine now warns when a schematic's
annotation resolves before its first stage reveal; the warning is a defect, not noise. And
an annotation that fires WITH its target's reveal is usually redundant — the pop is the
emphasis; circle things the narration returns to, not things that just appeared.

*(Historical note — the #55 method this replaces: draw every authored mark onto its own
art with PIL, tile, and look. Kept here only so nobody reinvents it as an "improvement";
it catches transposed/garbled coordinates but not miseyeballed ones, which is the class
that actually ships.)*

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
