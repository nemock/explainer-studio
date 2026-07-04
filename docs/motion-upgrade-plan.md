# Motion Upgrade Plan — narration-led drawing, diagrams that assemble

*2026-07-04 · Status: **SHIPPED same day** (operator approved: "let's get it done") ·
Operator directive: "things like hand-drawn arrows leading a viewer visually through a
diagram, drawn as the voice narration is happening, a picture assembling… we have basic
visual assembly (text blocks, enumerated lists) and that's fine, but we can do so much
better."*

**Build result:** Batches 1–4 all shipped + verified via `remotion/motion-lab.json`
still frames; Batch 5's transitions item deferred (see below). Plus an unplanned
addition: the operator's **CopyDoodles** library (106 Sharpie-scanned stamps) imported
via `tools/import_doodles.py` → `library/doodles/` (gitignored, EULA: use-don't-
redistribute) and wired into the annotation layer as `kind: "doodle"`. Authoring
docs: deck-playbook §2 (`schematic`) + §4c (cues/annotations/tours) and
motion-playbook §2C/§2H/§5/§6. The remaining known gap: `remotion still` verification
of a real project spec before each render is manual — keep using the §7 checklist.

Follows the `docs/booth-upgrade-plan.md` pattern: numbered batches, each independently
shippable, operator approves direction before build.

---

## 0. Gap analysis (what exists vs. what the playbook promises)

