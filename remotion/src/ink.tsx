import React, {createContext, useContext} from 'react';
import {BRAND} from './brand';

// Theme-keyed ink for the text/data components (2026-07-15). The navy world keeps its
// exact prior colors (BRAND.white body, heavy dark drop-shadow); the paper worlds
// ('nemock-deep-dive', 'cut-bond') get a deep warm ink that reads on the cream surface —
// white body text is invisible on off-white paper. Accents (green/red) read on both worlds
// and are unchanged. Non-paper resolves to today's exact values => ZERO regression for the
// midnight masterclass and every legacy deck.

export const PAPER_THEMES = ['nemock-deep-dive', 'cut-bond', 'brg-paper', 'brg-deep-dive', 'wte-guide', 'circumvent',
  'plg-guide',
  // The six personal-show worlds (2026-08-06 brand system) — all render the Cvg family.
  'fwf', 'mmt-tangerine', 'ftt-study', 'wsc-goldenrod', 'ttd-indigo', 'fmf-alarm'];
export const isPaperTheme = (t?: string): boolean => !!t && PAPER_THEMES.includes(t);

export type Ink = {
  body: string;    // primary body text
  soft: string;    // secondary / sub text
  cardBg: string;  // panel fill (SideBySide, StatGrid cells, ...)
  track: string;   // faint empty track / unfilled dot (Ring, Pictograph)
  neutral: string; // mid neutral fill (Waterfall neutral bar)
  accent: string;  // the ONE accent (kicker + highlighted words). Default = the studio green.
  accentWash: string; // translucent accent for marker-wipe highlights laid OVER artwork
  // The "something is wrong" colour: PunchWord kind:'bad', Reframe's strike-through,
  // Schematic bad nodes, negative deltas. OPTIONAL — useInk defaults it to BRAND.red, so
  // every theme that does not declare one behaves exactly as it always has. A theme sets
  // it only when the studio red is foreign to its world: plg-guide is strictly
  // cream/navy/rust, and a scarlet punch word on that cream is the same off-brand leak as
  // the green accent and the pink note were (operator, 2026-08-12).
  danger?: string;
  paper: boolean;  // true on the paper worlds — gate dark drop-shadows off
  // Headline type sits on real paper stock in this world: statement posters, the hook card,
  // compare trays, and the opt-in PaperStage scenes. Scoped to the two DEEP-DIVE channels
  // (nemock-deep-dive, brg-deep-dive) by operator directive 2026-08-01 — deliberately NOT
  // every paper world. cut-bond is portrait shorts, brg-paper backs an already-produced
  // cohort promo, wte-guide is its own channel, and circumvent has its own scene family
  // where the paper IS the slide. Adding a world here is a per-channel decision.
  typeOnPaper: boolean;
};

const NAVY: Ink = {
  body: BRAND.white,
  soft: 'rgba(245,247,255,0.75)',
  cardBg: 'rgba(255,255,255,.05)',
  track: 'rgba(255,255,255,.12)',
  neutral: 'rgba(255,255,255,.5)',
  accent: BRAND.green,
  accentWash: 'rgba(61,220,132,.42)',  // the exact prior Figure highlight => zero regression
  paper: false,
  typeOnPaper: false,
};

// Deep ink for the cream world — matches the PaperHook headline ink (#2c1e4e).
const PAPER: Ink = {
  body: '#2c1e4e',
  soft: '#6b6459',
  cardBg: 'rgba(120,92,40,.06)',
  track: 'rgba(70,50,30,.14)',
  neutral: 'rgba(90,70,45,.55)',
  accent: BRAND.green,
  accentWash: 'rgba(61,220,132,.42)',
  paper: true,
  typeOnPaper: false,
};

