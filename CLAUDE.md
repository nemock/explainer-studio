# CLAUDE.md — Explainer2

## Operating rules (read first, every session)

1. **Ask, don't assume.** If something is unclear, ask before writing a single line.
2. **Simplest solution first.** No abstractions or flexibility that weren't requested.
3. **Don't touch unrelated code.** Files outside the current task stay untouched.
4. **Flag uncertainty explicitly.** Say so before proceeding.

---

## What this project is

A local-first **explainer-video studio**: YouTube competitive intelligence → retention-engineered script → operator voice → layered visuals → deep dive + Shorts → monetization-ready package. **`PRD.md` is the source of truth.** If this file and the PRD disagree, the PRD wins — and flag it.

**This is NOT v1.** The production v1 lives at `/Volumes/Casima/claudeCode/explainer-system` and is **frozen from this project's perspective: never import from it, never write into it.**

> **One declared exception, operator-approved 2026-08-05: `renderlock.py`.** The
> machine-global render lock is a *shared contract*, not v1 code — every rendering
> codebase on this Mac holds the same `fcntl.flock` on the same fixed path, and a
> participant running an older version of the protocol is exactly how #55 got a corrupt
> master and then starved for 55 minutes. So when the lock protocol changes, v1's copy at
> `explainer-system/src/explainer/renderlock.py` is updated too, along with
> `waveform-studio/renderlock.py` and `daily_beats/capture/renderlock.py`.
> **Port the lock logic surgically; never copy the file wholesale.** v1's
> `launch_detached()` builds its own command line without this repo's engine arguments,
> and overwriting it would break the recording watcher's Phase 1 render for all five booth
> shows plus Circumvent. Replace `acquire()` and the helpers above it; leave
> `launch_detached`, `status`, `_media_pid_for` and `release` alone, then diff
> `launch_detached` against the original to prove it is untouched. The freeze still binds
> everywhere else in that repo. Its proven media core was vendored once into `src/explainer2/` (headers say `VENDORED_FROM` + the v1 commit); divergence here is expected and fine.

