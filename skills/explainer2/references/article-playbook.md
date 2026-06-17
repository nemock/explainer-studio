# Article Playbook — the written companion essay

Follow as a procedure. The article is `package/article.md`: a long-form,
read-not-heard companion to the finished video. It carries the SAME content and
arc as the script, but it is a real essay — written for a reader who is
scanning and skimming, not a listener following a voice over coffee. It is a
**generation-plane** artifact (you write it; no Python, no media pipeline). It
exists for SEO, newsletter/blog repurposing, and the operator's site — a
durable written twin of the video.

This is NOT a transcript and NOT a re-paste of `script.json`. A transcript of a
spoken script reads as broken prose: breath-paragraphs, booth self-interruptions,
numbers spelled out for the TTS. The article fixes all of that. If you find
yourself copying segments across with light edits, stop — you are transcribing,
not writing.

---

## 0. The contract (read once)

- **Same content, same facts, same arc — different medium.** The article covers
  exactly what the video covers, in the same order of argument. It does NOT add
  a claim, number, story, or quote the video didn't earn. Every fact still
  traces to the intel pull, the research wiki, the talk-time library, or a named
  published source (HBR, OpenAI benchmark, the reported $500M coverage). **No new
  facts.** If the essay wants a detail the script didn't have, that is a research
  prompt, not an airable line — verify or cut, same rule as the script.
- **It reads as written English, not spoken English.** See §2 for the
  transformation rules. The single most common failure is leaving the spoken
  scaffolding in.
- **The operator's voice survives the move to the page.** First person,
  contractions, the storyteller-coffee register, the anti-Barnum daily-user
  stance, the lived Lucent story. Warm and direct — just on paper now.
- **Mandatory Humanizer pass (§5) is the step's gate.** After drafting, the full
  article goes through the operator's `humanizer` skill before it is presented.
  Not a self-check against your own rules — the actual skill. It is ground truth
  and is updated regularly.

---

## 1. Inputs (gather before writing a word)

1. The approved `script.json` — the spine. Same beats, same arc, same facts,
   same order. The article implements the script's argument; it does not
   re-decide it.
2. `intel/blueprint.md` — the angle, the GAP statement, the title candidates,
   the SEO/keyword notes (§8 of the blueprint). The article should serve the
   same gap and lean on the same keywords for discoverability.
3. `package/meta.json` (if Package is done) — the description, the chapter list,
   and the CTA links (book, newsletter, site). Reuse the real URLs; keep the
   CTA offers identical to the video's.
