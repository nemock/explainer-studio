# Papercraft Motion — design spec (v1, 2026-07-25)

The next generation of the deep-dive visual language: the approved BRG/FWF
**papercraft** still style (cut-paper dioramas, layered sheets, real shadows,
sculptural objects) brought into the Remotion motion engine with enough
dynamism to match Dave's delivery. Companion to `motion-playbook.md` (which
stays the procedural brain); this file is the *design canon* for the
papercraft world. Source canon for the still style:
`brgweb/brand-assets/papercraft/manifest.json`,
`make_money/brand_kits/FWF/papercraft/README.md`,
`make_money/routine_changes/2026-07-23-brg-papercraft-asset-library.md`.

Dave's brief, verbatim: "the next generation of really visually dynamic,
popping stuff" that carries as much character as the voiceovers do.

---

## 0. The one big shift: from *page* to *table*

The current paper theme is a **page**: dark ink text on a flat cream field.
The approved brand identity is a **table**: a deep ink-purple ground with
layered paper sheets on it, and cream sculptural paper objects standing on
top, photographed with soft studio light and real drop shadows.

Papercraft Motion adopts the table. Every scene is a miniature set built on
the dark ground; content lives on **cream paper objects** (cards, chips,
props) that are *placed, popped up, unfolded, or torn away* by an unseen
hand. Text never floats in space — text is always printed on a piece of
paper that physically exists in the set.

Why this matters beyond fidelity to the stills:
- Shadows only read against a dark ground; shadow is half the craft.
- Cream-card-on-ink is higher contrast than ink-on-cream (legibility win).
- A dark surround lets **light act as a character** (§6).
- It visually rhymes with baserealitygroup.com and the davesaunders.net
  storefront, so the whole brand shares one language.

## 1. World tokens (per-channel; isolation holds)

One component set, parameterized by a **world token file**
(`remotion/src/brands/papercraft.ts`), selected by theme — never global:

| token | FWF / davesaunders (`nemock-deep-dive`) | BRG (future BRG-branded series) |
|---|---|---|
| `ground` | ink `#2A1142` | navy `#1B2B4B` |
| `groundDeep` | `#1D0B30` (vignette edge) | `#12203A` |
| `sheet` | plum `#36185B` | navy-2 `#24365C` |
| `sheetAlt` | violet `#5A3494` | teal-deep `#0A5A5E` |
| `paper` | cream `#FAF6EF` | cream `#F5F0EB` |
| `paperShade` | `#E9E0D2` (object side/fold shading) | `#E5DCCE` |
| `ink` | `#2A1142` (text on cream) | `#1B2B4B` |
| `accent` | violet `#5A3494` | teal `#0D7377` |
| `accentSoft` | lilac `#C7B6E6` | teal-soft `#7FC9C4` |
| `shadow` | `rgba(15,5,30,.45)` | `rgba(6,14,30,.45)` |

Rules carried over from the still canon, now binding on motion:
- **Strict palette.** Nothing outside the token set. NOTE: this retires the
  green `#3ddc84` accent inside the deep-dive world (captions' active word,
  kickers → `accentSoft` lilac). Flagged as a deliberate brand decision —
  the FWF palette has no green; one language everywhere.
- **No photorealism, no humans, no text inside generated art** (real product
  covers may carry their real title). Headlines/labels are composited by the
  engine on cream cards, never baked into Magnific stills.
- ISO/midnight series and Cut & Bond keep their own identities untouched.
  `nemock-deep-dive` is the first theme to get Papercraft Motion.

## 2. Depth system — four named planes + one camera

Every papercraft scene is composed of up to four planes, front to back:

| plane | name | contents | parallax factor |
|---|---|---|---|
| P0 | **table** | ink ground, vignette, 2–3 big torn/cut paper sheets | 0.15 |
| P1 | **set** | Magnific diorama backdrop or large sculptural props | 0.45 |
| P2 | **stage** | the active content: cards, counters, stairs, props | 1.0 |
| P3 | **float** | pinned annotations, marks, callout tags, film grain | 1.25 |

One shared **scene camera** `{x, y, zoom}`. Every plane renders inside a
transform of `translate(cam * factor) scale(1 + (zoom-1) * factor)`, so a
camera move produces true parallax: foreground slides past background. The
AnnotateOverlay rides P3 — marks are *pinned to the paper* and move with it.

