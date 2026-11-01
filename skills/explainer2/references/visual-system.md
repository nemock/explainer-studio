# Visual system — type scale, lit paper, layout, visual QA (paper worlds)

**This file owns** how big type is, how paper is lit, how a slide uses its space, and how a
rendered video is checked at the size it is watched. motion-playbook (what moves, and why),
deck-playbook (what to author) and the papercraft specs point here instead of restating it.

Origin: the 2026-11-01 visual upgrade (decision doc
`make_money/routine_changes/2026-11-01-visual-upgrade-phone-type-lit-paper.md`). #79 was the
channel's most-viewed video, and on a phone its headlines were unreadable over a mostly empty
frame, and its post-its still read as rendered boxes.

---

## 0. Which worlds this applies to

Two world tokens in `remotion/src/brands/papercraft.ts`, both opt-in per theme:

| token | what it turns on |
|---|---|
| `phoneType` | the type scale below, the slide heading, content sized to the space, 44 px captions |
| `lit` | lit paper: real fibre, a light falloff across each sheet, two shadows from one light |

**On today: `nemock-deep-dive` only** (operator 2026-11-01: deep dives first). Every other
theme renders byte-for-byte as before. A world joins by setting both tokens AND adding its
theme to `PHONE_TYPE_THEMES` in `src/explainer2/remotion_engine.py` (captions and annotation
snapping read that tuple). Prove it on stills of that show first (§6). Never flip a global
default (theme-keyed branding isolation).

## 1. The phone test (the rule everything else serves)

A 16:9 video on a phone held upright is **about 390 pt wide**. A 1080 frame shrinks by ~0.2.
Small type reads from about 9–10 pt on a phone, which is **about 48 px in a 1080 frame**.
Anything a viewer must read is at least that. #79 shipped kickers at 32 px (6.5 pt), note
sub-lines at 22 px (4.5 pt) and captions at 28 px.

Not comically large either: the scale tops out where a slide still has air around its content,
and the fill check (§5) flags a wall of type as readily as an empty frame.

## 2. The type scale (`remotion/src/type.ts`)

Sizes are **roles**, fractions of the frame's SHORT side (so 16:9 and 9:16 share a scale).
`size` is the natural size, `min` the phone floor that fitted text never goes under.

| role | use | size → px at 1080 | floor |
|---|---|---|---|
| `display` | the one big term/line a slide is about (define term, reframe "after") | 0.096 → 104 | 0.072 |
| `heading` | the slide's headline (see §2a) | 0.080 → 86 | 0.064 |
| `label` | the main words on an object: note, card, tray value, list item | 0.062 → 67 | 0.048 |
| `body` | a sentence set as reading text: a definition, a stat label | 0.047 → 51 | 0.042 |
| `sub` | an object's second line, an edge label, a tray header | 0.041 → 44 | 0.038 |
| `eyebrow` | the small caps line ABOVE a heading | 0.040 → 43 | 0.038 |
| `annotation` | hand-drawn mark labels | 0.040 → 43 | 0.038 |
| `caption` | a figure's caption line | 0.044 → 48 | 0.040 |

Burned-in captions: 44 px on phone-type themes (engine `captionFontSize`).

**In a component:** `const {ts, floor} = useTypeScale();` then
`fontSize: ts('label', height * 0.03)`. The second argument is the component's OLD literal,
which unscaled worlds still render, so adopting the scale never moves another show. Never add
a bare `height * 0.0NN` under 0.044: `tools/test_type_floor.py` fails the build (a ratchet:
each file may only keep its 2026-11-01 count of legacy literals, and the count only goes down).

### 2a. Kicker → heading

