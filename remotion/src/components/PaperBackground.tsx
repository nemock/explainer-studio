import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {CUTANDBOND} from '../brands/cutandbond';

// The Cut & Bond paper world backdrop (2026-07-15). The persistent surface every
// paper cutout sits on — selected by the paper themes ('nemock-deep-dive' / 'cut-bond') in Video.tsx, in place of the
// navy studio Background. Paper should feel STILL and tactile, not like navy space:
// motion here is deliberately minimal (a slow warm-light breath + a barely-drifting
// fiber grain) so it never reads as animated, only alive. All motion is frame-driven
// and deterministic (no CSS animation, no unseeded random) per the render-correctness rule.
export const PaperBackground: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  const noiseId = `paper-fiber-${React.useId().replace(/:/g, '')}`;

  // very slow warm-light breath (12s), so the surface is never dead (QA dead-air) but
  // stays subtle enough that you don't "watch" it.
  const breath = Math.sin((t / 12) * Math.PI * 2);
  const glow = 0.06 + 0.04 * ((1 + breath) / 2); // 0.06 -> 0.10
  // Near-still light + grain (Dave 2026-07-16: the drifting light + grain read as a
  // distracting gyration). A whisper of movement only — the paper should sit still.
  const hx = 50 + 0.9 * Math.cos(t * ((Math.PI * 2) / 46)); // barely-moving hotspot
  const hy = 34 + 0.6 * Math.sin(t * ((Math.PI * 2) / 46));

  // fiber grain drifts only a few px, very slowly — no perceptible crawl.
  const gx = Math.sin(t * 0.05) * 6;
  const gy = Math.cos(t * 0.045) * 5;

  return (
    <AbsoluteFill style={{backgroundColor: CUTANDBOND.paper}}>
      {/* warm paper base with a soft top-center light */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(130% 100% at ${hx}% ${hy}%, #fbf4df 0%, ${CUTANDBOND.paper} 52%, ${CUTANDBOND.paperDeep} 100%)`,
        }}
      />
      {/* the breathing highlight */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(48% 42% at ${hx}% ${hy}%, rgba(255,255,255,${glow.toFixed(3)}) 0%, rgba(255,255,255,0) 70%)`,
          mixBlendMode: 'screen',
        }}
      />
      {/* paper fiber tooth — multiply, very low opacity, slow drift */}
      <AbsoluteFill style={{overflow: 'hidden', mixBlendMode: 'multiply', opacity: 0.05}}>
        <svg
          style={{
            position: 'absolute',
            width: '160%',
            height: '160%',
            left: `calc(-30% + ${gx}px)`,
            top: `calc(-30% + ${gy}px)`,
          }}
        >
          <defs>
            <filter id={noiseId}>
              <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} stitchTiles="stitch" />
            </filter>
          </defs>
          <rect width="100%" height="100%" filter={`url(#${noiseId})`} />
        </svg>
      </AbsoluteFill>
      {/* soft warm vignette to hold weight toward the center */}
      <AbsoluteFill style={{boxShadow: 'inset 0 0 340px rgba(120,92,40,.16)'}} />
    </AbsoluteFill>
  );
};