// Base Reality Group paper world — exact BRG navy ink on cream (kept separate from the
// green/purple PAPER world so the nemock-deep-dive and cut-bond channels are untouched).
// USED BY: the `brg-paper` theme = BRG marketing/promo videos (Plan to Market cohort).
// Accent stays the studio green here so that already-produced promo is untouched.
const PAPER_BRG: Ink = {
  body: '#1b2b4b',
  soft: '#5b6577',
  cardBg: 'rgba(27,43,75,.06)',
  track: 'rgba(27,43,75,.14)',
  neutral: 'rgba(27,43,75,.5)',
  accent: BRAND.green,
  accentWash: 'rgba(61,220,132,.42)',
  paper: true,
  typeOnPaper: false,
};

// BRG DEEP-DIVE paper world (2026-07-26) — the fractional-CPO/product series' own palette.
// Same BRG navy-on-cream ink as the promo world, but the accent is BRG INDIGO (#7b5bff, the
// brand accent already used on the series' thumbnails) instead of the studio green. Kept as
// its OWN entry rather than retuning `brg-paper`, which the Plan to Market cohort promo
// already renders with (operator directive 2026-07-26: add a palette, never repaint one
// that's in use — same rule as theme-keyed branding isolation).
const PAPER_BRG_DEEP: Ink = {
  body: '#1b2b4b',
  soft: '#5b6577',
  cardBg: 'rgba(27,43,75,.06)',
  track: 'rgba(27,43,75,.14)',
  neutral: 'rgba(27,43,75,.5)',
  accent: '#7b5bff',
  accentWash: 'rgba(123,91,255,.34)',
  paper: true,
  typeOnPaper: true,
};

// WASTE-TO-FUEL Operator's Guide paper world (2026-07-29) — the process-safety series'
// own palette. Same BRG navy-on-cream ink as its siblings, but the accent is BRG TEAL
// (#0d7377, the site's own accent) so the series reads as its own family next to the
// indigo CPO series and the green promo world. Its own entry rather than a retune of
// `brg-paper`/`brg-deep-dive`, both of which are already in use (operator rule: add a
// palette, never repaint one that's shipping).
const PAPER_WTE: Ink = {
  body: '#1b2b4b',
  soft: '#5b6577',
  cardBg: 'rgba(27,43,75,.06)',
  track: 'rgba(27,43,75,.14)',
  neutral: 'rgba(27,43,75,.5)',
  accent: '#0d7377',
  accentWash: 'rgba(13,115,119,.30)',
  paper: true,
  typeOnPaper: false,   // its own channel — not a deep-dive world
};

// PRODUCT LEADERSHIP Operator's Guide paper world (2026-08-11) — the twelve-part
// head-of-product / CPO teaching series on Dave's personal channel. Navy-on-cream like its
// paper siblings; the accent is RUST/TERRACOTTA (#a8481f, operator's choice).
//
// The accent choice is load-bearing, not decorative. This series teaches the SAME subject
// matter as the BRG deep-dive series (#39/#40/#50) but is a different product: free,
// ungated, like-and-subscribe, outside the sales funnel. Sharing BRG indigo (#7b5bff)
// would make two different things read as one in a thumbnail grid — exactly the confusion
// the theme-isolation rule exists to prevent. Rust also sits furthest from its neighbours:
// indigo (#7b5bff), WTE teal (#0d7377), Circumvent gold (#c89b3c), studio green.
// Contrast on the cream ground (#f5f0eb) is ~5.1:1, so it carries accent TEXT, not just
// fills. Its own entry, never a retune of a shipping palette.
const PAPER_PLG: Ink = {
  body: '#1b2b4b',
  soft: '#5b6577',
  cardBg: 'rgba(27,43,75,.06)',
  track: 'rgba(27,43,75,.14)',
  neutral: 'rgba(27,43,75,.5)',
  accent: '#a8481f',
  accentWash: 'rgba(168,72,31,.30)',
  danger: '#a8481f',   // no scarlet in this world — 'bad' is the rust, deepened by context
  paper: true,
  typeOnPaper: false,   // its own series world — not a deep-dive world
};

