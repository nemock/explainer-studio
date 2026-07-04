import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import {colorizeText} from './colorize';

// motion-playbook §2A — the cold-open / outro punch: kicker + a big headline that
// springs in, accent words colored. fields: {kicker, headline, accent[], accentRed[], sub}
const colorize = (text: string, accent: string[] = [], accentRed: string[] = []) =>
  colorizeText(text, accent, accentRed);

export const KineticHook: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const k = spring({frame, fps, config: {damping: 200}});
  const big = spring({frame: frame - 6, fps, config: {damping: 14, stiffness: 120}});
  const sub = spring({frame: frame - 22, fps, config: {damping: 16}});

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 7%'}}>
      {fields.kicker ? (
        <div
          style={{
            fontFamily: BRAND.font,
            color: BRAND.green,
            fontWeight: 800,
            fontSize: height * 0.024,
            letterSpacing: 5,
            textTransform: 'uppercase',
            textAlign: 'center',
            opacity: k,
            transform: `translateY(${interpolate(k, [0, 1], [24, 0])}px)`,
            marginBottom: height * 0.012,
          }}
        >
          {fields.kicker}
        </div>
      ) : null}
      <div
        style={{
          fontFamily: BRAND.font,
          fontWeight: 900,
          fontSize: height * 0.085,
          lineHeight: 1.04,
          textAlign: 'center',
          transform: `scale(${big})`,
          textShadow: '0 10px 50px rgba(0,0,0,.6)',
        }}
      >
        {colorize(fields.headline || '', fields.accent, fields.accentRed)}
      </div>
      {fields.sub ? (
        <div
          style={{
            fontFamily: BRAND.font,
            fontWeight: 800,
            fontSize: height * 0.034,
            textAlign: 'center',
            marginTop: height * 0.02,
            opacity: sub,
            transform: `translateY(${interpolate(sub, [0, 1], [20, 0])}px)`,
          }}
        >
          {colorize(fields.sub, fields.accent, fields.accentRed)}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
