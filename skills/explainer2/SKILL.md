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
- `references/spoken-humanizer.md` — read BEFORE drafting any operator-voiced
  script, and RUN as a mandatory pass before the booth (CUT clichés + COMPEL the
  speech). The spoken counterpart to the written `humanizer` skill.
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
Read `references/script-playbook.md` AND `references/spoken-humanizer.md` IN FULL
(the latter shapes the hook + cadence as you write, and is the mandatory CUT +
COMPEL pass before the booth). Pull operator takes:
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
Runs narrate → align → deck → render → mux → manifest → qa. A short takes
~1–2 min; a **deep-dive render runs ~18–25 min**. **Requires `deck.json`
(step 5b).** Then read the QA warnings in the results JSON and fix what is
fixable (deck pacing, dead air) — at most ONE re-render cycle.

**Render robustness (learned the hard way on #34).** A deep-dive render exceeds
the Bash 10-min cap, so it must run as a tracked background job, and a render
that is interrupted mid-encode leaves a **corrupt `work/video_16x9.mp4`
("moov atom not found")**. To survive:
- Wrap it in `caffeinate -i` so the Mac can't idle-sleep mid-encode:
  `caffeinate -i bin/explainer2 media <project_dir>` (run as a tracked
  background job; the harness notifies on completion — do NOT write a polling
  loop, global CLAUDE.md rules still apply).
- **Keep the Claude Code session active until it finishes.** The render is a
  child of the session; switching the desktop app away (e.g. into CoWork) can
  suspend the session and kill the render. `caffeinate` covers OS sleep, not
  session suspension — tell the operator to stay in Claude Code.
- If a render died: delete the corrupt `work/video_16x9.mp4`, then re-run
  `media` (narrate/align/deck are cheap and idempotent; the render redoes).
  Verify the final file with `ffprobe` (duration present, no moov error) before
  Package, and after any deck fix re-cut affected Shorts.

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
`package/thumbnails/`.**
**GATE: present the package. Wait. Then STOP — never post.**

**Shorts (their own medium — read `references/shorts-playbook.md`).** Shorts are
NOT clips of the long-form: each cut reuses the long-form body audio but gets a
**separately-recorded native hook + outro** (short-form best practices). So the
`shorts/plan.json` (3 cuts, each with `segments` + a `hook`/`hook_headline` + an
`outro`, `ending: "loop"` by default) is authored **at the Script stage**, so the
booth records the hooks in the SAME session: `bin/explainer2 record` surfaces them
as extra cards (saved to `voiceover/short_<slug>_{hook,outro}.wav`), then
`bin/explainer2 shorts` assembles hook → body → spoken outro per cut. A cut with no
hook/outro falls back to the legacy lift + silent end-card.

### 8b. Article (generation plane — written companion)
Read `references/article-playbook.md` IN FULL, then write the read-not-heard
companion essay to `package/article.md`: the SAME content and arc as the script,
transformed into real written prose (de-spoken, numbers in written style,
subheads, the Reliance Policy as a boxed list). **No new facts** beyond what the
video earned. **Mandatory: run the full draft through the operator's `humanizer`
skill — the actual skill, not a from-memory self-check — and apply its edits;
it is ground truth for human-readable output.** Set `humanized: true` in the
front matter once done. No render gate — the article is text, reviewed in place.

### 8c. Social share copy (generation plane — `package/linkedin.md`)
Every produced video gets a `package/linkedin.md`: ready-to-paste intros the
operator pastes by hand when sharing the video on LinkedIn (or anywhere). The
tool never posts — this is copy for a human to use.

Write **three** distinct hook-first options, each a different angle on the same
video (e.g. the core idea / a contrarian hook / "the proof, not the pep talk").
Rules:
- **Hook-first.** The first line is all that shows before "see more," so lead
  with the sharpest line, not setup.
- **Short.** A few short paragraphs per option, then the video URL on its own
  line, then ~3 hashtags (LinkedIn ~3 is plenty; trim for other platforms).
- **The live URL goes in inline.** If the video isn't public yet, leave a clear
  `<URL>` placeholder and note it; backfill the real link once it's live.
- **Operator voice, not hustle-bro.** Measured, honest, the adult-in-the-room
  take (see the talk-time library + the article). No fabricated claims, no
  numbers the video didn't earn.
- **Run the draft through the `humanizer` skill** (no em dashes, no clichés,
  no AI tells) — same ground-truth pass the article gets.
End with a one-line *Voice note* describing the register, for the operator's
reference. No render gate — it's text, reviewed in place. (Mirror the format of
an existing `package/linkedin.md`, e.g. video #07's.)

Upload-flow checklist (operator-approved Chrome tag-team on the iMac Chrome;
the operator drags the video + both thumbnail PNGs, you drive the form; the
tool itself never posts): every deep dive gets (1) title/description/tags from
meta.json. The upload form PRE-FILLS channel-default tags that include
cross-channel contamination from the operator's OTHER ventures (climate /
energy / medtech: "methane reduction", "climate tech", "waste to energy",
"robotics for good", "surgical robotics", "AI in clean tech", and the like).
**This channel has nothing to do with climate or medtech — ALWAYS strip those
off-topic defaults, every upload** (operator directive 2026-06-20). Keep only
on-topic founder/business tags, add the video's meta.json tags, and stay under
the 500-char cap; (2) AI-disclosure answered honestly (operator voice + licensed stock +
motion graphics = No); (3) an end screen (subscribe + video) over the payoff
slide — "Import from latest video" is the fast, series-consistent path;
(4) **added to the "Deep Dives" playlist — standing operator rule, 2026-06-12**;
(5) **both thumbnails into Test & Compare, always** (standing rule, 2026-06-19;
never ask whether to A/B); (6) visibility is the operator's call — never set
Public / schedule-Public without an explicit go.
- **Title/description gotcha:** YouTube REJECTS angle brackets (`<` / `>`) in
  the title and description (error "Angled brackets aren't allowed"). Write
  "over $2B" / "40 percent-plus", not ">$2B" / "40%+", in `meta.json` and when
  typing the form.
