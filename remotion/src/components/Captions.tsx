import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import type {Word} from '../schema';

// Word-synced, windowed kinetic captions (motion-playbook §2A). Baseline on every
// scene. Reads the alignment words and highlights the active word in green.
export const Captions: React.FC<{
  words: Word[];
  bottomPx: number;
  fontSize: number;
}> = ({words, bottomPx, fontSize}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  if (!words || words.length === 0) return null;

  let active = words.findIndex((w) => t >= w.start && t < w.end);
  if (active === -1) {
    for (let i = 0; i < words.length; i++) if (words[i].start <= t) active = i;
  }
  if (active === -1) active = 0;

  const start = Math.max(0, active - 2);
  const win = words.slice(start, start + 6);

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'flex-end', paddingBottom: bottomPx}}>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: `0 ${Math.round(fontSize * 0.3)}px`,
          maxWidth: '86%',
          padding: `${Math.round(fontSize * 0.35)}px ${Math.round(fontSize * 0.55)}px`,
          borderRadius: 24,
          background: 'rgba(7,11,22,.55)',
        }}
      >
        {win.map((w, i) => {
          const isActive = start + i === active;
          return (
            <span
              key={start + i}
              style={{
                fontFamily: BRAND.font,
                fontWeight: 900,
                fontSize,
                color: isActive ? BRAND.green : BRAND.white,
                opacity: isActive ? 1 : 0.72,
                textShadow: '0 3px 16px rgba(0,0,0,.8)',
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
