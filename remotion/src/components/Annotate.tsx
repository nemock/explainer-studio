import React from 'react';
import {AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import rough from 'roughjs';
import {BRAND} from '../brand';

// motion-playbook §2H — the annotation overlay: hand-drawn arrows/circles/underlines
// that DRAW THEMSELVES starting on a narration cue, leading the eye while the voice
// talks. Two families, one layer:
//   vector kinds (rough.js, seeded): arrow | circle | underline | strike | box —
//     precise point-to-point geometry with true stroke draw-on
//   doodle kind: an operator-licensed CopyDoodles stamp (real Sharpie scans), tinted
//     via CSS mask, revealed with a pop or wipe
// Every annotation: {kind, cueFrame, color?: 'green'|'red'|'white', label?} plus
// per-kind geometry in 0-1 frame space: from/to (arrow, strike), at+w/h (circle, box,
// underline, doodle). cueFrame is resolved by the Python spec-builder from a spoken
// phrase — the React side stays a pure function of frame.
//
// Determinism: rough.js is ALWAYS seeded (hash of geometry + index); no randomness.

const seedFrom = (s: string) => {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 2147483645) + 1; // rough.js treats 0 as "random" — never allow it
};

const COLOR: Record<string, string> = {green: BRAND.green, red: BRAND.red, white: BRAND.white};

type Ann = {
  kind: 'arrow' | 'circle' | 'underline' | 'strike' | 'box' | 'doodle';
  cueFrame: number;
  color?: 'green' | 'red' | 'white';
  label?: string;
  from?: [number, number];
  to?: [number, number];
  at?: [number, number];
  w?: number;
  h?: number;
  // doodle-only
  file?: string;
  aspect?: number;
  rotate?: number;
  reveal?: 'pop' | 'wipe';
};

// one rough drawable -> svg paths + an estimated ink length (for draw-on pacing)
const useRoughPaths = (a: Ann, i: number, W: number, H: number) => {
  return React.useMemo(() => {
    const gen = rough.generator();
    const color = COLOR[a.color || 'green'];
    const sw = Math.max(3, H * 0.007);
    const opts = {seed: seedFrom(`${a.kind}:${i}:${a.from}:${a.to}:${a.at}`), roughness: 2.2,
                  bowing: 1.6, stroke: color, strokeWidth: sw, fill: undefined};
    const px = (p?: [number, number]): [number, number] => [(p?.[0] ?? 0.5) * W, (p?.[1] ?? 0.5) * H];
    let drawable = null;
    let length = 0;
    let tip: {x: number; y: number; angle: number} | null = null;
    if (a.kind === 'arrow' || a.kind === 'strike') {
      const [x1, y1] = px(a.from);
      const [x2, y2] = px(a.to);
      drawable = gen.line(x1, y1, x2, y2, opts);
      length = Math.hypot(x2 - x1, y2 - y1) * 2.3; // rough double-stroke
      if (a.kind === 'arrow') tip = {x: x2, y: y2, angle: Math.atan2(y2 - y1, x2 - x1)};
    } else if (a.kind === 'circle') {
      const [cx, cy] = px(a.at);
      const w = (a.w ?? 0.2) * W;
      const h = (a.h ?? 0.14) * H;
      drawable = gen.ellipse(cx, cy, w, h, opts);
      length = Math.PI * (w + h) * 1.2; // two passes
    } else if (a.kind === 'box') {
      const [cx, cy] = px(a.at);
      const w = (a.w ?? 0.24) * W;
      const h = (a.h ?? 0.16) * H;
      drawable = gen.rectangle(cx - w / 2, cy - h / 2, w, h, opts);
      length = 2 * (w + h) * 2.3;
    } else if (a.kind === 'underline') {
      const [cx, cy] = px(a.at);
      const w = (a.w ?? 0.24) * W;
      drawable = gen.line(cx - w / 2, cy, cx + w / 2, cy, {...opts, bowing: 3});
      length = w * 2.3;
    }
    const paths = drawable ? gen.toPaths(drawable) : [];
    return {paths, length: Math.max(60, length), color, sw, tip};
  }, [a, i, W, H]);
};

