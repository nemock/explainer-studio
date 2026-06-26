import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

// Studio standard background — LOCKED 2026-06-26 (operator spec). Four independent,
// frame-driven animation passes over the navy palette (#15314a / #0d1428 / #090d1c):
//   Layer 1 — breathing radial gradient: scale on an 8s sine (≈1.01→1.09) with an
//             inner glow pulsing 0→~13% opacity in sync with the breath.
//   Layer 2 — elliptical orbit of the light center: both axes at 2π/12 rad/s (12s
//             period) with a 90° phase offset (cos x / sin y) for a clean ellipse,
//             radius ±10% H / ±7% V; the inner glow tracks the same orbit. A green
//             aurora (~13%, screen) drifts its own independent Lissajous path.
//   Layer 3 — drifting fractal-noise grain: a STATIC feTurbulence texture (the
//             pattern is identical every frame) moved by slow position (~90s) and
//             scale (±8%, ~48s) transforms; 6% opacity, screen blend.
//   Layer 4 — fixed vignette (inset box-shadow) to hold weight in the center.
// All motion is derived from useCurrentFrame()/useVideoConfig() — NO CSS animations,
// timers, or unseeded random — so Remotion's out-of-order renderer is deterministic.
// All values are percentage- or frame-derived, so it works for 16:9 and 9:16 alike.
export const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  // Unique filter id per instance (deterministic; spec note — avoid collisions when
  // more than one Background mounts on the same page). useId is SSR/Remotion-safe;
  // strip colons so it is a clean SVG fragment id.
  const noiseId = `bg-fractal-noise-${React.useId().replace(/:/g, '')}`;

  // Layer 1 — breath (8s period)
  const breath = Math.sin((t / 8) * Math.PI * 2);
  const scale = 1.05 + 0.04 * breath; // 1.01 → 1.09
  const glowOpacity = 0.13 * ((1 + breath) / 2); // 0 → 0.13, in sync with the breath

  // Layer 2 — elliptical orbit of the main hotspot (12s period, ±10% H / ±7% V).
  // Same angular frequency on both axes + 90° phase (cos vs sin) ⇒ a true ellipse.
  const orbitOmega = (Math.PI * 2) / 12;
  const hx = 50 + 10 * Math.cos(t * orbitOmega);
  const hy = 40 + 7 * Math.sin(t * orbitOmega);

  // Secondary green aurora on its own independent Lissajous path (depth).
  const ax = 32 + 18 * Math.sin(t * 0.19 + 1.2);
  const ay = 68 + 12 * Math.cos(t * 0.22);

  // Layer 3 — drifting fractal-noise grain (static texture; motion is transform-only).
  const noiseOffX = Math.sin(t * 0.07) * 180; // ~90s period, ±180px
  const noiseOffY = Math.cos(t * 0.055) * 140; // slow, ±140px
  const noiseScale = 1 + 0.08 * Math.sin(t * 0.13); // ±8%, ~48s period

  return (
    <AbsoluteFill>
      {/* Layer 1/2 — primary gradient: orbiting hotspot + breathing scale */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(120% 90% at ${hx}% ${hy}%, ${BRAND.navyIn} 0%, ${BRAND.navyMid} 55%, ${BRAND.navyOut} 100%)`,
          transform: `scale(${scale})`,
        }}
      />
      {/* Layer 1 — pulsing inner glow, tracks the same orbit */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(52% 52% at ${hx}% ${hy}%, rgba(21,49,74,${glowOpacity.toFixed(3)}) 0%, rgba(21,49,74,0) 70%)`,
          mixBlendMode: 'screen',
        }}
      />
      {/* Layer 2 — secondary aurora */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(40% 40% at ${ax}% ${ay}%, rgba(61,220,132,.13) 0%, rgba(61,220,132,0) 70%)`,
          mixBlendMode: 'screen',
        }}
      />
      {/* Layer 3 — drifting fractal-noise grain */}
      <AbsoluteFill style={{overflow: 'hidden', mixBlendMode: 'screen', opacity: 0.06}}>
        <svg
          style={{
            position: 'absolute',
            width: '200%',
            height: '200%',
            left: `calc(-50% + ${noiseOffX}px)`,
            top: `calc(-50% + ${noiseOffY}px)`,
            transform: `scale(${noiseScale})`,
            transformOrigin: 'center center',
          }}
        >
          <defs>
            <filter id={noiseId}>
              <feTurbulence
                type="fractalNoise"
                baseFrequency="0.45"
                numOctaves={4}
                stitchTiles="stitch"
              />
            </filter>
          </defs>
          <rect width="100%" height="100%" filter={`url(#${noiseId})`} />
        </svg>
      </AbsoluteFill>
      {/* Layer 4 — vignette */}
      <AbsoluteFill style={{boxShadow: 'inset 0 0 380px rgba(0,0,0,.6)'}} />
    </AbsoluteFill>
  );
};
