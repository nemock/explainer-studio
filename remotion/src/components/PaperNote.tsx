import React from 'react';
import {Img, staticFile} from 'remotion';

// Real paper substrates instead of CSS-drawn cards (papercraft-substrate-plan.md).
//
// The rule: Magnific generates BLANK paper, Remotion renders the type on top. Nothing in
// public/papercraft-notes/ contains a word, and nothing there ever should — baking text
// into an asset would cost a regeneration round-trip per copy edit and would soften the
// type at 1080p.
//
// The substrates are generated warm yellow (gpt-2 knows what colour a post-it is and
// overrides a "pale cream" instruction). We do NOT fight that at generation time. Instead
// the paper is desaturated and renormalised here, then a pastel is multiplied over it, so
// the grain and the cut edge survive and the colour lands exactly on the palette value.
// A straight multiply over the yellow goes muddy — pastel blue comes out sage. Proved
// 2026-07-31; see the plan's "tint needs a desaturate step".

// This file holds BOTH substrate primitives:
//   PaperNote  — a whole note, drawn at its own true aspect (the box adapts to the paper)
//   PaperSheet — a 9-sliced card for content-sized boxes (the paper adapts to the box)
// They differ because PaperCard callers size to their text and have no aspect to give.

export type NoteFamily = 'note_square' | 'note_half_torn' | 'note_wide' | 'note_tall'
                       | 'note_strip' | 'note_flag';

// aspect = the TRUE object aspect (w/h) after the alpha trim, from
// public/papercraft-notes/provenance.json. It is not the generated frame aspect.
const FAMILIES: {family: NoteFamily; aspect: number; takes: number}[] = [
  {family: 'note_flag', aspect: 0.21, takes: 4},
  {family: 'note_tall', aspect: 0.54, takes: 4},
  {family: 'note_square', aspect: 0.97, takes: 4},
  {family: 'note_wide', aspect: 1.77, takes: 4},
  {family: 'note_half_torn', aspect: 2.62, takes: 4},
  {family: 'note_strip', aspect: 6.38, takes: 4},
];

// Pastels, in Dave's four (2026-07-31). Pulled warm and slightly desaturated from stock
// office-supply colours so they read as post-its without fighting the cream/navy/green
// world. Multiplied over near-white paper, so these ARE the resulting surface colour.
export const NOTE_PASTEL = {
  yellow: '#ffe8a3',
  pink: '#ffd2d8',
  blue: '#c3dcf0',
  green: '#cbe8c8',
} as const;
export type NotePastel = keyof typeof NOTE_PASTEL;
export const PASTEL_CYCLE: NotePastel[] = ['yellow', 'blue', 'pink', 'green'];

const seed = (s: string) => {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0);
};

/**
 * Choose a substrate for a box whose CONTENT needs at most `contentAspect` (width/height).
 *
 * Real paper does not stretch. Scale a 2.6:1 torn note to 4:1 and the grain smears and the
 * ragged edge turns to mush — the first still of this component showed exactly that. So the
 * caller does not get to pick the box and make the paper fit it. Instead:
 *
 *   pick the WIDEST substrate that is still no wider than the content needs,
 *   then set the box height to width / substrate.aspect.
 *
 * Because the chosen aspect is <= the content aspect, the resulting height is always >= the
 * height the text needs. The surplus is blank note, which is what a real post-it looks like.
 * The paper is then drawn at its true aspect and never distorts.
 *
 * Pass `only` to lock the family (Schematic resolves the family once, at layout time, then
 * hands it to the component so both agree).
 *
 * Every take curls the same corner (bottom-right), a visible tell once four notes share a
 * slide, so odd takes are mirrored: 8 apparent variants from 4 files. Selection hashes off
 * the caller's id, never a random call, so renders stay deterministic.
 */
