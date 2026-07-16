// Cut & Bond — channel brand tokens (2026-07-15).
// A stand-alone, UNBRANDED chemistry-shorts channel: no wordmark, no CTA, no sting
// (portrait shorts already default sting-off). It reuses the studio's paper *technique*
// (layered cut-paper cutouts + soft cast shadows) with its OWN palette — deliberately
// distinct from the davesaunders.net paper world (cream/navy/green). Nothing here is
// imported by the davesaunders components; selection is by the `theme: 'cut-bond'` prop.

export const CUTANDBOND = {
  paper: '#f4ecd6',      // the off-white paper surface (the whole world) — matches the GPT-2 style anchor
  paperDeep: '#e7dcc0',  // a darker paper for edges / stacked-sheet shadows
  ink: '#2a2622',        // warm near-black — body/caption text
  inkSoft: '#6b6459',    // secondary ink — sub-lines, kickers
  // bold, saturated cut-paper accents (the channel's signature four)
  coral: '#ff5a4d',
  teal: '#17b7a6',
  sunflower: '#ffc23c',
  grape: '#7a4bd0',
  font: '-apple-system, "Helvetica Neue", Arial, sans-serif',
};

// Periodic-category -> accent color. The channel's teaching device: an element's
// color IS its category, so the palette itself teaches the table. Keys match the
// `category` we tag each element with in its project data. Ten hues; the signature
// four appear among them.
export const CATEGORY_COLOR: Record<string, string> = {
  'alkali-metal': '#ff5a4d',           // coral
  'alkaline-earth-metal': '#ff8a3d',   // amber-orange
  'transition-metal': '#ffc23c',       // sunflower
  'post-transition-metal': '#9bd14b',  // leaf
  'metalloid': '#17b7a6',              // teal
  'reactive-nonmetal': '#3ea8ff',      // sky
  'halogen': '#7a4bd0',                // grape
  'noble-gas': '#d24bd0',              // magenta
  'lanthanide': '#4bd0a6',             // mint
  'actinide': '#d04b7a',               // rose
  'unknown': '#8a8577',                // muted paper-grey
};

// House entrance easing (mirrors the studio EASE_OUT). Paper motion is settle-and-place,
// never bouncy sci-fi.
export const PAPER_EASE = [0.16, 1, 0.3, 1] as const;

export const categoryColor = (cat?: string): string =>
  (cat && CATEGORY_COLOR[cat]) || CATEGORY_COLOR.unknown;
