import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import {useWorld, Camera, CameraMove, PLANE, Plane, PaperTable, PaperCard, resolveCamera, usePlace, usePopup, flick, placeStyle} from './PaperWorld';

// Papercraft Motion — prototype scene components (papercraft-motion-spec.md §7).
// PaperSetHook: multi-plane cold open. PaperPopCard: keep-card popup on the table.
// PaperCounter: a stat as stacked paper chips that slap down and land on the cue.
// All beats come from the engine's cue resolution (deck "cues" -> fields.cueFrames).

// W now comes from the world context (per component, below) so each paper
// channel keeps its own ground; see PaperWorld.WorldProvider (2026-07-26).

const colorize = (text: string, accent: string[] = [], accentColor: string) => {
  if (!accent || !accent.length) return text;
  let parts: React.ReactNode[] = [text];
  accent.forEach((a) => {
    parts = parts.flatMap((p) => {
      if (typeof p !== 'string' || !a) return [p];
      const out: React.ReactNode[] = [];
      const segs = p.split(a);
      segs.forEach((s, i) => {
        if (s) out.push(s);
        if (i < segs.length - 1) out.push(<span key={a + i} style={{color: accentColor}}>{a}</span>);
      });
      return out;
    });
  });
  return parts;
};

// A placed element: object + its lagged shadow (the unseen hand, spec §3).
const Placed: React.FC<{at: number; style?: React.CSSProperties; shadowW?: string; children: React.ReactNode}> =
({at, style, shadowW = '86%', children}) => {
  const W = useWorld();
  const {height} = useVideoConfig();
  const p = usePlace(at);
  return (
    <div style={{position: 'relative', ...style}}>
      <div style={{position: 'absolute', left: '50%', bottom: -height * 0.012, width: shadowW,
                   height: height * 0.028, transform: 'translateX(-50%)', background: W.shadow,
                   borderRadius: '50%', filter: 'blur(6px)', opacity: p.shadowOpacity}} />
      <div style={p.object}>{children}</div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// PaperSetHook — the cold open as a miniature set (spec §7 "hook").
// fields: {set, props:[{image, at:[x,y], w, plane?}], kicker, headline, accent[],
//          beats:[string], cueFrames:{b1..bN, push}}
// Beat cards place on b1..bN; on `push` the camera steps in and the headline
// card places. Between beats: dead-still holds (stop-motion).
export const PaperSetHook: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const cf = fields.cueFrames || {};
  const beats: string[] = fields.beats || [];
  const beatAt = (i: number) => cf[`b${i + 1}`] ?? Math.round(((i + 1) / (beats.length + 2)) * durationInFrames * 0.5);
  const pushAt = cf.push ?? Math.round(durationInFrames * 0.55);

  const moves: CameraMove[] = [{at: pushAt, to: {zoom: 1.09, y: 0.46}}];
  const cam: Camera = resolveCamera(frame, useVideoConfig().fps, moves);
  const head = usePlace(pushAt + 4);

  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <Plane cam={cam} factor={PLANE.table}><PaperTable seed={fields.headline || 'hook'} /></Plane>
      {fields.set ? (
        <Plane cam={cam} factor={PLANE.set}>
          <Img src={staticFile(fields.set)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', transform: 'scale(1.07)'}} />
        </Plane>
      ) : null}
      <Plane cam={cam} factor={PLANE.stage}>
        {(fields.props || []).map((p: any, i: number) => (
          // zIndex 2: props are desk OBJECTS — they stand in front of the placed cards
          // (real depth: an object in front of a sign), never hidden behind them.
          <div key={i} style={{position: 'absolute', zIndex: 2, left: width * (p.at?.[0] ?? 0.5) - width * (p.w ?? 0.18) / 2,
                               top: height * (p.at?.[1] ?? 0.5), width: width * (p.w ?? 0.18)}}>
            <Placed at={p.cueFrame ?? 2}><Img src={staticFile(p.image)} style={{width: '100%', display: 'block'}} /></Placed>
          </div>
        ))}
        {/* beat cards — place WITH the spoken beats, in a row */}
        <div style={{position: 'absolute', left: 0, right: 0, top: height * 0.14, display: 'flex',
                     justifyContent: 'center', gap: width * 0.02}}>
          {beats.map((b, i) => (
            <Placed key={i} at={beatAt(i)}>
              <PaperCard style={{transform: `rotate(${(i % 2 ? 1.6 : -1.4)}deg) scale(${flick(frame, beatAt(i))})`}}>
                <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.034, color: W.ink, whiteSpace: 'nowrap'}}>{b}</div>
              </PaperCard>
            </Placed>
          ))}
        </div>
        {/* the promise headline — lands with the camera push */}
        <div style={{position: 'absolute', left: '50%', top: height * 0.4, transform: 'translateX(-50%)', maxWidth: width * 0.62}}>
          <div style={{opacity: frame >= pushAt + 4 ? 1 : 0}}>
            <div style={{position: 'absolute', left: '50%', bottom: -height * 0.016, width: '88%', height: height * 0.034,
                         transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%', filter: 'blur(8px)', opacity: head.shadowOpacity}} />
            <PaperCard style={{...head.object, padding: `${height * 0.03}px ${width * 0.03}px`, borderRadius: 20}}>
              {fields.kicker ? (
                <div style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.022, letterSpacing: 4,
                             textTransform: 'uppercase', color: W.accent, textAlign: 'center', marginBottom: height * 0.012}}>{fields.kicker}</div>
              ) : null}
              <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.062, lineHeight: 1.08,
                           color: W.ink, textAlign: 'center'}}>{colorize(fields.headline || '', fields.accent, W.accent)}</div>
            </PaperCard>
          </div>
        </div>
      </Plane>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PaperPopCard — a keep-card/figure pops up from the table (spec §7 "keep-card").
