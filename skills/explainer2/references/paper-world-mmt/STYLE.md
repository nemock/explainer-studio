# MMT tangerine paper-world style — LOCKED (2026-08-06)

The Magnific-papercraft look for **Monday MedTech** (theme key `mmt-tangerine`, hue:
orange). Locked with the video brand system
(`make_money/routine_changes/2026-08-06-video-brand-system-palettes-locked.md`).

Per-show variant of [`../paper-world/STYLE.md`](../paper-world/STYLE.md). Shared doctrine
— model settings, substrate neutrality (NEVER regenerate substrates; grounds tint at
runtime), chibi presenter staging, provenance/disclosure — is identical to
[`../paper-world-fwf/STYLE.md`](../paper-world-fwf/STYLE.md) §2/§6 and is not repeated.

## 1. The palette (strict — matches `mmt-tangerine` in `src/explainer2/themes.py`)

| Role | Hex | Use |
|---|---|---|
| Deep tangerine paper background | `#C25012` | the ground |
| Warm cream paper | `#FFF2E5` | figures, tubing, linework |
| Aqua accent | `#7FD9CF` | ONE accent (clinical instrument nod), sparingly |
| Apricot | `#F2B279` | secondary marks only |

## 2. The canonical PROMPT RECIPE (copy verbatim, fill `{SUBJECT}` / `{SETTING}`)

> Layered cut-paper collage illustration, handmade papercraft style with visibly torn and
> cleanly-cut paper edges and soft drop shadows between stacked paper layers. Subject:
> {SUBJECT}. {SETTING}. Editorial explainer / storybook aesthetic, flat and clean. Color
> palette strictly: deep tangerine-orange paper background (#C25012), warm cream paper for
> figures and linework (#FFF2E5), and a single soft aqua paper accent (#7FD9CF) used
> sparingly. Generous negative space, calm composition, no text, no words, no logos.

Model `gpt-2`, style anchor from §4. Always `simulate_cost` first.

## 3. The show mark (LOCKED 2026-08-06)

Coiled paper stethoscope: cream tubing in a symmetric concentric coil, aqua earpieces and
chest piece. Chosen from a 4-take proof (take 1 — the coil reads as a true emblem).

| Asset | Where |
|---|---|
| Magnific library product | `mmt-stethoscope-mark`, id `2138937` — `references: [{type: "product", identifier: "2138937"}]` |
| Transparent cutout | [`mark/mmt_stethoscope_mark.png`](mark/mmt_stethoscope_mark.png) (RGBA 1024²) |
| Source render (on tangerine) | [`mark/mmt_stethoscope_mark_source.png`](mark/mmt_stethoscope_mark_source.png) — thumbnail-ready |
| Generation record | [`mark/provenance.json`](mark/provenance.json) |

## 4. Style anchors

The mark source render (creation `O69dBMwynm`) is the world's canonical style reference.
Scene anchors: TBD at the show's first explainer2 episode — add the first approved scene
here. Cold-start: re-upload the source PNG as a style reference or run §2 fresh.
