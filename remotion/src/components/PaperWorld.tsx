import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {PaperWorldTokens, PAPER_FWF, SNAP, HINGE, CAM} from '../brands/papercraft';

// Papercraft Motion — shared world infrastructure (papercraft-motion-spec.md §2/§3/§6).
// The scene is a miniature SET on a dark table: four planes (table/set/stage/float)
// under one camera, paper-physics entrances, and a key light. All motion is a pure
// function of frame (deterministic). HARD RULE: paper never floats — no ambient drift;
// stillness between beats is the stop-motion hold (operator veto 2026-07-16).

export type Camera = {x: number; y: number; zoom: number};
export type CameraMove = {at: number; to: Partial<Camera>};

export const PLANE = {table: 0.15, set: 0.45, stage: 1.0, float: 1.25} as const;

// Resolve the scene camera at `frame`: starts centered, spring-steps through moves
// (each a 12–18f settle, then dead-still hold — never a continuous drift).
export const resolveCamera = (frame: number, fps: number, moves: CameraMove[] = []): Camera => {
  let cam: Camera = {x: 0.5, y: 0.5, zoom: 1};
  for (const mv of moves) {
    const t = spring({frame: frame - mv.at, fps, config: CAM, durationInFrames: 24});
    if (frame < mv.at) continue;
    cam = {
      x: cam.x + ((mv.to.x ?? cam.x) - cam.x) * t,
      y: cam.y + ((mv.to.y ?? cam.y) - cam.y) * t,
      zoom: cam.zoom + ((mv.to.zoom ?? cam.zoom) - cam.zoom) * t,
    };
  }
  return cam;
};

// Plane wrapper: parallax transform of the shared camera scaled by the plane factor.
export const Plane: React.FC<{cam: Camera; factor: number; children: React.ReactNode}> = ({cam, factor, children}) => {
  const {width, height} = useVideoConfig();
  const tx = (0.5 - cam.x) * width * factor;
  const ty = (0.5 - cam.y) * height * factor;
  const sc = 1 + (cam.zoom - 1) * factor;
  return (
    <AbsoluteFill style={{transform: `translate(${tx.toFixed(2)}px, ${ty.toFixed(2)}px) scale(${sc.toFixed(4)})`, transformOrigin: '50% 50%'}}>
      {children}
    </AbsoluteFill>
  );
};

// --- paper physics (spec §3) ------------------------------------------------
// place: drops in with a 1-frame overshoot; the shadow lands 3–4 frames AFTER
// the object (the unseen hand). Returns styles for the object and its shadow.
export const usePlace = (at: number) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const e = spring({frame: frame - at, fps, config: SNAP});
  const vis = frame >= at;
  return {
    object: {
      opacity: vis ? 1 : 0,
      transform: `translateY(${((1 - e) * -height * 0.022).toFixed(2)}px) scale(${(1.06 - 0.06 * e).toFixed(4)})`,
    } as React.CSSProperties,
    shadowOpacity: interpolate(frame, [at + 3, at + 7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
    settled: e,
  };
};

// popup: hinges up from the table like a pop-up book page (origin: base edge).
export const usePopup = (at: number) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const e = spring({frame: frame - at, fps, config: HINGE});
  const vis = frame >= at;
  return {
    object: {
      opacity: vis ? 1 : 0,
      transform: `perspective(1200px) rotateX(${(85 * (1 - e)).toFixed(2)}deg)`,
      transformOrigin: '50% 100%',
    } as React.CSSProperties,
    shadow: {opacity: vis ? 0.25 + 0.75 * e : 0, transform: `scaleY(${(0.15 + 0.85 * e).toFixed(3)})`} as React.CSSProperties,
    settled: e,
  };
};

