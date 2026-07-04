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

export const colorizeText = (
  text: string | undefined,
  accent: string[] = [],
  accent2: string[] = []
): React.ReactNode => {
  const a = new Set((accent || []).flatMap((s) => s.split(/\s+/)).map(norm));
  const a2 = new Set((accent2 || []).flatMap((s) => s.split(/\s+/)).map(norm));
  const parts = String(text || '').split(/(\s+)/);
  return parts.map((tok, i) => {
    const key = norm(tok);
    if (key && a.has(key)) return <span key={i} style={{color: BRAND.green}}>{tok}</span>;
    if (key && a2.has(key)) return <span key={i} style={{color: BRAND.red}}>{tok}</span>;
    return tok;
  });
};
