# Deck Playbook — how to author deck.json (the visual layer)

Follow as a procedure. The deck is `deck.json`. The media pipeline's **`deck`
stage** (`src/explainer2/deckbuild.py`) builds a standalone `deck/index.html`
from it and the fixed theme; `render` then captures that HTML under CDP virtual
time. **You (the generation plane) author `deck.json` — never raw HTML.** The
engine is data-driven: you pick a slide `type` and supply its fields, and the
JS animation driver renders + animates it deterministically. Authoring HTML, or
raw CSS animation, breaks the determinism contract (see CLAUDE.md hard rules).

`media` **requires** `deck.json` — without it the `deck` stage fails with
`FileNotFoundError`. So the deck is authored as a normal build step, right after
the Script gate. It is NOT auto-generated.

---

## 0. The contract (read once)

- **One slide per script segment.** `deck.json.slides[i].id` MUST equal the
  `slide` field of the corresponding `script.json` segment (`s01`, `s02`, … —
  contiguous, in order). The renderer aligns spoken words to the slide of the
  segment being read; a missing or misnumbered slide desyncs the whole video.
- **On-screen text is terse, not the spoken sentence.** The narration carries
  the sentence; the slide carries the *idea*. Kicker = 2–5 word context label;
  headline = a punchy phrase; accents = 1–3 emphasis words.
- **Numbers may be digits on slides** ("$500M", "10 kt", "93%") — unlike the
  script, where they're spelled out for TTS/captions. Keep them faithful to the
  script/wiki; never invent a number for a slide.
- Top level: `{ "title": <video title>, "slides": [ … ] }`.

## 1. Inputs (gather before authoring)

1. The approved `intel/blueprint.md` — **§6 Structure & retention-map skeleton**
   (the beats table names the intended visual *device* per beat and the midroll
   seam) and **§5 hook**, **§7 thumbnail direction**, **§3 visual budget**
   (which scenes are `visual: footage`). The deck realizes this plan.
2. `script.json` — read every segment's `text` (what's spoken over the slide),
   `beat` (chapter label → good `kicker`/`title` source), and `device` (the
   retention cue → guides the slide type; see §3).
3. The research wiki / intel for any number or quote that lands on a slide.

## 2. The slide-type catalog (authoritative — from `assets/deck_engine.js`)

Every slide also accepts these **common optional fields**: `kicker` (top
label), `title` (a McKinsey-style action/"so-what" line above the visual;
honors `accent`/`accent2`), `subkicker` (a line under the content), `source`
(citation pinned bottom-left), and `transition` (`rise` (default) / `fade` /
`pop` / `slide`; `punch` defaults to `pop`).

`accent` / `accent2` are arrays of **words that appear in the headline/title**;
the engine highlights matching tokens (indigo / secondary). They must be
substrings of the text they accent or nothing highlights.

### Text slides (the workhorses)
- **`statement` / `hook` / `payoff`** *(and any unlisted type)* → the default
  renderer: `headline` (+ `accent`, `accent2`). The type name is semantic only
  (it tags the slide) — these render identically. Use `hook` for the cold open,
  `payoff` for the closing card, `statement` for talky transitional beats.
- **`highlight`** → `headline` + `mark` (array of words to wrap in a marker
  highlight). For the one "aha" line you want to pop.
- **`build`** → `headline` + `accent`/`accent2`, rendered word-by-word.
- **`punch`** → one big word: `word` (falls back to `headline`), `kind`
  (`good`→accent / `bad`→accent2). For the biggest energy beat (often the
  midroll seam).
- **`reframe`** → `before` + `strike` (struck-through) + `after`. "X → Y".
- **`quote`** → `quote` (falls back to `headline`) + `attribution`. For verbatim
  lines (e.g. a book quote). Put the attribution as the source.
- **`define`** → `term` + `definition`.
- **`list`** → `items` (array of strings; auto-numbered). Promise stacks,
  recaps, "screenshot this" checklists.
- **`steps`** → `steps` (array of strings, or `{title, text}`); numbered process.

