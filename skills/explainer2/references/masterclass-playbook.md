# Masterclass Playbook — multi-part series (Operator's Guide / Masterclass)

Read this IN FULL before scaffolding a series or any episode of one. It layers
ON TOP of the normal pipeline: every episode still gets the blueprint, script,
spoken-humanizer, deck/motion, shorts, and package treatment. This playbook
covers what a SERIES changes.

The reference implementation is **The Operator's Guide to ISO 14971**
(`/Volumes/Casima/claudeCode/ISO_14971_Masterclass/` — read its CLAUDE.md for
the precedents cited below).

---

## 0. What this content type is (and is not)

A masterclass-type project is ONE EPISODE of a multi-part series that teaches a
large concept in order. Episodes build on each other: module six assumes module
three happened. That is the structural difference from a deep dive — ten deep
dives are ten standalone stories; ten episodes are one curriculum.

Consequences:
- The unit of editorial judgment is the SERIES, not the episode. The gap
  analysis, the audience definition, and the brand promise are decided once, at
  the series outline (§2), and every episode inherits them.
- Episodes are longer and deeper than deep dives — tutorial pacing, real
  artifacts, worked examples. Typical: 15–35 minutes vs. the deep dive's 8–17.
  Density rules still apply; longer means more substance, never more padding.
- The series is a completion machine: the goal is a viewer who watches module
  one and finishes module twelve. Retention engineering therefore includes
  EPISODE-TO-EPISODE retention (§4), not just within-video retention.

## 1. Branding rule — Operator's Guide vs. Masterclass (2026-07-05, binding)

The word **"Masterclass" is reserved for PAID content**. The same production
published free on YouTube is branded **"The Operator's Guide to X"**. This was
decided 2026-07-05 when the ISO 14971 series was renamed, and it is why the
internal content type is `masterclass` while most series will publicly be
Operator's Guides.

In the tooling: scaffold with `--distribution youtube` (default) or
`--distribution paywalled`; the CLI derives `series.brand_label` — use that
label in titles, playlist names, on-screen copy, and spoken script.

Hard rules:
- `distribution: youtube` → the word "masterclass" NEVER appears in titles,
  playlist names, thumbnails, on-screen copy, or the spoken script. It may
  survive as an SEO keyword in tags/description metadata only.
- `distribution: paywalled` → brand as "Masterclass"; it never publishes to
  YouTube, and its package carries no subscribe/comment CTAs (§6).
- Free series follow the brand pattern *The Operator's Guide to X* so the
  family reads as a family (ISO 14971 → quality control → cybersecurity →
  IEC 62304/62366 were the planned siblings).
- A free series is deliberately OUTSIDE the sales funnel: never gate it, price
  it, or attach a hard sales CTA. A soft one-line site CTA is the ceiling.

## 2. The series outline — a gate BEFORE episode one

A series begins with `outline.md` at the series root, and the outline is an
operator gate exactly like a blueprint. Never scaffold episode one until the
outline is approved.

The outline must contain:
1. **The large concept and the transformation.** What can the viewer DO after
   finishing that they couldn't before? One paragraph. If the transformation
   fits in one video, it's a deep dive, not a series.
2. **The audience and their starting point** — what episode one may assume,
   stated explicitly, because every later episode inherits it.
3. **The episode ladder** — 8–15 episodes, each with: working title, the ONE
   question that episode answers, what it builds on (episode numbers), and the
   artifact or capability the viewer leaves with. Order by dependency
   (foundation → build), not by topic taxonomy. If an episode doesn't depend
   on any earlier one and nothing depends on it, ask whether it's really a
   deep dive wearing a badge.
4. **Series-level intel.** Run ONE full intel sweep on the umbrella topic
   (blueprint-playbook §1–§6 at series altitude): who else teaches this
   end-to-end, where their series loses people, and the gap OUR series owns.
   Cite it in the outline.
5. **Distribution + brand** (§1), decided once, recorded at the top.

## 3. Scaffolding an episode

```
bin/explainer2 scaffold "<episode-slug>" --content-type masterclass \
  --series "<series-slug>" --series-title "<public series title>" \
  --episode <n> --episodes-total <N> --distribution youtube \
  --aspect 16:9 --voice-source operator --outdir <series-root>
```

