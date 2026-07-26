import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import {useWorld, CameraMove, PLANE, Plane, PaperTable, PaperCard, resolveCamera, usePlace, popupStyle, placeStyle, flick} from './PaperWorld';

// Papercraft Motion — data & structure family (papercraft-motion-spec.md §7).
// Charts are physical objects: stairs pop up step by step and a paper pawn
// climbs them; compares are two trays; flows are cards along a paper path.

// W now comes from the world context (per component, below) so each paper
// channel keeps its own ground; see PaperWorld.WorldProvider (2026-07-26).

const Kicker: React.FC<{text?: string; height: number}> = ({text, height}) => {
  const W = useWorld();
  return text ? (
    <div style={{position: 'absolute', top: height * 0.12, left: 0, right: 0, textAlign: 'center',
                 fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.026, letterSpacing: 5,
                 textTransform: 'uppercase', color: W.accentSoft}}>{text}</div>
  ) : null;
};

// ---------------------------------------------------------------------------
// PaperStairs — trend/chart as a physical staircase. Steps popup in sequence
// (anchored so the LAST step lands on cueFrames.land when given); the pawn
// element climbs them; the end label places on a tag at the top step.
// fields: {kicker, points:[num], endLabel, kind, cueFrames:{land?}}
export const PaperStairs: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const raw: number[] = (fields.points || []).map((p: any) => (typeof p === 'number' ? p : p?.value ?? 0));
  const pts = raw.slice(0, 8);
  const n = Math.max(2, pts.length);
  const lo = Math.min(...pts), hi = Math.max(...pts);
  const norm = (v: number) => (hi === lo ? 0.5 : (v - lo) / (hi - lo));
  const cf = fields.cueFrames || {};
  const lastAt = cf.land ?? Math.round(durationInFrames * 0.5);
  // spread the build across the story (start ~12% in), still landing the last
  // step exactly on the cue — a late cue must not compress the whole staircase
  // into one slam at the end
  const GAP = Math.max(7, Math.round((lastAt - durationInFrames * 0.12) / Math.max(1, n - 1)));
  const stepAt = (i: number) => lastAt - (n - 1 - i) * GAP;

  const areaW = width * 0.6, stepW = areaW / n;
  const baseY = height * 0.78, maxH = height * 0.4;
  const topY = (i: number) => baseY - (height * 0.09 + norm(pts[i]) * maxH);
  const x = (i: number) => width * 0.2 + i * stepW;

  // the pawn climbs: piecewise ease to each newly-popped step top (tiny hop arc)
  let px = x(0) + stepW / 2, py = topY(0);
  for (let i = 1; i < n; i++) {
    const t = interpolate(frame, [stepAt(i) + 4, stepAt(i) + 13], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    px += (x(i) + stepW / 2 - px) * t;
    py += (topY(i) - py) * t - Math.sin(Math.PI * t) * height * 0.045;
  }
  const pawnW = width * 0.045;
  const pawnIn = usePlace(stepAt(0) + 2);

  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <PaperTable seed={fields.endLabel || 'stairs'} tightenAt={lastAt} mood={fields.kind === 'bad' ? 'hard' : 'soft'} />
      <Kicker text={fields.kicker} height={height} />
      {pts.map((_, i) => {
        const st = popupStyle(frame, fps, stepAt(i));
        return (
          <div key={i} style={{position: 'absolute', left: x(i), top: topY(i), width: stepW * 0.94,
                               height: baseY - topY(i), background: W.paper, borderRadius: 8,
                               borderBottom: `6px solid ${W.paperShade}`,
                               boxShadow: `0 ${height * 0.014}px ${height * 0.03}px ${W.shadow}`, ...st}} />
        );
      })}
      {/* the climber (zIndex above the end tag so it never hides beneath it) */}
      <div style={{position: 'absolute', zIndex: 2, left: px - pawnW / 2, top: py - pawnW * 1.9, width: pawnW, ...pawnIn.object}}>
        <Img src={staticFile('papercraft/elements/el_pawn.png')} style={{width: '100%', display: 'block',
             filter: `drop-shadow(0 ${height * 0.01}px ${height * 0.018}px ${W.shadow})`}} />
      </div>
      {fields.endLabel ? (
        <div style={{position: 'absolute', left: Math.min(x(n - 1) + stepW * 0.1, width * 0.78), top: topY(n - 1) - height * 0.26,
                     ...placeStyle(frame, fps, height, lastAt + 8)}}>
          <PaperCard style={{display: 'inline-block', padding: `${height * 0.012}px ${width * 0.016}px`, borderRadius: 10, transform: 'rotate(1.4deg)'}}>
            <div style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.03, color: W.accent, whiteSpace: 'nowrap'}}>{fields.endLabel}</div>
          </PaperCard>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PaperCompare — two paper trays popup left then right; the "bad" side sits in
// harder shadow with a plum header strip (the palette carries the judgment).
// fields: {left:{title,value,kind}, right:{title,value,kind}, cueFrames:{l?,r?}}
export const PaperCompare: React.FC<{fields: any}> = ({fields}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const cf = fields.cueFrames || {};
  const lAt = cf.l ?? 8, rAt = cf.r ?? 20;
  const tray = (d: any, at: number) => {
    const bad = d?.kind === 'bad';
    const st = popupStyle(frame, fps, at);
    return (
      <div style={{flex: 1, position: 'relative', maxWidth: width * 0.36}}>
        <div style={{position: 'absolute', left: '50%', bottom: -height * 0.018, width: '86%', height: height * 0.036,
                     transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%',
                     filter: `blur(${bad ? 12 : 8}px)`, opacity: frame >= at ? (bad ? 1 : 0.75) : 0}} />
        <div style={{...st, background: W.paper, borderRadius: 18, borderBottom: `7px solid ${W.paperShade}`,
                     overflow: 'hidden', boxShadow: `0 ${height * (bad ? 0.026 : 0.016)}px ${height * (bad ? 0.05 : 0.034)}px ${W.shadow}`}}>
          <div style={{background: bad ? W.sheet : W.accentSoft, padding: `${height * 0.014}px 0`, textAlign: 'center',
                       fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.026, letterSpacing: 3,
                       textTransform: 'uppercase', color: bad ? W.paper : W.ink}}>{d?.title}</div>
          <div style={{padding: `${height * 0.03}px ${width * 0.018}px`, fontFamily: BRAND.font, fontWeight: 900,
                       fontSize: height * 0.042, lineHeight: 1.15, color: W.ink, textAlign: 'center'}}>{d?.value}</div>
        </div>
      </div>
    );
  };
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <PaperTable seed={(fields.left?.title || '') + 'vs'} />
      <Kicker text={fields.kicker} height={height} />
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{display: 'flex', gap: width * 0.05, width: '100%', justifyContent: 'center', alignItems: 'stretch'}}>
          {tray(fields.left, lAt)}
          {tray(fields.right, rAt)}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PaperSteps — a flow as popup cards along a violet paper path; each card pops
// AS its step is spoken (itemTimes), the path strip extends to meet it, and the
// camera steps laterally with the active card.
// fields: {kicker, steps:[string|{title}], itemTimes?}
export const PaperSteps: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const steps: string[] = (fields.steps || []).map((s: any) => (typeof s === 'string' ? s : s?.title || ''));
  const n = Math.max(1, steps.length);
  const itemTimes: (number | null)[] = fields.itemTimes || [];
  const per = durationInFrames / (n + 1);
  const at = (i: number) => (itemTimes[i] != null ? (itemTimes[i] as number) : Math.round((i + 0.5) * per));

  const areaW = width * 0.86, cardW = Math.min(width * 0.24, areaW / n - width * 0.02);
  const cx = (i: number) => width * 0.07 + (areaW / n) * (i + 0.5);

  const moves: CameraMove[] = n > 3
    ? steps.slice(1).map((_, i) => ({at: at(i + 1), to: {x: 0.5 + (cx(i + 1) / width - 0.5) * 0.3, zoom: 1.05}}))
    : [];
  const cam = resolveCamera(frame, fps, moves);

  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <Plane cam={cam} factor={PLANE.table}><PaperTable seed={steps[0] || 'steps'} /></Plane>
      <Plane cam={cam} factor={PLANE.stage}>
        <Kicker text={fields.kicker} height={height} />
        {steps.map((s, i) => {
          const st = popupStyle(frame, fps, at(i));
          const stripT = i > 0 ? interpolate(frame, [at(i) - 5, at(i) + 2], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
          return (
            <React.Fragment key={i}>
              {i > 0 ? (
                <div style={{position: 'absolute', left: cx(i - 1), top: height * 0.545, width: cx(i) - cx(i - 1),
                             height: height * 0.014, background: W.sheetAlt, borderRadius: 6,
                             transform: `scaleX(${stripT})`, transformOrigin: 'left center',
                             boxShadow: `0 ${height * 0.006}px ${height * 0.014}px ${W.shadow}`}} />
              ) : null}
              <div style={{position: 'absolute', left: cx(i) - cardW / 2, top: height * 0.42, width: cardW}}>
                <div style={{position: 'absolute', left: '50%', bottom: -height * 0.014, width: '82%', height: height * 0.028,
                             transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%', filter: 'blur(7px)',
                             opacity: frame >= at(i) ? 1 : 0}} />
                <div style={{...st, background: W.paper, borderRadius: 16, borderBottom: `6px solid ${W.paperShade}`,
                             padding: `${height * 0.022}px ${width * 0.012}px`, textAlign: 'center'}}>
                  <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.05, color: W.accent, lineHeight: 1}}>{i + 1}</div>
                  <div style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.028, color: W.ink,
                               lineHeight: 1.18, marginTop: height * 0.01}}>{s}</div>
                </div>
              </div>
            </React.Fragment>
          );
        })}
      </Plane>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PaperList — items place one by one AS they're said: lilac number chip + a
