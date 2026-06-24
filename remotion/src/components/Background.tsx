import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

// Brand navy, but ALIVE (motion-playbook §0 "dynamic is the norm"): a breathing zoom,
// a slowly drifting hotspot, and a faint second aurora glow + vignette. All frame-driven.
export const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  const t = frame / fps;
  const scale = interpolate(frame, [0, durationInFrames], [1, 1.07]);
  const hx = 50 + 8 * Math.sin(t * 0.18);
  const hy = 40 + 6 * Math.cos(t * 0.14);
  const ax = 30 + 14 * Math.sin(t * 0.1 + 1);
  const ay = 70 + 10 * Math.cos(t * 0.12);
  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          background: `radial-gradient(120% 90% at ${hx}% ${hy}%, ${BRAND.navyIn} 0%, ${BRAND.navyMid} 55%, ${BRAND.navyOut} 100%)`,
          transform: `scale(${scale})`,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(40% 40% at ${ax}% ${ay}%, rgba(61,220,132,.10) 0%, rgba(61,220,132,0) 70%)`,
          mixBlendMode: 'screen',
        }}
      />
      <AbsoluteFill style={{boxShadow: 'inset 0 0 380px rgba(0,0,0,.6)'}} />
    </AbsoluteFill>
  );
};
