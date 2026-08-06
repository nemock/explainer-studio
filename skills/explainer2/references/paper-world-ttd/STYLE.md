# TTD indigo paper-world style — LOCKED (2026-08-06)

The Magnific-papercraft look for **The Teardown** (theme key `ttd-indigo`, hue: indigo —
the blueprint world). Locked with the video brand system
(`make_money/routine_changes/2026-08-06-video-brand-system-palettes-locked.md`).

Per-show variant of [`../paper-world/STYLE.md`](../paper-world/STYLE.md). Shared doctrine
— model settings, substrate neutrality (NEVER regenerate substrates), chibi presenter
staging, provenance/disclosure — is identical to
[`../paper-world-fwf/STYLE.md`](../paper-world-fwf/STYLE.md) §2/§6 and is not repeated.

## 1. The palette (strict — matches `ttd-indigo` in `src/explainer2/themes.py`)

| Role | Hex | Use |
|---|---|---|
| Electric-indigo paper background | `#2E33A0` | the ground |
| Near-white paper | `#EDF0FF` | components, linework |
| Safety-orange accent | `#F2762E` | ONE accent (annotations, callouts), sparingly |
| Periwinkle | `#9BA8F5` | quiet secondary marks only |

Deliberately vivid and blue-leaning: it must never blur with the daily tip's red-leaning
violet (`#36185B`) or Founder Tip Tuesday's gray steel blue (`#1D3557`).

## 2. The canonical PROMPT RECIPE (copy verbatim, fill `{SUBJECT}` / `{SETTING}`)

> Layered cut-paper collage illustration, handmade papercraft style with visibly torn and
> cleanly-cut paper edges and soft drop shadows between stacked paper layers. Subject:
> {SUBJECT}. {SETTING}. Editorial explainer / storybook aesthetic, flat and clean. Color
> palette strictly: deep electric-indigo paper background (#2E33A0), near-white paper for
> figures and linework (#EDF0FF), and a single safety-orange paper accent (#F2762E) used
> sparingly. Generous negative space, calm composition, no text, no words, no logos.

Model `gpt-2`, style anchor from §4. Exploded views, cutaways, and layered assemblies are
this show's native subjects — lean into them. Always `simulate_cost` first.

## 3. The show mark (LOCKED 2026-08-06)

Exploded-view paper device: near-white layered components hovering apart in a vertical
stack, thin connector lines, safety-orange accents. Chosen from a 4-take proof (take 2 —
tightest stack, reads as one object even tiny).

| Asset | Where |
|---|---|
| Magnific library product | `ttd-exploded-mark`, id `2138941` — `references: [{type: "product", identifier: "2138941"}]` |
| Transparent cutout | [`mark/ttd_exploded_mark.png`](mark/ttd_exploded_mark.png) (RGBA 1024²) |
| Source render (on indigo) | [`mark/ttd_exploded_mark_source.png`](mark/ttd_exploded_mark_source.png) — thumbnail-ready |
| Generation record | [`mark/provenance.json`](mark/provenance.json) |

## 4. Style anchors

The mark source render (creation `0eDbKU0TfW`) is the world's canonical style reference.
Scene anchors: TBD at the show's first explainer2 episode. Cold-start: re-upload the
source PNG as a style reference or run §2 fresh.
