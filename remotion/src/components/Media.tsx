import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

// wrap accent substrings of `text` in green (for the figure's phase-1 title line)
const figColorize = (text: string, accents: string[]) => {
  if (!text) return null;
  if (!accents || !accents.length) return text;
  const esc = accents.map((a) => a.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const re = new RegExp(`(${esc.join('|')})`, 'ig');
  return text.split(re).map((p, i) =>
    accents.some((a) => a.toLowerCase() === p.toLowerCase())
      ? <span key={i} style={{color: BRAND.green}}>{p}</span>
      : <React.Fragment key={i}>{p}</React.Fragment>);
};

// figure -> a framed document/artifact excerpt with Ken Burns + an optional marker-wipe
// highlight (motion-playbook §2D). fields: {image, kicker, caption, highlight?, title?, accent?, imageFromFrac?}
// imageFromFrac: when set (0-1), the figure opens as a TEXT card (the `title` line) and the
// framed image is revealed only at that fraction of the scene — so a long single-segment
// figure can hold a lesson, then reveal the artifact when the narration names it (#13 Magic Link).
export const Figure: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const revealFrac = fields.imageFromFrac ?? 0;
  const revealAt = revealFrac * durationInFrames;
  const phased = revealFrac > 0 && !!fields.title;

  const kIntro = spring({frame, fps, config: {damping: 18, stiffness: 90}});
  const imgIntro = spring({frame: frame - revealAt, fps, config: {damping: 18, stiffness: 90}});
  const kb = interpolate(frame, [0, durationInFrames], [1, 1.06]);
  const scale = interpolate(imgIntro, [0, 1], [0.92, 1]) * kb;
  const imgOpacity = phased ? interpolate(frame, [revealAt, revealAt + 0.4 * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
  const titleOpacity = phased ? interpolate(frame, [6, 16, revealAt - 8, revealAt + 2], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
  const hl = fields.highlight;
  const at = (hl?.atFrac ?? 0.35) * durationInFrames;
  const hlW = hl ? interpolate(frame, [at, at + 0.45 * fps * 3], [0, hl.widthTo ?? 40], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 6%'}}>
      {fields.kicker ? (
        <div style={{fontFamily: BRAND.font, color: BRAND.green, fontWeight: 800, fontSize: height * 0.024, letterSpacing: 4, textTransform: 'uppercase', opacity: kIntro, marginBottom: height * 0.025}}>
          {fields.kicker}
        </div>
      ) : null}
      {phased ? (
        <div style={{position: 'absolute', left: 0, right: 0, textAlign: 'center', padding: '0 12%', fontFamily: BRAND.font, color: BRAND.white, fontWeight: 900, fontSize: height * 0.062, lineHeight: 1.15, opacity: titleOpacity, textShadow: '0 3px 18px rgba(0,0,0,.6)'}}>
          {figColorize(fields.title, fields.accent || [])}
        </div>
      ) : null}
      <div style={{position: 'relative', maxWidth: '76%', background: '#fff', borderRadius: 26, padding: height * 0.022, boxShadow: '0 40px 120px rgba(0,0,0,.55)', transform: `scale(${scale})`, opacity: imgOpacity}}>
        <Img src={staticFile(fields.image)} style={{maxWidth: '100%', maxHeight: Math.round(height * 0.56), objectFit: 'contain', display: 'block', borderRadius: 8}} />
        {hl ? (
          <div style={{position: 'absolute', top: `${hl.top ?? 30}%`, left: `${hl.left ?? 6}%`, height: `${hl.height ?? 12}%`, width: `${hlW}%`, background: 'rgba(61,220,132,.42)', borderRadius: 8}} />
        ) : null}
      </div>
      {fields.caption ? (
        <div style={{fontFamily: BRAND.font, color: BRAND.white, opacity: 0.75 * imgOpacity, fontSize: height * 0.022, marginTop: height * 0.025}}>
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
  const src: string | undefined = fields.image;
  const isVideo = typeof src === 'string' && /\.(mp4|mov|webm|m4v)$/i.test(src);
  const media = src ? (
    isVideo ? (
      <OffthreadVideo src={staticFile(src)} muted loop style={{width: '100%', height: '100%', objectFit: 'cover'}} />
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
              {fields.headline}
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
        <div style={{position: 'absolute', top: '7%', left: 0, right: 0, textAlign: 'center', fontFamily: BRAND.font, color: BRAND.green, fontWeight: 800, fontSize: height * 0.026, letterSpacing: 4, textTransform: 'uppercase', opacity: intro, padding: '0 8%'}}>
          {fields.headline}
        </div>
      ) : null}
      <div style={{position: 'absolute', top: '14%', left: '19%', width: '62%', height: '60%', borderRadius: 18, overflow: 'hidden', border: '2px solid rgba(245,247,255,.10)', boxShadow: '0 36px 100px rgba(0,0,0,.62), 0 0 0 1px rgba(0,0,0,.4)', transform: `scale(${winScale})`, opacity: intro}}>
        <div style={{position: 'absolute', inset: 0, transform: `scale(${kb})`}}>{media}</div>
        <div style={{position: 'absolute', inset: 0, borderRadius: 18, boxShadow: 'inset 0 0 70px rgba(9,13,28,.5)'}} />
      </div>
    </AbsoluteFill>
  );
};
