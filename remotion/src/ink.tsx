import React, {createContext, useContext} from 'react';
import {BRAND} from './brand';

// Theme-keyed ink for the text/data components (2026-07-15). The navy world keeps its
// exact prior colors (BRAND.white body, heavy dark drop-shadow); the paper worlds
// ('nemock-deep-dive', 'cut-bond') get a deep warm ink that reads on the cream surface —
// white body text is invisible on off-white paper. Accents (green/red) read on both worlds
// and are unchanged. Non-paper resolves to today's exact values => ZERO regression for the
// midnight masterclass and every legacy deck.

export const PAPER_THEMES = ['nemock-deep-dive', 'cut-bond'];
export const isPaperTheme = (t?: string): boolean => !!t && PAPER_THEMES.includes(t);

export type Ink = {
  body: string;    // primary body text
  soft: string;    // secondary / sub text
  cardBg: string;  // panel fill (SideBySide, StatGrid cells, ...)
  track: string;   // faint empty track / unfilled dot (Ring, Pictograph)
  neutral: string; // mid neutral fill (Waterfall neutral bar)
  paper: boolean;  // true on the paper worlds — gate dark drop-shadows off
};

const NAVY: Ink = {
  body: BRAND.white,
  soft: 'rgba(245,247,255,0.75)',
  cardBg: 'rgba(255,255,255,.05)',
  track: 'rgba(255,255,255,.12)',
  neutral: 'rgba(255,255,255,.5)',
  paper: false,
};

// Deep ink for the cream world — matches the PaperHook headline ink (#2c1e4e).
const PAPER: Ink = {
  body: '#2c1e4e',
  soft: '#6b6459',
  cardBg: 'rgba(120,92,40,.06)',
  track: 'rgba(70,50,30,.14)',
  neutral: 'rgba(90,70,45,.55)',
  paper: true,
};

// Soft warm shadow for headlines on paper (the heavy dark blur smudges on off-white).
export const PAPER_SHADOW = '0 4px 14px rgba(120,92,40,.16)';

const InkContext = createContext<Ink>(NAVY);

export const InkProvider: React.FC<{theme?: string; children: React.ReactNode}> = ({theme, children}) => (
  <InkContext.Provider value={isPaperTheme(theme) ? PAPER : NAVY}>{children}</InkContext.Provider>
);

export const useInk = (): Ink => useContext(InkContext);