// CIRCUMVENT GLOBAL paper world (2026-07-30) — the Circumvent marketing/explainer program.
// The only paper world with GREEN ink rather than navy or purple, which is what makes it
// legible as a different brand at a glance. Deep forest body ink (#1c3a29) extends the
// #14532D already used in Circumvent's investor materials; the accent is harvest gold
// (#c89b3c) rather than a green, on purpose: green-on-green reads as environmental
// advocacy, and this brand sells to agricultural producers and energy buyers. Green ink
// plus harvest gold reads farm, grain and refinery. Not a BRG property and not part of
// Dave's personal channels; its own entry per the standing rule (add a palette, never
// repaint one that is shipping).
const PAPER_CIRCUMVENT: Ink = {
  body: '#1c3a29',
  soft: '#5c7266',
  cardBg: 'rgba(28,58,41,.06)',
  track: 'rgba(28,58,41,.14)',
  neutral: 'rgba(28,58,41,.5)',
  accent: '#c89b3c',
  accentWash: 'rgba(200,155,60,.34)',
  paper: true,
  typeOnPaper: false,   // its own channel — not a deep-dive world
};

// Soft warm shadow for headlines on paper (the heavy dark blur smudges on off-white).
export const PAPER_SHADOW = '0 4px 14px rgba(120,92,40,.16)';

const InkContext = createContext<Ink>(NAVY);

// nemock-deep-dive shares PAPER's colours but opts INTO type-on-paper; cut-bond keeps
// PAPER as-is. Without this split the two could not differ, since both fall through
// isPaperTheme to the same object.
const PAPER_NEMOCK: Ink = {...PAPER, typeOnPaper: true};

// The six personal-show worlds (2026-08-06). They render through the Cvg scene family
// (world tokens in brands/papercraft.ts do the heavy lifting), so these Ink entries
// mostly serve captions and any classic component that sneaks in. Each is its show's
// dark ink + accent; per the standing rule these are new entries, nothing repainted.
const mkShowInk = (body: string, accent: string, wash: string): Ink => ({
  body, soft: `${body}99`, cardBg: `${body}0F`, track: `${body}24`, neutral: `${body}80`,
  accent, accentWash: wash, paper: true, typeOnPaper: false,
});
const INK_BY_THEME: Record<string, Ink> = {
  'nemock-deep-dive': PAPER_NEMOCK,
  'brg-paper': PAPER_BRG,
  'brg-deep-dive': PAPER_BRG_DEEP,
  'wte-guide': PAPER_WTE,
  'plg-guide': PAPER_PLG,
  'circumvent': PAPER_CIRCUMVENT,
  'fwf': mkShowInk('#2A1142', '#757BBD', 'rgba(117,123,189,.34)'),
  'mmt-tangerine': mkShowInk('#5F2508', '#0F7E75', 'rgba(15,126,117,.30)'),
  'ftt-study': mkShowInk('#1D3557', '#A8822F', 'rgba(201,162,74,.32)'),
  'wsc-goldenrod': mkShowInk('#1F3D2E', '#A4551E', 'rgba(164,85,30,.32)'),
  'ttd-indigo': mkShowInk('#1D2170', '#E2661F', 'rgba(242,118,46,.32)'),
  'fmf-alarm': mkShowInk('#5A1010', '#A87E00', 'rgba(245,197,24,.34)'),
};

export const InkProvider: React.FC<{theme?: string; children: React.ReactNode}> = ({theme, children}) => (
  <InkContext.Provider value={(theme && INK_BY_THEME[theme]) || (isPaperTheme(theme) ? PAPER : NAVY)}>{children}</InkContext.Provider>
);

// Deliberately does NOT fill in `danger`. Each call site keeps the exact fallback it
// had before this field existed — plain BRAND.red in most components, the deeper #c2352b
// on the paper worlds for Media marks and Annotate. Filling a single default here would
// have quietly repainted the red on every other paper theme (nemock, brg, wte, cut-bond
// and the six shows), which is exactly the repaint the theme-isolation rule forbids.
export const useInk = (): Ink => useContext(InkContext);
