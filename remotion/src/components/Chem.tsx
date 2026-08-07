import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {CUTANDBOND as CB} from '../brands/cutandbond';

// Cut & Bond — the paper chemistry component kit (2026-07-15).
// Every piece is a THICK cut-paper shape: a top face, a darker extruded EDGE (the paper's
// side), and a soft cast shadow on the layer beneath — so pieces read as physically
// stacked (base sheet < ring < nucleus, electron riding on the ring), not flat stickers.
// The electron orbits on a QUANTIZED clock for a hand-made stop-motion cadence.
// Frame-driven only (no CSS animation / unseeded random) per the render-correctness rule.
// Slides route here via the deck's direct-component escape hatch
// ({component: "PaperAtom", fields: {...}}), so none of these need a _scene_for entry.

const NEUTRON = '#c9b48f'; // muted tan paper for neutrons (vs the coral proton)

// A tiling grain texture (fractal noise) painted onto the solid pieces at low multiply
// opacity — the tooth of real paper, so a flat fill never looks like plastic.
const GRAIN =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='g'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23g)'/%3E%3C/svg%3E";

const Grain: React.FC<{round?: boolean}> = ({round}) => (
  <div style={{
    position: 'absolute', inset: 0, borderRadius: round ? '50%' : 'inherit',
    backgroundImage: `url("${GRAIN}")`, backgroundSize: '120px 120px',
    mixBlendMode: 'multiply', opacity: 0.2, pointerEvents: 'none',
  }} />
);

// A reusable SVG filter that roughens a piece's edges into a hand-cut, scissor-snipped
// wobble (feTurbulence displaces the outline). Same id -> identical displacement, so a
// piece's top face, extruded edge and cast shadow all rough TOGETHER and stay aligned.
// Deterministic (fixed seed) per the render-correctness rule.
const RoughDefs: React.FC<{id: string; scale?: number; freq?: number}> = ({id, scale = 7, freq = 0.02}) => (
  <svg width={0} height={0} style={{position: 'absolute'}} aria-hidden>
    <defs>
      <filter id={id} x="-60%" y="-60%" width="220%" height="220%">
        <feTurbulence type="fractalNoise" baseFrequency={freq} numOctaves={2} seed={4} result="n" />
        <feDisplacementMap in="SourceGraphic" in2="n" scale={scale} xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </defs>
  </svg>
);

// darken a #rrggbb hex toward black by factor f (the extruded paper edge is the piece's
// own color, darker — like the shadowed side of a real paper cut-out).
const darken = (hex: string, f = 0.68): string => {
  const m = hex.replace('#', '');
  const r = Math.round(parseInt(m.slice(0, 2), 16) * f);
  const g = Math.round(parseInt(m.slice(2, 4), 16) * f);
  const b = Math.round(parseInt(m.slice(4, 6), 16) * f);
  return `rgb(${r},${g},${b})`;
};

// box-shadow recipe for a solid paper piece floating at height `lift` above the surface:
// a stacked extruded edge of thickness `th` + a soft cast shadow further below.
const thick = (color: string, th: number, lift: number, blur: number, op: number): string => {
  const edge = darken(color);
  const layers: string[] = [];
  for (let k = 1; k <= th; k++) layers.push(`0 ${k}px 0 ${edge}`); // the paper's side
  layers.push(`0 ${th + lift}px ${blur}px rgba(70,52,20,${op})`);  // cast shadow on the layer below
  layers.push('inset 0 2px 0 rgba(255,255,255,.22)');             // faint top bevel
  return layers.join(', ');
};

// STOP-MOTION clock: the orbit advances in discrete hops (hold N frames, then jump) so
// the electron moves like a stop-motion puppet, not a smooth tween.
const STEP = 6; // frames held per hop (30fps -> 5 hops/sec) — calm stop-motion cadence