- **Close-out checklist — do ALL of it the moment the video goes live, in the
  same sitting (operator directive 2026-06-21: "when a project is closed out, all
  of that information is updated, so we never have to backfill again"). Skipping
  any of these is what causes drift and painful reconstruction later:**
  1. `package/meta.json` → set `youtube_url` to the real `youtu.be/...` link.
  2. `package/linkedin.md` → replace the `<URL>` placeholder with the live link.
  3. **`channel/CATALOG.md` — the master local record. MOVE the row out of the
     queue into Published / Made and fill ALL four columns:** the **final
     published title** (it usually differs from the blueprint working title — use
     exactly what's on YouTube), the project dir, the **`youtu.be/...` URL**, and
     the **posted date** (read it off the Studio content page; don't guess).
     Never leave `(fill)` once you have the value.
  4. **Regenerate the promotions ledger:** `bin/explainer2 promote report
     --projects-dir <projects>`. This rewrites `promotions.json` + `PROMOTIONS.md`
     so the just-produced video flips from *(not promotable)* to promotable — it
     now has cut Shorts AND a resolvable URL (the two promotability conditions,
     §9). Skip this and the ledger stays stale and the back-catalogue promoter
     (§9) silently skips the video. (The *(not promotable)* tag is correct only
     for scaffolded-but-unproduced dirs.)
  5. Record in PLAYBOOK §7, then commit all of the above together (including the
     regenerated `promotions.json` + `PROMOTIONS.md`).
  Rule of thumb: a folder with both `package/` and `video/` is *produced*; once
  it's uploaded it is *published* and MUST live in Published / Made, never the
  queue. If CATALOG and `projects/` ever disagree, `projects/` is ground truth —
  reconcile. Launch distribution of a NEW video's Shorts is a SEPARATE
  human-in-the-loop step (the blotato-crosspost skill / `bin/explainer2 shorts`
  then Blotato). Re-sharing the back catalogue later is §9 below.

### 9. Promote (re-share already-published Shorts — `bin/explainer2 promote`)

Keep the back catalogue circulating: on demand, pick a produced+published video
and re-share ONE of its Shorts with fresh wording, tracked in a global ledger so
nothing is over- or under-promoted. It is fine — the point — to re-share a Short
more than once as the library grows; each re-share gets reworded so it never
reads as a duplicate.

This is the ONE place the tool posts to social directly (PRD N1 declared
exception, 2026-06-20). **Operator-invoked only; never schedule it unattended**
(the caption rewrite is a Claude step, so a human/Claude is always in the loop).

Flow:
1. `bin/explainer2 promote select` → picks the next video + Short. Rotation:
   never-promoted videos first, then least-recently-promoted; within the video,
   the least-recently-posted Short. Override with `--video <slug>` / `--short`.
   Returns the mp4 path, resolved video URL, target platforms, and
   `prior_captions` (the do-not-repeat list).
2. YOU (generation plane) write FRESH captions — hook-first, operator voice,
   per-platform, genuinely distinct from `prior_captions` (reword, don't shuffle;
   Reddit/X punish near-dupes). Keep the clickable video URL as the reply-comment
   on X/Bluesky/Threads (`url_comment`), in the YT description, and in the IG
   caption (IG can't auto-comment). Write a plan JSON:
   `{video_slug, short_slug, video_url, short_mp4, scheduled:"next_free_slot",
   posts:[{platform, caption, url_comment?, extra?}]}` (`extra` carries
   platform-specific fields — `mediaType:"reel"` for IG, `title`/`privacyStatus`/
   `shouldNotifySubscribers`/`isMadeForKids` for YouTube).
3. `bin/explainer2 promote post --plan plan.json` → **dry-run by default**: prints
   the exact Blotato payloads. Review them (this is the confirm step).
4. `... promote post --plan plan.json --fire` → publishes (uploads the mp4 once,
   reuses the URL across platforms) and logs each platform to the ledger so the
   rotation advances.
5. `bin/explainer2 promote status` / `report` → library promotion state and
   regenerates `PROMOTIONS.md`. Ledger of record: `<projects>/../promotions.json`.

Notes: Blotato key from `BLOTATO_API_KEY` env, else the blotato MCP config —
never hardcode it. Account IDs default to the operator's channels
(`promote.py` `DEFAULT_ACCOUNTS`); a plan may override per platform; if a post
401s, re-verify via the blotato MCP `list_accounts`. A video must have a
resolvable URL (meta `youtube_url`, else a youtu.be link in meta/PLAYBOOK) AND
cut Shorts to be promotable — `status` flags what isn't (e.g. backfill a missing
`youtube_url`).

## Failure behavior

Any stage fails → report the failed stage, its error, and what you tried. Do
not silently fall back to a different toolchain. Do not switch voices, models,
or services to route around a failure without asking.