### Data-viz slides (only with a real, sourced number)
- **`stat`** → `value` + `label`. One hero number.
- **`statgrid`** → `stats[]` of `{value, label}`.
- **`progress`** / **`ring`** → `value` (0–100) + `label` (bar / dial).
- **`pictograph`** → `filled` + `total` + `kind` + `label` (X-of-Y dots).
- **`trend`** → `points[]` + `end_label` + `kind` (sparkline).
- **`ranked`** → `bars[]` of `{label, value, display?, kind?(muted|bad)}`.
- **`diagram`** → `bars[]` of `{value, label, kind?(muted|bad)}` (bar chart).
- **`delta`** → `from`/`from_label` → `to`/`to_label` + `kind` + `change` badge.
- **`waterfall`** → `start{label,value}` / `steps[]{label,value,kind}` / `end{}`.
- **`timeline`** → `events[]` of `{date, label}`.
- **`matrix`** → `x_axis[lo,hi]`, `y_axis[lo,hi]`, `points[]{x,y,label,kind}` (2×2).
- **`compare`** → `left{title,value,kind}` vs `right{title,value,kind}`.

### Media slides — REQUIRE a real image on disk (see §4)
- **`figure`** → `image` (path, **must exist**) + `caption`. A framed still /
  artifact (a screenshot of an authored HTML artifact, a chart, etc.).
- **`footage`** → `image` (path, **must exist**) + `headline`/`accent` overlay.
  Full-bleed licensed B-roll with deterministic Ken Burns drift.
- **`cta`** → brand-driven (pulls `DECK.brand.product/logo/cta.*`); needs brand
  config. **For a normal closing card use `payoff`, not `cta`,** unless a brand
  with a `cta` block is wired up.

## 3. Mapping segment `device` → slide type (a starting heuristic)

`cold_open` → `hook` · `thesis`/`statement` → `statement` · `promise_stack` →
`list` · `credibility` → `statement` · `re_hook` → `statement`/`highlight`/`punch`
· `midroll_seam` → `punch` or `reframe` (the energy peak) · a cited number →
`stat`/`statgrid`/`delta` · a verbatim line → `quote` · a named process →
`steps`/`list` · `payoff` → `highlight`/`payoff` · `cta` → `payoff`.

Vary the visual mode at least every 3–4 slides (the script-playbook's
pattern-interrupt rule is satisfied in the deck): don't run six `statement`s in
a row — break them with a `stat`, `list`, `quote`, or `punch`.

## 4. The image rule (the deck's one true footgun)

`figure` and `footage` emit an `<img src="…">`. **If that file doesn't exist,
the render captures a broken image.** So:

- Only use `figure`/`footage` when the image actually exists in the project:
  a licensed Adobe-Stock still ingested via the `assets` flow (lands under
  `assets/…`), or an authored artifact PNG under `sources/artifacts/` (author
  an HTML artifact, then `python3 tools/html2png.py …` — see the shipped
  examples like `sources/artifacts/calendar.png`).
- If you have no asset yet, render the idea as a **text type** (`list`,
  `statement`, `stat`, `quote`) — a "screenshot this" card is perfectly served
  by a `list`. Don't point at an image you haven't created.
- Every `footage` scene must still read with its headline as a fallback, and
  per SKILL §6b the scene keeps a deck-slide fallback so render proceeds either
  way.

## 5. Validate before the full render

Run the deck stage alone — it's fast and catches bad fields / missing images
without the long render:
```
bin/explainer2 deck <project_dir>     # → {"slides": N, "deck_html": "deck/index.html"}
```
Then a structural check (Python): `deck.json` is valid JSON; `len(slides)` ==
segment count; every `slides[i].id` equals the i-th script segment's `slide`;
every `accent`/`accent2`/`mark` token is a substring of its headline/title; no
`figure`/`footage` points at a missing file.

## 6. Self-QA checklist (run before handing the deck to `media`)

- [ ] One slide per script segment; ids contiguous `s01…sNN` and matched to the
      script in order.
- [ ] Slide 0 = `hook` (the cold open); closing card = `payoff` (or `cta` only
      if brand is wired).
- [ ] On-screen text is terse — no slide dumps the full spoken sentence.
- [ ] Every `accent`/`accent2`/`mark` word actually appears in its headline/title.
- [ ] Numbers on slides trace to the script/wiki; none invented; illustrative
      figures are labeled as such (a `delta.change` note, a caption).
- [ ] No `figure`/`footage` without an existing image; otherwise a text type.
- [ ] Visual mode changes at least every 3–4 slides; the midroll seam gets the
      strongest visual.
- [ ] `bin/explainer2 deck <dir>` renders with no error.

The deck has no separate operator gate — the operator sees it in the rendered
video at the Package gate. But a deck that fails §6 fails review.