**Camera grammar (percussive, not floaty):**
- The camera moves in **steps, on narration cues** — a 12–18 frame
  spring-settled move, then a dead-still hold. Never a continuous drift.
- One push-in (zoom 1.0 → 1.06–1.12) per scene maximum, on the scene's key
  beat; one lateral step per additional cue. Big moves (act transitions) are
  handled by the tear transition (§4), not the camera.
- **HARD RULE — paper never floats.** No ambient sine bob, no breathing, no
  idle sway (operator vetoed 2026-07-16: nauseating). Stillness between
  events is a feature: this is stop-motion, and stop-motion holds are still.
  QA's dead-air warning on held papercraft frames is accepted by design.

## 3. Entrance & exit vocabulary (paper physics)

All springs; all frame-driven; all deterministic. House timing: **snap and
settle** — damping 12–14, stiffness 170–220 (punchy), never ease-in-ease-out
symmetric. Entrances land ON the narration cue frame (the sync system already
resolves cue phrases → frames; anticipate by 2 frames so the settle peaks
with the spoken word).

| name | motion | shadow behavior | use for |
|---|---|---|---|
| **place** | drops from 1.06 scale + slight above, 1-frame overshoot, settles | shadow fades in 3–4 frames AFTER the object lands (the unseen hand) | default for cards, props, counters |
| **popup** | hinges up from the table: rotateX 85°→0 with perspective origin at the base edge | shadow grows from a line to full as it rises | keep-cards, compare panels, stairs steps |
| **unfold** | two-panel fold opens (clip + mid-fold shade sweep), 2 steps | soft shade in the fold that brightens | wide cards, maps, timelines |
| **slide-under** | enters masked from beneath a nearer plane/prop | pre-shadowed | secondary elements, list items |
| **flick** | 2-frame scale hit 1.00→1.045→1.00 | shadow blinks darker 1 frame | beat accents on already-present elements (punch words, counter landings) |
| **peel** (exit) | a corner lifts (slight rotate + curl shadow), then the sheet slides off-frame | shadow stretches then vanishes | element exits mid-scene |
| **tear** (transition) | §4 | — | scene/act boundaries |

Budget: ≤ 2 vocabulary words per scene + flicks on cues. The craft reads
because each move is singular and physical, not because everything moves.

## 4. Transitions

- **Cut with a place** (default): next scene's stage content places in on
  its first cue. Between-scene cross-fade drops from 7 frames to 4 — cuts,
  not dissolves, carry percussive energy.
- **Tear** (act boundaries / hard topic pivots, ≤ 3 per deep dive): the
  entire frame tears along a deterministic rough edge (seeded SVG path);
  the two halves part (with paper-thickness edge + shadow) revealing the
  next scene already set. 10–14 frames, loud.
- **Sheet wipe** (light pivot): a plum sheet slides across P2, drops the old
  content off with it, the new content places on top. 12 frames.
- **Camera hand-off** (within a schematic/tour): no transition — the camera
  steps, per §2.

## 5. Percussive editing — the beat contract

The visuals hit WITH the voice. Mechanically:
1. Deck authors mark `cue` phrases exactly as today (verbatim words from the
   segment). The engine resolves them to frames (existing sync pass).
2. Every papercraft component treats its cues as **beats**: entrances,
   camera steps, counter landings, spotlight snaps all quantize to beats.
3. Between beats: stillness (holds). The energy comes from the contrast.
4. Punch lines (deck `punch`/`accent` beats) get a **flick + spotlight snap**
   on the cue frame — the paper punches when Dave punches.

## 6. Light as a character

Implemented as two cheap, deterministic layers (no WebGL):
- **Key light**: a radial gradient overlay on the whole set whose center,
  radius, and strength are scene-typed. Wide & soft for talking/list beats;
  tightens (radius −35%, surround −20% brightness) for stat landings and
  midroll punches — the **spotlight snap**, 6 frames, on cue.
- **Shadow direction**: all object shadows share one global light angle per
  scene (default upper-left, matching the still library). Mood shifts
  (a "bad" beat, the drift story) may flip the angle or deepen `shadow`
  alpha by 30% for that scene — set per-slide via `mood: "hard"`.

## 7. Scene-type translations (what replaces what)

