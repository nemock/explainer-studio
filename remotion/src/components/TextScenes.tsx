import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import {colorizeText} from './colorize';

const colorize = (text: string, accent: string[] = [], red: string[] = []) =>
  colorizeText(text, accent, red);

const SubKicker: React.FC<{text?: string; height: number}> = ({text, height}) =>
  text ? (
    <div style={{fontFamily: BRAND.font, color: BRAND.white, opacity: 0.75, fontWeight: 700, fontSize: height * 0.03, marginTop: height * 0.02, textAlign: 'center'}}>
      {text}
    </div>
  ) : null;

const Kicker: React.FC<{text?: string; o: number; height: number}> = ({text, o, height}) =>
  text ? (
    <div style={{fontFamily: BRAND.font, color: BRAND.green, fontWeight: 800, fontSize: height * 0.024, letterSpacing: 5, textTransform: 'uppercase', textAlign: 'center', opacity: o, marginBottom: height * 0.018}}>
      {text}
    </div>
  ) : null;

// statement -> a headline that scales/fades in. fields: {kicker, headline, accent, accentRed, subkicker}
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
      <SubKicker text={fields.subkicker} height={height} />
    </AbsoluteFill>
  );
};

// define -> a term + its definition. fields: {kicker, term, definition, accent, accentRed}
export const DefineTerm: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const t = spring({frame, fps, config: {damping: 18, stiffness: 90}});
  const d = spring({frame: frame - 10, fps, config: {damping: 18}});
  const termSize = (fields.term || '').length > 16 ? height * 0.06 : height * 0.075;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 9%'}}>
      <Kicker text={fields.kicker} o={t} height={height} />
      <div style={{fontFamily: BRAND.font, color: BRAND.green, fontWeight: 900, fontSize: termSize, lineHeight: 1.1, textAlign: 'center', opacity: t, transform: `translateY(${interpolate(t, [0, 1], [24, 0])}px)`, textShadow: '0 10px 50px rgba(0,0,0,.6)'}}>
        {colorize(fields.term, fields.accent, fields.accentRed)}
      </div>
      <div style={{fontFamily: BRAND.font, color: BRAND.white, fontWeight: 700, fontSize: height * 0.038, lineHeight: 1.3, textAlign: 'center', maxWidth: '85%', marginTop: height * 0.028, opacity: d, transform: `translateY(${interpolate(d, [0, 1], [18, 0])}px)`}}>
        {fields.definition}
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
// OR the headline variant: {headline, accent, accentRed} — per-word accent coloring takes
// precedence over the whole-word `kind` color when accent/accentRed are actually set.
export const PunchWord: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const p = spring({frame, fps, config: {damping: 9, stiffness: 140}});
  const color = fields.kind === 'good' ? BRAND.green : fields.kind === 'bad' ? BRAND.red : BRAND.white;
  const text = fields.word || fields.headline;
  const hasAccent = (fields.accent && fields.accent.length) || (fields.accentRed && fields.accentRed.length);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 6%'}}>
      <Kicker text={fields.kicker} o={interpolate(p, [0, 1], [0, 1])} height={height} />
      <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.2, lineHeight: 1.02, color, textTransform: 'uppercase', transform: `scale(${p})`, textShadow: '0 16px 70px rgba(0,0,0,.6)', textAlign: 'center', maxWidth: '92%', whiteSpace: 'pre-line', textWrap: 'balance' as any}}>
        {hasAccent ? colorize(text, fields.accent, fields.accentRed) : text}
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

// list / steps -> numbered items revealing one by one. fields: {kicker, items[], title, accent, accentRed}
export const BuildList: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const items: string[] = fields.items || [];
  const itemTimes: (number | null)[] | undefined = fields.itemTimes;
  const per = durationInFrames / Math.max(1, items.length + 1);
  const titleO = spring({frame: frame - 6, fps, config: {damping: 18}});
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 10%'}}>
      <div style={{maxWidth: '100%'}}>
        <Kicker text={fields.kicker} o={spring({frame, fps, config: {damping: 18}})} height={height} />
        {fields.title ? (
          <div style={{fontFamily: BRAND.font, color: BRAND.white, fontWeight: 800, fontSize: height * 0.036, lineHeight: 1.2, opacity: titleO, marginBottom: height * 0.024, transform: `translateY(${interpolate(titleO, [0, 1], [16, 0])}px)`}}>
            {colorize(fields.title, fields.accent, fields.accentRed)}
          </div>
        ) : null}
        {items.map((it, i) => {
          // appear AS the item is spoken (itemTimes from alignment), else even stagger
          const appear = itemTimes && itemTimes[i] != null ? (itemTimes[i] as number) : i * per;
          const e = spring({frame: frame - appear, fps, config: {damping: 18}});
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

// timeline -> events appearing along a line in time.
// fields: {kicker, events:[{date,label}], itemTimes?: (number|null)[]} — cue-synced.
export const Timeline: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const events: any[] = fields.events || [];
  const itemTimes: (number | null)[] | undefined = fields.itemTimes;
  const per = durationInFrames / Math.max(1, events.length + 1);
  const lineGrow = interpolate(frame, [0, durationInFrames * 0.85], [0, 100], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 9%'}}>
      <div style={{width: '100%', maxWidth: '90%'}}>
        <Kicker text={fields.kicker} o={spring({frame, fps, config: {damping: 18}})} height={height} />
        <div style={{position: 'relative', paddingLeft: height * 0.03}}>
          <div style={{position: 'absolute', left: 0, top: 0, width: 4, height: `${lineGrow}%`, background: BRAND.green, borderRadius: 4}} />
          {events.map((e, i) => {
            const at = itemTimes && itemTimes[i] != null ? (itemTimes[i] as number) : (i + 0.5) * per;
            const o = spring({frame: frame - at, fps, config: {damping: 18}});
            return (
              <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: height * 0.02, opacity: o, transform: `translateX(${interpolate(o, [0, 1], [-24, 0])}px)`, marginBottom: height * 0.03}}>
                <span style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.03, color: BRAND.green, minWidth: height * 0.14}}>{e.date}</span>
                <span style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.038, color: BRAND.white, lineHeight: 1.12}}>{e.label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
