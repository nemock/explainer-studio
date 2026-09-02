---
name: explainer-studio
description: >
  Produce a YouTube-intelligence-driven, retention-engineered explainer video
  (deep dive, Shorts, a masterclass/Operator's-Guide series episode, or a
  promotional video) end-to-end on this Mac: intel sweep → Blueprint → script →
  operator recording (or Kokoro) → align → render → package → publish. Use when the
  user says "/explainer-studio <topic>", "make a video about", "run the studio
  pipeline", or asks for a Blueprint on a topic. Local/free only; the single
  allowed subscription is the operator's stock.adobe.com membership,
  human-in-the-loop. Nothing auto-posts: `publish` (YouTube) and `promote`
  (Blotato re-shares) run only when the operator asks. See hard rule 3.
---

# /explainer-studio — Explainer Studio pipeline

You are the **generation plane** of this system. The CLI (`bin/explainer2`) is the
**media plane** — pure Python, no LLM. You do research, judgment, and writing;
the CLI does fetching, audio, rendering. Never hand-do what a CLI verb does.

**You are expected to follow the playbooks, not improvise.** The analytical
method lives in four reference files you MUST read at the step that needs them:

- `references/blueprint-playbook.md` — read BEFORE synthesizing any Blueprint.
- `references/script-playbook.md` — read BEFORE writing any script.
- `references/spoken-humanizer.md` — read BEFORE drafting any operator-voiced
  script, and RUN as a mandatory pass before the booth (COMPEL the speech for
  the ear — hook craft, cadence, momentum; general AI-tell removal is the
  `humaner` skill's LINT.md pass).
- `references/deck-playbook.md` — read BEFORE authoring any `deck.json`.
- `references/motion-playbook.md` — the Remotion motion-graphics vocabulary (animated
  successor to the deck-playbook); read BEFORE authoring a motion spec. Engine is a
  phased build (shorts first); until it ships, the deck-playbook governs.
- `references/thumbnail-playbook.md` — read BEFORE building thumbnails (Package).
- `references/article-playbook.md` — read BEFORE writing the written companion
  essay (`package/article.md`, after Package).
- `references/masterclass-playbook.md` — read BEFORE scaffolding a multi-part
  series (Operator's Guide / Masterclass) or any episode of one.
- `references/promo-playbook.md` — read BEFORE any `promo` content type (the
  copywriting-driven commercial for one specific offer).

These files encode the methodology that makes the videos good. If your own
judgment conflicts with a playbook rule, follow the playbook and note the
conflict for the operator. Do not skip steps because they seem obvious.

## Hard rules (violating any of these is a failed run)

1. **No paid services.** No API keys, no SaaS. Adobe Stock only via the
   human-in-the-loop flow (you suggest searches; the operator downloads).
2. **Operator gates are real.** STOP and wait for approval at: Blueprint,
   Script, and Package. Never auto-proceed past a gate.
3. **The GENERATION pipeline never posts to social platforms.** Producing a video ends at
   the project dir + manifest.json. **Two declared exceptions, both operator-invoked and
   both long-standing — this rule does NOT block them** (clarified 2026-08-04, because the
   old flat "never post anywhere" wording contradicted a month of normal practice):
   - **`explainer2 publish`** uploads the finished video to YouTube (OAuth, channel
     `nemock`). Default privacy is `private`; we normally ship `--privacy unlisted` for
     the operator's review. This is standard for every deep dive, not an exception to argue
     about. Altered-content and the pinned comment remain manual browser steps.
   - **`explainer2 promote`** re-shares already-published Shorts via Blotato (PRD N1).

   The rule that still binds: nothing auto-posts, and neither command runs without the
   operator asking for it.
4. **Talk-time rules:** quote `quotes.md` verbatim; adapt positions/anecdotes;
   NEVER fabricate a take, story, or statistic not in the library or the wiki.
5. **Sourced facts only.** Every factual claim in a script traces to the intel
   pull, the research wiki, or the talk-time library. No invented numbers.
6. **Numbers are spelled out in scripts** ("five hundred", not "500") — TTS
   and captions both need words.
7. **The heavy render launches DETACHED; everything else runs foreground.** The
   light media stages (narrate/align/deck) and all other CLI verbs run
   synchronously in the foreground. The one exception is the deep-dive render: it
   exceeds the Bash 10-min cap and a harness-backgrounded encode dies on
   app-suspend, so launch it detached via `bin/explainer2 render` (§7) and check
   progress on re-invocation. Never write a polling loop (global CLAUDE.md shell
   rules).
8. **NEVER edit `script.json` after the operator has recorded it** (added
   2026-08-10, after a near-miss). Forced alignment does not fail on a text/audio
   mismatch — it silently maps the new words onto the old audio and the video
   ships saying the old ones. If a line must change after recording, the segment
   must be RE-RECORDED. `explainer2 media` now enforces this: it refuses to run,
   writes `BLOCKED.md` naming the stale segments, and exits non-zero (§7a).

## Environment

- CLI: `/Volumes/Casima/claudeCode/explainer2/bin/explainer2` (wraps the
  shared `~/myenv` interpreter; never install into that venv).
- Projects: `projects/<date>_<slug>/` under the repo root.
- Talk-time library (operator's voice): pass
  `--library /Volumes/Casima/claudeCode/make_money/talk_time` to `talktime`.

## Content types (canonized 2026-07-06 — pick ONE before scaffolding)

One production system, four canonical types (`src/explainer2/contenttypes.py`
is the registry; `--content-type` on scaffold; recorded in project.json + the
manifest). The media plane is identical for all of them — a type changes which
playbooks you read, the structure/CTA rules, and what `validate` requires in
the package.

| Type | What it is | Extra playbook | Package set |
|---|---|---|---|
| `deepdive` | standalone retention-engineered teaching video (~8–17 min); the default for 16:9 | — | meta + article + linkedin + both thumbs |
| `short` | 9:16 vertical; usually a derived cut, sometimes a standalone run | — | meta only |
| `masterclass` | ONE EPISODE of a multi-part series teaching a large concept in order (15–35 min; episodes build on each other) | `masterclass-playbook.md` | same as deepdive |
| `promo` | a little commercial: direct-response piece for ONE offer/event/book (60 s–3 min, multiple CTAs) | `promo-playbook.md` | meta + linkedin + both thumbs (no article) |

Rules of thumb:
- **Ten standalone ideas = ten deep dives. One large concept split into
  ordered episodes that build on each other = a masterclass-type series.**
- **Branding for `masterclass` follows `--distribution` (2026-07-05 rule):**
  `youtube` (free) → "The Operator's Guide to X"; `paywalled` → "Masterclass".
  The word "masterclass" never appears in a free series' public copy.
- **A teaching video with a CTA at the end is NOT a promo.** `promo` is only
  for videos whose success metric is an action (register/buy/join), and it
  requires `--promotes "<the one offer>"` at scaffold.
- Recognized sub-uses, not separate types: a series/book **trailer** is a
  `promo`; a case study/teardown is a `deepdive` angle.
- Omitted `--content-type` is inferred (16:9 → deepdive, else short), so
  legacy projects and existing routines behave exactly as before.

## Pipeline (follow in order)

### 1. Scaffold
```
bin/explainer2 scaffold "<slug>" --title "<topic>" --aspect 16:9 \
  --content-type <type> --outdir <repo>/projects [--brand <SLUG>]
```
Default 16:9 for deep dives, 9:16 for Shorts-only runs. Masterclass episodes
add `--series/--series-title/--episode/--distribution` and scaffold into the
SERIES root, not `projects/` (masterclass-playbook §3); promos add
`--promotes`. Ask the operator for angle/length/aspect ONLY if not given —
one cheap confirmation, then proceed.

**The canonical number is auto-assigned** from the `projects/` folder (highest
`_NN_` + 1, zero-padded) and written into the dir name + `project.json`; the
scaffold also refreshes the counter line in `channel/CATALOG.md`. So pass a slug
**without** a number (a leading number is stripped if you include one). `--number`
forces a specific number; `--force` allows a duplicate. Run `bin/explainer2 catalog`
anytime to see the derived count, next number, and per-project state — the folder
is the source of truth, never a hand-typed counter.

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
the top-3 finalists' full transcripts). Also read `channel/learn/REPORT.md` —
our own scoreboard (refresh if >7 days stale: `bin/explainer2 learn refresh`
then `learn report`; unattended yt-dlp, no auth) — and let it tiebreak title
ranking per playbook §7. Write `intel/blueprint.md` and
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
COMPEL pass before the booth). **HumanER first (added 2026-07-26):** also read
`~/.claude/skills/humaner/CONSTRAINTS.md` and the "Operator VO script" dial in
`~/.claude/skills/humaner/FORMATS.md` before drafting — the script is written IN
the operator's mined voice from the start (spoken register: And/So starts,
hedged recalled numbers, "right?" check-ins, verdict lines), not voiced after
the fact. Where spoken-humanizer's blocklist conflicts with the voice profile,
CONSTRAINTS.md wins. Stories only from CONSTRAINTS.md Part 3 or talk_time, flags honored.
**Pre-booth gate (added 2026-07-26):** before the booth is opened, the finished
script must pass all four checks: (1) grammar clean; (2) every segment/card is a
complete thought (nothing ends mid-clause or depends on the previous card to
parse); (3) the read-aloud test — read every line aloud, rewrite anything that
trips the tongue, forces a mid-clause breath, or sounds "written"; (4) the
`humaner` skill's LINT.md pass has run on the full script (CONSTRAINTS.md wins conflicts).
A script failing any check does not open the booth. Pull operator takes:
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
or `footage` images) before the full render. **Then run
`python3 tools/deck_census.py <project_dir>` — the visual-variety floor
(motion-playbook §4b, added 2026-07-06 after #18 shipped as a "narrated
PowerPoint"). A FAIL census blocks the render exactly like a failed word
budget blocks the script gate; paste the tally into PLAYBOOK's deck notes.**
No separate operator gate — the deck is seen in the rendered video at the
Package gate.

### 5c. Shorts plan (generation plane — author at the Script stage, BEFORE the booth)
Read `references/shorts-playbook.md`, then author `shorts/plan.json` (3 cuts, each
with a native `hook` + `outro`). This MUST happen before recording, because the
booth surfaces the hook/outro lines as extra cards and the operator records them
in the SAME session as the long-form — a separate retrofit booth pass later is
the failure mode (#11, 2026-06-23). Validate: hooks/outros blocklist-clean
(spoken-humanizer), `hook_accent` ⊂ `hook_headline`, segments in range, and the
hook/outro lines appear NOWHERE in the long-form script (and not the cut's own
body line).
- **Picking up a scaffolded / queued project = the FULL new-video pass, not a
  script-only fix (operator directive 2026-06-22/06-23).** A `record-ready` tag in
  CATALOG is NOT trustworthy — re-evaluate from the gate down: refresh the
  blueprint to current rules, rewrite/restructure the script (new ending rules),
  re-author the deck, AND author the shorts plan — all before the booth, exactly
  as a brand-new video would. The booth pass then records the long-form AND the
  shorts hooks together.

### 6. Record (operator voice) or narrate (Kokoro)
- Operator: launch the booth with **`python3 tools/launch_booth.py <project_dir>`**,
  NOT a bare `bin/explainer2 record` run in a harness background task.
  **HARD RULE (operator directive 2026-06-23, said more than once): the booth is a
  long-lived server and MUST launch DETACHED + caffeinated** — its own session
  (`start_new_session`) under `caffeinate -ims`, exactly like renders (§7). A
  harness-tracked background task DIES when the machine/app suspends while the
  operator is AFK, which silently freezes the booth UI mid-record (the Stop button
  stops responding because its backend is gone). `launch_booth.py` does the detached
  launch, waits for the server to answer, prints READY, and **pops the booth tab
  in the operator's Chrome itself** (2026-07-04: macOS `open -a "Google Chrome"
  <url>`, plain `open` fallback — a fire-and-forget OS handoff, no browser
  automation). Launching the booth IS opening the tab: never tell the operator
  to open the URL by hand, and never reach for browser-control tools just to
  show the booth. Re-running the launcher on an already-open booth re-pops the
  tab (`--no-open` for headless launches). `--stop` takes it down.
  The operator records in the browser; takes save to `voiceover/` as they go (a
  restart never loses recorded takes). When done, `python3 tools/launch_booth.py --stop <project_dir>` — **pass the project.** Bare `--stop` kills EVERY booth in the 8765-8794 pool, which on 2026-09-02 took out an unrelated ig_carousel booth that had been open since 07:23 alongside the one being closed. The scoped form matches on the running `explainer2.cli record <project>` process, so a stale `work/booth_port` cannot point it at somebody else's booth.
  - **Finish signal (operator directive 2026-06-23): right after READY, start the
    waiter as a harness BACKGROUND task** — `python3 tools/launch_booth.py --wait
    <project_dir>` via `run_in_background`. The booth writes `work/record_done.json`
    when the operator clicks the green "Finish & render" button, and the waiter
    returns the instant that file appears — so the harness notifies you that
    recording is done, no polling and no asking. The sentinel is durable: if the
    waiter dies on suspension, re-run `--wait` or just check for the file.
  - Script edits during a session need NO restart (Booth 2.0): the booth
    hot-reloads `script.json` on refresh, and the operator can edit lines
    inline in the booth (writes back to the script with a backup). **An edited
    card that is already recorded must be re-recorded** — the booth stamps each
    take's text (`voiceover/seg_NNN.meta.json`) and the render guard blocks on the
    mismatch (§7a).
  - **After Finish, `script.json` is frozen** (hard rule 8). The Finish sentinel
    carries a digest of the script's spoken content; any later edit is caught by
    the guard and the render refuses to start.
  Then read `work/adlib_report.json` — the booth drift-checks every take live
  and writes the report at Finish (§7b; run `bin/explainer2 adlib` only as the
  fallback for `unchecked` segments). If a segment is flagged `rerecord`, tell
  the operator which and relaunch the booth (`launch_booth.py`). Fix any real
  drift BY HAND (edit the segment, re-run narrate+align) — **do NOT use
  `--apply`** (it overwrites your spelled-out numbers and proper nouns with raw
  ASR; see §7b).
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

### 7a. Script/audio staleness guard (runs first, blocks the render)
Before any stage, `media` checks that every recorded segment's audio still
matches `script.json` (`src/explainer2/media/scriptguard.py`). Two layers: the
booth stamps `voiceover/seg_NNN.meta.json` with a hash of each card's text at
save time, and the mtime of `script.json` versus the newest take is the cheap
pre-check. On a mismatch it writes **`BLOCKED.md`** naming the stale segments
with recorded-vs-current text and **exits non-zero** — no mp4, no
`work/render_complete.json`, so the recording watcher's Phase 2 never publishes.

Why it is a refusal and not a warning: on 2026-08-10 `script.json` was edited
three minutes after the operator clicked Finish, the watcher rendered ninety
seconds later, and align reported "OK, 395 words" while mapping the NEW text onto
the OLD audio. Only a human noticing the render stopped it publishing.

Recovery — move the stale takes aside so the booth asks for them again (audio and
alternate takes are preserved as `seg_NNN.oldtext.bak`), clear the watcher's
locks, relaunch the booth:
```
python3 tools/unstick_stale_script.py <project_dir> --fix --relaunch-booth
```
If the audio is genuinely still correct and only the script's *wording on disk*
changed (numerals spelled out, punctuation), assert that instead of re-recording:
`--accept <ids|all>`. Re-check with `bin/explainer2 media <dir> --recheck` (exit
0/1; deletes `BLOCKED.md` when it passes). `--allow-stale-script` overrides the
guard — the video will then say something other than what the script says.

### 7. Media pipeline
Run the light stages inline, then launch the heavy render **detached**:
```
bin/explainer2 media --only narrate,align <project_dir>   # quick, foreground
bin/explainer2 render <project_dir>                       # detached: remotion render→manifest→qa
```
**Remotion is the default engine** (motion-playbook.md) — `media`/`render`/`shorts`
default to `--engine remotion`, which outputs the final muxed mp4 directly (no
deck/mux stages) and needs the Node toolchain (`npm install` in `remotion/`). Pass
**`--engine deck`** to use the legacy JS deck engine instead (and add `deck` to the
`--only` list, since the deck engine needs `deck.json`/step 5b). Either way the
**deep-dive render runs ~15–25 min**, exceeds the Bash 10-min cap, and dies if the app
suspends — so always split it: light stages inline, then the detached `render`.
Then read the QA warnings in the results
JSON and fix what is fixable (deck pacing, dead air) — at most ONE re-render
cycle.

**Render robustness (learned the hard way on #34, then #10).** A deep-dive
render exceeds the Bash 10-min cap, and a render interrupted mid-encode leaves a
**corrupt `work/video_16x9.mp4` ("moov atom not found")**. The hard lesson (#10,
2026-06-22): a render launched as a child of the Claude session **dies the moment
the desktop app is switched away** — the harness kills the background task
mid-encode. `caffeinate` blocks OS idle-sleep but NOT task termination. So:
- **Launch renders DETACHED — this is the standard path:**
  `bin/explainer2 render <project_dir>`. It runs render→mux→manifest→qa in its
  OWN session (`start_new_session`, the portable macOS `setsid`) under
  `caffeinate`, so suspending/closing Claude Code leaves it running. It returns
  immediately (the render is detached — no completion notification), and is
  idempotent (won't double-encode a project already rendering).
- **Check progress with `bin/explainer2 render-status`** (lock holder + every
  live render + each one's last `run.log` line) or tail `work/run.log`. Do NOT
  write a polling loop — check on re-invocation; global CLAUDE.md rules apply.
- A `render-status` showing `render-lock: engine busy … queued, waiting` is the
  lock **working** (another render is in flight; this one auto-starts after) —
  not a hang. The lockfile *content* is just a note; if its named holder pid is
  dead, the flock is already free.
- **Killing a render: `python3 tools/kill_render.py <project_dir> --fix`, never a
  bare `kill <pid>` (2026-08-10).** A render is a tree — `npm exec remotion
  render` → `node` → the whole `chrome-headless-shell` fleet — and killing the
  parent reaps only the parent. On 2026-08-10 the Phase-1 shell was killed and
  the remotion tree kept rendering, reparented to init, under a lockfile whose
  recorded pid was already dead. `kill_render.py` signals the process GROUP,
  verifies nothing is left, and clears a stale lock note. `explainer2 media` also
  traps SIGTERM/SIGINT/SIGHUP itself now (`childproc.py`) and takes its render
  children down with it.
- If a render died: delete the corrupt `work/video_16x9.mp4`, then re-run
  `bin/explainer2 render <project_dir>` (narrate/align/deck are cheap, cached,
  and idempotent; the render redoes). Verify the final file with `ffprobe`
  (duration present, no moov error) before Package; after any deck fix re-cut
  affected Shorts.

**Concurrent renders are serialized — the render-lock (2026-06-21).** Both this
studio AND v1 `explainer-system` (which the CVG routine uses) acquire a
machine-global `fcntl.flock` on `/tmp/explainer-render.lock` before `render` and
hold it through `mux`, so two projects/routines never run the memory-heavy
capture+encode at once (that collision SIGTERM'd #10 mid-render). You can launch
a render any time — if another is in flight you'll see `render-lock: engine busy
… queued, waiting` in `work/run.log`, and it **auto-starts when the other
finishes** (no manual coordination). flock auto-releases when the holder dies
(even SIGKILL), so a crashed render never deadlocks the queue. Code:
`renderlock.py` in each codebase — the LOCKFILE path MUST stay identical across
both, or they won't see each other. (It's flock-only by design: an earlier
process-sniffing guard false-positived on persistent MCP headless browsers and
deadlocked the queue — never reintroduce that.)

**HARD RULE — never run a raw heavy ffmpeg (2026-06-23).** The lock protects the
render *engine*, but a hand-rolled `ffmpeg` you run yourself (a B-roll motion
splice, the SV-clip splice, any post-mux re-encode) bypasses it unless you make
it take the lock. A bare-ffmpeg B-roll splice on 2026-06-23 overlapped Founder
Tip Tuesday's scheduled render, blew the 16 GB budget, and got OOM-killed
mid-write — the exact collision the lock exists to prevent. So: **route every
heavy encode through `renderlock.run_locked(cmd, label=…)`** (in
`src/explainer2/renderlock.py`) — it acquires the flock, runs the subprocess,
releases on success or failure. Write the splice as a `.py` that calls it
(`sys.path.insert(0, '…/explainer2/src'); from explainer2 import renderlock`).
Two independent requirements, both mandatory (2026-06-23, learned the hard way —
the splice died twice in one afternoon, once per cause):
1. **SERIALIZE** — go through `run_locked` so it never encodes alongside a
   scheduled render (the OOM kill).
2. **SURVIVE** — launch it **DETACHED** (its own session + `caffeinate`, the way
   `launch_detached` starts renders), NOT merely backgrounded via the harness.
   A harness-backgrounded child is killed when the desktop app is suspended; that
   killed the splice, released the lock, and let the scheduled render jump in.
   Launcher pattern: `subprocess.Popen(["/usr/bin/caffeinate","-ims", py, splice],
   start_new_session=True, stdout=open(log,'a'), stderr=STDOUT)`, then check the
   log / output file on re-invocation (don't poll).
No raw `ffmpeg` for an encode, ever, now that the helper exists.

### 7b. Ad-lib drift check (REQUIRED before Package — operator-recorded videos)
The operator records with flexibility: they cut, add, and rephrase live, and that
freedom is intentional. But captions are generated from the recorded script
**snapshot**, so any live deviation leaves captions showing words that weren't
said (or missing words that were).

**The booth now does this check live (2026-07-03 — the standalone stage is
retired as a mandatory step).** Every take gets a whisper drift badge in the
booth, and clicking Finish writes `work/adlib_report.json` from those results —
same schema as the old stage, plus an `"unchecked"` list for any cards whose
in-booth check didn't complete (drift disabled, deferred behind a render, or a
worker error). So before packaging: **read `work/adlib_report.json`**; only if
it's missing or has `unchecked` entries, run the fallback:
```
bin/explainer2 adlib <project_dir>    # FALLBACK only — re-transcribes everything
```
Either way, review per segment (`drift`, `script_text`, `asr_text`) and
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

**RUN THE `humaner` SKILL FIRST, and write ALL reader-facing text inside that one
invocation** (operator directive, restated 2026-08-04). It is a hard requirement with no
exceptions, and never an approximation from memory of CRAFT/VOICE/LINT. The point is not
dodging AI detectors; it is writing better text.

What must go through it: **`article.md`, `linkedin.md`, the `meta.json` `description`, the
`meta.json` `pinned_comment`**, the spoken script, shorts hook/outro lines, and thumbnail
headline words. What need not: tags, chapter titles, slugs, internal notes.

The `description` is the one that gets missed, because `meta.json` looks like metadata. It
is prose on a public page. On #54 the article and linkedin got the pass and the description
and pinned comment did not, purely because meta.json was authored first. **Order fixes it:
invoke the skill, then write every reader-facing artifact in that pass.**

Write titles/description/chapters per blueprint §8 into `meta.json` (the
manifest merges it). **Thumbnails: read `references/thumbnail-playbook.md`, then
build the two 1280×720 cards (a = live, b = promo reuse) (cutout → brand template → `tools/html2png.py`) into
`package/thumbnails/`.**

> **Two keys `publish` actually reads, and neither is the obvious one (2026-08-05).**
> `meta.json` MUST carry:
> ```json
> "category_id": "28",
> "thumbnails": { "a": "thumbnails/thumb_a.png", "b": "thumbnails/thumb_b.png" }
> ```
> `publish.py` reads `meta["category_id"]` and `meta["thumbnails"]["a"]`. It does **not**
> read `"category": "Science & Technology"` — that string is decorative, and a meta.json
> carrying only it uploads into the default category with no custom thumbnail. **#55
> shipped exactly that way**: `thumb_a.png` was built, validated and never sent, and the
> `warnings` array came back empty because the missing-thumbnail check only fired when a
> thumbnail was *declared and absent*, not when none was declared. Paths are relative to
> `package/`. `category_id` is **28 = Science & Technology**, the channel-wide setting as
> of the 2026-08-05 sweep. `publish` now warns on the no-key case, but the warning is a
> backstop — write the keys.
**GATE: present the package. Wait for the operator.**

**ORDER IS LOAD-BEARING: Package must be COMPLETE before `publish` runs.** `publish.py`
attaches `package/thumbnails/thumb_a.png` to the upload itself (see `_thumb_for_upload`) —
nobody does it by hand. It can only attach a file that exists at upload time, so:

> render → shorts → **package (meta + thumbnails + article + linkedin)** → `validate` →
> `publish --fire --privacy unlisted`

Publishing first strands the video with no thumbnail and the dry-run reports
`thumbnail_A: null`. That happened on #54 (2026-08-04). If a package deliverable looks
impossible to produce, **re-read its playbook before reordering the pipeline around it** —
the reorder there was caused by wrongly believing the thumbnail base had to come from the
operator (see thumbnail-playbook §2d).

**Shorts (their own medium — read `references/shorts-playbook.md`).** Shorts are
NOT clips of the long-form: each cut reuses the long-form body audio but gets a
**separately-recorded native hook + outro** (short-form best practices). So the
`shorts/plan.json` (3 cuts, each with `segments` + a `hook`/`hook_headline` + an
`outro`, `ending: "loop"` by default) is authored **at the Script stage**, so the
booth records the hooks in the SAME session: the booth (launched via
`launch_booth.py`, §6) surfaces them as extra cards (saved to
`voiceover/short_<slug>_{hook,outro}.wav`), then
`bin/explainer2 shorts` assembles hook → body → spoken outro per cut — rendered through
the **Remotion motion engine by default** (kinetic hook, synced captions, animated beats;
motion-playbook.md), with `--engine deck` for the legacy deck look. A cut with no
hook/outro falls back to the legacy lift + silent end-card.

### 8b. Article (generation plane — written companion)
Read `references/article-playbook.md` IN FULL, then write the read-not-heard
companion essay to `package/article.md`: the SAME content and arc as the script,
transformed into real written prose (de-spoken, numbers in written style,
subheads, the Reliance Policy as a boxed list). **No new facts** beyond what the
video earned. **HumanER first (added 2026-07-26; this article type is exactly
what got flagged 100% AI on 2026-07-25):** before drafting, read
`~/.claude/skills/humaner/SKILL.md` + `CONSTRAINTS.md` (section 1.10 written register)
+ the Substack dial in `FORMATS.md`, and draft in voice from the start — watch
the seven architecture tells (max one landed line, no coined frameworks or
callbacks, uneven paragraph rhythm, a parked digression, hedged recalled
numbers, verified stories only, no manufactured intimacy). **Then run the
`humaner` skill's LINT.md pass as the mandatory lint — the actual pass, not a
from-memory self-check — and apply its edits except where they conflict with
the voice profile; CONSTRAINTS.md wins conflicts.** Set `humanized: true` in the
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
- **Short.** A few short paragraphs per option, then the video URL, then **3 to 5
  hashtags** (operator directive 2026-08-03, raised from ~3; trim for other
  platforms). This overrides the HumanER LinkedIn dial's "0-3, if any" — that
  dial describes his organic commentary posts, where a hashtag pile reads as
  reach-chasing; a share post for a published video is a different job and 3 to 5
  is the working range.
- **ALL THREE options carry the URL.** Each one is a standalone paste, so each
  needs the link inside it. Do not write "link in the comments" and do not put
  the URL only in the header: the header line is a convenience for the operator,
  not part of what gets pasted.
- **The live URL goes in inline.** If the video isn't public yet, leave a clear
  `<URL>` placeholder and note it; backfill the real link once it's live.
- **Operator voice, not hustle-bro.** Measured, honest, the adult-in-the-room
  take (see the talk-time library + the article). No fabricated claims, no
  numbers the video didn't earn.
- **Draft via the HumanER LinkedIn dial** (`~/.claude/skills/humaner/FORMATS.md`;
  clean register, affirm-then-deposit is for comments — posts open on the hook),
  **then run the `humaner` skill's LINT.md pass** (no em dashes, no clichés, no AI
  tells) — CONSTRAINTS.md wins conflicts.
End with a one-line *Voice note* describing the register, for the operator's
reference. No render gate — it's text, reviewed in place. (Mirror the format of
an existing `package/linkedin.md`, e.g. video #07's.)

### 8d. Package completeness — `validate` enforces it
A complete package is generation-plane deliverables, none produced by a
media stage (so nothing else guarantees they exist — that's how #16 shipped
without `linkedin.md`, 2026-07-04). For a deep dive or masterclass episode
that's FOUR: `package/meta.json` · `package/article.md` · `package/linkedin.md`
· `package/thumbnails/thumb_a.png` + `thumb_b.png` (a = live, b = promo reuse). The set is
per-content-type (promo drops the article; standalone short needs meta only —
`contenttypes.py` is the registry and validate reads it).
**Run `bin/explainer2 validate <project_dir>` at the end of Package and again
before any upload/promo.** It checks the manifest handoff AND the four package
files, and fails with the specific missing path. (It is engine-correct: the
remotion default produces no `deck/index.html`, and validate no longer requires
one.) Treat a non-`ok` validate as a blocker — do not present the package gate
or start an upload until it returns `{"ok": true}`.

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
(5) **thumb_a only. A/B Test & Compare is RETIRED** (operator, 2026-07-26,
re-confirmed 2026-08-20): the channel's per-video volume never reaches
significance, so it buys friction and not information. thumb_b is still built,
as a PROMO asset the operator uses by hand for social and the newsletter. The
2026-06-19 "always A/B, never ask" rule this replaces stayed live here for four
weeks after the decision, because the retirement was recorded in the thumbnail
playbook and nowhere else; (6) visibility is the operator's call — never set
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
exception, 2026-06-20). The caption rewrite (step 2) is a Claude step, so a
human/Claude must always be in the loop — never wire `promote post --fire` into
a dumb cron that reposts without fresh captions. A **scheduled Claude routine is
sanctioned** (decision 2026-06-22): the `explainer2-promote-daily` task fires
8:00 AM ET, and because a scheduled run *is* a Claude instance, it writes fresh
per-platform captions each morning — honoring the in-the-loop rule while keeping
the back catalogue circulating hands-off. Run by hand any time too.

Flow:
1. `bin/explainer2 promote select` → picks the next video + Short. Rotation:
   never-promoted videos first, then least-recently-promoted; within the video,
   the least-recently-posted Short. Override with `--video <slug>` / `--short`.
   Returns the mp4 path, resolved video URL, target platforms, and
   `prior_captions` (the do-not-repeat list).
2. YOU (generation plane) write FRESH captions **inside a `humaner` skill
   invocation** (Skill tool; it owns voice, cadence, and the AI-tell lint — don't
   re-derive them). Per-platform, distinct from `prior_captions` (reword, don't
   shuffle; Reddit/X punish near-dupes). Set `url_comment` for X/Bluesky/Threads —
   it posts as a reply-comment on X and Threads, and inlines into the Bluesky text,
   which is link-only (no media, 300 chars including the URL). Put the URL in the YT
   description and inline in the IG and Facebook captions (neither can
   auto-comment). Write a plan JSON:
   `{video_slug, short_slug, video_url, short_mp4,
   posts:[{platform, caption, url_comment?, extra?}]}` (no `scheduled` field —
   the local post queue owns all timing; `extra` carries
   platform-specific fields — `mediaType:"reel"` for IG and Facebook;
   `title`/`privacyStatus`/`shouldNotifySubscribers`/`isMadeForKids` for YouTube.
   Facebook posts to the FWF Page; its `pageId` is resolved from the routing table,
   so you don't set it in the plan).
3. `bin/explainer2 promote post --plan plan.json` → **dry-run by default**: prints
   the queue spec it would enqueue. Review it (this is the confirm step).
4. `... promote post --plan plan.json --fire` → uploads the mp4 once and hands the
   spec to the LOCAL post queue (`postq.py enqueue` — the dispatcher places the
   posts and `reconcile.py` records live URLs later; nothing publishes at fire
   time), and logs each platform to the ledger so the rotation advances. Direct
   Blotato submission survives only in `post-direct`, the broken-run escape hatch —
   never the normal path (queue cutover 2026-08-08).
5. `bin/explainer2 promote status` / `report` → library promotion state and
   regenerates `PROMOTIONS.md`. Ledger of record: `<projects>/../promotions.json`.

Notes: Blotato key from `BLOTATO_API_KEY` env, else the blotato MCP config —
never hardcode it. **Account and Page ids are never written here or in the plan.**
They resolve from brand `fwf` in the post queue's routing table,
`make_money/post_queue/targets.json`, which is the only place they are allowed to
live — `promote.py` kept its own copy until 2026-08-26 and it went stale. If a post
401s or is held for a disconnected account, fix the row in `targets.json`. A video
must have a
resolvable URL (meta `youtube_url`, else a youtu.be link in meta/PLAYBOOK) AND
cut Shorts to be promotable — `status` flags what isn't (e.g. backfill a missing
`youtube_url`).

## Failure behavior

Any stage fails → report the failed stage, its error, and what you tried. Do
not silently fall back to a different toolchain. Do not switch voices, models,
or services to route around a failure without asking.
