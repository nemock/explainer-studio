import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import {useInk, PAPER_SHADOW} from '../ink';
import {PaperSheet} from './PaperNote';
import {PaperStage, isStageName, stageZonePx, fitStageText} from './PaperStage';
import {colorizeText} from './colorize';

const colorize = (text: string, accent: string[] = [], red: string[] = [],
                 accentColor?: string, dangerColor?: string) =>
  colorizeText(text, accent, red, accentColor, dangerColor);

const SubKicker: React.FC<{text?: string; height: number}> = ({text, height}) => {
  const ink = useInk();
  return text ? (
    <div style={{fontFamily: BRAND.font, color: ink.body, opacity: 0.75, fontWeight: 700, fontSize: height * 0.03, marginTop: height * 0.02, textAlign: 'center'}}>
      {text}
    </div>
  ) : null;
};

const Kicker: React.FC<{text?: string; o: number; height: number}> = ({text, o, height}) => {
  const ink = useInk();
  return text ? (
    // 0.024 -> 0.030 (2026-08-11, operator): at 1080 the kicker was 26px, which is ~5pt on a
    // phone — legible on a desktop preview, a squint in the feed where most of this is watched.
    // Letter-spacing eased 5 -> 4 because tracking that wide at the larger size eats the line.
    <div style={{fontFamily: BRAND.font, color: ink.accent, fontWeight: 800, fontSize: height * 0.030, letterSpacing: 4, textTransform: 'uppercase', textAlign: 'center', opacity: o, marginBottom: height * 0.020}}>
      {text}
    </div>
  ) : null;
};

