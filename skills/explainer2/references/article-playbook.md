# Article Playbook — the research essay

Follow as a procedure. The article is `package/article.md`: an **in-depth research
essay that answers the video's question further than the video could** (operator
directive 2026-11-12, replacing the "faithful companion" of the same facts). It asks the
same question the video asks and goes deeper: more evidence, the primary sources behind
the video's claims, the strongest counter-argument, the history, the numbers the video had
to round or skip. It does not open new topics. It is published on Substack with the video
embedded after the opening paragraphs, so a reader gets the essay's lede, then the video,
then the depth. It is a **generation-plane** artifact (you research and write it; no
Python, no media pipeline), written AFTER the video is uploaded (§7).

This is NOT a transcript and NOT a re-paste of `script.json`. A transcript of a
spoken script reads as broken prose: breath-paragraphs, booth self-interruptions,
numbers spelled out for the TTS. The article fixes all of that. If you find
yourself copying segments across with light edits, stop — you are transcribing,
not writing.

**VOICE SOURCE (binding, added 2026-07-26; corrected 2026-09-10):** the article is
drafted by invoking the `humaner` skill, which owns all writing quality. Its own order
of authority applies and is not restated here: CRAFT.md is the North Star and writes,
CONSTRAINTS.md breaks ties and carries the hard constraints, LINT.md runs last and
only subtracts, and the fresh-eyes gate runs after everything else. Load the Substack
dial in its FORMATS.md. (This paragraph used to point at a CONSTRAINTS section that was
moved on 2026-08-04, say CONSTRAINTS wins conflicts, which is the inversion the skill's
2026-07-31 ruling reversed, and require a parked digression, a quota the skill deleted
on 2026-08-02. A restatement of the skill drifts; the skill does not.) Everything below
layers on top of that.

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
> embellish the EVIDENCE: the fabrication guardrail below is untouched by this.
> *(2026-11-12: new evidence is now welcome, but only RESEARCHED evidence. A new number,
> source or quote enters through §1b — found, verified, written to the research wiki with
> its provenance — never as a flourish. A new personal anecdote still needs the verified
> story bank or the talk-time library.)*
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

- **Same question, deeper answer (operator directive 2026-11-12).** The essay
  answers the question the video answers, and it may reorder the argument when the
  page reads better that way. It goes further on that one question: what the
  primary sources actually say, the strongest case against the video's conclusion
  and how the evidence handles it, how we got here, the detail and the numbers the
  video had to compress. It does NOT range into adjacent topics the research turns
  up; those are notes for a future video (`content search` first, then the
  blueprint queue). **This reverses the earlier "no new facts" rule, and the
  guardrail moves rather than disappears:** every fact, new or carried over, traces
  to the research wiki, the intel pull, the talk-time library, or a named,
  linked, published source, and every NEW fact is verified and written to the
  wiki before it is written into the essay (§1b). A claim you could not verify is
  cut, or written in the conditional as unverified (the same rule the script
  follows).
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

1. The approved `script.json` — the spine: the question, the conclusion, the
   beats. The essay deepens the script's argument; it does not re-decide the
   conclusion (if the research turns the conclusion, stop and tell the operator:
   that is a correction to the video, not an essay choice).
1a. The project's research: `research/sources.md` and the topic's wiki nodes
   (`explainer-content/research/<topic>/`), plus the blueprint's
   `to_verify_before_script` and `evidence` fields. Read what is already
   verified before searching for more, and check `bin/explainer2 content search
   <topic>` for earlier videos and essays on the same ground.
2. `intel/blueprint.md` — the angle, the GAP statement, the title candidates,
   the SEO/keyword notes (§8 of the blueprint). The article should serve the
   same gap and lean on the same keywords for discoverability.
3. `package/meta.json` (if Package is done) — the description, the chapter list,
   and the CTA link (the site). Reuse the real URL; keep the
   CTA identical to the video's.
