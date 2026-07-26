import React, {createContext, useContext} from 'react';
import {BRAND} from './brand';

// Theme-keyed ink for the text/data components (2026-07-15). The navy world keeps its
// exact prior colors (BRAND.white body, heavy dark drop-shadow); the paper worlds
// ('nemock-deep-dive', 'cut-bond') get a deep warm ink that reads on the cream surface —
// white body text is invisible on off-white paper. Accents (green/red) read on both worlds
// and are unchanged. Non-paper resolves to today's exact values => ZERO regression for the
// midnight masterclass and every legacy deck.

export const PAPER_THEMES = ['nemock-deep-dive', 'cut-bond', 'brg-paper', 'brg-deep-dive'];
export const isPaperTheme = (t?: string): boolean => !!t && PAPER_THEMES.includes(t);

export type Ink = {
  body: string;    // primary body text
  soft: string;    // secondary / sub text
  cardBg: string;  // panel fill (SideBySide, StatGrid cells, ...)
  track: string;   // faint empty track / unfilled dot (Ring, Pictograph)
  neutral: string; // mid neutral fill (Waterfall neutral bar)
  accent: string;  // the ONE accent (kicker + highlighted words). Default = the studio green.
  paper: boolean;  // true on the paper worlds — gate dark drop-shadows off
};

const NAVY: Ink = {
  body: BRAND.white,
  soft: 'rgba(245,247,255,0.75)',
  cardBg: 'rgba(255,255,255,.05)',
  track: 'rgba(255,255,255,.12)',
  neutral: 'rgba(255,255,255,.5)',
  accent: BRAND.green,
  paper: false,
};

// Deep ink for the cream world — matches the PaperHook headline ink (#2c1e4e).
const PAPER: Ink = {
  body: '#2c1e4e',
  soft: '#6b6459',
  cardBg: 'rgba(120,92,40,.06)',
  track: 'rgba(70,50,30,.14)',
  neutral: 'rgba(90,70,45,.55)',
  accent: BRAND.green,
  paper: true,
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
  paper: true,
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
  paper: true,
};

// Soft warm shadow for headlines on paper (the heavy dark blur smudges on off-white).
export const PAPER_SHADOW = '0 4px 14px rgba(120,92,40,.16)';

const InkContext = createContext<Ink>(NAVY);

const INK_BY_THEME: Record<string, Ink> = {
  'brg-paper': PAPER_BRG,
  'brg-deep-dive': PAPER_BRG_DEEP,
};

export const InkProvider: React.FC<{theme?: string; children: React.ReactNode}> = ({theme, children}) => (
  <InkContext.Provider value={(theme && INK_BY_THEME[theme]) || (isPaperTheme(theme) ? PAPER : NAVY)}>{children}</InkContext.Provider>
);

export const useInk = (): Ink => useContext(InkContext);
