# Script Playbook — retention-engineered, conversational, in the operator's voice

Follow as a procedure. The script is `script.json` (schema `script/2`). The
operator reads it aloud from the booth, so every line must survive being
SPOKEN — read each segment out in your head; if you'd stumble, rewrite it.

---

## 1. Inputs (gather before writing a word)

1. The approved `intel/blueprint.md` — the angle, beats table, hook draft,
   open loops. The script implements the blueprint; it does not re-decide it.
2. Talk-time candidates: run `talktime` with the blueprint's topics, then READ
   the listed files. Rules (non-negotiable): quote `quotes.md` lines verbatim;
   adapt positions/anecdotes into prose; never fabricate a take or stat. Tag
   adapted segments with a `note` naming the source position so the operator
   recognizes their own take on the teleprompter.
3. The research wiki / intel facts for every number you will cite.

## 2. script.json schema (`script/2`)

Top level: `schema`, `title`, `target_duration_s: [lo, hi]`,
`voice_register`, `talk_time_sources[]`, `retention_map{}`, `segments[]`.

`retention_map`: `open_loops[] {id, opened_at_seg, closed_at_seg, promise}` ·
`re_hooks[]` (segment ids) · `midroll_seam_seg` · `pattern_interrupts` (rule
text) · `ending_rule`.

Each segment: `id` (0-based, contiguous), `slide` ("s01"…), `text` (the spoken
words — nothing else), and optionally `beat` (short label), `device` (the
retention device, shown on the booth card as a performance cue), `note`
(delivery guidance / source attribution, shown under the script text).

The media pipeline reads only id/slide/text; the extra fields drive the booth
teleprompter and review UIs. Extra fields are safe.

## 3. Word budget (do this math first)

Spoken pace ≈ 150 wpm (the operator's measured effective rate is ~154 wpm
including gaps — use it). `words ≈ target_minutes × 150`. A 13-min deep dive
≈ 1,950 words. Segment size: 30–60 words (one breath-paragraph; recordable in
one take). A 13-min script ⇒ roughly 32–40 segments. Shorts: 45 s ⇒ ~110
words ⇒ 4–6 segments. Storyteller register (§5) pushes deep dives toward the
TOP of the operator's stated range — confirm target minutes at the blueprint
gate, set the budget, and COUNT WORDS BEFORE PRESENTING THE GATE (both videos
to date missed length on the first draft; the rule exists because it bites).

## 4. Retention rules (each is checkable — check them)

