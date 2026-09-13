# Booth finish without a session waiter — plan (2026-09-13)

**Status: Phase A IMPLEMENTED 2026-09-13** (operator: "go ahead with Phase A, retire
the waiter … we don't need to hold on to artifacts that don't work the way we
intended"). Change record: `make_money/routine_changes/2026-09-13-booth-waiter-retired.md`.
Deviations from the plan as written: A2 has no `work/on_finish.cmd` hook (not needed
until Phase B), the origin file is `work/booth_origin.json` (`booth_session.json` was
already the booth's wrap report), and A5 (reaper gate) was dropped because `--wait`
now refuses inside a session, so there is no waiter tree to spare.

**Phase B IMPLEMENTED 2026-09-13** (operator: "Proceed with Phase B"). Change record:
`make_money/routine_changes/2026-09-13-studio-joins-the-recording-watcher.md`. As built:
`run_studio()` in the watcher, `--profile studio` in `phase1_render.py`, the
`explainer-studio` entry in shows.json (`ignore_hours: true`, candidates by Finish-sentinel
mtime under `project_globs`), `work/RESUME.md` + notification + deep link at render end.
B3 (auto-resume via `claude --resume -p`) deliberately NOT built. Phase C docs done with A and B.

## 1. What is actually happening

The explainer2 SKILL (§6, operator directive 2026-06-23) arms a harness background
task right after the booth launches:

    python3 tools/launch_booth.py --wait <project_dir>     # run_in_background

That waiter sleeps until `work/record_done.json` appears. Two things kill it, and
neither reports an error to the session.

### Killer 1: the session reaper (the "lately")

`~/.claude/reaper/session_reaper.py` (rewritten 2026-08-26, launchd
`com.brg.session-reaper`, every 15 min) SIGTERMs then SIGKILLs the **entire process
tree** of any desktop-session CLI that is

- older than 90 min, and
- whose transcript file has not been written for 45 min, and
- whose subtree burned under 15 s of CPU in a 60 s window.

A session sitting on a booth waiter is exactly that profile: the transcript goes
quiet the moment the operator walks to the mic, and the waiter is a sleeping Python
process. Verified today that a harness background task runs as a `zsh` child of the
session's CLI pid (pid 9702 under CLI 7965), so the tree kill takes it.

Reaper log, Sep 9–13, kills of the two interactive sessions that had booths open:

| Killed at | Session | Quiet | Note |
|---|---|---|---|
| 2026-09-10 10:23 | 46b08bfa (make_money) | 88 min | |
| 2026-09-10 18:01 | 46b08bfa | 57 min | waiter armed 12:56 reported "stopped … previous session" at 15:03 |
| 2026-09-11 16:37 | 0b54d84c (explainer2) | 48 min | waiter armed 16:31, six minutes earlier |
| 2026-09-12 16:42 | 0b54d84c and 46b08bfa | 103 / 77 min | |
| 2026-09-13 11:33 | 46b08bfa | 58 min | |

203 kills since 2026-08-25 in total. The reaper doc from 2026-08-20 says interactive
sessions can never match; the 2026-08-26 rewrite dropped that gate when it switched
to transcript mtime, and the 2026-08-26 routine-change doc records the operator
choosing that option. The reaper's CPU safety net was written for renders (heavy
CPU) and cannot see a waiter (zero CPU).

The desktop app respawns the session process when the operator next types, so the
conversation is not lost. Only the waiter is: the harness then reports
"Background shell command didn't finish before the previous session ended" (seen
2026-09-13 15:55) or "No completion record was found … from the previous session"
(2026-09-10 15:03, 2026-07-22 13:16).

### Killer 2: app quits, updates, and restarts

Same effect as above, no reaper involved. Any in-session waiter is a child of a
process the desktop app is free to end.

### Two bugs in `wait()` itself (tools/launch_booth.py)

- It exits 2 ("booth exited WITHOUT a finish marker") when **no booth in the whole
  pool** is listening for one 5-second tick. A scoped `--stop` + relaunch to fix a
  card opens that gap. Seen 2026-07-03 (exit 2 at 23:18, re-armed by hand).
- Hard 6-hour cap (exit 3, seen 2026-07-21). A long day at the mic hits it.

### Delivery history since June (all project dirs, 60 waiters)

Roughly two-thirds delivered a completion. The rest: "killed / was stopped" (11),
"NO NOTIFICATION EVER" (18, the session ended, compacted, or was re-armed first),
"stopped … previous session" (3), exit 2 (1), exit 3 (1). The signal was never
lost, because `record_done.json` is durable, but the *session* had to be told by
the operator every time the waiter died.

## 2. Why the session should not be the waiter at all

The PRD's generation/media split already says it: waiting for a file is media-side
work, pure Python, zero LLM. The machine already runs one such waiter for free:
`com.brg.recording-watcher` (`tools/recording_watcher.py`, launchd, every 5 min,
config `make_money/recording_watcher/shows.json`) polls `launch_booth.py --status`
for six shows, launches the detached render when a recording is DONE, and only
spawns a Claude process at the very end. **explainer2 deep dives, masterclass
episodes, and promos are not in that config**, so the studio pipeline fell back to
the one mechanism that dies with the session.

The design goal restated: **nothing about the session needs to survive the
recording**. The booth (detached, caffeinated) and launchd carry the wait. The
session ends its turn after launching the booth and is resumed, by the operator or
by a deep link, when the machine has something for it to do.

## 3. The plan

### Phase A — stop the bleeding (one sitting, no behavior change for the six shows)

**A1. SKILL §6: retire the in-session waiter.** After READY, the session tells the
operator what happens at Finish and **ends its turn**. No `--wait`, no polling, no
`ScheduleWakeup`. On resume it runs `launch_booth.py --status` once (instant,
durable). **DECISION NEEDED:** this reverses the 2026-06-23 directive "start the
waiter as a harness background task right after READY". The directive's intent
(get notified, never poll, never ask) is kept by A2 + B1 below.

**A2. Booth-side Finish hook (recorder.py, zero tokens).** The booth process is
alive exactly until Finish, so it is the right thing to fire the signal. On the
Finish click, after writing `record_done.json` and `adlib_report.json`:

- post a macOS notification via `osascript` ("Recording finished: <title>.
  <N> cards, <M> flagged. Session <name> is ready to resume.") — same pattern the
  watcher already uses for `notify_render_blocked_once`;
- if `work/on_finish.cmd` exists, run it detached (`start_new_session`) and log
  the pid to `work/booth_exit.json`. The launcher writes that file (A3); the
  recorder never decides what goes in it.

**A3. Launcher records the originating session (launch_booth.py).** The session's
shell exports `CLAUDE_CODE_SESSION_ID` (verified today; this session's value
matches its transcript basename `c53291c3-…`). At launch, write
`work/booth_session.json` = `{session_id, cwd, launched_at, title}`. This is the
only piece of state the resume path needs, and it costs nothing.

**A4. Fix `wait()` for the manual/fallback case.** Keep the command, but:
identify *this* project's booth (`_booth_project(port)` already exists) instead of
"any port in the pool"; on a gap, re-check for `booth_exit.json` with
`reason: finished` before giving up; raise the cap to 12 h or drop it. Small diff,
worth doing because `--wait` stays the right tool from a plain terminal.

**A5. Reaper: spare a tree that holds a live booth waiter.** One extra gate in
`session_reaper.py`: skip any candidate whose subtree command lines contain
`launch_booth.py --wait`. Cheap insurance for the transition and for any other
long-lived background task an interactive session legitimately parks. This does
not fix the studio flow on its own (Killer 2 remains), which is why A1 comes first.

### Phase B — the studio joins the launchd watcher (zero tokens until resume)

**B1. New show family in `shows.json`: `mode: "studio"`.** Candidates =
`/Volumes/Casima/claudeCode/explainer-content/projects` (dir names already match
`DATE_RE`), plus the masterclass/promo series dirs the operator names; lookback
3 days. "Published" marker for the scan: `manifest.json` in the project root with
`ready_for_post: true`, or `SKIPPED.md`; deep dives never write `README.md`, so
the existing test would rescan them forever.

Per cycle, on `--status` = DONE:

1. Run the same guards the six shows get for free: `media --recheck`
   (scriptguard), render-blocked and crash-loop backoff, the global render cap.
2. Read `work/adlib_report.json`. If any segment is `rerecord`, do **not** render:
   notify once ("card 14, 27 need a re-record"), write `work/READY-FOR-OPERATOR.md`,
   and stop. This is the one judgment the session used to make after the waiter
   fired, and it is a JSON read.
3. Otherwise launch Phase 1 detached: a studio variant of `phase1_render.py`
   whose verbs are `media --only narrate,align` then the in-process render chain
   (verify that a bare `explainer2 media <dir>` runs narrate → align → render →
   mux → manifest → qa under the render lock; if not, run `media --only
   narrate,align` then `render` and wait on `work/render_complete.json`). Same
   process-group reaping as the existing driver.
4. **No Phase 2 `claude -p` spawn.** Instead write `work/RESUME.md` (what was
   rendered, QA warnings, the next SKILL step, the originating session name) and
   post the notification. Tokens are spent only when the operator resumes.

**B2. Resume ergonomics.** The notification names the session. The desktop app
registers deep links (found in the app bundle today):
`claude://code/continue?session=<id>` and `claude://resume?session=<uuid>`. The
finish/render notification can carry an `open` of that URL so one click lands the
operator in the right session. Verify by hand with this session's id before
relying on it; the fallback is the session name in the notification text.

**B3. Optional, off by default: auto-resume.** `resume_session: true` in the show
entry makes the watcher, after Phase 1, run
`claude --resume <session_id> -p "<RESUME.md>"` detached, so the *same
conversation* continues unattended into QA and Package. Costs tokens once, at the
real event, with the conversation prefix cached. **Unverified risk:** a headless
resume and the desktop app both append to one transcript; the app may not show the
new turns until reopened. Test on a scratch session before turning it on for real
work. Until then the default is B1 step 4: notify and wait for a human.

### Phase C — docs and memory

- `skills/explainer2/SKILL.md` §6 rewritten (A1), §7 note that Phase 1 may already
  have run and `work/RESUME.md` is the handoff.
- `make_money/routine_changes/<date>-booth-finish-leaves-the-session.md` (rule 5).
- Memory: `booth-launches-detached` gains "the waiter is gone; the watcher owns
  the wait; the session ends its turn at READY".
- `recording-watcher-zero-token` memory updated with the studio family.

## 4. What stays zero-token, and what does not

| Step | Who runs it | Tokens |
|---|---|---|
| Waiting for Finish | booth process + launchd watcher | 0 |
| Finish notification, `on_finish.cmd` | booth (recorder.py) | 0 |
| adlib re-record check | watcher (JSON read) | 0 |
| narrate, align, render, mux, manifest, qa | Phase 1 driver, detached | 0 |
| RESUME.md + notification + deep link | watcher | 0 |
| QA judgment, Package, publish | the resumed session | yes, once |
| Optional auto-resume (B3) | `claude --resume -p` | yes, once, opt-in |

## 5. Verification checklist before calling any phase done

- Arm a booth on a scratch project, walk away 100 min, confirm the session tree is
  reaped (or spared under A5) **and** Finish still produces the notification and
  `RESUME.md` with no session alive.
- Scoped `--stop` + relaunch mid-recording: `record_done.json` from the second
  booth is the one the watcher acts on (the launcher already clears the stale one).
- `--status` on resume returns DONE with the digest the scriptguard expects.
- Six existing shows: watcher log shows no change in their branch (the studio
  family is additive; `mode` defaults to the current behavior when absent).
- Deep link: `open "claude://code/continue?session=<this session id>"` brings the
  session forward.

## 6. Out of scope, noticed on the way

`monday-medtech` project `2026-09-07_medtech-2026-09-07` has been RENDER-BLOCKED
for 23 consecutive Phase 1 launches (`handoff exited 1`); the watcher logs it every
five minutes and nothing publishes. Separate fix.
