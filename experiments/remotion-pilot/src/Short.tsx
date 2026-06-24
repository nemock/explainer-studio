import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import captions from './captions.json';

// Brand palette (matches the deck/thumbnail system)
const NAVY_IN = '#15314a';
const NAVY_MID = '#0d1428';
const NAVY_OUT = '#090d1c';
const RED = '#ff4d4d';
const GREEN = '#3ddc84';
const WHITE = '#f5f7ff';
const FONT =
  '-apple-system, "Helvetica Neue", Arial, sans-serif';

const HOOK_END = 6.6;
const BODY_END = 37.56;

type Word = {word: string; slide: string; start: number; end: number};
const WORDS = captions as Word[];

// when does the narrator say "...lock-in"? drive the highlight off the real timing
const lockWord = WORDS.find((w) => w.word.toLowerCase().includes('lock'));
const HIGHLIGHT_AT = lockWord ? lockWord.start : 20;

const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  // very slow breathing zoom so the bg isn't dead-static
  const scale = interpolate(frame, [0, durationInFrames], [1, 1.08]);
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(120% 90% at 50% 38%, ${NAVY_IN} 0%, ${NAVY_MID} 55%, ${NAVY_OUT} 100%)`,
        transform: `scale(${scale})`,
      }}
    />
  );
};

const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const k = spring({frame, fps, config: {damping: 200}});
  const big = spring({frame: frame - 8, fps, config: {damping: 14, stiffness: 120}});
  const line2 = spring({frame: frame - 26, fps, config: {damping: 16}});
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: 80}}>
      <div
        style={{
          fontFamily: FONT,
          color: GREEN,
          fontWeight: 800,
          fontSize: 46,
          letterSpacing: 6,
          textTransform: 'uppercase',
          opacity: k,
          transform: `translateY(${interpolate(k, [0, 1], [30, 0])}px)`,
        }}
      >
        Anthropic's Founder Playbook
      </div>
      <div
        style={{
          fontFamily: FONT,
          color: WHITE,
          fontWeight: 900,
          fontSize: 230,
          lineHeight: 1,
          marginTop: 18,
          transform: `scale(${big})`,
          textShadow: '0 10px 50px rgba(0,0,0,.6)',
        }}
      >
        PAGE 30
      </div>
      <div
        style={{
          fontFamily: FONT,
          color: WHITE,
          fontWeight: 800,
          fontSize: 64,
          marginTop: 26,
          opacity: line2,
          transform: `translateY(${interpolate(line2, [0, 1], [24, 0])}px)`,
        }}
      >
        the heading I read <span style={{color: RED}}>twice</span>
      </div>
    </AbsoluteFill>
  );
};

const Body: React.FC = () => {
  const frame = useCurrentFrame(); // relative to body start
  const {fps} = useVideoConfig();
  const intro = spring({frame, fps, config: {damping: 18, stiffness: 90}});
  const kb = interpolate(frame, [0, (BODY_END - HOOK_END) * fps], [1, 1.07]); // ken burns
  const cardScale = interpolate(intro, [0, 1], [0.9, 1]) * kb;

  // green marker wipe over "Create workflow lock-in", timed to the narration
  const hlLocal = HIGHLIGHT_AT - HOOK_END; // seconds into the body
  const hlW = interpolate(
    frame,
    [hlLocal * fps, (hlLocal + 1.4) * fps],
    [0, 40],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: 70}}>
      <div
        style={{
          fontFamily: FONT,
          color: GREEN,
          fontWeight: 800,
          fontSize: 40,
          letterSpacing: 4,
          textTransform: 'uppercase',
          opacity: intro,
          marginBottom: 34,
        }}
      >
        An actual section heading
      </div>
      <div
        style={{
          position: 'relative',
          width: 940,
          background: '#fff',
          borderRadius: 32,
          padding: 30,
          boxShadow: '0 40px 120px rgba(0,0,0,.55)',
          transform: `scale(${cardScale})`,
        }}
      >
        <Img src={staticFile('p30_lockin.png')} style={{width: '100%', display: 'block', borderRadius: 8}} />
        {/* marker highlight over the heading line */}
        <div
          style={{
            position: 'absolute',
            top: '36%',
            left: '6.5%',
            height: '12%',
            width: `${hlW}%`,
            background: 'rgba(61,220,132,.42)',
            borderRadius: 8,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const a = spring({frame, fps, config: {damping: 18}});
  const b = spring({frame: frame - 22, fps, config: {damping: 16}});
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: 90}}>
      <div
        style={{
          fontFamily: FONT,
          color: WHITE,
          fontWeight: 900,
          fontSize: 86,
          textAlign: 'center',
          lineHeight: 1.08,
          opacity: a,
          transform: `translateY(${interpolate(a, [0, 1], [30, 0])}px)`,
        }}
      >
        Useful advice, or a <span style={{color: RED}}>sales funnel?</span>
      </div>
      <div
        style={{
          fontFamily: FONT,
          color: GREEN,
          fontWeight: 800,
          fontSize: 54,
          textAlign: 'center',
          marginTop: 40,
          opacity: b,
          transform: `translateY(${interpolate(b, [0, 1], [24, 0])}px)`,
        }}
      >
        Tell which sentence is which.
      </div>
    </AbsoluteFill>
  );
};

// TikTok-style word-windowed kinetic captions, synced to the alignment
const Captions: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  let active = WORDS.findIndex((w) => t >= w.start && t < w.end);
  if (active === -1) {
    // between words: stick to the most recent one
    for (let i = 0; i < WORDS.length; i++) {
      if (WORDS[i].start <= t) active = i;
    }
  }
  if (active === -1) active = 0;
  const start = Math.max(0, active - 2);
  const win = WORDS.slice(start, start + 5);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'flex-end', paddingBottom: 360}}>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: '0 18px',
          maxWidth: 900,
          padding: '22px 34px',
          borderRadius: 26,
          background: 'rgba(7,11,22,.55)',
        }}
      >
        {win.map((w, i) => {
          const isActive = start + i === active;
          return (
            <span
              key={start + i}
              style={{
                fontFamily: FONT,
                fontWeight: 900,
                fontSize: 62,
                color: isActive ? GREEN : WHITE,
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

export const Short: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  return (
    <AbsoluteFill>
      <Background />
      {t < HOOK_END ? <Hook /> : t < BODY_END ? <Body /> : <Outro />}
      <Captions />
      <Audio src={staticFile('narration.wav')} />
    </AbsoluteFill>
  );
};