| beat (deck type) | today | Papercraft Motion |
|---|---|---|
| hook / cold open | PaperHook (flat full-bleed + label) | **PaperSet hook**: multi-plane set (Magnific backdrop P1 + hero prop P2), camera push-in on the promise cue, headline card *places* with settle |
| statement / punch | KineticHeadline / PunchWord on flat field | cream **punch card** places hard; spotlight snap; flick on the accent word; JAMMED-style words emboss (inner shadow) |
| stat | StatCounter (flat number) | **PaperCounter**: the number as a stack of cream paper chips that slap down chip-by-chip and land on the cue; label on a small placed tag |
| trend / chart | DrawLine (glowing SVG line) | **PaperStairs**: bars as a physical paper staircase, steps *popup* in sequence; a lilac paper marker climbs (or tumbles down, for crashes); camera steps with it |
| steps / flow | StepFlow (flat pills + arrows) | popup cards along a paper path on the table; camera lateral-steps per stage |
| schematic | flat cards + drawn edges | raised cream node cards, edges = violet paper strips that *extend* from node to node; existing camera logic kept |
| compare | SideBySide (two flat panels) | two paper trays popup left/right; the "bad" tray sits in harder shadow (§6 mood) |
| keep-card / figure | KeepCard, Figure (flat framed image) | same cards, but *popup* entrance onto the table world, true shadow, one camera step closer on the label cue |
| define | DefineTerm on flat field | term on a big cream tag (*place*), definition unfolds beneath (*unfold*) |
| midroll punch | PunchWord | punch card + **spotlight snap** + flick; table darkens |
| CTA | CTA (book cover float) | the papercraft book (cover-matched hero recipe) stands on the set; headline card places beside it |
| sting | PaperSting (kept) | kept as-is — already on-language (paper D + rocket) |

Captions: unchanged mechanically (cream pill, ink text) — they read as a
paper strip on the dark ground; active-word accent moves green → lilac.

## 8. Set pieces (Magnific) — generation contract

- Backdrops (P1) and hero props are generated with the **locked style
  recipe**: style suffix from the canon + `type:"style"` reference to an
  existing set member (FWF: `davesaunders-hero-a.jpg`; BRG: any manifest
  member). FWF prompts add "no teal, no blue".
- **Backdrops**: one wide diorama per video (the video's visual theme —
  same role the PaperHook illustration plays today), composed with a low
  center-stage so engine-composited cards sit in the middle third. Generated
  16:9 at the video aspect.
- **Props**: generated as single objects on the plain ink ground, then
  `images_remove_background` → transparent PNGs for P1/P2 layering.
- Every asset lands in the project's `assets/imagegen/` with provenance via
  `tools/imagegen.py fetch` (existing practice), then is staged to the
  render public dir by the engine like all deck images. Stills are locked
  at generation time — deterministic renders hold.
- Reusable set dressing (generic sheets, desk props, the book) lives in
  `remotion/public/papercraft/` as brand assets, tracked in git, so a video
  needs only 1–3 fresh generations (~15–45 credits at GPT-2 rates).

## 9. Performance & determinism guardrails

- Planes are flat PNGs/JPGs with texture and shadows **baked by Magnific**;
  runtime adds only transforms, cheap CSS drop-shadows on small elements,
  and gradient light layers. No SVG turbulence over large areas (the
  per-frame grain experiment bloated files 50% and was reverted).
- All motion is a pure function of `frame` (springs + interpolate). No
  Date.now, no unseeded randomness; torn edges use seeded paths.
- The record-review loop is untouched: narration → align → render exactly as
  today; the deck just names different components/fields.

## 10. Authoring surface (deck.json)

Existing slide types keep working (they render with papercraft entrances on
the papercraft theme). New/extended fields:

```jsonc
{
  "id": "s01", "type": "hook",
  "set": "assets/imagegen/desk_wide.png",      // P1 backdrop (optional)
  "props": [{"image": "assets/imagegen/compass.png", "at": [0.72, 0.55], "w": 0.2, "plane": 2}],
  "camera": [{"to": {"x": 0.5, "y": 0.45, "zoom": 1.08}, "cue": "three jobs"}],
  "mood": "hard",                                // optional light state
  "kicker": "...", "headline": "...", "accent": ["..."]
}
// new types: "papercounter" {value,label,cues}, "paperstairs" {points,end_label,kind}
```

Per-video authoring cost after migration: unchanged deck flow + one backdrop
generation (+ optional 1–2 props) ≈ 5 minutes of Magnific wait, batched at
deck time. No new manual steps for Dave.
