// Papercraft Motion — world tokens (papercraft-motion-spec.md §1, 2026-07-25).
// The approved BRG/FWF papercraft STILL style (cut-paper dioramas on a dark
// ground) brought into motion. One component set, parameterized per channel;
// selection is by theme (nemock-deep-dive -> FWF world). Never a global default.

export type PaperWorldTokens = {
  ground: string;      // the table: deep ink/navy field
  groundDeep: string;  // vignette edge
  sheet: string;       // big paper sheets laid on the table
  sheetAlt: string;
  paper: string;       // cream object/card paper
  paperShade: string;  // object side / fold shading (paper thickness)
  ink: string;         // text printed on cream
  accent: string;
  accentSoft: string;
  shadow: string;      // object drop shadows on the ground
};

// FWF / davesaunders.net (the nemock-deep-dive channel)
export const PAPER_FWF: PaperWorldTokens = {
  ground: '#2A1142',
  groundDeep: '#1D0B30',
  sheet: '#36185B',
  sheetAlt: '#5A3494',
  paper: '#FAF6EF',
  paperShade: '#E9E0D2',
  ink: '#2A1142',
  accent: '#5A3494',
  accentSoft: '#C7B6E6',
  shadow: 'rgba(15,5,30,.45)',
};

// BRG marketing/promo world — the teal site accent (pairs with the `brg-paper` theme,
// which the Plan to Market cohort promo renders with).
export const PAPER_BRG: PaperWorldTokens = {
  ground: '#1B2B4B',
  groundDeep: '#12203A',
  sheet: '#24365C',
  sheetAlt: '#0A5A5E',
  paper: '#F5F0EB',
  paperShade: '#E5DCCE',
  ink: '#1B2B4B',
  accent: '#0D7377',
  accentSoft: '#7FC9C4',
  shadow: 'rgba(6,14,30,.45)',
};

// BRG DEEP-DIVE world (2026-07-26) — the fractional-CPO/product series. Same BRG navy
// ground + cream paper, but the accent is BRG INDIGO (#7b5bff), matching the series'
// thumbnails and the PAPER_BRG_DEEP ink. Kept separate from PAPER_BRG so the cohort
// promo's teal world is untouched (operator directive: add a palette, never repaint a
// palette that is already in use).
export const PAPER_BRG_DEEP: PaperWorldTokens = {
  ground: '#1B2B4B',
  groundDeep: '#12203A',
  sheet: '#24365C',
  sheetAlt: '#3B2E7A',
  paper: '#F5F0EB',
  paperShade: '#E5DCCE',
  ink: '#1B2B4B',
  accent: '#7B5BFF',
  accentSoft: '#C3B4FF',
  shadow: 'rgba(6,14,30,.45)',
};

// Theme -> world. Every paper channel owns its ground; anything unmapped keeps FWF
// (zero regression for nemock-deep-dive and every deck that predates this).
export const paperWorldFor = (theme?: string): PaperWorldTokens =>
  theme === 'brg-deep-dive' ? PAPER_BRG_DEEP
    : theme === 'brg-paper' ? PAPER_BRG
      : PAPER_FWF;

// House timing (spec §3): snap-and-settle, stop-motion energy. Springs only.
export const SNAP = {damping: 13, stiffness: 200} as const;   // place
export const HINGE = {damping: 12, stiffness: 170} as const;  // popup
export const CAM = {damping: 13, stiffness: 190} as const;    // camera steps
