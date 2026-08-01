# Papercraft substrate library — COMPLETE (phases 0–4 shipped 2026-07-31 → 2026-08-01)

> **Read §5–§5f first if you are picking this up.** They record what the plan below got
> wrong and why, which is more useful than the original proposal. Headlines:
> gpt-2 beats Nano Banana Pro for post-its; tint needs a desaturate step; paper never
> stretches; grounds ship as flat grey texture tiles blended with `overlay`; and before
> generating a new family, **check whether the surface is just a rectangle** — Phase 3
> needed 6 assets where the plan budgeted 25.


**Ask (operator, 2026-07-31):** replace the engine-drawn Remotion visual elements with
real Magnific papercraft, because the CSS-drawn ones now stick out next to the generated
paper. Named example: post-its. Named idea: build a size assortment (square, rectangular,
half-torn) so the shape can match the amount of text instead of forcing one size.

---

## 1. Why they stick out (the diagnosis)

Almost every "paper" object the engine draws goes through one primitive,
`PaperCard` in [PaperWorld.tsx:194](remotion/src/components/PaperWorld.tsx:194):

```js
background: world.paper,           // one flat cream, zero fiber
borderRadius: 14,                  // a perfect geometric radius
borderBottom: `6px solid ...`,     // a fake "thickness" edge
```

Three tells, and they are the same three every time:

1. **No grain.** A flat hex fill next to a Magnific asset with visible paper fiber reads
   as a UI element pasted into a photograph.
2. **Machine-perfect edges.** Real cut paper has a slightly irregular edge and a visible
   cut thickness that varies along its length. `borderRadius` does not.
3. **A drawn shadow, not a cast one.** `boxShadow` is a uniform blur. The Magnific assets
   have raking side light with a shadow that changes shape along the object.

The Schematic post-it ([Schematic.tsx:267](remotion/src/components/Schematic.tsx:267)) adds
a fourth: its folded corner is a `clipPath` triangle. It reads as a triangle, not a fold.

This is not a tuning problem. No amount of CSS texture fixes it, and the one attempt on
record (per-frame SVG turbulence) bloated files 50% and was reverted
(papercraft-motion-spec §9). The fix is to stop drawing paper and start photographing it.

## 2. The architecture: substrate and type are separate

**Magnific generates blank paper. Remotion renders the text on top.** Never bake words
into a generated asset.