The motion-playbook §2 vocabulary already NAMES much of what the operator wants —
StepFlow ("nodes assemble and arrows draw"), DocZoomAnnotate ("pan/zoom to a line +
highlight-wipe / underline / circle"), DecisionTree, Cycle, MaskReveal — but the
implemented library is thinner than the vocabulary:

**Implemented today (24 components):** text scenes (KineticHook/Headline, DefineTerm,
Quote, PunchWord, Reframe), BuildList (word-time-synced items — the one true
narration-synced element besides captions), StepFlow (even-stagger boxes + unicode
arrows), data-viz (StatCounter/Grid, DrawLine, Waterfall, Pictograph, Ring, Funnel),
Figure (Ken Burns + ONE marker-wipe + phased reveal), Footage, Hero3D, CTA, stings.

**Not implemented (vocabulary-only):** DocZoomAnnotate's pan/zoom+multi-annotation,
DecisionTree/Branch, Cycle, MaskReveal, BeforeAfterSlider, Cutaway/PiP, LowerThird,
CodeType, Gauge/Drain, BarRace. And **nothing hand-drawn exists anywhere.**

**The structural gap (the real finding):** motion-playbook §5 promises a per-scene
`sync` field ("cue word/time the component lands its key moment on… defaults to the
alignment JSON"). That generic mechanism was never built. Only BuildList got a bespoke
version (`itemTimes`, resolved in `remotion_engine.py`); StatCounter uses a hardcoded
proportional window. Everything else animates on scene-relative springs — which is why
long segments feel static after the entrance (QA on #40: "longest shot 34.2s — consider
splitting"). The narration-sync plumbing is the single highest-leverage build in this
plan; every batch after it rides on it.

**Assets in hand:** `work/alignment.json` word timestamps (already driving captions +
BuildList) · DrawLine proves SVG stroke draw-on in-house · deterministic-by-construction
Remotion · the spec-driven architecture (Claude authors data, never React).

## Batch 1 — the generic cue resolver (the multiplier)

Python side (`remotion_engine.py`): any slide may carry `cues` — a map of cue-name →
spoken phrase: `"cues": {"arrow1": "hiding inside it", "reveal2": "manufacturing"}`.
At spec-build time, resolve each phrase against that segment's alignment words →
absolute scene-relative frame numbers, delivered to the component as
`fields.cueFrames = {arrow1: 112, …}`.

- Generalize + harden BuildList's `_key/_norm` fuzzy matcher: match on a normalized
  leading content word, search only within the segment's time window, **fall back to
  proportional spacing on a miss and WARN in run.log** (a missed cue must never break a
  render — same degrade-gracefully posture as missing footage).
- Components start springs at `cueFrames[x]` instead of `i * per`.
- Retrofit immediately: StepFlow arrows/nodes, Waterfall bars, Funnel stages, Timeline
  events, StatCounter's landing window, Figure's highlight `atFrac`.
- Est: ~1 day. No new deps. This alone converts "items stagger evenly" into "the thing
  appears as he says it" across six existing components.

## Batch 2 — the Annotate overlay (hand-drawn arrows, circles, underlines)

A new overlay layer any scene can carry (most valuable on Figure, Schematic, and text
scenes): `"annotations": [{kind: "arrow"|"circle"|"underline"|"strike"|"marker",
from: [x,y], to: [x,y], label?, cue, sketch?: true}]` — coordinates in 0-1 scene space.

- **Draw-on:** SVG path + stroke-dashoffset (the proven DrawLine technique), 0.4–0.8s
  from the cue frame, house easing. An arrowhead that fades in as the stroke arrives.
- **Hand-drawn aesthetic:** `roughjs` (the only new dependency) generates the sketchy
  path geometry. **Seeded per annotation** (hash of slide id + index) — rough.js accepts
  a `seed` option, so the wobble is identical every render: the determinism hard rule
  holds. Marker-style label text in a handwriting-adjacent weight, kept on-palette
  (green/red/white only).
- Circles/ellipses for "this one", underlines for phrases on text scenes (ties the
  accent-color system to narration timing), strike for "not this".
- Est: 1–2 days including deck-playbook/motion-playbook schema docs.

## Batch 3 — Schematic (the guided diagram — the centerpiece)

A real node-and-edge diagram that assembles under narration, replacing StepFlow for
anything non-linear. Authored as pure data:

```json
{"type": "schematic", "kicker": "WHO ACTUALLY BUYS",
 "nodes": [{"id": "surgeon", "label": "Clinical champion", "x": 0.15, "y": 0.3},
           {"id": "vac", "label": "Value analysis committee", "x": 0.45, "y": 0.5}],
 "edges": [{"from": "surgeon", "to": "vac", "label": "sponsors", "cue": "committee"}],
 "stages": [{"reveal": ["surgeon"], "cue": "the surgeon"},
            {"reveal": ["vac", "surgeon-vac"], "cue": "value analysis"}],
 "camera": [{"center": [0.45, 0.5], "zoom": 1.35, "cue": "value analysis"}]}
```

- Nodes spring in per stage cue; edges draw on (Batch 2's stroke technique, sketch
  optional); the **camera** (a container translate/scale) drifts toward the active
  region — the "leading the viewer's eye through the diagram" ask, literally.
- Layout is authored (0-1 space), not computed — keeps Claude authoring data and the
  render deterministic; 5–9 nodes max per scene (legibility guardrail).
- Est: 2–3 days. First real use: BRG piece 6's hospital buying map (see series review).

## Batch 4 — Figure 2.0 (guided document/image tours + assembly)

- **Multiple cued annotations** on the image (Batch 2 overlay in image space) — the
  playbook's DocZoomAnnotate, finally real.
- **Cued camera moves:** `"moves": [{"to": {"x": 0.3, "y": 0.62, "scale": 2.2}, "cue":
  "the fine print"}]` — pan/zoom between regions as they're discussed (replaces the
  single global Ken Burns when present).
- **Assemble mode:** the "picture assembling" ask — the image revealed as 3–6 cued
  regions (deterministic clip-path wipes), or layered PNGs flying together for product
  shots (precedent: the layered Studio Background; the #13 phased reveal).
- Est: 1–2 days. BRG series is document-heavy (FDA letters, board decks, data-room
  lists) — this batch earns its keep immediately.

## Batch 5 — polish + process

- ~~Seeded rough-icon primitives~~ **COVERED BY COPYDOODLES** (2026-07-04): the
  imported library's arrows/ovals/bursts/checks/numbers supply the hand-drawn stamp
  vocabulary with real Sharpie character; rough.js covers the geometric kinds. Revisit
  only if a needed icon (person/building/gear) has no doodle equivalent.
- **Motivated transitions at beat boundaries — DEFERRED, deliberately.**
  `@remotion/transitions`' `TransitionSeries` requires restructuring the absolute
  scene timeline (scenes are `<Sequence from>` positioned off alignment times); the
  existing SceneWrap cross-fade + light-leak already connects beats. Don't destabilize
  the working timeline model for this; revisit as its own batch if wanted.
- **`motion-lab` fixture — SHIPPED** as `remotion/motion-lab.json` (a props file for
  the existing parametric Video composition, not a separate comp):
  `npx remotion still src/index.ts Video out.png --props=motion-lab.json --frame=N
  --public-dir=<dir with staged doodle__*.png>`. Check frames 80/170/250/350.
- **Playbook updates — SHIPPED**: motion-playbook §2C (Schematic), §2H (annotation
  layer + doodles + license boundary), §5 (the implemented sync contract, deck.json
  as the authored artifact), §6 (component map); deck-playbook §2 (`schematic`),
  §4c (cues/annotations/tours authoring), §6 (new self-QA lines: verbatim cues,
  run.log sync-warning grep, ≤2 annotations/slide, mid-scene beat on >20s segments).

## Guardrails (unchanged, restated for the new surface area)

Determinism: frame-driven only; rough.js always seeded; cues resolved in Python at
spec-build so React stays a pure function of frame. Brand: palette/type/springs locked;
sketch style is an accent, not a theme change. Legibility: one focal motion at a time;
annotation labels ≥ caption size. Memory: all SVG/DOM — negligible vs. the existing 3D
scenes on the M3/16GB budget. Architecture: Claude authors deck.json data; components
stay generic; **no per-video React, ever.**

## Sequencing & first target

Batch 1 → 2 → 3 → 4 → 5; each independently shippable. Batches 1+2 alone deliver the
operator's headline ask (narration-timed hand-drawn annotation) on every existing
component. Pilot the full system on **BRG piece 6** ("the hospital buying map" — a
made-for-schematic teaching diagram), per the series review's production order.
