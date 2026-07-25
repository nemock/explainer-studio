# Papercraft Motion — migration note (deliverable 3, 2026-07-25)

What changes, what stays, and what a video costs to author after the cutover.
Companion to `papercraft-motion-spec.md` (the design canon). Status: spec ✅,
world infrastructure + 3 prototype scene components ✅, set-piece + element
library ✅, prototypes rendered on #21's real narration for the operator gate.

## 1. Styles are sequestered — "classic" vs "papercraft"

The system now treats visual languages as **styles**: a named set of Remotion
components + world tokens, selected per channel. Nothing is deleted; nothing
is global.

| style | components | world | used by |
|---|---|---|---|
| **classic** | the existing flat kit (KineticHeadline, DefineTerm, StatCounter, DrawLine, StepFlow, Schematic, SideBySide, …) | navy (or flat cream on paper themes) | `midnight` (ISO series + legacy), and any deck slide the papercraft map doesn't cover yet |
| **papercraft** | the `Paper*` family driven by `PaperWorld.tsx` (planes/camera/physics/light) + `brands/papercraft.ts` tokens | dark ink table, cream objects (the approved still style) | `nemock-deep-dive` (FWF tokens); future BRG series (BRG tokens); NOT Cut & Bond (own style), NOT midnight |
| cut-bond | the Chem kit | its own cream world | `cut-bond` only |

Calling a style up later = the theme string. The classic kit stays exactly as
it is for the ISO series, so the sequestration costs nothing.

## 2. What changed (already committed)

- `remotion/src/brands/papercraft.ts` — FWF + BRG world token sets.
- `remotion/src/components/PaperWorld.tsx` — the shared physics/depth/light
  engine: 4 planes + one stepped camera, place/popup/flick (+ pure
  `placeStyle` for loops), PaperTable ground, key light with spotlight snap.
- `remotion/src/components/PaperSet.tsx` — first 3 papercraft scenes:
  `PaperSetHook`, `PaperPopCard`, `PaperCounter` (registered in Video.tsx).
- `remotion_engine.py` — stages `set` + `props[].image` deck fields;
  stages `remotion/public/papercraft/` wholesale into every render.
- `remotion/public/papercraft/` — the reusable brand asset library
  (tracked in git, provenance.json):
  - **backdrops**: `desk_wide_a/b.jpg` (wide founder's desk, empty center mat)
  - **props**: `prop_bottleneck.png`, `prop_docstack.png` (transparent)
  - **elements/** — 10 storytelling cutouts: arrow, growth-arrow, pawn, tag,
    warning, magnifier, hourglass, gears, shield, lightbulb.

## 3. The papercraft scene map (migration wave SHIPPED 2026-07-25)

`_papercraft_scene` in `remotion_engine.py` routes deck **types** to `Paper*`
components when `theme == nemock-deep-dive`; anything it returns None for
falls back to the classic component, so decks never break mid-migration.

| deck type | papercraft component |
|---|---|
| hook (`set`/`beats` present) | PaperSetHook (multi-plane set) |
| hook (illustration only) | PaperHook (full-bleed, kept) |
| statement / highlight / quote | PaperStatement |
| define | PaperDefine (term tag + unfolding definition) |
| punch | PaperPunch (embossed stamp; kind:bad adds the warning element) |
| compare / delta | PaperCompare |
| steps / flow | PaperSteps (per-item narration sync + lateral camera) |
| list | PaperList (per-item narration sync) |
| trend / ranked (with points) | PaperStairs (+ the pawn climber) |
| ring / progress | PaperCounter |
| keepcard | PaperPopCard |
| cta / payoff | PaperCTA (real book cover on the table) |
| any slide + `"transition": "tear"` | TearReveal act-boundary (spec §4) |

**Still classic on papercraft (later waves, by demand):** schematic (keeps the
post-it/Sharpie paper treatment it already has), figure/footage (Ken Burns +
marks are strong as-is), waterfall, pictograph, statgrid, stat, timeline,
reframe, funnel, waveform.

## 4. Authoring cost per video (after migration)

- Deck flow unchanged (same types, same cues). New optional fields: `set`
  (backdrop), `props` (library elements or per-video cutouts), `camera`,
  `mood`.
- Per-video Magnific: ONE wide backdrop (the video's visual theme — replaces
  the PaperHook illustration gen that already happens today) + 0–2 topic
  props → cutout. ~5 min wait, batched at deck time, ~80–250 credits.
- The element library covers recurring metaphors at zero per-video cost;
  extend it with the provenance.json recipe (style-ref an existing member).
- Dave's record-review loop: untouched. No new manual steps.

## 5. Open flags for the operator

- **Accent color**: papercraft world retires green for lilac/violet (the FWF
  palette has no green). Applied to captions (`captionAccent` per project) and
  the Paper* components. Veto = one token change in `brands/papercraft.ts`.
- The classic kit's paper-theme text components (dark-ink-on-cream) remain the
  fallback during migration, so a nemock deep dive mid-migration mixes worlds
  scene-by-scene: acceptable during rollout, but plan one video fully
  papercraft ASAP to avoid a half-and-half look.
- QA dead-air heuristic still fires on stop-motion holds (accepted by design,
  spec §2). Read the warning against the papercraft rule before "fixing" it.
