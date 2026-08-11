# Product Leadership rust paper-world style — LOCKED (2026-08-11)

The visual world for **The Operator's Guide to Product Leadership**
(`/Volumes/Casima/claudeCode/Product_Leadership_Operators_Guide/`), theme `plg-guide`.

Same structure as the FWF/WTE/show worlds: strict three-colour palette, shared substrates,
one canonical prompt recipe, one locked style anchor. Follow it verbatim — the point of a
locked world is that module nine looks like module one.

## 1. The palette (strict)

| Role | Hex | Use |
|---|---|---|
| Warm cream paper background | `#f5f0eb` | the ground every scene sits on |
| Deep navy paper | `#1b2b4b` | figures, cards, linework, primary shapes |
| Rust / terracotta accent | `#a8481f` | ONE accent, used sparingly — a single card, a sun, a marked edge |

No fourth colour. The theme locks `accent2 == accent` so nothing off-brand can leak; imagery
follows the same rule. Cream may also appear as a *cut shape* on navy (see the anchor) —
that is the same cream, not a fourth colour.

**Why rust.** This series teaches the same subject as the BRG deep-dive series but is a
different product: free, ungated, like-and-subscribe, outside the sales funnel. Sharing
BRG indigo (`#7b5bff`) would make two different things read as one in a thumbnail grid.
Rust also sits furthest from WTE teal (`#0d7377`), Circumvent gold (`#c89b3c`) and the
studio green. Contrast on cream is ~5.1:1, so it carries accent TEXT, not just fills.

## 2. Substrates — do NOT regenerate

`remotion/public/papercraft-grounds|cards|notes|fixings` are palette-neutral by design:
grounds are flat grey tiles multiplied with the theme colour, notes/cards are desaturated
then multiply-tinted, tape is deliberately beige. Per-series Magnific spend is **the mark
plus per-episode scene art only**.

**Open risk, test before episode one:** the tint path is `grayscale(1) brightness(1.18)`
then a pastel multiply. A warm multiply over warm paper has gone wrong before — yellow
notes went sage. Rust over cream is that same shape of risk. Render one still of a
rust-tinted post-it on the cream ground and look at it.

## 3. The canonical PROMPT RECIPE (copy verbatim, fill `{SUBJECT}` / `{SETTING}`)

> Layered cut-paper collage illustration, handmade papercraft style with visibly torn and
> cleanly-cut paper edges and soft drop shadows between stacked paper layers. Subject:
> {SUBJECT}. {SETTING}. Editorial explainer / storybook aesthetic, flat and clean. Color
> palette strictly: warm cream paper background (#f5f0eb), deep navy paper for figures and
> linework (#1b2b4b), and a single rust-terracotta paper accent (#a8481f) used sparingly.
> Generous negative space, calm composition, no text, no words, no logos.

- Model `gpt-2`, style-anchored: `references: [{type: "style", identifier: "rglbjzsxtc"}]`.
- **Keep "no text, no words, no logos".** Every label in this series is Remotion typography
  rendered on top. This is not a stylistic preference — it is what lets one asset serve
  several modules with different labels, and it is why the decision-set visual costs nothing.
- `simulate_cost` (free) before every paid call. Measured: 130 cr at 1k/medium, 700 cr at
  2k/high. Proof at 1k/medium, final in-video art at 2k/high.
- WebP out. Paper never stretches — fit, never distort.

### Prompting note learned in the Phase 0 proof

**Say what is ON the cards, or the model will decorate them.** Three of four proof takes
filled each card with landscapes, foliage and vases — attractive, and structurally useless,
because this world's cards must stay blank for typography. When a subject includes cards,
panels or pages, state explicitly that they are *blank / empty / unmarked*.

Separately: the word "hand" tripped a content-filter false positive on one take. If it
recurs, describe it as "a simple cut-paper hand shape" or drop it.

## 4. Style anchor — LOCKED

Take 1 of the 2026-08-11 four-take proof, chosen by the operator. Subject: four blank navy
cards in a row on cream, a cut-paper hand placing the fourth, one card carrying a torn rust
shape.

| | |
|---|---|
| Creation identifier | `rglbjzsxtc` — pass as `references: [{type: "style", identifier: "rglbjzsxtc"}]` |
| Local file | `Product_Leadership_Operators_Guide/style-proof/take1_rglbjzsxtc.png` |
| Provenance | `Product_Leadership_Operators_Guide/assets/imagegen/provenance.json` |
| Rejected takes | 2, 3, 4 — kept in `style-proof/` as the record of what was rejected and why |

Why this one: it is the only take whose cards are genuinely blank. It is also the series'
thesis as a single image — someone deliberately placing a decision rather than letting it
land by default.

## 5. The series mark — LOCKED (2026-08-11)

Four **blank** cut-paper cards fanned in a shallow arc: three deep navy, the fourth rust
and forward. It is the spine object (the Decision Set) as an object. Deliberately not a
book (that is FWF) and not a rocket-and-D (that is BRG). Take 4 of a four-take proof,
chosen by the operator for the crispest silhouette and the strongest rust read at badge
size.

| Asset | Where |
|---|---|
| Magnific library **product** | `plg-cards-mark`, library id **`2156054`** — pass as `references: [{type: "product", identifier: "2156054"}]` to re-pose consistently |
| Transparent cutout (USE THIS) | `Product_Leadership_Operators_Guide/mark/plg_cards_mark_clean.png` — RGBA 1024², matte-cleaned |
| Raw cutout (superseded) | `mark/plg_cards_mark.png` — kept for reference; has an edge halo, see below |
| Source render (on cream) | `mark/plg_cards_mark_source.png` — thumbnail-ready as-is |
| Rejected takes | `mark/mark_take1|2|3_*.png` |
| Provenance | `Product_Leadership_Operators_Guide/assets/imagegen/provenance.json` |

**Always composite from `plg_cards_mark_clean.png`.** A cream-paper subject cut from a
cream background leaves a light fringe on the silhouette — invisible on this world's cream
ground, obvious the moment the mark lands on a dark thumbnail. Verified by compositing on
grey, navy and near-black, then fixed with:

```bash
python3 tools/clean_matte.py mark/plg_cards_mark.png mark/plg_cards_mark_clean.png \
  --erode 2 --feather 1 --no-trim
```

The faint light lines *between* overlapping cards are real torn-paper edges in the artwork
and should stay — do not erode them away chasing a perfectly flat silhouette.

**Do not bake an episode number into the mark.** The badge number is Remotion/compositor
typography over the mark, for the same reason the cards stay blank.

## 6. The presenter

OFF for this world, matching the show-world decision of 2026-08-10, unless the operator
asks otherwise.
