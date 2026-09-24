# RRP paper-world style — the Robot Roundup show mark (2026-09-18)

The Magnific-papercraft look for **Robot Roundup** (`robot-roundup-wednesday`), which took
the Wednesday booth slot from Who Signs The Check on 2026-09-18
(`make_money/routine_changes/2026-09-18-youtube-channel-analysis-and-cuts.md`).

**This is NOT a full per-show world yet.** It is a show mark plus a borrowing policy. The
show renders on the existing **`wsc-goldenrod`** theme key and draws its sets and props from
the libraries listed in §3. Read that before authoring a deck.

Shared doctrine — model settings, substrate neutrality (NEVER regenerate substrates), chibi
staging, provenance/disclosure — is identical to
[`../paper-world-fwf/STYLE.md`](../paper-world-fwf/STYLE.md) §2/§6 and is not repeated.

## 1. The palette (strict — the Wednesday slot's locked goldenrod)

| Role | Hex | Use |
|---|---|---|
| Goldenrod paper background | `#F2C94C` | the ground |
| Deep ledger-green paper | `#1F3D2E` | figures, machines, linework |
| Copper accent | `#A4551E` | ONE accent (a joint, a seal, a nib), sparingly |

Goldenrod is a hand-me-down, not a design choice: it is the Wednesday hue in the locked
feed grid (tangerine Mon, steel-blue Tue, goldenrod Wed, indigo Thu, brick-red Fri) and the
slot changed shows, not colors. It reads as industrial caution yellow, which suits a
robotics show better than the accident deserves.

**A dedicated Robot Roundup palette is open follow-up work.** It needs its own papercraft
ink tokens and a Magnific substrate set before anything renders on it, per the warning in
`src/explainer2/themes.py`. Do not invent a new theme key and render on it.

## 2. The canonical PROMPT RECIPE (copy verbatim, fill `{SUBJECT}` / `{SETTING}`)

Identical to the goldenrod world's, because it is the goldenrod world:

> Layered cut-paper collage illustration, handmade papercraft style with visibly torn and
> cleanly-cut paper edges and soft drop shadows between stacked paper layers. Subject:
> {SUBJECT}. {SETTING}. Editorial explainer / storybook aesthetic, flat and clean. Color
> palette strictly: goldenrod-yellow paper background (#F2C94C), deep ledger-green paper
> for figures and linework (#1F3D2E), and a single copper paper accent (#A4551E) used
> sparingly. Generous negative space, calm composition, no text, no words, no writing,
> no signatures, no numbers, no logos.

Model `gpt-2`, style anchor from §4. Always `simulate_cost` first (free).

**Keep the extended no-writing clause.** Machine subjects invite rendered control panels,
badges, dials and maker logos, which are the same failure mode money subjects have with
text. The engine adds all typography.

## 3. Sets and props — BORROWED, and that is deliberate

Robot Roundup has no set or prop library of its own. Until it earns one:

| need | take it from | why |
|---|---|---|
| machines, instruments | `papercraft-mmt/props/` — `prop_robot_arm.png`, `prop_monitor_pulse.png`, `prop_microscope.png` | the closest existing art to this show's subject matter |
| rooms, desks, corridors | `papercraft-wsc/sets/` | same goldenrod ground, so they composite without seams |

Per-episode one-off art follows §2 with the §4 anchor. Do NOT regenerate a borrowed asset
into this library just to rename it.

## 4. Style anchors

The mark source render (creation `p8FnZ4Jehw`) is this show's anchor. It was itself
style-anchored to `8ahgUPJIrU`, the WSC mark source render and the goldenrod world's
canonical reference, so the whole Wednesday family stays coherent.

Pass it as `references: [{type: "style", identifier: "p8FnZ4Jehw"}]`. Cold-start: re-upload
[`mark/rrp_arm_mark_source.png`](mark/rrp_arm_mark_source.png) as a style reference, or run
§2 fresh.

## 5. The show mark (LOCKED 2026-09-18)

A single articulated paper robot arm in profile: three ledger-green segments, two copper
pivot joints, a wide open two-finger gripper, on a round stacked base.

Chosen by the operator from a 4-take proof (take 3) on **legibility at mark size**, which is
the only test that matters for a mark. Its gripper is the widest of the four, so the
silhouette still reads at ~96px on the CTA card where a tighter claw closes into a blob.

| Asset | Where |
|---|---|
| Runtime (what decks reference) | `remotion/public/papercraft-rrp/mark_rrp.png` (RGBA 1024²) |
| Transparent cutout | [`mark/rrp_arm_mark.png`](mark/rrp_arm_mark.png) |
| Source render (on goldenrod) | [`mark/rrp_arm_mark_source.png`](mark/rrp_arm_mark_source.png) — thumbnail-ready, and the §4 anchor |
| Generation record | [`mark/provenance.json`](mark/provenance.json) |

In a deck the CTA slide carries it as `"mark": "papercraft-rrp/mark_rrp.png"`.
