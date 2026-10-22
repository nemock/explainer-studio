# PM Guide plum paper-world style — LOCKED (2026-10-19)

The visual world for **The Product Manager's Guide to Getting Sh\*t Done**
(`/Volumes/Casima/claudeCode/Product_Manager_Guide/`), theme `pmg-guide`. The sister world
to `paper-world-plg` (Product Leadership): same cream and navy, same paper physics, a plum
accent instead of rust so the two series read as siblings, not as one. Follow it verbatim.

## 1. The palette (strict)

| Role | Hex | Use |
|---|---|---|
| Warm cream paper background | `#f5f0eb` | the ground every scene sits on |
| Deep navy paper | `#1b2b4b` | figures, linework, primary shapes |
| Deep plum accent | `#7a2e5c` | ONE accent, used sparingly: a note, a cuff, a banner edge |

No fourth colour; `accent2 == accent` in the theme. ~7.8:1 on the cream, so plum carries
accent text. Operator-chosen 2026-10-19.

## 2. Substrates — do NOT regenerate

Same rule as plg-guide: `remotion/public/papercraft-grounds|cards|notes|fixings` are
palette-neutral. The series' own element directory is `remotion/public/papercraft-pmg/elements/`
(the warning triangle, recolored plum from plg's, 2026-10-19). Per-episode Magnific spend is
scene art only.

## 3. The canonical PROMPT RECIPE (copy verbatim, fill `{SUBJECT}`)

> Layered cut-paper collage illustration, handmade papercraft style with visibly torn and
> cleanly-cut paper edges and soft drop shadows between stacked paper layers. Subject:
> {SUBJECT} Editorial explainer / storybook aesthetic, flat and clean. Color palette
> strictly: warm cream paper background (#f5f0eb), deep navy paper for figures and linework
> (#1b2b4b), and a single deep plum paper accent (#7a2e5c) used sparingly. Generous negative
> space, calm composition, no text, no words, no letters, no numbers, no logos.

- Model `gpt-2`, style-anchored: `references: [{type: "style", identifier: "s7TxRhsl8e"}]`.
- Cost, measured 2026-10-19 with `simulate_cost`: **100 cr at 1k/medium (proofs), 600 cr at
  2k/high (final in-video art).** Re-quote before every batch.
- **Say what is blank.** Any card, note, page, banner, screen or receipt in a subject is
  described as blank / empty / unmarked, or the model fills it. Words are Remotion's job
  (`pageText`, titles, schematic labels).
- Recurring character: **the new product manager** at Fieldstone, a young woman with dark
  hair in a bun, navy clothing. Describe her in those words every time; the anchor carries
  her look. She is a composite's employee, never a real person.

## 4. Style anchor — LOCKED

Take 1 of the 2026-10-19 four-take proof (1k/medium), the one generated with the
Product Leadership anchor (`rglbjzsxtc`) as its style reference, which is what keeps the two
series visibly related. Subject: seven blank paper columns on a cream wall, a pile of blank
notes on the fourth (planning), one plum note, the new PM at a desk facing the wall.

| | |
|---|---|
| Creation identifier | `s7TxRhsl8e` |
| Local file | `Product_Manager_Guide/style-proof/take1_s7TxRhsl8e.png` |
| Rejected takes | 2, 3, 4 in `style-proof/` (2 and 4 lacked the desk scene; 3 drew a second character) |

Why this one: it is the series' spine object (the seven-column map) and its recurring
character in one frame, and it inherited the sister series' paper finish.

## 5. Series mark, badge

Not yet made. The thumbnails are photoreal Dave (series CLAUDE.md), so a mark is only
needed if an on-screen series badge is wanted; decide before module 2.
