# Magnific / image-gen — optional in-studio capability (PROVEN + built)

**Status:** scoped 2026-07-14; **end-to-end flow PROVEN 2026-07-14** (both use cases,
real generations); playbooks + PRD exception + assist landed 2026-07-14.
**Owner decision source:** operator (Dave), 2026-07-14 session.

Optional AI image-generation via the operator's paid **Magnific** MCP (Claude Desktop
OAuth connector; tools surface as `mcp__magnific__*`). Optional enhancement, never
required.

## The north star (non-negotiable)

The studio must **fully function with zero outside services.** Image-gen is optional,
used only when the `mcp__magnific__*` tools are present, with graceful fallback to the
current flow (operator pastes prompts into an external generator / Adobe Stock). It is
the **second** declared subscription exception, parallel to stock.adobe.com:
human-in-the-loop, **never an API dependency** (PRD §1, hardened 2026-07-14).

## Style + disclosure policy (operator directive 2026-07-14) — the core guardrail

- **In-video AI imagery: STYLIZED ONLY.** Paper-cutout / **layered sheets of paper**
  (operator's favorite; validated), cartoon, or other clearly-stylized art. **NEVER
  photo-realistic or deceptive images/video inside the video.** Test: could a viewer
  mistake it for real footage/photos? If yes, it's out.
- **Deterministic motion.** Generated elements are stylized stills/cutouts; all motion
  is composited + animated **deterministically in Remotion** (Vox-style layered scenes).
  No generative video inside our videos.
- **Thumbnails: photo-real AI bases ARE allowed** (Magnific ToS + existing practice).
- **AI-disclosure discipline stays honest.** See "AI-disclosure policy" below and
  memory [[youtube-altered-content-disclosure-manual]].

## Model choice — GPT 2 is the default (validated head-to-head 2026-07-14)

- **GPT 2** (`gpt-2`): **15 credits**/16:9 image. Best composition, legible detail,
  strong likeness. **Default for thumbnail bases AND stylized elements.**
- **Nano Banana Pro** (`imagen-nano-banana-2`): **75 credits** (5×). FALLBACK only when
  GPT 2's likeness slips. (Recraft `recraft-v4-1` is a fast style-only alt; no image ref.)
- Run **`simulate_cost`** (free, read-only) before every paid call.

## The proven flow (exact tool sequence)

1. **Cost check (free):** `simulate_cost {tool:"images_generate", arguments:{…same args…}}`.
2. **Upload a local file (e.g. a selfie):**
   a. `creations_request_upload {mimeType:"image/png"}` → `proxyUploadUrl` + `path`.
   b. Shell PUT the bytes (NOT via MCP):
      `python3 tools/imagegen.py put <localfile> "<proxyUploadUrl>"`
      (or raw `curl -sS -X PUT -H "Content-Type: image/png" --data-binary "@<file>" "<url>"`).
      Don't re-PUT a failed target — request a fresh one.
   c. `creations_finalize_upload {path:"<path>"}` → `{identifier, status:"completed"}`.
      (For a PUBLIC url, one-step: `creations_upload_image {url}`.)
3. **Generate:** `images_generate {prompt, mode:"gpt-2", aspectRatio:"16:9", count:1,
   references:[{type:"image", identifier:"<selfie-id>"}]}` → queued creation ids.
   (No `references` = pure text-to-image, e.g. stylized elements.) Output is OPAQUE.
4. **Wait:** `creations_wait {identifiers:[…], timeoutSeconds:25}`, re-poll until
   `status:"completed"`; read `results.results.url`.
5. **Download + record provenance:**
   `python3 tools/imagegen.py fetch "<url>" <out.png> --project <dir> --model gpt-2 --prompt "…" [--in-video]`
   (writes the PNG and appends a record to `<project>/assets/imagegen/provenance.json`).
6. **Cutout (in-video elements needing transparency):** `images_remove_background
   {creationIdentifier:"<id>"}` → wait + fetch the transparent PNG.

## Wardrobe rule (operator directive 2026-07-14)

Restyling a selfie base: **default to the hoodie / no-hoodie sweatshirt motif** (Dave's
recognizable brand; stands out from the scene). Thematic restyle only when the topic
clearly earns it (the P.T. Barnum tux, #35). Keep Dave recognizable.

## AI-disclosure policy (decided 2026-07-14)

`meta.json.ai_disclosure` records what's true:
- **Thumbnail-only AI** (base image AI, video motion deterministic): `ai_generated_visuals:
  false`, note that the thumbnail base is AI-composed but the VIDEO isn't synthetic.
  YouTube altered-content answer: **No** (unchanged from today).
- **AI imagery INSIDE the video** (stylized elements): set `ai_generated_visuals: true`
  with `synthetic: false` and a note: "stylized (non-photoreal) AI illustrations,
  animated deterministically; no realistic depiction of real people/events." This is
  NOT deceptive synthetic media, so YouTube's altered/synthetic-content answer stays
  **No** — that question targets realistic content that could mislead. Keep the note
  honest and specific. When unsure, describe what was generated and ask the operator.
- `tools/imagegen.py disclosure --project <dir>` reads `provenance.json` and prints
  whether any `in_video: true` AI assets exist, so packaging sets the flag correctly.

## Environment gotcha — shell Full Disk Access (cost real time 2026-07-14)

The MCP tools run app-side, but the local-file **PUT** and result **download** are
shell/curl ops. The shell helper needs macOS **Full Disk Access** to read
`/Volumes/Casima` and TCC-protected home folders (Downloads/Documents/Desktop). Missing
→ `curl`/`cp`/`git` return "Operation not permitted". Fix: grant FDA to the Claude Code
shell helper, then **restart the session** (long-lived shell caches the grant at
launch). No-FDA fallback: stage files at home ROOT (`/Users/davesaunders/…`, not
Downloads) or `/private/tmp`. Resolved for this machine 2026-07-14 (FDA + restart).

## Where it's wired

- **thumbnail-playbook.md §2d** — optional Magnific selfie-as-base (GPT 2 default).
- **deck-playbook.md §4d** — optional stylized in-video elements (paper/cutout/cartoon).
- **PRD.md §1** — the second declared exception.
- **tools/imagegen.py** — `put` / `fetch` (+ provenance) / `disclosure` helper.
- Config: Magnific added to Claude Desktop as an OAuth connector; resolve tools via
  ToolSearch "magnific" each session. (Stale `magnific` HTTP entry in explainer2's
  `~/.claude.json` scope is superseded; backup `~/.claude.json.bak-magnific`.)
