# Thumbnail Playbook — the on-brand YouTube thumbnail (1280×720)

Follow as a procedure. Thumbnails are built at the **Package** step (SKILL §8).
A thumbnail is an HTML card rendered headlessly to PNG — **author the HTML/CSS,
never hand-paint a PNG** — so the look is deterministic and reproducible. This
file freezes the quality bar so any model reproduces it without guessing.

The output goes in `<project>/package/thumbnails/`: `thumb_a.{html,png}` and
`thumb_b.{html,png}` (a = the live thumbnail, b = a promo asset for social and the
newsletter; A/B testing retired, see §6), each pointing
at a cutout `headshot-a.png` / `headshot-b.png`.

---

## 0. What "good" looks like (the contract)

The proven look (this is the reference — match it): a **dark, cool navy radial
gradient** that is lighter right behind the operator and falls to near-black at
the frame edges; the operator **cut out, large, anchored bottom-right**, with a
soft drop-shadow separating him and the bottom edge **faded out**; a **2-line
keyword headline in red bands** top-left; a **white sub-line with the payoff
words accented in green**. Readable at 120 px wide. No clutter, ≤ ~6 words in the
headline, one idea.

## 1. The cutout (selfie → transparent PNG)

The operator appears as a transparent-PNG cutout. Two valid sources:

- **Operator supplies a transparent PNG** (preferred when they've already keyed
  it). Verify it's RGBA with real alpha. Phone tools (Photoshop Express) leave a
  faint light **fringe** at hair/shoulder edges — clean it (below).
- **Operator supplies a light-background selfie (jpg).** Run the local segmenter:
  `python tools/cutout.py <in.jpg> <out.png>` (rembg / U2-Net, on-device, no
  cloud). It keys the *person* out regardless of background colour — a clean,
  uniform backdrop (even a flat fill) gives the cleanest mask.

Then **de-fringe + soften** for compositing:
`python tools/clean_matte.py <in.png> <out.png> --threshold 110 --erode 2 --feather 2`
- `threshold` drops low-confidence (background-contaminated) edge pixels.
- `erode` shaves the contaminated rim. **For thin props (calipers, a pen, a phone
  held up) use `--erode 0` (or 1) at full resolution** so the prop isn't thinned.
- `feather` softens the edge so it reads soft at thumbnail scale, not knife-cut.
Keep the cutout **full-resolution**; the template scales it down crisply at 2×.

## 2. The brand template (canonical — copy this, change only the copy + cutout)

```html
<!doctype html><html><head><meta charset="utf-8"><style>
  * { margin:0; box-sizing:border-box; }
  body { width:1280px; height:720px; overflow:hidden; position:relative;
    background:radial-gradient(135% 120% at 74% 42%, #1a2750 0%, #0d1428 58%, #090d1c 100%);
    font-family:-apple-system,"Helvetica Neue",Arial,sans-serif; }
  .facewrap { position:absolute; right:-90px; bottom:0; height:660px;
    -webkit-mask-image:linear-gradient(to top, transparent 0%, black 16%);
    mask-image:linear-gradient(to top, transparent 0%, black 16%); }
  .face { height:100%; filter:drop-shadow(0 0 44px rgba(0,0,0,.5)); }
  .text { position:absolute; left:56px; top:104px; z-index:2; width:760px; }
  .band { display:inline-block; background:#ff4d4d; color:#fff; font-size:104px; font-weight:900;
    letter-spacing:-.02em; padding:8px 26px; border-radius:14px; line-height:1.04;
    box-shadow:0 16px 60px rgba(255,77,77,.4); }
  .band.b2 { margin-top:14px; }
  .sub { margin-top:42px; font-size:50px; font-weight:900; color:#f5f7ff; line-height:1.2;
    text-shadow:0 3px 18px rgba(0,0,0,.7); }
  .sub span { color:#3ddc84; }
</style></head><body>
  <div class="facewrap"><img class="face" src="headshot-a.png"></div>
  <div class="text">
    <div class="band">KEYWORD</div><br>
    <div class="band b2">SECOND LINE</div>
    <div class="sub">supporting line, <span>payoff words green</span></div>
  </div>
</body></html>
```

**Brand constants — do NOT change** (these are the channel signature): the red
band `#ff4d4d`, the green accent `#3ddc84`, white sub, 900-weight, the radial-
gradient *structure* (lighter hotspot behind the subject at ~`74% 42%`, falling
to near-black edges), the face `drop-shadow`, the bottom mask-fade, and the
left/top text block. **Adjustable per video:** the copy, which cutout, the
headline size if a word overflows, and — only under the rule in §5 — the
gradient's *inner hue*.

