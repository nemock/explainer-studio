import React from 'react';
import {
  AbsoluteFill,
  Audio,
  interpolate,
  interpolateColors,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import words from './dataviz-captions.json';

const NAVY_IN = '#15314a';
const NAVY_MID = '#0d1428';
const NAVY_OUT = '#090d1c';
const RED = '#ff4d4d';
const GREEN = '#3ddc84';
const WHITE = '#f5f7ff';
const FONT = '-apple-system, "Helvetica Neue", Arial, sans-serif';

type W = {word: string; start: number; end: number};
const WORDS = words as W[];

// counter drains from the $1,000 starting float down to $1,000 in the red,
// landing on "...a thousand dollars into the red" (~23s in this take)
const DRAIN_START = 11;
const DRAIN_END = 23.6;

const fmtMoney = (n: number) =>
  (n < 0 ? '−$' : '$') + Math.abs(Math.round(n)).toLocaleString('en-US');

const Captions: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  let active = WORDS.findIndex((w) => t >= w.start && t < w.end);
  if (active === -1) for (let i = 0; i < WORDS.length; i++) if (WORDS[i].start <= t) active = i;
  if (active === -1) active = 0;
  const start = Math.max(0, active - 2);
  const win = WORDS.slice(start, start + 6);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'flex-end', paddingBottom: 70}}>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: '0 16px',
          maxWidth: 1500,
          padding: '16px 30px',
          borderRadius: 20,
          background: 'rgba(7,11,22,.5)',
        }}
      >
        {win.map((w, i) => {
          const isActive = start + i === active;
          return (
            <span
              key={start + i}
              style={{
                fontFamily: FONT,
                fontWeight: 800,
                fontSize: 44,
                color: isActive ? GREEN : WHITE,
                opacity: isActive ? 1 : 0.7,
                textShadow: '0 3px 14px rgba(0,0,0,.8)',
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

export const DataViz: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  const bgScale = interpolate(frame, [0, durationInFrames], [1, 1.06]);
  const kIntro = spring({frame: frame - 6, fps, config: {damping: 18}});

  const balance = interpolate(
    frame,
    [DRAIN_START * fps, DRAIN_END * fps],
    [1000, -1000],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );
  const numColor = interpolateColors(balance, [-1000, 0, 1000], [RED, '#cdd6ff', GREEN]);

  // balance bar: track centered on zero; fill grows right (green) or left (red)
  const TRACK = 1200;
  const frac = balance / 1000; // -1 .. 1
  const fillW = Math.abs(frac) * (TRACK / 2);
  const negative = balance < 0;

  // a small pulse when we cross into the red
  const crossed = balance <= 0;
  const pulse = crossed ? 1 + 0.04 * Math.sin((frame / fps) * 10) * Math.max(0, 1 - (frame / fps - DRAIN_END)) : 1;

  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          background: `radial-gradient(110% 90% at 50% 40%, ${NAVY_IN} 0%, ${NAVY_MID} 55%, ${NAVY_OUT} 100%)`,
          transform: `scale(${bgScale})`,
        }}
      />
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div
          style={{
            fontFamily: FONT,
            color: GREEN,
            fontWeight: 800,
            fontSize: 40,
            letterSpacing: 6,
            textTransform: 'uppercase',
            opacity: kIntro,
            transform: `translateY(${interpolate(kIntro, [0, 1], [24, 0])}px)`,
          }}
        >
          Anthropic's own Project Vend
        </div>

        {/* the counting balance */}
        <div
          style={{
            fontFamily: FONT,
            fontWeight: 900,
            fontSize: 280,
            lineHeight: 1,
            color: numColor,
            marginTop: 30,
            transform: `scale(${pulse})`,
            textShadow: '0 12px 60px rgba(0,0,0,.55)',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {fmtMoney(balance)}
        </div>

        {/* balance bar: zero in the middle */}
        <div style={{width: TRACK, height: 26, marginTop: 40, position: 'relative', background: 'rgba(255,255,255,.08)', borderRadius: 13}}>
          <div style={{position: 'absolute', left: '50%', top: -10, width: 2, height: 46, background: 'rgba(255,255,255,.35)'}} />
          <div
            style={{
              position: 'absolute',
              top: 0,
              height: '100%',
              borderRadius: 13,
              width: fillW,
              left: negative ? `calc(50% - ${fillW}px)` : '50%',
              background: negative ? RED : GREEN,
            }}
          />
        </div>
        <div
          style={{
            fontFamily: FONT,
            fontWeight: 800,
            fontSize: 38,
            color: negative ? RED : WHITE,
            opacity: 0.85,
            marginTop: 26,
            letterSpacing: 2,
          }}
        >
          {negative ? 'IN THE RED' : 'STARTING BALANCE'}
        </div>
      </AbsoluteFill>
      <Captions />
      <Audio src={staticFile('projectvend.wav')} />
    </AbsoluteFill>
  );
};
