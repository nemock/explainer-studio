import React from 'react';
import {AbsoluteFill, Easing, Img, Video, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import rough from 'roughjs';
import {BRAND} from '../brand';
import {useInk, PAPER_SHADOW} from '../ink';
import {PaperSheet, Tape} from './PaperNote';

// --- figure MARKS: hand-drawn circle/arrow/underline/box in the figure's OWN image space,
// rendered INSIDE the moving/zooming container so the callout TRAVELS with the Ken Burns
// (unlike the frame-space AnnotateOverlay, which sits over the whole scene and drifts off a
// panning subject). Coords are 0-1 of the image; the SVG viewBox (16:9) maps them linearly to
// the contained image box. cueFrame is resolved from a spoken phrase by the Python spec-builder.
const MARK_COLOR: Record<string, string> = {green: BRAND.green, red: BRAND.red, white: BRAND.white};
const markSeed = (s: string) => {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return ((h >>> 0) % 2147483645) + 1;
};
const FigMark: React.FC<{m: any; i: number}> = ({m, i}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const VW = 1000, VH = 562, sw = VH * 0.013;
  const ink = useInk();
  // 'green' means "the world's accent" — indigo in the BRG world, studio green on navy;
  // 'white' means "the body ink", which is a deep ink on the cream paper worlds.
  const color = m.color === 'red' ? (ink.danger ?? (ink.paper ? '#c2352b' : BRAND.red))
              : m.color === 'white' ? ink.body : ink.accent;
  const {paths, length, tip} = React.useMemo(() => {
    const gen = rough.generator();
    const opts = {seed: markSeed(`${m.kind}:${i}:${m.at}:${m.from}:${m.to}`), roughness: 2.2,
                  bowing: 1.6, stroke: color, strokeWidth: sw};
    const px = (p?: [number, number]): [number, number] => [(p?.[0] ?? 0.5) * VW, (p?.[1] ?? 0.5) * VH];
    let d: any = null, len = 0, tp: any = null;
    if (m.kind === 'arrow' || m.kind === 'strike') {
      const [x1, y1] = px(m.from); const [x2, y2] = px(m.to);
      d = gen.line(x1, y1, x2, y2, opts); len = Math.hypot(x2 - x1, y2 - y1) * 2.3;
      if (m.kind === 'arrow') tp = {x: x2, y: y2, angle: Math.atan2(y2 - y1, x2 - x1)};
    } else if (m.kind === 'box') {
      const [cx, cy] = px(m.at); const w = (m.w ?? 0.28) * VW, h = (m.h ?? 0.3) * VH;
      d = gen.rectangle(cx - w / 2, cy - h / 2, w, h, opts); len = 2 * (w + h) * 2.3;
    } else if (m.kind === 'underline') {
      const [cx, cy] = px(m.at); const w = (m.w ?? 0.3) * VW;
      d = gen.line(cx - w / 2, cy, cx + w / 2, cy, {...opts, bowing: 2, disableMultiStroke: true}); len = w * 1.2;
    } else { // circle (default)
      const [cx, cy] = px(m.at); const w = (m.w ?? 0.28) * VW, h = (m.h ?? 0.34) * VH;
      d = gen.ellipse(cx, cy, w, h, opts); len = Math.PI * (w + h) * 1.2;
    }
    return {paths: d ? gen.toPaths(d) : [], length: Math.max(60, len), tip: tp};
  }, [m, i, color, sw]);
  const drawFrames = Math.round((m.kind === 'arrow' || m.kind === 'strike' || m.kind === 'underline' ? 0.55 : 0.8) * fps);
  const t = interpolate(frame, [m.cueFrame ?? 0, (m.cueFrame ?? 0) + drawFrames], [0, 1],
                        {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (frame < (m.cueFrame ?? 0)) return null;
  const tipO = interpolate(t, [0.8, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const hl = Math.max(18, VH * 0.05);
  return (
    <>
      {paths.map((p, j) => (
        <path key={j} d={p.d} fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round"
              strokeLinejoin="round" strokeDasharray={length} strokeDashoffset={length * (1 - t)}
              vectorEffect="non-scaling-stroke"
              style={ink.paper ? undefined : {filter: `drop-shadow(0 0 10px ${color}66)`}} />
      ))}
      {tip ? (
        <g opacity={tipO} stroke={color} strokeWidth={sw} strokeLinecap="round" fill="none" vectorEffect="non-scaling-stroke">
          <line x1={tip.x} y1={tip.y} x2={tip.x - hl * Math.cos(tip.angle - 0.46)} y2={tip.y - hl * Math.sin(tip.angle - 0.46)} />
          <line x1={tip.x} y1={tip.y} x2={tip.x - hl * Math.cos(tip.angle + 0.46)} y2={tip.y - hl * Math.sin(tip.angle + 0.46)} />
        </g>
      ) : null}
    </>
  );
};
// Type rendered ON the paper page, in IMAGE space, inside the same moving container as
// FigureMarks — so it rides the Ken Burns and stays on the sheet.
//
// WHY THIS EXISTS. Generated paper art carries NO text by construction (the STYLE.md recipe
// ends "no text, no words, no logos"). So a document slide whose whole point is a sentence
// had nowhere to put the sentence: the title rendered ABOVE the mount, and the page itself
// stayed blank. #57 shipped a figure with a green highlighter stroke and an authored
// `underline` mark on top of it — two green lines, neither underlining anything, over an
// empty page. The words belong on the page; the stroke underneath them is the underline.
//
// `size` and the wrap width are fractions, and the whole block sits inside the image's
// transform, so it scales with the shot instead of drifting off it.
const FigurePageType: React.FC<{pageText?: any; height: number; ink: any}> = ({pageText, height, ink}) => {
  if (!pageText || !pageText.text) return null;
  const [x, y] = pageText.at || [0.5, 0.42];
  return (
    <div style={{
      position: 'absolute', left: `${x * 100}%`, top: `${y * 100}%`,
      width: `${(pageText.w ?? 0.5) * 100}%`, transform: 'translate(-50%, -50%)',
      fontFamily: BRAND.font, fontWeight: 700,
      fontSize: height * (pageText.size ?? 0.032), lineHeight: 1.28,
      color: ink.body, textAlign: pageText.align || 'center',
      textWrap: 'balance', pointerEvents: 'none',
    }}>
      {figColorize(pageText.text, pageText.accent, pageText.accent2, ink.accent,
                   (ink.danger ?? (ink.paper ? '#c2352b' : BRAND.red)))}
    </div>
  );
};

const FigureMarks: React.FC<{marks?: any[]}> = ({marks}) => {
  if (!marks || !marks.length) return null;
  return (
    <svg viewBox="0 0 1000 562" preserveAspectRatio="none"
         style={{position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible', pointerEvents: 'none'}}>
      {marks.map((m, i) => <FigMark key={i} m={m} i={i} />)}
    </svg>
  );
};

// wrap accent/accent2 substrings of `text` in green/red (figure's phase-1 title line,
// footage's headline overlay). Regex-substring based (not token-split) so it also handles
// phrases that include punctuation the token splitter in ./colorize would choke on.
// `accentColor` is the world's ONE accent (studio green on navy, indigo in the BRG world) —
// pass ink.accent from the caller so figures never hard-code a green that is off-brand here.
const figColorize = (text: string, accents: string[] = [], accents2: string[] = [],
                     accentColor: string = BRAND.green,
                     dangerColor: string = BRAND.red) => {
  if (!text) return null;
  const all = [...(accents || []), ...(accents2 || [])];
  if (!all.length) return text;
  const esc = all.map((a) => a.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const re = new RegExp(`(${esc.join('|')})`, 'ig');
  return text.split(re).map((p, i) => {
    if ((accents || []).some((a) => a.toLowerCase() === p.toLowerCase())) {
      return <span key={i} style={{color: accentColor}}>{p}</span>;
    }
    if ((accents2 || []).some((a) => a.toLowerCase() === p.toLowerCase())) {
      return <span key={i} style={{color: dangerColor}}>{p}</span>;
    }
    return <React.Fragment key={i}>{p}</React.Fragment>;
  });
};

// figure -> a framed document/artifact excerpt with Ken Burns + an optional marker-wipe
// highlight (motion-playbook §2D). fields: {image, kicker, caption, highlight?, title?, accent?, imageFromFrac?,
//   moves?: [{to: {x, y, scale}, cueFrame}], assemble?: {pieces: [{clip: [x,y,w,h], cueFrame}]}}
// imageFromFrac: when set (0-1), the figure opens as a TEXT card (the `title` line) and the
// framed image is revealed only at that fraction of the scene — so a long single-segment
// figure can hold a lesson, then reveal the artifact when the narration names it (#13 Magic Link).
// Figure 2.0 (motion-playbook §2D, 2026-07-04):
//   moves — a guided TOUR of the artifact: the framed image pans/zooms to each region as
//     the narration reaches its cue (x/y = the region's center in 0-1 card space; scale =
//     zoom level). Replaces the ambient Ken Burns when present.
//   assemble — the image builds in cued pieces (clip = [x,y,w,h] region in 0-1 space),
//     each wiping in on its cue; the "picture assembling" treatment.
export const Figure: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const ink = useInk();
  const revealFrac = fields.imageFromFrac ?? 0;
  const revealAt = revealFrac * durationInFrames;
  const phased = revealFrac > 0 && !!fields.title;
  // A `title` authored WITHOUT imageFromFrac used to be silently discarded (titleOpacity
  // stayed 0 forever), so headline copy the deck author wrote simply never appeared. That
  // quietly cost real editorial lines across several videos before it surfaced — on #52
  // seven of nine image slides had a dropped title, including the video's central claim
  // (operator-caught 2026-07-28). A title is now ALWAYS rendered:
  //   title + imageFromFrac -> phased  (title holds alone, then the image reveals under it)
  //   title alone           -> persistent header above the image, for the whole scene
  const persistentTitle = !!fields.title && !phased;

  const kIntro = spring({frame, fps, config: {damping: 18, stiffness: 90}});
  const imgIntro = spring({frame: frame - revealAt, fps, config: {damping: 18, stiffness: 90}});
  const scale = interpolate(imgIntro, [0, 1], [0.92, 1]);  // card intro; Ken Burns lives on the inner image
  const imgOpacity = phased ? interpolate(frame, [revealAt, revealAt + 0.4 * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
  const titleOpacity = phased ? interpolate(frame, [6, 16, revealAt - 8, revealAt + 2], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
  const hl = fields.highlight;
  const marks = fields.marks || [];  // image-space callouts that ride the Ken Burns (see FigureMarks)
  // highlight timing: a narration cueFrame (resolved from highlight.cue by the Python
  // spec-builder) beats the proportional atFrac fallback
  const at = hl?.cueFrame != null ? hl.cueFrame : (hl?.atFrac ?? 0.35) * durationInFrames;
  const hlW = hl ? interpolate(frame, [at, at + 0.45 * fps * 3], [0, hl.widthTo ?? 40], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;

  // guided tour: ease the INNER image between cued {x, y, scale} keys (0-1 card space)
  const MOVE = Math.round(0.9 * fps);
  let tx = 0.5, ty = 0.5, tz = 1;
  for (const mv of (fields.moves || [])) {
    const t = interpolate(frame, [mv.cueFrame ?? 0, (mv.cueFrame ?? 0) + MOVE], [0, 1],
                          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
                           easing: Easing.bezier(0.16, 1, 0.3, 1)});
    tx = tx + ((mv.to?.x ?? 0.5) - tx) * t;
    ty = ty + ((mv.to?.y ?? 0.5) - ty) * t;
    tz = tz + ((mv.to?.scale ?? 1) - tz) * t;
  }
  const tour = fields.moves?.length
    ? {transform: `scale(${tz}) translate(${(0.5 - tx) * 100}%, ${(0.5 - ty) * 100}%)`}
    : undefined;

  const pieces: any[] = fields.assemble?.pieces || [];
  // Automatic Ken Burns for plain figures (no cued tour / no assemble): a continuous
  // pan + zoom so the scene is never static during speech. The PAN moves every pixel each
  // frame, which is what clears ffmpeg freezedetect (qa.py dead-air) — a slow zoom alone
  // does not. Direction is seeded off the image name so figures vary but stay deterministic.
  const kenSeed = (fields.image || '').split('').reduce((a: number, c: string) => a + c.charCodeAt(0), 0);
  const autoKen = (!fields.moves?.length && !pieces.length)
    ? {transform: `scale(${interpolate(frame, [0, durationInFrames], [1.04, 1.22])}) `
        + `translate(${interpolate(frame, [0, durationInFrames], [-4, 4]) * (kenSeed % 2 ? 1 : -1)}%, `
        + `${interpolate(frame, [0, durationInFrames], [-3, 3]) * ((kenSeed >> 1) % 2 ? 1 : -1)}%)`}
    : undefined;
  // _stage_images() nulls the field when it cannot resolve the asset, and its contract is
  // "missing -> component shows headline/caption only". Figure used to call staticFile()
  // unconditionally, so one unresolvable path threw and killed the whole render ~2 min in
  // (#50, 2026-07-31: a deck referencing `imagegen/x.png` instead of `assets/imagegen/x.png`).
  // Degrade to the caption card instead — a missing image must never cost a 20-minute render.
  const img = fields.image ? (
    <Img src={staticFile(fields.image)} style={{maxWidth: '100%', maxHeight: Math.round(height * 0.56), objectFit: 'contain', display: 'block', borderRadius: 8}} />
  ) : null;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 6%'}}>
      {/* Kicker marginBottom 0.025 -> 0.07 (2026-08-11): at the larger size the kicker reached
          the mount's top-left tape, which draws over it and ate the first characters ("SERIES"
          rendered as "ERIES"). The tape overhangs the corner by roughly height*0.06, so the
          kicker has to clear the TAPE, not just the mount edge. */}
      {fields.kicker ? (
        <div style={{fontFamily: BRAND.font, color: ink.accent, fontWeight: 800, fontSize: height * 0.030, letterSpacing: 4, textTransform: 'uppercase', opacity: kIntro, marginBottom: height * 0.07}}>
          {fields.kicker}
        </div>
      ) : null}
      {phased ? (
        <div style={{position: 'absolute', left: 0, right: 0, textAlign: 'center', padding: '0 12%', fontFamily: BRAND.font, color: ink.body, fontWeight: 900, fontSize: height * 0.062, lineHeight: 1.15, opacity: titleOpacity, textShadow: ink.paper ? PAPER_SHADOW : '0 3px 18px rgba(0,0,0,.6)'}}>
          {figColorize(fields.title, fields.accent, fields.accent2, ink.accent, (ink.danger ?? (ink.paper ? '#c2352b' : BRAND.red)))}
        </div>
      ) : null}
      {persistentTitle ? (
        // in-flow header: kicker -> title -> image card -> caption. Smaller than the phased
        // title (which owns the whole frame on its own) so the image still leads.
        // marginBottom 0.022 -> 0.075 (2026-08-14): SAME BUG AS THE KICKER ABOVE, one line
        // down. The mount's top-left tape overhangs by ~height*0.06, and a persistent title
        // is centred with only 4% side padding, so any title long enough to reach the
        // mount's left edge had its first characters drawn over by the tape — #57 shipped
        // "It traveled" as "t raveled", "The situation" as "he situation", "People left" as
        // "eople left". The kicker got this clearance in 2026-08-11; persistentTitle landed
        // 2026-07-28 and was never re-checked against the tape. Clear the TAPE, not the mount.
        <div style={{textAlign: 'center', padding: '0 4%', fontFamily: BRAND.font, color: ink.body, fontWeight: 900, fontSize: height * 0.042, lineHeight: 1.16, opacity: kIntro, marginBottom: height * 0.075, textShadow: ink.paper ? PAPER_SHADOW : '0 3px 18px rgba(0,0,0,.6)'}}>
          {figColorize(fields.title, fields.accent, fields.accent2, ink.accent, (ink.danger ?? (ink.paper ? '#c2352b' : BRAND.red)))}
        </div>
      ) : null}
      {/* The artifact frame: a bright white card + deep shadow reads as a lit print on the
          navy stage, but on the cream paper worlds it becomes a glaring white border with a
          gloomy halo. There the frame is REAL paper stock (phase 3) — a mount the figure is
          laid onto. This is the loudest synthetic surface in the system, because a flat white
          box wrapped around generated paper art puts both materials side by side in one
          object. Non-paper themes keep the white print card. */}
      {img ? (
      // Outer wrapper exists ONLY so the tape can hang outside the mount. The mount itself
      // sets overflow:hidden whenever the figure pans (tour / Ken Burns), and tape is
      // positioned at negative offsets, so tape placed inside would be clipped away on
      // exactly the figures that most need it — nearly all of them.
      <div style={{position: 'relative', maxWidth: '76%', transform: `scale(${scale})`, opacity: imgOpacity}}>
      <div style={{position: 'relative', background: ink.paper ? undefined : '#fff', borderRadius: 26, padding: height * 0.022, boxShadow: ink.paper ? PAPER_SHADOW : '0 40px 120px rgba(0,0,0,.55)', overflow: (tour || autoKen) ? 'hidden' : undefined}}>
        {ink.paper ? <PaperSheet id={`mount:${fields.image ?? fields.title ?? ''}`} family="card_index" radius={26} tint="#fffcf5" /> : null}
        {pieces.length ? (
          // assembling: base image hidden; each piece is a clipped copy wiping in on cue
          <div style={{position: 'relative', ...(tour || {})}}>
            <div style={{opacity: 0}}>{img}</div>
            {pieces.map((p, i) => {
              const [px, py, pw, ph] = p.clip || [0, 0, 1, 1];
              const e = spring({frame: frame - (p.cueFrame ?? 0), fps, config: {damping: 16, stiffness: 110}});
              if (frame < (p.cueFrame ?? 0)) return null;
              return (
                <div key={i} style={{position: 'absolute', inset: 0, opacity: e,
                                     transform: `translateY(${interpolate(e, [0, 1], [14, 0])}px)`,
                                     clipPath: `inset(${py * 100}% ${(1 - px - pw) * 100}% ${(1 - py - ph) * 100}% ${px * 100}%)`}}>
                  {img}
                </div>
              );
            })}
            <FigureMarks marks={marks} />
          </div>
        ) : tour ? (
          <div style={{position: 'relative', ...tour}}>{img}<FigurePageType pageText={fields.pageText} height={height} ink={ink} /><FigureMarks marks={marks} /></div>
        ) : autoKen ? (
          <div style={{position: 'relative', ...autoKen}}>{img}<FigurePageType pageText={fields.pageText} height={height} ink={ink} /><FigureMarks marks={marks} /></div>
        ) : (
          <div style={{position: 'relative'}}>{img}<FigurePageType pageText={fields.pageText} height={height} ink={ink} /><FigureMarks marks={marks} /></div>
        )}
        {hl ? (
          <div style={{position: 'absolute', top: `${hl.top ?? 30}%`, left: `${hl.left ?? 6}%`, height: `${hl.height ?? 12}%`, width: `${hlW}%`, background: ink.accentWash, borderRadius: 8}} />
        ) : null}
      </div>
        {/* two torn strips fix the mount to the table. Without them a figure floats, which is
            exactly what the old white card did. Opposite corners only — tape across the middle
            would cover the thing the viewer is meant to be reading. */}
        {ink.paper ? (
          <>
            <Tape id={`tape-a:${fields.image ?? ''}`} width={height * 0.16} at="tl" />
            <Tape id={`tape-b:${fields.image ?? ''}`} width={height * 0.16} at="br" />
          </>
        ) : null}
      </div>
      ) : null}
      {/* Caption (2026-08-11, operator): was 24px with a 27px gap — small, and the mount's
          bottom-right tape strip ran into it. Now 30px, centred, capped at 62% measure so a
          long caption breaks to two lines instead of one thin full-width run, and pushed down
          to 0.055 so it clears the tape rather than sharing space with it. */}
      {/* When the slide ALSO carries an on-screen citation, the caption has to clear it.
          SourceLine is bottom-anchored at height*0.05 and grows upward to two lines
          (~height*0.099 total); this caption is the last item of a centred column and was
          landing inside that band, so the two overprinted — #57's release and Bloomberg
          figures both rendered their caption on top of the source line. Introduced the same
          day as the universal source/source_url passthrough (remotion_engine.build_spec):
          before that, only statgrid could carry a source, and it draws its own footer.
          A centred column shifts up by half of any marginBottom, so this reserves 2x the
          band it needs to clear. */}
      {fields.caption ? (
        <div style={{fontFamily: BRAND.font, color: ink.body, opacity: 0.75 * imgOpacity,
                     fontSize: height * 0.028, lineHeight: 1.35, textAlign: 'center',
                     maxWidth: '62%', marginTop: height * 0.055,
                     marginBottom: (fields.source || fields.source_url) ? height * 0.11 : 0}}>
          {fields.caption}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// footage -> full-bleed image/B-roll with Ken Burns + a headline overlay + scrim
// (motion-playbook §2E). fields: {image, headline, accent}
export const Footage: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {height, fps} = useVideoConfig();
  const ink = useInk();
  const src: string | undefined = fields.image;
  const isVideo = typeof src === 'string' && /\.(mp4|mov|webm|m4v)$/i.test(src);
  const media = src ? (
    isVideo ? (
      <Video src={staticFile(src)} muted loop style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    ) : (
      <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    )
  ) : null;

  // FULL-BLEED (opt-in via fields.fit === 'full') — the original cover-the-frame look,
  // for the rare dramatic shot. Captions land on the footage in this mode.
  if (fields.fit === 'full') {
    const kb = interpolate(frame, [0, durationInFrames], [1.12, 1.22]);
    const pan = interpolate(frame, [0, durationInFrames], [-2, 2]);
    return (
      <AbsoluteFill>
        {src ? <AbsoluteFill style={{transform: `scale(${kb}) translateX(${pan}%)`}}>{media}</AbsoluteFill> : null}
        <AbsoluteFill style={{background: 'linear-gradient(0deg, rgba(9,13,28,.85) 0%, rgba(9,13,28,.25) 45%, rgba(9,13,28,.55) 100%)'}} />
        {fields.headline ? (
          <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 8%'}}>
            <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.07, color: BRAND.white, textAlign: 'center', textShadow: '0 10px 50px rgba(0,0,0,.8)'}}>
              {figColorize(fields.headline, fields.accent, fields.accent2, ink.accent, (ink.danger ?? (ink.paper ? '#c2352b' : BRAND.red)))}
            </div>
          </AbsoluteFill>
        ) : null}
      </AbsoluteFill>
    );
  }

  // INSET (DEFAULT, operator directive 2026-06-24) — the clip plays inside a framed,
  // shadowed window ON the brand background (the global <Background/> shows through the
  // transparent surround), sized to clear the lower-third caption zone so the burned-in
  // captions sit in their normal home. Reads as one continuous branded layout, not a jump-cut.
  const intro = spring({frame, fps, config: {damping: 18, stiffness: 90}});
  const winScale = interpolate(intro, [0, 1], [0.94, 1]);
  const kb = interpolate(frame, [0, durationInFrames], [1, 1.06]);
  return (
    <AbsoluteFill>
      {fields.headline ? (
        <div style={{position: 'absolute', top: '7%', left: 0, right: 0, textAlign: 'center', fontFamily: BRAND.font, color: ink.accent, fontWeight: 800, fontSize: height * 0.026, letterSpacing: 4, textTransform: 'uppercase', opacity: intro, padding: '0 8%'}}>
          {fields.accent2 && fields.accent2.length ? figColorize(fields.headline, fields.accent, fields.accent2, ink.accent, (ink.danger ?? (ink.paper ? '#c2352b' : BRAND.red))) : fields.headline}
        </div>
      ) : null}
      <div style={{position: 'absolute', top: '14%', left: '19%', width: '62%', height: '60%', borderRadius: 18, overflow: 'hidden', border: '2px solid rgba(245,247,255,.10)', boxShadow: '0 36px 100px rgba(0,0,0,.62), 0 0 0 1px rgba(0,0,0,.4)', transform: `scale(${winScale})`, opacity: intro}}>
        <div style={{position: 'absolute', inset: 0, transform: `scale(${kb})`}}>{media}<FigureMarks marks={fields.marks} /></div>
        <div style={{position: 'absolute', inset: 0, borderRadius: 18, boxShadow: 'inset 0 0 70px rgba(9,13,28,.5)'}} />
      </div>
    </AbsoluteFill>
  );
};
