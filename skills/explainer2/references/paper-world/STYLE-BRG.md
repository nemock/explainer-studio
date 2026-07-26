# BRG paper world — the Base Reality Group style palette (LOCKED 2026-07-26)

The papercraft identity for the **Base Reality Group** deep-dive series (theme
`brg-deep-dive`). Sibling to [STYLE.md](STYLE.md), which is Dave's personal /
davesaunders.net world (`nemock-deep-dive`). **Two different brands, two worlds — never
repaint one to serve the other.**

## 1. What BRG is (get this right before generating anything)

**BRG is not a medtech brand.** Base Reality Group helps **entrepreneurs and business
operators build products, build product roadmaps, and run their businesses better.**
MedTech is Dave's personal background and shows up as a worked example in individual
videos (e.g. #50's hospital buying map) — it is not BRG's focus. So this world's
vocabulary is **general business/product**: founders and operators, roadmaps, products,
customers, decisions. Per-video subject props (a surgeon, a hospital committee) are
scene dressing for THAT video, never part of the reusable BRG cast.

The other brand boundary: BRG's CTA is **baserealitygroup.com** — the practice. It never
carries the book/newsletter CTA, and its CTA card renders **book-less** (`cta_book: false`).

## 2. The palette (strict)

| Role | Hex | Use |
|---|---|---|
| Cream page | `#f5f0eb` | the base sheet (a shade cooler than FWF's `#f4ecd6`) |
| Navy ink | `#1b2b4b` | figures, linework, body text, the wordmark |
| BRG indigo accent | `#7b5bff` | the ONE accent — kickers, highlighted words, accent sheet |
| Indigo soft | `#c3b4ff` | secondary accent (kicker over the dark ground) |
| Navy ground | `#1b2b4b` / deep `#12203a` | the papercraft "table" under set scenes |
| Paper shade | `#e5dcce` | card thickness / fold shading |

Indigo (not teal) is BRG's in-video accent, matching the series' thumbnails
(operator decision 2026-07-26). The **teal** `#0d7377` world is BRG *marketing/promo*
(`brg-paper`, the Plan to Market cohort promo) — a different, still-live palette.

## 3. Where it lives in the engine

| Piece | Where |
|---|---|
| Theme | `themes.py` → `brg-deep-dive` (cream/navy/indigo, Fraunces + Inter) |
| Text ink | `remotion/src/ink.tsx` → `PAPER_BRG_DEEP` (navy body, indigo `accent`) |
| World tokens | `remotion/src/brands/papercraft.ts` → `PAPER_BRG_DEEP` + `paperWorldFor()` |
| World plumbing | `PaperWorld.tsx` → `WorldProvider` / `useWorld()` (theme-keyed, FWF default) |
| Brand sting | `components/BRGPaperSting.tsx` — BRG's indigo D+rocket mark, baserealitygroup.com |
| Sting asset | `<project>/brand/brg-sting-mark.png` (copy of `brg-logo-d-indigo.png`), staged by `render()` |
| Routing | `remotion_engine.py` — papercraft type map, PaperHook, BRGPaperSting, book-less CTA |

**Isolation rule (why it is built this way):** `nemock-deep-dive` (Dave's book/site world)
and `brg-paper` (the cohort promo) were BOTH already in use. Adding a palette is safe;
repainting one is not. Verified: an FWF still rendered before and after this work is
**byte-identical** (same md5) — zero regression.

## 4. Generating art for this world (Magnific)

Use the [STYLE.md](STYLE.md) §3 recipe with the BRG palette substituted:

> Layered cut-paper collage illustration, handmade papercraft style with visibly torn and
> cleanly-cut paper edges and soft drop shadows between stacked paper layers. Subject:
> {SUBJECT}. {SETTING}. Editorial explainer / storybook aesthetic, flat and clean. Color
> palette strictly: warm cream paper background (#f5f0eb), deep navy-ink paper for figures
> and linework (#1b2b4b), and a single indigo paper accent (#7b5bff) used sparingly.
> Generous negative space, calm composition, no text, no words, no logos.

**Cast — general business, reusable across the 10-piece series** (not yet generated;
generate on first need, then add rows here + save PNGs beside this file):
the founder/operator · the customer/buyer · an advisor/second-opinion figure ·
product & roadmap objects (a board of cards, a product box, a calendar, a signed contract).
Follow STYLE.md §4 for character consistency and §7 for provenance/disclosure
(`ai_generated_visuals: true`, `synthetic: false`, YouTube altered-content **No**).

## 5. Verified

Still-rendered 2026-07-26: BRG sting (indigo mark + wordmark on cream), PaperHook
(cream page, navy ink, indigo accent words), PaperStatement (navy ground, cream card),
book-less PaperBookCTA (BRG contact). Fixture: `remotion/motion-lab.json` pattern with
`"theme": "brg-deep-dive"`.
