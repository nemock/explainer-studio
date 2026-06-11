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

Spoken pace ≈ 150 wpm. `words ≈ target_minutes × 150`. A 13-min deep dive ≈
1,950 words. Segment size: 30–60 words (one breath-paragraph; recordable in
one take). A 13-min script ⇒ roughly 32–40 segments. Shorts: 45 s ⇒ ~110
words ⇒ 4–6 segments.

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

## 6. Self-QA checklist (run before presenting the gate)

- [ ] Word count within ±10% of budget; read-time matches target
- [ ] Every open loop closes at a real segment id
- [ ] Re-hook spacing ≤ 6 segments everywhere
- [ ] Visual mode changes per the interrupt rule (mark `device` accordingly)
- [ ] Seg 0 passes the cold-open FORBIDDEN list; ending passes rule 7
- [ ] All numbers spelled out; no unsourced stats; talk-time rules honored
- [ ] Title promise(s) each map to a specific segment
- [ ] Read every segment aloud mentally — no tongue-twisters, no 70-word runs

Present to the operator: title, read-time estimate, the retention map table,
and the full script. Wait for approval before recording/narrating.