// Word-by-word reveal that preserves accent coloring + pops the accent words. Keeps text
// alive instead of one block-fade. (motion-playbook: text cards are the floor, give them life.)
const normWord = (s: string) => s.toLowerCase().replace(/[^a-z0-9']/g, '');
const RevealWords: React.FC<{text: string; accent?: string[]; accentRed?: string[]; startDelay?: number}> =
({text, accent, accentRed, startDelay = 0}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const ink = useInk();
  // match colorize.tsx exactly: split multi-word accent phrases into constituent words
  const A = new Set((accent || []).flatMap((s) => s.split(/\s+/)).map(normWord));
  const R = new Set((accentRed || []).flatMap((s) => s.split(/\s+/)).map(normWord));
  const parts = (text || '').split(/(\s+)/);
  let wi = 0;
  return (
    <>
      {parts.map((w, i) => {
        if (/^\s*$/.test(w)) return <span key={i}>{w}</span>;
        const clean = normWord(w);
        const isA = !!clean && A.has(clean), isR = !!clean && R.has(clean);
        const delay = startDelay + wi * 2.2; wi++;
        const e = spring({frame: frame - delay, fps, config: {damping: 15, stiffness: 130}});
        const pop = (isA || isR) ? interpolate(e, [0, 1], [1.22, 1], {extrapolateRight: 'clamp'}) : 1;
        return (
          <span key={i} style={{display: 'inline-block', color: isA ? ink.accent : isR ? (ink.danger ?? BRAND.red) : undefined,
            opacity: e, transform: `translateY(${interpolate(e, [0, 1], [20, 0])}px) scale(${pop})`,
            transformOrigin: 'center bottom'}}>{w}</span>
        );
      })}
    </>
  );
};

// statement -> a headline that reveals word-by-word, then keeps a slow continuous drift so it
// never sits frozen. fields: {kicker, headline, accent, accentRed, subkicker}
export const KineticHeadline: React.FC<{fields: any; durationInFrames?: number}> = ({fields, durationInFrames = 300}) => {
  const frame = useCurrentFrame();
  const {fps, height, width} = useVideoConfig();
  const s = spring({frame, fps, config: {damping: 18, stiffness: 90}});
  const ink = useInk();

  // OPT-IN stage scene (deck field `stage`). Deliberately not automatic: statement is the
  // most-used slide type, and putting every one of them in the same room would be its own
  // kind of monotony. The deck author picks the handful that earn a scene.
  if (isStageName(fields.stage)) {
    const zone = stageZonePx(fields.stage, width, height);
    const size = fitStageText(fields.headline || '', zone.w, zone.h);
    return (
      <PaperStage stage={fields.stage} durationInFrames={durationInFrames}>
        <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: size, lineHeight: 1.12,
                     color: ink.body, textAlign: 'center', width: '100%'}}>
          <RevealWords text={fields.headline} accent={fields.accent} accentRed={fields.accentRed} startDelay={6} />
        </div>
      </PaperStage>
    );
  }
  // Headline type FILLS the frame instead of defaulting to one thin line (operator, 2026-08-11:
  // "break that headline into two lines and make the font larger... we're trying to minimize
  // font size to preserve space that doesn't need to be preserved"). The old fixed height*0.07
  // set one 76px line across the middle of an otherwise empty 1080 frame — fine on a desktop
  // preview, small on the phone where most of this is watched.
  //
  // fitStageText grows the type until the string genuinely needs the box, so a short headline
  // gets big and a long one wraps to two or three lines rather than shrinking to a strip.
  // FLOORED at the previous 0.07 so no headline that reads well today can come out smaller —
  // this change can only ever increase type size.
  const HEADLINE_BOX = {w: width * 0.84, h: height * 0.42};
  const headlineSize = Math.max(height * 0.07,
                                fitStageText(fields.headline || '', HEADLINE_BOX.w, HEADLINE_BOX.h));

  // slow continuous life: a gentle push-in + upward drift across the whole scene (clears the
  // freezedetect dead-air the old one-shot fade left; premium, not jittery).
  const live = interpolate(frame, [0, durationInFrames], [1, 1.035]);
  const drift = interpolate(frame, [0, durationInFrames], [0, -height * 0.014]);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 8%', color: ink.body}}>
      <div style={{transform: `scale(${live}) translateY(${drift}px)`, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
        <Kicker text={fields.kicker} o={s} height={height} />
        {/* On the paper worlds the headline sits on a real poster instead of floating as bare
            type on the ground (operator-caught on #50). Statement is the most-used slide type
            in the catalogue, so this is where "type on paper" is most visible — and a poster
            is a RECTANGLE, so it is a tinted PaperSheet rather than a generated asset. The
            navy worlds keep bare type, which is correct there: there is no paper to sit on. */}
        <div style={{position: 'relative', maxWidth: '100%',
                     padding: ink.typeOnPaper ? `${height * 0.036}px ${height * 0.055}px` : undefined,
                     filter: ink.typeOnPaper ? `drop-shadow(0 ${height * 0.013}px ${height * 0.03}px rgba(120,92,40,.24))` : undefined}}>
          {ink.typeOnPaper ? <PaperSheet id={`stmt:${fields.headline ?? ''}`} family="card" radius={22} tint="#fffdf6" /> : null}
          <div style={{position: 'relative', fontFamily: BRAND.font, fontWeight: 900, fontSize: headlineSize, maxWidth: HEADLINE_BOX.w, lineHeight: 1.07, textAlign: 'center', textShadow: ink.paper ? PAPER_SHADOW : '0 10px 50px rgba(0,0,0,.6)'}}>
            <RevealWords text={fields.headline} accent={fields.accent} accentRed={fields.accentRed} startDelay={4} />
          </div>
        </div>
        <SubKicker text={fields.subkicker} height={height} />
      </div>
    </AbsoluteFill>
  );
};

// define -> a term + its definition. fields: {kicker, term, definition, accent, accentRed}
export const DefineTerm: React.FC<{fields: any; durationInFrames?: number}> = ({fields, durationInFrames = 300}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const t = spring({frame, fps, config: {damping: 18, stiffness: 90}});
  const d = spring({frame: frame - 10, fps, config: {damping: 18}});
  const ink = useInk();
  const termSize = (fields.term || '').length > 16 ? height * 0.06 : height * 0.075;
  // slow continuous life so the definition doesn't sit frozen after it reveals (paper freezedetect)
  const live = interpolate(frame, [0, durationInFrames], [1, 1.03]);
  const drift = interpolate(frame, [0, durationInFrames], [0, -height * 0.012]);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 9%', transform: `scale(${live}) translateY(${drift}px)`}}>
      <Kicker text={fields.kicker} o={t} height={height} />
      <div style={{fontFamily: BRAND.font, color: ink.accent, fontWeight: 900, fontSize: termSize, lineHeight: 1.1, textAlign: 'center', opacity: t, transform: `translateY(${interpolate(t, [0, 1], [24, 0])}px)`, textShadow: ink.paper ? PAPER_SHADOW : '0 10px 50px rgba(0,0,0,.6)'}}>
        {colorize(fields.term, fields.accent, fields.accentRed, ink.accent, (ink.danger ?? BRAND.red))}
      </div>
      <div style={{fontFamily: BRAND.font, color: ink.body, fontWeight: 700, fontSize: height * 0.038, lineHeight: 1.3, textAlign: 'center', maxWidth: '85%', marginTop: height * 0.028, opacity: d, transform: `translateY(${interpolate(d, [0, 1], [18, 0])}px)`}}>
        {fields.definition}
      </div>
    </AbsoluteFill>
  );
};

