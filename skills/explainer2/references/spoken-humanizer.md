# Spoken/COMPEL Pass — make a script compelling for the ear

The spoken counterpart to the `humaner` skill's LINT.md pass. LINT.md is
mostly **subtractive** (strip general AI tells: em dashes, AI vocabulary,
rule of three, negative parallelism, staccato runs, nominalizations — run it,
don't re-derive it here). A *spoken* script needs a second, **generative**
half on top of that: it has to actually pull a listener and sound like a real
person talking. Removal alone gives you clean-but-flat, which is its own
failure. So this pass is mostly **COMPEL**, plus pointers for the CUT half, which
the `humaner` skill's LINT.md owns in full, plus a process.

These videos are read aloud by the operator from a teleprompter booth. The bar:
the operator must NEVER be the one catching a cliché or a flat line on the
teleprompter mid-record. This pass is what guarantees that.

## When to run it (twice)

1. **Before drafting** — read this file alongside the script-playbook so the
   craft (especially the hook) informs the writing, not just the review.
2. **As a mandatory gate, before the booth** — run the full CUT + COMPEL pass
   over the finished draft. A script that hasn't passed this does not get the
   booth. (Wired into script-playbook §6.)

---

## A. CUT — remove what makes speech sound machine-made

### A1. Spoken clichés — now covered by LINT.md (converted to pointers 2026-09-10)

This section carried its own blocklist from 2026-06 to 2026-09-10, plus a "reusable CUT
scanner" that sessions copied out and ran. Both are gone. Every rule they held now lives
in the `humaner` skill's LINT.md, which owns all removal, and this file keeps only the
pointers, because a copied list drifts: on 2026-09-10 this section "discovered" *I want
to be careful here* five days after LINT §12b already had it, and the two lists had
been growing separately since August. New phrases go into LINT.md first, under a
category with a test (LINT §12c, the transplant test), and never here
(`~/.claude/skills/humaner/MAINTAINING.md` §2).

Where each thing this section used to hold now lives:

- **Fake-suspense openers, manufactured drama beats, throat-clearing, telegraphed
  virtue** (*here's the thing*, *let that sink in*, *plot twist*, *I want to be careful
  here*, *I want to be fair about that*) → LINT §12b, both shapes, and §12c, the parent
  category and its test. The repair is deletion, never a replacement connector.
- **Secret-knowledge framing and the groundless prevalence claim** (*the part nobody
  talks about*, *most founders have never heard of*) → LINT §4b. The positive half of
  operator directive #13 (ground the hook in the operator's practice, not in
  everyone-else-is-blind) is hook craft, not removal, and stays in B1 below.
- **Ad-copy and hype, reflexive praise of a quoted source** (*game changer*, *imagine a
  world where*, *put it perfectly*) → LINT §3.
- **Stock closers and end-signalers** (*at the end of the day*, *to recap*, *before you
  go*) → LINT §5. The retention reason they matter on video is script-playbook §4.7.