**`projects/`, `channel/`, and `research/` are symlinks into a separate private repo.** This repo (`explainer-studio` on GitHub) is **public**. The actual operator content — project dirs, `channel/CATALOG.md`, `promotions.json`/`PROMOTIONS.md`, the research wiki — lives in a private sibling repo, `/Volumes/Casima/claudeCode/explainer-content` (its own independent git repo), and is symlinked in at those three paths (see `.gitignore`'s comment above `/projects`, `/channel`, `/research`). explainer2 is the code; explainer-content is the data. Read/write through the symlinked paths as normal — they resolve transparently, and `bin/explainer2 scaffold --outdir <repo>/projects` already lands in the right place — but never conclude a project doesn't exist just because a fresh clone of explainer2 shows `projects/` as empty or a broken symlink; check `explainer-content` directly.

## Hard constraints (from the PRD — do not violate without asking)

- **Target machine:** Apple **M3, 16 GB unified memory, Metal — no CUDA**. Budget against unified memory; **serialize** memory-heavy stages (never Kokoro + Chrome capture + ffmpeg concurrently).
- **No SaaS subscriptions in the pipeline.** One declared exception: the operator's **stock.adobe.com** membership, human-in-the-loop only (guided searches + watched inbox folder), never an API dependency.
- **LLM = the operator's Claude subscription** (Claude Code / Agent SDK subscription auth). **Never an API key, never per-token billing.**
- **Generation/media split:** Claude touches only generation stages (intel synthesis, research, blueprint, script, packaging copy, QA judgments). The media path (narrate → align → compose → render → mux) is **pure Python, zero LLM calls**, runs unattended.
- **Aligner:** torchaudio forced alignment (Apple-Silicon-native). WhisperX is not viable here.
- **Render correctness:** all motion driven by the JS animation driver under CDP virtual time + seeded RNG. **Raw CSS animations/transitions forbidden on captured elements.**
- **Boundary:** generation only — labeled output dir + versioned `manifest.json` (schema 2.0), then stop. **The generation pipeline never AUTO-posts anywhere.** *Two declared, operator-invoked exceptions — neither runs unless asked, and neither is up for debate at run time:*
  - *`publish` (standard since 2026-07-16): uploads the finished video to YouTube over OAuth, channel `nemock`. Normal call is `--fire --privacy unlisted` for the operator's review. Altered-content and the pinned comment stay manual browser steps.*
  - *`promote` (2026-06-20, PRD N1): re-shares already-published Shorts via Blotato, dry-run by default, tracked in `promotions.json`.*

  *Added 2026-08-04: this bullet previously said "never posts to social platforms" with `promote` as the only exception, which contradicted a month of routine YouTube publishing and left a cold session unsure whether it was allowed to upload.*
- **YouTube intelligence:** `yt-dlp` metadata/transcript analysis for editorial judgment only; competitor media is never republished.

## The playbooks are the brain — read them, follow them

This project is built to be run by ANY Claude model, including ones less
capable than the one that designed it. The analytical methodology is therefore
written down, not assumed:

- **[skills/explainer2/SKILL.md](skills/explainer2/SKILL.md)** — the pipeline procedure, gates, and hard rules.
- **[skills/explainer2/references/blueprint-playbook.md](skills/explainer2/references/blueprint-playbook.md)** — how to turn an intel sweep into a Blueprint (convention extraction, comment mining, the four gap questions, title rules). Read IN FULL before any Blueprint.
- **[skills/explainer2/references/script-playbook.md](skills/explainer2/references/script-playbook.md)** — retention engineering, voice rules, talk-time integration, self-QA checklist. Read IN FULL before any script.
- **[skills/explainer2/references/spoken-humanizer.md](skills/explainer2/references/spoken-humanizer.md)** — the spoken/COMPEL pass for operator-voiced scripts: hook craft, cadence, concreteness, momentum, and the speech-specific clichés general AI-tell lint doesn't catch. General AI-tell removal is covered by the `humaner` skill's LINT.md pass. Read before drafting any operator-voiced script; RUN as a mandatory pass before the booth.
- **[skills/explainer2/references/deck-playbook.md](skills/explainer2/references/deck-playbook.md)** — the visual layer: the slide-type catalog + fields (from the deck engine), the 1:1 script-segment mapping, the `figure`/`footage` image rule, self-QA. Read IN FULL before authoring any `deck.json`. **Required before `media`.**
- **[skills/explainer2/references/thumbnail-playbook.md](skills/explainer2/references/thumbnail-playbook.md)** — the YouTube thumbnail: the brand template (navy radial gradient, red bands, green accent), the cutout pipeline (`cutout.py` / `clean_matte.py`), and the outfit-vs-background separation rule. Read before building thumbnails at Package.
- **[skills/explainer2/references/research-wiki.md](skills/explainer2/references/research-wiki.md)** — facts go to DISK with provenance, one atomized node per claim, the moment they are verified (operator 2026-08-12: context rot means anything held only in a session is already lost). Also the on-screen citation contract: `source` + `source_url` on any slide, rendered by `SourceLine.tsx`.
- **[skills/explainer2/references/article-playbook.md](skills/explainer2/references/article-playbook.md)** — the written companion essay (`package/article.md`): how to transform the spoken script into a read-not-heard article (de-spoken, written number style, subheads, boxed artifacts) without adding facts, and the mandatory `humaner` pass. Read before writing the article, after Package.
- **[skills/explainer2/references/shorts-playbook.md](skills/explainer2/references/shorts-playbook.md)** — Shorts as their own medium: short-form retention best practices (the 0–3s hook, payoff-first, loop outro), cut selection, and the `shorts/plan.json` schema. Each cut gets a **separately-recorded native hook + outro** (the booth records them alongside the main script) — never a bare clip of the long-form. Author the shorts plan at the Script stage.
- **[skills/explainer2/references/masterclass-playbook.md](skills/explainer2/references/masterclass-playbook.md)** — multi-part series (content type `masterclass`): the series-outline gate, episode continuity (entry-point cold opens, light backward references, forward hooks), and the branding rule — `--distribution youtube` brands as "The Operator's Guide to X", `paywalled` as "Masterclass" (2026-07-05 naming decision). Read IN FULL before scaffolding a series or any episode.
- **[skills/explainer2/references/promo-playbook.md](skills/explainer2/references/promo-playbook.md)** — the promotional video (content type `promo`): a direct-response commercial for ONE offer — offer brief, spoken-sales-letter structure, multiple CTAs, and the honesty guardrails (real proof only, no false scarcity). Read IN FULL before any promo.

**Content types are canonical (2026-07-06):** `deepdive` · `short` · `masterclass` · `promo` — registry in `src/explainer2/contenttypes.py`, chosen at scaffold (`--content-type`), recorded in project.json + manifest, and enforced per-type by `validate` (package deliverables). See SKILL.md "Content types" for selection rules.

If your judgment conflicts with a playbook, follow the playbook and flag the
conflict. When you discover a better technique mid-run, propose adding it to
the playbook — the repo, not the session, is where insight accumulates.

## How to run

- CLI: **`bin/explainer2`** (wraps `PYTHONPATH=src ~/myenv/bin/python3.12 -m explainer2.cli`). The shared `~/myenv` venv holds the verified torch/Kokoro/Playwright stack — do not create a new venv without asking.
- Projects land in `projects/<date>_<slug>/` — a symlink into the private `explainer-content` repo, not a plain gitignored local dir (see "What this project is" above). Per-project layout: PRD §10.
- **Media stages run in the foreground EXCEPT the heavy render.** Run the light stages synchronously (`bin/explainer2 media --only narrate,align <dir>`), then launch the deep-dive render **detached** with `bin/explainer2 render <dir>` — it exceeds the Bash 10-min cap and a harness-backgrounded encode dies on app-suspend, and detaching keeps the machine usable instead of locking it up mid-encode. No polling loops (global CLAUDE.md shell rules apply: no loops, no brace expansion, absolute paths). See SKILL §7 for the full render-robustness + render-lock detail. **Rendering defaults to the Remotion motion engine** (motion-playbook.md; needs `npm install` in `remotion/`); pass `--engine deck` for the legacy JS deck engine (then also run the `deck` stage).

### After ANY re-record: align before you render

`bin/explainer2 render <dir>` dispatches **only** `render,mux,manifest,qa`. It does
**not** re-run `align`. So a take re-recorded in the booth after the last align gets
rendered against the previous run's `work/timeline.json`, and the result is a video
whose slides and captions drift from the card onward with the tail cut off. It does not
error: the render succeeds, QA passes, `ready_for_post` comes back true.

```bash
bin/explainer2 media '<dir>' --only narrate,align   # rebuild the timeline FIRST
bin/explainer2 render '<dir>'
```

**`media/timelineguard.py` now enforces this** (2026-08-12, after the Plan to Market
promo nearly shipped desynced). `align` stamps `work/timeline_audio.json` with a
fingerprint of the takes it consumed; any later run that touches a timeline-consuming
stage without re-aligning recomputes that fingerprint, and on a mismatch writes
`BLOCKED-TIMELINE.md` and exits non-zero so nothing downstream publishes. Runs that
include `align` are never blocked. Override with `--allow-stale-timeline` /
`EXPLAINER_ALLOW_STALE_TIMELINE=1`, which you almost never want.

This is the **audio** counterpart to `media/scriptguard.py`, which guards the **text**.
Scriptguard could not catch this: the operator recorded exactly the current words, so
the text agreed perfectly while the audio changed underneath.

## Decisions already made (don't relitigate without asking)

- GUI = local FastAPI + plain HTML/JS at localhost ("Mission Control"), opened in Chrome. No Electron/Tauri in v2.0. Every GUI action has a CLI twin.
- v1's deck engine, themes, brand/CTA, talk-time reader, recorder, and deepdive orchestrator are carried forward as the foundation; v2 features layer on top per the PRD's phases.
- Phase order: 0 skeleton → 1 Intelligence → 2 retention scripting + booth → 3 compositor + Adobe Stock assist → 4 Mission Control → 5 dual-format + packaging + Learn.
