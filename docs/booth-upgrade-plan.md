# Recording Booth 2.0 — implementation plan (approved direction 2026-07-03)

The operator approved the full enhancement slate for the recording booth and asked
that the v1-based daily skills (Founder Tip Tuesday, MedTech Mondays, daily shorts,
daily IG carousel where voice applies) adopt the same booth. This doc is the build
plan: five batches, each one working session, in build order. The repo is the
source of truth for this plan; check batches off as they land.

**Current state:** `src/explainer2/recorder.py` + `assets/recorder.html` — card
list, per-card MediaRecorder record/stop, header waveform meter, take archiving
(`seg_NNN.takeK.wav`), ~150wpm read-time estimates, fixed port 8765 (mic-grant
origin), detached launch + `record_done.json` sentinel via `tools/launch_booth.py`.
v1 (`explainer-system`, FROZEN) has the same recorder lineage plus
`recordlock.py` (`record-open` detached launcher) — FTT's routine already
mandates booth recording.

**Hard constraints throughout:**
- v1 is frozen: no imports from, no writes into `explainer-system`. Adoption
  happens at the ROUTINE level (skills call explainer2's booth), never by
  patching v1.
- M3 / 16 GB: any whisper work in-booth is serialized (one transcription at a
  time) and skipped while a render holds `/tmp/explainer-render.lock`.
- Fixed port 8765 stays (Chrome scopes the mic grant to the exact origin). One
  booth machine-wide at a time — same philosophy as the render lock.
- Booth launches stay detached + caffeinated (`launch_booth.py`), never
  harness-tracked background tasks.

---

## Batch 1 — Flow: Focus Mode + hot reload/inline edit  ✅ LANDED 2026-07-03

Built + server-side smoke-tested (segments/edit/reload/backup round-trips, JS
parse-checked). Live acceptance: the #40 recording session. Note: in Focus Mode
the header waveform meter is covered by the fullscreen view — the REC dot +
elapsed clock stand in until Batch 5's big waveform.

The session-changers. Files: `recorder.py`, `assets/recorder.html`.

1. **Focus Mode (teleprompter).** One card at a time, full-screen, huge type
   (the card list remains as an overview; `Tab` toggles views).
   Keyboard loop: `Space` = 3-2-1 countdown then record; `Space` again = stop;
   `P` = play the take; `Enter` = keep & auto-advance; `R` = retake;
   `←/→` = navigate cards. Countdown prevents clipped first words; auto-advance
   turns a 27-card session into one continuous rhythm.
2. **Hot reload.** `GET /segments` re-reads `script.json` from disk on every
   call (seg_list becomes a function, not a startup snapshot) + a "Reload
   script" button. Closes the observed pain: editing a card mid-session
   currently requires a booth restart.
3. **Inline edit.** Pencil icon on a card → edit the text in place →
   `POST /edit?seg=N` writes back to `script.json` (timestamped `.bak` first),
   card shows an "edited" chip. The operator finds tongue-twisters first; the
   fix should happen where he finds them.

Acceptance: record the next video (#39 or #40) entirely in Focus Mode; at least
one inline edit round-trips to script.json without a restart.

## Batch 2 — Quality gates: take QC + room tone + WPM + wrap report

Catch bad audio in the booth, not at render QA. Files: `recorder.py` (analysis
on `/save` — ffmpeg/ffprobe astats), `recorder.html` (badges).

4. **Instant take QC.** After each save, analyze the WAV: peak dBFS / clip
   count, mean RMS (too quiet?), rough noise floor, duration vs the ~150wpm
   estimate ("48s recorded, ~32s expected"). Return with the save response;
   card gets a green/amber/red chip with reasons. Amber/red suggests retake
   while the operator is still in the chair.
5. **Room-tone check at session start.** One-time 3s silence capture: warn if
   the noise floor is high (fan/HVAC); save `voiceover/roomtone.wav` for
   future cleanup use.
6. **Live WPM meter** while recording (card word count vs elapsed, vs the
   operator's measured ~154wpm).
7. **Session wrap report on Finish.** `work/booth_session.json` — takes,
   retake rate, total record time, QC flags — surfaced on the done screen and
   available for the project PLAYBOOK.

## Batch 3 — Share it: standalone booth + daily-skill adoption

Do this BEFORE the remaining feature batches so every later improvement lands
once and benefits all channels (FWF deep dives + FTT + MedTech Mondays + any
voiced short).

8. **Generalize the booth core.** `tools/launch_booth.py` (and `recorder.run`)
   accept any project dir with `script.json` + `voiceover/` — schema-tolerant:
   v2 `script/2` (beat/device/note, shorts plan cards) and v1 `script/1`
   (id/slide/text only) both render; optional fields degrade gracefully. No
   imports from v1 — a small generic loader reads the common layout directly.
9. **Discovery audit.** Enumerate the v1-based routines (Founder Tip Tuesday,
   MedTech Mondays, daily shorts, daily IG carousel) and record per routine:
   operator-voiced (adopts the booth) vs Kokoro/no-audio (no change). FTT is
   confirmed operator-voiced (its 2026-07-01 routine change mandates a booth).
10. **Adopt per routine.** Each voiced routine's record step switches from v1's
    `record-open` to `explainer2` booth launch (absolute-path invocation,
    global shell rules). v1 untouched. Each change gets a doc in
    `make_money/routine_changes/` (standing rule) + the skill's SKILL.md
    updated. Verify one live FTT run end-to-end before flipping the rest.

## Batch 4 — The ear: per-take drift + take manager + continuity

11. **Per-take drift badge.** On save, queue mlx_whisper transcription in a
    serialized worker (skip + mark "pending" if a render holds the render
    lock). Badge: green "matches script" / amber "ad-libbed — N% drift, view
    diff" with an inline word-level diff. Decide keep-vs-retake in the moment;
    "keep" can push the spoken text into script.json via the Batch-1 edit path
    (same rules as the adlib stage: recognizer noise ≠ drift).
12. **Take manager.** Drawer per card: list `takeK` files, play any,
    `POST /promote` to restore an older take as primary (current becomes a new
    take). Makes retakes risk-free.
13. **Continuity playback.** One key (`C`): play the last ~3s of the previous
    card, roll straight into the countdown. Tone/energy matching for
    out-of-order retakes.

## Batch 5 — Stagecraft: slide previews + on-air ambiance + mic picker

14. **Slide preview per card.** At booth launch, if `deck.json` exists,
    pre-render per-slide PNG thumbs (existing deckbuild + html2png path);
    show the slide beside the text in both views. The midroll punch card
    should LOOK like the energy peak in the booth too.
15. **On-air ambiance.** Recording state: dim everything but the active card,
    large live waveform behind the text, red edge glow + "ON AIR" lamp.
    Cosmetic, but mood shows up in the read.
16. **Mic picker + level calibration.** Input-device dropdown (USB vs
    built-in) + a calibration bar at session start.

---

## Sequencing rationale

1 → 2 → 3 → 4 → 5. Batches 1–2 are the highest-value and purely local to two
files. Batch 3 early so 4–5 are built once for every channel. Batch 4 leans on
existing whisper plumbing (adlib stage). Batch 5 is polish and can trail.

## Risks / notes

- **Mic permission:** all new endpoints stay same-origin on 8765; the grant is
  unaffected. MediaRecorder path unchanged.
- **RAM:** whisper serialized; QC (ffprobe/astats) is negligible. Never run
  drift transcription while a render is active.
- **Unattended safety:** the booth remains operator-invoked; automated
  (Kokoro/no-voice) routines never open one.
- **Testing:** extend `tools/simulate_takes.py` to drive the new endpoints
  (save-with-QC, edit, promote) for regression runs without a human.
