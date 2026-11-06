import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import {useInk} from '../ink';
import {useTypeScale} from '../type';
import {useWorld} from './PaperWorld';
import {PaperSheet, litBoxShadow} from './PaperNote';

// motion-playbook §2F — the reusable FWF brand sting (intro/outro). Wordmark scales +
// glows in with an accent sweep. fields: {title, subtitle?}
export const BrandSting: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height, width} = useVideoConfig();
  const inn = spring({frame, fps, config: {damping: 13, stiffness: 120}});
  const sweepX = interpolate(frame, [6, 30], [-width, width], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const out = interpolate(frame, [durationInFrames - 10, durationInFrames], [1, 0], {extrapolateLeft: 'clamp'});
  const title = fields.title || 'FOUNDERS WHO FINISH';
  // paper worlds: BRAND.white on cream was invisible (found in the 2026-11-01 visual review)
  const ink = useInk();
  const {ts} = useTypeScale();
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', opacity: out, overflow: 'hidden'}}>
      <div style={{position: 'relative'}}>
        <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.072, letterSpacing: 2, color: ink.paper ? ink.body : BRAND.white, textAlign: 'center', transform: `scale(${interpolate(inn, [0, 1], [0.7, 1])})`, opacity: inn, textShadow: ink.paper ? 'none' : `0 0 ${40 * inn}px rgba(61,220,132,.5), 0 12px 60px rgba(0,0,0,.7)`}}>
          {title}
        </div>
        {/* accent light sweep across the wordmark */}
        <AbsoluteFill style={{background: `linear-gradient(105deg, transparent 40%, rgba(61,220,132,.55) 50%, transparent 60%)`, transform: `translateX(${sweepX}px)`, mixBlendMode: 'screen'}} />
      </div>
      {fields.subtitle ? (
        <div style={{fontFamily: BRAND.font, fontWeight: 700, fontSize: ts('eyebrow', height * 0.026), color: BRAND.green, marginTop: height * 0.02, opacity: interpolate(frame, [18, 34], [0, 1], {extrapolateRight: 'clamp'}), letterSpacing: 4, textTransform: 'uppercase'}}>
          {fields.subtitle}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// motion-playbook §2C — a process flow: nodes connected by arrows, revealing in sequence.
// fields: {kicker, steps:[string | {title,text}], itemTimes?: (number|null)[]}
// itemTimes (narration-cue frames, resolved by the Python spec-builder) land each node
// AS it's spoken; null/absent entries fall back to the even stagger.
export const StepFlow: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height, width} = useVideoConfig();
  const raw = fields.steps || [];
  const steps = raw.map((s: any) => (typeof s === 'string' ? {title: s} : s));
  const itemTimes: (number | null)[] | undefined = fields.itemTimes;
  const per = durationInFrames / Math.max(1, steps.length + 1);
  const appearAt = (i: number) => (itemTimes && itemTimes[i] != null ? (itemTimes[i] as number) : i * per);
  const ink = useInk();
  const {on, ts} = useTypeScale();
  const lit = Boolean(useWorld().lit) && ink.paper;
  // a word never overflows its card: the title steps down to fit the longest word, not under 36 px
  const colW = (width * 0.88 - height * 0.07 * (steps.length - 1)) / Math.max(1, steps.length) - height * 0.05;
  const longest = Math.max(1, ...steps.map((s: any) => Math.max(0, ...String(s.title || '').split(/\s+/).map((w) => w.length))));
  const titlePx = on ? Math.max(height * 0.034, Math.min(ts('body', 0), colW / (longest * 0.58))) : height * 0.036;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: `0 6% ${on ? height * 0.14 : 0}px`}}>
      <div style={{width: '100%'}}>
        {fields.kicker ? (
          <div style={{fontFamily: BRAND.font, color: on ? ink.accent : BRAND.green, fontWeight: 800, fontSize: ts('eyebrow', height * 0.024), letterSpacing: on ? 3 : 5, textTransform: 'uppercase', textAlign: 'center', opacity: spring({frame, fps, config: {damping: 18}}), marginBottom: height * 0.04}}>
            {fields.kicker}
          </div>
        ) : null}
        <div style={{display: 'flex', alignItems: 'center', justifyContent: 'center', gap: height * 0.012, flexWrap: 'nowrap'}}>
          {steps.map((s: any, i: number) => {
            const at = appearAt(i);
            const prevAt = i > 0 ? appearAt(i - 1) : 0;
            const e = spring({frame: frame - at, fps, config: {damping: 16, stiffness: 110}});
            const arrow = i > 0 ? interpolate(frame, [Math.max(prevAt, at - 0.5 * per), at], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
            return (
              <React.Fragment key={i}>
                {i > 0 ? (
                  <div style={{color: on ? ink.accent : BRAND.green, fontSize: height * 0.05, fontWeight: 900, opacity: arrow, transform: `translateX(${interpolate(arrow, [0, 1], [-10, 0])}px)`}}>→</div>
                ) : null}
                <div style={{flex: '1 1 0', minWidth: 0, position: 'relative', padding: height * 0.025, borderRadius: lit ? 5 : 18,
                             ...(lit ? {boxShadow: litBoxShadow(height)} : {background: ink.cardBg, border: '2px solid rgba(61,220,132,.4)'}),
                             textAlign: 'center', opacity: e, transform: `translateY(${interpolate(e, [0, 1], [26, 0])}px) scale(${interpolate(e, [0, 1], [0.9, 1])})`}}>
                  {lit ? <PaperSheet id={`flow:${i}:${s.title ?? ''}`} radius={5} tint="#fffcf5" /> : null}
                  <div style={{position: 'relative', fontFamily: BRAND.font, fontWeight: 900, fontSize: titlePx, color: ink.body, lineHeight: 1.1}}>{s.title}</div>
                  {s.text ? <div style={{position: 'relative', fontFamily: BRAND.font, fontWeight: 600, fontSize: ts('sub', height * 0.022), color: ink.body, opacity: 0.75, marginTop: height * 0.012}}>{s.text}</div> : null}
                </div>
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
