import React from 'react';
import {AbsoluteFill, Sequence, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import {useInk} from '../ink';

// On-screen source citation (operator directive 2026-08-12: "we cite our sources, so
// URLs. We don't have to read them in the script, but we'll put them at the bottom of
// the screen. Make sure that these subtitles don't land on them.")
//
// TWO PROBLEMS THIS SOLVES, and the second is the one that was actually broken.
//
// 1. COVERAGE. Before this, exactly ONE component rendered a source footer — StatGrid,
//    with its own private `bottom: height * 0.05`. Every other slide type dropped
//    `fields.source` on the floor. A `figure` or `quote` slide could carry a citation in
//    deck.json and show nothing. Rendering once at the Video level, next to Captions,
//    means every slide type gets it and there is one place to reason about layout.
//
// 2. COLLISION. Captions sit at `captionBottomPx` (height * 0.16 by default) measured
//    from the frame bottom. The source sits at height * 0.05 and grows UPWARD, because
//    it is bottom-anchored. A short label like "GitClear (vendor)" never reached the
//    captions. A full URL is a different animal: unwrapped it overflows the frame, and
//    wrapped it climbs into the caption band. So the band is CAPPED at two lines and the
//    font shrinks to fit rather than growing into the captions.
//
// Budget at the default 1080p: bottom 0.05 + two lines at 0.018 * 1.35 = 0.099 of frame
// height. Caption floor is 0.16. Roughly 6% of frame height stays clear between them.

const BOTTOM_FRAC = 0.05;      // distance from frame bottom to the band's baseline
const FONT_FRAC = 0.018;       // matches the old StatGrid footer, so nothing shifts
const LINE_HEIGHT = 1.35;
const MAX_LINES = 2;
const CLEARANCE_FRAC = 0.03;   // minimum gap the band must leave under the caption floor

/** Make a URL readable at 18px on a 1080p frame without overflowing the line.
 *  Strips the protocol and www, keeps the host and the last meaningful path segment,
 *  and elides the middle — `klarna.com/…/klarna-ai-assistant-handles-two-thirds…`.
 *  A URL nobody can read is decoration; the pinned comment carries the full link. */
export const prettyUrl = (raw: string, maxLen = 68): string => {
  let u = String(raw).replace(/^https?:\/\//i, '').replace(/^www\./i, '').replace(/\/$/, '');
  if (u.length <= maxLen) return u;
  const slash = u.indexOf('/');
  if (slash < 0) return u.slice(0, maxLen - 1) + '…';
  const host = u.slice(0, slash);
  const tail = u.slice(u.lastIndexOf('/') + 1);
  const room = maxLen - host.length - 4;
  return host + '/…/' + (tail.length > room ? tail.slice(0, Math.max(8, room - 1)) + '…' : tail);
};

export const SourceLine: React.FC<{
  source?: string;
  sourceUrl?: string;
  captionBottomPx: number;
}> = ({source, sourceUrl, captionBottomPx}) => {
  const {height} = useVideoConfig();
  const ink = useInk();
  if (!source && !sourceUrl) return null;

  const parts = [source, sourceUrl ? prettyUrl(sourceUrl) : ''].filter(Boolean);
  const text = parts.join('  ·  ');

  // Shrink to fit rather than climb: whatever two lines of this font would occupy, it
  // must still clear the caption floor by CLEARANCE_FRAC.
  const budget = captionBottomPx - height * (BOTTOM_FRAC + CLEARANCE_FRAC);
  const wanted = height * FONT_FRAC * LINE_HEIGHT * MAX_LINES;
  const fontSize = wanted <= budget
    ? height * FONT_FRAC
    : Math.max(height * 0.012, budget / (LINE_HEIGHT * MAX_LINES));

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{
        position: 'absolute', bottom: height * BOTTOM_FRAC, left: '8%', right: '8%',
        textAlign: 'center', fontFamily: BRAND.font, fontSize, lineHeight: LINE_HEIGHT,
        color: ink.soft,
        // hard stop at MAX_LINES; anything longer is elided rather than allowed to grow
        display: '-webkit-box', WebkitLineClamp: MAX_LINES, WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
      }}>
        {text}
      </div>
    </AbsoluteFill>
  );
};

/** Per-scene wrapper: mount once at the Video level so EVERY slide type is covered. */
export const SourceLines: React.FC<{scenes: any[]; captionBottomPx: number}> = ({scenes, captionBottomPx}) => (
  <>
    {scenes.map((s, i) => {
      const f = s.fields || {};
      if (!f.source && !f.source_url) return null;
      return (
        <Sequence key={`src${i}`} from={s.from} durationInFrames={s.durationInFrames} layout="none">
          <SourceLine source={f.source} sourceUrl={f.source_url} captionBottomPx={captionBottomPx} />
        </Sequence>
      );
    })}
  </>
);
