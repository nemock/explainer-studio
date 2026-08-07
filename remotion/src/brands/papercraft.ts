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
  // PaperHook's full-bleed cold-open sheet + headline ink. These predate the
  // per-channel world tokens and were hardcoded in the component to FWF's values;
  // they live here now so a new channel can own them WITHOUT repainting the
  // channels already rendering with the originals (2026-07-29).
  hookSheet: string;
  hookInk: string;
  // Key-light colours as bare "r,g,b" triples; PaperTable composes the alpha. Optional,
  // and both default to the original hardcoded values, so every world that predates this
  // renders byte-identically. They exist because a LIGHT ground needs a warm falloff:
  // the original near-black surround (10,3,20) is invisible on a dark table and reads as
  // grey dirt on cream (2026-08-07).
  lightTint?: string;
  lightSurround?: string;
  // Kicker TEXT colour. Defaults to accentSoft, which is what every dark world has always
  // used. It needs its own token because accentSoft does double duty — kicker text AND
  // chip/band fills — and on a LIGHT ground one value cannot do both: a fill light enough
  // for navy text on it is far too pale to read as text on cream (2026-08-07).
  kicker?: string;
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
  hookSheet: '#f4ecd6',
  hookInk: '#2c1e4e',
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
  hookSheet: '#f4ecd6',
  hookInk: '#2c1e4e',
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
  hookSheet: '#f4ecd6',
  hookInk: '#2c1e4e',
};

// WASTE-TO-FUEL Operator's Guide world (2026-07-29) — the process-safety series.
// BRG navy ground + cream paper + the teal site accent, and unlike its siblings it
// also carries the BRG palette into the cold-open hook sheet (the older worlds keep
// FWF's warm cream + purple ink there, because they are already rendering with it).
export const PAPER_WTE: PaperWorldTokens = {
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
  hookSheet: '#F5F0EB',
  hookInk: '#1B2B4B',
};

// CIRCUMVENT GLOBAL world (2026-07-30) — the only paper world grounded in green rather
// than navy or purple. Kraft cream sheet (#F2EDE0) over a deep forest ground, harvest-gold
// accent. See "Circumvent Marketing/PALETTE.md" for why the accent is gold and not a second
// green: this brand sells to agricultural producers and energy buyers, and green-on-green
// reads as environmental advocacy to that audience.
export const PAPER_CIRCUMVENT: PaperWorldTokens = {
  ground: '#14361F',
  groundDeep: '#0D2415',
  sheet: '#1F4A2F',
  sheetAlt: '#2F7D4F',
  paper: '#F2EDE0',
  paperShade: '#E2D8C2',
  ink: '#1C3A29',
  accent: '#C89B3C',
  accentSoft: '#E3C687',
  shadow: 'rgba(12,28,18,.45)',
  hookSheet: '#F2EDE0',
  hookInk: '#1C3A29',
};

// ---- The six personal-show worlds (video brand system, locked 2026-08-06 —
// make_money/routine_changes/2026-08-06-video-brand-system-palettes-locked.md).
// All render through the Cvg scene family (full-bleed sets, cutouts, type on a light
// paper scrim), so each world's `paper`/`ink` pair is the scrim + type, and the show's
// hue lives in ground/sheet/accent + its generated papercraft-<show> asset library.
// Per the standing rule these are NEW entries; no shipping world was repainted.

// Daily founder tip (theme `fwf`) — the book cover's violet.
export const PAPER_SHOW_FWF: PaperWorldTokens = {
  ground: '#2A1142', groundDeep: '#1D0B30', sheet: '#36185B', sheetAlt: '#757BBD',
  paper: '#F3EFFA', paperShade: '#DFD8EE', ink: '#2A1142',
  accent: '#757BBD', accentSoft: '#C7CCEA', shadow: 'rgba(15,5,30,.45)',
  hookSheet: '#F3EFFA', hookInk: '#2A1142',
};

// Monday MedTech (`mmt-tangerine`) — tangerine stock, clinical aqua.
export const PAPER_MMT: PaperWorldTokens = {
  ground: '#7A2F09', groundDeep: '#5A2206', sheet: '#C25012', sheetAlt: '#F2B279',
  paper: '#FFF2E5', paperShade: '#F0DCC6', ink: '#5F2508',
  accent: '#0F7E75', accentSoft: '#7FD9CF', shadow: 'rgba(40,15,4,.45)',
  hookSheet: '#FFF2E5', hookInk: '#5F2508',
};

// Founder Tip Tuesday (`ftt-study`) — the midnight-blue study, brass and parchment.
export const PAPER_FTT: PaperWorldTokens = {
  ground: '#14253E', groundDeep: '#0D1930', sheet: '#1D3557', sheetAlt: '#C9A24A',
  paper: '#F0E8D2', paperShade: '#DFD3B6', ink: '#1D3557',
  accent: '#A8822F', accentSoft: '#E2CC92', shadow: 'rgba(8,16,32,.45)',
  hookSheet: '#F0E8D2', hookInk: '#1D3557',
};