This is already the negative-prompt constant in both existing libraries ("no text, no
lettering"), and it is the right call for four reasons: type stays crisp at 1080p and
above; `deck.json` authoring does not change at all; renders stay deterministic; and a
copy change costs zero credits instead of a regeneration round-trip.

So every asset below is a **blank substrate**. The engine picks one, sizes it, and lays
type on it.

## 3. The fitting problem (the part that decides the asset list)

Real paper does not stretch. Scale a 1:1 post-it PNG to 3:1 and the grain smears and the
torn edge turns to mush. Three strategies, and each asset class gets exactly one:

| strategy | how | used for |
|---|---|---|
| **A. Nearest-fit, fixed aspect** | generate a set of real aspect ratios, engine picks the nearest, squash capped at ±8% | post-its, tags, chips, cards — objects that genuinely have a shape |
| **B. Crop, don't stretch** | generate one long/tall piece, crop to the length needed | bars, connector strips, rules — uniform along their length |
| **C. 9-slice** | CSS `border-image`, corners fixed, middle repeats | caption pill, long label strips |

Strategy A is why Dave's instinct about the assortment is the correct one and not just a
nice-to-have: **the assortment IS the fitting mechanism.** Half-torn post-its aren't a
style choice, they're what you reach for when the text is two words and a square note
would leave a lake of empty cream.

Two rules that fall out of this:

- **Multiple takes per shape, mandatory.** A schematic puts 4–7 nodes on screen at once.
  One post-it PNG repeated seven times is *worse* than the CSS version, because identical
  paper grain is an obvious tell where identical flat cream is invisible. Minimum 4 takes
  per geometry, picked by a hash of the node id so renders stay deterministic.
- **Tint at runtime, don't generate per colour.** Generate cream only; multiply-blend the
  accent over it. Preserves the grain, guarantees exact palette values, and cuts the
  library by two thirds. I'll generate one lilac set as ground truth to check the tint
  against — if the blend looks dead next to it, we generate per colour instead and I'll
  say so.

## 4. The asset list

Palette is the FWF/nemock world (`PAPER_FWF`): cream `#FAF6EF`, ink `#2A1142`,
violet `#5A3494`, lilac `#C7B6E6`. Every asset passes a single style anchor as
`references[{type:"style"}]` so the family stays coherent, exactly as the Circumvent
library does.

### A. Note family — the post-its (24)

The headline request. Fitting strategy A.

| id | aspect | takes | what it's for |
|---|---|---|---|
| `note_square` | 1:1 | 4 | classic post-it, a short phrase |
| `note_half_torn` | 2:1 | 4 | **Dave's idea** — a square torn across, ragged long edge. Two or three words. |
| `note_wide` | 3:2 | 4 | a full clause |
| `note_tall` | 2:3 | 4 | stacked short lines, narrow columns |
| `note_strip` | 4:1 | 4 | one word, a label, a step name |
| `note_square_lilac` | 1:1 | 4 | ground truth for the tint test (§3) |

Every take: slight independent corner curl, one lifted corner catching the light, real
cast shadow, visible cut thickness. No adhesive strip drawn on — that reads as clip art.

### B. Card / panel family (12)

Replaces `PaperCard` itself, which upgrades punch cards, define tags, compare trays,
list cards, keep-cards and the CTA card **in one change**. Highest leverage item here.

| id | aspect | takes |
|---|---|---|
| `card_wide` | 16:9 | 3 |
| `card_panel` | 4:3 | 3 |
| `card_index` | 5:3, faint ruled lines | 3 |
| `card_tag` | 6:1, 9-sliceable | 3 |

### C. Counter chips (4)

`PaperCounter` slaps digits down as chips ([PaperData.tsx](remotion/src/components/PaperData.tsx)).
Small 1:1 squares with a thicker board feel than a note. 4 takes.

### D. Bars and columns (5)

`PaperStairs` currently draws `borderRadius: 8` rectangles. Fitting strategy B: generate
one tall column, crop from the bottom to the height needed.

`bar_column` ×3 (cream), `bar_column_bad` ×2 (the harder-shadow variant §6 mood).

### E. Connectors (6)

Schematic edges. `strip_h` ×3 (long, crop-to-length), `arrowhead` ×3 (transparent).

**Judgment call I want to flag:** paper strips work for orthogonal runs. Diagonal edges
would need per-angle assets or rotation that fights the baked lighting. My recommendation
is orthogonal runs get paper, diagonals keep the current drawn stroke. Mixing is fine
here because a drawn line reads as a drawn line, not as failed paper.

### F. Mounts and tape (10)

`Media.tsx:196` frames every figure in a white rounded box. Replace with a real mount.

`mount_landscape` ×2, `mount_portrait` ×2, `photo_corner` ×2 (transparent),
`tape_piece` ×4 (transparent, torn masking tape).

The tape is the cheapest high-impact item on this list — four transparent PNGs that make
every figure, keep-card and note look pinned to the table rather than floating over it.

### G. Grounds (3)

The table is currently a flat `#2A1142` plus a CSS vignette. Three wide ground textures
(paper, blotter, worn desk mat) lift *every scene in every video* for three generations.
Second-cheapest high-impact item.

### H. Tear masks (4)

The act-boundary tear already exists as a seeded SVG path. Four real torn-edge alpha
masks would replace it. Low priority, listed for completeness.

### I. Caption strip (3) — **recommend deciding separately**

The caption pill ([Captions.tsx:87](remotion/src/components/Captions.tsx:87)) is the most
visible synthetic element in the system: it's on screen for essentially every frame of
every video.

I am **not** recommending we convert it in this pass. Two reasons. Grain on a strip that
re-renders every couple of seconds risks shimmer, which is a jank problem, not a taste
problem. And the caption is arguably not a world object at all — it's an overlay, like a
lower third, and the synthetic look may be *correct* there. Worth a single test render
before committing either way.

**Total: ~70 assets, ~1,050 credits at GPT-2 rates.** Balance is 475,846. Even with three
rounds of iteration this is under 1% of what's on the account. Cost is not the constraint
on this project; coherence is.

## 5. Model choice — RESOLVED 2026-07-31: GPT-2

Phase 0 ran: three geometries × two models × two takes, same prompt, 540 credits.

**GPT-2 wins, and not on raw fidelity.** Nano Banana Pro has more surface texture, which
was the reason to test it — but it spends that texture on *handmade deckle-edge cotton
paper*. Torn edges on all four sides, irregular deckle, artisanal. That is the wrong
object. A post-it is machine-cut, and the clean square edge is exactly what makes it
instantly readable as a post-it, which is the operator's own argument for using them.
GPT-2 gave a clean square with a soft curled corner and consistent takes.

Convenient consequence: GPT-2 is already the locked anchor in paper-world/STYLE.md §2, so
**no re-render of the existing nemock assets is needed.** The world stays coherent for free.

Nano Banana Pro stays the right call where deckle *is* the object — torn sheets, aged
documents, hand-made paper props. Noted, not used here.

### Two prompt defects found (fix before the volume run)

- **"Torn in half" reads as two pieces.** Both models, one take in two, rendered the note
  torn *and both halves shown*. Prompt must say a single piece: "the lower half only, one
  piece, the other half absent."
- **The page flag prompt was too vague** and produced a plain rectangle with no flag
  character from either model. Needs rewriting from scratch, model-independent.

### The tint needs a desaturate step (proved, not assumed)

GPT-2 renders the post-it **yellow** even when the prompt says pale cream — the model
knows what colour a post-it is. That breaks a straight multiply: yellow × pastel blue is
sage, yellow × pastel green is olive. Both were muddy in test.

**Fix: desaturate to luminance, renormalise ~1.18× so the mid-tone sits near white, then
multiply.** All four pastels came out clean and correct with the grain and the curled
corner intact. This is now the required tint path, not an option.

Background removal preserves grain, cut edge and corner curl, and removes the baked cast
shadow. That is fine — the shadow is re-added in Remotion. The edge and the grain were the
tells; the shadow never was.

## 5b. Original reasoning (superseded, kept for the record)

The nemock paper world is anchored to a **GPT-2** recipe (paper-world/STYLE.md §2, 15cr).
The newer Circumvent library used **Nano Banana Pro** (75cr) and, to my eye, has better
edge fidelity and grain — which is the entire point of a substrate library.

But these have to sit next to the existing nemock assets, not next to Circumvent. So:

**Phase 0 is a bake-off.** Five post-its each way, composited against a real slide from
#53, side by side. Dave picks. ~450 credits, ~15 minutes. Everything downstream inherits
that decision, so it's worth spending the round-trip on.

## 5c. Phase 1 — SHIPPED 2026-07-31

24 substrates live in `remotion/public/papercraft-notes/`, `PaperNote.tsx` renders them, and
`Schematic` nodes use them on every paper theme. Both prompt defects fixed: every torn note
is now a single piece, and the flag got a swallowtail so it has a shape.

**Format: lossy WebP, not PNG.** PNG came to 12 MB for the set — paper grain is noise and PNG
cannot compress it. WebP with alpha at q90 is 1.5 MB total, 66 KB mean, no visible difference
on a paper substrate, and native to Chrome, which is what Remotion renders through.

**Engine change:** `remotion_engine.py` stages asset dirs by name. `papercraft-notes` had to
be added or nothing resolves. Unlike `papercraft/` and `papercraft-circumvent/`, it is staged
unconditionally, because no deck ever names these files — the component picks internally.

### The fitting rule changed after the first still

The plan said nearest-fit with a ±8% squash cap. The first render showed why that is wrong:
the deck's node boxes run about 4:1, the nearest substrate is 2.6:1, and stretching smeared
the grain and turned the torn edge to mush. **The box does not get to size the paper.** So:

> pick the WIDEST substrate no wider than the content needs, then set the box height to
> `width / substrate.aspect`.

Because the chosen aspect is ≤ the content aspect, the height always exceeds what the text
needs, and the surplus is blank note — which is what a real post-it looks like. The paper is
then drawn at its true aspect and never distorts. `fitNote()` in PaperNote.tsx.

**Variety: 16 apparent variants from 4 files.** Every take curls the same corner, and every
torn note is the *lower* half, so a row of four read as a repeating motif. Takes now flip on
both axes (`take & 1`, `take & 2`), hashed off the node id so renders stay deterministic. A
vertically flipped half-torn note is simply the upper half — equally real.

### Open, for the operator

- **Node aspect picks the family, so the deck controls the shape.** #53's nodes are wide and
  short, so all four land on `note_half_torn`. It reads fine, but a slide wanting real square
  post-its must author `shape: "square"` or a narrower `w`. The assortment only pays off if
  the deck asks for varied shapes — noted in deck-playbook §Schematic.
- **The pastels are softer than the CSS colours they replace.** The old `bad` node was a
  saturated coral; it is now pastel pink. Gentler, and on-brief per the operator's four
  pastels, but a `bad` node carries less alarm than it did. Worth a look before Phase 2.

## 5d. Phase 2 — SHIPPED 2026-08-01

12 card substrates in `remotion/public/papercraft-cards/` (`card`, `card_index`, `card_tag`
× 4 takes, 596 KB), a new `PaperSheet` primitive beside `PaperNote`, and `PaperCard` rebuilt
on top of it — which carries all 12 of its call sites at once: punch cards, define terms and
bodies, statement cards, list beats, promise headlines, counter cards and labels, stair
labels, step cards and the CTA card. `PaperCompare`'s tray drew its own paper rather than
going through `PaperCard`, so it was converted directly.

### Why these assets are deliberately boring

`PaperCard` is **content-sized** — it grows to fit its text — so Phase 1's trick (let the
paper's aspect set the box) has nothing to work with. That forces 9-slice, and 9-slice
forces the generation brief: **no curl, no tear, dead-straight edges, square corners, and
soft even frontal light.** A curl cannot survive being sliced into corner tiles, and raking
light bakes a gradient across the face that cannot tile. The uniform interior is the feature.

### Three fixes the stills forced

1. **`border-image`'s `fill` squashed the grain into vertical streaks.** A 587px-tall source
   painted into a 315px card compressed the fibre until it read as brushed linen. Fixed by
   dropping `fill` and painting the interior as a `background-size: auto` layer underneath —
   natural pixel scale, so it *cannot* distort, and grain now stays at one constant scale
   across every card in the video regardless of size. border-image draws only the cut edge.
2. **The card stock generates warmer than the world's cream** and read as kraft next to every
   other cream surface. Fixed by routing the substrate through the tint path with
   `tint={world.paper}`: real grain and real cut edge, colour landing exactly on the channel's
   token. Theme isolation comes free — BRG, Circumvent and Cut & Bond each get their own paper
   with no further work.
3. **Background removal leaves a 1–3px feathered fringe**, which 9-slice would smear along
   every border. The ingest trims past it. First attempt tested whole edge lines and the
   transparent *corners* vetoed each side, eating 25% of the card; it now samples the middle
   80% of each line, then squares the corners separately.

### Honest note on the payoff

This is a smaller visual step than Phase 1. The notes gained curls and torn edges — real
character. A card is just a card, so the gain is fibre, a true cut edge, and the loss of the
fake `borderBottom` thickness. Correct, but subtle. The compounding win is that it is now one
primitive: every future card surface inherits real paper for free.

Non-paper themes are untouched — `PaperCard` only ever renders inside the papercraft
components, and `substrate={false}` opts an individual card back out.

## 5e. Phase 3 — SHIPPED 2026-08-01

**The asset list in §4 (C–F) was wrong, and the reason matters.** It budgeted 25 new
generations for chips, bars, columns, connector strips, mounts and trays. Almost all of those
are *rectangles*, and after Phase 2 the engine already had a primitive that renders a real
paper rectangle at any size: `PaperSheet`. So Phase 3 generated **6** assets, not 25 — only
the things with a shape of their own — and wired everything else to what already existed.

The general rule for the rest of this project: **before generating a new substrate family,
check whether the surface is a rectangle.** If it is, it is a `PaperSheet` with a tint.

### New assets (6) — `remotion/public/papercraft-fixings/`

`tape_1..4` and `corner_1..2`, transparent, 164 KB. Tape is the cheapest high-impact element
in the whole library: a figure with tape on it is *fixed to the table*, and the same figure
without it floats. Deliberately **not** normalised to `world.paper` the way cards are — the
beige has to stay distinct from whatever it is holding down or it disappears into it.

### Converted with no new assets

| surface | was | now |
|---|---|---|
| Figure mount (`Media`) | flat `#fffcf5` rounded box | `card_index` sheet + two tape strips |
| Stairs risers | `W.paper` + fake `borderBottom` | per-step `PaperSheet` |
| Stage connector strips | `W.sheetAlt` bar | tinted `card_tag` |
| Flow step cards | `W.paper` + fake edge | `PaperSheet` |
| List number chips | `W.accentSoft` square | tinted `card_tag` |
| Schematic edge labels | flat `#fbf5df` pill | `card_tag` — these sit directly ON the note substrates, the most exposed synthetic surface on the slide |
| StatCounter meter | two flat pills | two tinted `card_tag` strips |

### The tape had to move outside the mount

First attempt put the tape inside the figure's frame and gated it off whenever the figure
pans (`tour` / Ken Burns), because the frame sets `overflow: hidden` there and tape sits at
negative offsets. That gate silenced tape on nearly every figure in the catalogue, since most
of them pan. Fixed with an outer wrapper: the mount still clips its own contents, the tape
hangs outside it.

### Not converted, deliberately

- **Schematic edges** stay hand-drawn Sharpie strokes (§4E). A drawn line reads as a drawn
  line, not as failed paper; only the orthogonal-strip idea was ever a candidate.
- **StatGrid** has no card at all — numbers straight on the ground. Nothing to convert.
- **The caption pill** (§4I) remains an overlay, per the operator's ruling.

### Unverified

`PaperStairs`, `PaperFlow` and `PaperList` do not appear in #53, so those four conversions
typecheck and follow the same pattern as the verified ones but have **not** been seen in a
render. Check them on the first video that uses them.

### Honest note on the meter

The `StatCounter` track is ~17px tall. Paper grain at that size is essentially invisible, so
this conversion buys consistency of *material* rather than a visible gain. It is not wasted —
it means there is no CSS-drawn surface left in the scene to catch the eye — but it should not
be described as an improvement anyone will notice on its own.

## 5f. Phase 4 — SHIPPED 2026-08-01. Project complete.

13 assets in `remotion/public/papercraft-grounds/` (1.4 MB): 3 cream grounds, 2 table grounds,
and 4 tears emitted as 8 complementary alpha masks.

- **The cream ground** is the single most-seen surface in the catalogue — behind every Figure,
  Schematic, StatCounter and StatGrid scene. It was a CSS radial gradient with a full-frame
  `feTurbulence` fractal-noise layer over it. Now it is generated paper fibre, which also
  retires a live SVG filter from every frame.
- **The table ground** sits under `PaperTable`'s laid sheets.
- **The act-boundary tear** was a seeded 9-point polygon. It is now a real torn fibre edge.

### Grounds ship as prepared TEXTURE TILES, not as sheets

The first attempt shipped the generated sheet as-is and normalised it at runtime with
`grayscale → brightness → multiply`, the same path the cards use. Measured on the render, the
fibre survived at about **one grey level** — the ground was indistinguishable from the CSS
gradient it replaced, and all that showed was the vignette.

The fix is to prepare the texture at ingest instead:

> high-pass the sheet (source minus a 60px gaussian), amplify the residual to a known standard
> deviation, and ship a **flat grey tile centred on 128**.

Runtime then draws the palette colour and lays the tile over it with **`mix-blend-mode:
overlay`** — not multiply, which would halve the brightness of a mid-grey tile. Overlay leaves
the mean exactly on the palette value and modulates only by the fibre. Removing the sheet's own
large-scale lighting is a feature, not a loss: the CSS light layer above supplies that, and two
competing gradients is what made the first attempt muddy.

Side benefit worth knowing: the amplified fibre **dithers the vignette**, so the gradient
banding visible in the old ground is gone.

### The tear masks are a complementary pair, and rotation direction is load-bearing

The tears generate horizontal but `TearReveal` wipes on a vertical seam, so they are rotated
at ingest. Two traps, both hit:

1. **`rotate(-90)`, not `rotate(90)`.** Only the clockwise quarter turn brings the paper to the
   left. Getting it backwards inverts both halves, and the render then shows each panel's own
   straight rectangular edge — the transition looked *worse* than the polygon it replaced, with
   no error anywhere. Caught by measuring the mask's alpha edge, not by reading the code.
2. **The right half is the same rotation with alpha INVERTED, never a horizontal mirror.**
   Mirroring reverses the notch profile and the two halves stop interlocking.

### Motion guardrail

The generated grounds are static images. The breathing light layer above them is deliberately
kept: a fully frozen frame risks tripping `freezedetect` in QA, and the paper world is meant to
read as alive-but-still.

### Where the project ends

Every CSS-drawn paper surface in the paper worlds is now real generated paper. What remains
synthetic is deliberate: the caption pill (an overlay, operator's ruling), the schematic's
hand-drawn Sharpie edges (a drawn line should read as drawn), and the non-paper themes, which
were never in scope.

## 6. Two constraints I want on the record before we start

**Memory.** The PRD budgets against 16GB unified memory and the render is already the
heavy stage. A schematic with seven nodes means seven PNG decodes per frame. Generate at
2k, then **downsample each substrate to about 2× its real on-screen size** before it goes
in git — a post-it occupies roughly 300px on a 1920 frame and does not need a 2048px
source. This also keeps a public repo from gaining 150MB of blank paper.

**Determinism.** Take selection must hash from the node/slide id, never from a random
call. Same deck, same render, always.

## 7. Phasing

Nothing here needs to land at once, and I'd rather prove the pipeline on one real slide
than deliver 70 assets on faith.

| phase | what | gate |
|---|---|---|
| ~~0~~ | ~~Model bake-off~~ | **DONE 2026-07-31 — GPT-2 (§5)** |
| ~~1~~ | ~~Note family (A) + wire `Schematic` nodes~~ | **DONE 2026-07-31 — 24 assets, gate passed on #53 s26/s10 (§5c)** |
| ~~2~~ | ~~`PaperCard` substrate (B)~~ | **DONE 2026-08-01 — 12 assets, 12 call sites + the compare tray (§5d)** |
| ~~3~~ | ~~Chips, bars, connectors, mounts, tape (C–F)~~ | **DONE 2026-08-01 — 6 assets (not 25), 7 surfaces converted (§5e)** |
| ~~4~~ | ~~Grounds + tears (G, H)~~ | **DONE 2026-08-01 — 13 assets (§5f). Project complete.** |
| **—** | Caption strip (I) | Not converted — operator's ruling: it is an overlay, and standing out is the better design |

Phases 1 and 2 are where nearly all the visible improvement is. If it stalls after 2,
the videos already look substantially better.

## 8. What does not change

Zero pipeline work. `remotion/public/papercraft/` is copied wholesale into the render's
public dir ([remotion_engine.py:709](src/explainer2/remotion_engine.py:709)), so new
subdirectories resolve with no engine change. `deck.json` authoring is untouched — the
substrate is chosen inside the component, not named in the deck. The record → align →
render loop is untouched.

Theme isolation holds: substrates live under the FWF/nemock world tokens and no component
flips unconditionally. Circumvent, BRG and Cut&Bond keep what they have unless we
deliberately build them their own.
