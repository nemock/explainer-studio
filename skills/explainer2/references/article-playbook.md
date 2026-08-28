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

**VOICE SOURCE (binding, added 2026-07-26):** the article is written in the
operator's mined voice via the HumanER skill. Before drafting, read
`~/.claude/skills/humaner/CONSTRAINTS.md` (especially section 1.10, the written
register) and the Substack dial in `~/.claude/skills/humaner/FORMATS.md`. The
seven architecture tells in `~/.claude/skills/humaner/SKILL.md` are the failure
modes that got this exact article type flagged 100% AI-generated (2026-07-25):
max one landed line per piece, no coined frameworks or callback motifs, uneven
paragraph rhythm, at least one parked digression, hedged recalled numbers vs
exact cited ones, verified stories only, no manufactured intimacy. The `humaner`
skill's LINT.md pass runs AFTER drafting as the mechanical AI-tell lint;
CONSTRAINTS.md wins conflicts. Everything below layers on top of that voice source.

---

## 0. The contract (read once)

> **The article is a PERFORMANCE IN ITS OWN MEDIUM, not a transcript with headings
> bolted on (operator directive, 2026-08-05).** Dave's words: *"make sure it's a
> well-written article. It doesn't need to just be basically a regurgitation of the
> transcript with bold headings. That's not good writing... we can easily embellish on
> details, bring more color into the writing... let's make sure that these two different
> performances, the video and the article, are doing the right job in their particular
> mediums."*
>
> What that changes in practice. The video and the essay share an argument, not a
> wording. **Follow the video's flow roughly, not slavishly** — a beat that needed three
> short spoken segments to land may be one tight paragraph on the page, and a beat the
> voice had to keep moving past can breathe, because a reader can stop and re-read. Reach
> for what print can do and speech cannot: a real opening scene, a sentence that rewards
> a second look, an aside in parentheses, a line of white space used for timing.
> **Embellish the WRITING — the color, the texture, the depth of explanation.** Do not
> embellish the EVIDENCE: the fabrication guardrail below is untouched by this, and
> "more color" never means a new number, source, anecdote, or quote. If a paragraph
> wants a fact the script didn't earn, that is a research prompt, not a flourish.
>
> The failure this exists to prevent is the article that is legibly the script with the
> spoken bits filed off and `##` headings inserted every 200 words. If a reader who
> watched the video learns nothing new from the *reading experience*, the article did
> not do its job. Structure it as an essay, with an argument that builds in written
> paragraphs, not as a set of captioned sections mirroring the slide list.

