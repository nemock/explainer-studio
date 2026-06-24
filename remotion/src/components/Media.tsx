import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

// figure -> a framed document/artifact excerpt with Ken Burns + an optional marker-wipe
// highlight (motion-playbook §2D). fields: {image, kicker, caption, highlight?{top,left,height,widthTo,atFrac}}
export const Figure: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const intro = spring({frame, fps, config: {damping: 18, stiffness: 90}});
  const kb = interpolate(frame, [0, durationInFrames], [1, 1.06]);
  const scale = interpolate(intro, [0, 1], [0.92, 1]) * kb;
  const hl = fields.highlight;
  const at = (hl?.atFrac ?? 0.35) * durationInFrames;
  const hlW = hl ? interpolate(frame, [at, at + 0.45 * fps * 3], [0, hl.widthTo ?? 40], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 6%'}}>
      {fields.kicker ? (
        <div style={{fontFamily: BRAND.font, color: BRAND.green, fontWeight: 800, fontSize: height * 0.024, letterSpacing: 4, textTransform: 'uppercase', opacity: intro, marginBottom: height * 0.025}}>
          {fields.kicker}
        </div>
      ) : null}
      <div style={{position: 'relative', maxWidth: '82%', background: '#fff', borderRadius: 26, padding: height * 0.022, boxShadow: '0 40px 120px rgba(0,0,0,.55)', transform: `scale(${scale})`}}>
        <Img src={staticFile(fields.image)} style={{width: '100%', display: 'block', borderRadius: 8}} />
        {hl ? (
          <div style={{position: 'absolute', top: `${hl.top ?? 30}%`, left: `${hl.left ?? 6}%`, height: `${hl.height ?? 12}%`, width: `${hlW}%`, background: 'rgba(61,220,132,.42)', borderRadius: 8}} />
        ) : null}
      </div>
      {fields.caption ? (
        <div style={{fontFamily: BRAND.font, color: BRAND.white, opacity: 0.75 * intro, fontSize: height * 0.022, marginTop: height * 0.025}}>
          {fields.caption}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// footage -> full-bleed image/B-roll with Ken Burns + a headline overlay + scrim
// (motion-playbook §2E). fields: {image, headline, accent}
export const Footage: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {height} = useVideoConfig();
  const kb = interpolate(frame, [0, durationInFrames], [1.12, 1.22]);
  const pan = interpolate(frame, [0, durationInFrames], [-2, 2]);
  return (
    <AbsoluteFill>
      {fields.image ? (
        <AbsoluteFill style={{transform: `scale(${kb}) translateX(${pan}%)`}}>
          <Img src={staticFile(fields.image)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </AbsoluteFill>
      ) : null}
      <AbsoluteFill style={{background: 'linear-gradient(0deg, rgba(9,13,28,.85) 0%, rgba(9,13,28,.25) 45%, rgba(9,13,28,.55) 100%)'}} />
      {fields.headline ? (
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 8%'}}>
          <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.07, color: BRAND.white, textAlign: 'center', textShadow: '0 10px 50px rgba(0,0,0,.8)'}}>
            {fields.headline}
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
