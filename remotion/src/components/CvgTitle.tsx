import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import {useWorld} from './PaperWorld';

// SHOW TITLE PANEL for the six personal-show worlds (2026-09-03, operator request).
//
// Why: the six Cvg-family shows (daily founder tip, Monday MedTech, Founder Tip Tuesday,
// Who Signs the Check, The Teardown, Failure Modes Friday) carried NO opening bumper —
// `_NO_STING` in remotion_engine.py kept every wordmark sting off them so no other
// brand could leak in — and so an episode opened cold on its hook slide, identifiable
// only by the small kicker. This panel is the show's own name card: its locked paper
// mark settles onto the show's paper ground, the brand kicker and the show title rise
// beneath, and a cut-paper accent strip draws in under the title. Nothing here is a
// wordmark for another brand; the world tokens (brands/papercraft.ts) supply every
// colour, so the panel matches the episode that follows it by construction.
//
// Fields (all set by the engine's per-theme table, never authored in a deck):
//   mark     — 'papercraft-<show>/mark_<show>.png' (the locked show mark)
//   kicker   — small tracked label above the title (the owning brand)
//   title    — the show name; '\n' forces a line break, otherwise one line, width-fit
//   sub      — small line under the strip ("with Dave Saunders")
//   accent   — optional colour override for kicker/strip (defaults from the world)
//   fg       — optional type colour override (defaults: paper on dark grounds, ink on light)
//
// Deterministic (frame-driven springs/interpolate only) and self-composed for BOTH
// aspects — it is in Video.tsx's FULL_BLEED set, so it owns the whole frame.

const lum = (hex: string): number => {
  const h = hex.replace('#', '');
  const n = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const r = parseInt(n.slice(0, 2), 16) / 255, g = parseInt(n.slice(2, 4), 16) / 255, b = parseInt(n.slice(4, 6), 16) / 255;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

const ease = (frame: number, at: number, dur = 16) =>
  interpolate(frame, [at, at + dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

export const CvgTitle: React.FC<{fields?: any; durationInFrames?: number}> = ({fields}) => {
  const f = fields || {};
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const W = useWorld();
  const portrait = height > width;
  const M = Math.min(width, height);

  // Ground = the show's sheet (its locked bg hue). Light grounds (goldenrod) take ink
  // type and the deep accent; dark grounds take paper type and the soft accent.
  const ground = W.sheet;
  const light = lum(ground) > 0.5;
  const fg = f.fg || (light ? W.ink : W.paper);
  const accent = f.accent || (light ? W.accent : W.accentSoft);
  const shadow = W.shadow;

  const bg = ease(frame, 0, 8);
  // the mark places like a piece of paper: drops in, settles, tiny overshoot rotation
  const place = spring({frame: frame - 3, fps, config: {damping: 13, stiffness: 120}});
  const markScale = interpolate(place, [0, 1], [0.82, 1]);
  const markY = interpolate(place, [0, 1], [-height * 0.05, 0]);
  const markRot = interpolate(place, [0, 1], [-5, 0]);

  const kk = ease(frame, 20, 14);
  const tt = ease(frame, 26, 18);
  const strip = spring({frame: frame - 34, fps, config: {damping: 15, stiffness: 140}});
  const ss = ease(frame, 40, 14);

  const markH = portrait ? width * 0.42 : height * 0.36;
  const lines: string[] = String(f.title || '').split('\n').filter((l: string) => l.length);
  const longest = lines.reduce((a, l) => Math.max(a, l.length), 1);
  // One line per row, width-fit (900-weight glyphs run ~0.52em), capped by a
  // height-based ceiling so short names don't balloon.
  const fit = (width * 0.86) / Math.max(1, longest * 0.52);
  const tSize = Math.min(portrait ? width * 0.11 : height * 0.11, fit);
  const kSize = M * (portrait ? 0.028 : 0.03);
  const sSize = M * (portrait ? 0.032 : 0.034);
  const stripW = Math.min(width * 0.28, tSize * 2.4);

  return (
    <AbsoluteFill style={{background: ground, alignItems: 'center', justifyContent: 'center', overflow: 'hidden'}}>
      {/* soft paper light + vignette, the same treatment the other paper stings use */}
      <AbsoluteFill style={{
        background: light
          ? 'radial-gradient(120% 120% at 50% 40%, rgba(255,255,255,.22), rgba(0,0,0,.08))'
          : 'radial-gradient(120% 120% at 50% 40%, rgba(255,255,255,.06), rgba(0,0,0,.24))',
        opacity: bg,
      }} />

      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        transform: `translateY(${portrait ? -height * 0.03 : 0}px)`,
      }}>
        {f.mark ? (
          <div style={{
            height: markH, position: 'relative', opacity: bg,
            transform: `translateY(${markY}px) scale(${markScale}) rotate(${markRot}deg)`,
            marginBottom: M * 0.06,
          }}>
            <Img src={staticFile(f.mark)} style={{
              height: '100%', width: 'auto', display: 'block',
              filter: `drop-shadow(0 ${M * 0.012}px ${M * 0.022}px ${shadow})`,
            }} />
          </div>
        ) : null}

        {f.kicker ? (
          <div style={{
            fontFamily: BRAND.font, fontWeight: 800, fontSize: kSize, letterSpacing: kSize * 0.22,
            textTransform: 'uppercase', color: accent, textAlign: 'center',
            opacity: kk, transform: `translateY(${(1 - kk) * 14}px)`,
            marginBottom: M * 0.018,
          }}>{f.kicker}</div>
        ) : null}

        <div style={{
          fontFamily: BRAND.font, fontWeight: 900, fontSize: tSize, lineHeight: 1.02,
          color: fg, letterSpacing: -tSize * 0.015, textAlign: 'center', whiteSpace: 'nowrap',
          opacity: tt, transform: `translateY(${(1 - tt) * 26}px)`,
        }}>
          {lines.map((l, i) => <div key={i}>{l}</div>)}
        </div>

        {/* cut-paper accent strip draws in under the title */}
        <div style={{
          width: stripW * strip, height: Math.max(6, M * 0.011), background: accent,
          marginTop: M * 0.03, borderRadius: 2,
          boxShadow: `0 ${M * 0.004}px ${M * 0.01}px ${shadow}`,
          opacity: strip,
        }} />

        {f.sub ? (
          <div style={{
            fontFamily: BRAND.font, fontWeight: 700, fontSize: sSize, color: fg,
            opacity: 0.88 * ss, transform: `translateY(${(1 - ss) * 12}px)`,
            marginTop: M * 0.03, letterSpacing: sSize * 0.02, textAlign: 'center',
          }}>{f.sub}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
