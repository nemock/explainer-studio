import React, {createContext, useContext} from 'react';
import {continueRender, delayRender, staticFile, useVideoConfig} from 'remotion';
import {BRAND} from './brand';
import {useWorld} from './components/PaperWorld';

// The type scale (visual upgrade, 2026-11-01). Text sizes are ROLES, not numbers.
//
// Why: every component used to carry its own inline literal (`height * 0.03`), so one role
// had four sizes across the engine, and most of them were sized for a monitor. A 16:9 video
// on a phone held upright is about 390 pt wide, which shrinks 1080p type by ~0.2: the 32 px
// kicker that was the only headline on most #79 slides became 6.5 pt, and the 22 px note
// sub-lines 4.5 pt. Small type is readable on a phone from about 9-10 pt, which is ~48 px in
// a 1080 frame. The floors below come from that test.
//
// Opt-in per world (`phoneType` in brands/papercraft.ts), so a theme that has not been
// proven on the new scale renders exactly as it did. Fractions are of the frame's SHORT
// side, so landscape and portrait share one scale (Schematic's U, usePaperLayout's M).

export type TypeRole =
  | 'heading'     // the slide's headline: replaces the lone uppercase kicker
  | 'eyebrow'     // optional small line above a heading (the old kicker, now secondary)
  | 'display'     // the one big term or line a slide is about (define term, reframe after)
  | 'label'       // the main words on an object: note, card, tray value, list item
  | 'body'        // a sentence or two set as reading text: a definition, a statement attrib
  | 'sub'         // a second line on an object, an edge label, a tray header
  | 'annotation'  // hand-drawn mark labels
  | 'caption';    // a figure caption under the art

// size = the role's natural size; min = the phone floor. Fitted text never goes below min.
export const PHONE_TYPE: Record<TypeRole, {size: number; min: number}> = {
  heading:    {size: 0.080, min: 0.064},   // 86 px, floor 69
  eyebrow:    {size: 0.040, min: 0.038},   // 43 px
  display:    {size: 0.096, min: 0.072},   // 104 px
  label:      {size: 0.062, min: 0.048},   // 67 px, floor 52
  body:       {size: 0.047, min: 0.042},   // 51 px
  sub:        {size: 0.041, min: 0.038},   // 44 px
  annotation: {size: 0.040, min: 0.038},
  caption:    {size: 0.044, min: 0.040},
};

/**
 * `ts(role, legacyPx)` -> px. On a phoneType world the role's size; anywhere else the
 * component's own legacy literal, untouched. Every call site passes its old value, so the
 * diff that adopts the scale is also the record of what each role used to be.
 */
export const useTypeScale = () => {
  const {width, height} = useVideoConfig();
  const world = useWorld();
  const U = Math.min(width, height);
  const on = Boolean(world.phoneType);
  const ts = (role: TypeRole, legacyPx: number) => (on ? Math.round(PHONE_TYPE[role].size * U) : legacyPx);
  const floor = (role: TypeRole) => Math.round(PHONE_TYPE[role].min * U);
  // a headline's size by its length: long lines step down rather than run under the captions
  const headline = (len: number, legacyPx: number) => {
    if (!on) return legacyPx;
    return Math.round(U * (len <= 70 ? 0.08 : len <= 130 ? 0.062 : len <= 220 ? 0.054 : 0.047));
  };
  // FILL THE SPACE (operator 2026-11-14, #85): "when we render our own text and elements, we
  // are underutilizing the visual space available on the screen." The length tiers above size
  // a headline for the shortest frame it might ever share, so a seven-word line sat at 86 px in
  // a card half the frame wide. `fill` returns the LARGEST size, up to `max` of the short side,
  // at which `text` word-wraps inside boxW x boxH, never under the role's phone floor. The wrap
  // is estimated (glyph width `cw` em, generous for 800-900 weights so it errs toward fitting),
  // which is what every other paper fit here does; no DOM measurement exists at render time.
  // Off a phoneType world it returns `legacyPx` untouched, like `ts`.
  const fill = (text: string, boxW: number, boxH: number, legacyPx: number,
                opts: {max?: number; min?: TypeRole; lh?: number; cw?: number} = {}) => {
    if (!on) return legacyPx;
    const {max = 0.15, min = 'heading', lh = 1.08, cw = 0.58} = opts;
    const words = String(text || '').split(/\s+/).filter(Boolean);
    const lines = (px: number) => {
      let n = 1, w = 0;
      for (const word of words) {
        const ww = word.length * cw * px, sp = 0.3 * px;
        if (ww > boxW) return Infinity;            // one word wider than the box: too big
        if (w === 0) w = ww;
        else if (w + sp + ww <= boxW) w += sp + ww;
        else { n += 1; w = ww; }
      }
      return n;
    };
    const lo = floor(min);
    for (let px = max * U; px > lo; px *= 0.96) {
      if (lines(px) * px * lh <= boxH) return Math.round(px);
    }
    return lo;
  };
  return {on, ts, floor, U, headline, fill};
};

// ---------------------------------------------------------------------------------------
// Heading face. One display face for headings; body and labels stay in BRAND.font.
// Supplied as a top-level render prop (project.json `heading_font`), so a trial or a
// per-series face needs no code change. Loaded with FontFace + delayRender so the first
// frame never renders in the fallback face.

export type HeadingFont = {family: string; file: string; weight?: string} | null;
export const HeadingFontContext = createContext<HeadingFont>(null);

const loaded = new Map<string, Promise<void>>();
const loadFace = (f: NonNullable<HeadingFont>) => {
  const key = `${f.family}|${f.file}`;
  if (!loaded.has(key)) {
    const handle = delayRender(`heading font ${f.family}`);
    const face = new FontFace(f.family, `url(${staticFile(f.file)})`, {weight: f.weight ?? '100 900'});
    const p = face.load().then((ff) => { (document.fonts as any).add(ff); })
      .catch((e) => { console.error(`heading font ${f.family} failed to load`, e); })
      .finally(() => continueRender(handle));
    loaded.set(key, p);
  }
};

export const HeadingFontProvider: React.FC<{font?: HeadingFont; children: React.ReactNode}> = ({font, children}) => {
  if (font) loadFace(font);
  return React.createElement(HeadingFontContext.Provider, {value: font ?? null}, children);
};

/** The font-family for a heading: the trial/series face when one is set, else BRAND.font. */
export const useHeadingFamily = () => {
  const f = useContext(HeadingFontContext);
  return f ? `"${f.family}", ${BRAND.font}` : BRAND.font;
};
