# Blueprint Playbook — how to turn intel.json into a winning video plan

This file encodes the full analytical method. **Follow it as a procedure, in
order, producing each named artifact.** Do not summarize the intel and call it
a blueprint — the value of this tool is the analysis below, especially §6 (the
gap). A blueprint without a defensible gap statement is a failed blueprint.

The operator is a **curator**: they may not personally know the topic's best
practices yet. Your job is to (a) extract what the winning videos collectively
teach, so the operator can deliver best-of-breed content in their own voice,
and (b) find the angle none of the winners owns. Both halves are mandatory.

---

## 1. Query expansion (before running `intel`)

Write 4–6 queries that triangulate the topic. Use these slots:

1. The topic as a viewer would type it ("how to get your first customers SaaS")
2. A number-promise variant ("first 100 customers SaaS")
3. An objection/constraint variant ("SaaS marketing with no audience")
4. A first-person story variant ("how I got my first paying customers startup")
5. An adjacent-audience variant (B2B / app / agency — one step sideways)
6. (optional) A named-authority variant if one dominates the niche

Avoid: queries that are just synonyms of each other; queries broader than the
topic ("marketing tips"); queries with fewer than 3 words.

## 2. Reading intel.json — build the finalist table FIRST

Make a table of all finalists: title · channel · outlier score · views ·
duration · upload date. Then mark:

- **Breakouts** (outlier ≥ 20×): what did these do that their own channel's
  baseline didn't? The breakout's *delta from its channel* is the lesson.
- **Heavyweights** (views ≥ 100K regardless of outlier): proven absolute demand.
- **Strays**: off-topic finalists (adjacent niche that leaked in). Note and
  discount them — but check their top comments for crossover demand signals.
- **Aged winners** (>2 years old, still ranking): evergreen demand; their
  framing is the incumbent you must beat.

Read with vision the thumbnails of every breakout + the top heavyweight. Read
the FULL transcript of at least the top-3 (by your judgment of relevance ×
performance). Read every finalist's `transcript_hook`, `chapters`,
`description_head`, and `top_comments`. This is not optional — the gap in §6
almost always hides in the transcripts and comments, not the titles.

## 3. Convention extraction (what the winners share)

Produce three short lists:

**a. Consensus content beats.** The claims/advice nearly every winner makes.
These go in OUR video too — a credible entry must cover the consensus;
differentiation comes from execution and the gap, NOT from contradicting
settled advice. List each beat in one line.

**b. Title patterns.** Classify every finalist title into: number promise /
objection-removal qualifier ("without ads", "no audience") / conditional
restart ("If I started in YEAR") / borrowed authority (named org/person) /
earned authority ($X MRR) / negative-or-mistake framing / command. Note word
counts. Our titles must use these patterns — ideally a combination or an
unused permutation (see §7).

**c. Hook shapes (first 30 s of transcripts).** Classify each: negation
("forget X, forget Y") / credential-stack / proof-montage / question-mirror
(voicing the viewer's question) / cold-claim. Note: how many seconds until the
video's thesis? Winners are almost always under 10. Ours must be.

## 4. Comment mining (demand + authenticity signals)

Top comments are free market research. Extract:

- **Demand signals**: questions asked repeatedly; "I wish you covered X";
  the next video the audience is asking for.
- **Density praise** ("no BS", "straight to the point") — if present, the
  audience punishes padding; keep our script dense and say so in the script
  notes.
- **Authenticity policing** (accusations of AI content, ad fatigue, astroturf
  bots in the comments) — if present, recommend operator voice and note that
  polish-over-substance will be attacked.
- **Top-comment summaries** (someone lists the video's points and gets top
  likes) — signal that viewers want the structure visible: use chapters and
  put the list on screen.

## 5. Thumbnail analysis (vision, every breakout)

For each: text on image (count words) · face present? · color scheme ·
before/after or progression devices · what makes it readable at 120 px wide.
Output 2–3 directions for OUR thumbnail that match niche conventions while
staying brand-consistent. Convention beats novelty in thumbnails; the title
carries the differentiation.

## 6. THE GAP — the analysis that justifies this tool's existence

Answer ALL FOUR questions in writing. Cite finalist evidence for each:

1. **Who is underserved?** What viewer situation do all finalists assume away?
   (Most common: winners narrate from post-success; the true beginner's
   constraints — no audience, no money, no network — are claimed in titles
   but not honored in content.)
2. **What's buried?** Is the single most counterintuitive, save-worthy insight
   in the dataset trapped mid-video in a long piece? (Check the heavyweight's
   transcript especially.) A buried insight promoted to a cold open is a
   proven breakout pattern.
3. **What's missing entirely?** Concrete artifacts (real templates, real
   numbers, real calendars)? A current-year reality the older winners predate?
   A step everyone references but nobody shows?
4. **What's the contrarian truth?** Is there a position the comments support
   but no video states plainly? (Often visible as the highest-liked comment
   disagreeing with or extending the video.)

Then write the **gap statement**: 2–4 sentences naming the angle that exploits
the strongest of these, and why THIS operator can own it (check the talk-time
library for positions that align — an angle backed by an authentic operator
take beats a synthetic one).

**Quality bar:** if your gap statement could have been written without reading
the transcripts and comments (i.e., it's generic — "be more practical", "go
deeper"), it is not done. Re-read §2's materials and find the specific gap.

## 7. Title candidates

Write 5, ranked. Rules: every candidate uses patterns from §3b; at least one
combines two patterns in a way no finalist used; at least one is the "safe
conventional" play; the #1 pick should weaponize the gap. 8–14 words. No
clickbait the video doesn't cash: every promise in the title must map to a
script beat.

## 8. Assemble blueprint.md + blueprint.json

`blueprint.md` sections (in order): 1 Competitive picture (the §2 table +
one-line lesson per row) · 2 What the winners share (§3) · 3 The gap (§6, with
the recommended angle) · 4 Title candidates (§7) · 5 Hook strategy (draft the
actual cold-open lines; name the open loops and where each pays off) ·
6 Structure & retention-map skeleton (beats table with times + devices; mark
the midroll seam for 8 min+) · 7 Thumbnail direction (§5) · 8 SEO/description
notes (keywords from finalist tags; chapters; operator CTA block; pinned-
comment idea) · 9 Risks/notes (incl. authenticity findings from §4).

`blueprint.json`: machine-readable mirror — schema `blueprint/1`, fields:
topic, angle, gap[], consensus_beats_required[], title_candidates[],
hook{draft, open_loops[]}, format{primary, target_duration_s, shorts[]},
voice{source, rationale}, visual_budget{}, thumbnail_directions[], seo{},
evidence{intel_json, finalists_analyzed, top_outliers[]}.
Set `status: "awaiting_operator_approval"`.

**Format recommendation rule:** target duration = the median of the
non-stray finalists, clamped to 8–17 min for deep dives (8+ for midroll).
Always propose 3 Shorts cut from the strongest standalone beats.

## 9. Present the gate

Show the operator: the angle + gap statement (3–4 sentences), the #1 title,
the target length/format, and ONE question if anything material is ambiguous.
Wait. Do not start the script until approved.
