import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

// motion-playbook §2A baseline — a talking beat where the kinetic captions are the hero.
// Shows an optional kicker/headline above the captions so the frame isn't empty.
// fields: {kicker?, headline?, accent[]?}
export const TalkingScene: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const a = spring({frame, fps, config: {damping: 18}});
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 8%'}}>
      {fields.kicker ? (
        <div
          style={{
            fontFamily: BRAND.font,
            color: BRAND.green,
            fontWeight: 800,
            fontSize: height * 0.024,
            letterSpacing: 5,
            textTransform: 'uppercase',
            textAlign: 'center',
            opacity: a,
            marginBottom: fields.headline ? height * 0.018 : 0,
          }}
        >
          {fields.kicker}
        </div>
      ) : null}
      {fields.headline ? (
        <div
          style={{
            fontFamily: BRAND.font,
            color: BRAND.white,
            fontWeight: 900,
            fontSize: height * 0.058,
            lineHeight: 1.08,
            textAlign: 'center',
            opacity: a,
            transform: `translateY(${interpolate(a, [0, 1], [24, 0])}px)`,
            textShadow: '0 10px 50px rgba(0,0,0,.6)',
          }}
        >
          {fields.headline}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
