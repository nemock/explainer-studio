import React, {createContext, useContext} from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {PaperWorldTokens, PAPER_FWF, paperWorldFor, SNAP, HINGE, CAM} from '../brands/papercraft';
import {PaperSheet, CardFamily} from './PaperNote';

// World context (2026-07-26) — which channel's paper ground/palette this render uses.
// Mirrors InkProvider: theme-keyed, defaulting to FWF so every existing paper deck is
// byte-identical. Components call useWorld() instead of importing PAPER_FWF directly,
// which is what let BRG get its own ground without repainting Dave's.
const WorldContext = createContext<PaperWorldTokens>(PAPER_FWF);
export const WorldProvider: React.FC<{theme?: string; children: React.ReactNode}> = ({theme, children}) => (
  <WorldContext.Provider value={paperWorldFor(theme)}>{children}</WorldContext.Provider>
);
export const useWorld = (): PaperWorldTokens => useContext(WorldContext);

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
// Two ink-dark halves part along a torn seam to reveal the incoming scene
// (scene-local, deterministic; ~14 frames, loud). Rendered by SceneWrap when
// the deck slide sets "transition": "tear". The seam was a seeded 9-point
// polygon until 2026-08-01; it is now a generated torn-fibre alpha mask, which
// carries detail a handful of jitter points never could.

export const TearReveal: React.FC<{seed?: string; world?: PaperWorldTokens}> = ({seed = 't', world: worldProp}) => {
  const world = worldProp ?? useWorld();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const DUR = 14;
  if (frame >= DUR + 6) return null;
  const e = spring({frame, fps, config: {damping: 15, stiffness: 120}});
  // Phase 4: the seam is a real torn fibre edge, not a seeded polygon. tear_vl / tear_vr are
  // a complementary pair cut from ONE generated tear, so the two halves interlock exactly.
  // Take is seeded off the caller's id, so a given act boundary always tears the same way.
  const take = (Math.floor(hash(seed) * 4) % 4) + 1;
  const maskOf = (side: 'vl' | 'vr'): React.CSSProperties => {
    const url = `url(${staticFile(`papercraft-grounds/tear_${side}_${take}.webp`)})`;
    return {WebkitMaskImage: url, maskImage: url,
            WebkitMaskSize: '100% 100%', maskSize: '100% 100%',
            WebkitMaskRepeat: 'no-repeat', maskRepeat: 'no-repeat'};
  };
  // left half: paper up to the tear ; right half: the complement — both slide out as e rises
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <AbsoluteFill style={{background: world.groundDeep, transform: `translateX(${(-e * 104).toFixed(2)}%)`,
                            ...maskOf('vl')}} />
      <AbsoluteFill style={{background: world.ground, transform: `translateX(${(e * 104).toFixed(2)}%)`,
                            ...maskOf('vr')}} />
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
}> = ({world: worldProp, seed = 'set', tightenAt = null, mood = 'soft'}) => {
  const world = worldProp ?? useWorld();
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
      {/* the table itself is real paper stock (phase 4), tinted to the channel's ground so
          every paper world keeps its own colour. Sits under the laid sheets and the light. */}
      <Img src={staticFile(`papercraft-grounds/ground_table_${(hash(seed + 'g') > 0.5 ? 2 : 1)}.webp`)}
           style={{position: 'absolute', inset: 0, width: '100%', height: '100%',
                   objectFit: 'cover', display: 'block', mixBlendMode: 'overlay'}} />
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

// A cream paper card (text always printed ON paper — spec §0). The card is REAL generated
// paper as of 2026-08-01 (papercraft-substrate-plan.md phase 2), 9-sliced so the cut edge
// and grain hold at any content size. The flat `world.paper` fill and the fake `borderBottom`
// thickness edge were the primitive that made every card in the system read as a UI element
// pasted into a photograph — and PaperCard backs punch cards, define tags, compare trays,
// list cards, keep-cards and the CTA, so this one swap carries all of them.
//
// `id` seeds which take is used; pass a stable per-element string so two cards on the same
// slide don't share paper. `substrate={false}` opts an individual card back out.
export const PaperCard: React.FC<{
  world?: PaperWorldTokens;
  style?: React.CSSProperties;
  id?: string;
  family?: CardFamily;
  substrate?: boolean;
  children: React.ReactNode;
}> = ({world: worldProp, style, id, family, substrate = true, children}) => {
  const world = worldProp ?? useWorld();
  const radius = (style?.borderRadius as number) ?? 14;
  if (!substrate) {
    return (
      <div style={{background: world.paper, borderRadius: 14,
                   borderBottom: `6px solid ${world.paperShade}`,
                   padding: '0.6em 0.9em', ...style}}>
        {children}
      </div>
    );
  }
  return (
    // position:relative so the substrate backdrop can fill this box without touching the
    // caller's padding or size; content rides above it in the normal flow.
    <div style={{position: 'relative', borderRadius: radius, padding: '0.6em 0.9em', ...style}}>
      {/* tinted to world.paper, not left as generated. The card stock comes out warmer than
          the world's cream, and unnormalised it reads as kraft next to every other cream
          surface in the scene. Routing it through the tint keeps the real grain and cut edge
          while landing the colour exactly on the channel's token — which also means theme
          isolation holds for free: BRG, Circumvent and Cut & Bond each get their own paper. */}
      <PaperSheet id={id ?? 'card'} family={family} radius={radius} tint={world.paper} />
      <div style={{position: 'relative'}}>{children}</div>
    </div>
  );
};
