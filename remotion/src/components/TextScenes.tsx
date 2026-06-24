import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

const lc = (s: string) => s.replace(/[^a-z0-9]/gi, '').toLowerCase();
const colorize = (text: string, accent: string[] = [], red: string[] = []) => {
  const a = (accent || []).flatMap((s) => s.split(' ')).map(lc);
  const r = (red || []).flatMap((s) => s.split(' ')).map(lc);
  const parts = String(text || '').split(' ');
  return parts.map((w, i) => (
    <span key={i} style={{color: r.includes(lc(w)) ? BRAND.red : a.includes(lc(w)) ? BRAND.green : 'inherit'}}>
      {w}{i < parts.length - 1 ? ' ' : ''}
    </span>
  ));
};

const Kicker: React.FC<{text?: string; o: number; height: number}> = ({text, o, height}) =>
  text ? (
    <div style={{fontFamily: BRAND.font, color: BRAND.green, fontWeight: 800, fontSize: height * 0.024, letterSpacing: 5, textTransform: 'uppercase', textAlign: 'center', opacity: o, marginBottom: height * 0.018}}>
      {text}
    </div>
  ) : null;

// statement -> a headline that scales/fades in. fields: {kicker, headline, accent, accentRed}
export const KineticHeadline: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const s = spring({frame, fps, config: {damping: 18, stiffness: 90}});
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 8%', color: BRAND.white}}>
      <Kicker text={fields.kicker} o={s} height={height} />
      <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.07, lineHeight: 1.07, textAlign: 'center', opacity: s, transform: `translateY(${interpolate(s, [0, 1], [28, 0])}px)`, textShadow: '0 10px 50px rgba(0,0,0,.6)'}}>
        {colorize(fields.headline, fields.accent, fields.accentRed)}
      </div>
    </AbsoluteFill>
  );
};

// quote -> big quote + attribution reveal. fields: {quote, attribution}
export const Quote: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const q = spring({frame, fps, config: {damping: 18}});
  const at = spring({frame: frame - 18, fps, config: {damping: 16}});
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 9%'}}>
      <div style={{fontFamily: BRAND.font, color: BRAND.white, fontWeight: 800, fontSize: height * 0.058, lineHeight: 1.25, textAlign: 'center', opacity: q, transform: `translateY(${interpolate(q, [0, 1], [26, 0])}px)`, textShadow: '0 10px 40px rgba(0,0,0,.6)'}}>
        {fields.quote}
      </div>
      {fields.attribution ? (
        <div style={{fontFamily: BRAND.font, color: BRAND.green, fontWeight: 800, fontSize: height * 0.028, marginTop: height * 0.03, opacity: at}}>
          — {fields.attribution}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// punch -> one giant word, max energy (the seam). fields: {word, kicker, kind:'good'|'bad'}
export const PunchWord: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const p = spring({frame, fps, config: {damping: 9, stiffness: 140}});
  const color = fields.kind === 'good' ? BRAND.green : fields.kind === 'bad' ? BRAND.red : BRAND.white;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 6%'}}>
      <Kicker text={fields.kicker} o={interpolate(p, [0, 1], [0, 1])} height={height} />
      <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.2, lineHeight: 1, color, textTransform: 'uppercase', transform: `scale(${p})`, textShadow: '0 16px 70px rgba(0,0,0,.6)'}}>
        {fields.word || fields.headline}
      </div>
    </AbsoluteFill>
  );
};

// reframe -> "before" struck through, dissolving into "after". fields: {before, after}
export const Reframe: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const a = spring({frame, fps, config: {damping: 18}});
  const flip = spring({frame: frame - 26, fps, config: {damping: 16}});
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 8%', flexDirection: 'column'}}>
      <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.06, color: BRAND.white, opacity: interpolate(flip, [0, 1], [1, 0.35]), textDecoration: 'line-through', textDecorationColor: BRAND.red, textAlign: 'center'}}>
        {fields.before}
      </div>
      <div style={{fontFamily: BRAND.font, color: BRAND.green, fontWeight: 900, fontSize: height * 0.04, margin: `${height * 0.02}px 0`, opacity: a}}>↓</div>
      <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.078, color: BRAND.white, textAlign: 'center', opacity: flip, transform: `scale(${interpolate(flip, [0, 1], [0.85, 1])})`, textShadow: '0 10px 50px rgba(0,0,0,.6)'}}>
        {fields.after}
      </div>
    </AbsoluteFill>
  );
};

// list / steps -> numbered items revealing one by one. fields: {kicker, items[]}
export const BuildList: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const items: string[] = fields.items || [];
  const per = durationInFrames / Math.max(1, items.length + 1);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 10%'}}>
      <div style={{maxWidth: '100%'}}>
        <Kicker text={fields.kicker} o={spring({frame, fps, config: {damping: 18}})} height={height} />
        {items.map((it, i) => {
          const e = spring({frame: frame - i * per, fps, config: {damping: 18}});
          return (
            <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: height * 0.02, opacity: e, transform: `translateX(${interpolate(e, [0, 1], [-30, 0])}px)`, marginBottom: height * 0.022}}>
              <span style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.05, color: BRAND.green}}>{i + 1}</span>
              <span style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.044, color: BRAND.white, lineHeight: 1.1}}>{it}</span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// compare -> two columns animating in. fields: {left:{title,value}, right:{title,value}}
export const SideBySide: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const l = spring({frame, fps, config: {damping: 18}});
  const r = spring({frame: frame - 10, fps, config: {damping: 18}});
  const col = (d: any, o: number, dir: number, bad?: boolean) => (
    <div style={{flex: 1, padding: height * 0.03, borderRadius: 20, background: 'rgba(255,255,255,.05)', border: `2px solid ${bad ? 'rgba(255,77,77,.5)' : 'rgba(61,220,132,.4)'}`, opacity: o, transform: `translateX(${interpolate(o, [0, 1], [dir * 40, 0])}px)`}}>
      <div style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.024, letterSpacing: 3, textTransform: 'uppercase', color: bad ? BRAND.red : BRAND.green, marginBottom: height * 0.018}}>{d?.title}</div>
      <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.044, color: BRAND.white, lineHeight: 1.12}}>{d?.value}</div>
    </div>
  );
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 7%'}}>
      <div style={{display: 'flex', gap: height * 0.03, width: '100%', alignItems: 'stretch'}}>
        {col(fields.left, l, -1, false)}
        {col(fields.right, r, 1, true)}
      </div>
    </AbsoluteFill>
  );
};