// quote -> big quote + attribution reveal. fields: {quote, attribution}
export const Quote: React.FC<{fields: any; durationInFrames?: number}> = ({fields, durationInFrames = 300}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const q = spring({frame, fps, config: {damping: 18}});
  const at = spring({frame: frame - 18, fps, config: {damping: 16}});
  const ink = useInk();
  // slow continuous life so the quote doesn't sit frozen after it springs in (paper freezedetect)
  const live = interpolate(frame, [0, durationInFrames], [1, 1.03]);
  const drift = interpolate(frame, [0, durationInFrames], [0, -height * 0.012]);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 9%', transform: `scale(${live}) translateY(${drift}px)`}}>
      <div style={{fontFamily: BRAND.font, color: ink.body, fontWeight: 800, fontSize: height * 0.058, lineHeight: 1.25, textAlign: 'center', opacity: q, transform: `translateY(${interpolate(q, [0, 1], [26, 0])}px)`, textShadow: ink.paper ? PAPER_SHADOW : '0 10px 40px rgba(0,0,0,.6)'}}>
        {fields.quote}
      </div>
      {fields.attribution ? (
        <div style={{fontFamily: BRAND.font, color: ink.accent, fontWeight: 800, fontSize: height * 0.028, marginTop: height * 0.03, opacity: at}}>
          — {fields.attribution}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// punch -> one giant word, max energy (the seam). fields: {word, kicker, kind:'good'|'bad'}
// OR the headline variant: {headline, accent, accentRed} — per-word accent coloring takes
// precedence over the whole-word `kind` color when accent/accentRed are actually set.
/**
 * A slow living drift for typography-only cards (operator-approved 2026-08-12).
 *
 * These cards finish their entrance and then hold perfectly still while the narration
 * keeps going, which is what QA's freezedetect reports as "visual dead air": on module 1
 * the punch and reframe cards alone accounted for 184 of 373 flagged seconds, while figure
 * slides — which drift under Ken Burns — scored ZERO. PaperBackground already carries an
 * anti-freeze breath, but at ~0.0002 alpha per frame it is far under the -60dB threshold,
 * and turning it up is not an option: the operator rejected a livelier background on
 * 2026-07-16 as "a distracting gyration". So the motion goes on the card, not the ground.
 *
 * It is applied to the OUTER AbsoluteFill, so it composes with each card's own entrance
 * transform rather than fighting it, and moves the whole composition as one piece — no
 * reflow, no re-wrap, nothing shifting relative to anything else.
 *
 * Sized so it CANNOT clip. Worst-case text width is 81% of frame on PunchWord (6% padding,
 * then maxWidth 92% of that) and 84% on Reframe; at the 1.4% peak scale those become 82.1%
 * and 85.2%, leaving ~7.4% clear on each side. Vertically these cards are centred with
 * hundreds of spare pixels, so an 11px drift is nowhere near an edge. Periods are primes-ish
 * and different per axis so the two never resolve into an obvious loop.
 */
const useCardDrift = (height: number, durationInFrames: number) => {
  const frame = useCurrentFrame();
  // Deliberately the SAME ramp KineticHeadline uses, not a new invention. That component
  // added this for exactly this reason, and module 1's QA numbers show it works: `statement`
  // logged 9 flagged spans totalling 6s, against punch's 49 spans / 105s over a comparable
  // slide count. Matching the proven constants also means these three card types age
  // together instead of drifting at three different rates.
  const live = interpolate(frame, [0, durationInFrames], [1, 1.035]);
  const dy = interpolate(frame, [0, durationInFrames], [0, -height * 0.014]);
  return `scale(${live.toFixed(5)}) translateY(${dy.toFixed(3)}px)`;
};

export const PunchWord: React.FC<{fields: any; durationInFrames?: number}> = ({fields, durationInFrames = 300}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const p = spring({frame, fps, config: {damping: 9, stiffness: 140}});
  const ink = useInk();
  const color = fields.kind === 'good' ? ink.accent : fields.kind === 'bad' ? (ink.danger ?? BRAND.red) : ink.body;
  const text = fields.word || fields.headline;
  const hasAccent = (fields.accent && fields.accent.length) || (fields.accentRed && fields.accentRed.length);
  const drift = useCardDrift(height, durationInFrames);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 6%', transform: drift}}>
      <Kicker text={fields.kicker} o={interpolate(p, [0, 1], [0, 1])} height={height} />
      <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.2, lineHeight: 1.02, color, textTransform: 'uppercase', transform: `scale(${p})`, textShadow: ink.paper ? PAPER_SHADOW : '0 16px 70px rgba(0,0,0,.6)', textAlign: 'center', maxWidth: '92%', whiteSpace: 'pre-line', textWrap: 'balance' as any}}>
        {hasAccent ? colorize(text, fields.accent, fields.accentRed, ink.accent, (ink.danger ?? BRAND.red)) : text}
      </div>
    </AbsoluteFill>
  );
};

