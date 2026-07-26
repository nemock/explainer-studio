import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

// BRG paper brand sting (2026-07-26) — the Base Reality Group counterpart to PaperSting.
//
// WHY ITS OWN COMPONENT (operator directive 2026-07-26): PaperSting is DAVE'S mark — the
// paper "D" card that the paper rocket flies into, wordmarked davesaunders.net, promoting
// the book/personal brand. BRG is a different brand (helping entrepreneurs and operators
// build products, roadmaps, and run their businesses better) with its own logo and its own
// site. Repainting PaperSting would have leaked BRG into every davesaunders.net deep dive,
// so BRG gets its own sting, exactly as it gets its own palette.
//
// The mark: BRG's real logo (an indigo D with a rocket knocked out of it) placed as a piece
// of cut paper — it settles onto the cream sheet with a paper drop-shadow, then the wordmark
// rises beneath. INTRO = the settle; OUTRO (fields.outro) = a calm fade-in, no re-place.
// All deterministic (frame-driven springs/interpolate only).
// Asset: public/brg_sting_mark.png (staged by remotion_engine from the brand dir).
export const BRGPaperSting: React.FC<{fields?: any; durationInFrames?: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height, durationInFrames: dur} = useVideoConfig();
  void (durationInFrames ?? dur);

  const outro = !!(fields && fields.outro);
  const subtitle = (fields && fields.subtitle) || '';
  const wordmark = (fields && fields.wordmark) || 'baserealitygroup.com';

  // BRG paper palette (matches the brg-deep-dive theme + PAPER_BRG_DEEP ink)
  const CREAM = '#f5f0eb';
  const INK = '#1b2b4b';
  const ACCENT = '#7b5bff';

  const bg = interpolate(frame, [0, outro ? 12 : 8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  // the mark places like a piece of paper: drops in, settles, tiny overshoot rotation
  const place = outro ? bg : spring({frame: frame - 4, fps, config: {damping: 13, stiffness: 120}});
  const markScale = interpolate(place, [0, 1], [outro ? 0.97 : 0.82, 1]);
  const markY = interpolate(place, [0, 1], [outro ? 0 : -height * 0.06, 0]);
  const markRot = outro ? 0 : interpolate(place, [0, 1], [-5, 0]);

  const wm = outro
    ? interpolate(frame, [10, 26], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
    : interpolate(frame, [30, 48], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const wmY = interpolate(wm, [0, 1], [height * 0.03, 0]);
  const sub = interpolate(frame, [outro ? 22 : 46, outro ? 36 : 62], [0, 1],
                          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const markSize = height * 0.34;

  return (
    <AbsoluteFill style={{background: CREAM, alignItems: 'center', justifyContent: 'center', overflow: 'hidden'}}>
      {/* soft paper light, same treatment as the other paper worlds */}
      <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 42%, rgba(255,255,255,.45), rgba(0,0,0,.05))', opacity: bg}} />

      <div style={{
        width: markSize, height: markSize,
        transform: `translateY(${markY - height * 0.04}px) scale(${markScale}) rotate(${markRot}deg)`,
        opacity: bg,
      }}>
        <Img src={staticFile('brg_sting_mark.png')} style={{
          width: '100%', height: '100%', objectFit: 'contain',
          filter: 'drop-shadow(0 14px 24px rgba(27,43,75,.20))',
        }} />
      </div>

      <div style={{
        position: 'absolute', bottom: height * (subtitle ? 0.19 : 0.17),
        opacity: wm, transform: `translateY(${wmY}px)`,
        fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.055, letterSpacing: 1,
        color: INK, textAlign: 'center',
      }}>
        {wordmark}
      </div>
      {subtitle ? (
        <div style={{
          position: 'absolute', bottom: height * 0.12, opacity: sub,
          fontFamily: BRAND.font, fontWeight: 700, fontSize: height * 0.028, letterSpacing: 3,
          color: ACCENT, textAlign: 'center', textTransform: 'lowercase',
        }}>
          {subtitle}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