> **Two mechanical checks before presenting, both learned the hard way on #55.**
>
> **1. A heading resets the reader, so no section may open on a bare pronoun.**
> The script pass already tests this — every segment is recorded cold, so none may
> start on *Which* or *Because* — and the same logic applies to prose the moment a
> `##` breaks the flow. #55 shipped a section headed "What you took on" whose first
> line was *"You didn't take on writing it."* Writing **what**? The antecedent was
> three paragraphs back, behind a heading, past a block of comments about other
> people's videos. Dave's verdict: *"a pronoun at the start of a section, hanging in
> space… lazy writing I'd expect from a 9th grader."* Name the noun. Check the first
> sentence after every heading, and while you are there, kill any expletive opener
> (*It would be convenient to…*) — the active form is stronger anyway.
>
> **2. Count the short paragraphs. Do not celebrate the spread.**
> FORMATS.md: *"a short paragraph installed to satisfy a rule reads as a drumroll,
> and the short paragraph only lands because it is rare."* #55's first draft ran 12
> of 64 paragraphs at 12 words or fewer, and the offenders were pure announcements —
> *"Here's the moment everything turns on."* *"Here's where the Saturday left you."*
> Those are throat-clearing set to look like emphasis. Worse, the draft was presented
> as good BECAUSE the lengths varied from 1 to 81 words, which is optimizing for the
> measurement instead of the writing. **A short paragraph earns its place only when
> the thought genuinely ended there.** One or two per piece. The rewrite ran 23
> paragraphs at a median of 91 words with exactly one short one, and it reads as an
> essay instead of a slide deck.

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
- **Mandatory LINT.md pass (§5) is the step's gate.** After drafting, the full
  article goes through the `humaner` skill's LINT.md pass before it is presented.
  Not a self-check against your own rules — the actual pass. It is ground truth
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
  subheaded sections · the boxed artifact(s) · CTA outro.
  - **NO end recap (reversed 2026-07-31, Dave's instruction).** The article
    previously ended with a "short version" recap, kept deliberately on
    2026-06-21 on the reasoning that an article has no dwell algorithm and the
    recap is a useful skim artifact. That reasoning is overruled by the craft
    source: Zinsser, ch. 9, holds that readers leave the moment the end is in
    sight, that a summary repeats in compressed form what was already said in
    detail, and that it carries an implied insult that the reader was too dumb
    to get it the first time. When the point is made, find the nearest exit and
    end on a line worth ending on. See
    `make_money/concepts/zinsser-unity-and-the-lead`.
  - The skim-artifact job the recap was doing is better served by the boxed
    artifact mid-piece (the test, the checklist, the rule), which is already in
    the structure above and which readers can find without being re-taught the
    article at the end.
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
  the LINT.md pass will catch it, but don't manufacture work for it.
- Keep the narrative generosity: when the piece names a company or person
  (Lucent, Argenti, Goldman), give the real context the script gave. Same hard
  rule — every piece of backstory color must be verifiable; no plausible-sounding
  invented detail.
- Attribute borrowed authority by name in the text (Argenti / Harvard Business
  Review, OpenAI's benchmark, the reported $500M bill) — honest and good for
  discoverability.

## 5. Mandatory LINT.md pass (the gate)

After the draft is complete, run the **full article** through the `humaner`
skill's LINT.md pass. This is non-negotiable and is the step's gate.

- Invoke the actual pass — do NOT substitute your own from-memory checklist for
  it. LINT.md is ground truth for human-readable output and is updated
  regularly; your shorthand is not.
- Apply the edits it returns to `article.md`, then set `humanized: true` in the
  front matter.
- If the pass flags something the playbook or the source facts forbid changing
  (e.g. it wants to soften a verbatim quote, or cut an attribution), keep the
  fact correct and note the conflict for the operator — facts and verbatim
  quotes win over stylistic smoothing.

## 5b. Fresh-eyes gate (after LINT, before presenting)

LINT.md is not sufficient on its own and module 3 proved it. That article passed the full
LINT pass with zero blocklist hits, and a fresh reviewer then found that the
negate-then-assert construction fired about ten times against a cap of one, that nearly
every section closed on its own epigram, and that two "Here's the ___" openers were sitting
on top of real spine gaps. None of that is a banned phrase. All of it is bad writing.

Spawn one reviewer subagent (model `sonnet`), give it the finished article, the written
brief, CRAFT.md, the architecture tells, and the **article/Substack** dial in FORMATS.md.
Not CONSTRAINTS.md. Tell it to read the whole piece aloud in one pass and to name the craft
problem in the skill's vocabulary, and hand it the settled carve-outs so it does not
re-argue them: a declared `length_variant`, deliberate repetition, verbatim quotes, the
series CTA rule. Fix every finding or answer it in one line. Two rounds maximum.

**Re-run the mechanical checks after applying its fixes.** On module 3 the repair for one
finding introduced a section opening on a bare "Which", which is the §0 defect this
playbook already bans. A fix made to satisfy one rule can break another.

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
- [ ] **`humaner` skill's LINT.md pass run on the full draft and its edits
      applied**; `humanized: true` set
- [ ] Front-matter block present and filled

Output: `package/article.md`. Present the operator the headline, the word count,
and a note that the LINT.md pass ran. No separate render gate — the article is
text, reviewed in place.
