import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

// A paper KEEP-CARD (2026-07-14). The generated paper card (icon in the upper two-thirds,
// blank lower third) slides up and settles like a card placed on a table; a crisp label +
// sub-line are stamped into the blank third. The recurring "franchise" device for naming a
// framework beat. fields: {image, label, sub?}. Cream paper world (matches the sting).
export const KeepCard: React.FC<{fields: any; durationInFrames?: number}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, height, width} = useVideoConfig();
  const portrait = height > width;
  const CREAM = '#f1e8d4';
  const INK = '#2c1e4e';
  const PURPLE = '#6a4bb0';

  const inn = spring({frame: frame - 2, fps, config: {damping: 15, stiffness: 110}});
  const y = interpolate(inn, [0, 1], [height * 0.5, 0]);
  const rot = interpolate(inn, [0, 1], [5, 0]);
  // The card settles from its slide-in and then holds STILL. (An earlier continuous
  // breathe+sway was removed 2026-07-16: any always-on paper motion reads as a nauseating
  // bob. The QA dead-air warning on the held card is accepted; paper is calm by design.)
  // Portrait (Shorts): the content box is only the upper two-thirds (the bottom third is the
  // caption band), so a full-height card spills its sub-line into the captions. Shrink + center
  // the card so it sits cleanly in the upper two-thirds (operator direction 2026-07-16).
  const cardH = height * (portrait ? 0.56 : 0.78);

  const label = fields.label || '';
  const sub = fields.sub || '';
  const labelIn = interpolate(frame, [9, 20], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const subIn = interpolate(frame, [15, 27], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{background: CREAM, alignItems: 'center', justifyContent: portrait ? 'center' : 'flex-start', paddingTop: portrait ? 0 : height * 0.035, overflow: 'hidden'}}>
      <div style={{position: 'relative', height: cardH, transform: `translateY(${y}px) rotate(${rot}deg)`, opacity: inn}}>
        {fields.image ? (
          <Img src={staticFile(fields.image)} style={{height: '100%', display: 'block', filter: 'drop-shadow(0 20px 34px rgba(0,0,0,.18))'}} />
        ) : null}
        <div style={{position: 'absolute', left: 0, right: 0, top: '64%', textAlign: 'center'}}>
          <div style={{
            fontFamily: BRAND.font, fontWeight: 900, fontSize: cardH * 0.084, letterSpacing: 1,
            color: INK, lineHeight: 1.05, opacity: labelIn,
            transform: `translateY(${interpolate(labelIn, [0, 1], [10, 0])}px)`,
          }}>
            {label}
          </div>
          {sub && !portrait ? (
            <div style={{
              fontFamily: BRAND.font, fontWeight: 600, fontSize: cardH * 0.036, color: PURPLE,
              marginTop: cardH * 0.022, padding: '0 9%', lineHeight: 1.2, opacity: subIn,
            }}>
              {sub}
            </div>
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};
