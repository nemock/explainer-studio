import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

// Brand navy radial with a slow "breathing" zoom so nothing is dead-static
// (motion-playbook §1). Lives under every scene.
export const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const scale = interpolate(frame, [0, durationInFrames], [1, 1.06]);
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(120% 90% at 50% 40%, ${BRAND.navyIn} 0%, ${BRAND.navyMid} 55%, ${BRAND.navyOut} 100%)`,
        transform: `scale(${scale})`,
      }}
    />
  );
};
