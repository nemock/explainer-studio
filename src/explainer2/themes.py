# VENDORED_FROM: nemock/video-explainer-system @ d593aa41dc32d04e3b714b4731b1763f6e31843e (src/explainer/themes.py) — copied 2026-06-10; diverges freely (v1 is frozen).
"""Theme family (PRD §8.5) — named presets so a channel produces a *family* of
looks, not one. Each theme = palette + a motion personality (the default per-slide
intro transition). A slide can override with its own `transition`."""

THEMES = {
    "midnight": {"bg": "#0b1020", "fg": "#f5f7ff", "accent": "#5b8cff", "accent2": "#ff7a59", "motion": "rise"},
    "paper":    {"bg": "#f5f2ea", "fg": "#1b1b2a", "accent": "#d8432f", "accent2": "#2a7de1", "motion": "fade"},
    "sunset":   {"bg": "#1a1020", "fg": "#fff4ee", "accent": "#ff7a59", "accent2": "#ffd166", "motion": "pop"},
    "forest":   {"bg": "#0c1a14", "fg": "#eafff4", "accent": "#3ddc84", "accent2": "#ffd166", "motion": "rise"},
    "mono":     {"bg": "#101012", "fg": "#fafafa", "accent": "#f5d90a", "accent2": "#9aa0a6", "motion": "slide"},
    # BRG MedTech: cream bg, navy text, teal accent (+ warm-rust accent2 for caution/contrast).
    # Pair with a brand whose logo reads on cream (e.g. the navy-gradient BRG mark).
    "medtech":  {"bg": "#f5f0eb", "fg": "#1b2b4b", "accent": "#0d7377", "accent2": "#c2410c", "motion": "fade"},
    # BRG Founder Tip Tuesday: deep-forest bg, parchment text, brass accent (+ clay accent2).
    # The established FTT identity (forest #1E3A2F / brass #C9A24A / parchment #F0E8D2).
    # Pair with a brand whose logo reads on forest (the BRGFTT brand). NOT the neon-green
    # `forest` theme above. Fraunces display + Inter body via the optional `fonts` field.
    "founder":  {"bg": "#1E3A2F", "fg": "#F0E8D2", "accent": "#C9A24A", "accent2": "#B5654A", "motion": "fade",
                 "fonts": {"display": "Fraunces", "body": "Inter"}},
    # Founders Who Finish (deep-dive long-form): flat deep-purple bg + grain/vignette,
    # white text, ONE indigo accent (accent2 == accent so no off-brand red ever leaks).
    # Montserrat 800 Condensed in the kit -> bundled as Archivo variable (wght+wdth) which
    # has a real width axis; the condensed cut + ALL-CAPS titles / sentence-case body live in
    # the `[data-theme="fwf"]` block of deck.css. `ambient:false` kills the drifting accent
    # glow (the kit forbids gradients except the vignette). Pair with the FFW brand.
    "fwf":      {"bg": "#36185B", "fg": "#FFFFFF", "accent": "#757BBD", "accent2": "#757BBD", "motion": "fade",
                 "ambient": False, "fonts": {"display": "Archivo", "body": "Archivo"}},
    # --- Remotion-engine paper channels (2026-07-15). The Remotion engine keys its brand
    # off the theme STRING (Video.tsx / remotion_engine.py); these palette values exist so
    # scaffold accepts the theme and the legacy deck engine (if ever run) has sane colors.
    # nemock-deep-dive = Dave Saunders deep dives (cream paper, dark-ink, green accent).
    "nemock-deep-dive": {"bg": "#f4ecd6", "fg": "#2c1e4e", "accent": "#3ddc84", "accent2": "#3ddc84", "motion": "fade"},
    # cut-bond = Cut & Bond channel (cream paper, warm ink, coral/teal accents).
    "cut-bond": {"bg": "#f4ecd6", "fg": "#2a2622", "accent": "#ff5a4d", "accent2": "#17b7a6", "motion": "fade"},
    # brg-paper = Base Reality Group papercraft promos (Plan to Market cohort, etc.). A
    # DEDICATED paper theme so BRG marketing videos carry the exact site palette (cream
    # #F5F0EB / navy #1B2B4B / teal #0D7377) WITHOUT overwriting the nemock-deep-dive or
    # cut-bond paper worlds. Added 2026-07-21. Fraunces display + Inter body match the BRG
    # brand system. NOTE (blast radius): the Remotion paper engine currently hardcodes the
    # green/purple paper palette in ink.tsx + the Paper* components; full navy/teal ink
    # threading is a separate, render-verified engine change (see the promo project's
    # theme-plan.md). The papercraft LOOK itself comes from the generated image assets,
    # which are authored in the BRG palette regardless of the ink layer.
    "brg-paper": {"bg": "#f5f0eb", "fg": "#1b2b4b", "accent": "#0d7377", "accent2": "#c2410c",
                  "motion": "fade", "fonts": {"display": "Fraunces", "body": "Inter"}},
    # brg-deep-dive = the Base Reality Group DEEP-DIVE series (fractional-CPO / product &
    # business teaching videos; baserealitygroup.com, never the book/newsletter CTA). Its own
    # palette so the series can be papercraft WITHOUT repainting either neighbour: `brg-paper`
    # is already rendering the Plan to Market cohort promo, and `nemock-deep-dive` is Dave's
    # personal/book channel (davesaunders.net). Same BRG cream+navy, but the accent is BRG
    # INDIGO (#7b5bff — the accent the series' thumbnails already use) rather than the promo
    # world's teal. accent2 == accent so no off-brand colour can leak (same trick as `fwf`).
    # Paired in the engine with BRGPaperSting (BRG's own mark) + a book-less paper CTA.
    # Added 2026-07-26 per the operator's "give BRG its own style palette" directive.
    "brg-deep-dive": {"bg": "#f5f0eb", "fg": "#1b2b4b", "accent": "#7b5bff", "accent2": "#7b5bff",
                      "motion": "fade", "fonts": {"display": "Fraunces", "body": "Inter"}},
    # wte-guide = The Operator's Guide to Waste-to-Fuel Process Safety (nemock channel,
    # /Volumes/Casima/claudeCode/WTE_Operators_Guide). BRG cream+navy paper-craft like its
    # brg-* neighbours, teal accent, but its OWN key because its branding differs from both:
    # like-and-subscribe-only CTA (no book, no site) on Dave's personal channel. NOTE: engine
    # pairing (isPaperTheme + ink palette + CTA end card, remotion/src) is a pre-render TODO
    # tracked in that project's CLAUDE.md — do not render wte-guide before it ships.
    "wte-guide": {"bg": "#f5f0eb", "fg": "#1b2b4b", "accent": "#0d7377", "accent2": "#c2410c",
                  "motion": "fade", "fonts": {"display": "Fraunces", "body": "Inter"}},
    # plg-guide = The Operator's Guide to Product Leadership (twelve-part head-of-product /
    # CPO teaching series, /Volumes/Casima/claudeCode/Product_Leadership_Operators_Guide).
    # BRG cream+navy paper like its siblings; accent is RUST/TERRACOTTA (#a8481f, operator
    # 2026-08-11). Its own key for a reason worth restating: this series teaches the SAME
    # subject as the BRG deep-dive series but is a different product — free, ungated,
    # like-and-subscribe, outside the sales funnel. Sharing brg-deep-dive's indigo would
    # make two different things read as one. accent2 == accent so no off-brand colour can
    # leak (same trick as `fwf`). CTA is like-and-subscribe ONLY: no book, no spoken site.
    "plg-guide": {"bg": "#f5f0eb", "fg": "#1b2b4b", "accent": "#a8481f", "accent2": "#a8481f",
                  "motion": "fade", "fonts": {"display": "Fraunces", "body": "Inter"}},
    # circumvent = Circumvent Global marketing + explainer videos (circumventglobal.com).
    # NOT part of Dave's personal brand and NOT a BRG property: its own key so the Circumvent
    # program can be papercraft without repainting any neighbour. Added 2026-07-30 per the
    # operator's "create a Circumvent marketing color scheme" directive.
    #
    # Palette rationale (see the Circumvent Marketing project's PALETTE.md):
    #   bg  #f2ede0 — warm kraft cream. Earthier than the BRG/nemock creams so the two paper
    #                 worlds read as different brands on the same substrate.
    #   fg  #1c3a29 — deep forest-green ink. Extends the #14532D already used in Circumvent's
    #                 investor materials. Green INK (not navy/purple) is what distinguishes
    #                 this world at a glance.
    #   accent  #c89b3c — wheat/harvest gold. Deliberate: green alone reads "environmental
    #                 advocacy", which is the wrong register for the agricultural and energy
    #                 audience this brand sells to. Green + harvest gold reads farm, grain and
    #                 refinery instead.
    #   accent2 #2f7d4f — field green, for process/positive/growth marks.
    "circumvent": {"bg": "#f2ede0", "fg": "#1c3a29", "accent": "#c89b3c", "accent2": "#2f7d4f",
                   "motion": "fade", "fonts": {"display": "Fraunces", "body": "Inter"}},
    # --- Hue-assigned weekly-show palettes (locked 2026-08-06; see
    # make_money/routine_changes/2026-08-06-video-brand-system-palettes-locked.md). Background
    # hue is the show identifier in a feed grid: tangerine Mon, steel-blue Tue, goldenrod Wed,
    # indigo Thu, brick-red Fri (the daily keeps `fwf` violet; Circumvent keeps `circumvent`).
    # These REPLACE medtech/founder/paper/midnight/mono for new renders per show, but the old
    # keys stay untouched for the v1 back catalog. NOTE (blast radius, same doctrine as
    # wte-guide): engine pairing (papercraft ink tokens + scene family) and each palette's
    # Magnific substrate set are pre-render TODOs — do not render a show on its new key before
    # both ship.
    # mmt-tangerine = Monday MedTech. Clinical teal brightened to aqua so it pops on orange;
    # apricot for secondary marks.
    "mmt-tangerine": {"bg": "#C25012", "fg": "#FFF2E5", "accent": "#7FD9CF", "accent2": "#F2B279",
                      "motion": "fade"},
    # ftt-study = Founder Tip Tuesday. The founder den moved from forest to a steel-blue study;
    # brass/parchment/clay carry over intact. Grayer + lighter than ttd-indigo on purpose.
    "ftt-study": {"bg": "#1D3557", "fg": "#F0E8D2", "accent": "#C9A24A", "accent2": "#B5654A",
                  "motion": "fade", "fonts": {"display": "Fraunces", "body": "Inter"}},
    # wsc-goldenrod = Who Signs The Check. File-folder/ledger-jacket yellow, ledger-green ink,
    # copper (coin/pen), "sign here" red reserved for each episode's one flag.
    "wsc-goldenrod": {"bg": "#F2C94C", "fg": "#1F3D2E", "accent": "#A4551E", "accent2": "#B3271D",
                      "motion": "fade"},
    # ttd-indigo = The Teardown. Blueprint world on electric indigo — deliberately vivid and
    # blue-leaning so it never blurs with fwf's red-leaning violet or ftt-study's gray blue.
    # Safety orange annotates; periwinkle for quiet secondary marks.
    "ttd-indigo": {"bg": "#2E33A0", "fg": "#EDF0FF", "accent": "#F2762E", "accent2": "#9BA8F5",
                   "motion": "fade"},
    # fmf-alarm = Failure Modes Friday. Brick red (deep, not fire-engine, so long text stays
    # comfortable), caution yellow kept from mono, ash gray for secondary marks.
    "fmf-alarm": {"bg": "#9E1B1B", "fg": "#FBEFE8", "accent": "#F5C518", "accent2": "#C9CDD2",
                  "motion": "fade"},
}
DEFAULT = "midnight"
VALID_MOTION = {"rise", "fade", "pop", "slide"}


def resolve(spec):
    """spec may be a theme name (str), an override dict, or None."""
    theme = dict(THEMES[DEFAULT])
    if isinstance(spec, str) and spec in THEMES:
        theme.update(THEMES[spec])
    elif isinstance(spec, dict):
        theme.update(spec)
    return theme