// reframe -> "before" struck through, dissolving into "after". fields: {before, after}
export const Reframe: React.FC<{fields: any; durationInFrames?: number}> = ({fields, durationInFrames = 300}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const a = spring({frame, fps, config: {damping: 18}});
  const flip = spring({frame: frame - 26, fps, config: {damping: 16}});
  const ink = useInk();
  const drift = useCardDrift(height, durationInFrames);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 8%', flexDirection: 'column', transform: drift}}>
      <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.06, color: ink.body, opacity: interpolate(flip, [0, 1], [1, 0.35]), textDecoration: 'line-through', textDecorationColor: (ink.danger ?? BRAND.red), textAlign: 'center'}}>
        {fields.before}
      </div>
      <div style={{fontFamily: BRAND.font, color: ink.accent, fontWeight: 900, fontSize: height * 0.04, margin: `${height * 0.02}px 0`, opacity: a}}>↓</div>
      <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.078, color: ink.body, textAlign: 'center', opacity: flip, transform: `scale(${interpolate(flip, [0, 1], [0.85, 1])})`, textShadow: ink.paper ? PAPER_SHADOW : '0 10px 50px rgba(0,0,0,.6)'}}>
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
  const ink = useInk();
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 10%'}}>
      <div style={{maxWidth: '100%'}}>
        <Kicker text={fields.kicker} o={spring({frame, fps, config: {damping: 18}})} height={height} />
        {fields.title ? (
          <div style={{fontFamily: BRAND.font, color: ink.body, fontWeight: 800, fontSize: height * 0.036, lineHeight: 1.2, opacity: titleO, marginBottom: height * 0.024, transform: `translateY(${interpolate(titleO, [0, 1], [16, 0])}px)`}}>
            {colorize(fields.title, fields.accent, fields.accentRed, ink.accent, (ink.danger ?? BRAND.red))}
          </div>
        ) : null}
        {items.map((it, i) => {
          // appear AS the item is spoken (itemTimes from alignment), else even stagger
          const appear = itemTimes && itemTimes[i] != null ? (itemTimes[i] as number) : i * per;
          const e = spring({frame: frame - appear, fps, config: {damping: 18}});
          return (
            <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: height * 0.02, opacity: e, transform: `translateX(${interpolate(e, [0, 1], [-30, 0])}px)`, marginBottom: height * 0.022}}>
              <span style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.05, color: ink.accent}}>{i + 1}</span>
              <span style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.044, color: ink.body, lineHeight: 1.1}}>{it}</span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// compare -> two columns animating in. fields: {left:{title,value}, right:{title,value}}
