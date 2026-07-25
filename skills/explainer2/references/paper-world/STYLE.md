# Paper-world illustration style — LOCKED (2026-07-14)

The durable, reproducible spec for the layered cut-paper illustration look used in the
**nemock-deep-dive** paper channel (Dave Saunders' deep dives, davesaunders.net) — and
specifically the **"AI grinds, humans decide" explainer series** (see
[channel/series_ai-augments-human_2026-07-14.md](../../../channel/series_ai-augments-human_2026-07-14.md)).

**Why this file exists (operator directive 2026-07-14):** so the look and the character
designs are NEVER lost across sessions. Any future session can reproduce the exact
aesthetic from the recipe below, and reuse the exact cast via the Magnific library ids or
the local reference PNGs. This is the source of truth; the Magnific library is the
convenience mirror.

Generated via the optional Magnific image-gen capability
([docs/magnific-imagegen-plan.md](../../../docs/magnific-imagegen-plan.md)); in-video use is
**stylized-only** and disclosed honestly (`ai_generated_visuals: true`, `synthetic: false`).

---

## 1. The palette (strict — matches the `nemock-deep-dive` theme in `src/explainer2/themes.py`)

| Role | Hex | Use |
|---|---|---|
| Cream paper background | `#f4ecd6` | the base sheet everything sits on |
| Navy ink | `#2c1e4e` | figures, linework, clothing, primary shapes |
| Green accent | `#3ddc84` | ONE accent, used sparingly (a mug, a note, a cuff, a pin) |
| Warm mid tones | tan/kraft paper | skin, secondary paper (kraft cream, one step darker than bg) |

## 2. Model + settings

- **Model:** `gpt-2` (15 credits / image; renders clean layered paper). Fallback
  `imagen-nano-banana-2` only if likeness/quality slips (75 cr).
- **Aspect:** `16:9` for full scenes/backgrounds; `2:3` (portrait) for standalone character
  references; character cutouts get `images_remove_background` after generation.
- Always run `simulate_cost` (free) before a paid call.

## 3. The canonical PROMPT RECIPE (copy verbatim, fill `{SUBJECT}` / `{SETTING}`)

> Layered cut-paper collage illustration, handmade papercraft style with visibly torn and
> cleanly-cut paper edges and soft drop shadows between stacked paper layers. Subject:
> {SUBJECT}. {SETTING}. Editorial explainer / storybook aesthetic, flat and clean. Color
> palette strictly: warm cream paper background (#f4ecd6), deep navy-ink paper for figures
> and linework (#2c1e4e), and a single bright green paper accent (#3ddc84) used sparingly.
> Generous negative space, calm composition, no text, no words, no logos.

- For a **clean character reference:** `{SUBJECT}` = the person + wardrobe + expression +
  "shown from the knees up, centered, facing forward"; `{SETTING}` = "Plain empty warm
  cream paper background, no desk."
- For a **scene:** `{SETTING}` describes the environment (cubicle, office, desk).
- Keep the "no text, no words, no logos" clause — the deck engine adds all typography.

## 4. Keeping characters CONSISTENT (two mechanisms, both durable)

1. **Magnific library characters (native).** Pass the character as a reference in
   `images_generate`: `references: [{type: "character", identifier: "<numeric id>"}]`.
   Same person, new pose/scene.
2. **Style continuity across DIFFERENT people.** Pass a canonical scene as a *style*
   reference: `references: [{type: "style", identifier: "<creation id or re-upload>"}]`.
   Carries the paper aesthetic without copying identity. (The cast below was generated this
   way off the rookie proof.)
3. **Cold-start (no library access):** re-upload a local cast PNG (`creations_upload_image`
   / `creations_request_upload`) and use it as an `image`/`style` reference, or just run the
   recipe in §3 fresh — it reproduces the look on its own.

## 5. The cast roster (LOCKED 2026-07-14)

Local reference PNGs live in [`cast/`](cast/) beside this file. Magnific library ids are in
Dave's account (durable).

| Character | Role | Magnific library id | identifier | Local ref |
|---|---|---|---|---|
| The rookie | new support agent, headset | `2056390` | `s4wmGl8e2G` | `cast/rookie_scene.png` |
| The veteran | experienced support agent, grey hair + glasses | `2056396` | `ea89jdqL9P` | `cast/veteran.png` |
| The customer | frustrated caller, green bag | `2056397` | `5SxeAKxeWO` | `cast/customer.png` |
| The writer | bearded knowledge worker, notebook + green pen (#46) | `2056398` | `dfINlXSLvM` | `cast/writer.png` |
| The coder | developer in a hoodie + glasses, paper laptop w/ green code (#47) | `2085587` | `hbK4tvqLJl` | `cast/coder.png` |

To ADD a cast member: generate with the §3 recipe + a §4 style reference, review, then
`library_create {type:"character", images:[{creationIdentifier}]}`, save the PNG to `cast/`,
and add a row here.

## 6. Props & motifs (same recipe, `{SUBJECT}` = the object, transparent cutout)

Recurring paper props for this series (generate per-project into
`<project>/assets/imagegen/`, remove background for overlays): a growing **stack of support
tickets/paper slips**; the **AI "machine of gears"** (a friendly paper contraption of
interlocking cogs) as AI's lane; a **blank sheet of paper** + a rising **green quality
meter**; a **paper "source card"/citation clipping** (pairs with the Remotion KeepCard slide).

## 7. Provenance & disclosure

Every in-video generation is fetched with `tools/imagegen.py fetch … --project <dir>
--in-video`, which appends to `<project>/assets/imagegen/provenance.json`. At packaging,
`tools/imagegen.py disclosure --project <dir>` → in-video stylized art means
`ai_generated_visuals: true`, `synthetic: false`, YouTube altered-content answer **No**
(non-deceptive, non-photoreal). See the plan doc's AI-disclosure policy.
