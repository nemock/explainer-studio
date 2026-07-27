import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import type {Word} from '../schema';

// Word-synced, PAGED kinetic captions (motion-playbook §2A). Baseline on every scene.
// A static block of up to MAX_WORDS words is shown; the highlight walks across them IN
// PLACE, then the whole block swaps to the next page. This replaced the earlier
// continuously-sliding window, which recomputed a word window every frame and kept every
// word in constant horizontal motion — legible but exhausting to read (operator feedback
// 2026-07-21: a viewer called it jittery/"epilepsy-inducing"). Paging cuts the motion to
// one discrete swap every ~2-3s while staying dynamic (active word still highlighted).
//
// Two hard rules for grouping words into pages:
//   1. A page never exceeds MAX_WORDS.
//   2. A page never spans a sentence boundary — broken after any word ending in . ! or ?
//      so you never see the tail of one sentence beside the head of the next. A long
//      sentence simply splits into several pages, all still within that one sentence.
//
// Theme-aware (unchanged): navy world = dark pill + white ink; paper worlds
// ('nemock-deep-dive', 'cut-bond') = cream paper-label strip + dark ink. Active-word
// accent: green for davesaunders, coral for Cut & Bond.
const MAX_WORDS = 6;
const endsSentence = (w: string): boolean => /[.!?]["')\]]?\s*$/.test(w);

type Page = {words: Word[]; startIdx: number; endIdx: number};

function buildPages(words: Word[]): Page[] {
  const pages: Page[] = [];
  let cur: Word[] = [];
  let startIdx = 0;
  for (let i = 0; i < words.length; i++) {
    if (cur.length === 0) startIdx = i;
    cur.push(words[i]);
    if (cur.length >= MAX_WORDS || endsSentence(words[i].word) || i === words.length - 1) {
      pages.push({words: cur, startIdx, endIdx: i});
      cur = [];
    }
  }
  return pages;
}

export const Captions: React.FC<{
  words: Word[];
  bottomPx: number;
  fontSize: number;
  theme?: string;
  accentColor?: string;
}> = ({words, bottomPx, fontSize, theme, accentColor}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const cutbond = theme === 'cut-bond';
  const paper = cutbond || theme === 'nemock-deep-dive';
  const pill = paper ? 'rgba(250,245,232,.92)' : 'rgba(7,11,22,.55)';
  const restInk = paper ? '#2a2622' : BRAND.white;
  const activeInk = accentColor || (cutbond ? '#ff5a4d' : BRAND.green);
  const shadow = paper ? '0 2px 6px rgba(120,92,40,.25)' : '0 3px 16px rgba(0,0,0,.8)';

  const pages = React.useMemo(() => buildPages(words || []), [words]);
  if (!words || words.length === 0) return null;
  // stay hidden before narration starts (intro sting) and after it ends (outro sting)
  if (t < words[0].start - 0.05 || t > words[words.length - 1].end + 0.4) return null;

  // active word (global index): the word being spoken, or the most recent one started
  let active = words.findIndex((w) => t >= w.start && t < w.end);
  if (active === -1) {
    for (let i = 0; i < words.length; i++) if (words[i].start <= t) active = i;
  }
  if (active === -1) active = 0;

  // the page that owns the active word. Because `active` holds on the most-recent started
  // word during pauses, the block persists until the next page's first word is actually
  // spoken — no flicker, no gaps, just a discrete swap.
  const page = pages.find((p) => active >= p.startIdx && active <= p.endIdx) || pages[0];

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'flex-end', paddingBottom: bottomPx}}>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: `${Math.round(fontSize * 0.1)}px ${Math.round(fontSize * 0.3)}px`,
          maxWidth: '86%',
          padding: `${Math.round(fontSize * 0.35)}px ${Math.round(fontSize * 0.55)}px`,
          borderRadius: 24,
          background: pill,
        }}
      >
        {page.words.map((w, i) => {
          const isActive = page.startIdx + i === active;
          return (
            <span
              key={page.startIdx + i}
              style={{
                fontFamily: BRAND.font,
                fontWeight: 900,
                fontSize,
                color: isActive ? activeInk : restInk,
                opacity: isActive ? 1 : paper ? 0.55 : 0.72,
                textShadow: shadow,
              }}
            >
              {w.word}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
