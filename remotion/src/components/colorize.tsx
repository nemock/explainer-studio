import React from 'react';
import {BRAND} from '../brand';

// Shared accent-word colorizer for headline/title text (motion-playbook §1: the fixed
// 2-color scheme, `accent` -> green, `accent2` -> red, locked across every component —
// do not reintroduce a per-component reimplementation of this).
//
// Accepts single words OR multi-word phrases in `accent`/`accent2`. Each phrase is split
// into its constituent words before matching, so `accent: ["the evidence"]` tints BOTH
// "the" AND "evidence" wherever they appear as tokens in `text`. A naive whole-phrase
// match fails here because `text` is tokenized on whitespace one word at a time — a
// multi-word key can never equal a single-word token, so nothing would ever highlight.
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9']/g, '');

// `accentColor` is the THEME's accent (ink.accent), not a fixed green. ink.ts defines
// accent as "the ONE accent (kicker + highlighted words)", but this function hardcoded
// BRAND.green, so on every theme whose accent is not green — plg-guide rust, wte-guide
// gold, cut-bond teal, BRG indigo, the six show worlds — a headline's accent words came
// out studio green while the kicker directly above them rendered the real accent. Caught
// on plg-guide module 1's closing card, 2026-08-12. Defaults to green so any call site
// that does not pass a color behaves exactly as before.
export const colorizeText = (
  text: string | undefined,
  accent: string[] = [],
  accent2: string[] = [],
  accentColor: string = BRAND.green,
  // Same reasoning as accentColor: accent2 is the world's DANGER colour, not a fixed
  // studio scarlet. Callers pass ink.danger; the default keeps every old call unchanged.
  dangerColor: string = BRAND.red
): React.ReactNode => {
  const a = new Set((accent || []).flatMap((s) => s.split(/\s+/)).map(norm));
  const a2 = new Set((accent2 || []).flatMap((s) => s.split(/\s+/)).map(norm));
  const parts = String(text || '').split(/(\s+)/);
  return parts.map((tok, i) => {
    const key = norm(tok);
    if (key && a.has(key)) return <span key={i} style={{color: accentColor}}>{tok}</span>;
    if (key && a2.has(key)) return <span key={i} style={{color: dangerColor}}>{tok}</span>;
    return tok;
  });
};
