import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

// motion-playbook §2A/F — the closing CTA. Floats the brand book cover in next to the
// call-to-action text (operator directive 2026-06-24: show the cover, don't just talk
// about it). fields: {kicker, headline, subkicker, accent, image(book cover basename)}
export const CTA: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const portrait = height > width;
  const intro = spring({frame, fps, config: {damping: 16, stiffness: 80}});
  const tIntro = spring({frame: frame - 12, fps, config: {damping: 18}});
  const bob = Math.sin((frame / fps) * 1.1) * (height * 0.01);
  const sway = Math.sin((frame / fps) * 0.7) * 2.2; // gentle degrees of life

  const book = fields.image ? (
    <Img
      src={staticFile(fields.image)}
      style={{
        width: portrait ? '74%' : '44%',
        maxHeight: portrait ? '46%' : '78%',
        objectFit: 'contain',
        opacity: intro,
        transform: `translateY(${interpolate(intro, [0, 1], [80, 0]) + bob}px) scale(${interpolate(intro, [0, 1], [0.82, 1])}) rotate(${sway}deg)`,
        filter: 'drop-shadow(0 36px 70px rgba(0,0,0,.6))',
      }}
    />
  ) : null;

  const text = (
    <div style={{textAlign: (portrait || !book) ? 'center' : 'left', maxWidth: portrait ? '90%' : (book ? '46%' : '72%'), opacity: tIntro,
                 transform: `translateY(${interpolate(tIntro, [0, 1], [24, 0])}px)`}}>
      {fields.kicker ? (
        <div style={{fontFamily: BRAND.font, color: BRAND.green, fontWeight: 800, fontSize: height * 0.024, letterSpacing: 4, textTransform: 'uppercase', marginBottom: height * 0.02}}>
          {fields.kicker}
        </div>
      ) : null}
      <div style={{fontFamily: BRAND.font, color: BRAND.white, fontWeight: 900, fontSize: height * 0.07, lineHeight: 1.05, textShadow: '0 10px 50px rgba(0,0,0,.6)'}}>
        {fields.headline}
      </div>
      {fields.subkicker ? (
        <div style={{fontFamily: BRAND.font, color: BRAND.white, opacity: 0.82, fontWeight: 700, fontSize: height * 0.03, marginTop: height * 0.028, lineHeight: 1.3}}>
          {fields.subkicker}
        </div>
      ) : null}
    </div>
  );

  return (
    <AbsoluteFill
      style={{
        alignItems: 'center',
        justifyContent: 'center',
        gap: portrait ? height * 0.04 : width * 0.04,
        flexDirection: portrait ? 'column' : 'row',
        padding: '0 7%',
      }}
    >
      {book}
      {text}
    </AbsoluteFill>
  );
};
