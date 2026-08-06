# WSC goldenrod paper-world style — LOCKED (2026-08-06)

The Magnific-papercraft look for **Who Signs The Check** (theme key `wsc-goldenrod`, hue:
yellow — the file-folder/ledger-jacket color purchase orders travel in). Locked with the
video brand system
(`make_money/routine_changes/2026-08-06-video-brand-system-palettes-locked.md`).

Per-show variant of [`../paper-world/STYLE.md`](../paper-world/STYLE.md). Shared doctrine
— model settings, substrate neutrality (NEVER regenerate substrates), chibi presenter
staging, provenance/disclosure — is identical to
[`../paper-world-fwf/STYLE.md`](../paper-world-fwf/STYLE.md) §2/§6 and is not repeated.

## 1. The palette (strict — matches `wsc-goldenrod` in `src/explainer2/themes.py`)

| Role | Hex | Use |
|---|---|---|
| Goldenrod paper background | `#F2C94C` | the ground (the grid's only light tile) |
| Deep ledger-green paper | `#1F3D2E` | figures, linework, ink |
| Copper accent | `#A4551E` | ONE accent (coin, pen), sparingly |
| "Sign here" red | `#B3271D` | reserved for each episode's ONE flag |

## 2. The canonical PROMPT RECIPE (copy verbatim, fill `{SUBJECT}` / `{SETTING}`)

> Layered cut-paper collage illustration, handmade papercraft style with visibly torn and
> cleanly-cut paper edges and soft drop shadows between stacked paper layers. Subject:
> {SUBJECT}. {SETTING}. Editorial explainer / storybook aesthetic, flat and clean. Color
> palette strictly: goldenrod-yellow paper background (#F2C94C), deep ledger-green paper
> for figures and linework (#1F3D2E), and a single copper paper accent (#A4551E) used
> sparingly. Generous negative space, calm composition, no text, no words, no writing,
> no signatures, no numbers, no logos.

Model `gpt-2`, style anchor from §4. Keep the extended no-writing clause — money
subjects (checks, ledgers, invoices) invite rendered text. Always `simulate_cost` first.

## 3. The show mark (LOCKED 2026-08-06)

Blank paper bank check with a ledger-green fountain pen resting across it, copper nib.
Chosen from a 4-take proof (take 3 — boldest border, most prominent pen). The blank
ruled lines are deliberate: they are what make it read as a check.

| Asset | Where |
|---|---|
| Magnific library product | `wsc-check-mark`, id `2138939` — `references: [{type: "product", identifier: "2138939"}]` |
| Transparent cutout | [`mark/wsc_check_mark.png`](mark/wsc_check_mark.png) (RGBA 1024²) |
| Source render (on goldenrod) | [`mark/wsc_check_mark_source.png`](mark/wsc_check_mark_source.png) — thumbnail-ready |
| Generation record | [`mark/provenance.json`](mark/provenance.json) |

## 4. Style anchors

The mark source render (creation `8ahgUPJIrU`) is the world's canonical style reference.
Scene anchors: TBD at the show's first explainer2 episode. Cold-start: re-upload the
source PNG as a style reference or run §2 fresh.
