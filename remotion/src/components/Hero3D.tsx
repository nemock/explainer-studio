import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {BRAND} from '../brand';

// motion-playbook §2G — 3D hero (cold opens / seam / payoff). A slowly rotating brand
// wireframe solid behind a 2D kinetic headline. Rotation is frame-driven (deterministic).
// fields: {kicker?, headline, accent?, shape?: 'ico'|'torus'|'octa'}
const Solid: React.FC<{shape: string}> = ({shape}) => {
  const frame = useCurrentFrame();
  const rx = frame * 0.013;
  const ry = frame * 0.02;
  return (
    <>
      <ambientLight intensity={1.4} />
      <pointLight position={[8, 8, 8]} intensity={120} />
      <pointLight position={[-8, -4, 4]} intensity={60} color={BRAND.green} />
      <mesh rotation={[rx, ry, 0]} scale={2.1}>
        {shape === 'torus' ? (
          <torusKnotGeometry args={[1, 0.32, 160, 24]} />
        ) : shape === 'octa' ? (
          <octahedronGeometry args={[1.3, 0]} />
        ) : (
          <icosahedronGeometry args={[1.4, 1]} />
        )}
        <meshStandardMaterial color={BRAND.green} wireframe metalness={0.3} roughness={0.4} />
      </mesh>
    </>
  );
};

export const Hero3D: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const headIn = spring({frame: frame - 10, fps, config: {damping: 16, stiffness: 110}});
  const fade = interpolate(frame, [0, 14], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{opacity: 0.9 * fade}}>
        <ThreeCanvas width={width} height={height} camera={{position: [0, 0, 6], fov: 55}}>
          <Solid shape={fields.shape || 'ico'} />
        </ThreeCanvas>
      </AbsoluteFill>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 8%'}}>
        {fields.kicker ? (
          <div style={{fontFamily: BRAND.font, color: BRAND.green, fontWeight: 800, fontSize: height * 0.024, letterSpacing: 6, textTransform: 'uppercase', opacity: fade, marginBottom: height * 0.014}}>
            {fields.kicker}
          </div>
        ) : null}
        <div
          style={{
            fontFamily: BRAND.font,
            color: BRAND.white,
            fontWeight: 900,
            fontSize: height * 0.085,
            lineHeight: 1.04,
            textAlign: 'center',
            transform: `scale(${interpolate(headIn, [0, 1], [0.8, 1])})`,
            opacity: headIn,
            textShadow: '0 12px 60px rgba(0,0,0,.8)',
          }}
        >
          {fields.headline}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