## 2c. The illustrative / composed path — NOW THE STANDARD (operator directive, hardened 2026-06-29)

**This is the default to hit every video, not an occasional treatment.** On
2026-06-29 the operator named the three strongest thumbnails the channel has made
and set them as the quality bar to *maintain consistently*:

- **#35 P.T. Barnum** — Dave in a tux, Barnum in the scene, old-timey center type.
- **#15 the $1-salary myth** — composed split, hero headline.
- **#20 Ford** — Dave-as-veteran + a robot in the cubicle, "350 HIRED BACK" + a red RECALLED stamp.

His words: these "look creative… far more dynamic," and are "approaching the kind
of thumbnail creativity" MrBeast-tier designers make. The old plain cutout
thumbnails "weren't bad," but the results show we can do better — so **up our game
and hold this level every time.** Do NOT quietly regress to the bare
cutout-on-navy template to save effort.

So the two paths are now ranked, not equal:

- **(a) The illustrative / composed thumbnail — the DEFAULT.** A real *scene with
  Dave in it*, era/topic-appropriate styling, a strong central brand headline, a
  story readable in one glance (a stamp, struck words, a clear visual contrast),
  text kept off Dave's face. Aim here first for every video.
- **(b) The cutout template** (§2 above) — the **fallback**, when a topic genuinely
  can't carry a scene. If you fall back to it, say why.

**The recipe that worked in all three:** a scene (not a floating cutout) + Dave in
it + topic-appropriate type + one bold headline with brand accents + a single
glanceable story device + face kept clear of text.