export const fitNote = (id: string, contentAspect: number, only?: NoteFamily) => {
  const pool = only ? FAMILIES.filter((f) => f.family === only) : FAMILIES;
  const usable = pool.filter((f) => f.aspect <= contentAspect);
  // widest that still fits; if the content is narrower than every substrate, take the
  // narrowest we have and let the box be taller than the text needs
  const best = usable.length
    ? usable.reduce((a, b) => (b.aspect > a.aspect ? b : a))
    : pool.reduce((a, b) => (b.aspect < a.aspect ? b : a));
  const take = (seed(id) % best.takes) + 1;
  return {
    src: `papercraft-notes/${best.family}_${take}.webp`,
    family: best.family,
    aspect: best.aspect,
    // 4 takes x 2 flips x 2 flips = 16 apparent variants from 4 files. The vertical flip
    // matters most on note_half_torn: every take is the LOWER half, so the tear is always
    // at the top, and a row of four notes reads as a repeating motif rather than as paper.
    // Flipped, it is simply the upper half of a torn note — equally real.
    flipX: (take & 1) === 1,
    flipY: (take & 2) === 2,
  };
};

/**
 * A note substrate with children laid on top. Fills its parent; the caller owns position,
 * size, entrance transform and tilt.
 *
 * `shadow` is re-added here because background removal strips the cast shadow Magnific
 * baked in. That is the right trade: the edge and the grain were the tells, the shadow
 * never was, and a runtime shadow can respond to the scene's light.
 */
export const PaperNote: React.FC<{
  id: string;
  aspect: number;
  pastel?: NotePastel | string;
  family?: NoteFamily;
  shadow?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}> = ({id, aspect, pastel = 'yellow', family, shadow, children, style}) => {
  const note = fitNote(id, aspect, family);
  const tint = (NOTE_PASTEL as Record<string, string>)[pastel as string] ?? pastel;
  return (
    <div style={{position: 'relative', width: '100%', height: '100%',
                 filter: shadow ? `drop-shadow(${shadow})` : undefined, ...style}}>
      <div style={{position: 'absolute', inset: 0}}>
        <Img
          src={staticFile(note.src)}
          style={{
            width: '100%', height: '100%', display: 'block',
            // the desaturate half of the tint: strip the generated yellow and lift the
            // mid-tone to near-white so the multiply below lands on the true palette value
            filter: 'grayscale(1) brightness(1.18)',
            transform: `scaleX(${note.flipX ? -1 : 1}) scaleY(${note.flipY ? -1 : 1})`,
          }}
        />
        {/* the multiply half. Masked to the paper's own alpha so the tint stops at the
            cut edge instead of painting a rectangle over the scene. */}
        <div style={{
          position: 'absolute', inset: 0, background: tint, mixBlendMode: 'multiply',
          WebkitMaskImage: `url(${staticFile(note.src)})`,
          maskImage: `url(${staticFile(note.src)})`,
          WebkitMaskSize: '100% 100%', maskSize: '100% 100%',
          WebkitMaskRepeat: 'no-repeat', maskRepeat: 'no-repeat',
          transform: `scaleX(${note.flipX ? -1 : 1}) scaleY(${note.flipY ? -1 : 1})`,
        }} />
      </div>
      {children ? (
        <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
                     alignItems: 'center', justifyContent: 'center'}}>
          {children}
        </div>
      ) : null}
    </div>
  );
};

// ---------------------------------------------------------------------------------------
// PaperSheet — the 9-sliced card substrate (papercraft-substrate-plan.md §3 strategy C).
//
// PaperNote's trick (let the paper's aspect set the box) cannot work here: PaperCard is
// content-sized — it grows to fit its text — so there is no aspect to hand the paper, and
// scaling one card image to every box would crush the cut edge on small tags and smear the
// grain on wide ones. border-image pins the four corners and the four cut edges at a fixed
// size and stretches only the uniform interior, which is why the card assets are generated
// deliberately featureless: even grain, even light, no curl, no tear.
//
// The border-image sits on a BACKDROP layer rather than on the content element. Putting a
// border on the element itself would inset its content box and shift all 13 PaperCard call
// sites; the backdrop fills the parent and leaves the caller's own padding untouched.

// public/papercraft-cards/<family>_N.webp
//   card       — the workhorse, backs PaperCard
//   card_index — heavier, warmer index stock for quotes and keep-cards
//   card_tag   — small low tags and chips, where a full card's edge would be out of scale
export type CardFamily = 'card' | 'card_index' | 'card_tag';
const CARD_TAKES = 4;
const CARD_SLICE = 36;                // source px taken as the corner/edge tiles