- **Honesty presuppositions and the self-applied honest adjective** (*let me be honest*,
  *my honest answer*, *if I'm honest*) → LINT §6, house additions, and CONSTRAINTS.md
  Part 4. The repair is uncertainty, not honesty: *as best I can tell*.
- **Honesty overclaims** (*nothing to sell*, *no course*, *no affiliate link*) →
  CONSTRAINTS.md Part 4, identity guardrails: he has a book, a newsletter and a site.
  The framing to use instead, the answer is not gated, is script-playbook §4.3.

### A2. Written-tell carryover — now covered by LINT.md
General AI-tell removal (em/en dashes, curly quotes, AI vocabulary like delve,
leverage, tapestry, underscore, intricate, pivotal, testament, vibrant, realm,
navigate (fig.), foster, robust, seamless) is the `humaner` skill's LINT.md
pass — run it, don't re-derive it here. One caption-specific reason to still
care: dashes and curly quotes render LITERALLY in captions, so after LINT.md
runs, re-check the caption text specifically (not just the script prose) for
any straggler the pass missed.

### A3. Overused structures — now covered by LINT.md
Negative parallelism, forced rule-of-three/mirrored slogans, staccato drama
runs, and nominalizations/passive voice are general AI-tell patterns — the
`humaner` skill's LINT.md pass catches these too. Run it rather than
eyeballing this list by hand.

### A4. Conversational fidelity — write the contraction, always (operator directive 2026-07-24)
The operator reads every line aloud, and his delivery — the emotion, emphasis,
and personality no TTS could ever match — **is the product**. It's what gives
these videos their feeling. A stiff, written-out line makes him *fight the
teleprompter* instead of telling the story, and that tension shows on camera.
So the words on the page must already sound like a person talking, not a
"stiff, overly perfect, machine-sounding script."

Default to contractions **everywhere a person would use them**: don't (not "do
not"), I'm, here's, that's, you're, it's, can't, couldn't, won't, who's, we're,
they'd. Written-out forms ("do not", "I am", "cannot", "you are", "it is") read
as machine-formal and flatten the read. Reserve them ONLY for a deliberate,
spaced emphasis beat ("you can **not** ship that"). Grep for the written-out
forms and contract every non-emphatic hit. *(Operator, verbatim: "I say don't,
not do not. That's how human beings speak."; #47, 2026-07-24.)* See
[[dave-delivery-style]].

Caveat when fixing an ALREADY-RECORDED script: match the caption to what the
operator actually SAID, not to a rule. He contracts naturally on the mic, so a
written-out script usually just needs the text updated to the contraction +
re-align (no re-record). But never invent a change the audio won't back — a
caption that contradicts the voice is the [[annotation-marks-land-on-subject]]
class of error for text.

---

## B. COMPEL — make the speech pull the listener

This is the half LINT.md doesn't have. Clean is necessary, not sufficient. The
opening especially must compel — but the *lazy* way to compel is the cliché
LINT §12b and §12c cut. Earn the same pull with substance.

### B1. Hook craft (the cold open) — the paradox, resolved
We need an opening that compels people to keep watching, without sounding like
every AI-scripted video. The cliché is a shortcut to the *feeling* of a hook
without the substance. Build the substance instead:
- **Specificity beats generality.** A real number, a named company, a concrete
  scene, a dated event. ("Claude Code reportedly crossed a billion dollars a
  year" pulls; "AI is changing everything" repels.)
- **Name the stakes.** A concrete reason to stay — what the viewer gains or loses.
  Curiosity *plus* stakes, not curiosity alone.
- **Open a real loop.** A genuine tension the body resolves: a paradox, a
  contradiction, a "both of these are true — how?" (A fake loop — "the answer
  will shock you" — is a cliché; a real one — "I use AI daily and it's the best
  money I spend, so why is most AI spending wasted?" — is a hook.) The loop must
  close at a real segment.
- **Open in media res.** Drop into the surprising fact, scene, or claim. No
  runway, no slow build, no setup of the setup. Thesis inside ~10 seconds.
- **Let the viewer self-qualify (added 2026-07-06).** The strongest openings
  also answer "is this me?" in the first breath — name the problem the viewer
  already feels, or mirror who they are ("if you're the founder who…").
  Problem-first and identity-mirror openings pull attention almost
  involuntarily because they hit survival/identity tension — but ONLY when
  honest: a real pain the video really solves, a real viewer it really serves.
  The dishonest versions (manufactured fear, secret-knowledge framing,
  drill-sergeant exclusion) are exactly what LINT §4b and §12b ban.
- **Never claim secret knowledge to manufacture a hook** (operator directive #13,
  2026-06-24; kept here rather than in the removal pass because it is hook craft). The
  differentiator is the operator's own voice, perspective, experience and humor, "the
  seasoning on the meat that is me," not a pretense that no one else has ever said this.
  The same claim sourced to lived experience ("after thirty years of building things,
  here's where I've landed") is honest, warmer, and a stronger hook than "the part
  nobody says out loud." A real open loop still works ("one thing I always check
  first"); ground it in his practice, never in everyone-else-is-blind. If a thing is
  genuinely overlooked or misattributed, say so plainly and factually, and teach it.

Two tests every cold open must pass:
- **Specificity test:** could this exact opening front a different video on
  another topic? If yes, it's too generic — add the detail only this one has.
- **Substance test:** delete any opener/transition phrase. Does a concrete claim,
  number, or scene remain? If removing the throat-clearing leaves nothing, the
  hook was hollow — rebuild it on a fact, not a phrase.

### B2. Rhythm and cadence (write for the breath, not the eye)
- **Vary sentence length.** Mix long, connective sentences that take their time
  with short punch lines. Even, mid-length cadence is the tell of machine prose.
- **One idea per breath.** A segment is a breath-paragraph; if you'd run out of
  air or lose the thread reading it aloud, split it.
- **The operator's register** (see [[dave-delivery-style]] equivalent): warm,
  over-coffee, conversational. Asides and direct second-person are encouraged.
  Conversational is not rambling; every sentence still earns its place.
- **Register comes from the thinking, not from tics** (operator directive,
  2026-07-31). Warmth is built with firm opinions stated without hedging,
  concrete particulars, and writing to one person. It is NOT built by sprinkling
  `right?`, `you know`, `I mean`, doubled words, or staged self-corrections into
  the text. Those land wrong when a checklist places them; the operator adds them
  himself at the microphone, which is where they belong. If you can delete the
  tic and the sentence gets clearer, it was never his. Same correction as the
  `humaner` skill's "style is organic — there is no style store."

### B3. Concrete over abstract
- Real numbers, named people and companies, specific scenes. Specific nouns beat
  category nouns ("a handful of torn paper" beats "some materials").
- Show the thing happening; don't summarize that it happened.

### B4. Direct address and warmth
- "You" throughout. Talk to one person, not an audience. The listener should feel
  addressed, not lectured.

### B5. Momentum (earn the next sentence)
- Every segment should end giving a reason to keep listening — a small open loop,
  a turn, a fact that reframes the one before it. **Not a staged reveal.** This
  line used to offer "but here's where it gets real" with a parenthetical saying
  to use the substance version and not the cliché; per the 2026-08-02 ruling a
  disclaimer does not neutralize an imperative, and the phrase got reached for
  anyway. It is now banned outright (`humaner` LINT §12b, 2026-08-28). The
  substance does the pulling; a phrase announcing that a payoff is coming spends
  the listener's patience on nothing. Honor the retention map's re-hooks and
  open loops.

### B6. A point of view
- Have an opinion and let stakes show. Acknowledge tension or mixed feelings where
  they're real. This is the "soul" CRAFT.md and CONSTRAINTS.md ask for in writing,
  aimed at the ear — neutral reporting is forgettable; a clear, honest stance is not.

---

## C. Process (draft → cut → compel → read aloud)

1. Draft per the script- and blueprint-playbooks (hook craft from B1 informs the
   cold open as you write).
2. **CUT pass:** the `humaner` skill's LINT.md pass, in its own running order, over
   every segment's `text` including each Short's hook and outro. It owns every removal
   rule, spoken clichés included (§12b, §12c, §4b, §3, §5, §6); this file has carried no
   list of its own since 2026-09-10. SKILL.md wires the pass into the pre-booth gate.
3. **COMPEL pass:** run the B checklist. Rewrite flat openers, even cadence,
   abstract nouns, and any segment that doesn't earn its next line. Apply the two
   hook tests to seg 0.
4. **COHERENCE pass (mandatory — operator directive 2026-07-24).** We have shipped
   several cards with a verb dropped, a word missing, or an entire sentence that
   simply doesn't parse. These are tiny, human-readable strings — trivial to catch,
   embarrassing to miss, and they wreck a live read.

   **Run the checker FIRST — it is not optional and reading the cards is not a
   substitute (added 2026-08-07, #56).** This step used to say only "go card by card and
   check", and on #56 that eye-pass shipped eight verbless noun-stacks and two bare
   numerals to the booth. Dave caught the first one on card one and called it caveman
   talk. They are invisible to every other pass: not short enough for the staccato rule,
   no banned words for the blocklist. They need a parser.
   ```
   python3 tools/script_coherence.py <project_dir>
   ```
   It flags verbless sentences, a count standing in for a noun ("deal with these
   forty" — forty *what*), cards opening on a bare pronoun or connective, sentences over
   23 words, and mid-sentence colons. It also flags British spelling, British
   vocabulary, and (since 2026-09-10) multi-word British **idiom/construction**. That
   last table is a blocklist of what has actually reached a script, so it catches
   repeats, not first offenses; the general "would an American say this out loud"
   question belongs to the fresh-eyes reviewer, whose brief now asks for it. Exit 1 means fix before the booth; exit 2 means the
   check could not run (install spaCy — never proceed on a skipped coherence gate).

   **It covers EVERY card the booth will show — the script AND each Short's hook and
   outro** (its card numbers are the booth's, so a hit is findable where the operator
   sees it). The first version read `script.json` only, and a defective Short hook walked
   straight past it (#56 card 88). Dave's ruling: *"It should apply to all writing.
   Putting an intro and an outro on a portion of the script to construct a short doesn't
   eliminate the need to write well."* Anything read aloud gets the same gate.

   **What it cannot catch, so the passes below still matter.** Card 88's real faults were
   a wrong idiom ("overstates its evidence"), a subject held across an embedded clause,
   and a referent — "the sales camp" — that a Short introduces cold with nothing behind
   it. None is mechanical. A late-main-verb check was built and REJECTED: on that hook the
   verb arrived at word six, earlier than nine lines of perfectly good script, so it would
   have missed the defect and flagged good prose. The parser buys you completeness, not
   sense.

   Expect one or two false positives in the verbless list: the tagger reads the odd verb
   as a noun ("The projects **span** five fields", "One video **promises** to…"). Read
   each hit. **Do not add an auto-filter** — every filter tried during the build also hid
   real fragments, which is worse than the noise.

   Then go card by card, with the ear, for what the parser cannot see:
   - **Every sentence is complete.** Subject + verb, no dropped words, no half
     sentence, no two sentences fused into nonsense. (You build massive code
     flawlessly; hold these few hundred words of English to the same bar.)
   - **It parses on first read.** If you have to re-read a line to understand it,
     the operator will stumble on it cold on the teleprompter. Rewrite it.
   - **The grammar matches how he'll say it** (contractions per A4), so the caption
     can never contradict the audio.
5. **Read every segment ALOUD** (or mentally). Fix tongue-twisters, stacked
   clauses, and compressions a first-time reader would stumble on.
6. Only then present the script gate / open the booth.
7. **After the deck is built, re-run the coherence pass on the CAPTION BREAKS**
   (deck-playbook self-QA): captions paginate at ~6 words and sentence boundaries,
   so confirm no page strands a fragment that reads wrong out of context (the
   canonical failure: "form this month." split off from "login form", #47). Where a
   break falls wrong, repunctuate the sentence so the page breaks cleanly — a period
   forces a new caption page, a comma does not. Never leave a caption that reads as a
   typo in isolation.

The reusable CUT scanner that sat here was removed 2026-09-10. A copied list drifts:
it "discovered" *I want to be careful here* five days after LINT §12b had it. If a
mechanical pre-pass is wanted, grep LINT.md's own **Watch** lines over the script, and
remember that a grep finds only repeats. The check is the category read (LINT §12c,
the transplant test), and the fresh-eyes reviewer runs it.

## Quick checklist (run before the gate)
- [ ] `humaner` skill's LINT.md pass run in full, including the §12c transplant read.
      It owns all removal, spoken clichés included; this file has no list of its own.
- [ ] Cold open passes the specificity test AND the substance test.
- [ ] Sentence length genuinely varies; no even mid-length drone.
- [ ] Concrete nouns / real numbers / named people, not abstractions.
- [ ] Direct "you" address; a clear point of view.
- [ ] Every segment earns the next; open loops + re-hooks honored.
- [ ] **Contractions everywhere natural (A4);** written-out "do not / I am / cannot"
      only for deliberate emphasis.
- [ ] **`python3 tools/script_coherence.py <project_dir>` exits 0** — no verbless
      noun-stacks, no bare numerals, no card opening on a pronoun/connective, nothing
      over 23 words, no mid-sentence colons. An eye-pass does not substitute for this
      (#56); exit 2 means the gate did not run, which is not a pass.
- [ ] **Coherence: every sentence complete + parses on first read** — no dropped
      verbs, missing words, or broken/fused sentences.
- [ ] Read aloud — nothing the operator would stumble on cold.
- [ ] **After deck build: caption breaks reviewed** — no fragment stranded so it
      reads as a typo out of context (repunctuate to force a clean page break).