1. **Cold open (seg 0):** the gap-derived claim or question, ≤ 3 sentences.
   FORBIDDEN: greetings, "welcome back", channel branding, "in this video I".
   The thesis lands in the first 10 seconds.

   **Hook craft — compel WITHOUT clichés.** The opening must pull the viewer, but
   the lazy way to pull (the cliché openers) makes us sound like every AI-scripted
   video. Earn the pull with substance: specificity over generality, name the
   stakes, open a *real* loop (a true paradox the body resolves, not "you won't
   believe…"), and start in media res. Full craft + the two gate tests
   (specificity test, substance test) live in **`references/spoken-humanizer.md`
   §B1** — read it before drafting the cold open.

   **Name the problem so the viewer self-qualifies (added 2026-07-06).** The
   first line should let the viewer answer "is this me?" — name the problem
   they already feel (survival tension) and/or who they are (identity mirror:
   "if you're…"). Self-qualification IS the retention filter: the right viewer
   leans in, the wrong one leaves before hurting average-view-duration. This is
   the story's opening tension, not a demographic label. Same guardrail as the
   blueprint's tension check: name a real pain the video really solves.
2. **Promise stack (by seg 2):** open 2–3 loops explicitly ("here's what
   you're getting…"). Record each in `retention_map.open_loops` with its
   closing segment. EVERY loop opened MUST close; verify ids exist.
   - **Paint the transformation, don't list topics (added 2026-07-06).** At
     least one promise should be the AFTER-STATE — what the viewer can do or
     see differently by the end ("by the end you'll spot this trap in any
     pitch deck in thirty seconds"), not a table of contents ("we'll cover
     three things"). Imagining the outcome fires the same circuitry as having
     it; a topic list doesn't. Every painted transformation must be one the
     video actually delivers — it's a promise, and it maps to a closing beat.
   - **Honest exclusion (optional, use sparingly).** ONE line naming who this
     is/isn't for can sharpen the promise when it's TRUE ("this is for the
     founder six months in, not the one picking a logo") — it deepens
     self-qualification and costs only viewers who'd have bounced anyway.
     GUARDRAIL: only when the video genuinely isn't for them; never
     manufactured tribalism or drill-sergeant gatekeeping ("this isn't for
     people who make excuses…") — that register is the manipulation this
     brand is the antidote to.
3. **Credibility is a toll booth** (≤ 1 segment, ≤ 30 words, before the first
   payoff — never before the hook).
   - **Honesty rule — never claim "nothing to sell" (operator directive
     2026-06-22).** The operator DOES have things to sell: the book, the site,
     and *The Build* newsletter (which bundles masterclasses), named once in the
     CTA. So "I've got nothing to sell you / no course, no affiliate link" is
     literally false and corrodes the exact trust the credibility beat exists to
     build — the moment the viewer reaches the CTA, the claim is exposed. Frame
     the *real, defensible* thing instead: **the answer isn't paywalled.** The
     honest, warmer version — *"I'm not burying the actual answer inside a
     membership site or a course you have to buy your way into. I'm giving it to
     you right here, because I genuinely want you to benefit — to level up your
     own game. I've got a book and a newsletter; I'll name them once at the very
     end, but you don't need either one to walk away with the whole answer."*
     This is the standard credibility-beat framing now. It applies anywhere the
     script contrasts itself with the affiliate-funnel niche, and a blueprint's
     "differentiation" should be written as *ungated / not-paywalled + genuine
     generosity*, never as *nothing-to-sell*.
4. **Re-hooks:** a curiosity reset every 25–40 s of script time (≈ every 4–6
   segments): a named trap, a counterintuitive rule, "here's where it gets
   interesting". List their segment ids in `retention_map.re_hooks`.
5. **Pattern interrupts:** the visual mode (deck / diagram / artifact /
   footage) must change at least every 3–4 segments; record the rule and the
   planned interrupt points. The biggest energy shift belongs at the midroll
   seam.
6. **Midroll seam (8 min+ videos):** one clean chapter boundary near the
   middle where the strongest re-hook lands; set `midroll_seam_seg`.
7. **Ending (last 2–3 segments) — do NOT signal the end.** Updated 2026-06-21
   (from a YouTube-retention teardown, confirmed by the operator). **No recap
   slide. No wind-down** — kill "thanks for watching", "in conclusion", "let's
   recap", "to wrap up", "before you go / before you click away". Any "let's
   recap"/"we're at the end" beat tells the viewer they're free to leave: it
   bleeds end-retention AND halves the end-screen suggested-video click. You've
   already taught the lesson and shown the payoff — trust it. Go straight from
   the last substantive beat into the comment-CTA, then ONE clean CTA, and stop.
   - **Comment-CTA (next-to-last slide, standard since 2026-06-19, video #08).**
     This beat EARNS its end placement: a genuine open question makes an engaged
     viewer linger to reply — the dwell + engagement we actually want. Make it an
     *honest opinion-splitter* — invite disagreement ("if you think X is naive,
     say so") and/or a personal-story prompt ("what was the moment you…").
     Disagreement is the strongest comment driver. GUARDRAIL: never manufactured
     engagement-bait ("smash the comments", "comment YES if…") — it reads as
     exactly the manipulation the brand is the antidote to. A small "I might be
     wrong about some of this" is good: it lowers the barrier to reply AND models
     the operator's voice. Annotate the segment `device: comment_prompt`.
   - **Final CTA = ONE ask, then stop.** Close on a single `cta`/`payoff` slide
     naming the operator's book/site/newsletter and a single "subscribe". That's
     the end of the video. **CUT the old "final sentence = an action imperative"
     homework line.** Stacking asks (subscribe AND comment AND "now go do X this
     week") triggers decision fatigue and converts none of them; worse, a "go do
     your homework" close lands exactly when the viewer is already reaching to
     click away, so it earns nothing and just signals the end. End on the CTA,
     not on homework. (Operator call, #35 review: keep the comment ask — it can
     buy dwell — but drop the trailing homework imperative.)
     - **No false modesty AT the CTA (operator directive 2026-06-25, #14).** The
       "not-paywalled / you don't need it to get the whole answer" generosity line
       (§4.3) belongs ONLY in the EARLY credibility beat, where it builds trust
       before the value is delivered. Do NOT repeat it at the closing CTA. The CTA
       is the moment of the *ask*; tacking on "but you don't really need it" right
       there talks the viewer out of the exact thing you just asked them to buy.
       Dave: "that's the wrong time to suggest it's not important that they get it."
       So the CTA = name the book + site + newsletter, then the single subscribe
       line, and stop. Keep the genuine humility, just not at the moment of the ask.
     - **Make the CTA crisp, direct, and confident (operator directive 2026-07-14).**
       Beyond just removing the false-modesty line: the ask itself must be clean and
       plainly stated — never wishy-washy, hedged, or padded. Don't pontificate over
       it. Say it warmly and directly, name the offers, and stop. Model cadence:
       *"Go grab a copy of my book, Founders Who Finish, at davesaunders.net. While
       you're there, sign up for my newsletter, The Build."* You may add ONE genuinely
       current teaser only when it's true (e.g. new books landing this year) — kept
       truthful, never invented. Confident and generous is the register, not apologetic.
   - **Medium note — this is a VIDEO rule, not a universal one.** "Don't recap,
     don't signal the end" exists because a *watcher* who hears "let's recap"
     leaves, costing watch-time and the suggested-video click. The written
     [[article-playbook]] deliberately KEEPS a short recap — an article has no
     dwell algorithm, a recap is a useful skim artifact, and it signals the essay
     isn't just a transcript of the video. Each format follows its own best
     practices (operator directive 2026-06-21); don't flatten one ruleset across
     video, article, and short.
8. **Chapters** = the `beat` labels; every beat boundary is a chapter.
9. **Define terms as you use them — comprehension IS retention (operator directive
   2026-07-14).** An undefined term the viewer doesn't know blocks them from
   following everything after it: they quietly tune out, so it's a retention leak,
   not just a clarity miss. When the script reaches for a term a newcomer to the
   topic might not know — jargon, an acronym, an insider phrase — define it
   *observably* the first time. Not a dictionary gloss: what it looks like in real
   life or how you'd actually do it. ("Progressive overload just means lift a weight
   for a set number of reps, and once that's easy, add a little more.") This is the
   channel's teaching thesis in miniature — guided, contextual understanding a
   beginner won't get by prompting an LLM cold. **The filter (from the source
   teardown):** reread the draft asking *"what does that mean?"* at every line;
   anywhere you'd have to ask, it wasn't defined. Two payoffs land at once —
   beginners get their first real grasp of the idea and bond to the operator,
   while experts think "I've never heard it put that clearly." GUARDRAIL: define,
   don't condescend. One clean observable definition, then move on; don't stop to
   re-explain terms the whole audience already owns.

## 5. Voice rules (conversational, spoken, the operator's)

- **Operator-voice scripts are spoken essays, not caption decks** (operator
  directive, 2026-06-11). The operator is voice-only — no camera, no
  teleprompter-to-lens juggling — and is at his best in flowing, emotive,
  over-coffee delivery. So: let thoughts run. Mix long connective sentences
  with short punch lines instead of defaulting to staccato one-liners.
  Asides, self-interruptions ("and look—"), and direct second-person warmth
  are encouraged. Segments may run 60–90 words when the thought is genuinely
  continuous; the 30–60 guidance applies to TTS-tier scripts. Conversational
  is not rambling: every sentence still earns its place.
- **Storyteller register (operator directive, 2026-06-12): these are stories
  that help, not video-form sales letters.** The videos being modeled are
  often cut-and-dry funnel pieces; the operator's edge is narrative. When the
  script cites a company or founder, give them real context — two to four
  sentences of who they were, what they'd tried before, what corner they were
  in — instead of compressing a history into one clause. ("Drew Houston got
  the Dropbox idea on a bus with a forgotten USB stick" beats "Dropbox
  validated with a video.") HARD RULE: every piece of backstory color must be
  verifiable from intel, the wiki, or talk-time. If the operator (or you)
  reaches for a plausible-sounding detail, that is a RESEARCH PROMPT, not an
  airable fact — verify or cut. The CTA stack stays (book, site, mailing
  list, subscribe), but it rides on generosity of narrative; the goal is
  videos that endure for years, not funnels that convert this week.
- Contractions always. Direct address ("you") throughout. No hype words
  (game-changer, insane, secret weapon).
- **Spell out ALL numbers as words** ("five hundred", "fifteen percent") —
  TTS, captions, and the adlib checker all want words.
- No stage directions inside `text` (it is read aloud verbatim). Delivery
  guidance goes in `note`/`device`.
- Rhetorical questions sparingly (≤ 1 per 5 segments). Lists of three, max.
- Every factual claim: traceable to intel, wiki, or talk-time. Attribute
  borrowed authority by name in the text ("Y Combinator's Startup School puts
  real numbers on this") — it's both honest and a proven performance pattern.
- If comment mining found density-praise: cut 10% of words after drafting.
- **Spoken-cliché ban + compelling-speech craft → `references/spoken-humanizer.md`
  (operator directive, 2026-06-19).** The `humanizer` skill is tuned for *written*
  tells and lets **spoken** clichés through (the operator caught several on the
  teleprompter mid-record on #34). The spoken-humanizer playbook is the single
  source of truth for BOTH halves: **CUT** (the spoken-cliché blocklist) and
  **COMPEL** (hooks, rhythm, concreteness, momentum, register). Read it alongside
  this playbook before drafting; run it as a pass before the booth (see §6).

## 6. Self-QA checklist (run before presenting the gate)

- [ ] Word count within ±10% of budget; read-time matches target
- [ ] Every open loop closes at a real segment id
- [ ] Re-hook spacing ≤ 6 segments everywhere
- [ ] Visual mode changes per the interrupt rule (mark `device` accordingly)
- [ ] Seg 0 passes the cold-open FORBIDDEN list; ending passes rule 7
- [ ] All numbers spelled out; no unsourced stats; talk-time rules honored
- [ ] Title promise(s) each map to a specific segment
- [ ] Every topic-specific term a newcomer might not know is defined observably on
      first use (§4.9) — reread asking "what does that mean?"; no line leaves it unanswered
- [ ] Read every segment aloud mentally — no tongue-twisters, no 70-word runs
- [ ] **Spoken-humanizer pass (mandatory since 2026-06-19, supersedes the old
      speakability pass):** run `references/spoken-humanizer.md` end to end before
      the gate — **CUT** (grep the spoken-cliché blocklist; every hit rewritten)
      and **COMPEL** (hook tests, cadence variety, concreteness, momentum) — then
      read every segment aloud and fix anything the operator would stumble on
      ("the company Square acquired"-style compressions, stacked clauses). This
      MUST pass before the operator is given the booth — the operator should never
      be the one catching a cliché or a flat line on the teleprompter. (The
      written `humanizer` skill is still ground truth for the article; it does NOT
      catch spoken tells, which is why this pass exists.)

Present to the operator: title, read-time estimate, the retention map table,
and the full script. Wait for approval before recording/narrating.