const VectorAnn: React.FC<{a: Ann; i: number}> = ({a, i}) => {
  const frame = useCurrentFrame();
  const {fps, width: W, height: H} = useVideoConfig();
  const {paths, length, color, sw, tip} = useRoughPaths(a, i, W, H);
  const drawFrames = Math.round((a.kind === 'circle' || a.kind === 'box' ? 0.8 : 0.55) * fps);
  const t = interpolate(frame, [a.cueFrame, a.cueFrame + drawFrames], [0, 1],
                        {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (frame < a.cueFrame) return null;
  const tipO = interpolate(t, [0.8, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const headLen = Math.max(18, H * 0.032);
  return (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
      {paths.map((p, j) => (
        <path key={j} d={p.d} fill="none" stroke={color} strokeWidth={sw}
              strokeLinecap="round" strokeLinejoin="round"
              strokeDasharray={length} strokeDashoffset={length * (1 - t)}
              style={{filter: `drop-shadow(0 0 12px ${color}66)`}} />
      ))}
      {tip ? (
        <g opacity={tipO} stroke={color} strokeWidth={sw} strokeLinecap="round" fill="none">
          <line x1={tip.x} y1={tip.y}
                x2={tip.x - headLen * Math.cos(tip.angle - 0.46)}
                y2={tip.y - headLen * Math.sin(tip.angle - 0.46)} />
          <line x1={tip.x} y1={tip.y}
                x2={tip.x - headLen * Math.cos(tip.angle + 0.46)}
                y2={tip.y - headLen * Math.sin(tip.angle + 0.46)} />
        </g>
      ) : null}
    </svg>
  );
};

const DoodleAnn: React.FC<{a: Ann}> = ({a}) => {
  const frame = useCurrentFrame();
  const {fps, width: W, height: H} = useVideoConfig();
  if (!a.file || frame < a.cueFrame) return null;
  const color = COLOR[a.color || 'white'];
  const w = (a.w ?? 0.14) * W;
  const h = w / (a.aspect || 1);
  const [cx, cy] = [(a.at?.[0] ?? 0.5) * W, (a.at?.[1] ?? 0.5) * H];
  const e = spring({frame: frame - a.cueFrame, fps, config: {damping: 13, stiffness: 160}});
  const wipe = interpolate(frame, [a.cueFrame, a.cueFrame + 0.5 * fps], [0, 100],
                           {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const reveal = a.reveal || 'pop';
  const url = `url(${JSON.stringify(staticFile(a.file))})`;
  return (
    <div style={{
      position: 'absolute', left: cx - w / 2, top: cy - h / 2, width: w, height: h,
      backgroundColor: color,
      WebkitMaskImage: url, maskImage: url,
      WebkitMaskSize: '100% 100%', maskSize: '100% 100%',
      WebkitMaskRepeat: 'no-repeat', maskRepeat: 'no-repeat',
      opacity: reveal === 'pop' ? e : 1,
      clipPath: reveal === 'wipe' ? `inset(0 ${100 - wipe}% 0 0)` : undefined,
      transform: `rotate(${(a.rotate ?? 0) + (reveal === 'pop' ? (1 - e) * -6 : 0)}deg) ` +
                 `scale(${reveal === 'pop' ? 0.7 + 0.3 * e : 1})`,
      filter: `drop-shadow(0 0 14px ${color}55)`,
    }} />
  );
};

export const AnnotateOverlay: React.FC<{annotations: Ann[]}> = ({annotations}) => {
  const frame = useCurrentFrame();
  const {fps, height: H} = useVideoConfig();
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {annotations.map((a, i) => (
        a.kind === 'doodle' ? <DoodleAnn key={i} a={a} /> : <VectorAnn key={i} a={a} i={i} />
      ))}
      {annotations.map((a, i) => {
        if (!a.label) return null;
        const lx = (a.to?.[0] ?? a.at?.[0] ?? 0.5);
        const ly = (a.to?.[1] ?? a.at?.[1] ?? 0.5);
        const o = spring({frame: frame - a.cueFrame - Math.round(0.4 * fps), fps, config: {damping: 16}});
        return (
          <div key={`l${i}`} style={{
            position: 'absolute', left: `${lx * 100}%`, top: `${ly * 100}%`,
            transform: `translate(-50%, ${H * 0.02}px)`,
            fontFamily: BRAND.font, fontStyle: 'italic', fontWeight: 800,
            fontSize: H * 0.026, color: COLOR[a.color || 'green'], opacity: o,
            textShadow: '0 3px 14px rgba(0,0,0,.7)', whiteSpace: 'nowrap',
          }}>
            {a.label}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