// ---------------------------------------------------------------------------
// PaperAtom — thick paper nucleus + thick electron shell(s); electron rides the
// ring on a stop-motion clock. fields:
//   {protons, neutrons, shells:[e per shell], accent, nucleusColor, name, number,
//    label:'name'|'symbol'|'none', spin}
// ---------------------------------------------------------------------------
// AtomGlyph — one atom (packed paper nucleus + electron shells, stop-motion orbit), sized
// by outer radius R. Extracted so PaperAtom and PaperMolecule share it. `phase` offsets the
// orbit so paired atoms in a molecule don't look identical. All internals scale off R.
const AtomGlyph: React.FC<{
  protons: number; neutrons: number; shells: number[]; accent: string; nucleusColor: string;
  R: number; rough: string; spin?: boolean; phase?: number;
}> = ({protons, neutrons, shells, accent, nucleusColor, R, rough, spin = true, phase = 0}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const k = (width / 1080) * (R / (width * 0.30)); // depth scale (= full-size atom at R=0.30w)
  const N = protons + neutrons;
  const nucIn = spring({frame: frame - 2, fps, config: {damping: 14, stiffness: 130}});
  const hop = Math.floor(frame / STEP);
  const d = R * 0.1733 * Math.min(1, 2.3 / Math.sqrt(N));
  const spacing = d * 0.62;
  const nucleons = Array.from({length: N}, (_, i) => {
    const ang = i * 2.399963;
    const r = spacing * Math.sqrt(i);
    return {x: r * Math.cos(ang), y: r * Math.sin(ang), proton: i < protons};
  });
  const innerR = Math.max(R * 0.4333, spacing * Math.sqrt(N) + d);
  const shellR = (i: number) => shells.length === 1 ? R * 0.72 : innerR + (R - innerR) * (i / (shells.length - 1));
  const ringThick = Math.max(6, R * 0.0367);
  const eD = R * 0.1667;
  return (
    <div style={{position: 'relative', width: R * 2, height: R * 2}}>
      {shells.map((count, i) => {
        const rr = shellR(i);
        const ringIn = spring({frame: frame - 6 - i * 5, fps, config: {damping: 16, stiffness: 120}});
        const box = {position: 'absolute' as const, left: R - rr, top: R - rr, width: rr * 2, height: rr * 2,
          borderRadius: '50%', transform: `scale(${ringIn})`, opacity: ringIn};
        const tpo = 24 + i * 8;
        const dir = i % 2 === 0 ? 1 : -1;
        return (
          <React.Fragment key={i}>
            <div style={{...box, top: R - rr + 10 * k, border: `${ringThick}px solid rgba(70,52,20,.16)`, filter: `blur(${8 * k}px)`}} />
            <div style={{...box, top: R - rr + 5 * k, border: `${ringThick}px solid ${darken(accent)}`, filter: rough}} />
            <div style={{...box, border: `${ringThick}px solid ${accent}`, filter: rough}} />
            {Array.from({length: count}, (_, j) => {
              const base = (j / count) * Math.PI * 2 + i * 0.6 + phase;
              const ang = base + (spin ? dir * hop * (Math.PI * 2 / tpo) : 0);
              const ex = R + rr * Math.cos(ang) - eD / 2;
              const ey = R + rr * Math.sin(ang) - eD / 2;
              const eIn = interpolate(frame, [10 + i * 5 + j * 2, 22 + i * 5 + j * 2], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
              return (
                <div key={j} style={{position: 'absolute', left: ex, top: ey, width: eD, height: eD, borderRadius: '50%',
                  background: accent, boxShadow: thick(accent, Math.round(5 * k), 8 * k, 14 * k, 0.26),
                  opacity: eIn, transform: `scale(${eIn})`, filter: rough}}><Grain round /></div>
              );
            })}
          </React.Fragment>
        );
      })}
      <div style={{position: 'absolute', left: R, top: R, transform: `scale(${nucIn})`}}>
        {nucleons.map((n, i) => {
          const c = n.proton ? nucleusColor : NEUTRON;
          return (
            <div key={i} style={{position: 'absolute', left: n.x - d / 2, top: n.y - d / 2, width: d, height: d,
              borderRadius: '50%', background: c, boxShadow: thick(c, Math.round(6 * k), 12 * k, 17 * k, 0.28), filter: rough}}><Grain round /></div>
          );
        })}
      </div>
    </div>
  );
};

export const PaperAtom: React.FC<{fields: any; durationInFrames?: number}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {width} = useVideoConfig();
  const label = fields.label ?? 'name';
  const rid = 'r' + React.useId().replace(/:/g, '');
  const rough = `url(#${rid})`;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
      <RoughDefs id={rid} scale={11} freq={0.014} />
      {label !== 'none' && (fields.number || fields.name) ? (
        <div style={{textAlign: 'center', marginBottom: width * 0.075}}>
          {fields.number ? (
            <div style={{fontFamily: CB.font, fontWeight: 800, fontSize: width * 0.03, letterSpacing: 4,
              color: CB.inkSoft, textTransform: 'uppercase'}}>
              {`Element ${fields.number}`}
            </div>
          ) : null}
          {fields.name && label === 'name' ? (
            <div style={{fontFamily: CB.font, fontWeight: 900, fontSize: width * 0.11, lineHeight: 1,
              color: CB.ink, opacity: interpolate(frame, [2, 14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
              {fields.name}
            </div>
          ) : null}
        </div>
      ) : null}
      <AtomGlyph protons={fields.protons ?? 1} neutrons={fields.neutrons ?? 0}
        shells={Array.isArray(fields.shells) ? fields.shells : [1]}
        accent={fields.accent || CB.teal} nucleusColor={fields.nucleusColor || CB.coral}
        R={width * 0.30} rough={rough} spin={fields.spin !== false} />
    </AbsoluteFill>
  );
};

// LogoAtom — the assembled hydrogen atom (coral proton nucleus, teal ring + a single
// electron parked upper-right) on a TRANSPARENT background: the Cut & Bond channel logo.
// Rendered as a still -> alpha PNG. `spin=false` so the electron sits at a fixed, tidy spot.
export const LogoAtom: React.FC = () => {
  const {width} = useVideoConfig();
  const rid = 'cb-logo-atom';
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <RoughDefs id={rid} scale={11} freq={0.014} />
      <AtomGlyph protons={1} neutrons={0} shells={[1]} accent={'#17b7a6'} nucleusColor={'#ff5a4d'}
        R={width * 0.4} rough={`url(#${rid})`} spin={false} phase={-Math.PI * 0.28} />
    </AbsoluteFill>
  );
};

// PaperMolecule — two (or more) scaled-down atoms side by side, joined by a paper bond.
// Bridges "atoms" -> "molecule": e.g. two oxygen atoms = the O2 you actually breathe.
// fields: {atoms:[{protons,neutrons,shells,accent,nucleusColor}], name, sub, atomR, bondColor}
export const PaperMolecule: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const s = width / 1080;
  const rid = 'r' + React.useId().replace(/:/g, '');
  const rough = `url(#${rid})`;
  const atoms: any[] = fields.atoms || [];
  const R = fields.atomR ?? width * 0.185;
  const bondColor = fields.bondColor || (atoms[0] && atoms[0].accent) || CB.teal;
  const inn = spring({frame: frame - 10, fps, config: {damping: 16, stiffness: 110}});

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
      <RoughDefs id={rid} scale={9} freq={0.02} />
      {fields.name ? (
        <div style={{textAlign: 'center', marginBottom: width * 0.06}}>
          <div style={{fontFamily: CB.font, fontWeight: 900, fontSize: width * 0.11, lineHeight: 1, color: CB.ink}}>
            {fields.name}
          </div>
          {fields.sub ? (
            <div style={{fontFamily: CB.font, fontWeight: 700, fontSize: width * 0.038, color: CB.inkSoft, marginTop: width * 0.015,
              opacity: interpolate(frame, [10, 22], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
              {fields.sub}
            </div>
          ) : null}
        </div>
      ) : null}
      <div style={{display: 'flex', alignItems: 'center'}}>
        {atoms.map((a, i) => (
          <React.Fragment key={i}>
            {i > 0 ? (
              <div style={{display: 'flex', flexDirection: 'column', gap: 12 * s, margin: `0 ${-R * 0.16}px`, zIndex: 3,
                transform: `scaleX(${inn})`, opacity: inn}}>
                <div style={{width: R * 0.55, height: 13 * s, borderRadius: 9 * s, background: darken(bondColor, 0.85),
                  boxShadow: thick(bondColor, Math.round(4 * s), 5 * s, 8 * s, 0.2)}} />
                <div style={{width: R * 0.55, height: 13 * s, borderRadius: 9 * s, background: darken(bondColor, 0.85),
                  boxShadow: thick(bondColor, Math.round(4 * s), 5 * s, 8 * s, 0.2)}} />
              </div>
            ) : null}
            <AtomGlyph protons={a.protons} neutrons={a.neutrons} shells={Array.isArray(a.shells) ? a.shells : [1]}
              accent={a.accent || CB.teal} nucleusColor={a.nucleusColor || CB.coral} R={R} rough={rough} phase={i * Math.PI} />
          </React.Fragment>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// ElementStat — a giant paper number + label, with an optional thick dot pictograph.
// fields: {value, label, sub, accent, filled, total}
// ---------------------------------------------------------------------------
export const ElementStat: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const s = width / 1080;
  const accent = fields.accent || CB.coral;
  const total = fields.total ?? 0;
  const filled = fields.filled ?? 0;
  const pop = spring({frame: frame - 3, fps, config: {damping: 12, stiffness: 130}});
  const dot = width * 0.06;
  const rid = 'r' + React.useId().replace(/:/g, '');
  const rough = `url(#${rid})`;

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
      <RoughDefs id={rid} scale={9} freq={0.016} />
      {total > 0 ? (
        <div style={{display: 'flex', gap: width * 0.02, marginBottom: width * 0.055, maxWidth: '84%',
          flexWrap: 'wrap', justifyContent: 'center'}}>
          {Array.from({length: total}, (_, i) => {
            const inn = interpolate(frame, [6 + i * 2, 16 + i * 2], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
            const c = i < filled ? accent : CB.paperDeep;
            return (
              <div key={i} style={{
                width: dot, height: dot, borderRadius: '50%', background: c,
                boxShadow: thick(c, Math.round(5 * s), 7 * s, 13 * s, 0.24),
                opacity: inn, transform: `scale(${inn})`, filter: rough,
              }}><Grain round /></div>
            );
          })}
        </div>
      ) : null}
      <div style={{fontFamily: CB.font, fontWeight: 900, fontSize: width * 0.24, lineHeight: 0.95,
        color: accent, transform: `scale(${pop})`, textShadow: `0 ${6 * s}px 0 ${darken(accent, 0.6)}, 0 ${16 * s}px ${14 * s}px rgba(70,52,20,.18)`}}>
        {fields.value}
      </div>
      {fields.label ? (
        <div style={{fontFamily: CB.font, fontWeight: 800, fontSize: width * 0.05, color: CB.ink,
          textAlign: 'center', maxWidth: '82%', marginTop: width * 0.03,
          opacity: interpolate(frame, [10, 22], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
          {fields.label}
        </div>
      ) : null}
      {fields.sub ? (
        <div style={{fontFamily: CB.font, fontWeight: 600, fontSize: width * 0.032, color: CB.inkSoft,
          textAlign: 'center', maxWidth: '78%', marginTop: width * 0.015,
          opacity: interpolate(frame, [16, 28], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
          {fields.sub}
        </div>
      ) : null}
      {/* optional decorative paper prop anchored at the bottom of the view (e.g. Earth's crust) */}
      {fields.bottomImage ? (
        <Img src={staticFile(fields.bottomImage)} style={{
          position: 'absolute', bottom: 0, left: 0, width: '100%', height: 'auto',
          opacity: interpolate(frame, [10, 26], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          transform: `translateY(${interpolate(frame, [10, 26], [width * 0.06, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}px)`,
        }} />
      ) : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PaperWord — one big cut-paper concept word (thick, crisp) + an optional sub-line.
// The series' way to NAME a thing (REACTIVE, OXIDATION, the proton's two names).
// fields: {word, sub, accent}
// ---------------------------------------------------------------------------
export const PaperWord: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const s = width / 1080;
  const accent = fields.accent || CB.coral;
  const pop = spring({frame: frame - 3, fps, config: {damping: 13, stiffness: 120}});
  // Gentle one-way idle after the pop: slow float + faint tilt (no zoom — big text stays
  // crisp). One-directional, so the word feels alive without the old bob.
  const kbC = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const idleY = interpolate(frame, [15, 420], [0, -width * 0.02], kbC);
  const idleRot = interpolate(frame, [15, 420], [0, -0.7], kbC);
  const idle = `translateY(${idleY}px) rotate(${idleRot}deg)`;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
      <div style={{
        fontFamily: CB.font, fontWeight: 900, fontSize: width * 0.13, lineHeight: 1.02,
        color: accent, textAlign: 'center', maxWidth: '90%', transform: `${idle} scale(${pop})`,
        textShadow: `0 ${5 * s}px 0 ${darken(accent, 0.6)}, 0 ${16 * s}px ${14 * s}px rgba(70,52,20,.18)`,
      }}>
        {fields.word}
      </div>
      {fields.sub ? (
        <div style={{fontFamily: CB.font, fontWeight: 700, fontSize: width * 0.042, color: CB.ink,
          textAlign: 'center', maxWidth: '80%', marginTop: width * 0.035, lineHeight: 1.2, transform: idle,
          opacity: interpolate(frame, [10, 22], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
          {fields.sub}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PaperFire — layered cut-paper flames that flicker + rise, with drifting embers.
// A visual storyteller for combustion/oxidation. Optional word/sub sit above the fire.
// Frame-driven flicker (deterministic). fields: {word, sub, accent}
// ---------------------------------------------------------------------------
// One flame silhouette (viewBox 100x140), stacked at decreasing scale (outer red ->
// inner white) so it reads as real fire, not fanned feathers.
const FLAME_PATH = 'M50 3 C 61 34 87 53 78 91 C 73 117 55 121 52 138 C 51 141 49 141 48 138 C 45 121 27 117 22 91 C 13 53 39 34 50 3 Z';
const FLAME_STACK = [
  {color: '#e8452f', scale: 1.0, sp: 0.20, ph: 0.0},
  {color: '#ff7a2f', scale: 0.72, sp: 0.27, ph: 1.1},
  {color: '#ffc23c', scale: 0.48, sp: 0.34, ph: 2.1},
  {color: '#ffe9a8', scale: 0.27, sp: 0.42, ph: 0.6},
];

export const PaperFire: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const s = width / 1080;
  const rid = 'r' + React.useId().replace(/:/g, '');
  const rough = `url(#${rid})`;
  const inn = spring({frame: frame - 3, fps, config: {damping: 15, stiffness: 110}});
  const accent = fields.accent || CB.coral;

  const zoneW = width * 0.4;
  const zoneH = width * 0.5; // outer flame bounding box
  const hashF = (i: number, salt: number) => {
    const x = Math.sin(i * 91.7 + salt * 47.3) * 43758.5453;
    return x - Math.floor(x);
  };

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
      <RoughDefs id={rid} scale={6} freq={0.03} />
      {fields.word ? (
        <div style={{textAlign: 'center', marginBottom: width * 0.055}}>
          <div style={{fontFamily: CB.font, fontWeight: 900, fontSize: width * 0.12, lineHeight: 1, color: accent,
            textShadow: `0 ${5 * s}px 0 ${darken(accent, 0.6)}, 0 ${16 * s}px ${14 * s}px rgba(70,52,20,.18)`}}>
            {fields.word}
          </div>
          {fields.sub ? (
            <div style={{fontFamily: CB.font, fontWeight: 700, fontSize: width * 0.04, color: CB.ink,
              marginTop: width * 0.02, maxWidth: '80%', marginLeft: 'auto', marginRight: 'auto',
              opacity: interpolate(frame, [10, 22], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
              {fields.sub}
            </div>
          ) : null}
        </div>
      ) : null}
      <div style={{position: 'relative', width: zoneW, height: zoneH}}>
        {/* embers drifting up out of the flames */}
        {Array.from({length: 6}, (_, i) => {
          const dur = 55 + hashF(i, 1) * 40;
          const t = ((((frame + i * 11) % dur) + dur) % dur) / dur;
          const ex = zoneW * (0.5 + (hashF(i, 2) - 0.5) * 0.5) + 10 * s * Math.sin(frame * 0.1 + i);
          const ey = -zoneH * 0.12 - zoneH * 0.55 * t; // rise above the flame tips
          const eop = Math.sin(t * Math.PI) * 0.7 * inn;
          const ed = width * (0.01 + hashF(i, 3) * 0.012);
          const ec = hashF(i, 4) > 0.5 ? CB.sunflower : CB.coral;
          return (
            <div key={`e${i}`} style={{position: 'absolute', left: ex - ed / 2, top: ey, width: ed, height: ed,
              borderRadius: '50%', background: ec, opacity: eop}} />
          );
        })}
        {/* nested flame silhouettes — same shape, smaller each layer, flickering from the base */}
        {FLAME_STACK.map((l, i) => {
          const flick = 0.9 + 0.12 * Math.sin(frame * l.sp + l.ph) + 0.05 * Math.sin(frame * l.sp * 2.3 + l.ph * 1.6);
          const sway = 3 * Math.sin(frame * l.sp * 0.8 + l.ph);
          const lw = zoneW * l.scale;
          const lh = zoneH * l.scale;
          return (
            <div key={`f${i}`} style={{
              position: 'absolute', left: zoneW / 2 - lw / 2, bottom: 0, width: lw, height: lh,
              transformOrigin: 'bottom center',
              transform: `rotate(${sway}deg) scaleY(${inn * flick}) scaleX(${0.94 + 0.06 * flick})`,
              filter: `${rough} drop-shadow(0 ${4 * s}px ${7 * s}px rgba(70,52,20,.18))`,
              opacity: inn,
            }}>
              <svg viewBox="0 0 100 140" preserveAspectRatio="none" style={{width: '100%', height: '100%', display: 'block'}}>
                <path d={FLAME_PATH} fill={l.color} />
              </svg>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PaperProp — a staged generated paper cut-out asset (fields.image, e.g. rusty nails)
// settling in, with an optional word/sub above. The reusable "show a paper prop" scene.
// fields: {image, word, sub, accent}
// ---------------------------------------------------------------------------
export const PaperProp: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const s = width / 1080;
  const accent = fields.accent || CB.coral;
  const inn = spring({frame: frame - 3, fps, config: {damping: 15, stiffness: 110}});
  const y = interpolate(inn, [0, 1], [width * 0.14, 0]);
  const rot = interpolate(inn, [0, 1], [3, 0]);
  // Slow one-way "Ken Burns" idle: a continuous float + drift + zoom + faint tilt over the
  // hold. One-directional (NOT an oscillation), so it reads as alive without the old bob/nausea.
  const kbEnd = 420; // ~14s ramp, then clamps and holds
  const kbClamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const kbZoom = interpolate(frame, [0, kbEnd], [1, 1.07], kbClamp);
  const kbY = interpolate(frame, [0, kbEnd], [0, -width * 0.03], kbClamp);
  const kbX = interpolate(frame, [0, kbEnd], [0, width * 0.012], kbClamp);
  const kbRot = interpolate(frame, [0, kbEnd], [0, 1.1], kbClamp);
  void s;

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
      {fields.word ? (
        <div style={{textAlign: 'center', marginBottom: width * 0.06}}>
          <div style={{fontFamily: CB.font, fontWeight: 900, fontSize: width * 0.12, lineHeight: 1, color: accent,
            textShadow: `0 4px 0 ${darken(accent, 0.6)}`}}>
            {fields.word}
          </div>
          {fields.sub ? (
            <div style={{fontFamily: CB.font, fontWeight: 700, fontSize: width * 0.04, color: CB.ink,
              marginTop: width * 0.02, maxWidth: '80%', marginLeft: 'auto', marginRight: 'auto',
              opacity: interpolate(frame, [10, 22], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
              {fields.sub}
            </div>
          ) : null}
        </div>
      ) : null}
      {fields.image ? (
        <Img src={staticFile(fields.image)} style={{
          width: '58%', maxHeight: '44%', objectFit: 'contain', opacity: inn,
          transform: `translate(${kbX}px, ${y + kbY}px) rotate(${rot + kbRot}deg) scale(${kbZoom})`,
          filter: 'drop-shadow(0 22px 30px rgba(70,52,20,.24))',
        }} />
      ) : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PaperThumb — the Cut & Bond YouTube thumbnail (16:9, 1280x720). Rendered from the
// SAME paper kit as the videos so every thumbnail is automatically on-brand, free, and
// reproducible (no per-video hand generation). Render with:
//   npx remotion still src/index.ts PaperThumb out.png --props='{"fields":{...}}'
// Shorts largely ignore custom thumbnails in-feed, but they DO show in search and on the
// channel page, so they are worth having.
// Layout: big punch word + sub on the left, hero prop image on the right, element tile
// in the corner. Text is sized to stay readable at small sizes.
// fields: {word, sub, symbol, number, accent, image}
// ---------------------------------------------------------------------------
export const PaperThumb: React.FC<{fields: any}> = ({fields}) => {
  const {width, height} = useVideoConfig();
  const s = width / 1280;
  const accent = fields.accent || CB.coral;
  const rid = 'r' + React.useId().replace(/:/g, '');
  const rough = `url(#${rid})`;
  const hasImg = Boolean(fields.image);

  return (
    <AbsoluteFill style={{background: CB.paper, overflow: 'hidden'}}>
      <RoughDefs id={rid} scale={9} freq={0.018} />
      <Grain />
      {/* soft paper light, mirrors PaperBackground so the thumb matches the video */}
      <div style={{position: 'absolute', inset: 0,
        background: `radial-gradient(60% 55% at 50% 38%, rgba(255,255,255,.5), rgba(255,255,255,0) 70%)`}} />

      <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
        padding: `${44 * s}px ${56 * s}px`, gap: 32 * s}}>
        {/* left column: tile, punch word, sub — all in normal flow so nothing can collide
            or overflow. Keep `word` under ~18 chars and `sub` under ~48 for best results. */}
        <div style={{flex: hasImg ? 1.2 : 1, minWidth: 0, display: 'flex', flexDirection: 'column',
          justifyContent: 'center', gap: 16 * s, maxHeight: '100%', overflow: 'hidden'}}>
          {fields.symbol ? (
            <div style={{position: 'relative', width: 88 * s, height: 88 * s, borderRadius: 14 * s,
              background: accent, flexShrink: 0,
              boxShadow: thick(accent, Math.round(5 * s), 8 * s, 14 * s, 0.3), filter: rough,
              display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
              <Grain />
              <div style={{fontFamily: CB.font, fontWeight: 900, fontSize: 44 * s, color: '#2a2622',
                lineHeight: 1, position: 'relative'}}>{fields.symbol}</div>
              {fields.number != null ? (
                <div style={{position: 'absolute', top: 6 * s, left: 10 * s, fontFamily: CB.font,
                  fontWeight: 800, fontSize: 17 * s, color: 'rgba(42,38,34,.75)'}}>{fields.number}</div>
              ) : null}
            </div>
          ) : null}
          <div style={{fontFamily: CB.font, fontWeight: 900, color: accent,
            // Size on TWO limits, because either can overflow. Total length sets the
            // headline tier, but a single long word cannot wrap, so it also has to fit
            // the column on its own — that is what clipped "ISOTOPES" on the first pass.
            fontSize: width * (() => {
              const w = String(fields.word || '');
              const byTotal = w.length > 18 ? 0.072 : w.length > 11 ? 0.094 : 0.125;
              const longest = w.split(/\s+/).reduce((m, t) => Math.max(m, t.length), 0) || 1;
              const colFrac = hasImg ? 0.52 : 0.86;   // share of frame width the text gets
              const byWord = colFrac / (longest * 0.72); // 0.72 ~= cap glyph width / font size
              return Math.min(byTotal, byWord);
            })(),
            lineHeight: 0.96, letterSpacing: -1 * s,
            textShadow: `0 ${5 * s}px 0 ${darken(accent, 0.6)}, 0 ${16 * s}px ${16 * s}px rgba(70,52,20,.20)`}}>
            {fields.word}
          </div>
          {fields.sub ? (
            <div style={{fontFamily: CB.font, fontWeight: 800, color: CB.ink,
              fontSize: width * 0.034, lineHeight: 1.18, maxWidth: '96%'}}>
              {fields.sub}
            </div>
          ) : null}
        </div>

        {/* right: hero prop */}
        {hasImg ? (
          <div style={{flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            height: '100%', minWidth: 0}}>
            <Img src={staticFile(fields.image)} style={{
              maxWidth: '100%', maxHeight: '86%', objectFit: 'contain',
              filter: 'drop-shadow(0 20px 26px rgba(70,52,20,.26))',
              transform: 'rotate(-2deg)',
            }} />
          </div>
        ) : null}
      </div>
      {void height}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PaperFootage — REAL reference footage taped into the paper world. A landscape video
// window sits on a torn-paper mat with a cast shadow and a slight tilt, so live-action
// reads as a clipping pinned to the cut-paper background rather than breaking the style.
// Use SPARINGLY: only when the script points at something the viewer is told they have
// seen (e.g. "you've seen the videos" for sodium in water), where a stylized paper prop
// cannot stand in for the real thing.
// fields: {video, startFrom (seconds into the clip), word, sub, accent}
// ---------------------------------------------------------------------------
export const PaperFootage: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const s = width / 1080;
  const accent = fields.accent || CB.coral;
  const inn = spring({frame: frame - 3, fps, config: {damping: 16, stiffness: 105}});
  const y = interpolate(inn, [0, 1], [width * 0.12, 0]);
  const rid = 'r' + React.useId().replace(/:/g, '');
  const rough = `url(#${rid})`;
  // Gentle one-way idle (matches the rest of the kit): slow float + faint tilt, no
  // oscillation, so it feels alive without the old bob.
  const kbC = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const idleY = interpolate(frame, [15, 420], [0, -width * 0.015], kbC);
  const idleRot = interpolate(frame, [15, 420], [-1.4, -0.4], kbC);
  const matPad = width * 0.028;

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
      <RoughDefs id={rid} scale={10} freq={0.016} />
      {fields.word ? (
        <div style={{textAlign: 'center', marginBottom: width * 0.055}}>
          <div style={{fontFamily: CB.font, fontWeight: 900, fontSize: width * 0.11, lineHeight: 1, color: accent,
            textShadow: `0 ${4 * s}px 0 ${darken(accent, 0.6)}`}}>
            {fields.word}
          </div>
          {fields.sub ? (
            <div style={{fontFamily: CB.font, fontWeight: 700, fontSize: width * 0.04, color: CB.ink,
              marginTop: width * 0.018, maxWidth: '80%', marginLeft: 'auto', marginRight: 'auto',
              opacity: interpolate(frame, [10, 22], [0, 1], kbC)}}>
              {fields.sub}
            </div>
          ) : null}
        </div>
      ) : null}
      {fields.video ? (
        <div style={{
          position: 'relative', width: '86%', padding: matPad, borderRadius: 18 * s,
          background: '#fbf6e8', filter: rough, opacity: inn,
          transform: `translateY(${y + idleY}px) rotate(${idleRot}deg)`,
          boxShadow: `0 ${5 * s}px 0 ${darken('#fbf6e8', 0.86)}, 0 ${26 * s}px ${44 * s}px rgba(70,52,20,.30)`,
        }}>
          <Grain />
          <div style={{position: 'relative', overflow: 'hidden', borderRadius: 8 * s, lineHeight: 0}}>
            <OffthreadVideo
              src={staticFile(fields.video)}
              startFrom={Math.round((fields.startFrom || 0) * fps)}
              muted
              style={{width: '100%', height: 'auto', display: 'block'}}
            />
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PaperCTA — the reusable like + subscribe outro (channel's ONLY CTA; nothing external).
// A paper thumbs-up (fields.image) presses + bursts, then a paper SUBSCRIBE button presses.
// No on-screen text — the burned-in caption ("Like and subscribe for more") carries it.
// fields: {image}
// ---------------------------------------------------------------------------
export const PaperCTA: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const s = width / 1080;
  const rid = 'r' + React.useId().replace(/:/g, '');
  const rough = `url(#${rid})`;
  const RED = '#e8452f';

  const thumbIn = spring({frame: frame - 4, fps, config: {damping: 12, stiffness: 130}});
  const press1 = interpolate(frame, [30, 36, 44], [1, 0.86, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const burst = interpolate(frame, [36, 62], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const burstOp = interpolate(frame, [36, 62], [0.55, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const subIn = spring({frame: frame - 44, fps, config: {damping: 13, stiffness: 120}});
  const press2 = interpolate(frame, [70, 76, 84], [1, 0.9, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const thumb = width * 0.34;

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
      <RoughDefs id={rid} scale={7} freq={0.02} />
      <div style={{position: 'relative', width: thumb, height: thumb, marginBottom: width * 0.07,
        display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{position: 'absolute', width: thumb, height: thumb, borderRadius: '50%',
          border: `${7 * s}px solid ${CB.coral}`, transform: `scale(${0.75 + burst * 1.15})`, opacity: burstOp}} />
        {fields.image ? (
          <Img src={staticFile(fields.image)} style={{width: '100%', height: '100%', objectFit: 'contain',
            transform: `scale(${thumbIn * press1})`, filter: 'drop-shadow(0 16px 22px rgba(70,52,20,.24))'}} />
        ) : null}
      </div>
      <div style={{position: 'relative', transform: `scale(${subIn * press2})`}}>
        <div style={{position: 'absolute', inset: 0, background: RED, borderRadius: width * 0.03, filter: rough,
          boxShadow: thick(RED, Math.round(5 * s), 9 * s, 16 * s, 0.28)}}><Grain /></div>
        <div style={{position: 'relative', color: '#fff5ef', fontFamily: CB.font, fontWeight: 900,
          fontSize: width * 0.058, letterSpacing: 2, padding: `${width * 0.028}px ${width * 0.075}px`}}>
          SUBSCRIBE
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// DiscoveryCard — a thick paper card settles in; a raised wax seal, cut-out year, name, note.
// fields: {year, name, note, accent}
// ---------------------------------------------------------------------------
export const DiscoveryCard: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const s = width / 1080;
  const accent = fields.accent || CB.sunflower;
  const inn = spring({frame: frame - 2, fps, config: {damping: 15, stiffness: 110}});
  const y = interpolate(inn, [0, 1], [width * 0.4, 0]);
  const rot = interpolate(inn, [0, 1], [4, 0]);
  // Gentle one-way idle after the card settles: slow float + faint tilt (no zoom — text stays
  // crisp/legible). One-directional, so it adds life without the old bob.
  const kbC = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const idleY = interpolate(frame, [18, 420], [0, -width * 0.018], kbC);
  const idleRot = interpolate(frame, [18, 420], [0, -0.8], kbC);
  const cardW = width * 0.78;
  const cardEdge = darken('#fbf6e8', 0.86);
  const rid = 'r' + React.useId().replace(/:/g, '');
  const rough = `url(#${rid})`;

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <RoughDefs id={rid} scale={14} freq={0.011} />
      <div style={{position: 'relative', width: cardW, transform: `translateY(${y + idleY}px) rotate(${rot + idleRot}deg)`, opacity: inn}}>
        {/* the rough, grained paper card back (edges hand-cut; text stays crisp on top) */}
        <div style={{
          position: 'absolute', inset: 0, background: '#fbf6e8', borderRadius: 28,
          boxShadow: `0 ${5 * s}px 0 ${cardEdge}, 0 ${9 * s}px 0 ${cardEdge}, 0 ${30 * s}px ${54 * s}px rgba(70,52,20,.30), inset 0 2px 0 rgba(255,255,255,.55)`,
          filter: rough,
        }}><Grain /></div>
        <div style={{position: 'relative', padding: `${width * 0.07}px ${width * 0.06}px`, textAlign: 'center'}}>
        {/* raised wax-seal motif */}
        <div style={{width: width * 0.11, height: width * 0.11, borderRadius: '50%', background: accent,
          boxShadow: thick(accent, Math.round(6 * s), 8 * s, 14 * s, 0.26), margin: '0 auto', marginBottom: width * 0.045,
          filter: rough, position: 'relative'}}><Grain round /></div>
        {fields.year ? (
          <div style={{fontFamily: CB.font, fontWeight: 900, fontSize: width * 0.19, lineHeight: 1,
            color: accent, letterSpacing: 1, textShadow: `0 ${3 * s}px 0 ${darken(accent, 0.62)}`}}>
            {fields.year}
          </div>
        ) : null}
        {fields.name ? (
          <div style={{fontFamily: CB.font, fontWeight: 900, fontSize: width * 0.062, color: CB.ink,
            marginTop: width * 0.025,
            opacity: interpolate(frame, [10, 20], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
            {fields.name}
          </div>
        ) : null}
        {fields.note ? (
          <div style={{fontFamily: CB.font, fontWeight: 600, fontSize: width * 0.036, color: CB.inkSoft,
            marginTop: width * 0.02, lineHeight: 1.25,
            opacity: interpolate(frame, [16, 28], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
            {fields.note}
          </div>
        ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PeriodicSlot — debossed paper table cells; the element's THICK bright tile flies from
// center into its cell, then pulses. A note line fades in below.
// fields: {symbol, number, row, col, accent, note}   (row 1-7, col 1-18)
// ---------------------------------------------------------------------------
const MAIN_TABLE: Record<number, number[]> = {
  1: [1, 18],
  2: [1, 2, 13, 14, 15, 16, 17, 18],
  3: [1, 2, 13, 14, 15, 16, 17, 18],
  4: Array.from({length: 18}, (_, i) => i + 1),
  5: Array.from({length: 18}, (_, i) => i + 1),
  6: Array.from({length: 18}, (_, i) => i + 1),
  7: Array.from({length: 18}, (_, i) => i + 1),
};

export const PeriodicSlot: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const s = width / 1080;
  const accent = fields.accent || CB.coral;
  const row = fields.row ?? 1;
  const col = fields.col ?? 1;

  const tableW = width * 0.9;
  const cell = tableW / 18;
  const gap = cell * 0.12;
  const tableH = cell * 7;

  const flight = spring({frame: frame - 8, fps, config: {damping: 16, stiffness: 90}});
  const startScale = 4.2;
  const scale = interpolate(flight, [0, 1], [startScale, 1]);
  const cx0 = tableW / 2 - cell / 2;
  const cy0 = tableH / 2 - cell / 2;
  const cx1 = (col - 1) * cell;
  const cy1 = (row - 1) * cell;
  const tx = interpolate(flight, [0, 1], [cx0, cx1]);
  const ty = interpolate(flight, [0, 1], [cy0, cy1]);
  const pulse = 1 + 0.12 * Math.max(0, Math.sin((frame - 26) * 0.5)) * interpolate(frame, [26, 46], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  // Gentle one-way idle push-in on the whole table once the tile has landed: slow float + tiny
  // zoom + faint tilt. One-directional, so the diagram feels alive without the old bob.
  const kbC = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const idleY = interpolate(frame, [50, 430], [0, -width * 0.015], kbC);
  const idleZoom = interpolate(frame, [50, 430], [1, 1.04], kbC);
  const idleRot = interpolate(frame, [50, 430], [0, 0.6], kbC);
  const rid = 'r' + React.useId().replace(/:/g, '');
  const rough = `url(#${rid})`;

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
      <RoughDefs id={rid} scale={8} freq={0.02} />
      <div style={{position: 'relative', width: tableW, height: tableH, transform: `translateY(${idleY}px) rotate(${idleRot}deg) scale(${idleZoom})`}}>
        {/* debossed table cells (slots cut into the base sheet) */}
        {Object.entries(MAIN_TABLE).flatMap(([r, cols]) =>
          cols.map((c) => {
            const isTarget = Number(r) === row && c === col;
            const cin = interpolate(frame, [0, 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
            return (
              <div key={`${r}-${c}`} style={{
                position: 'absolute', left: (c - 1) * cell + gap / 2, top: (Number(r) - 1) * cell + gap / 2,
                width: cell - gap, height: cell - gap, borderRadius: cell * 0.14,
                background: isTarget ? 'transparent' : CB.paperDeep,
                border: isTarget ? `2px dashed ${accent}` : 'none',
                boxShadow: isTarget ? 'none' : 'inset 0 2px 4px rgba(70,50,30,.14)',
                opacity: isTarget ? cin : cin * 0.7,
              }} />
            );
          })
        )}
        {/* the flying element tile — thick raised paper */}
        <div style={{
          position: 'absolute', left: tx, top: ty, width: cell, height: cell,
          transform: `scale(${scale * pulse})`, transformOrigin: 'center center', zIndex: 5,
        }}>
          {/* rough, grained colored tile back */}
          <div style={{
            position: 'absolute', inset: 0, borderRadius: cell * 0.14, background: accent,
            boxShadow: thick(accent, Math.round(4 * s), 9 * s, 16 * s, 0.3), filter: rough,
          }}><Grain /></div>
          {/* crisp symbol + number on top */}
          <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <div style={{fontFamily: CB.font, fontWeight: 900, fontSize: cell * 0.5, color: '#2a2622', lineHeight: 1}}>
              {fields.symbol}
            </div>
          </div>
          <div style={{position: 'absolute', top: cell * 0.08, left: cell * 0.12,
            fontFamily: CB.font, fontWeight: 800, fontSize: cell * 0.2, color: 'rgba(42,38,34,.75)'}}>
            {fields.number}
          </div>
        </div>
      </div>
      {fields.note ? (
        <div style={{fontFamily: CB.font, fontWeight: 800, fontSize: width * 0.05, color: CB.ink,
          textAlign: 'center', maxWidth: '82%', marginTop: width * 0.06,
          opacity: interpolate(frame, [30, 44], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
          {fields.note}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