4. `script.json.talk_time_sources` — for any line the script marked VERBATIM
   (e.g. Argenti's "garbage output look plausible"), keep it verbatim in the
   essay too, and attribute by name.

## 2. Script → essay: the transformation rules (this is the work)

1. **De-spoken.** Cut everything that exists only because a voice needed it:
   booth filler ("Okay.", "Alright.", "Now —"), breath-beats, and
   self-interruptions that only land aloud ("and look—", "here's the wild
   part"). Some asides are voice; a few are genuinely good on the page — keep
   those, cut the scaffolding.
2. **Restore written number style.** The script spells numbers out for TTS and
   captions ("five hundred million", "fifty-two cents", "eighty percent"). The
   article must NOT. Use digits and symbols the way prose does: $500 million,
   52¢, 80%, $80 → 52¢, 10%. Keep every figure faithful to the script; never
   round or invent.
3. **Connect the prose.** Script segments are one-breath paragraphs. An essay
   needs real paragraphs with transitions and topic sentences. Merge segments
   that are one thought; split a segment that's secretly two. Structure by the
   argument, not by where the operator took a breath.
4. **Scaffold for a reader.** Give it the furniture a written piece has:
   - An **article-specific headline** — it may echo the video title or a
     blueprint candidate, but written-for-the-page (it can be longer, quieter,
     more keyword-true than a thumbnail title).
   - A one-to-two-sentence **dek** (standfirst) under the headline.
   - **Subheads** at the act/beat boundaries (the script's `beat` labels and the
     meta chapter list are your map).
   - The **artifacts render as structure**: the 3-question AI Reliance Policy and
     the Monday-morning checklist become a numbered list or a boxed callout —
     these are the most reusable, screenshot-able part of the piece.
   - Optional **pull quote** for the one-line thesis ("never build your business
     on somebody else's subsidy").
5. **Reader retention, not viewer retention.** Open loops still work on the page,
   but delete the spoken re-hook tics ("here's where it gets interesting",
   "stay with me"). A reader is held by a strong lede, skimmable subheads, white
   space, and short opening sentences — not by curiosity-reset lines aimed at a
   watch-time graph.
6. **CTA as prose.** Close with the same offers as the video (book, *The Build*
   newsletter, the site), written as a short generous outro with real links from
   `meta.json` — not "subscribe and hit the bell".

## 3. Length & shape

- **Faithful companion: ~1,800–2,500 words.** The written twin of the video,
  same scope. (If the operator asks for an expanded or condensed variant, note
  it — default is faithful companion.)
- Headline · dek · lede (the hook, rewritten for a reader) · the acts as
  subheaded sections · the boxed artifact(s) · a short recap · CTA outro.
- Front-matter block at the top of `article.md`:
  ```
  ---
  title: <article headline>
  dek: <one-line standfirst>
  source_script: script.json
  word_count: <n>
  humanized: true            # set true only after the §5 pass
  date: <YYYY-MM-DD>
  ---
  ```

## 4. Voice rules (inherit the script's, adapted for print)

- Storyteller-coffee register, first person, contractions throughout. Direct
  second-person address ("you", "your business") stays.
- No hype words (game-changer, insane, secret weapon). No em-dash overuse —
  the Humanizer pass will catch it, but don't manufacture work for it.
- Keep the narrative generosity: when the piece names a company or person
  (Lucent, Argenti, Goldman), give the real context the script gave. Same hard
  rule — every piece of backstory color must be verifiable; no plausible-sounding
  invented detail.
- Attribute borrowed authority by name in the text (Argenti / Harvard Business
  Review, OpenAI's benchmark, the reported $500M bill) — honest and good for
  discoverability.

## 5. Mandatory Humanizer pass (the gate)

After the draft is complete, run the **full article** through the operator's
`humanizer` skill. This is non-negotiable and is the step's gate.

- Invoke the actual skill — do NOT substitute your own from-memory checklist for
  it. The skill is ground truth for human-readable output and is updated
  regularly; your shorthand is not.
- Apply the edits it returns to `article.md`, then set `humanized: true` in the
  front matter.
- If the skill flags something the playbook or the source facts forbid changing
  (e.g. it wants to soften a verbatim quote, or cut an attribution), keep the
  fact correct and note the conflict for the operator — facts and verbatim
  quotes win over stylistic smoothing.

## 6. Self-QA checklist (run before presenting)

- [ ] Same arc and facts as the script; **zero new claims/numbers/quotes**
- [ ] Reads as written English — no booth filler, no breath-paragraphs, no
      spoken-only re-hooks left in
- [ ] Numbers in written style (digits/symbols), every figure faithful to script
- [ ] Article-specific headline + dek; subheads at the act boundaries
- [ ] The Reliance Policy + Monday checklist rendered as a clean list/box
- [ ] Verbatim quotes still verbatim and attributed by name
- [ ] CTA outro uses the real links from `meta.json`; same offers as the video
- [ ] Word count in the ~1,800–2,500 band (faithful companion)
- [ ] **`humanizer` skill run on the full draft and its edits applied**;
      `humanized: true` set
- [ ] Front-matter block present and filled

Output: `package/article.md`. Present the operator the headline, the word count,
and a note that the Humanizer pass ran. No separate render gate — the article is
text, reviewed in place.