// flick: 2-frame percussive scale hit on an already-present element (beat accent).
export const flick = (frame: number, at: number): number =>
  interpolate(frame, [at, at + 2, at + 6], [1, 1.045, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

// Pure (non-hook) place physics — for elements created in loops (e.g. counter chips).
export const placeStyle = (frame: number, fps: number, height: number, at: number): React.CSSProperties => {
  const e = spring({frame: frame - at, fps, config: SNAP});
  return {
    opacity: frame >= at ? 1 : 0,
    transform: `translateY(${((1 - e) * -height * 0.022).toFixed(2)}px) scale(${(1.06 - 0.06 * e).toFixed(4)})`,
  };
};

// Pure (non-hook) popup physics — for hinged elements created in loops (stairs, trays).
export const popupStyle = (frame: number, fps: number, at: number): React.CSSProperties => {
  const e = spring({frame: frame - at, fps, config: HINGE});
  return {
    opacity: frame >= at ? 1 : 0,
    transform: `perspective(1200px) rotateX(${(85 * (1 - e)).toFixed(2)}deg)`,
    transformOrigin: '50% 100%',
  };
};

// --- tear transition (spec §4) ----------------------------------------------
// Two ink-dark halves with a seeded jagged seam part to reveal the incoming
// scene (scene-local, deterministic; ~14 frames, loud). Rendered by SceneWrap
// when the deck slide sets "transition": "tear".
const tearPoints = (seed: string, n = 9): number[] => {
  const out: number[] = [];
  for (let i = 0; i < n; i++) out.push((hash(seed + i) - 0.5) * 6); // % jitter around the seam
  return out;
};

export const TearReveal: React.FC<{seed?: string; world?: PaperWorldTokens}> = ({seed = 't', world = PAPER_FWF}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const DUR = 14;
  if (frame >= DUR + 6) return null;
  const e = spring({frame, fps, config: {damping: 15, stiffness: 120}});
  const jit = tearPoints(seed);
  const seam = (off: number) =>
    jit.map((j, i) => `${(50 + j + off).toFixed(2)}% ${(i * 100 / (jit.length - 1)).toFixed(2)}%`).join(', ');
  // left half: 0..seam ; right half: seam..100 — both slide out as e rises
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <AbsoluteFill style={{background: world.groundDeep, transform: `translateX(${(-e * 104).toFixed(2)}%)`,
                            clipPath: `polygon(0% 0%, ${seam(1.5)}, 0% 100%)`,
                            boxShadow: `40px 0 80px ${world.shadow}`}} />
      <AbsoluteFill style={{background: world.ground, transform: `translateX(${(e * 104).toFixed(2)}%)`,
                            clipPath: `polygon(100% 0%, ${seam(-1.5)}, 100% 100%)`}} />
    </AbsoluteFill>
  );
};

// --- the table (P0) + key light (spec §6) -----------------------------------
const hash = (s: string) => {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return (h >>> 0) / 4294967295;
};

// PaperTable: ink ground + vignette + 2–3 big paper sheets (seeded layout) +
// the key light. `tightenAt` snaps the light to a spotlight on that frame
// (midroll punch / stat landing); STILL between events by design.
export const PaperTable: React.FC<{
  world?: PaperWorldTokens;
  seed?: string;
  tightenAt?: number | null;
  mood?: 'soft' | 'hard';
}> = ({world = PAPER_FWF, seed = 'set', tightenAt = null, mood = 'soft'}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const r1 = hash(seed), r2 = hash(seed + 'b'), r3 = hash(seed + 'c');
  // spotlight snap: 6 frames, on cue (spec §6)
  const tight = tightenAt == null ? 0 : interpolate(frame, [tightenAt, tightenAt + 6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const radius = 78 - 30 * tight;                 // % of frame
  const surround = 0.22 + 0.26 * tight + (mood === 'hard' ? 0.1 : 0);
  const sheetShadow = `0 ${height * 0.018}px ${height * 0.05}px ${world.shadow}`;
  return (
    <AbsoluteFill style={{background: world.ground}}>
      {/* big paper sheets laid on the table (the hero-a ground language) */}
      <div style={{position: 'absolute', left: width * (0.06 + r1 * 0.08), top: height * (0.52 + r2 * 0.1),
                   width: width * 0.46, height: height * 0.5, background: world.sheet,
                   transform: `rotate(${(-4 + r1 * 8).toFixed(2)}deg)`, boxShadow: sheetShadow}} />
      <div style={{position: 'absolute', right: width * (0.04 + r2 * 0.07), top: height * (0.6 + r3 * 0.08),
                   width: width * 0.38, height: height * 0.44, background: world.sheetAlt,
                   transform: `rotate(${(3 - r2 * 7).toFixed(2)}deg)`, boxShadow: sheetShadow}} />
      <div style={{position: 'absolute', left: width * (0.3 + r3 * 0.2), top: height * (0.78 + r1 * 0.06),
                   width: width * 0.5, height: height * 0.35, background: world.sheet, opacity: 0.75,
                   transform: `rotate(${(-2 + r3 * 5).toFixed(2)}deg)`, boxShadow: sheetShadow}} />
      {/* vignette toward groundDeep */}
      <AbsoluteFill style={{background: `radial-gradient(120% 105% at 50% 42%, transparent 45%, ${world.groundDeep} 100%)`}} />
      {/* key light: wide + soft by default; tightens on cue */}
      <AbsoluteFill style={{
        background: `radial-gradient(${radius}% ${radius * 0.85}% at 50% 40%, rgba(255,246,230,${(0.10 + 0.06 * tight).toFixed(3)}) 0%, rgba(255,246,230,0) 62%, rgba(10,3,20,${surround.toFixed(3)}) 100%)`,
      }} />
    </AbsoluteFill>
  );
};

// A cream paper card (text always printed ON paper — spec §0). Paper thickness
// via the shade edge; shadow provided by the caller (so place/popup can lag it).
export const PaperCard: React.FC<{
  world?: PaperWorldTokens;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({world = PAPER_FWF, style, children}) => (
  <div style={{background: world.paper, borderRadius: 14,
               borderBottom: `6px solid ${world.paperShade}`,
               padding: '0.6em 0.9em', ...style}}>
    {children}
  </div>
);
