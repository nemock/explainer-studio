# FTT steel-blue paper-world style — LOCKED (2026-08-06)

The Magnific-papercraft look for **Founder Tip Tuesday** (theme key `ftt-study`, hue:
blue — the founder den moved to a midnight study; brass/parchment carry over). Locked
with the video brand system
(`make_money/routine_changes/2026-08-06-video-brand-system-palettes-locked.md`).

Per-show variant of [`../paper-world/STYLE.md`](../paper-world/STYLE.md). Shared doctrine
— model settings, substrate neutrality (NEVER regenerate substrates), chibi presenter
staging, provenance/disclosure — is identical to
[`../paper-world-fwf/STYLE.md`](../paper-world-fwf/STYLE.md) §2/§6 and is not repeated.

## 1. The palette (strict — matches `ftt-study` in `src/explainer2/themes.py`)

| Role | Hex | Use |
|---|---|---|
| Deep steel-blue paper background | `#1D3557` | the ground |
| Parchment paper | `#F0E8D2` | figures, linework |
| Brass accent | `#C9A24A` | ONE accent, sparingly |
| Clay | `#B5654A` | secondary warmth only |

Deliberately grayer and lighter than The Teardown's electric indigo (`#2E33A0`) — keep it
that way so the two blues never blur in a feed grid.

## 2. The canonical PROMPT RECIPE (copy verbatim, fill `{SUBJECT}` / `{SETTING}`)

> Layered cut-paper collage illustration, handmade papercraft style with visibly torn and
> cleanly-cut paper edges and soft drop shadows between stacked paper layers. Subject:
> {SUBJECT}. {SETTING}. Editorial explainer / storybook aesthetic, flat and clean. Color
> palette strictly: deep steel-blue paper background (#1D3557), warm parchment paper for
> figures and linework (#F0E8D2), and a single brass-gold paper accent (#C9A24A) used
> sparingly. Generous negative space, calm composition, no text, no words, no logos.

Model `gpt-2`, style anchor from §4. Always `simulate_cost` first.

## 3. The show mark (LOCKED 2026-08-06)

Paper lightbulb of layered parchment with a glowing brass filament — "tip" made literal.
Chosen from a 4-take proof (take 1 — the lit filament reads idea-switched-on).

| Asset | Where |
|---|---|
| Magnific library product | `ftt-lightbulb-mark`, id `2138938` — `references: [{type: "product", identifier: "2138938"}]` |
| Transparent cutout | [`mark/ftt_lightbulb_mark.png`](mark/ftt_lightbulb_mark.png) (RGBA 1024²) |
| Source render (on steel blue) | [`mark/ftt_lightbulb_mark_source.png`](mark/ftt_lightbulb_mark_source.png) — thumbnail-ready |
| Generation record | [`mark/provenance.json`](mark/provenance.json) |

## 4. Style anchors

The mark source render (creation `CqFP99ZEEy`) is the world's canonical style reference.
Scene anchors: TBD at the show's first explainer2 episode. Cold-start: re-upload the
source PNG as a style reference or run §2 fresh.
