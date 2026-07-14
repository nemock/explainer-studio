# Magnific / image-gen — optional in-studio capability (plan + guardrails)

**Status:** scoped 2026-07-14, config wired, awaiting tool introspection.
**Owner decision source:** operator (Dave), 2026-07-14 session.

This is the build spec + standing policy for adding an **optional** AI image-generation
capability to explainer-studio via the operator's paid **Magnific** MCP. Written down
because the enabling step (authorize the MCP) requires an explainer2 session restart,
which drops the originating conversation's context. Resume from here.

## The north star (non-negotiable)

The studio must **fully function with zero outside services.** Image-gen is an
*optional enhancement*, used only when the MCP is present, with graceful fallback to
the current flow (operator pastes prompts into an external generator / Adobe Stock).
It is the **second** declared subscription exception, exactly parallel to
stock.adobe.com: human-in-the-loop, **never an API dependency**. This must be written
into `PRD.md`'s hard constraints when the integration lands.

## Style + disclosure policy (operator directive 2026-07-14) — the core guardrail

- **In-video AI imagery: STYLIZED ONLY.** Paper-cutout / **layered sheets of paper**
  (the operator's favorite animation style), cartoon, or other clearly-stylized
  artistic approaches. **NEVER photo-realistic or otherwise deceptive images or video
  inside the video.** The test: could a viewer mistake it for real footage/photos? If
  yes, it's out.
- **Deterministic motion.** Generated elements are stylized *stills/cutouts*; all
  movement is composited and animated **deterministically in Remotion** (Vox-style
  layered scenes: locked background + midground + foreground cutouts). No generative
  *video*.
- **Thumbnails: photo-real AI bases are allowed** (per Magnific's current ToS and
  existing practice — thumbnail bases were already AI-composed). This is unchanged.
- **AI-disclosure discipline stays honest.** Stylized in-video art is not deceptive
  synthetic media, but the moment AI imagery appears *inside* the video the
  `ai_generated_visuals` story changes from today's "deterministic Remotion only."
  Decide the exact `meta.json` flag semantics + the manual YouTube altered-content
  answer when building; keep it truthful. See memory
  [[youtube-altered-content-disclosure-manual]].

## Two use cases

1. **In-video illustrations & cutouts (stylized)** — paper/cutout/cartoon scene assets
   (backgrounds, foreground props, halftone/paper character cutouts) for the deck when
   a topic wants illustrated storytelling. Lives in the **deck-authoring** generation
   stage.
2. **Thumbnail bases, incl. selfie-as-base** — upload a `dave_selfies/*.png` as the base
   and generate scene variations. Lives in the **thumbnail/package** stage. Claude still
   composes the brand headline on top (thumbnail-playbook §2c).

## Wardrobe rule (operator directive 2026-07-14)

When restyling a selfie base: **default to the hoodie / no-hoodie sweatshirt motif** —
it's becoming Dave's recognizable visual brand and makes him stand out from the scene.
Restyle thematically only when the topic clearly earns it (the P.T. Barnum tux, #35).
Keep Dave recognizable regardless.

## Architecture (mirror the Adobe Stock assist)

- Model it on `src/explainer2/stockassist.py` + `assets/` (the proven optional
  human-in-the-loop asset source). New assist: `assets/imagegen` (or extend assets).
- **Generation stages only** (Claude-in-the-loop: deck author, thumbnail/package).
  NEVER the deterministic, unattended media plane (narrate→align→compose→render→mux).
- **Availability detection:** the capability activates only if the `mcp__magnific__*`
  tools are present in the session; otherwise the playbooks' existing operator-paste /
  Adobe Stock fallback is used, unchanged.
- Likely OAuth-gated + interactive → expect it visible in interactive explainer2
  terminal sessions, absent in headless/scheduled runs. That's fine: it's a
  generation-stage enhancement, not a media-pipeline dependency.

## Config already done (2026-07-14)

- Added `magnific` (`{type: http, url: https://mcp.magnific.com}`) to the **explainer2**
  project scope in `~/.claude.json` (it was previously only at the
  `/Volumes/Casima/claudeCode` workspace-root scope, invisible to explainer2 sessions).
- Backup: `~/.claude.json.bak-magnific`.

## NEXT (resume here after restart + OAuth authorize)

1. Confirm `mcp__magnific__*` tools are visible; **introspect the real tool surface** —
   names, params, whether it does image-to-image from an uploaded selfie, output format
   (URL vs bytes), styling controls. Do NOT guess tool names before this.
2. Build `assets/imagegen` assist mirroring `stockassist.py` (optional, graceful
   fallback).
3. Add "optional image-gen" sections to **deck-playbook** (stylized in-video elements,
   layered-paper style) and **thumbnail-playbook** (selfie-as-base + wardrobe rule).
4. Write the **PRD** second-exception into hard constraints (optional, human-in-loop,
   never an API dependency).
5. Nail the **AI-disclosure policy** wording (`meta.json` flag + manual YouTube step).
