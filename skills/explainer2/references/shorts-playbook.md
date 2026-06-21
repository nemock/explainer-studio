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
  (negativity bias) · result/proof-first · curiosity gap · in-media-res.

**Structure.**
- **Payoff first, explanation after** — reverse of long-form; never make a cold
  scroller wait for a build.
- **One idea per short.** Precision, not depth. Layered multi-act is a long-form move.
- **One open loop, and pay it off.** An unresolved loop reads as wasted time.
- **Length is a metric trade-off, not "shorter is better":** ~15–30s maximizes
  completion %; ~30–60s tends to win more total reach. Optimize % watched first.

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

`shorts/plan.json` is an array of cuts. Per cut:
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

`bin/explainer2 record <deep-dive>` surfaces each cut's hook/outro as extra booth
cards (saved to `voiceover/short_<slug>_{hook,outro}.wav`). Then
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
