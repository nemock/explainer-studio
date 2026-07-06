# Promo Playbook — the promotional video (a little commercial)

Read this IN FULL before scaffolding or scripting any `promo` content type.
A promo is a **direct-response marketing piece for ONE specific offer** — a
live class, a cohort, a book launch, a new series. The teaching videos use a
story to teach and carry one CTA at the end; a promo IS the CTA, start to
finish. Different job, different craft: this is copywriting, not curriculum.

The script-playbook's retention machinery still matters (a promo nobody
finishes converts nobody), but where the two conflict, THIS playbook wins for
promos. Spoken-humanizer remains mandatory and unchanged.

---

## 0. What qualifies (and what doesn't)

Scaffold `--content-type promo` when the video's success metric is an ACTION
(register, buy, join, pre-order), not watch time or subscribers. One video,
one offer, one action — a promo pushing two things converts to neither; make
two promos. A deep dive that happens to end on the book CTA is NOT a promo;
don't reclassify teaching content to sell harder.

```
bin/explainer2 scaffold "<slug>" --content-type promo \
  --promotes "<the one offer, e.g. 'Plan to Market cohort, Sept 2026'>" \
  --aspect 16:9 --voice-source operator --outdir <repo>/projects
```

`--promotes` is required on purpose: a promo that can't name its offer in one
line is a failed promo before the first word is written.

## 1. The offer brief (gather BEFORE writing — this replaces deep research)

Write these down in `intel/offer-brief.md`; the script implements the brief.

1. **The offer**, in one sentence a stranger understands. What it is, when,
   what it costs (or "free"), where the action happens (the exact URL).
2. **The audience and their temperature.** Cold (never heard of the operator),
   warm (subscribers/list), or hot (waitlist)? Temperature sets how much
   trust-building the script buys before asking: cold needs proof early; hot
   can be asked in the first thirty seconds.
3. **The ONE action** and every step of friction between viewer and done.
   Name the friction; the script must lower it ("takes two minutes",
   "no card required" — only if TRUE).
