# CLAUDE.md — Explainer2

## Operating rules (read first, every session)

1. **Ask, don't assume.** If something is unclear, ask before writing a single line.
2. **Simplest solution first.** No abstractions or flexibility that weren't requested.
3. **Don't touch unrelated code.** Files outside the current task stay untouched.
4. **Flag uncertainty explicitly.** Say so before proceeding.

---

## What this project is

A local-first **explainer-video studio**: YouTube competitive intelligence → retention-engineered script → operator voice → layered visuals → deep dive + Shorts → monetization-ready package. **`PRD.md` is the source of truth.** If this file and the PRD disagree, the PRD wins — and flag it.

**This is NOT v1.** The production v1 lives at `/Volumes/Casima/claudeCode/explainer-system` and is **frozen from this project's perspective: never import from it, never write into it.** Its proven media core was vendored once into `src/explainer2/` (headers say `VENDORED_FROM` + the v1 commit); divergence here is expected and fine.

## Hard constraints (from the PRD — do not violate without asking)

- **Target machine:** Apple **M3, 16 GB unified memory, Metal — no CUDA**. Budget against unified memory; **serialize** memory-heavy stages (never Kokoro + Chrome capture + ffmpeg concurrently).
- **No SaaS subscriptions in the pipeline.** One declared exception: the operator's **stock.adobe.com** membership, human-in-the-loop only (guided searches + watched inbox folder), never an API dependency.
- **LLM = the operator's Claude subscription** (Claude Code / Agent SDK subscription auth). **Never an API key, never per-token billing.**
- **Generation/media split:** Claude touches only generation stages (intel synthesis, research, blueprint, script, packaging copy, QA judgments). The media path (narrate → align → compose → render → mux) is **pure Python, zero LLM calls**, runs unattended.
- **Aligner:** torchaudio forced alignment (Apple-Silicon-native). WhisperX is not viable here.
- **Render correctness:** all motion driven by the JS animation driver under CDP virtual time + seeded RNG. **Raw CSS animations/transitions forbidden on captured elements.**
- **Boundary:** generation only — labeled output dir + versioned `manifest.json` (schema 2.0), then stop. **The generation pipeline never posts to social platforms.** *One declared exception (2026-06-20, PRD N1): the operator-invoked `promote` command re-shares already-published Shorts directly via Blotato (dry-run by default, `--fire` to publish), tracked in `promotions.json`. Producing a video still stops at the package.*
- **YouTube intelligence:** `yt-dlp` metadata/transcript analysis for editorial judgment only; competitor media is never republished.

## The playbooks are the brain — read them, follow them

This project is built to be run by ANY Claude model, including ones less
capable than the one that designed it. The analytical methodology is therefore
written down, not assumed:

- **[skills/explainer2/SKILL.md](skills/explainer2/SKILL.md)** — the pipeline procedure, gates, and hard rules.
- **[skills/explainer2/references/blueprint-playbook.md](skills/explainer2/references/blueprint-playbook.md)** — how to turn an intel sweep into a Blueprint (convention extraction, comment mining, the four gap questions, title rules). Read IN FULL before any Blueprint.
- **[skills/explainer2/references/script-playbook.md](skills/explainer2/references/script-playbook.md)** — retention engineering, voice rules, talk-time integration, self-QA checklist. Read IN FULL before any script.
- **[skills/explainer2/references/spoken-humanizer.md](skills/explainer2/references/spoken-humanizer.md)** — the spoken counterpart to the written Humanizer skill: CUT (spoken-cliché blocklist) + COMPEL (hook craft, cadence, concreteness, momentum). Read before drafting any operator-voiced script; RUN as a mandatory pass before the booth.
- **[skills/explainer2/references/deck-playbook.md](skills/explainer2/references/deck-playbook.md)** — the visual layer: the slide-type catalog + fields (from the deck engine), the 1:1 script-segment mapping, the `figure`/`footage` image rule, self-QA. Read IN FULL before authoring any `deck.json`. **Required before `media`.**
- **[skills/explainer2/references/thumbnail-playbook.md](skills/explainer2/references/thumbnail-playbook.md)** — the YouTube thumbnail: the brand template (navy radial gradient, red bands, green accent), the cutout pipeline (`cutout.py` / `clean_matte.py`), and the outfit-vs-background separation rule. Read before building thumbnails at Package.
- **[skills/explainer2/references/article-playbook.md](skills/explainer2/references/article-playbook.md)** — the written companion essay (`package/article.md`): how to transform the spoken script into a read-not-heard article (de-spoken, written number style, subheads, boxed artifacts) without adding facts, and the mandatory Humanizer pass. Read before writing the article, after Package.
- **[skills/explainer2/references/shorts-playbook.md](skills/explainer2/references/shorts-playbook.md)** — Shorts as their own medium: short-form retention best practices (the 0–3s hook, payoff-first, loop outro), cut selection, and the `shorts/plan.json` schema. Each cut gets a **separately-recorded native hook + outro** (the booth records them alongside the main script) — never a bare clip of the long-form. Author the shorts plan at the Script stage.

If your judgment conflicts with a playbook, follow the playbook and flag the
conflict. When you discover a better technique mid-run, propose adding it to
the playbook — the repo, not the session, is where insight accumulates.

## How to run

- CLI: **`bin/explainer2`** (wraps `PYTHONPATH=src ~/myenv/bin/python3.12 -m explainer2.cli`). The shared `~/myenv` venv holds the verified torch/Kokoro/Playwright stack — do not create a new venv without asking.
- Projects land in `projects/<date>_<slug>/` (gitignored). Per-project layout: PRD §10.
- The `media` command is **synchronous — run it in the foreground and let it finish.** No polling, no backgrounding (global CLAUDE.md shell rules apply: no loops, no brace expansion, absolute paths).

## Decisions already made (don't relitigate without asking)

- GUI = local FastAPI + plain HTML/JS at localhost ("Mission Control"), opened in Chrome. No Electron/Tauri in v2.0. Every GUI action has a CLI twin.
- v1's deck engine, themes, brand/CTA, talk-time reader, recorder, and deepdive orchestrator are carried forward as the foundation; v2 features layer on top per the PRD's phases.
- Phase order: 0 skeleton → 1 Intelligence → 2 retention scripting + booth → 3 compositor + Adobe Stock assist → 4 Mission Control → 5 dual-format + packaging + Learn.
