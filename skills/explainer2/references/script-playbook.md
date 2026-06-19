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
2. **Promise stack (by seg 2):** open 2–3 loops explicitly ("here's what
   you're getting…"). Record each in `retention_map.open_loops` with its
   closing segment. EVERY loop opened MUST close; verify ids exist.
3. **Credibility is a toll booth** (≤ 1 segment, ≤ 30 words, before the first
   payoff — never before the hook).
4. **Re-hooks:** a curiosity reset every 25–40 s of script time (≈ every 4–6
   segments): a named trap, a counterintuitive rule, "here's where it gets
   interesting". List their segment ids in `retention_map.re_hooks`.
5. **Pattern interrupts:** the visual mode (deck / diagram / artifact /
   footage) must change at least every 3–4 segments; record the rule and the
   planned interrupt points. The biggest energy shift belongs at the midroll
   seam.
6. **Midroll seam (8 min+ videos):** one clean chapter boundary near the
   middle where the strongest re-hook lands; set `midroll_seam_seg`.
7. **Ending (last 1–2 segments):** recap in ONE segment max, then pivot
   directly into the CTA stack (operator's book/site → next video) while the
   payoff is still landing. FORBIDDEN: "thanks for watching", "don't forget to
   like and subscribe", any wind-down. Final sentence = an action imperative.
8. **Chapters** = the `beat` labels; every beat boundary is a chapter.

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
- **Spoken-cliché ban (operator directive, 2026-06-19).** The `humanizer` skill is
  tuned for *written* tells (em dashes, AI vocab) and lets **spoken** clichés
  through; the operator caught several on the teleprompter mid-record on #34.
  Before the booth, hunt and kill these and their close cousins — when spoken they
  read as AI throat-clearing:
  - **Fake-suspense openers:** "here's the thing", "here's the kicker", "and here's
    the kicker", "the truth is", "make no mistake", "let me be clear", "real talk",
    "buckle up".
  - **"Nobody-talks-about" framing:** "the one X nobody argues about / talks about",
    "the part nobody mentions", "what they don't tell you", "the part the
    cheerleaders skip", "the dirty little secret".
  - **Manufactured drama beats:** "let that sink in", "sit with that", "and that,
    right there, is…", "plot twist", "but here's the twist", "and the twist?".
  - **Stock closers:** "at the end of the day", "the bottom line is", "so there you
    have it".
  - **Ad-copy / hype:** "game changer", "in a world where", "imagine a world where",
    "unlock the potential", "say goodbye to X and hello to Y", "the future of X is
    here", "this isn't just X, it's Y", "we're not just X, we're Y", "what if you
    could", "seamless, intuitive, powerful", "supercharge", "elevate", "revolutionize".
  - **Reflexive praise/transition tics:** "put it perfectly", "nailed it", "couldn't
    have said it better".
  Rule of thumb: if a sentence's first clause only exists to tee up the second
  ("Here's the kicker:", "And the twist?"), delete the throat-clearing and just say
  the thing. A real person usually just says it. One genuinely-in-voice "Look," or
  "Here's the thing" across a whole script can survive; a pattern of them cannot.

## 6. Self-QA checklist (run before presenting the gate)

- [ ] Word count within ±10% of budget; read-time matches target
- [ ] Every open loop closes at a real segment id
- [ ] Re-hook spacing ≤ 6 segments everywhere
- [ ] Visual mode changes per the interrupt rule (mark `device` accordingly)
- [ ] Seg 0 passes the cold-open FORBIDDEN list; ending passes rule 7
- [ ] All numbers spelled out; no unsourced stats; talk-time rules honored
- [ ] Title promise(s) each map to a specific segment
- [ ] Read every segment aloud mentally — no tongue-twisters, no 70-word runs
- [ ] **Speakability pass (mandatory since 2026-06-12):** run the full draft
      through the operator's `humanizer` skill (plus a grammar read) before
      the gate. Booth incidents have come from sentences the operator
      literally could not parse mid-read ("the company Square acquired"-style
      compressions, stacked clauses, awkward word choices). Fix anything a
      first-time reader would stumble on — accessible and conversational
      beats clever.
- [ ] **Spoken-cliché hunt (mandatory since 2026-06-19):** the `humanizer` skill
      does NOT reliably catch spoken clichés, so run the §5 spoken-cliché ban list
      over the draft BY HAND before the gate. A single grep for the blocklist
      phrases is cheap insurance; every hit gets rewritten. This must pass before
      the operator is given the booth — the operator should never be the one
      catching "the one place nobody argues about" on the teleprompter.

Present to the operator: title, read-time estimate, the retention map table,
and the full script. Wait for approval before recording/narrating.
