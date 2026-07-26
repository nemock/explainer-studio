import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import {useInk} from '../ink';

// Paper cold-open hook (2026-07-14) — REPLACES the rotating 3D "buckyball" (Hero3D) as the
// default open. A full-bleed paper illustration (this video's visual theme) with a gentle
// Ken Burns drift; the headline sits on a warm paper "label" card so it reads over any
// illustration. No image -> a warm paper backdrop. fields: {image, kicker, headline, accent[]}
// Accent color comes from the theme ink (2026-07-26) so each paper world keeps its own
// accent: green for nemock-deep-dive/cut-bond, BRG indigo for brg-deep-dive.
const colorize = (text: string, accent: string[] = [], accentColor: string = BRAND.green) => {
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

export const PaperHook: React.FC<{fields: any}> = ({fields}) => {
  const ink = useInk();
  const frame = useCurrentFrame();
  const {fps, height, width} = useVideoConfig();
  const CREAM = '#f4ecd6';
  const INK = '#2c1e4e';

  const kb = interpolate(frame, [0, 150], [1.05, 1.12], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const headIn = spring({frame: frame - 6, fps, config: {damping: 16, stiffness: 120}});
  const kickIn = interpolate(frame, [0, 14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  // With a full-bleed illustration the label sits near the top (over the art). With NO image
  // (headline-only hooks, e.g. Shorts), pin-to-top leaves a dead middle — center the label in
  // the content box instead so it settles around the top-third line (operator direction 2026-07-16).
  const hasImg = !!fields.image;
  const labelPos: React.CSSProperties = hasImg
    ? {position: 'absolute', top: '7%', left: '50%', transform: `translateX(-50%) translateY(${interpolate(headIn, [0, 1], [-height * 0.03, 0])}px) scale(${interpolate(headIn, [0, 1], [0.92, 1])})`}
    : {position: 'relative', transform: `translateY(${interpolate(headIn, [0, 1], [-height * 0.03, 0])}px) scale(${interpolate(headIn, [0, 1], [0.92, 1])})`};

  return (
    <AbsoluteFill style={{background: CREAM, overflow: 'hidden', ...(hasImg ? {} : {alignItems: 'center', justifyContent: 'center'})}}>
      {fields.image ? (
        <Img src={staticFile(fields.image)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${kb})`}} />
      ) : (
        <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 40%, #fbf4e0 0%, #efe5cb 100%)'}} />
      )}

      <div style={{...labelPos, opacity: headIn, width: '84%'}}>
        {fields.kicker ? (
          <div style={{textAlign: 'center', color: ink.accent, fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.026, letterSpacing: 5, textTransform: 'uppercase', opacity: kickIn, marginBottom: height * 0.018}}>
            {fields.kicker}
          </div>
        ) : null}
        <div style={{background: '#fbf6e8', borderRadius: 24, padding: `${height * 0.032}px ${width * 0.045}px`, boxShadow: '0 24px 60px rgba(0,0,0,.30)', border: '3px solid rgba(44,30,78,.10)', margin: '0 auto', maxWidth: '100%'}}>
          <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.072, lineHeight: 1.06, color: INK, textAlign: 'center'}}>
            {colorize(fields.headline || '', fields.accent, ink.accent)}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
