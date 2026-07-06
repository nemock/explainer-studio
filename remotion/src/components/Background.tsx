import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

// Studio standard background — ALIVE PASS 2026-07-06 (operator directive: the 2026-06-26
// spec read as "hypnotic… you have to stare at it to even notice it's moving"; make it
// feel alive, accepting the larger encode). Six independent, frame-driven passes over
// the navy palette (#15314a / #0d1428 / #090d1c):
//   Layer 1 — breathing radial gradient: scale on a 5s sine (≈1.00→1.10) with an inner
//             glow pulsing 0→~15% opacity in sync with the breath.
//   Layer 2 — elliptical orbit of the light center: both axes at 2π/7 rad/s (7s period)
//             with a 90° phase offset (cos x / sin y), radius ±12% H / ±8% V. A green
//             aurora (~16%, screen) roams its own faster Lissajous path for depth.
//   Layer 3 — bokeh field (NEW): 14 seeded depth-blurred discs (cool white-blue, a few
//             brand green) rising and swaying on independent paths with slow twinkle;
//             wraps vertically so the field never empties. All constants derive from a
//             pure index hash — no Math.random.
//   Layer 4 — light sweep (NEW): a soft diagonal band crossing the frame every ~11s,
//             screen blend, ≤6% — a periodic, plainly visible beat of motion.
//   Layer 5 — drifting fractal-noise grain: STATIC feTurbulence texture moved by
//             position (~40s) and scale (±8%, ~27s) transforms; 6% opacity, screen.
//   Layer 6 — fixed vignette (inset box-shadow) to hold weight in the center.
// All motion is derived from useCurrentFrame()/useVideoConfig() — NO CSS animations,
// timers, or unseeded random — so Remotion's out-of-order renderer is deterministic.
// Percentage- and frame-derived throughout: works for 16:9 and 9:16 alike. Legibility
// guardrail: every added layer is a low-opacity screen blend; body text stays readable.

// Pure, deterministic per-particle constants (fractional-sine hash of the index).
const hash = (i: number, salt: number) => {
  const x = Math.sin(i * 127.1 + salt * 311.7) * 43758.5453;
  return x - Math.floor(x);
};

type Bokeh = {
  x0: number; y0: number; size: number; speed: number; swayAmp: number;
  swayFreq: number; phase: number; baseOp: number; blur: number; color: string;
};

const BOKEH: Bokeh[] = Array.from({length: 14}, (_, i) => {
  const r = (salt: number) => hash(i, salt);
  const size = 46 + r(1) * 190; // px at a 1080 short-side basis (scaled at render)
  return {
    x0: r(3) * 100,
    y0: r(4) * 130 - 15,
    speed: 3 + r(5) * 4, // % of frame height per second, rising
    swayAmp: 2 + r(6) * 5,
    swayFreq: 0.25 + r(7) * 0.5,
    phase: r(8) * Math.PI * 2,
    baseOp: 0.08 + r(9) * 0.1,
    size,
    blur: 6 + (size / 236) * 28, // bigger disc = nearer = softer
    color: r(2) > 0.78 ? '61,220,132' : '196,220,255', // mostly cool white-blue, some green
  };
});

const SWEEP_PERIOD = 11; // seconds per light-sweep crossing

export const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const t = frame / fps;
  const u = Math.min(width, height) / 1080; // scale px constants to the render size

  // Unique filter id per instance (deterministic; spec note — avoid collisions when
  // more than one Background mounts on the same page). useId is SSR/Remotion-safe;
  // strip colons so it is a clean SVG fragment id.
  const noiseId = `bg-fractal-noise-${React.useId().replace(/:/g, '')}`;

  // Layer 1 — breath (5s period; was 8s pre-2026-07-06)
  const breath = Math.sin((t / 5) * Math.PI * 2);
  const scale = 1.05 + 0.05 * breath; // 1.00 → 1.10
  const glowOpacity = 0.15 * ((1 + breath) / 2); // 0 → 0.15, in sync with the breath

  // Layer 2 — elliptical orbit of the main hotspot (7s period, ±12% H / ±8% V).
  // Same angular frequency on both axes + 90° phase (cos vs sin) ⇒ a true ellipse.
  const orbitOmega = (Math.PI * 2) / 7;
  const hx = 50 + 12 * Math.cos(t * orbitOmega);
  const hy = 40 + 8 * Math.sin(t * orbitOmega);

  // Secondary green aurora on its own independent, faster Lissajous path (depth).
  const ax = 30 + 22 * Math.sin(t * 0.3 + 1.2);
  const ay = 66 + 16 * Math.cos(t * 0.26);

  // Layer 4 — light sweep position: -70% (off left) → +170% (off right) each period.
  const sweepX = -70 + 240 * ((t % SWEEP_PERIOD) / SWEEP_PERIOD);

  // Layer 5 — drifting fractal-noise grain (static texture; motion is transform-only).
  const noiseOffX = Math.sin(t * 0.15) * 220; // ~40s period (was ~90s)
  const noiseOffY = Math.cos(t * 0.12) * 160;
  const noiseScale = 1 + 0.08 * Math.sin(t * 0.23); // ±8%, ~27s period

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
          background: `radial-gradient(44% 44% at ${ax}% ${ay}%, rgba(61,220,132,.16) 0%, rgba(61,220,132,0) 70%)`,
          mixBlendMode: 'screen',
        }}
      />
      {/* Layer 3 — bokeh field: seeded discs rising, swaying, twinkling (wraps vertically) */}
      <AbsoluteFill style={{mixBlendMode: 'screen'}}>
        {BOKEH.map((b, i) => {
          const y = ((((b.y0 - b.speed * t) % 130) + 130) % 130) - 15; // -15 → 115, wraps
          const x = b.x0 + b.swayAmp * Math.sin(t * b.swayFreq + b.phase);
          const op = b.baseOp * (0.55 + 0.45 * Math.sin(t * (0.4 + b.swayFreq) + b.phase * 2));
          const px = b.size * u;
          return (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: `${x}%`,
                top: `${y}%`,
                width: px,
                height: px,
                marginLeft: -px / 2,
                marginTop: -px / 2,
                borderRadius: '50%',
                background: `radial-gradient(circle, rgba(${b.color},${op.toFixed(3)}) 0%, rgba(${b.color},0) 70%)`,
                filter: `blur(${(b.blur * u).toFixed(1)}px)`,
              }}
            />
          );
        })}
      </AbsoluteFill>
      {/* Layer 4 — periodic diagonal light sweep */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(108deg, rgba(190,215,255,0) ${sweepX - 22}%, rgba(190,215,255,.06) ${sweepX}%, rgba(190,215,255,0) ${sweepX + 22}%)`,
          mixBlendMode: 'screen',
        }}
      />
      {/* Layer 5 — drifting fractal-noise grain */}
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
      {/* Layer 6 — vignette */}
      <AbsoluteFill style={{boxShadow: 'inset 0 0 380px rgba(0,0,0,.6)'}} />
    </AbsoluteFill>
  );
};
