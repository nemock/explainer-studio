import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import {useInk, PAPER_SHADOW} from '../ink';
import {colorizeText} from './colorize';
import {fitStageText} from './PaperStage';

// motion-playbook §2A/F — the closing CTA. Floats the brand book cover in next to the
// call-to-action text (operator directive 2026-06-24: show the cover, don't just talk
// about it). fields: {kicker, headline, subkicker, accent, image(book cover basename)}
export const CTA: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const portrait = height > width;
  const ink = useInk();
  const intro = spring({frame, fps, config: {damping: 16, stiffness: 80}});
  const tIntro = spring({frame: frame - 12, fps, config: {damping: 18}});
  const bob = Math.sin((frame / fps) * 1.1) * (height * 0.01);
  const sway = Math.sin((frame / fps) * 0.7) * 2.2; // gentle degrees of life

  const book = fields.image ? (
    <Img
      src={staticFile(fields.image)}
      style={{
        width: portrait ? '74%' : '44%',
        maxHeight: portrait ? '46%' : '78%',
        objectFit: 'contain',
        opacity: intro,
        transform: `translateY(${interpolate(intro, [0, 1], [80, 0]) + bob}px) scale(${interpolate(intro, [0, 1], [0.82, 1])}) rotate(${sway}deg)`,
        filter: 'drop-shadow(0 36px 70px rgba(0,0,0,.6))',
      }}
    />
  ) : null;

  // With a book cover beside it the text is one column of a two-column layout, so its
  // size is set by the space the cover leaves. WITHOUT a cover the same fixed 7% headline
  // floats in an otherwise empty frame — which is how the closing card of a 20-minute
  // video ended up as a small line of type surrounded by cream (operator, 2026-08-12:
  // "fix the CTA card spacing"). In that case fit the headline to the frame, using the
  // same box as the TextScenes headlines so the closing card matches the cards before it.
  // Floored at the old 7%, so this can only ever grow the type, never shrink it.
  const wide = !book && !portrait;
  const headlineSize = wide
    ? Math.max(height * 0.07, fitStageText(fields.headline || '', width * 0.84, height * 0.42))
    : height * 0.07;

  const text = (
    <div style={{textAlign: (portrait || !book) ? 'center' : 'left', maxWidth: portrait ? '90%' : (book ? '46%' : '84%'), opacity: tIntro,
                 transform: `translateY(${interpolate(tIntro, [0, 1], [24, 0])}px)`}}>
      {fields.kicker ? (
        <div style={{fontFamily: BRAND.font, color: ink.accent, fontWeight: 800, fontSize: height * 0.030, letterSpacing: 4, textTransform: 'uppercase', marginBottom: height * 0.028}}>
          {fields.kicker}
        </div>
      ) : null}
      <div style={{fontFamily: BRAND.font, color: ink.body, fontWeight: 900, fontSize: headlineSize, lineHeight: 1.05, textShadow: ink.paper ? PAPER_SHADOW : '0 10px 50px rgba(0,0,0,.6)'}}>
        {colorizeText(fields.headline, fields.accent, fields.accentRed, ink.accent, (ink.danger ?? BRAND.red))}
      </div>
      {fields.subkicker ? (
        <div style={{fontFamily: BRAND.font, color: ink.body, opacity: 0.82, fontWeight: 700, fontSize: height * 0.03, marginTop: height * 0.028, lineHeight: 1.3}}>
          {fields.subkicker}
        </div>
      ) : null}
    </div>
  );

  // The like/subscribe corner badge (operator, 2026-08-12: viewers expect it up there, and
  // it does not read as unserious even on a professional training series). Deliberately
  // NOT the `image` field — that one puts a book cover beside the text and reflows the
  // whole card into two columns. This sits over the layout and changes nothing beneath it.
  // It drifts and breathes so the closing card never trips freezedetect.
  const badgeIn = spring({frame: frame - 20, fps, config: {damping: 14, stiffness: 90}});
  const badgeBob = Math.sin((frame / fps) * 1.4) * (height * 0.006);
  const badge = fields.badge ? (
    <Img
      src={staticFile(fields.badge)}
      style={{
        position: 'absolute',
        top: height * 0.07,
        right: width * 0.06,
        width: portrait ? '34%' : '15%',
        opacity: badgeIn,
        transform: `translateY(${interpolate(badgeIn, [0, 1], [-26, 0]) + badgeBob}px) `
                 + `scale(${interpolate(badgeIn, [0, 1], [0.7, 1])}) `
                 + `rotate(${Math.sin((frame / fps) * 0.9) * 1.6}deg)`,
        filter: 'drop-shadow(0 14px 26px rgba(12,4,24,.28))',
      }}
    />
  ) : null;

  return (
    <AbsoluteFill
      style={{
        alignItems: 'center',
        justifyContent: 'center',
        gap: portrait ? height * 0.04 : width * 0.04,
        flexDirection: portrait ? 'column' : 'row',
        padding: '0 7%',
      }}
    >
      {book}
      {text}
      {badge}
    </AbsoluteFill>
  );
};