- **The series root is the series' own directory, not the channel `projects/`
  dir** (ISO precedent: modules never land in the BRG projects collection).
  Rename the scaffolded dated dir to `module-NN/` right after scaffold —
  before any other work — so the series reads as a curriculum on disk.
- Set the series' standing `project.json` flags in the SAME sitting, per the
  series decision recorded in its CLAUDE.md (ISO sets `"sting": false,
  "cta_book": false` to suppress cross-brand FWF branding). An episode
  rendered with the wrong brand sting is a re-render.
- The `series` block (slug/title/episode/distribution/brand_label) is written
  by the scaffold and flows into the manifest — downstream tools and the
  operator can always tell an episode from a deep dive.

## 4. Per-episode pipeline deltas

Everything in SKILL.md still applies (intel per episode — the sweep-first rule
has no series exception; blueprint; script + spoken-humanizer; shorts plan
before the booth; validate). On top of that:

1. **Blueprint inherits the outline.** The episode blueprint does not re-decide
   the audience, the gap, or the ordering — it implements this episode's rung
   of the ladder. Its intel sweep is scoped to the episode's question (who
   teaches THIS sub-topic well, what do their comments ask for).
2. **Every episode is an entry point.** YouTube will hand a stranger module
   six first. The cold open must work with zero prior episodes: hook on this
   episode's question, then ONE orientation line ("this is part six of the
   Operator's Guide to X — it stands on its own, and the full series is in the
   description"). Never open with a recap.
3. **Reference backward with a light touch.** "In module three we built the
   risk matrix — here's where it earns its keep" is good: it rewards the
   loyal viewer and advertises the back catalogue to the newcomer. A re-teach
   of module three is not. One or two callbacks per episode, each one line.
4. **Hook forward at the end.** The ending rule changes from the deep dive's:
   after the last substantive beat, the next-to-last beat is the NEXT-EPISODE
   hook — open a real loop the next module closes ("the matrix works until
   production drift breaks it; module seven is where we fix that"). Then the
   comment-CTA, then one clean CTA, stop. Still no recap, no "thanks for
   watching", no end-signaling.
5. **Consistency is a retention device.** Same structure rhythm, same visual
   vocabulary, same episode-badge placement across the series. A returning
   viewer should feel the format snap into place. Record series-standing
   decisions (accent color, thumbnail layout, structure quirks) in the series
   CLAUDE.md the first time they're made; never re-decide per episode.

## 5. Length and depth

Confirm the target minutes at the outline (per series), not per episode.
Tutorial pacing earns length only through artifacts: worked examples, real
documents, on-screen walkthroughs — things a viewer pauses on. The word-budget
math and self-QA of the script-playbook apply unchanged; a 25-minute episode
at ~150 wpm is ~3,750 words, and every one of them still has to earn its seat.

## 6. Packaging deltas

- **Titles:** episode value first, series brand after — "Your Risk Matrix Is
  Lying to You | Operator's Guide to ISO 14971 #6", not "Episode 6: Risk
  Matrices". The title must sell the episode to a stranger; the series tag
  sells the playlist to the convinced.
- **Thumbnails:** same cutout treatment + layout across the set, with a
  visible episode number; series accent color may override the channel default
  (thumbnail-playbook series rules — a standing series decision, decided once).
- **Description:** the series index (playlist link + episode list) appears in
  every episode's description. Chapters as usual.
- **Playlist is mandatory** and is the series' public spine on YouTube.
- **Paywalled distribution:** the package still ends at the project dir —
  the studio never uploads anywhere, paid platforms included. No subscribe or
  comment CTAs in the script; the forward hook (§4.4) points at the next
  lesson, and course navigation replaces the CTA stack.
- Package deliverables are the deep-dive set (meta.json, article.md,
  linkedin.md, A/B thumbnails) — `validate` enforces them per content type.

## 7. Self-QA (before any episode's script gate)

- [ ] Series outline exists, is approved, and this episode matches its rung
      (question, dependencies, artifact)
- [ ] Brand label matches distribution (§1) — grep the script and meta for
      "masterclass" on a youtube-distribution series
- [ ] Cold open works for a stranger; orientation is ≤ 1 line; no recap open
- [ ] Backward references ≤ 2, one line each; forward hook opens a loop the
      next episode really closes
- [ ] Series-standing visual/structure decisions honored (check the series
      CLAUDE.md), episode badge on thumbnails
- [ ] Everything in script-playbook §6 and spoken-humanizer — unchanged and
      mandatory