4. `script.json.talk_time_sources` — for any line the script marked VERBATIM
   (e.g. Argenti's "garbage output look plausible"), keep it verbatim in the
   essay too, and attribute by name.
5. `package/meta.json` `youtube_url` — the video is live by now (§7), so the
   closing line links the real video, never a `<URL>` placeholder.

## 1b. The research pass (before drafting; this is what makes it an essay)

The video had a runtime; the essay has room. Use it on the video's own question.
Work through these in order, and stop when the next one would not change what a
careful reader concludes:

1. **Go to the primary source behind every load-bearing claim** the video made
   from a secondary one (the paper, the filing, the dataset, the transcript, the
   court record). Quote it where its exact words matter. The video often had to
   cite the coverage; the essay can cite the thing itself.
2. **The strongest counter-argument.** Find the best-informed person or study that
   disagrees with the video's conclusion and give it a fair hearing in the essay.
   Say what the evidence does to it.
3. **What the video compressed.** Numbers it rounded, caveats it dropped for time,
   the method behind a study, the timeline behind an event. Restore them where they
   change how much weight a reader should put on the claim.
4. **History and context** that explains how the situation came to be, where it
   helps the reader judge the present claim (not as a tour).
5. **The blueprint's open items**: anything in `to_verify_before_script` the
   video left hedged may now be verifiable. Verify it, or keep the hedge.

**Every new fact goes to disk the moment it is verified** (`research-wiki.md`: one
node per claim, with the source, the URL, the exact quote and its status) before a
sentence of the essay rests on it. Read web pages with
`python3 /Volumes/Casima/claudeCode/make_money/scripts/webfetch.py <url>` (workspace
rule 10). Keep a running list of the sources you actually use; it becomes the
closing Sources list (§3). Budget: research serves the essay, so aim for roughly 5
to 12 new verified sources, not an exhaustive survey.

**Snapshot every web source you cite, at the moment you cite it** (operator
2026-11-12). webfetch is for reading and may serve a cached copy; the citation
record is a fresh capture:

```bash
~/myenv/bin/python3.12 tools/ref_snapshot.py <project_dir> <url> --claim <wiki-claim-id>
```

It checks the URL resolves, then saves a full-length screenshot of the live page
(a PDF source is saved as the PDF) to `sources/snapshots/` and records it in
`sources/snapshots.json`. Exit 4 means the link is dead: find the live or archived
version, don't cite a dead URL. Exit 3 means a login wall or bot check: open it in
Claude in Chrome, capture it full size, and record that file with `--import <file>`.
`validate` fails an essay that links a source with no snapshot (projects from
2026-11-12 on; the operator's own sites and the video are exempt). **The snapshots
and `snapshots.json` are committed with the project** in explainer-content (operator
2026-11-12, accepting roughly 10-25 MB per essay); only their `previews/` copies are
gitignored. To look at a snapshot, Read only its `tools/frame_preview.py` preview,
never the full image.

## 2. Script → essay: the transformation rules (this is the work)

1. **De-spoken.** Cut everything that exists only because a voice needed it:
   booth filler ("Okay.", "Alright.", "Now —"), breath-beats, and
   self-interruptions that only land aloud ("and look—", "here's the wild
   part"). Some asides are voice; a few are genuinely good on the page — keep
   those, cut the scaffolding.
2. **Restore written number style.** The script spells numbers out for TTS and
   captions ("five hundred million", "fifty-two cents", "eighty percent"). The
   article must NOT. Use digits and symbols the way prose does: $500 million,
   52¢, 80%, $80 → 52¢, 10%. Keep every figure faithful to its source; never
   round or invent. Where the script rounded and the source is exact, the essay
   may use the exact figure.
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
6. **CTA as prose.** Close on the same destination as the video (the site, "more, including
   my latest book"; never a specific title), written as a short generous outro with real links from
   `meta.json` — not "subscribe and hit the bell".

## 3. Length & shape

- **Research essay: 3,000–4,500 words** (operator directive 2026-11-12; was
  1,800–2,500 for the faithful companion). The length is earned by the §1b
  research, never by padding the video's material: if the research doesn't fill
  it, the essay is shorter, and `length_variant: condensed` in the front matter
  says so. `validate` advises outside the band.
- Headline · dek · **lede of two to five paragraphs that stands on its own** (the
  YouTube embed is placed right before the first `##` subheading, so the lede is
  what a reader gets before the video) · the argument as subheaded sections · the
  boxed artifact(s) · CTA outro · **`## Sources`**.
- **Citations: inline links plus a closing Sources list** (operator 2026-11-12).
  Link each claim where it is made, on the words that name the source ("a
  [2023 Stanford study](url) found…"), never a bare "here". End the piece, after
  the CTA, with a `## Sources` section: a bulleted list, one line per source
  actually used, as `[Title](url), Publisher or author, date`. List only what the
  essay cites. No footnote markers: Substack has no native footnotes.
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
  substack_tags: ["AI and Technology", "AI", "Artificial Intelligence", "business"]
  ---
  ```
- **`title` and `dek` become the Substack post's title and subtitle**, and the
  `## ` subheads become real Substack headings, at close-out (`bin/explainer2
  substack`, SKILL §8d). Don't repeat the title as a `# H1` in the body.
  **Keep the `dek` to 250 characters or fewer:** Substack rejected a 321-character
  subtitle with a bare 400 (2026-11-12), and the dry run now flags a longer one.
  **`substack_tags`:** 3 to 6 tags already on the publication (`bin/explainer2
  substack <dir>` dry-run lists them), following how the operator tags by hand:
  AI pieces carry `AI and Technology`, `AI`, `Artificial Intelligence`, plus
  `business` or the field (`medtech`, `coding`, `Legal`); founder pieces carry
  `Startups`, `entrepreneur`, `business` plus a topic tag (`Sales`, `Getting
  Customers`, `Management`, `Product Strategy`, `Startup Life`); medtech pieces
  carry `medtech` and `business` plus `FDA`, `Sales` or `Product Leadership`.
  Don't invent a tag: Substack creates one on first use, so a new name needs
  the operator's OK and `--allow-new-tags`.

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
- Curly quotes and apostrophes are fine in the article: it goes to Substack, whose editor
  curls them anyway (operator 2026-11-13; LINT.md §11 carries the carve-out). Never
  straighten them. **The Substack draft is always curly** (operator 2026-11-14, after #84's
  draft arrived with straight marks throughout): `bin/explainer2 substack` curls quotes and
  apostrophes in the title, subtitle and body as it builds the draft, so `article.md` may be
  typed either way and the draft still matches what Substack's editor produces. Inline code
  and bare URLs stay literal. Check the dry run's `substack_draft.json` if in doubt.

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
series CTA rule. Fix every finding or answer it in one line. Rounds and the read every fix
gets before it ships: humaner SKILL.md, "The fresh-eyes gate."

**Re-run the mechanical checks after applying its fixes.** On module 3 the repair for one
finding introduced a section opening on a bare "Which", which is the §0 defect this
playbook already bans. A fix made to satisfy one rule can break another.

## 6. Self-QA checklist (run before presenting)

- [ ] Answers the video's question, deeper; no new topics; the conclusion still
      matches the video (or the operator has been told it doesn't)
- [ ] §1b research done: primary sources behind the load-bearing claims, the
      strongest counter-argument given a fair hearing
- [ ] **Every new fact is a research-wiki node with provenance**; nothing unverified
      is stated as fact
- [ ] Every claim from a source is linked inline; `## Sources` lists exactly the
      sources cited
- [ ] Every cited web source has a `tools/ref_snapshot.py` snapshot in
      `sources/snapshots/` (validate enforces it)
- [ ] Reads as written English — no booth filler, no breath-paragraphs, no
      spoken-only re-hooks left in
- [ ] Numbers in written style (digits/symbols), every figure faithful to its source
- [ ] Article-specific headline + dek; subheads at the act boundaries
- [ ] The Reliance Policy + Monday checklist rendered as a clean list/box
- [ ] Verbatim quotes still verbatim and attributed by name
- [ ] CTA outro uses the real links from `meta.json`; same offers as the video;
      the live video URL, no `<URL>` placeholder
- [ ] Word count in the 3,000–4,500 band, or `length_variant` declared
- [ ] **`humaner` skill's LINT.md pass run on the full draft and its edits
      applied**; `humanized: true` set
- [ ] Front-matter block present and filled, `substack_tags` included

Output: `package/article.md`. Then §7: it goes straight to Substack as a draft.

## 7. When it runs: after the upload, straight to a Substack draft

Operator directive 2026-11-12. The article is the LAST part of Package, after the
video is on YouTube:

> package (meta + thumbnails + linkedin) → `validate --pre-upload` →
> `publish --fire --privacy unlisted` (the video now has its URL) → §1b research →
> write the essay → LINT + fresh-eyes gate → `validate` (full) →
> `bin/explainer2 substack <dir>` dry-run → `--fire`

The Substack draft IS the article's review gate: there is no separate article gate.
Give the operator the draft URL, the word count, the number of new verified sources,
and a note that the LINT pass and the fresh-eyes gate ran. The operator reads it in
Substack and publishes it there; this pipeline never publishes. Then `bin/explainer2
content substack --write` once it is live (SKILL §8d). That write is also what ties the
post to its video in the learn loop: `bin/explainer2 learn articles` snapshots views,
opens, signups and restacks for every post, and the REPORT.md "Articles" section shows
them beside the video's views/day (2026-11-27).