**The foil rule (operator-confirmed 2026-06-29).** The strongest two (#20 Ford,
#35 Barnum) both put a **second character in the scene with Dave** — the robot,
P.T. Barnum — not just Dave against a backdrop. When a topic has a natural *foil*
(a person, a machine, an object that embodies the tension), that two-character
scene is the richest base, and it's what to reach for first. So when proposing
concepts, actively look for the foil: who or what is on the *other side* of this
video's argument, and can Dave share the frame with it? Default the lead concept
to a Dave-plus-foil scene whenever the topic offers one; a solo-Dave scene is the
next best, and the plain cutout is the fallback.

**Workflow for path (b) — a tag-team:**
1. **Propose 2-3 concepts first.** For each video, before anything is generated,
   give the operator 2-3 thumbnail CONCEPT ideas: the scene, who/what is in it,
   the headline words, the font feel (era/topic-appropriate where it fits), and
   any logos/icons/pictures to graft in. The operator reacts and picks.
2. **The base image gets generated.** ⚠️ **SUPERSEDED as the default 2026-08-04 — go to
   §2d.** Claude now generates the base itself via Magnific on every video, and has done
   for over a month. The historical operator route below (Gemini "nano banana" or ChatGPT,
   used on Barnum, operator drops the result into `package/thumbnails/`) remains valid ONLY
   as a fallback when the Magnific MCP is unreachable.

   The old wording here said flatly "Claude does not generate the base scene." Read cold,
   after a restart, that sentence stops the package dead. It is what broke #54. If you find
   yourself concluding you cannot build a thumbnail, you have read this step instead of §2d.
3. **Claude composes on top of the base image:** add the brand headline (red
   bands / green accent, or an era-appropriate type treatment when the concept
   calls for it), and **graft in logos, icons, or small pictures** to make it
   informative and clickable. Same HTML-card → `html2png.py` mechanic as §2/§6,
   just over the operator's base image instead of the navy gradient. Keep it
   legible at 120px (§0 contract still holds).
4. **Still produce two** (§6) — a = live, b = promo reuse. Not a test pair.

When in doubt, ask the operator which path a given video should take; lean toward
the illustrative path for story-driven / special-edition deep dives.

## 2d. THE DEFAULT: Claude generates the base with Magnific image-gen

**Promoted from "optional" to the standard path 2026-08-04.** This has been the actual
workflow for well over a month and every recent video used it. The section previously read
"an optional capability… it is never required… fall back to the operator generating the
base," which is how a cold session (post-restart, no conversation history) concluded that
the operator supplies the base and that the package therefore could not be finished. That
happened on #54 and cost a wrong upload order. Do not re-demote this section.

**Claude builds the thumbnail end to end.** Concept → pick a selfie from `dave_selfies/` →
Magnific → bring the base down → overlay the headline in `thumb_*.html` → screenshot to PNG.
The operator does not paste prompts into an external tool and does not hand over a base.

Two ways to fix the likeness, and **the wardrobe decides which**:

- **Selfie-as-base (preferred, and required whenever wardrobe matters).** Upload a
  `dave_selfies/*_clean.png` and pass it as `references:[{type:"image", identifier}]`, with
  a prompt that says *"use the reference for the man's face AND his wardrobe."* Sequence:
  `creations_request_upload {mimeType:"image/png"}` → `python3 tools/imagegen.py put <selfie>
  "<proxyUploadUrl>"` → `creations_finalize_upload {path}` → `images_generate`.
- **Library character `self` (id 2046066)** fixes the face with no upload, but **defaults him
  into a polo shirt**, which is the wrong look (see below). Use it only when the outfit is
  irrelevant to the shot.

**Wardrobe rule (operator, 2026-08-04): sweatshirt or hoodie, never a polo.** A casual polo
"makes me look a little bit old, a little stuffy." Reference selfies:
`dave_cream_shirt_1_clean.png`, `dave_cream_shirt_2_clean.png`, or the `dave_*_hoodie_*` set.

Fallback only if the Magnific MCP is genuinely absent (tools not resolvable via ToolSearch):
the §2c operator-generated route still works. Full flow + guardrails:
[docs/magnific-imagegen-plan.md](../../../docs/magnific-imagegen-plan.md).

- **Model = `gpt-2` (GPT 2), the default** — best composition/likeness at **15 credits**
  per 16:9 image; validated to beat Nano Banana Pro (`imagen-nano-banana-2`, 75 credits)
  for our bases. Reserve Nano Banana Pro as a fallback only when GPT 2's likeness slips.
  Photoreal thumbnail bases ARE allowed (this is a thumbnail, not in-video; see the
  disclosure note in the plan doc).
- **Operator directive 2026-07-24 (#47): for a PHOTOREAL Dave thumbnail, Claude generating
  the base via Magnific is now the GO-TO** — generate a few 16:9 variations, pick an
  acceptable one (show the operator; he'll flag any bad likeness), then superimpose the
  headline. No longer wait on the operator to paste prompts into an external tool for these.
- **Standing photoreal-Dave reference = the library character `self` (id 2046066)** — a
  persistent Magnific character (salt-and-pepper beard, receding hairline). Pass
  `references:[{type:"character", identifier:"2046066"}]`; NO per-video selfie upload needed.
  (The `dave_selfies/*.png` upload flow below still works as a fallback / for a specific outfit.)
- **Model for photoreal likeness = Nano Banana 2 (`imagen-nano-banana-2-flash`)** — strong
  character consistency + photoreal (used #47, 2026-07-24: 4 variations, ~75cr each, likeness
  held). `gpt-2` remains the default for STYLIZED/infographic bases; reach for Nano Banana when
  the target is a photoreal scene with Dave in it. Put Dave on the RIGHT with a darker/cleaner
  LEFT third for the headline; a legibility `.scrim` behind the text covers any busy base.
- **Selfie-as-base** (fallback / specific outfit): upload a `dave_selfies/*.png`,
  then reference it. Sequence: `creations_request_upload {mimeType:"image/png"}` →
  `python3 tools/imagegen.py put <selfie> "<proxyUploadUrl>"` →
  `creations_finalize_upload {path}` (→ creation id) → `images_generate {prompt,
  mode:"gpt-2", aspectRatio:"16:9", count:1, references:[{type:"image", identifier:<id>}]}`
  → `creations_wait` → `python3 tools/imagegen.py fetch "<url>" <base.png> --project <dir>
  --model gpt-2 --prompt "…"`. A single reference holds the likeness well.
- **Wardrobe rule (operator directive 2026-07-14):** default to the **hoodie /
  no-hoodie sweatshirt motif** — Dave's recognizable brand; it makes him stand out from
  the scene. Restyle thematically only when the topic clearly earns it (the P.T. Barnum
  tux, #35). Keep Dave recognizable regardless.
- **Cost hygiene:** `simulate_cost {tool:"images_generate", arguments:{…}}` (free) before
  generating. (The operator's plan has large credit headroom, but keep the habit.)
- Then compose the brand headline on top exactly as §2c step 3 — the generated base
  replaces the operator-supplied `base.png`; everything downstream is unchanged. Both
  thumbnails still get built (§6): a = live, b = promo reuse.

## 3. Copy rules

- Headline = the blueprint's **§7 thumbnail direction** distilled to a **2–4 word
  keyword line, ≤ 2 lines** in red bands. It restates the title's promise, it
  does not repeat the full title. Spell punchy: "MEASURE / ANYTHING", "FIRST /
  10 CUSTOMERS".
- Sub-line = one short clause; accent the **payoff words in green** (`<span>`).
- Headline and the title must promise the same thing.
- If a word is too long for one band, drop `font-size` to 92–96 px; never wrap a
  word.

## 4. Cutout placement

Right side, `bottom:0`, ~`660px` tall, `right:-90px` (bleeds off the right edge),
bottom 16 % faded. The face/expression and any held prop should sit in the upper
two-thirds (the bottom fades). Pick the cutout whose gesture reads at small size.

## 5. Outfit-vs-background rule (when the operator blends in)

The template already separates the subject three ways — the **drop-shadow glow**,
the **lighter navy hotspot behind him**, and the **bottom fade** — so most outfits
read fine (a mid/cool navy shirt still separates). But when the operator's
**dominant garment is dark navy/black/charcoal** it can merge with the navy bg.
Diagnose by rendering once and looking; if the torso dissolves, separate it —
**in this order, stopping at the first that works**:

1. **Strengthen the existing separation** (cheapest, fully on-brand): raise the
   drop-shadow to `drop-shadow(0 0 60px rgba(0,0,0,.65))`, and/or lift the inner
   gradient stop slightly brighter (e.g. `#22305f`) so the hotspot behind him
   reads more.
2. **Shift the inner gradient HUE within the brand range** (still on-brand): keep
   the gradient structure, the outer stops (`#0d1428` → `#090d1c`), and the red/
   green copy colours fixed — change only the **inner hotspot colour** to another
   **dark, cool, jewel tone** that contrasts the outfit:

   | Outfit problem | Inner-hotspot swap (replace `#1a2750`) | Reads as |
   |---|---|---|
   | navy / blue shirt | deep teal `#123a4a` | same family, cooler |
   | black / charcoal | indigo `#28204f` | same family, richer |
   | dark green | slate-plum `#2a1f46` | same family, warmer-cool |

   **Hard limits:** the inner hotspot must stay **dark** (luminance ≲ 30 %) and
   **cool** (blue/teal/indigo/plum). NEVER go light, and NEVER go warm
   (orange/tan/red) — warm clashes with the red bands and the skin tone and
   breaks brand continuity.
3. **Last resort — a subtle rim light:** add a thin bright edge behind the
   subject (`drop-shadow(0 0 0 ...)` stacked, or a blurred light ellipse div
   behind `.facewrap`). Use sparingly; it's the least "brand-default" option.

Record which adjustment (if any) was used in the project's PLAYBOOK §5 so the
series stays consistent.

## 5b. Per-brand color override (multi-brand studios)

The red/green/navy signature in §0/§2 is the **default channel's** brand — it
is not universal across every brand this studio produces for. Before building
a thumbnail, **check the project's `--brand` config** (`project.json.brand`,
sourced from the brand's `brand.json`) for a `thumbnail` block. If one exists,
it overrides the template's default colors for that brand's whole run:

- `accent_hex` replaces the green `.sub span` accent (`#3ddc84` default).
- `inner_hotspot_hex` replaces the gradient's inner hotspot (`#1a2750`
  default) — still subject to §5's hard limits (dark, cool; never light or
  warm) even when brand-driven.
- `bands_hex` replaces the red `.band` color (`#ff4d4d` default) — often left
  at the default even when the accent changes, since the red bands read as a
  cross-studio structural device more than a brand-identity color.

**Example — BRG (Base Reality Group), decided 2026-07-02 for its whole
10-video fractional-CPO series:** `accent_hex: #7b5bff` (BRG's own brand
accent), `inner_hotspot_hex: #28204f` (the indigo option already vetted in
§5's outfit-swap table), `bands_hex` unchanged. See
`~/.claude/explainer-brands/BRG/brand.json`. Apply this to every thumbnail in
that series without re-asking; it's a standing series decision, not a
per-video judgment call.

If a brand has no `thumbnail` block, use the §0/§2 defaults.

## 6. Render

```
python tools/html2png.py <project>/package/thumbnails/thumb_a.html \
  <project>/package/thumbnails/thumb_a.png --width 1280 --height 720
```
(2× device scale is built in for crisp text.)

**A/B Test & Compare is RETIRED (operator directive, 2026-07-26).** Dave: "we
really don't get enough data to do an A/B test. They're always inconclusive. It's
just not worth the effort of uploading." The channel's per-video volume never
reaches significance, so the extra step buys friction, not information.

**The current rule: ship ONE best thumbnail and ONE best title.** Still build
**two** thumbnails, but the second is for **promotional reuse** (social, the
newsletter, LinkedIn), not for testing — design it to stand alone in those
contexts rather than as a near-twin of A. Name them plainly: `thumb_a` = the live
thumbnail, `thumb_b` = promo.

**BOTH thumbnails put Dave in the base image — the promo variant is not exempt
(operator directive 2026-08-12, #56).** A thumb_b built as pure papercraft
data-viz with no Dave was rejected on sight: "We always produce a thumbnail with
me in the base image. The thumbnail is a photorealistic representation of me as
part of the narrative scene." So B gets its own photoreal Dave-in-scene base
(different narrative angle from A, per §6's differ-at-a-glance rule), never an
illustration standing alone. Same session, a second sizing ruling: **band
headlines over a composed scene run ~70px/58px, not the §2 template's
96px** — the template sizes assume the empty navy gradient, and at 96px over a
scene the headline crowds the subject ("the headline is too large"). `publish` sets thumbnail A over the API and nothing
further is needed in Studio; the old "Ineligible until Public" two-step below is
now moot and kept only as historical context.

**SUPERSEDED — the whole Test & Compare flow below is retired.** It is kept as the
record of what the two-step upload used to require (operator directive 2026-06-26:
Test & Compare reads "Ineligible" until the video is Public, every single time).
None of it runs now. Attach thumb_a at upload and stop; do not open Test & Compare,
and do not hold thumb_b back for it.

Thumb_b still gets built, and it still **must differ in a way a viewer notices** —
not to beat variant A in a test, but because it has to stand alone in a feed or a
newsletter where the video's title is not next to it. The
high-leverage variable is the **hook**: give B a different headline *angle*
(claim vs. curiosity vs. negation — e.g. A "MEASURE ANYTHING" / B "NO DATA?
DECIDE ANYWAY"), paired with a different pose/expression. **Two near-identical
poses under the SAME headline is NOT a valid test** — at sidebar size it reads
as one thumbnail, which defeats the experiment. Keep the cutout files as
`headshot-a.png` / `headshot-b.png` beside the HTML.

## 7. Self-QA checklist

- [ ] 1280×720; reads at 120 px wide (squint test: headline + face legible).
- [ ] ≤ 6 headline words, ≤ 2 bands; headline promise == title promise.
- [ ] Payoff words accented green; brand red/green/navy intact.
- [ ] Cutout edge clean (no light fringe, no tan/background halo); thin props not
      thinned by erosion.
- [ ] Subject separates from the bg — if not, applied §5 (and noted it in PLAYBOOK).
- [ ] Two thumbnails rendered: a (live) and b (promo reuse).
- [ ] For a multi-video series: same cutout treatment + layout across the set;
      only copy (and, if needed, the §5 hue) varies.

## 8. Generating with Remotion (preferred path, 2026-06-24)

The brand template above is now also a Remotion **`<Still>`** — `remotion/src/Thumbnail.tsx`,
registered in `Root.tsx` as id `Thumbnail` (1280×720). It replicates this exact look
(navy radial + cool inner hotspot, bottom-right cutout with drop-shadow + bottom fade,
red keyword bands, white sub with green accent) but is **prop-driven**, so it reuses the
same `brand.ts` as the video and the thumbnail is a visual sibling of the render.

- Props: `{bands[], sub, accent[], cutout, mirror, innerHot, bandSize}`.
- Render each: `cd remotion && npx remotion still src/index.ts Thumbnail <out.png> --props=<variant.json> --public-dir=<thumbnails dir>` (the cutout PNG lives in that public dir, referenced by `staticFile`).
- The matting preprocess is unchanged: `cutout.py` (only if the selfie isn't already keyed — **check the alpha first; an operator-supplied transparent PNG is preferred, don't re-segment it**) then `clean_matte.py`.
- **Always trim the cutout to its alpha bbox** — `clean_matte.py --trim` is now the default. A wide transparent PNG with the subject mid-canvas otherwise renders dead-centre under the headline (caught on #12); trimming lets the template anchor the subject to the right.
- The HTML + `html2png.py` path (§2/§6) remains a valid fallback.

## 9. Best-practice guidelines (researched 2026-06-24 — useful, NOT hard rules)

Operator steer: treat these as guidelines for improving our work, not laws.
- **One clear focal point.** Subject anchored to one side; headline owns the opposite zone (don't let text cover the subject).
- **Bigger subject / face** reads better at sidebar size — lean larger. A strong story-prop (the hard hat + saw on #12) can carry the frame when a face alone won't.
- **High contrast** subject-vs-bg and text-vs-bg; the §5 teal/indigo hotspots earn their keep.
- **Fewer words win.** Our two-band + green-sub is the channel signature; keep each line tight and legible.
- **b must differ from a at a glance** — different hook *angle* (claim vs curiosity vs negation) plus a pose change (mirror works); near-identical pairs aren't a real test.
- **Squint test at ~120 px** before shipping.