export const PaperSheet: React.FC<{
  id?: string;
  family?: CardFamily;
  edge?: number;                      // rendered thickness of the cut edge, px
  tint?: string;
  radius?: number;
  style?: React.CSSProperties;
}> = ({id = 'card', family = 'card', edge = 14, tint, radius, style}) => {
  const take = (seed(`${family}:${id}`) % CARD_TAKES) + 1;
  const src = staticFile(`papercraft-cards/${family}_${take}.webp`);
  // same two-step as the notes: strip the paper's own warmth before multiplying, or the
  // tint lands somewhere other than the palette value asked for
  const desat = tint ? 'grayscale(1) brightness(1.12)' : undefined;
  return (
    <div style={{position: 'absolute', inset: 0, borderRadius: radius, overflow: 'hidden', ...style}}>
      {/*
        Interior grain, drawn at the asset's NATURAL pixel size and centred — never scaled to
        the box. The first attempt let border-image's `fill` paint the middle, which squashed
        a 587px-tall source into a 315px card and turned the paper fibre into vertical
        streaks that read as brushed linen. `background-size: auto` cannot distort: for any
        box smaller than the asset this is a plain centre crop, and grain therefore stays at
        one constant scale across every card in the video regardless of their sizes.
      */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: `url(${src})`, backgroundSize: 'auto',
        backgroundRepeat: 'repeat', backgroundPosition: 'center',
        filter: desat,
      }} />
      {/* the real cut edge, 9-sliced. No `fill` — the middle is the layer above. */}
      <div style={{
        position: 'absolute', inset: 0,
        borderStyle: 'solid', borderWidth: edge,
        borderImageSource: `url(${src})`,
        borderImageSlice: `${CARD_SLICE}`,
        borderImageWidth: `${edge}px`,
        borderImageRepeat: 'stretch',
        filter: desat,
      }} />
      {tint ? <div style={{position: 'absolute', inset: 0, background: tint, mixBlendMode: 'multiply'}} /> : null}
    </div>
  );
};

// ---------------------------------------------------------------------------------------
// Tape — a torn strip laid across a corner or edge, from public/papercraft-fixings/.
//
// This is the cheapest high-impact element in the substrate library: a card with tape on it
// reads as FIXED to the table, where the same card without it floats. It is an overlay, not
// a substrate, so unlike the cards it is NOT normalised to world.paper — the beige has to
// stay distinct from whatever it is holding down or it vanishes into it.
//
// Never scaled non-uniformly: a stretched tear reads as a smear. Width is set, height follows
// the asset's own aspect.

const TAPE_TAKES = 4;
const TAPE_ASPECT = [3.87, 4.27, 4.38, 3.91];   // provenance.json, true aspect after trim

export const Tape: React.FC<{
  id: string;
  width: number;                      // px; height follows the asset aspect
  at?: 'tl' | 'tr' | 'bl' | 'br' | 'top';
  angle?: number;                     // degrees; omit for a seeded hand-placed tilt
  opacity?: number;
}> = ({id, width, at = 'tl', angle, opacity = 1}) => {
  const h = seed(id);
  const take = (h % TAPE_TAKES) + 1;
  const height = width / TAPE_ASPECT[take - 1];
  // seeded tilt so a slide of taped elements doesn't look machine-aligned
  const tilt = angle ?? (at === 'top' ? ((h >> 3) % 7) - 3 : (at === 'tl' || at === 'br' ? -45 : 45) + (((h >> 3) % 9) - 4));
  const pos: React.CSSProperties =
    at === 'top' ? {top: -height * 0.55, left: '50%', marginLeft: -width / 2}
    : at === 'tl' ? {top: -height * 0.45, left: -width * 0.28}
    : at === 'tr' ? {top: -height * 0.45, right: -width * 0.28}
    : at === 'bl' ? {bottom: -height * 0.45, left: -width * 0.28}
    : {bottom: -height * 0.45, right: -width * 0.28};
  return (
    <div style={{position: 'absolute', width, height, zIndex: 3, opacity, ...pos,
                 transform: `rotate(${tilt}deg)`, pointerEvents: 'none'}}>
      <Img src={staticFile(`papercraft-fixings/tape_${take}.webp`)}
           style={{width: '100%', height: '100%', display: 'block',
                   filter: 'drop-shadow(0 3px 6px rgba(12,4,24,.30))'}} />
    </div>
  );
};
