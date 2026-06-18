---
name: explainer2
description: >
  Produce a YouTube-intelligence-driven, retention-engineered explainer video
  (deep dive and/or Shorts) end-to-end on this Mac: intel sweep → Blueprint →
  script → operator recording (or Kokoro) → align → render → package. Use when
  the user says "/explainer2 <topic>", "make a video about", "run the studio
  pipeline", or asks for a Blueprint on a topic. Local/free only; the single
  allowed subscription is the operator's stock.adobe.com membership,
  human-in-the-loop. This skill NEVER posts to social platforms.
---

# /explainer2 — Explainer Studio pipeline

You are the **generation plane** of this system. The CLI (`bin/explainer2`) is the
**media plane** — pure Python, no LLM. You do research, judgment, and writing;
the CLI does fetching, audio, rendering. Never hand-do what a CLI verb does.

**You are expected to follow the playbooks, not improvise.** The analytical
method lives in four reference files you MUST read at the step that needs them:

- `references/blueprint-playbook.md` — read BEFORE synthesizing any Blueprint.
- `references/script-playbook.md` — read BEFORE writing any script.
- `references/deck-playbook.md` — read BEFORE authoring any `deck.json`.
- `references/thumbnail-playbook.md` — read BEFORE building thumbnails (Package).
- `references/article-playbook.md` — read BEFORE writing the written companion
  essay (`package/article.md`, after Package).

These files encode the methodology that makes the videos good. If your own
judgment conflicts with a playbook rule, follow the playbook and note the
conflict for the operator. Do not skip steps because they seem obvious.

## Hard rules (violating any of these is a failed run)

1. **No paid services.** No API keys, no SaaS. Adobe Stock only via the
   human-in-the-loop flow (you suggest searches; the operator downloads).
2. **Operator gates are real.** STOP and wait for approval at: Blueprint,
   Script, and Package. Never auto-proceed past a gate.
3. **Never post anywhere.** Output ends at the project dir + manifest.json.
4. **Talk-time rules:** quote `quotes.md` verbatim; adapt positions/anecdotes;
   NEVER fabricate a take, story, or statistic not in the library or the wiki.
5. **Sourced facts only.** Every factual claim in a script traces to the intel
   pull, the research wiki, or the talk-time library. No invented numbers.
6. **Numbers are spelled out in scripts** ("five hundred", not "500") — TTS
   and captions both need words.
7. The media pipeline is **synchronous — run it in the foreground** and let it
   finish. No polling, no backgrounding loops (global CLAUDE.md shell rules).

## Environment

- CLI: `/Volumes/Casima/claudeCode/explainer2/bin/explainer2` (wraps the
  shared `~/myenv` interpreter; never install into that venv).