On a phone-type world the deck's `kicker` changes job:
- **alone** (no `title`/`headline` on the slide): it IS the headline. Set in ink, `heading`
  size, sentence case as authored, balanced wrap. (#79: "Three-SAT", "Two bets".)
- **above a title**: it stays an uppercase green eyebrow, at `eyebrow` size.

Author kickers knowing this: a lone kicker should read as a headline ("Two bets"), not a
label ("SECTION 2").

### 2b. Heading face

Headings can take a display face via project.json:
`"heading_font": {"family": "Fraunces", "file": "fonts/fraunces-latin.woff2"}` (file under the
render's public dir). Absent → the system sans. Trialed 2026-11-01: Fraunces, Bricolage
Grotesque, Archivo (all OFL); **no face chosen yet** — the operator's call. Body, labels and
captions always stay in `BRAND.font`.

## 3. Lit paper (`PaperNote.tsx` → LIT PAPER)

The substrate library (papercraft-substrate-plan.md) put real generated paper under every
card and note. On screen it still read as boxes because the tint step lifted brightness
(washing out the paper's own light and grain), background removal stripped the cast shadow
and each component added one flat CSS blur, and nothing lit the object itself. On `lit`
worlds:

1. **Tint after a contrast lift**, not a brightness wash: `grayscale(1) contrast(1.32)
   brightness(1.07)` then the multiply tint. Fibre survives.
2. **A light falloff across every sheet** from the world's one light (upper left,
   papercraft-motion-spec §6): a soft-light gradient masked to the paper's own edge, pre-
   mirrored for flipped takes so the light never jumps.
3. **Two shadows from that light**: a tight contact shadow and a soft cast shadow.
   `litShadowFilter(U, lift)` for cut-out shapes, `litBoxShadow(U, lift)` for rectangles.
   `lift` > 1 for objects higher off the table (a figure mount, the number card).
   No other shadow values on a lit world; the old blurred-ellipse contact shadows switch off.
4. **Ink printed into the paper** (`mix-blend-mode: multiply` on text over paper).
5. **Cut-paper corners**: radius ≤ 6 px, never a 20–26 px UI radius.
6. **No CSS surfaces left**: compare headers are tinted paper labels, counter chips are card
   stock, the table's laid sheets are card stock, the footage window is a mounted print.

## 4. Layout: use the space

- **Schematic** (`Schematic.tsx` LAYOUT): notes widen up to 1.3× their authored width (capped
  short of the row neighbour; squares do not widen), then the whole diagram is fitted,
  uniformly, up to 1.2×, into the band between the heading and the captions (~0.18–0.73 of the
  frame) and centred. The author's relative composition is kept. A collision pass then gives way
  only where notes touch: squares give up being square together (peers stay peers), and each
  colliding note shrinks about its centre; heights are re-fitted to the text at its final size.
- **Figure**: column = eyebrow, heading (at the heading FLOOR, 69 px: the art is the content),
  mount; art ≤ 0.42 of frame height, lifted so the mount ends above the caption pill (~0.76).
  **Tape never covers content** (operator 2026-11-01): the corner tape reaches ~0.066H in along
  the corner's diagonal, so the art's corner must sit further in than that: side border +
  top border > 0.066H. A lit mount uses 0.06H at the sides and 0.03H top and bottom. A deep
  border all round also clears the tape but costs the art its height (#79's wide document
  crops shrank to a third of the frame on that proof).
- **Compare/list/counter/statement**: wider measures (0.41–0.74 of frame width) so bigger type
  wraps instead of overflowing; a long list item steps down to the `label` floor, never under.

## 5. Visual QA on a phone-type world

Run in this order; all through the render queue where they render (CLAUDE.md rule 9).

1. **`bin/explainer2 deckcheck <dir>`** — content checks, before the booth (unchanged).
2. **Annotations on a schematic name their node**: `{"kind": "circle", "target": "r", "cue": …}`
   (circle, box, underline, strike). The schematic draws it around the node's laid-out box,
   inside the camera, so it lands wherever layout puts the note; a strike crosses each wrapped
   line of the label. Frame coordinates cannot survive the type scale: on #79 the s13 and s29
   strikes landed on the wrong words until anchored. An old `at`/`from`-`to` mark sitting on a
   node is snapped to it on phone-type themes, with a spec warning asking for `target`. A bad
   id, or `target` off a schematic, is refused (`BLOCKED-MARKS.md`).
3. **`python3 tools/mark_stills.py <dir>`** — figure `marks` on real rendered frames (unchanged).
4. **`python3 tools/phone_sheet.py <dir>`** — after the render. One frame per slide at 390 px
   wide, tiled to `work/phone_sheet.png`; Read its preview, at 100%. If you cannot read a slide
   there, a viewer cannot. Its **fill check** is advisory: `SPARSE` (< 8% of the band is
   edge-dense, or the content box < 25%) or `CROWDED` (≥ 24% edge-dense). Calibrated on #79:
   shipped "Two bets" 4.9% → re-rendered 12.1%; the crowded s17 re-render 24.4%.
5. **`python3 tools/test_type_floor.py`** — after any component change.

## 6. Proving a change

Re-render chosen slides of a shipped project with the new engine, never into the project:
copy its deck + timing to a scratch dir, build the spec, render stills at the frame the
shipped framecheck used (92% through each slide), tile before/after and phone sheets. The
2026-11-01 tool is `work/visual-upgrade/proof_stills.py` (gitignored scratch, run through
`explainer2 submit`). Sample every slide TYPE the change touches, and the last frame of
anything that builds.

## 7. Not done yet (as of 2026-11-01)

- **New object families** (Magnific; quote credits first, operator approves): ruled index
  cards, kraft tags, folders, pins and clips, and a relight pass on the existing notes/cards.
- Other paper worlds have not opted in.
- A strike across a short second label line runs the note's width (line widths are estimated).
- Portrait (Shorts) keeps the authored schematic geometry; only sizes change there.
