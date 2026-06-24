import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

const Kicker: React.FC<{text?: string; o: number; height: number}> = ({text, o, height}) =>
  text ? (
    <div style={{fontFamily: BRAND.font, color: BRAND.green, fontWeight: 800, fontSize: height * 0.024, letterSpacing: 5, textTransform: 'uppercase', textAlign: 'center', opacity: o, marginBottom: height * 0.035}}>
      {text}
    </div>
  ) : null;

// trend / crash -> a line chart drawn on left-to-right (motion-playbook §2B). The plummet
// reads as gut-punch. fields: {kicker, points:[numbers], endLabel, kind:'good'|'bad'}
export const DrawLine: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height, width} = useVideoConfig();
  const pts: number[] = (fields.points && fields.points.length ? fields.points : [10, 30, 25, 60, 45, 80]);
  const W = width * 0.62, H = height * 0.42;
  const max = Math.max(...pts), min = Math.min(...pts);
  const xy = pts.map((p, i) => [(i / (pts.length - 1)) * W, H - ((p - min) / (max - min || 1)) * H]);
  const d = xy.map((c, i) => `${i ? 'L' : 'M'}${c[0].toFixed(1)} ${c[1].toFixed(1)}`).join(' ');
  const draw = interpolate(frame, [0, durationInFrames * 0.8], [1, 0], {extrapolateRight: 'clamp'});
  const stroke = fields.kind === 'bad' ? BRAND.red : BRAND.green;
  const dotI = Math.min(pts.length - 1, Math.floor(interpolate(frame, [0, durationInFrames * 0.8], [0, pts.length - 1], {extrapolateRight: 'clamp'})));
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <Kicker text={fields.kicker} o={spring({frame, fps, config: {damping: 18}})} height={height} />
      <svg width={W} height={H} style={{overflow: 'visible'}}>
        <path d={d} fill="none" stroke={stroke} strokeWidth={height * 0.008} strokeLinecap="round" strokeLinejoin="round"
              strokeDasharray={6000} strokeDashoffset={6000 * draw} style={{filter: `drop-shadow(0 0 18px ${stroke}88)`}} />
        <circle cx={xy[dotI][0]} cy={xy[dotI][1]} r={height * 0.011} fill={stroke} />
      </svg>
      {fields.endLabel ? (
        <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.05, color: stroke, marginTop: height * 0.03, opacity: interpolate(frame, [durationInFrames * 0.7, durationInFrames * 0.85], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
          {fields.endLabel}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// waterfall -> cumulative bars building (motion-playbook §2B). fields: {kicker, start, steps[], end}
export const Waterfall: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const bars = [fields.start, ...(fields.steps || []), fields.end].filter(Boolean);
  const per = durationInFrames / Math.max(1, bars.length + 1);
  const maxV = Math.max(1, ...bars.map((b: any) => Math.abs(b.value || 0)));
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <Kicker text={fields.kicker} o={spring({frame, fps, config: {damping: 18}})} height={height} />
      <div style={{display: 'flex', alignItems: 'flex-end', gap: height * 0.02, height: height * 0.4}}>
        {bars.map((b: any, i: number) => {
          const g = spring({frame: frame - i * per, fps, config: {damping: 16}});
          const isEnd = i === bars.length - 1 || i === 0;
          const col = (b.kind === 'bad') ? BRAND.red : isEnd ? BRAND.green : 'rgba(255,255,255,.5)';
          return (
            <div key={i} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: height * 0.012}}>
              <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.026, color: BRAND.white}}>{b.value}</div>
              <div style={{width: height * 0.12, height: (Math.abs(b.value) / maxV) * height * 0.32 * g, background: col, borderRadius: 8}} />
              <div style={{fontFamily: BRAND.font, fontWeight: 700, fontSize: height * 0.02, color: BRAND.white, opacity: 0.75, maxWidth: height * 0.16, textAlign: 'center'}}>{b.label}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// pictograph -> X-of-Y dots filling (motion-playbook §2B). fields: {kicker, filled, total, label, kind}
export const Pictograph: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const total = fields.total || 100, filled = fields.filled || 0;
  const shown = Math.round(interpolate(frame, [0, durationInFrames * 0.7], [0, filled], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  const cols = Math.ceil(Math.sqrt(total * 1.6));
  const col = fields.kind === 'good' ? BRAND.green : BRAND.red;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <Kicker text={fields.kicker} o={spring({frame, fps, config: {damping: 18}})} height={height} />
      <div style={{display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: height * 0.01, maxWidth: '70%'}}>
        {Array.from({length: total}).map((_, i) => (
          <div key={i} style={{width: height * 0.022, height: height * 0.022, borderRadius: '50%', background: i < shown ? col : 'rgba(255,255,255,.12)'}} />
        ))}
      </div>
      {fields.label ? (
        <div style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.03, color: BRAND.white, marginTop: height * 0.035, textAlign: 'center', maxWidth: '70%'}}>
          <span style={{color: col, fontWeight: 900}}>{shown}</span> {fields.label}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ring / progress -> a circular sweep to a percentage (motion-playbook §2B). fields: {kicker, value, label}
export const Ring: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const target = fields.value || 0;
  const v = interpolate(frame, [0, durationInFrames * 0.7], [0, target], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const R = height * 0.16, C = 2 * Math.PI * R;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <Kicker text={fields.kicker} o={spring({frame, fps, config: {damping: 18}})} height={height} />
      <div style={{position: 'relative', width: R * 2.4, height: R * 2.4, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <svg width={R * 2.4} height={R * 2.4} style={{position: 'absolute', transform: 'rotate(-90deg)'}}>
          <circle cx={R * 1.2} cy={R * 1.2} r={R} fill="none" stroke="rgba(255,255,255,.1)" strokeWidth={height * 0.018} />
          <circle cx={R * 1.2} cy={R * 1.2} r={R} fill="none" stroke={BRAND.green} strokeWidth={height * 0.018} strokeLinecap="round"
                  strokeDasharray={C} strokeDashoffset={C * (1 - v / 100)} style={{filter: `drop-shadow(0 0 16px ${BRAND.green}aa)`}} />
        </svg>
        <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.075, color: BRAND.white, fontVariantNumeric: 'tabular-nums'}}>{Math.round(v)}%</div>
      </div>
      {fields.label ? <div style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.028, color: BRAND.white, opacity: 0.8, marginTop: height * 0.03}}>{fields.label}</div> : null}
    </AbsoluteFill>
  );
};

// funnel -> stages narrowing, revealing top-to-bottom (motion-playbook §2C). fields: {kicker, stages:[{label,value}]}
export const Funnel: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const stages = fields.stages || [];
  const per = durationInFrames / Math.max(1, stages.length + 1);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <Kicker text={fields.kicker} o={spring({frame, fps, config: {damping: 18}})} height={height} />
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: height * 0.012}}>
        {stages.map((s: any, i: number) => {
          const e = spring({frame: frame - i * per, fps, config: {damping: 16}});
          const w = interpolate(i, [0, Math.max(1, stages.length - 1)], [62, 26]); // % width narrowing
          return (
            <div key={i} style={{width: `${w}vw`, padding: height * 0.022, borderRadius: 12, background: `rgba(61,220,132,${0.5 - i * 0.07})`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', opacity: e, transform: `scaleY(${e})`}}>
              <span style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.032, color: BRAND.white}}>{s.label}</span>
              <span style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.034, color: BRAND.white}}>{s.value}</span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
