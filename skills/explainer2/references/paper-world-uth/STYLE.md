# UTH circuit-board teal paper-world style — LOCKED (2026-11-27)

The Magnific-papercraft look for **Under the Hood** (theme key `uth-circuit`), the Tuesday
show on Dave Saunders Dailies that replaced Founder Tip Tuesday
(`make_money/routine_changes/2026-11-27-founder-tip-tuesday-retired.md`). Short technical
explainers: how an AI or computing mechanism works, or a new paper explained.

Per-show variant of [`../paper-world/STYLE.md`](../paper-world/STYLE.md). Shared doctrine
(model settings, substrate neutrality, provenance/disclosure) is identical to
[`../paper-world-fwf/STYLE.md`](../paper-world-fwf/STYLE.md) §2/§6 and is not repeated. Like
the other weekday shows it renders through the Cvg scene family, and the chibi presenter is
blocked (`CHIBI_NEVER`).

## 1. The palette (strict — matches `uth-circuit` in `src/explainer2/themes.py`)

| Role | Hex | Use |
|---|---|---|
| Circuit-board teal paper background | `#0F3D3E` | the ground |
| Parchment paper | `#EDE6D6` | figures, linework |
| Copper accent | `#C8743A` | ONE accent, sparingly |
| Cyan | `#4FB3BF` | small secondary touches only (indicator lights, a highlight) |

Teal-green on purpose: it must never blur with Founder Tip Tuesday's steel blue (`#1D3557`,
retired but still in the archive) or The Teardown's electric indigo (`#2E33A0`).

## 2. The canonical PROMPT RECIPE (copy verbatim, fill `{SUBJECT}` / `{SETTING}`)

> Layered cut-paper collage illustration, handmade papercraft style with visibly torn and
> cleanly-cut paper edges and soft drop shadows between stacked paper layers. Subject:
> {SUBJECT}. {SETTING}. Editorial explainer / storybook aesthetic, flat and clean. Color
> palette strictly: deep circuit-board teal paper background (#0F3D3E), warm parchment paper
> for figures and linework (#EDE6D6), and a single copper paper accent (#C8743A) used
> sparingly, with small touches of cyan (#4FB3BF). Generous negative space, calm
> composition, no text, no words, no logos.

For a **prop** (to be cut out), swap the background clause for "Isolated object centered on
a plain flat light background, nothing else." and run `images_remove_background` on the
result. Model `gpt-2` (85 credits), style anchor from §4. `simulate_cost` first for a batch.

## 3. The show mark (2026-11-27)

An open vintage car hood revealing a paper engine of parchment gears, a glowing copper
microchip at its heart: "under the hood" made literal. Take 3 of a 4-take proof (the
cleanest silhouette at thumbnail size); takes 1, 2 and 4 are in Magnific if Dave prefers one.

| Asset | Where |
|---|---|
| Transparent cutout (engine) | `remotion/public/papercraft-uth/mark_uth.png` (RGBA 1024²) |
| Transparent cutout (this guide) | [`mark/uth_mark.png`](mark/uth_mark.png) |
| Source render (on teal) | [`mark/uth_mark_source.png`](mark/uth_mark_source.png), thumbnail-ready |
| Generation record | [`mark/provenance.json`](mark/provenance.json) |

## 4. Style anchors

The mark source render (Magnific creation `xSI3b52jfW`) is the world's canonical style
reference, for per-episode art and the YouTube thumbnail illustration.

## 5. The library (`remotion/public/papercraft-uth/`, provenance in its `provenance.json`)

- **Sets** (1344×752): `set_engine_room` (interlocking gears and copper pipes),
  `set_circuit_board` (traces running to a chip on the horizon), `set_server_aisle` (racks with
  cyan lights), `set_workbench` (an opened machine, parts laid out, copper lamp).
- **Props** (transparent, 1024²; Cvg key `size`): `prop_gear`, `prop_chip`,
  `prop_magnifier`, `prop_nodes` (a small neural network), `prop_papers` (research papers,
  copper clip), `prop_tools` (wrench and screwdriver).