// fields: {image, label, sub, cueFrames:{pop?, in?}}
export const PaperPopCard: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const cf = fields.cueFrames || {};
  const popAt = cf.pop ?? 4;
  const inAt = cf.in ?? Math.round(durationInFrames * 0.45);
  const pop = usePopup(popAt);
  const cam = resolveCamera(frame, fps, [{at: inAt, to: {zoom: 1.1, y: 0.47}}]);
  // 16:9 caption band lives in the lower ~18%: keep the card (and its on-card sub-line)
  // fully above it (the same lower-third lesson as the Shorts thirds layout).
  const cardH = height * 0.64;
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <Plane cam={cam} factor={PLANE.table}><PaperTable seed={fields.label || 'card'} tightenAt={inAt} /></Plane>
      <Plane cam={cam} factor={PLANE.stage}>
        <div style={{position: 'absolute', left: '50%', top: '45%', transform: 'translate(-50%, -50%)'}}>
          {/* contact shadow grows as the card rises */}
          <div style={{position: 'absolute', left: '50%', bottom: -height * 0.02, width: '80%', height: height * 0.05,
                       transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%', filter: 'blur(10px)', ...pop.shadow}} />
          <div style={{...pop.object, height: cardH}}>
            {fields.image ? (
              <Img src={staticFile(fields.image)} style={{height: '100%', display: 'block'}} />
            ) : null}
            <div style={{position: 'absolute', left: 0, right: 0, top: '64%', textAlign: 'center'}}>
              <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: cardH * 0.082, letterSpacing: 1, color: W.ink,
                           opacity: interpolate(frame, [popAt + 8, popAt + 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
                           transform: `scale(${flick(frame, inAt)})`}}>{fields.label}</div>
              {fields.sub ? (
                <div style={{fontFamily: BRAND.font, fontWeight: 600, fontSize: cardH * 0.034, color: W.accent, marginTop: cardH * 0.02, padding: '0 12.5%',
                             opacity: interpolate(frame, [popAt + 14, popAt + 24], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>{fields.sub}</div>
              ) : null}
            </div>
          </div>
        </div>
      </Plane>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PaperCounter — a stat as a stack of paper chips (spec §7 "stat"). Chips slap
// down in sequence and the LAST chip lands exactly on the cue; the number tag
// counts with the chips and flicks on the landing; the key light snaps tight.
// fields: {value, suffix?, label, kicker, cueFrames:{land}}
export const PaperCounter: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const value = fields.value ?? 0;
  const cf = fields.cueFrames || {};
  const land = cf.land ?? Math.round(durationInFrames * 0.55);
  const nChips = Math.min(8, Math.max(3, Math.round(value / 10)));
  const chipAt = (i: number) => land - (nChips - 1 - i) * 6;
  const landed = Array.from({length: nChips}, (_, i) => frame >= chipAt(i)).filter(Boolean).length;
  const shown = Math.round(value * (landed / nChips));
  const chipW = width * 0.2, chipH = height * 0.062;

  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <PaperTable seed={fields.label || 'stat'} tightenAt={land} />
      {fields.kicker ? (
        <div style={{position: 'absolute', top: height * 0.14, left: 0, right: 0, textAlign: 'center', fontFamily: BRAND.font,
                     fontWeight: 800, fontSize: height * 0.026, letterSpacing: 5, textTransform: 'uppercase', color: W.accentSoft}}>
          {fields.kicker}
        </div>
      ) : null}
      {/* the chip stack (grows upward from the table line) */}
      <div style={{position: 'absolute', left: width * 0.33 - chipW / 2, bottom: height * 0.24, width: chipW}}>
        {Array.from({length: nChips}, (_, i) => {
          const p = placeStyle(frame, fps, height, chipAt(i));
          // seeded per-chip jitter (x + tilt) so the stack reads chip-by-chip, hand-placed
          const j = ((i * 2654435761) % 97) / 97 - 0.5;
          return (
            <div key={i} style={{position: 'absolute', bottom: i * chipH * 0.86, left: j * chipW * 0.12,
                                 width: chipW, height: chipH,
                                 background: W.paper, borderRadius: 10, borderBottom: `6px solid ${W.paperShade}`,
                                 boxShadow: `0 ${height * 0.008}px ${height * 0.02}px ${W.shadow}`, ...p,
                                 transform: `${p.transform} rotate(${(i % 2 ? 2.4 : -2.2) + j * 1.5}deg)`}} />
          );
        })}
        <div style={{position: 'absolute', bottom: -height * 0.018, left: '50%', width: chipW * 1.2, height: height * 0.03,
                     transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%', filter: 'blur(8px)',
                     opacity: interpolate(frame, [chipAt(0) + 3, chipAt(0) + 8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}} />
      </div>
      {/* the number tag */}
      <div style={{position: 'absolute', left: width * 0.52, top: '50%', transform: `translateY(-50%) scale(${flick(frame, land)})`}}>
        <PaperCard style={{padding: `${height * 0.025}px ${width * 0.03}px`, borderRadius: 22,
                           boxShadow: `0 ${height * 0.02}px ${height * 0.045}px ${W.shadow}`}}>
          <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.15, lineHeight: 1, color: W.ink, fontVariantNumeric: 'tabular-nums'}}>
            {shown}{fields.suffix || ''}
          </div>
        </PaperCard>
        {fields.label ? (
          <div style={{marginTop: height * 0.024, opacity: interpolate(frame, [land + 4, land + 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
            <PaperCard style={{display: 'inline-block', padding: `${height * 0.01}px ${width * 0.016}px`, borderRadius: 10, transform: 'rotate(-1.2deg)'}}>
              <div style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.03, color: W.accent}}>{fields.label}</div>
            </PaperCard>
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
