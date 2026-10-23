# 3D Papercraft Matrix — LOCKED (2026-10-23)

The visual world for **The Product Manager's Guide to Cybersecurity in Medical Devices**
(`/Volumes/Casima/claudeCode/MedDevice_Cyber_Guide/`), theme `papercraft-matrix`. Follow it
verbatim.

**What it is.** The house 3D papercraft world (layered cut paper, real paper thickness, soft
shadows between layers) with a Matrix feel, built entirely in paper: a near-black green
ground, forest-green cardstock, one phosphor-green accent that glows softly, and hanging
strips of perforated paper tape falling like code rain. Operator brief, 2026-10-23: "kind of
like the movie Matrix ... that hacker motif," and then, after a non-paper attempt was
rejected, "I intended it to be implemented with the 3D papercraft." It is its own world and
theme key so the existing papercraft worlds are never touched.

**What it is NOT.** Not a dark non-paper theme, no CSS code rain, no Hero3D wireframe
sphere, no glyphs or letters baked into art (all type is Remotion's job).

## 1. The palette (strict)

| Role | Hex | Use |
|---|---|---|
| Near-black green ground | `#06120c` | the page and table every scene sits on |
| Deep ground (vignette edge) | `#020604` | falloff only |
| Forest-green cardstock | `#0f3a24` | laid sheets, background layers, tape strips |
| Muted sage paper | `#c9d4c2` | object bodies (the pump) and the text cards |
| Deep green ink | `#0b2418` | type printed on sage cards |
| Phosphor green accent | `#3ddc84` | ONE accent, sparingly, with a soft glow: a cable, a lit tape end, a key word |

`#3ddc84` is the studio green, chosen so the accent matches every green the engine already
draws. No red in art; the engine's danger red is for type marks only.

## 2. The prompt RECIPE (copy verbatim, fill `{SUBJECT}`)

> Layered cut-paper collage illustration, handmade 3D papercraft style with visibly torn and
> cleanly-cut paper edges, real paper thickness, and soft drop shadows between stacked paper
> layers. Subject: {SUBJECT}. Behind it, long hanging strips of perforated paper tape fall
> from the top of the frame like digital rain, each strip punched with rows of small holes,
> some strips glowing faintly green at their lower ends. Mood of a dark server room at night,
> quiet and precise. Editorial explainer / storybook aesthetic, flat and clean. Color palette
> strictly: near-black green paper background (#06120c), deep forest-green cardstock layers
> (#0f3a24), muted sage paper for objects, and a single bright phosphor-green paper accent
> (#3ddc84) used sparingly with a soft glow. Generous negative space, calm composition, no
> text, no words, no letters, no numbers, no logos, no screens showing characters.

- Model `gpt-2`, style-anchored: `references: [{type: "style", identifier: "jUTMvgWLD0"}]`.
- Cost, quoted exactly with `simulate_cost` on 2026-10-23: **100 cr per image at
  1k/medium** (proofs). Quote again before every batch, and before any 2k/high final.
- **Say what is blank.** Any screen, card, label or display is described as blank / dark /
  unmarked, or the model fills it. The take-1 pump's screen came out blank because the prompt
  forbade characters on screens.
- **Leave room for type.** Put the subject left or right of centre with open ground on the
  other side, as take 1 does. Headlines and captions need that space.
- The tape-rain clause may be dropped for close-up objects or cut-outs; keep it for scenes.

## 3. Style anchor — LOCKED

Take 1 of the 2026-10-23 four-take concept proof (1k/medium, no style reference: this is
the first image of the world). Subject: a paper infusion pump on an IV pole, a glowing
phosphor-green paper network cable running to a paper wall socket, perforated tape rain
behind, open ground on the right.

| | |
|---|---|
| Creation identifier | `jUTMvgWLD0` |
| Local file | `anchor_take1_jUTMvgWLD0.png` beside this file (original in `MedDevice_Cyber_Guide/style-proof/`) |
| Other takes | 2 (torn-paper hills foreground), 3 (glowing-dot tape, IV bag; the most "code-like", kept as a reference for that detail), 4 (drip chamber, floor line) in the same folder |

Why this one (operator, 2026-10-23): the cleanest composition, the clearest rain, and the
most open space for on-screen type.

## 4. Engine world (`papercraft-matrix`)

Tokens live in `remotion/src/brands/papercraft.ts` (`PAPER_MATRIX`), ink in
`remotion/src/ink.tsx`, the theme in `src/explainer2/themes.py`. The world's own element
directory is `remotion/public/papercraft-matrix/elements/` (`tape_rain.webp`, the page's
code-rain overlay; `el_warning.png`, the green warning triangle; `provenance.json`). The
shared substrates (cards, notes, fixings, grounds) are palette-neutral and are tinted to this
world's tokens, so they are not regenerated. Per-episode Magnific spend is scene art only.

**The only dark-PAGE paper world.** It sets the optional `page` token, which three
components read and every other world skips: `PaperBackground` (dark page + fibre + tape
rain), `Captions` (dark pill, light text), `PaperHook` (headline on sage card stock in card
ink). Video.tsx paints the matching base.

**Two greens, by surface.** Type on the dark page (kickers, captions, `ink.accent`) uses the
phosphor `#3ddc84`. Type printed ON sage cards uses the world `accent`, deep green
`#14743f`, because phosphor on sage is under 2:1.

Style proof of real episode 1 scenes (hook, statement card, counter):
`MedDevice_Cyber_Guide/style-proof/still_*.png`.

## 5. Provenance & disclosure

Same as every paper world: fetch in-video art with `tools/imagegen.py fetch … --project
<dir> --in-video`; stylized, non-photoreal, so `ai_generated_visuals: true`,
`synthetic: false`, YouTube altered-content answer **No**.
