import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import {useWorld, CameraMove, PLANE, Plane, PaperTable, PaperCard, PaperProps, usePaperLayout, resolveCamera, usePlace, popupStyle, placeStyle, flick, usePaperPush} from './PaperWorld';
import {PaperSheet} from './PaperNote';

// Papercraft Motion — data & structure family (papercraft-motion-spec.md §7).
// Charts are physical objects: stairs pop up step by step and a paper pawn
// climbs them; compares are two trays; flows are cards along a paper path.

// W now comes from the world context (per component, below) so each paper
// channel keeps its own ground; see PaperWorld.WorldProvider (2026-07-26).

// `height` is the type scale (the MIN dimension since the portrait pass — frame height in
// landscape, so nothing moves there); `top` is a real vertical position and stays in frame
// units, pulled up a little in portrait where the frame is much taller than it is wide.
const Kicker: React.FC<{text?: string; height: number}> = ({text, height}) => {
  const W = useWorld();
  const {portrait} = usePaperLayout();
  const {height: frameH} = useVideoConfig();
  return text ? (
    <div style={{position: 'absolute', top: frameH * (portrait ? 0.08 : 0.12), left: 0, right: 0, textAlign: 'center',
                 fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.026, letterSpacing: 5,
                 textTransform: 'uppercase', color: W.kicker ?? W.accentSoft}}>{text}</div>
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
  const {fps, width, height: frameH} = useVideoConfig();
  // Type/step metrics track the min dimension; the staircase's own floor and height are
  // frame-vertical, so they get portrait numbers that keep it clear of the caption band.
  const {portrait, M: height} = usePaperLayout();
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

  const areaW = width * (portrait ? 0.84 : 0.6), stepW = areaW / n;
  // Portrait: floor at 0.66 (clear of the caption band) and a shorter rise, so the whole
  // staircase plus its end tag fits between the kicker and the captions.
  const baseY = frameH * (portrait ? 0.66 : 0.78), maxH = frameH * (portrait ? 0.3 : 0.4);
  const topY = (i: number) => baseY - (frameH * (portrait ? 0.07 : 0.09) + norm(pts[i]) * maxH);
  const x = (i: number) => width * (portrait ? 0.08 : 0.2) + i * stepW;

  // the pawn climbs: piecewise ease to each newly-popped step top (tiny hop arc)
  let px = x(0) + stepW / 2, py = topY(0);
  for (let i = 1; i < n; i++) {
    const t = interpolate(frame, [stepAt(i) + 4, stepAt(i) + 13], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    px += (x(i) + stepW / 2 - px) * t;
    py += (topY(i) - py) * t - Math.sin(Math.PI * t) * height * 0.045;
  }
  const pawnW = width * (portrait ? 0.07 : 0.045);
  const pawnIn = usePlace(stepAt(0) + 2);

  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <PaperTable seed={fields.endLabel || 'stairs'} tightenAt={lastAt} mood={fields.kind === 'bad' ? 'hard' : 'soft'} />
      <PaperProps items={fields.props} />
      <Kicker text={fields.kicker} height={height} />
      {pts.map((_, i) => {
        const st = popupStyle(frame, fps, stepAt(i));
        return (
          // real paper columns (phase 3). Each step gets its own substrate id so a staircase
          // is not the same sheet of paper repeated across every riser.
          <div key={i} style={{position: 'absolute', left: x(i), top: topY(i), width: stepW * 0.94,
                               height: baseY - topY(i), borderRadius: 8,
                               boxShadow: `0 ${height * 0.014}px ${height * 0.03}px ${W.shadow}`, ...st}}>
            <PaperSheet id={`stair:${i}`} radius={8} edge={9} tint={W.paper} />
          </div>
        );
      })}
      {/* the climber (zIndex above the end tag so it never hides beneath it) */}
      <div style={{position: 'absolute', zIndex: 2, left: px - pawnW / 2, top: py - pawnW * 1.9, width: pawnW, ...pawnIn.object}}>
        <Img src={staticFile('papercraft/elements/el_pawn.png')} style={{width: '100%', display: 'block',
             filter: `drop-shadow(0 ${height * 0.01}px ${height * 0.018}px ${W.shadow})`}} />
      </div>
      {fields.endLabel ? (
        <div style={{position: 'absolute', left: Math.min(x(n - 1) + stepW * 0.1, width * (portrait ? 0.5 : 0.78)), top: topY(n - 1) - height * 0.26,
                     ...placeStyle(frame, fps, height, lastAt + 8)}}>
          <PaperCard id={`stairlbl:${fields.end_label ?? ''}`} family="card_tag" style={{display: 'inline-block', padding: `${height * 0.012}px ${width * 0.016}px`, borderRadius: 10, transform: 'rotate(1.4deg)'}}>
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
export const PaperCompare: React.FC<{fields: any; durationInFrames?: number}> = ({fields, durationInFrames = 300}) => {
  const push = usePaperPush(durationInFrames);
  const W = useWorld();
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  // Portrait stacks the two trays top/bottom — the same collision CvgCompare fixed: two
  // columns in a 1080-wide frame are too narrow to hold a tray's own words.
  const {portrait, M: height, reserve} = usePaperLayout();
  const cf = fields.cueFrames || {};
  const lAt = cf.l ?? 8, rAt = cf.r ?? 20;
  const tray = (d: any, at: number) => {
    const bad = d?.kind === 'bad';
    const st = popupStyle(frame, fps, at);
    return (
      <div style={{flex: portrait ? '0 0 auto' : 1, position: 'relative',
                   width: portrait ? width * 0.78 : undefined, maxWidth: portrait ? undefined : width * 0.36}}>
        <div style={{position: 'absolute', left: '50%', bottom: -height * 0.018, width: '86%', height: height * 0.036,
                     transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%',
                     filter: `blur(${bad ? 12 : 8}px)`, opacity: frame >= at ? (bad ? 1 : 0.75) : 0}} />
        {/* the tray body is real paper (phase 2); the flat W.paper fill and the fake
            borderBottom "thickness" are what made it read as a UI panel next to the
            generated art. The header band still paints over the paper, which is correct —
            it is ink on the card, not a second material. */}
        <div style={{...st, position: 'relative', borderRadius: 18, overflow: 'hidden',
                     boxShadow: `0 ${height * (bad ? 0.026 : 0.016)}px ${height * (bad ? 0.05 : 0.034)}px ${W.shadow}`}}>
          <PaperSheet id={`tray:${d?.title ?? ''}`} radius={18} tint={W.paper} />
          <div style={{position: 'relative', background: bad ? W.sheet : W.accentSoft, padding: `${height * 0.014}px 0`, textAlign: 'center',
                       fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.026, letterSpacing: 3,
                       textTransform: 'uppercase', color: bad ? W.paper : W.ink}}>{d?.title}</div>
          <div style={{position: 'relative', padding: `${height * 0.03}px ${width * 0.018}px`, fontFamily: BRAND.font, fontWeight: 900,
                       fontSize: height * 0.042, lineHeight: 1.15, color: W.ink, textAlign: 'center'}}>{d?.value}</div>
        </div>
      </div>
    );
  };
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <PaperTable seed={(fields.left?.title || '') + 'vs'} />
      <PaperProps items={fields.props} />
      <Kicker text={fields.kicker} height={height} />
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', paddingBottom: reserve, ...push}}>
        <div style={{display: 'flex', flexDirection: portrait ? 'column' : 'row',
                     gap: portrait ? height * 0.05 : width * 0.05, width: '100%',
                     justifyContent: 'center', alignItems: portrait ? 'center' : 'stretch'}}>
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
  const push = usePaperPush(durationInFrames);
  const W = useWorld();
  const frame = useCurrentFrame();
  const {fps, width, height: frameH} = useVideoConfig();
  // Portrait runs the flow DOWN the frame instead of across it (CvgSteps' fix): a row of
  // cards in a 1080-wide frame gives each step a column narrower than its own label.
  const {portrait, M: height, reserve} = usePaperLayout();
  const steps: string[] = (fields.steps || []).map((s: any) => (typeof s === 'string' ? s : s?.title || ''));
  const n = Math.max(1, steps.length);
  const itemTimes: (number | null)[] = fields.itemTimes || [];
  const per = durationInFrames / (n + 1);
  const at = (i: number) => (itemTimes[i] != null ? (itemTimes[i] as number) : Math.round((i + 0.5) * per));

  const areaW = width * 0.86, cardW = portrait ? width * 0.72 : Math.min(width * 0.24, areaW / n - width * 0.02);
  const cx = (i: number) => (portrait ? width * 0.5 : width * 0.07 + (areaW / n) * (i + 0.5));
  // vertical lane for the portrait stack: below the kicker, above the caption reserve
  const areaTop = frameH * 0.17, areaH = frameH - areaTop - reserve;
  const cy = (i: number) => areaTop + (areaH / n) * (i + 0.5);

  // The lateral step is DECORATION, not necessity: cardW is solved so the whole row
  // fits on screen with an equal margin each side, so every card is already visible and
  // the camera is only nodding toward the one being spoken. It must therefore never
  // travel far enough to push the outermost card off the frame — and on the stage plane
  // (factor 1.0) a pan of d costs exactly d*width of frame, on top of what the zoom and
  // usePaperPush have already eaten from the margin.
  //
  // #55 shipped a fixed 0.3 coefficient. On a four-card row that spends 0.097 of a 0.048
  // budget, and BOTH four-card steps slides rendered with card 1 clipped mid-word at the
  // left edge ("hich problems we"). It went unnoticed because the clip only appears once
  // the LAST card lands — the mid-scene frame a spot check catches looks perfect.
  // Budget it from the geometry instead, so it stays safe for any n.
  // Budget against the spring's PEAK, not where it settles. CAM is {damping 13,
  // stiffness 190}, a damping ratio of ~0.47, so it is underdamped and sails about 19%
  // past its target before coming back. A budget spent to the settle point is overspent
  // by a fifth at the moment the eye is most likely to be watching the card move.
  const CAM_ZOOM = 1.05, PUSH_MAX = 1.025;   // usePaperPush's default, compounding inside the plane
  const OVERSHOOT = 1.19;                    // exp(-pi*z/sqrt(1-z^2)) for z = 13/(2*sqrt(190))
  const zoomPeak = 1 + (CAM_ZOOM - 1) * OVERSHOOT;
  const margin = (cx(0) - cardW / 2) / width;                       // equal on both sides by construction
  // Spend 60% of what is free, not all of it: a card whose edge lands exactly on the
  // frame edge is not clipped, but it reads as though it is about to be, which is the
  // same design smell in a nicer suit.
  const SPEND = 0.6;
  const budget = Math.max(0, 0.5 - (0.5 - margin) * PUSH_MAX * zoomPeak) * SPEND;
  const spread = Math.max(...steps.map((_, i) => Math.abs(cx(i) / width - 0.5)), 1e-6);
  const panK = Math.min(0.3, budget / (spread * OVERSHOOT));
  const moves: CameraMove[] = n > 3 && !portrait
    ? steps.slice(1).map((_, i) => ({at: at(i + 1), to: {x: 0.5 + (cx(i + 1) / width - 0.5) * panK, zoom: CAM_ZOOM}}))
    : [];
  const cam = resolveCamera(frame, fps, moves);

  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <Plane cam={cam} factor={PLANE.table}><PaperTable seed={steps[0] || 'steps'} /></Plane>
      {/* props sit OUTSIDE the camera planes: they stand at the frame's corners, so they
          must not ride the lateral camera step that tracks the active flow card */}
      <PaperProps items={fields.props} />
      <Plane cam={cam} factor={PLANE.stage}>
        <AbsoluteFill style={{...push}}>
        <Kicker text={fields.kicker} height={height} />
        {steps.map((s, i) => {
          const st = popupStyle(frame, fps, at(i));
          const stripT = i > 0 ? interpolate(frame, [at(i) - 5, at(i) + 2], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
          return (
            <React.Fragment key={i}>
              {i > 0 ? (
                // the connector between stages is a laid paper strip, not a drawn bar —
                // horizontal between columns at 16:9, vertical between rows in portrait
                <div style={portrait
                  // sits in the GAP between two stacked cards, centred on the midpoint —
                  // a strip spanning card-centre to card-centre paints across their labels
                  ? {position: 'absolute', left: cx(i) - height * 0.007,
                     top: (cy(i - 1) + cy(i)) / 2 - height * 0.025, width: height * 0.014,
                     height: height * 0.05, borderRadius: 6,
                     transform: `scaleY(${stripT})`, transformOrigin: 'center top',
                     boxShadow: `0 ${height * 0.006}px ${height * 0.014}px ${W.shadow}`}
                  // 16:9 spans card-centre to card-centre, so it MUST sit behind the cards
                  // (zIndex 0 against the card's 1). The portrait branch above solved the
                  // same problem by sitting in the gap; this branch kept the full span and
                  // painted straight across the labels — on a two-line card the strip ran
                  // through the second line ("and for them", "solving them"), and four of
                  // module 1's five cards lost half a line to it. Behind the cards the strip
                  // still shows in every gap, so nothing about the look changes except that
                  // the type is legible.
                  : {position: 'absolute', left: cx(i - 1), top: frameH * 0.545, width: cx(i) - cx(i - 1),
                     height: height * 0.014, borderRadius: 6, zIndex: 0,
                     transform: `scaleX(${stripT})`, transformOrigin: 'left center',
                     boxShadow: `0 ${height * 0.006}px ${height * 0.014}px ${W.shadow}`}}>
                  <PaperSheet id={`strip:${i}`} family="card_tag" radius={6} edge={5} tint={W.sheetAlt} />
                </div>
              ) : null}
              <div style={{position: 'absolute', left: cx(i) - cardW / 2, zIndex: 1,
                           top: portrait ? cy(i) - height * 0.06 : frameH * 0.42, width: cardW}}>
                <div style={{position: 'absolute', left: '50%', bottom: -height * 0.014, width: '82%', height: height * 0.028,
                             transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%', filter: 'blur(7px)',
                             opacity: frame >= at(i) ? 1 : 0}} />
                <div style={{...st, position: 'relative', borderRadius: 16,
                             padding: `${height * 0.022}px ${width * 0.012}px`, textAlign: 'center'}}>
                  <PaperSheet id={`flowcard:${i}:${s}`} radius={16} tint={W.paper} />
                  <div style={{position: 'relative', fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.05, color: W.accent, lineHeight: 1}}>{i + 1}</div>
                  <div style={{position: 'relative', fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.028, color: W.ink,
                               lineHeight: 1.18, marginTop: height * 0.01}}>{s}</div>
                </div>
              </div>
            </React.Fragment>
          );
        })}
        </AbsoluteFill>
      </Plane>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// PaperList — items place one by one AS they're said: lilac number chip + a
// cream strip per item. fields: {kicker, title, items[], itemTimes?}
export const PaperList: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const push = usePaperPush(durationInFrames);
  const W = useWorld();
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const {M: height, reserve} = usePaperLayout();
  const items: string[] = fields.items || [];
  const itemTimes: (number | null)[] = fields.itemTimes || [];
  const per = durationInFrames / Math.max(1, items.length + 1);
  const at = (i: number) => (itemTimes[i] != null ? (itemTimes[i] as number) : Math.round(i * per));
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <PaperTable seed={fields.title || fields.kicker || 'list'} />
      <PaperProps items={fields.props} />
      <Kicker text={fields.kicker} height={height} />
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', paddingBottom: reserve, ...push}}>
        <div>
          {fields.title ? (
            <div style={{...placeStyle(frame, fps, height, 4), marginBottom: height * 0.024}}>
              <PaperCard id={`ctrlbl:${fields.label ?? ''}`} family="card_tag" style={{display: 'inline-block', padding: `${height * 0.012}px ${width * 0.02}px`, borderRadius: 12}}>
                <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.036, color: W.ink}}>{fields.title}</div>
              </PaperCard>
            </div>
          ) : null}
          {items.map((it, i) => (
            <div key={i} style={{display: 'flex', alignItems: 'center', gap: width * 0.014,
                                 marginBottom: height * 0.02, ...placeStyle(frame, fps, height, at(i))}}>
              <div style={{position: 'relative', width: height * 0.062, height: height * 0.062, borderRadius: 12,
                           display: 'flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 auto',
                           boxShadow: `0 ${height * 0.008}px ${height * 0.016}px ${W.shadow}`,
                           fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.034, color: W.ink}}>
                <PaperSheet id={`num:${i}`} family="card_tag" radius={12} edge={7} tint={W.accentSoft} />
                <span style={{position: 'relative'}}>{i + 1}</span>
              </div>
              <PaperCard id={`step:${i}`} style={{padding: `${height * 0.012}px ${width * 0.018}px`, borderRadius: 12,
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
export const PaperBookCTA: React.FC<{fields: any; durationInFrames?: number}> = ({fields, durationInFrames = 300}) => {
  const push = usePaperPush(durationInFrames);
  const W = useWorld();
  const frame = useCurrentFrame();
  const {width} = useVideoConfig();
  // Portrait stands the book ABOVE the offer card rather than beside it — side by side,
  // neither the cover nor the headline gets a usable width in a 1080-wide frame.
  const {portrait, M: height, reserve} = usePaperLayout();
  const book = usePlace(6);
  const card = usePlace(16);
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <PaperTable seed={fields.headline || 'cta'} />
      <PaperProps items={fields.props} />
      <AbsoluteFill style={{flexDirection: portrait ? 'column' : 'row', alignItems: 'center', justifyContent: 'center',
                            ...push,
                            gap: portrait ? height * 0.04 : width * 0.05,
                            padding: portrait ? `0 6% ${reserve}px` : '0 6%'}}>
        {fields.image ? (
          <div style={{position: 'relative', width: width * (portrait ? 0.42 : 0.24)}}>
            <div style={{position: 'absolute', left: '50%', bottom: -height * 0.022, width: '92%', height: height * 0.04,
                         transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%', filter: 'blur(11px)', opacity: book.shadowOpacity}} />
            <div style={book.object}>
              <Img src={staticFile(fields.image)} style={{width: '100%', display: 'block', borderRadius: 10,
                   boxShadow: `0 ${height * 0.02}px ${height * 0.05}px ${W.shadow}`, transform: 'rotate(-2deg)'}} />
            </div>
          </div>
        ) : null}
        <div style={{position: 'relative', maxWidth: width * (portrait ? 0.86 : 0.44)}}>
          <div style={{position: 'absolute', left: '50%', bottom: -height * 0.016, width: '88%', height: height * 0.03,
                       transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%', filter: 'blur(9px)', opacity: card.shadowOpacity}} />
          <PaperCard id={`ctacard:${fields.headline ?? ''}`} style={{...card.object, padding: `${height * 0.03}px ${width * 0.028}px`, borderRadius: 20}}>
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
