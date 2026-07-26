import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import {useWorld, PaperTable, PaperCard, usePlace, usePopup, flick} from './PaperWorld';

// Papercraft Motion — text family (papercraft-motion-spec.md §7). Text is always
// printed ON paper that physically exists in the set: statements/quotes/punches/
// definitions are cream cards and tags placed or popped onto the dark table.
// Beats come from the engine cue map ("cues" -> fields.cueFrames).

// W now comes from the world context (per component, below) so each paper
// channel keeps its own ground; see PaperWorld.WorldProvider (2026-07-26).

const colorize = (text: string, accent: string[] = [], accentColor: string) => {
  if (!accent || !accent.length) return text;
  let parts: React.ReactNode[] = [text];
  accent.forEach((a) => {
    parts = parts.flatMap((p) => {
      if (typeof p !== 'string' || !a) return [p];
      const out: React.ReactNode[] = [];
      const segs = p.split(a);
      segs.forEach((s, i) => {
        if (s) out.push(s);
        if (i < segs.length - 1) out.push(<span key={a + i} style={{color: accentColor}}>{a}</span>);
      });
      return out;
    });
  });
  return parts;
};

const Kicker: React.FC<{text?: string; height: number}> = ({text, height}) => {
  const W = useWorld();
  return text ? (
    <div style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.022, letterSpacing: 4,
                 textTransform: 'uppercase', color: W.accent, textAlign: 'center', marginBottom: height * 0.014}}>
      {text}
    </div>
  ) : null;
};

// statement / quote / highlight -> a cream card places center; optional `hit`
// cue flicks the card + snaps the light (used when the line lands mid-scene).
export const PaperStatement: React.FC<{fields: any}> = ({fields}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const cf = fields.cueFrames || {};
  const at = cf.in ?? 3;
  const hit = cf.hit ?? null;
  const p = usePlace(at);
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <PaperTable seed={fields.headline || 'statement'} tightenAt={hit} />
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{position: 'relative', maxWidth: width * 0.66, transform: `scale(${hit != null ? flick(frame, hit) : 1})`}}>
          <div style={{position: 'absolute', left: '50%', bottom: -height * 0.016, width: '88%', height: height * 0.034,
                       transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%', filter: 'blur(9px)', opacity: p.shadowOpacity}} />
          <PaperCard style={{...p.object, padding: `${height * 0.034}px ${width * 0.032}px`, borderRadius: 20}}>
            <Kicker text={fields.kicker} height={height} />
            <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.06, lineHeight: 1.1,
                         color: W.ink, textAlign: 'center'}}>{colorize(fields.headline || '', fields.accent, W.accent)}</div>
            {fields.attrib ? (
              <div style={{fontFamily: BRAND.font, fontWeight: 700, fontSize: height * 0.026, color: W.accent,
                           textAlign: 'center', marginTop: height * 0.018}}>— {fields.attrib}</div>
            ) : null}
            {fields.subkicker ? (
              <div style={{fontFamily: BRAND.font, fontWeight: 700, fontSize: height * 0.026, color: W.accent,
                           textAlign: 'center', marginTop: height * 0.018, opacity: 0.9}}>{fields.subkicker}</div>
            ) : null}
          </PaperCard>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// define -> the term on a big tag (places on its cue), the definition UNFOLDS
// beneath it (two-step clip reveal with a fold shade).
export const PaperDefine: React.FC<{fields: any}> = ({fields}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const cf = fields.cueFrames || {};
  const termAt = cf.term ?? 5;
  const defAt = termAt + 10;
  const p = usePlace(termAt);
  // unfold: clip opens top->bottom in two beats; a moving shade sells the fold
  const open = interpolate(frame, [defAt, defAt + 7, defAt + 9, defAt + 16], [0, 0.55, 0.62, 1],
                           {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const shade = interpolate(open, [0.3, 1], [0.35, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <PaperTable seed={fields.term || 'define'} tightenAt={termAt} />
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{position: 'relative'}}>
          <div style={{position: 'absolute', left: '50%', bottom: -height * 0.016, width: '86%', height: height * 0.032,
                       transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%', filter: 'blur(9px)', opacity: p.shadowOpacity}} />
          <PaperCard style={{...p.object, padding: `${height * 0.026}px ${width * 0.03}px`, borderRadius: 18, transform: `${(p.object.transform || '')} rotate(-0.8deg)`}}>
            <Kicker text={fields.kicker} height={height} />
            <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.078, lineHeight: 1.05,
                         color: W.ink, textAlign: 'center'}}>{fields.term}</div>
          </PaperCard>
          <div style={{clipPath: `inset(0 0 ${(100 - open * 100).toFixed(1)}% 0)`, marginTop: height * 0.02, position: 'relative'}}>
            <PaperCard style={{padding: `${height * 0.02}px ${width * 0.026}px`, borderRadius: 14, maxWidth: width * 0.5}}>
              <div style={{fontFamily: BRAND.font, fontWeight: 700, fontSize: height * 0.034, lineHeight: 1.3,
                           color: W.ink, textAlign: 'center'}}>{fields.definition}</div>
            </PaperCard>
            <div style={{position: 'absolute', inset: 0, background: `linear-gradient(180deg, rgba(42,17,66,${shade.toFixed(3)}) 0%, transparent 55%)`, borderRadius: 14, pointerEvents: 'none'}} />
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// punch -> ONE word stamped hard on a cream card: hard place on the hit cue,
// spotlight snap, flick; kind "bad" places the warning-triangle element beside
// it a beat later (the palette has no red — the warning prop carries the alarm).
export const PaperPunch: React.FC<{fields: any}> = ({fields}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const cf = fields.cueFrames || {};
  const hit = cf.hit ?? 5;
  const p = usePlace(hit);
  const warn = usePopup(hit + 7);
  const bad = fields.kind === 'bad';
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <PaperTable seed={fields.word || 'punch'} tightenAt={hit} mood={bad ? 'hard' : 'soft'} />
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{position: 'relative', transform: `scale(${flick(frame, hit)})`}}>
          <div style={{position: 'absolute', left: '50%', bottom: -height * 0.02, width: '92%', height: height * 0.04,
                       transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%', filter: 'blur(11px)', opacity: p.shadowOpacity}} />
          <PaperCard style={{...p.object, padding: `${height * 0.03}px ${width * 0.04}px`, borderRadius: 24}}>
            {fields.kicker ? <Kicker text={fields.kicker} height={height} /> : null}
            <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.16, lineHeight: 1.02,
                         color: W.ink, textTransform: 'uppercase', textAlign: 'center', whiteSpace: 'pre-line',
                         // embossed stamp: paper pressed by the letters
                         textShadow: `0 2px 0 rgba(255,255,255,.7), 0 -1px 1px rgba(42,17,66,.28)`}}>
              {fields.word}
            </div>
            <div style={{height: height * 0.012, width: '62%', margin: `${height * 0.014}px auto 0`,
                         background: bad ? W.sheet : W.accentSoft, borderRadius: 6,
                         transform: `scaleX(${interpolate(frame, [hit + 4, hit + 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})})`}} />
          </PaperCard>
          {bad ? (
            <div style={{position: 'absolute', right: -width * 0.055, top: -height * 0.055, width: width * 0.09, ...warn.object}}>
              <Img src={staticFile('papercraft/elements/el_warning.png')} style={{width: '100%', display: 'block',
                   filter: `drop-shadow(0 ${height * 0.012}px ${height * 0.022}px ${W.shadow})`, transform: 'rotate(8deg)'}} />
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
