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

// BRG (future BRG-branded series — parameterization proof, unused today)
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

export const paperWorldFor = (theme?: string): PaperWorldTokens =>
  theme === 'brg' ? PAPER_BRG : PAPER_FWF;

// House timing (spec §3): snap-and-settle, stop-motion energy. Springs only.
export const SNAP = {damping: 13, stiffness: 200} as const;   // place
export const HINGE = {damping: 12, stiffness: 170} as const;  // popup
export const CAM = {damping: 13, stiffness: 190} as const;    // camera steps
