# FWF violet paper-world style — LOCKED (2026-08-06)

The Magnific-papercraft look for the **Founders Who Finish daily founder tip** show
(brand FFW, background hue: violet — the book cover's color). Style-proofed and locked by
the operator 2026-08-06 as the first of the per-show worlds in the video brand system
(`make_money/routine_changes/2026-08-06-video-brand-system-palettes-locked.md`).

This file is the per-show variant of [`../paper-world/STYLE.md`](../paper-world/STYLE.md)
(the cream/navy nemock-deep-dive world). Everything that file says about model settings,
character consistency mechanisms, cost simulation, and provenance/disclosure applies here
unchanged; this file records only what differs for the FWF world.

---

## 1. The palette (strict — matches the FWF daily-tip theme)

| Role | Hex | Use |
|---|---|---|
| Deep violet paper background | `#36185B` | the ground every scene sits on |
| White paper | `#FFFFFF` | figures, pages, linework, primary shapes |
| Indigo accent | `#757BBD` | ONE accent (a laptop lid, a cover, a note) used sparingly |

No fourth color. The show's theme locks accent2 to the same indigo so nothing off-brand
can leak in; imagery follows the same rule.

## 2. Substrates — do NOT regenerate

The shared substrate libraries (`remotion/public/papercraft-grounds|cards|notes|fixings`)
are palette-neutral by design: grounds are flat grey tiles the runtime multiplies with
the theme color; notes/cards are desaturated then multiply-tinted; tape is deliberately
beige. The violet ground comes from theme tokens at render time. Per-show Magnific spend
is the mark + per-episode scene art only. (Established during the 2026-08-06 style
proof; see each substrate library's provenance.json.)

## 3. The canonical PROMPT RECIPE (copy verbatim, fill `{SUBJECT}` / `{SETTING}`)

> Layered cut-paper collage illustration, handmade papercraft style with visibly torn and
> cleanly-cut paper edges and soft drop shadows between stacked paper layers. Subject:
> {SUBJECT}. {SETTING}. Editorial explainer / storybook aesthetic, flat and clean. Color
> palette strictly: deep violet paper background (#36185B), white paper for figures and
> linework (#FFFFFF), and a single soft indigo paper accent (#757BBD) used sparingly.
> Generous negative space, calm composition, no text, no words, no logos.

- Model `gpt-2`, style-anchored: pass one of the §5 anchors as
  `references: [{type: "style", identifier: "<id>"}]`.
- Keep the "no text, no words, no logos" clause — the engine adds all typography.
- Always `simulate_cost` (free) before a paid call.

## 4. The show mark (LOCKED 2026-08-06)

The memetic logo for thumbnails, title cards, and stings: a standing open paper book,
indigo covers with a white botanical emblem, white fanned pages, on the violet ground.
Chosen by the operator from a 4-take proof (take 1 — cleanest silhouette at feed size).

| Asset | Where |
|---|---|
| Magnific library product | `fwf-book-mark`, library id `2138879`, identifier `pvxGOehwnQ` — pass as `references: [{type: "product", identifier: "2138879"}]` to re-pose consistently |
| Transparent cutout | [`mark/fwf_book_mark.png`](mark/fwf_book_mark.png) (RGBA 1024²) |
| Source render (on violet) | [`mark/fwf_book_mark_source.png`](mark/fwf_book_mark_source.png) — thumbnail-ready as-is |
| Generation record | [`mark/provenance.json`](mark/provenance.json) |

## 5. Style anchors (the 2026-08-06 proof set)

Canonical violet-world creations; pass as a style reference for continuity:

| Creation | What it is |
|---|---|
| `N2R8h9T6D9` | the mark source render (book on violet, 1:1) |
| `s7UWMJUl8e` | founder at desk with indigo laptop + rising paper stack (16:9) — the scene anchor |
| `xSlz0UNjfW` | second desk scene, pensive pose (16:9) |

Cold-start fallback: re-upload `mark/fwf_book_mark_source.png` as a style reference, or
run the §3 recipe fresh — it reproduces the look on its own.

## 6. The presenter

Dave's chibi character joins scenes as a bottom-corner cutout via `chibi/<pose>` deck
refs — see the CHIBI_DIR note in `src/explainer2/remotion_engine.py`. The chibi is a
separate private library and is NOT generated with this recipe; never try to redraw him
via Magnific prompts.
