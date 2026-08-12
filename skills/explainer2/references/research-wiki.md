# The research wiki — facts live on disk, with provenance

**Operator directive, 2026-08-12.** Dave asked whether explainer used an atomized wiki
like the other routines. It did not. `explainer-content/research/` held ten directories
from June containing `project.json` and `intel/` and **zero knowledge nodes**. Research
lived in per-project `sources.md` files, which meant a fact verified for #54 was
unavailable to #57, and anything not written down at all lived only in a model's context.

His reasoning, and it is the right one:

> "We need to make sure that we're not just reading information and hoping that memory
> stays intact, because LLMs do have problems with context rot, and so information like
> that can very quickly get lost."

## The rule

**A fact that matters goes to disk the moment it is verified, with its provenance, before
anything is written on top of it.** Not summarized into a paragraph, not held in context
until the script is drafted. Written down as its own node, so the next session — or the
next video — inherits the verification instead of redoing it or, worse, half-remembering
it.

## Where

```
explainer-content/research/<topic-slug>/<claim-slug>.md
```

Topic-scoped, not project-scoped, because the point is reuse across videos. `#57` and any
future Klarna piece read the same nodes. Per-project `research/sources.md` stays — it is
the *argument* for one video, the narrative of what the evidence means. The wiki holds the
*facts*, one per file.

## The node shape

```markdown
---
claim_id: klarna-700-is-an-equivalence
status: VERIFIED at primary | VERIFIED (direct quote, named outlet) | NOT VERIFIED — paywalled | RETRACTED
source: Klarna press release
url: https://www.klarna.com/international/press/...
source_date: 2024-02-27
retrieved: 2026-08-12
tier: PRIMARY | SECONDARY-DIRECT | SECONDARY-SUMMARY | INACCESSIBLE
---

The claim, stated plainly, with the load-bearing wording quoted verbatim.

What it does and does not support.
```

**`tier` is the field that earns its keep.** SECONDARY-SUMMARY means an outlet
summarizing another outlet — the ring of blogs citing each other is how a soft claim
hardens into a fact, and it is what produced the LawGeex number in #52 and nearly
produced a fabricated clone statistic in #55.

## Nodes for things that are NOT true

Write them anyway. Two kinds have already paid for themselves:

- **RETRACTED** — a claim we asserted and then disproved. `#57` has one: I wrote that
  Klarna's reopened roles were "remote, contract-based, targeted at students and rural
  workers," sourced from the blog ring. TechCrunch's direct reporting says no such thing.
  The node exists so nobody reinstates it from a half-memory of the earlier draft.
- **NOT VERIFIED** — a source we could not read. `#57`'s Bloomberg node records a 403 and
  the rule that follows from it: do not air its circulating quotes as Bloomberg quotes.

A wiki that only records wins is a wiki that repeats losses.

## Citing on screen

Same directive: *"we cite our sources, so URLs. We don't have to read them in the script,
but we'll put them at the bottom of the screen."*

Any slide may carry both:

```json
{"id": "s12", "type": "figure", "source": "Klarna press release, 27 Feb 2024",
 "source_url": "https://www.klarna.com/international/press/klarna-ai-assistant-..."}
```

`components/SourceLine.tsx` renders them once at the Video level, so **every** slide type
is covered. It shortens the URL for legibility, caps the band at two lines, and shrinks
the font rather than letting a long URL climb into the caption band. The full link belongs
in the pinned comment; the on-screen line is an attribution, not a clickable target.

**Before 2026-08-12 this was broken in a way nobody would have noticed:** `source` was
mapped by exactly one slide type (`statgrid`) and `source_url` by none, so a citation
authored on a `figure` or `quote` slide was silently dropped at spec-build. #55's deck
carried nine sources; most never reached the screen.

## When to write a node

At the moment of verification, during research — not at script time. The blueprint gate
should be able to point at nodes rather than at a paragraph claiming they exist.