- Projects: `projects/<date>_<slug>/` under the repo root.
- Talk-time library (operator's voice): pass
  `--library /Volumes/Casima/claudeCode/make_money/talk_time` to `talktime`.

## Pipeline (follow in order)

### 1. Scaffold
```
bin/explainer2 scaffold "<slug>" --title "<topic>" --aspect 16:9 \
  --outdir <repo>/projects [--brand <SLUG>]
```
Default 16:9 for deep dives, 9:16 for Shorts-only runs. Ask the operator for
angle/length/aspect ONLY if not given — one cheap confirmation, then proceed.

### 2. Intel sweep (media plane)
Write 4–6 search queries per the **query-expansion rules** in
`references/blueprint-playbook.md` §1, then:
```
bin/explainer2 intel <project_dir> --queries "<q1>; <q2>; <q3>; <q4>; <q5>"
```
Takes 1–3 minutes. Output: `intel/intel.json` + per-finalist transcripts and
thumbnails. If the sweep errors, check yt-dlp/network, retry once, then report.

### 3. Blueprint (generation plane — YOUR main analytical job)
Read `references/blueprint-playbook.md` IN FULL, then execute its procedure
against `intel/intel.json` (read finalist thumbnails with vision; read at least
the top-3 finalists' full transcripts). Write `intel/blueprint.md` and
`intel/blueprint.json` using the playbook's templates.
**GATE: present the Blueprint summary to the operator. Wait for approval.**

### 3b. PLAYBOOK.md (required, same gate)
Every project carries a `PLAYBOOK.md` — the human- and AI-readable record of
why this video is the way it is (learning, reference, modeling). Create it at
Blueprint approval from `references/project-playbook-template.md`; APPEND at
every later gate (script, recording, render, publish). The Learn loop reads
§7. A project without a current PLAYBOOK.md fails review.

### 4. Research wiki (only if the script needs facts beyond the intel)
`bin/explainer2 wiki fact <name> --body "..." --source "<url>"` for each
sourced claim you intend to use.

### 5. Script (generation plane)
Read `references/script-playbook.md` IN FULL. Pull operator takes:
```
bin/explainer2 talktime --library /Volumes/Casima/claudeCode/make_money/talk_time \
  --topics <comma-list from the blueprint>
```
Read the candidate files it lists. Write `script.json` (schema `script/2`, see
playbook §2) with the retention map filled in. Set
`project.json: voice_source` to `operator` for flagship videos.
**GATE: show the operator the script + retention map + read-time. Wait.**

### 5b. Deck (generation plane — REQUIRED before media)
Read `references/deck-playbook.md` IN FULL, then author `deck.json` — one slide
per script segment, ids matching the script. The `media` pipeline's `deck` stage
**fails without `deck.json`**; it is never auto-generated. Validate with
`bin/explainer2 deck <project_dir>` (fast; catches bad fields / missing `figure`
or `footage` images) before the full render. No separate operator gate — the
deck is seen in the rendered video at the Package gate.

### 6. Record (operator voice) or narrate (Kokoro)
- Operator: `bin/explainer2 record <project_dir>` — opens the booth in Chrome.
  The operator records; the command returns when they click Finish.
  Then: `bin/explainer2 adlib <project_dir>` — if any segment is flagged
  `rerecord`, tell the operator which and relaunch the booth; if `adlib`
  segments exist, run with `--apply` so captions follow what was said.
- Kokoro tier: skip record/adlib entirely.

### 6b. Assets (Adobe Stock assist — optional, never blocking)
For scenes the blueprint marked `visual: footage`, author `assets/queue.json`
(fields: slide, beat, queries[2], orientation, note, status:"pending") with
2 concrete searches per scene — name the *feeling* in the note, warn off
clichés. Then `bin/explainer2 assets <dir> open` opens the searches; the
operator downloads into `assets/inbox/` (filename prefixed with the slide id);
`bin/explainer2 assets <dir> ingest` conforms + records license provenance.
Every footage scene keeps its deck slide as fallback — render proceeds either
way.

### 7. Media pipeline
```
bin/explainer2 media <project_dir>
```
Runs narrate → align → deck → render → mux → manifest → qa. Foreground; a
short takes ~1–2 min, a deep dive substantially longer. **Requires `deck.json`
(step 5b).** Then read the QA
warnings in the results JSON and fix what is fixable (deck pacing, dead air)
— at most ONE re-render cycle.

### 7b. Ad-lib drift check (REQUIRED before Package — operator-recorded videos)
The operator records with flexibility: they cut, add, and rephrase live, and that
freedom is intentional. But captions are generated from the recorded script
**snapshot**, so any live deviation leaves captions showing words that weren't
said (or missing words that were). Before packaging, ALWAYS run:
```
bin/explainer2 adlib <project_dir>
```
Read `work/adlib_report.json` per segment (`drift`, `script_text`, `asr_text`) and
separate **recognizer noise** from **real drift**:
- **Noise — IGNORE.** Spelled-out numbers transcribed as digits ("seventy-five
  billion" → "$75 billion"), "A.I."/"I.P.O." losing their dots, contractions,
  and proper-noun mishears ("Anthropic" → "And Tropic"). The script is correct;
  do not touch it. (Whole-segment drift of even ~10% is usually all noise.)
- **Real drift — FIX.** A contiguous phrase in the script the operator plainly
  didn't say (a cut), or a genuine rephrase. To find these past the noise, diff
  *content words* (drop numbers/proper nouns/short function words) script-vs-asr.

**Do NOT use `--apply`.** It rewrites every flagged segment to the raw ASR text,
which would replace your correct spelled-out numbers and proper nouns with digits
and mishears. Fix real drift **by hand**: edit that segment's `text` in
`script.json`, then **re-run `narrate` + `align`** — editing `script.json` alone
is not enough, because captions/align read the snapshot in `work/segments.json`,
which only `narrate` regenerates. Captions are a sidecar file; the deck video does
NOT need re-rendering for a caption-only fix — **unless the fixed segment is used
in a Short, in which case re-cut that Short.**

### 8. Package
Write titles/description/chapters per blueprint §8 into `meta.json` (the
manifest merges it). **Thumbnails: read `references/thumbnail-playbook.md`, then
build A/B 1280×720 cards (cutout → brand template → `tools/html2png.py`) into
`package/thumbnails/`.** Shorts cutting: Phase 5 feature — follow its docs if present.
**GATE: present the package. Wait. Then STOP — never post.**

### 8b. Article (generation plane — written companion)
Read `references/article-playbook.md` IN FULL, then write the read-not-heard
companion essay to `package/article.md`: the SAME content and arc as the script,
transformed into real written prose (de-spoken, numbers in written style,
subheads, the Reliance Policy as a boxed list). **No new facts** beyond what the
video earned. **Mandatory: run the full draft through the operator's `humanizer`
skill — the actual skill, not a from-memory self-check — and apply its edits;
it is ground truth for human-readable output.** Set `humanized: true` in the
front matter once done. No render gate — the article is text, reviewed in place.

Upload-flow checklist (operator-approved Chrome tag-team; the tool itself
never posts): when driving YouTube Studio with the operator, every deep dive
gets (1) title/description/tags from meta.json, with channel default tags
pruned under the 500 cap; (2) AI-disclosure answered honestly (operator voice
+ licensed stock + motion graphics = No); (3) an end screen (subscribe +
video) over the payoff slide; (4) **added to the "Deep Dives" playlist —
standing operator rule, 2026-06-12**; (5) thumbnail A/B via Test & compare
when two comps exist.

## Failure behavior

Any stage fails → report the failed stage, its error, and what you tried. Do
not silently fall back to a different toolchain. Do not switch voices, models,
or services to route around a failure without asking.
