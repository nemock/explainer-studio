import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

// Paper-launch brand sting (2026-07-14). INTRO: cream paper; the paper D card settles in,
// the cream paper rocket flies in from OFF-SCREEN above trailing a fan of mixed-color paper
// flames, then drops and rotates into its slot in the D to form the finished mark; the
// wordmark rises in beneath. OUTRO (fields.outro): the finished mark + wordmark + subtitle
// fade in calmly, no relaunch. All deterministic.
// Assets: public/sting_paper_d.png, public/sting_paper_rocket.png.
export const PaperSting: React.FC<{fields?: any; durationInFrames?: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height, durationInFrames: dur} = useVideoConfig();
  void (durationInFrames ?? dur);

  const outro = !!(fields && fields.outro);
  const subtitle = (fields && fields.subtitle) || '';

  const CREAM = '#f4ecd6';
  const INK = '#2c1e4e';
  const LAND = 72;

  const bg = interpolate(frame, [0, outro ? 12 : 8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  // D card
  const dIn = outro ? bg : spring({frame: frame - 3, fps, config: {damping: 14, stiffness: 110}});
  const dScale = interpolate(dIn, [0, 1], [outro ? 0.96 : 0.86, 1]);
  const dY = interpolate(dIn, [0, 1], [outro ? 0 : -height * 0.05, 0]);

  // rocket flight (intro only)
  const flight = interpolate(frame, [10, LAND], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.32, 0.7, 0.28, 1),
  });
  const settle = spring({frame: frame - LAND, fps, config: {damping: 11, stiffness: 130}});
  const rocketAppear = outro ? bg : interpolate(frame, [6, 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const groupSize = height * 0.52;
  const rSize = groupSize * 0.62;
  const FINAL_X = -groupSize * 0.06;
  const FINAL_Y = groupSize * 0.02;
  const startX = groupSize * 0.55;
  const startY = -height * 1.02;
  const rx = outro ? FINAL_X : interpolate(flight, [0, 1], [startX, FINAL_X]);
  const ry = outro ? FINAL_Y : interpolate(flight, [0, 1], [startY, FINAL_Y]);
  const flyRot = outro ? 0 : interpolate(flight, [0, 1], [30, 0]);
  const overshoot = outro ? 0 : interpolate(settle, [0, 1], [-7, 0]);
  const rScale = interpolate(rocketAppear, [0, 1], [outro ? 0.98 : 0.9, 1]);

  const thrust = outro ? 0 : interpolate(frame, [10, LAND - 10, LAND + 4], [0, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const wm = outro
    ? interpolate(frame, [10, 26], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
    : interpolate(frame, [LAND + 8, LAND + 26], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const wmY = interpolate(wm, [0, 1], [height * 0.03, 0]);
  const sub = interpolate(frame, [outro ? 22 : LAND + 22, outro ? 36 : LAND + 38], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  // exhaust points DOWN-LEFT (opposite the up-right rocket): tip-down teardrop rotated
  // ~40-60deg clockwise. Fanned + mixed colors, longest in the middle.
  const flames = [
    {color: '#ffe9a8', w: 0.12, len: 2.6, rot: 48, ph: 0.0},
    {color: '#ffc24d', w: 0.18, len: 3.2, rot: 50, ph: 1.1},
    {color: '#ff9a3d', w: 0.22, len: 3.6, rot: 52, ph: 2.0},
    {color: '#ff6b4a', w: 0.16, len: 3.0, rot: 40, ph: 0.7},
    {color: '#e8452f', w: 0.18, len: 3.1, rot: 60, ph: 1.6},
  ];

  return (
    <AbsoluteFill style={{background: CREAM, alignItems: 'center', justifyContent: 'center', overflow: 'hidden'}}>
      <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 42%, rgba(255,255,255,.4), rgba(0,0,0,.06))', opacity: bg}} />

      <div style={{position: 'relative', width: groupSize, height: groupSize, transform: `translateY(${-height * 0.045}px)`}}>
        <Img src={staticFile('sting_paper_d.png')} style={{
          position: 'absolute', inset: 0, width: '100%', height: '100%',
          transform: `translateY(${dY}px) scale(${dScale})`, opacity: bg,
          filter: 'drop-shadow(0 16px 26px rgba(0,0,0,.16))',
        }} />

        <div style={{
          position: 'absolute', width: rSize, height: rSize,
          left: groupSize / 2 - rSize / 2, top: groupSize / 2 - rSize / 2,
          transform: `translate(${rx}px, ${ry}px) rotate(${flyRot + overshoot}deg) scale(${rScale})`,
          opacity: rocketAppear,
        }}>
          {!outro && flames.map((f, i) => {
            const flick = 0.75 + 0.25 * Math.sin(frame * 1.6 + f.ph);
            const w = rSize * f.w;
            return (
              <div key={i} style={{
                position: 'absolute', left: rSize * 0.34, top: rSize * 0.56,
                width: w, height: w * f.len,
                background: f.color,
                borderRadius: '50% 50% 50% 50% / 60% 60% 40% 40%',
                transform: `rotate(${f.rot}deg) scaleY(${thrust * flick}) scaleX(${0.85 + 0.15 * flick})`,
                transformOrigin: 'top center',
                opacity: thrust,
                boxShadow: '0 2px 6px rgba(0,0,0,.10)',
              }} />
            );
          })}
          <Img src={staticFile('sting_paper_rocket.png')} style={{
            position: 'absolute', inset: 0, width: '100%', height: '100%',
            filter: 'drop-shadow(0 9px 15px rgba(0,0,0,.22))',
          }} />
        </div>
      </div>

      <div style={{
        position: 'absolute', bottom: height * (subtitle ? 0.17 : 0.15), opacity: wm, transform: `translateY(${wmY}px)`,
        fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.06, letterSpacing: 2,
        color: INK, textAlign: 'center',
      }}>
        FOUNDERS WHO FINISH
      </div>
      {subtitle ? (
        <div style={{
          position: 'absolute', bottom: height * 0.11, opacity: sub,
          fontFamily: BRAND.font, fontWeight: 700, fontSize: height * 0.03, letterSpacing: 3,
          color: '#6a4bb0', textAlign: 'center', textTransform: 'lowercase',
        }}>
          {subtitle}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