// Who Signs The Check (`wsc-goldenrod`) — goldenrod folder, ledger-green ink.
export const PAPER_WSC: PaperWorldTokens = {
  ground: '#7A5E10', groundDeep: '#5C460B', sheet: '#F2C94C', sheetAlt: '#B3271D',
  paper: '#FBF3DC', paperShade: '#EBDDB4', ink: '#1F3D2E',
  accent: '#A4551E', accentSoft: '#D9A06B', shadow: 'rgba(60,45,8,.45)',
  hookSheet: '#F2C94C', hookInk: '#1F3D2E',
};

// The Teardown (`ttd-indigo`) — electric-indigo blueprint, safety-orange annotations.
export const PAPER_TTD: PaperWorldTokens = {
  ground: '#1D2170', groundDeep: '#141650', sheet: '#2E33A0', sheetAlt: '#9BA8F5',
  paper: '#EDF0FF', paperShade: '#D8DDF2', ink: '#1D2170',
  accent: '#E2661F', accentSoft: '#F9B98E', shadow: 'rgba(10,12,45,.5)',
  hookSheet: '#EDF0FF', hookInk: '#1D2170',
};

// Failure Modes Friday (`fmf-alarm`) — brick red, caution yellow (deepened on paper).
export const PAPER_FMF: PaperWorldTokens = {
  ground: '#6E1111', groundDeep: '#4E0C0C', sheet: '#9E1B1B', sheetAlt: '#C9CDD2',
  paper: '#FBEFE8', paperShade: '#EDD9CE', ink: '#5A1010',
  accent: '#A87E00', accentSoft: '#F5C518', shadow: 'rgba(45,8,8,.5)',
  hookSheet: '#FBEFE8', hookInk: '#5A1010',
};

// nemock-deep-dive — Dave's deep dives. THE CREAM WORLD (2026-08-07).
//
// Every other paper channel was given its own world and this one never was, so it fell
// through to PAPER_FWF and rendered its Paper* scenes on FWF's violet table — while the
// channel's own locked spec (skills/explainer2/references/paper-world/STYLE.md) says the
// base sheet is cream #f4ecd6 with navy ink and ONE green accent, and while its Magnific
// scene art is generated on exactly that cream. The result was a half-and-half deck: the
// Paper* text/data scenes dark violet, the Figure/Schematic/StatGrid scenes cream. This
// is the missing world, not a repaint — PAPER_FWF is untouched and the `fwf` show keeps
// its violet (papercraft-motion-migration.md §5's "plan one video fully papercraft").
//
// Here the PAGE is the table: ground is the same cream the art is drawn on, so a figure
// sits on the sheet rather than on a panel floating over it. Cards are brighter than the
// page so they still lift off it, and the vignette/shadow run warm kraft rather than ink.
export const PAPER_NEMOCK: PaperWorldTokens = {
  ground: '#f4ecd6',
  groundDeep: '#e3d4b0',
  sheet: '#eee1c2',
  sheetAlt: '#e7d8b6',
  paper: '#fdfaf3',
  paperShade: '#e0d3b8',
  ink: '#2c1e4e',
  accent: '#3ddc84',
  accentSoft: '#a9e7c6',
  shadow: 'rgba(120,92,40,.30)',
  hookSheet: '#f4ecd6',
  hookInk: '#2c1e4e',
  lightTint: '255,252,240',
  lightSurround: '150,120,70',
  // Exactly the green the CLASSIC components already use on this channel (ink.tsx ->
  // BRAND.green). The whole point of this world is that a Paper* kicker and a Schematic
  // kicker are the same colour on the same page.
  kicker: '#3ddc84',
};

// Theme -> world. Every paper channel owns its ground; anything unmapped keeps FWF.
const WORLD_BY_THEME: Record<string, PaperWorldTokens> = {
  'nemock-deep-dive': PAPER_NEMOCK,
  'brg-deep-dive': PAPER_BRG_DEEP,
  'brg-paper': PAPER_BRG,
  'wte-guide': PAPER_WTE,
  'circumvent': PAPER_CIRCUMVENT,
  'fwf': PAPER_SHOW_FWF,
  'mmt-tangerine': PAPER_MMT,
  'ftt-study': PAPER_FTT,
  'wsc-goldenrod': PAPER_WSC,
  'ttd-indigo': PAPER_TTD,
  'fmf-alarm': PAPER_FMF,
};
export const paperWorldFor = (theme?: string): PaperWorldTokens =>
  (theme && WORLD_BY_THEME[theme]) || PAPER_FWF;

// House timing (spec §3): snap-and-settle, stop-motion energy. Springs only.
export const SNAP = {damping: 13, stiffness: 200} as const;   // place
export const HINGE = {damping: 12, stiffness: 170} as const;  // popup
export const CAM = {damping: 13, stiffness: 190} as const;    // camera steps
