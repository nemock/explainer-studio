# Shorts Playbook — native short-form cuts from a deep dive

Follow as a procedure. Shorts are **their own medium**, not clips of the long-form.
A short reuses the long-form's *body* audio, but gets a **separately-recorded
native hook and outro** so it performs to short-form best practices. This is the
studio's core principle: each format (video / article / short) is built to ITS
own best practices, never one ruleset flattened across all three.

These rules are **universal across YouTube Shorts / Reels / TikTok** — we
deliberately do NOT author platform-specific variants or render per platform
(that's overreach for now; one 9:16 master per cut goes everywhere).

**Plan shorts at the SCRIPT stage**, not after production — because the hook and
outro lines must be recorded in the SAME booth session as the long-form. So
`shorts/plan.json` is authored right after the Script gate (alongside the deck).

---

## 1. Short-form best practices (the rules the cut must satisfy)

Sourced from a 2025–2026 short-form retention review (load-bearing anchors:
YouTube's Mar-2025 "loops/replays count as views", Mosseri on Reels signals,
TikTok Creator Academy on completion + replays, the Verizon/Publicis caption
survey, n=5,616). Treat directions as reliable; most *percentages* in this space
are single-vendor and unverified — don't quote figures.

**The hook (0–3s) — the whole game.**
- **Zero runway.** A short has ~1–3s before the swipe (vs 15–30s of long-form
  build). No logo, no intro music, no "in this video," no slow zoom, no "hey."
- **The first spoken words ARE the hook** — ~10–14 words carrying the payoff or
  the stakes, at 0.00s.
- **Mute-proof:** a bold on-screen headline carrying the hook in frame one (most
  viewers watch muted). Our `hook_headline` is that text.
- **Hook archetypes** (rotate): contrarian claim · "you've been doing X wrong"
  (negativity bias) · result/proof-first · curiosity gap · in-media-res ·
  identity call-out ("if you're X…" — the viewer self-qualifies in one breath;
  honest version only, per spoken-humanizer §B1).

**Structure.**
- **Payoff first, explanation after** — reverse of long-form; never make a cold
  scroller wait for a build.
- **One idea per short.** Precision, not depth. Layered multi-act is a long-form move.
- **One open loop, and pay it off.** An unresolved loop reads as wasted time.
- **Length is a metric trade-off, not "shorter is better":** ~15–30s maximizes
  completion %; ~30–60s tends to win more total reach. Optimize % watched first.
- **At PLAN time you cannot measure, so budget for it.** The rule below needs the
  recorded hook/outro wavs, and at the Script stage they do not exist yet — nor does
  `work/segments.json`, since nothing has been narrated. So estimate the body from script
  words at about one hundred and fifty four per minute, estimate the hook and outro the
  same way, and then **add fifteen percent before checking the band.** Delivery runs
  slower than the word count: module 2's first cut estimated 58s and recorded 63.5s, which
  is roughly ten percent, and the margin is the difference between trimming now for free
  and re-cutting after a render. Module 3 was planned this way and two of its three cuts
  were trimmed at the plan stage rather than after the booth.
- **MEASURE the length before rendering; never estimate it from word counts.** Body =
  the cut's segment spans from `work/segments.json`; hook and outro = the actual
  duration of `voiceover/short_<slug>_{hook,outro}.wav`, which exist by then because the
  booth records them with the script. Estimating hook/outro from words put module 2's
  first cut at 58s against a real 63.5s — the error lands entirely in the direction that
  breaks the band, because a written line always reads faster than it is spoken.
- **When a cut runs long, look first for a body segment the recorded outro already
  says.** Four of the six Operator's Guide cuts were over 60s, and in every case the
  fix was one segment whose point the outro repeats in compressed form — module 2's
  `ninety-seconds` enumerated the same four decisions in seg 13 and again in the outro,
  word for word. Dropping it took the cut from 63.5s to 41.8s and removed a literal
  repetition. That is the cheapest trim available: it costs nothing the viewer hears
  twice, and it needs no re-recording.

**The outro / loop (our default = loop).**
- **Never signal the end** — no "thanks for watching," recap, or goodbye (same
  rule as the long-form, and confirmed by the short-form research).
- **Default `ending: "loop"`:** write the outro so its last line flows back into
  the hook's first line — invisible replays, and replays now count as views.
- **`ending: "bridge"`** (opt-in per cut): a short, specific, benefit-framed push
  to the full video ("see how this ends"), rendered as the CTA end-card. Never
  loop AND bridge in the same short — pick one goal. (Either way the clickable
  long-form link lives in the post caption/first comment, handled at Blotato.)

**Captions / pacing.** Burned-in karaoke captions, lower-middle third, inside the
safe zones. No dead/silent open — audio + motion at 0.00s.

## 2. Selecting the cuts (default THREE per deep dive)

Pick moments that each: **(a) stand alone** (make sense with zero setup),
**(b) carry one sharp idea/payoff**, and **(c) together cover the video's range.**
The reliable trio:
1. a **curiosity / myth** beat (the surprising claim),
2. a **wow-stat** beat (one number that stops the scroll),
3. a **practical takeaway** (a rule/detector the viewer can use).

(Barnum's three were exactly this: "he never said it" / "38 million" / "3 signs
of fake hype.") Name the parent segment id(s) each cut lifts — non-contiguous is
fine (cut the promise stack out, jump to the payoff).

## 3. plan.json schema (authored at the Script stage)

`shorts/plan.json` is an array of cuts — **the JSON root is a bare `[ ... ]`, not an object
with a `cuts:` key.** This shape is READ BY CODE, not just documentation: `recorder.py`
iterates the root directly and reads `hook` / `outro` off each cut to build the booth's
native hook and outro cards. Deviate and one of two things happens, the second being worse:

- Wrong root (an object) → the booth **crashes** on launch with
  `'str' object has no attribute 'get'`. Loud, and therefore harmless.
- Right root but renamed keys (e.g. `native_hook` instead of `hook`) → it loads fine and
  **silently produces zero hook/outro cards.** The operator records the whole script,
  finishes, and only discovers the missing native hooks when the shorts are cut. That is a
  re-record. (Both were hit on #54, 2026-08-04.)

Copy the field names below exactly. Per cut:
```json
{
  "slug": "never-said-it",
  "title": "P.T. Barnum Never Said 'A Sucker Born Every Minute' #Shorts",
  "segments": [0],
  "hook": "Barnum never said his most famous line.",
  "hook_headline": "HE NEVER SAID IT",
  "hook_accent": ["NEVER"],
  "outro": "So the most famous thing he ever said... he never said.",
  "outro_headline": "HE NEVER SAID IT",
  "ending": "loop"
}
```
- `hook` / `outro` = the **spoken lines the operator records** (the booth surfaces
  them after the main script). Omit either and the cut renders without it (a warning
  logs); omit both and it falls back to the legacy lift + silent CTA end-card.
- `hook_headline` / `hook_accent` = the mute-proof on-screen hook (terse; the
  `accent` tokens must be substrings of the headline).
- `ending`: `"loop"` (default) or `"bridge"`. For `"bridge"`, also give
  `cta_kicker` / `cta_headline` / `cta_accent` / `cta_subkicker` (the end-card).

## 4. Writing the hook & outro (the craft)

- **Hook:** one breath, 3–8s, the sharpest line of the whole cut, the payoff or
  the stakes — NOT a setup. Run it through [[spoken-humanizer]] (no runway, no
  cliché, the operator's voice). The `hook_headline` is its 2–5 word on-screen twin.
- **Outro (loop):** write the last line to hand back to the hook's first line so a
  replay is seamless. It should feel like the sentence completes *into* the open.
- These lines live ONLY in the short — never in the long-form script (a hook in the
  long-form reads as monotonous repetition; the whole reason we record them separately).

## 5. How it renders (so you know what you're building)

The booth (launched detached via `tools/launch_booth.py <deep-dive>`, see SKILL §6)
surfaces each cut's hook/outro as extra cards (saved to
`voiceover/short_<slug>_{hook,outro}.wav`). Then
`bin/explainer2 shorts <deep-dive>` assembles each cut as **[hook + hook slide] →
[lifted body segments] → [spoken outro]** (the old *silent* end-card becomes the
recorded outro), 9:16, parent music bed, then align → deck → render → mux.

## 6. Honest limitation (our format)

Short-form best practice says "change the frame every 2–3s." Our shorts are
**motion-graphic deck slides held for each lifted segment** (often 10–40s a slide)
— we're a slides-and-narration explainer, not a fast-cut talking-head, so we do
NOT natively hit that cut-rhythm. The **hook, standalone framing, mute-proof
headline, captions, and spoken outro are the high-leverage 80%** we DO control.
Rapid cutting is a known trade-off; revisit only if retention data demands it.

## 7. Self-QA (before the booth / before `shorts`)

- [ ] 3 cuts; each stands alone, one idea, covers a distinct part of the video.
- [ ] Every cut has a `hook` + `hook_headline`; the first spoken words are the hook (no runway).
- [ ] Every cut has an `outro`; `loop` outros hand back to the hook; `bridge` outros are short + specific.
- [ ] Hook/outro lines are short-form native and appear NOWHERE in the long-form script.
- [ ] `hook_accent` tokens are substrings of `hook_headline`.
- [ ] Ran the hook/outro through the spoken-humanizer (no clichés, no end-signalers).
