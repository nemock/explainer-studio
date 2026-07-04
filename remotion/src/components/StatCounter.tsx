import React from 'react';
import {AbsoluteFill, interpolate, interpolateColors, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

// motion-playbook §2B — a number that counts to its figure and a bar that fills/drains,
// landing on the narration cue. fields: {kicker, from, to, prefix, label, labelNeg, cue:[a,b]}
const fmt = (n: number, prefix = '') => {
  const neg = n < 0;
  return (neg ? '−' : '') + prefix + Math.abs(Math.round(n)).toLocaleString('en-US');
};

export const StatCounter: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {height, fps} = useVideoConfig();
  const from = fields.from ?? 0;
  const to = fields.to ?? 0;
  const prefix = fields.prefix ?? '';
  // count happens over the cue window (fraction of the scene), default mid-scene.
  // cueFrames.land (a narration cue resolved by the Python spec-builder — author
  // `"cues": {"land": "<spoken phrase>"}` on the slide) makes the counter LAND on
  // the phrase: the count runs the ~1.1s up to that exact frame.
  const land: number | undefined = fields.cueFrames?.land;
  const cue = fields.cue ?? [0.28, 0.72];
  const window: [number, number] = land != null
    ? [Math.max(0, land - Math.round(1.1 * fps)), Math.max(1, land)]
    : [cue[0] * durationInFrames, cue[1] * durationInFrames];
  const value = interpolate(frame, window, [from, to], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const lo = Math.min(from, to, 0);
  const hi = Math.max(from, to, 0);
  // domain must be strictly increasing even when the range is one-sided (e.g. 0 -> -1000)
  const numColor = interpolateColors(value, [Math.min(lo, -1), 0, Math.max(hi, 1)], [BRAND.red, '#cdd6ff', BRAND.green]);
  const negative = value < 0;

  const TRACK = height * 0.62;
  const denom = Math.max(Math.abs(lo), Math.abs(hi)) || 1;
  const fillW = (Math.abs(value) / denom) * (TRACK / 2);

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      {fields.kicker ? (
        <div
          style={{
            fontFamily: BRAND.font,
            color: BRAND.green,
            fontWeight: 800,
            fontSize: height * 0.024,
            letterSpacing: 5,
            textTransform: 'uppercase',
            marginBottom: height * 0.02,
          }}
        >
          {fields.kicker}
        </div>
      ) : null}
      <div
        style={{
          fontFamily: BRAND.font,
          fontWeight: 900,
          fontSize: height * 0.17,
          lineHeight: 1,
          color: numColor,
          textShadow: '0 12px 60px rgba(0,0,0,.55)',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {fmt(value, prefix)}
      </div>
      <div style={{width: TRACK, height: height * 0.016, marginTop: height * 0.03, position: 'relative', background: 'rgba(255,255,255,.08)', borderRadius: 999}}>
        <div style={{position: 'absolute', left: '50%', top: -height * 0.006, width: 2, height: height * 0.028, background: 'rgba(255,255,255,.35)'}} />
        <div
          style={{
            position: 'absolute',
            top: 0,
            height: '100%',
            borderRadius: 999,
            width: fillW,
            left: negative ? `calc(50% - ${fillW}px)` : '50%',
            background: negative ? BRAND.red : BRAND.green,
          }}
        />
      </div>
      {fields.label || fields.labelNeg ? (
        <div
          style={{
            fontFamily: BRAND.font,
            fontWeight: 800,
            fontSize: height * 0.022,
            letterSpacing: 2,
            textTransform: 'uppercase',
            color: negative ? BRAND.red : BRAND.white,
            opacity: 0.85,
            marginTop: height * 0.02,
          }}
        >
          {negative ? fields.labelNeg || fields.label : fields.label}
        </div>
      ) : null}
      {fields.subkicker ? (
        <div style={{fontFamily: BRAND.font, color: BRAND.white, opacity: 0.75, fontWeight: 700, fontSize: height * 0.024, marginTop: height * 0.024, textAlign: 'center'}}>
          {fields.subkicker}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
