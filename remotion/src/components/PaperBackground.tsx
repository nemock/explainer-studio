import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
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
      {/* REAL paper ground (phase 4). This is the single most-seen surface in the catalogue —
          it sits behind every Figure, Schematic, StatCounter and StatGrid scene — and it was
          a flat radial gradient with an feTurbulence fractal-noise layer over it. Now it is
          a generated sheet with actual fibre, which also retires a full-frame live SVG filter.
          Desaturated then multiplied, exactly as the cards are, so the colour still comes from
          the palette constant and no existing render shifts hue. */}
      {/* The asset is a flat grey texture tile centred on 128 (see the library's
          texture_prep note), so it OVERLAYS the palette colour rather than multiplying it:
          multiply would halve the brightness, and the earlier grayscale+brightness+multiply
          route flattened the fibre to roughly one grey level. Overlay leaves the mean exactly
          on the palette value and modulates only by the fibre deviation. */}
      <Img
        src={staticFile('papercraft-grounds/ground_cream_1.webp')}
        style={{position: 'absolute', inset: 0, width: '100%', height: '100%',
                objectFit: 'cover', display: 'block', mixBlendMode: 'overlay'}}
      />
      {/* The warm top-center light. Was an opaque colour ramp that defined the whole tonal
          field; now alpha-only, or it would bury the fibre it sits on. */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(130% 100% at ${hx}% ${hy}%, rgba(255,250,229,.55) 0%, rgba(255,250,229,0) 52%, rgba(96,74,34,.13) 100%)`,
        }}
      />
      {/* the breathing highlight — kept. The ground itself is a still image, and a fully
          frozen frame risks tripping freezedetect in QA; this is what keeps it alive. */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(48% 42% at ${hx}% ${hy}%, rgba(255,255,255,${glow.toFixed(3)}) 0%, rgba(255,255,255,0) 70%)`,
          mixBlendMode: 'screen',
        }}
      />
      {/* soft warm vignette to hold weight toward the center */}
      <AbsoluteFill style={{boxShadow: 'inset 0 0 340px rgba(120,92,40,.16)'}} />
    </AbsoluteFill>
  );
};