export const SideBySide: React.FC<{fields: any; durationInFrames?: number}> = ({fields, durationInFrames = 300}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const l = spring({frame, fps, config: {damping: 18}});
  const r = spring({frame: frame - 10, fps, config: {damping: 18}});
  const ink = useInk();
  // continuous life so the two cards don't sit frozen after they slide in (paper freezedetect)
  const live = interpolate(frame, [0, durationInFrames], [1, 1.028]);
  const drift = interpolate(frame, [0, durationInFrames], [0, -height * 0.01]);
  // The side colours used to be POSITIONAL (left always good, right always bad), which quietly
  // ignored the deck's own `kind`. #50 has a compare with `bad` on the LEFT, one with `bad` on
  // BOTH sides, and one with neither — all three rendered wrong. Honour the authored kind when
  // either side declares one; fall back to the old positional default when neither does, so
  // every deck written before this keeps its exact previous colouring.
  const declared = !!(fields.left?.kind || fields.right?.kind);
  // On the paper worlds each side is a real card from the substrate library — two posters
  // laid side by side — instead of the CSS tray, which read as an engine artifact next to
  // the papercraft figures and post-its (operator-caught on #50). A compare tray is a plain
  // RECTANGLE, so per the substrate plan it needs no new generation: PaperSheet plus a tint.
  // The bad side takes a blush stock, echoing how Schematic gives a bad node a coral note,
  // so the contrast survives losing the coloured border. Navy is untouched.
  const col = (d: any, o: number, dir: number, positionalBad: boolean) => {
    const bad = declared ? d?.kind === 'bad' : positionalBad;
    const paper = ink.typeOnPaper;
    return (
      <div style={{flex: 1, position: 'relative', padding: height * 0.03, borderRadius: 20,
                   background: paper ? undefined : ink.cardBg,
                   border: paper ? undefined : `2px solid ${bad ? 'rgba(255,77,77,.5)' : `${ink.accent}66`}`,
                   filter: paper ? `drop-shadow(0 ${height * 0.012}px ${height * 0.028}px rgba(120,92,40,.22))` : undefined,
                   opacity: o,
                   // a hair of opposing tilt so the two read as laid-down paper, not as a grid
                   transform: `translateX(${interpolate(o, [0, 1], [dir * 40, 0])}px)${paper ? ` rotate(${dir * 0.5}deg)` : ''}`}}>
        {paper ? <PaperSheet id={`cmp:${d?.title ?? ''}:${d?.value ?? ''}`} family="card"
                             radius={20} tint={bad ? '#f6e0dc' : '#fffcf5'} /> : null}
        <div style={{position: 'relative', fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.024, letterSpacing: 3, textTransform: 'uppercase', color: bad ? (ink.danger ?? BRAND.red) : ink.accent, marginBottom: height * 0.018}}>{d?.title}</div>
        <div style={{position: 'relative', fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.044, color: ink.body, lineHeight: 1.12}}>{d?.value}</div>
      </div>
    );
  };
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 7%', transform: `scale(${live}) translateY(${drift}px)`}}>
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
  const ink = useInk();
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
                <span style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.038, color: ink.body, lineHeight: 1.12}}>{e.label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
