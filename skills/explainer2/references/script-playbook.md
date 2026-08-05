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

   **PREFERRED SHAPE — open on something they've already done, not on the
   concept (added 2026-07-29, from a structural teardown of Hannah Fry's
   explainer videos).** The strongest cold open is not a claim, a statistic, or
   an artifact. It's a **micro-behavior the viewer performed this week without
   thinking about it**, described concretely enough that they picture themselves
   doing it. Recognition creates the gap on its own — *there's a reason I do
   that, and I've never once asked why* — and the gap is what holds them. Only
   after the recognition lands do you name what the video is about.

   Fry does physical sensations because she does physics ("that slippery feeling
   when you get bleach on your hands"). Our equivalent is a **working-life
   micro-behavior**: the thing they skim, the tab they close, the number they
   quote without checking, the meeting they half-attend.

   **The selection test (all three, or use a different shape):**
   1. **Involuntary** — they did it without deciding to.
   2. **Recent and near-universal** — essentially everyone in the target
      audience did it in the last two weeks. If it needs a job title to qualify
      ("when you're redlining an MSA…"), it fails; fall back to the
      artifact/claim opener.
   3. **It IS the video's subject.** The behavior must be the thing the video
      explains, not a decorative on-ramp to it. If the opener could be swapped
      for a different topic's opener, it's decoration.

   **Then escalate, don't restate.** The felt moment earns the right to tell the
   hard story (the court case, the study, the number). Order is: they recognize
   themselves → then the evidence lands ON that recognition. The escalation is
   strongest when the outside world did the thing the viewer didn't
   (e.g. *"you never checked the summary. In April, a federal judge was handed
   one as evidence, and she checked."*).

   This does not retire the artifact/claim opener — it outranks it. Use the
   claim opener when the topic has no daily involuntary behavior attached.

   **THE THROUGH-LINE — the small thing must GROW, not get abandoned (operator
   directive 2026-07-29).** This is the half of the Fry structure the first pass
   missed. The felt moment is not a hook you leave behind once the video "really
   starts". Dave, on why her videos hold him: *"she draws you right in by just
   mentioning something small that you can quickly connect with. That idea then
   grows into the larger content of the video."* The shape is **one object
   examined at increasing depth**, not an opening anecdote followed by a tour of
   evidence.

   Name ONE concrete object or behavior in the cold open and keep it physically
   present. It must reappear **at every act boundary (≈ every 4–5 min), at the
   midroll seam, and in the closing beat.**

   This is NOT a callback, which stays banned (§1.6: no "remember the X from
   earlier", no motif architecture). The difference is real: a callback
   re-mentions something you dropped; a through-line never left. Each return
   shows the *same* object at a new depth, because the viewer now understands
   more about it than they did last time. Bleach on your hands → what a
   surfactant is → your skin is becoming soap → go wash your hands. One object,
   four depths.

   **How evidence enters.** A study, a number, or a case arrives as *something
   that happened to the object*, never as a new topic. "Here's what a randomized
   trial found about the thing sitting in your inbox" holds the line; "now let's
   look at the evidence on time savings" breaks it and turns the video into a
   lecture.

   **The test:** can the whole video be described as *"one thing, looked at
   closer"*? If the one-sentence summary needs "…and then it covers…", the
   through-line broke.

   **Diagnosis:** list the beats and mark each one where the object is on screen
   or in the sentence. **A run of four or more beats with no contact is where the
   video stops being a story and becomes a survey.** (Honest scoring of #53: the
   object — the summary you skimmed and the transcript underneath it — holds
   through the cold open and act one, then drops out across the email/meetings/
   microphone stretch before returning at the omission beat. That middle gap is
   the weakest passage in the video, and it is exactly what this rule exists to
   catch.)
2. **Promise stack (by seg 2):** open 2–3 loops explicitly ("here's what
   you're getting…"). Record each in `retention_map.open_loops` with its
   closing segment. EVERY loop opened MUST close; verify ids exist.
   - **EXCEPTION — when the cold open is a felt moment, do NOT enumerate them
     (added 2026-07-29; resolves a conflict this playbook was carrying).** An
     itemized "here's what you're getting" converts *I wonder* into *here's the
     menu*, and a menu is the opposite of a small thing growing. It also
     contradicts the sub-rule directly below it, which already forbids topic
     lists — #53 shipped a three-item table-of-contents slide anyway, because
     the parent rule invited one. With a felt-moment open: keep the loops in
     `retention_map` for structural tracking, but narrate **at most ONE**
     after-state line, folded into the flow rather than set out as a list, and
     let the recognition itself carry the rest of the tension. Never author a
     `list` slide for the promise beat in this mode.
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
3. **The credibility beat is RETIRED (operator directive 2026-07-29). Do not
   author one.** There is no longer a "why you should listen to me" segment.
   - **Why.** Dave: *"We're teaching people things. It's not about me. It's
     about the value that I bring. I don't think we need to remind somebody why
     we're important enough to listen to every single slide. In fact it might
     actually degrade our credibility to just be constantly referring to it."*
     He is right, and the mechanism is worth stating: **credibility transfers by
     demonstration, not assertion.** Every sourced number, every disclosed
     funder, every openly stated caveat, every "I could not verify this so I am
     not using it" IS a credibility beat — distributed across the whole video
     instead of concentrated in a claim about the operator. A person who keeps
     explaining why they are worth listening to reads as someone who is not
     sure. With a back catalogue this size, the work is the credential.
   - **What replaces it: nothing.** Do not relocate it, soften it, or fold a
     shorter version in elsewhere. Cut it and go straight from the cold open
     into the material. The runtime it frees belongs to the mechanism (§4.1
     through-line, blueprint §8 spine).
   - **Lived experience is still welcome — as a load-bearing clause, never as a
     credential.** VOICE.md §1.10's *subordinate-clause receipt* is the pattern:
     the experience arrives spent on the point, not displayed. *"After thirty
     years of reading what suppliers will and won't warrant, the first thing I
     check is…"* earns its place because it explains WHY he checks that thing.
     *"I've shipped forty products and led an FDA de novo"* standing alone does
     not. Test: delete the experience clause — if the sentence still teaches the
     same thing, the clause was a credential and should stay deleted.
   - **These are NOT the credibility beat and they REMAIN MANDATORY.** Do not
     let this retirement take them with it:
     - **Honesty disclaimers** ("I'm not a lawyer and this isn't legal advice",
       and its equivalents). Safety and honesty, not self-promotion. Keep.
     - **Evidence hygiene**: who funded a study, sample sizes, the caveat that
       makes a number honest, and openly saying when something could not be
       verified. Keep, and deliver per the riding rule below.
   - **The not-paywalled line is now OPTIONAL and never its own beat.** It was
     doing real work against the affiliate-funnel niche, but by Dave's own
     argument, having to *say* you're not running a funnel is weaker than simply
     not running one and letting the single clean CTA prove it. Use it only when
     a video genuinely contrasts itself with gated material, and then as one
     clause in flow — never a segment, never a slide of its own.
   - **OBLIGATIONS RIDE THE THROUGH-LINE; they do not interrupt it (added
     2026-07-29).** Fry carries no disclosures and no CTA, so nothing ever stops
     her growth. We still carry the mandatory ones above, and each is a full
     halt if authored as its own topic. Deliver them **while still touching the
     object**:
     - *Interrupting:* a standalone beat that leaves the story to explain that
       the answer isn't paywalled.
     - *Riding:* the same promise said with the object still on screen and in
       the sentence — "I'll tell you who paid for every study I cite, because
       on **this** the funding is the whole game."
     - *Interrupting:* a separate card announcing that three of four researchers
       worked for the vendor.
     - *Riding:* that fact spoken inside the sentence that delivers the finding,
       so the caveat and the evidence arrive together.
     Same rule for the mandatory caveats: a caveat folded into the claim's own
     sentence is honest AND keeps the line; a caveat given its own beat reads as
     a disclaimer break. Check the contact column (§4.1) — obligation beats are
     the ones most likely to show up as a gap.
   - **Honesty rule — never claim "nothing to sell" (operator directive
     2026-06-22, still binding wherever the paywall line is used at all).** The
     operator DOES have things to sell: the book, the site, and *The Build*
     newsletter, named once in the CTA. "I've got nothing to sell you / no
     course, no affiliate link" is literally false and is exposed the moment the
     viewer reaches the CTA. If the not-paywalled idea is used, the framing is
     **the answer isn't gated**, never *nothing-to-sell*.
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
   - **Land SMALLER than you started (added 2026-07-29, same source as §4.1).**
     The last substantive beat — the one right before the comment-CTA — must get
     *smaller*, not bigger. No forced inspirational takeaway, no zooming out to
     what this says about work or technology or the future. Land on one small,
     practical, almost throwaway thing the viewer can do, or a dry observation.
     *"Open the transcript once. Not every time. Just once, on a meeting where
     something actually got decided, and see whether it made it in."*
     The scale-up ending ("and that's really what this is all about…") is the
     single most common failure in our closing beats: it reads as a wind-down,
     which §4.7 already forbids, and it wastes the one slot where a concrete
     action would actually stick. **Our format constraint:** unlike the source
     material we can't simply get out of the way — the comment-CTA and the
     single CTA still follow. So "end smaller" governs the *last teaching beat*,
     and the CTA stays crisp and confident per the rules below.
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
     - **Register: warm curiosity, NOT a debate invite (operator behavior, 2026-07-26).**
       The comment prompt is the ONE beat the operator rewrites live in the booth
       essentially every time, and he always softens it the same way. Across #48/#49/#51
       he replaced scripted closers like *"I read the disagreements more carefully than
       the applause"* and *"I'd rather be corrected than repeated"* with *"hey, tell me
       that in the comments as well"*, *"I love the disagreements and I read them every
       time"*, and *"let me know how this works, I'd genuinely love to know more."*
       Those two stock lines are RETIRED. Write the warm version first: an honest open
       question plus a genuine "I'd love to know how this actually works for you." Still
       an opinion-splitter, just framed as an invitation rather than a contest — which
       also matters whenever the video reaches past the operator's own expertise.
       See memory [[comment-prompt-warmer-not-combative]].
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
       (§4.3) must NEVER appear at the closing CTA. (It used to live in the early
       credibility beat; that beat is retired as of 2026-07-29, so in most videos
       the line simply does not appear at all.) The CTA is the moment of the *ask*;
       tacking on "but you don't really need it" right
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
   - **Medium note — UPDATED 2026-07-31: the no-recap rule is now UNIVERSAL.**
     It began as a video-only rule, because a *watcher* who hears "let's recap"
     leaves, costing watch-time and the suggested-video click, and the written
     [[article-playbook]] used to KEEP a short recap as a skim artifact. **That
     exception is reversed.** The `humaner` skill's CRAFT layer (rewritten
     2026-07-31 from Zinsser) bans the summary ending in every format, including
     bulleted "the short version" recaps: the reader hears the cranking, and it
     carries an implied insult that they were too dumb to get it the first time.
     When the point is made, find the nearest exit. `article-playbook` §"NO end
     recap" and `humaner`/FORMATS.md now agree; the skim-artifact job is served by
     the boxed artifacts instead. Formats still differ elsewhere (spoken texture,
     length, CTA register) — don't flatten those.
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
10. **Engineer the click — validate AND reframe, both halves (added 2026-07-29,
    same source as §4.1).** The video's central reveal has a specific shape:
    **what you thought was happening isn't what's happening — but you weren't
    imagining it either.** Most reveals we write do only the second half, which
    lands as *correction*: you believed a wrong thing, here's the right thing.
    Correction makes the viewer defensive. The click makes them feel smart.

    - **Validate first.** Name the true part of what they already believed.
      *"The summary isn't lying to you. Everything in it usually did happen."*
    - **Then reframe.** Move the explanation, not the observation.
      *"You were right that it feels accurate. What's wrong with it isn't in
      there to notice."*

    The test: after the reveal, could the viewer say *"so I wasn't wrong, I was
    looking at the wrong thing"*? If instead they'd say *"so I was wrong,"* the
    reveal is a correction and needs the validating half written back in.
    Applies to the main reversal at the midroll seam and to any beat that
    overturns a belief the audience arrived with.

## 5. Voice rules (conversational, spoken, the operator's)

- **Operator-voice scripts are spoken essays, not caption decks** (operator
  directive, 2026-06-11). The operator is voice-only — no camera, no
  teleprompter-to-lens juggling — and is at his best in flowing, emotive,
  over-coffee delivery. So: let thoughts run. Mix long connective sentences
  with short punch lines instead of defaulting to staccato one-liners.
  Asides and direct second-person warmth are encouraged (but see the next
  rule on written-in tics). Segments may run 60–90 words when the thought is genuinely
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
- **Write the text clean; let the booth add the inflection** (operator
  directive, 2026-07-31). Do NOT write in verbal tics to make the script sound
  human: no inserted `right?`, `you know`, `I mean`, doubled words, or staged
  self-corrections. Those inflections are welcome in the *delivery* — the
  operator adds them naturally at the microphone and they do make the listener
  hear a person — but a tic that arrives because a checklist put it there lands
  in the wrong place and reads as a costume. Zinsser: style is organic, and
  adding it is a toupee. This mirrors the `humaner` skill's 2026-07-31
  correction (VOICE.md Part 1 mechanics are recognition evidence, never a
  generation target) and is why craft now outranks voice. Practical test: if
  you can delete the tic and the sentence gets clearer, it was never his.
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
  (operator directive, 2026-06-19).** The `humaner` skill's LINT.md pass is tuned
  for *written* tells and lets **spoken** clichés through (the operator caught
  several on the teleprompter mid-record on #34). The spoken-humanizer playbook
  is the source of truth for the spoken-specific cliché blocklist and for
  **COMPEL** (hooks, rhythm, concreteness, momentum, register); general AI-tell
  removal is LINT.md's job, not this playbook's. Read spoken-humanizer alongside
  this playbook before drafting; run it as a pass before the booth (see §6).

## 6. Self-QA checklist (run before presenting the gate)

- [ ] Word count within ±10% of budget; read-time matches target
- [ ] Every open loop closes at a real segment id
- [ ] Re-hook spacing ≤ 6 segments everywhere
- [ ] Visual mode changes per the interrupt rule (mark `device` accordingly)
- [ ] Seg 0 passes the cold-open FORBIDDEN list; ending passes rule 7
- [ ] **Cold open: felt moment, or a justified exception (§4.1).** Seg 0 opens on a
      micro-behavior the viewer performed this week, and it passes all three tests
      (involuntary · recent and near-universal · it IS the video's subject). If the topic
      genuinely has no daily involuntary behavior attached, the artifact/claim opener is
      correct — say so in one line at the gate rather than defaulting to it silently.
- [ ] **The through-line holds (§4.1).** The cold open's object is present at every act
      boundary, at the midroll seam, and in the closing beat. Mark each beat for contact:
      **no run of 4+ beats without it.** Evidence enters as something that happened to the
      object, not as a new topic. Test: does "one thing, looked at closer" describe the
      whole video without an "…and then it covers…"?
- [ ] **No enumerated promise stack under a felt-moment open (§4.2).** At most one
      after-state line, folded into the flow; no `list` slide for the promise beat.
- [ ] **NO credibility beat anywhere (§4.3, retired 2026-07-29).** No "why listen to me"
      segment, no relocated shorter version. Any lived experience present is a load-bearing
      clause that explains WHY — delete-test it: if the sentence still teaches the same
      thing without the experience, it was a credential and stays deleted.
- [ ] **The mandatory obligations survived the retirement:** honesty disclaimers (not a
      lawyer / not medical advice) present where required, and evidence hygiene (funder,
      sample size, the caveat that makes a number honest, "could not verify") delivered
      inside the claim's own sentence rather than as its own beat.
- [ ] **The click has both halves (§4.10).** The central reveal validates before it
      reframes. Test: after it, would the viewer say *"I wasn't wrong, I was looking at the
      wrong thing"*? If they'd say *"I was wrong"*, the validating half is missing.
- [ ] **The last teaching beat lands SMALLER (§4.7).** One small practical action or dry
      observation, not a zoom-out. If the beat before the comment-CTA summarizes or reaches
      for significance, rewrite it.
- [ ] **No written-in verbal tics (§5, 2026-07-31).** Grep the draft for `right?`,
      `you know`, `I mean`, doubled words, and staged self-corrections. Each hit gets
      the delete test: if cutting it makes the sentence clearer, cut it. The operator
      supplies that texture live at the microphone; the script does not fake it.
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
      `humaner` skill's LINT.md pass is still ground truth for general AI-tell
      removal and for the article; it does NOT catch spoken tells, which is why
      this pass exists.)

Present to the operator: title, read-time estimate, the retention map table,
and the full script. Wait for approval before recording/narrating.
