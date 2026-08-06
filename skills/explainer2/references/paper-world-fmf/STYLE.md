# FMF brick-red paper-world style — LOCKED (2026-08-06)

The Magnific-papercraft look for **Failure Modes Friday** (theme key `fmf-alarm`, hue:
red — the alarm color, kept brick-deep so long text stays comfortable). Locked with the
video brand system
(`make_money/routine_changes/2026-08-06-video-brand-system-palettes-locked.md`).

Per-show variant of [`../paper-world/STYLE.md`](../paper-world/STYLE.md). Shared doctrine
— model settings, substrate neutrality (NEVER regenerate substrates), chibi presenter
staging, provenance/disclosure — is identical to
[`../paper-world-fwf/STYLE.md`](../paper-world-fwf/STYLE.md) §2/§6 and is not repeated.

## 1. The palette (strict — matches `fmf-alarm` in `src/explainer2/themes.py`)

| Role | Hex | Use |
|---|---|---|
| Deep brick-red paper background | `#9E1B1B` | the ground |
| Warm chalk-white paper | `#FBEFE8` | figures, linework |
| Caution-yellow accent | `#F5C518` | ONE accent (the warning pairing), sparingly |
| Ash gray | `#C9CDD2` | secondary marks — the color of what's left after the failure |

Hazard-stripe motif available for kicker bars and section breaks (carried over from the
old mono look).

## 2. The canonical PROMPT RECIPE (copy verbatim, fill `{SUBJECT}` / `{SETTING}`)

> Layered cut-paper collage illustration, handmade papercraft style with visibly torn and
> cleanly-cut paper edges and soft drop shadows between stacked paper layers. Subject:
> {SUBJECT}. {SETTING}. Editorial explainer / storybook aesthetic, flat and clean. Color
> palette strictly: deep brick-red paper background (#9E1B1B), warm chalk-white paper for
> figures and linework (#FBEFE8), and a single caution-yellow paper accent (#F5C518) used
> sparingly. Generous negative space, calm composition, no text, no words, no logos.

Model `gpt-2`, style anchor from §4. Torn edges are on-theme here — this world may lean
into damage (tears, crumples, char-free wear) more than its siblings. Always
`simulate_cost` first.

## 3. The show mark (LOCKED 2026-08-06)

Warning triangle of layered chalk-white paper with torn edges, caution-yellow inner band
and bold exclamation mark. Chosen from a 4-take proof (take 3 — the yellow band punches
hardest at small size).

| Asset | Where |
|---|---|
| Magnific library product | `fmf-triangle-mark`, id `2138942` — `references: [{type: "product", identifier: "2138942"}]` |
| Transparent cutout | [`mark/fmf_triangle_mark.png`](mark/fmf_triangle_mark.png) (RGBA 1024²) |
| Source render (on brick red) | [`mark/fmf_triangle_mark_source.png`](mark/fmf_triangle_mark_source.png) — thumbnail-ready |
| Generation record | [`mark/provenance.json`](mark/provenance.json) |

## 4. Style anchors

The mark source render (creation `UPOMpQjwny`) is the world's canonical style reference.
Scene anchors: TBD at the show's first explainer2 episode. Cold-start: re-upload the
source PNG as a style reference or run §2 fresh.