// cream strip per item. fields: {kicker, title, items[], itemTimes?}
export const PaperList: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const items: string[] = fields.items || [];
  const itemTimes: (number | null)[] = fields.itemTimes || [];
  const per = durationInFrames / Math.max(1, items.length + 1);
  const at = (i: number) => (itemTimes[i] != null ? (itemTimes[i] as number) : Math.round(i * per));
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <PaperTable seed={fields.title || fields.kicker || 'list'} />
      <Kicker text={fields.kicker} height={height} />
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div>
          {fields.title ? (
            <div style={{...placeStyle(frame, fps, height, 4), marginBottom: height * 0.024}}>
              <PaperCard style={{display: 'inline-block', padding: `${height * 0.012}px ${width * 0.02}px`, borderRadius: 12}}>
                <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.036, color: W.ink}}>{fields.title}</div>
              </PaperCard>
            </div>
          ) : null}
          {items.map((it, i) => (
            <div key={i} style={{display: 'flex', alignItems: 'center', gap: width * 0.014,
                                 marginBottom: height * 0.02, ...placeStyle(frame, fps, height, at(i))}}>
              <div style={{width: height * 0.062, height: height * 0.062, borderRadius: 12, background: W.accentSoft,
                           display: 'flex', alignItems: 'center', justifyContent: 'center',
                           borderBottom: `4px solid ${W.sheetAlt}`, boxShadow: `0 ${height * 0.008}px ${height * 0.016}px ${W.shadow}`,
                           fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.034, color: W.ink}}>{i + 1}</div>
              <PaperCard style={{padding: `${height * 0.012}px ${width * 0.018}px`, borderRadius: 12,
                                 boxShadow: `0 ${height * 0.01}px ${height * 0.02}px ${W.shadow}`,
                                 transform: `rotate(${i % 2 ? 0.5 : -0.5}deg)`}}>
                <div style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.038, color: W.ink}}>{it}</div>
              </PaperCard>
            </div>
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PaperBookCTA — the close: the real book cover stands on the table (places with a
// settle + shadow), the offer card places beside it, warm soft light.
// fields: {kicker, headline, accent, subkicker, image (book cover, staged)}
export const PaperBookCTA: React.FC<{fields: any}> = ({fields}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const book = usePlace(6);
  const card = usePlace(16);
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <PaperTable seed={fields.headline || 'cta'} />
      <AbsoluteFill style={{flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: width * 0.05, padding: '0 6%'}}>
        {fields.image ? (
          <div style={{position: 'relative', width: width * 0.24}}>
            <div style={{position: 'absolute', left: '50%', bottom: -height * 0.022, width: '92%', height: height * 0.04,
                         transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%', filter: 'blur(11px)', opacity: book.shadowOpacity}} />
            <div style={book.object}>
              <Img src={staticFile(fields.image)} style={{width: '100%', display: 'block', borderRadius: 10,
                   boxShadow: `0 ${height * 0.02}px ${height * 0.05}px ${W.shadow}`, transform: 'rotate(-2deg)'}} />
            </div>
          </div>
        ) : null}
        <div style={{position: 'relative', maxWidth: width * 0.44}}>
          <div style={{position: 'absolute', left: '50%', bottom: -height * 0.016, width: '88%', height: height * 0.03,
                       transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%', filter: 'blur(9px)', opacity: card.shadowOpacity}} />
          <PaperCard style={{...card.object, padding: `${height * 0.03}px ${width * 0.028}px`, borderRadius: 20}}>
            {fields.kicker ? (
              <div style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.022, letterSpacing: 4,
                           textTransform: 'uppercase', color: W.accent, marginBottom: height * 0.014}}>{fields.kicker}</div>
            ) : null}
            <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.058, lineHeight: 1.08, color: W.ink}}>
              {fields.headline}
            </div>
            {fields.subkicker ? (
              <div style={{fontFamily: BRAND.font, fontWeight: 700, fontSize: height * 0.028, color: W.accent,
                           marginTop: height * 0.02, lineHeight: 1.3}}>{fields.subkicker}</div>
            ) : null}
          </PaperCard>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