4. **The transformation.** What is different for the buyer afterward? Sell
   the after-state, not the syllabus (same principle as the script-playbook's
   promise-stack rule: paint the transformation, don't list topics).
5. **The proof inventory.** Real numbers, verbatim testimonials (with
   permission), the operator's earned credentials, past results. Only what
   exists — this list is a hard boundary at scripting time (§4).
6. **The real deadline or capacity limit**, if one exists. If none exists,
   the promo runs WITHOUT urgency. Never invent one.
7. **Intel, scoped to the craft.** The sweep-first rule still applies, but
   point it at the FORM: how do the best launch/announcement/trailer videos in
   this niche hook, structure, and ask? 3–4 queries ("book launch video",
   "cohort course trailer", "<niche> announcement video that worked"). You're
   mining hook shapes and CTA placement, not consensus content beats.

**GATE: present the offer brief + the intended structure to the operator
before scripting.** (This replaces the Blueprint gate; same stop-and-wait.)

## 2. Structure — the shape of a spoken sales letter

Target length: **60 seconds to 3 minutes** (a launch flagship may stretch to
5; never deep-dive length). At ~150 wpm that's 150–450 words — every line
carries weight the way a Short's lines do.

The proven skeleton (adapt, don't worship):

1. **Hook (0–5 s):** the audience's problem or identity, sharpest form.
   Same craft as any cold open (spoken-humanizer §B1) — self-qualification
   IS the targeting. Never open with the product name on a cold audience;
   warm/hot audiences may open with the announcement itself ("it's here").
2. **Twist the problem (one or two lines):** the cost of the status quo,
   concrete. Honest tension only — name a pain the offer genuinely solves.
3. **The bridge:** introduce the offer as the answer. Say what it IS in plain
   words before any flourish.
4. **Proof:** one or two items from the inventory, verbatim and attributed.
   The strongest proof beats three weaker ones stacked.
5. **What you get:** concrete and countable (dates, sessions, deliverables,
   page counts) — specifics do the persuading.
6. **First CTA** — by the halfway mark, never later. Full instruction: the
   action, the place, the friction-lowering line.
7. **Objection beat:** the ONE thing most likely to stall the sale ("I don't
   have time" / "I'm not technical enough"), answered honestly — including
   who the offer is NOT for. The honest-exclusion line builds more trust in
   a promo than anywhere else, precisely because the viewer expects a pitch.
8. **Final CTA + real deadline** (if one exists), then STOP. No wind-down,
   no "anyway...", no softening after the ask (the no-false-modesty rule:
   never talk the viewer back out of the thing just asked for).

**Multiple CTAs are the norm** — first CTA mid-video, final CTA at the end,
and on longer promos one more between. Record them in the script's
`retention_map` as a `cta_map` (segment ids) so placement is checkable. Each
CTA asks for the SAME one action.

## 3. Copy craft

- **Write ten headline/hook candidates, keep one.** Test each against the
  blueprint-playbook §7 machinery — acute not chronic, problem-aware, tension
  named (survival/identity/progress). A promo hook must also pass the
  five-second test: would the named audience know within five seconds that
  this is for them?
- **You-language.** Count the yous and the wes; the viewer should win.
- **Specificity sells.** "Six live sessions in September, capped at twenty
  founders" beats "an intensive cohort experience" every time. If a line
  could appear in anyone's promo, cut or sharpen it.
- **One idea per sentence.** Promo cadence is punchier than the over-coffee
  deep-dive register — shorter sentences, more full stops — but it is still
  the operator talking, not an announcer. Read every line aloud.
- **Price posture:** if the offer costs money, say so plainly once. Burying
  the price reads as a trap; the measured adult names it and moves on.

## 4. Honesty guardrails (brand non-negotiables, sharpened for selling)

Selling is where trust is spent fastest, so the standing rules bind hardest:

- **Every claim from the proof inventory, verbatim where quoted.** No rounded-
  up numbers, no composite testimonials, no fabricated stories (talk-time
  rules apply to promos with zero exceptions).
- **No false scarcity, ever.** Real deadline or no deadline. Real cap or no
  cap. One fake "doors closing" and the operator's every future deadline is
  noise.
- **No secret-knowledge framing** ("what nobody tells you...") and no
  manufactured enemies. The offer wins on what it does, not on a conspiracy.
- **No hype vocabulary** (game-changer, insane, last chance to transform your
  life). The measured voice IS the differentiator in a niche full of hustle
  promos: the adult in the room, selling like an adult.
- **Own that it's a pitch.** This is the one format where "I'm selling
  something today" is the honest register — say it with a straight back.
  (The "answer isn't paywalled" credibility beat belongs to teaching videos;
  a promo doesn't apologize for having a price.)
- **Humanizer + spoken-humanizer passes: mandatory**, same as every script.

## 5. Visual and motion deltas

- **Impact over decoration:** bold kinetic type for the offer name, dates,
  price, and URL — the motion library's full range is on the table (the
  dynamic-is-the-norm rule applies doubly here).
- **Show the thing.** Book cover, cohort workspace, event venue, past-session
  stills — real artifacts of the offer, licensed/owned only.
- **Every CTA is seen AND heard:** on-screen URL/action text synced to the
  spoken ask, and the end-card holds the URL until the video ends.
- Thumbnails: A/B pair as standard; the composed-scene standard applies.

## 6. Pipeline + packaging deltas

- Gates: offer brief (§1) → script (with cta_map) → package. Same stop-and-
  wait discipline; the studio still NEVER posts — where the promo runs
  (channel, ads, embedded on a landing page, unlisted) is the operator's call
  at the package gate.
- Shorts: cut 1–3 **teasers** — each one hook + one CTA, native hook recorded
  in the same booth session as always. A teaser is a promo in miniature, not
  a highlight reel.
- Package deliverables: `meta.json`, `linkedin.md`, A/B thumbnails. **No
  article.md** — the offer's landing page is the written companion (validate
  enforces the per-type set).
- The comment-CTA is OPTIONAL for promos and off by default: the promo wants
  the click, not the thread. Include it only for a warm-audience announcement
  where discussion helps reach.

## 7. Self-QA (before presenting the script gate)

- [ ] One offer, one action; `--promotes` matches what the script sells
- [ ] Hook passes the five-second self-qualification test; ten candidates
      were written
- [ ] CTA appears by the halfway mark; cta_map recorded; all CTAs ask for the
      same action; nothing softens the final ask
- [ ] Every claim traces to the offer brief's proof inventory; any deadline/
      cap is real
- [ ] Zero hype vocabulary, zero false scarcity, zero secret-knowledge framing
- [ ] Word count fits 60 s–3 min at ~150 wpm; every line read aloud
- [ ] Spoken-humanizer CUT + COMPEL run end to end
