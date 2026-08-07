import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';
import {useWorld, usePlace, flick} from './PaperWorld';

// CIRCUMVENT scene family (2026-07-30).
//
// Why this exists instead of reusing the Paper* family: those components print
// every line on a rounded cream CARD floating over a gradient table. Against real
// layered-paper art that reads as a UI panel pasted on top of a photograph. The
// operator's note was exact: "too flat and rendered".
//
// Here the paper IS the slide. A generated set fills the frame, cut-out props and
// figures stand ON that set, and type sits directly on the scene with only a soft
// scrim for legibility. No card, no border-radius, no drop-shadowed rectangle.
//
// Motion stays deterministic (renderAt(t) contract): set drifts, props place with
// the house spring, type rises. Nothing generative.

const ease = (frame: number, at: number, dur = 18) =>
  interpolate(frame, [at, at + dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

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

// The set: full-bleed generated paper diorama with a very slow push so the frame
// is never dead even when nothing else moves (this is what killed the QA dead-air
// score on the card version).
const Set: React.FC<{src?: string; anchor?: string}> = ({src, anchor}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const W = useWorld();
  if (!src) return <AbsoluteFill style={{backgroundColor: W.paper}} />;
  const t = durationInFrames ? frame / durationInFrames : 0;
  const scale = 1.06 + t * 0.05;             // slow push in
  const drift = interpolate(t, [0, 1], [0, -12]);
  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: W.paper}}>
      <Img
        src={src.startsWith('papercraft') ? staticFile(src) : staticFile(src)}
        style={{
          width: '100%', height: '100%', objectFit: 'cover',
          objectPosition: anchor || 'center',
          transform: `scale(${scale}) translateX(${drift}px)`,
        }}
      />
    </AbsoluteFill>
  );
};

// A cut-out prop or figure standing on the set. `place` is a 0..1 x position and
// `size` is a fraction of frame height, so props and people share one scale space.
const Cutout: React.FC<{
  src: string; at: number; place: number; size: number; flip?: boolean; baseline?: number;
}> = ({src, at, place: placeRaw, size, flip, baseline = 0.92}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const s = spring({frame: frame - at, fps, config: {damping: 13, stiffness: 200}});
  const W = useWorld();
  const h = height * size;
  // Portrait re-centering (operator direction 2026-08-06): decks are composed for 16:9,
  // and on a 4:5/9:16 render the same `place` fraction crowds the type block or the
  // frame edge. Compress horizontal placement toward center on narrow frames so the
  // composition stays center-weighted without per-aspect deck authoring.
  const place = width < height ? 0.5 + (placeRaw - 0.5) * 0.72 : placeRaw;
  return (
    <div style={{
      position: 'absolute', left: `${place * 100}%`, top: height * baseline,
      transform: `translate(-50%, -100%) translateY(${(1 - s) * 26}px) scale(${0.94 + s * 0.06}) ${flip ? 'scaleX(-1)' : ''}`,
      opacity: s, height: h,
    }}>
      {/* contact shadow so the cut-out sits ON the ground rather than floating */}
      <div style={{
        position: 'absolute', left: '50%', bottom: -h * 0.012, width: h * 0.42, height: h * 0.05,
        transform: 'translateX(-50%)', background: W.shadow, borderRadius: '50%',
        filter: 'blur(10px)', opacity: 0.5 * s,
      }} />
      <Img src={staticFile(src)} style={{height: '100%', width: 'auto', display: 'block'}} />
    </div>
  );
};

const Cutouts: React.FC<{items?: any[]}> = ({items}) => (
  <>
    {(items || []).map((p, i) => (
      <Cutout key={i} src={p.image} at={p.at ?? 6 + i * 5} place={p.place ?? 0.5 + i * 0.18}
              size={p.size ?? 0.42} flip={p.flip} baseline={p.baseline} />
    ))}
  </>
);

// Type printed on the scene. A soft directional scrim keeps it legible over busy
// art without drawing a box around it.
// The world's `paper` tone as an "r,g,b" triplet for scrim gradients. The scrims were
// hardcoded to Circumvent's kraft (#F2EDE0) until 2026-08-06, when the Cvg family became
// the shared renderer for all six personal-show worlds — each world's scrim is now its
// own paper stock.
const paperRgb = (hex: string): string => {
  const h = hex.replace('#', '');
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)).join(',');
};

const SceneType: React.FC<{
  kicker?: string; headline?: string; accent?: string[]; sub?: string;
  align?: 'left' | 'center'; at?: number; hit?: number | null; band?: 'top' | 'middle';
}> = ({kicker, headline, accent, sub, align = 'left', at = 3, hit = null, band = 'top'}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const e = ease(frame, at);
  const scale = hit != null ? flick(frame, hit) : 1;
  const long = (headline || '').length > 48;
  const P = paperRgb(W.paper);
  // Portrait pass 2026-08-07: type tracks the min dimension (landscape identical), and
  // the text block widens on narrow frames — 62% of a portrait width wastes the room.
  const portrait = height > width;
  const M = Math.min(width, height);
  return (
    <>
      <AbsoluteFill style={{
        background: band === 'top'
          ? `linear-gradient(180deg, rgba(${P},.90) 0%, rgba(${P},.62) 30%, rgba(${P},0) 56%)`
          : `linear-gradient(180deg, rgba(${P},0) 0%, rgba(${P},.74) 26%, rgba(${P},.74) 74%, rgba(${P},0) 100%)`,
        opacity: 0.98,
      }} />
      <AbsoluteFill style={{
        alignItems: align === 'center' ? 'center' : 'flex-start',
        justifyContent: band === 'top' ? 'flex-start' : 'center',
        padding: `${height * 0.085}px ${width * 0.075}px`,
      }}>
        <div style={{
          maxWidth: width * (portrait ? 0.85 : 0.62),
          transform: `translateY(${(1 - e) * 22}px) scale(${scale})`, opacity: e,
          textAlign: align,
        }}>
          {kicker ? (
            <div style={{
              fontFamily: BRAND.font, fontWeight: 800, fontSize: M * 0.021, letterSpacing: 5,
              textTransform: 'uppercase', color: W.accent, marginBottom: M * 0.016,
            }}>{kicker}</div>
          ) : null}
          {headline ? (
            <div style={{
              fontFamily: BRAND.font, fontWeight: 900, fontSize: M * (long ? 0.062 : 0.078),
              lineHeight: 1.06, color: W.ink, letterSpacing: -0.5,
            }}>{colorize(headline, accent, W.accent)}</div>
          ) : null}
          {sub ? (
            <div style={{
              fontFamily: BRAND.font, fontWeight: 700, fontSize: M * 0.026, color: W.accent,
              marginTop: M * 0.02,
            }}>{sub}</div>
          ) : null}
        </div>
      </AbsoluteFill>
    </>
  );
};

// ---------------------------------------------------------------- exported scenes

// statement / hook / quote -> type on the set, props standing in it
export const CvgScene: React.FC<{fields: any}> = ({fields}) => {
  const cf = fields.cueFrames || {};
  return (
    <AbsoluteFill>
      <Set src={fields.set} anchor={fields.anchor} />
      <Cutouts items={fields.props} />
      <SceneType kicker={fields.kicker} headline={fields.headline} accent={fields.accent}
                 sub={fields.subkicker || fields.attrib} align={fields.align}
                 at={cf.in ?? 3} hit={cf.hit ?? null} band={fields.band} />
    </AbsoluteFill>
  );
};

// cta -> the end card (operator layout direction 2026-08-06): everything centered in
// BOTH aspects — kicker (the site URL), a ONE-LINE headline (font fit to width so
// "Like & follow Circumvent Global" never wraps at 4:5), subkicker, and the paper brand
// mark centered beneath the type with clear air between them. No set: the card sits on
// the world's paper ground so the mark owns the frame.
export const CvgCta: React.FC<{fields: any}> = ({fields}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const cf = fields.cueFrames || {};
  const at = cf.in ?? 3;
  const e = ease(frame, at);
  const s = spring({frame: frame - at - 6, fps, config: {damping: 13, stiffness: 170}});
  const headline = fields.headline || '';
  // One line, always: width-fit (900-weight glyphs run ~0.52em) capped by a height-based
  // ceiling so short headlines don't balloon.
  const fit = (width * 0.88) / Math.max(1, headline.length * 0.52);
  const hSize = Math.min(height * 0.062, fit);
  const markH = Math.min(width, height) * 0.34;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{
          textAlign: 'center', transform: `translateY(${(1 - e) * 24}px)`, opacity: e,
          marginBottom: height * 0.045,
        }}>
          {fields.kicker ? (
            <div style={{
              fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.022, letterSpacing: 5,
              textTransform: 'uppercase', color: W.accent, marginBottom: height * 0.02,
            }}>{fields.kicker}</div>
          ) : null}
          <div style={{
            fontFamily: BRAND.font, fontWeight: 900, fontSize: hSize, lineHeight: 1.04,
            color: W.ink, letterSpacing: -0.5, whiteSpace: 'nowrap',
          }}>{colorize(headline, fields.accent, W.accent)}</div>
          {fields.subkicker ? (
            <div style={{
              fontFamily: BRAND.font, fontWeight: 700, fontSize: height * 0.024, color: W.accent,
              marginTop: height * 0.016,
            }}>{fields.subkicker}</div>
          ) : null}
        </div>
        {fields.mark ? (
          <div style={{
            height: markH, transform: `translateY(${(1 - s) * 30}px) scale(${0.92 + s * 0.08})`,
            opacity: s, position: 'relative',
          }}>
            <div style={{
              position: 'absolute', left: '50%', bottom: -markH * 0.06, width: markH * 0.7,
              height: markH * 0.07, transform: 'translateX(-50%)', background: W.shadow,
              borderRadius: '50%', filter: 'blur(12px)', opacity: 0.4 * s,
            }} />
            <Img src={staticFile(fields.mark)} style={{height: '100%', width: 'auto', display: 'block'}} />
          </div>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// punch -> one enormous word straight on the paper, no tag, no card
export const CvgPunch: React.FC<{fields: any}> = ({fields}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const cf = fields.cueFrames || {};
  const at = cf.in ?? 2;
  const s = spring({frame: frame - at, fps, config: {damping: 11, stiffness: 190}});
  const word = fields.word || fields.headline || '';
  // Long words (a full domain on the end card) need an extra step down or they run
  // past the safe area at 16:9. Sized off the min dimension (2026-08-07 portrait pass)
  // so a punch word can't outgrow a narrow frame; landscape identical.
  const M = Math.min(width, height);
  const size = M * (word.length > 16 ? 0.105 : word.length > 12 ? 0.15 : word.length > 7 ? 0.2 : 0.26);
  return (
    <AbsoluteFill>
      <Set src={fields.set} anchor={fields.anchor} />
      <Cutouts items={fields.props} />
      <AbsoluteFill style={{background: `radial-gradient(120% 80% at 50% 50%, rgba(${paperRgb(W.paper)},.88) 0%, rgba(${paperRgb(W.paper)},.62) 55%, rgba(${paperRgb(W.paper)},.28) 100%)`}} />
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center', transform: `scale(${0.9 + s * 0.1})`, opacity: s}}>
          {fields.kicker ? (
            <div style={{
              fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.024, letterSpacing: 6,
              textTransform: 'uppercase', color: W.accent, marginBottom: height * 0.02,
            }}>{fields.kicker}</div>
          ) : null}
          <div style={{
            fontFamily: BRAND.font, fontWeight: 900, fontSize: size, lineHeight: 0.98,
            color: fields.kind === 'bad' ? W.neutral : W.ink, letterSpacing: -2,
          }}>{word}</div>
          <div style={{
            height: height * 0.012, width: `${Math.min(78, word.length * 7)}%`, margin: `${height * 0.026}px auto 0`,
            background: W.accent, transform: `scaleX(${s})`, transformOrigin: 'center',
          }} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// list -> items printed as torn strips on the set, revealed in sequence
export const CvgList: React.FC<{fields: any}> = ({fields}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const items = fields.items || [];
  const cues = fields.itemFrames || items.map((_: any, i: number) => 8 + i * 16);
  // Type tracks the min dimension (2026-08-07 portrait pass): landscape identical, and
  // portrait labels scale to the narrow width instead of the tall height.
  const M = Math.min(width, height);
  return (
    <AbsoluteFill>
      <Set src={fields.set} anchor={fields.anchor} />
      <Cutouts items={fields.props} />
      <AbsoluteFill style={{
        background: 'linear-gradient(90deg, rgba(242,237,224,.92) 0%, rgba(242,237,224,.70) 34%, rgba(242,237,224,0) 62%)',
      }} />
      <AbsoluteFill style={{justifyContent: 'center', padding: `0 ${width * 0.075}px`}}>
        {fields.kicker ? (
          <div style={{
            fontFamily: BRAND.font, fontWeight: 800, fontSize: M * 0.021, letterSpacing: 5,
            textTransform: 'uppercase', color: W.accent, marginBottom: M * 0.028,
          }}>{fields.kicker}</div>
        ) : null}
        {items.map((it: any, i: number) => {
          const e = ease(frame, cues[i] ?? 8 + i * 16, 12);
          const label = typeof it === 'string' ? it : (it.title || it.label || '');
          return (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: width * 0.016,
              transform: `translateX(${(1 - e) * -30}px)`, opacity: e,
              marginBottom: M * 0.024,
            }}>
              <div style={{
                width: M * 0.052, height: M * 0.052, background: W.accent,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: BRAND.font, fontWeight: 900, fontSize: M * 0.026, color: W.paper,
                transform: `rotate(${i % 2 ? 1.6 : -1.4}deg)`,
              }}>{i + 1}</div>
              <div style={{
                fontFamily: BRAND.font, fontWeight: 900, fontSize: M * 0.058, color: W.ink, lineHeight: 1.1,
              }}>{label}</div>
            </div>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// compare -> the set split down the middle, each side labelled on the paper
export const CvgCompare: React.FC<{fields: any}> = ({fields}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {height, width} = useVideoConfig();
  const L = fields.left || {}, R = fields.right || {};
  const eL = ease(frame, 5, 14), eR = ease(frame, 15, 14);
  // Portrait: the two sides stack top/bottom with a horizontal divider (same collision
  // class as CvgSteps, fixed 2026-08-07); type tracks the min dimension so landscape is
  // pixel-identical (min == height there).
  const portrait = height > width;
  const M = Math.min(width, height);
  const Side: React.FC<{d: any; e: number; side: 'l' | 'r'}> = ({d, e, side}) => (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      transform: `translateY(${(1 - e) * 24}px)`, opacity: e, padding: `0 ${width * 0.03}px`,
    }}>
      <div style={{
        fontFamily: BRAND.font, fontWeight: 800, fontSize: M * 0.022, letterSpacing: 4,
        textTransform: 'uppercase', color: d.kind === 'bad' ? W.neutral : W.accent, marginBottom: M * 0.018,
      }}>{d.title || ''}</div>
      <div style={{
        fontFamily: BRAND.font, fontWeight: 900, fontSize: M * 0.072, lineHeight: 1.05,
        color: W.ink, textAlign: 'center', opacity: d.kind === 'bad' ? 0.62 : 1,
      }}>{d.value || ''}</div>
      <div style={{
        marginTop: M * 0.026, width: '46%', height: M * 0.011,
        background: d.kind === 'bad' ? W.neutral : W.accent, transform: `scaleX(${e})`,
      }} />
    </div>
  );
  return (
    <AbsoluteFill>
      <Set src={fields.set} anchor={fields.anchor} />
      <AbsoluteFill style={{background: 'rgba(242,237,224,.70)'}} />
      {fields.kicker ? (
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'flex-start', paddingTop: height * 0.1}}>
          <div style={{
            fontFamily: BRAND.font, fontWeight: 800, fontSize: M * 0.021, letterSpacing: 5,
            textTransform: 'uppercase', color: W.accent,
          }}>{fields.kicker}</div>
        </AbsoluteFill>
      ) : null}
      <AbsoluteFill style={{flexDirection: portrait ? 'column' : 'row', alignItems: 'center',
                            justifyContent: 'center', padding: portrait ? `${height * 0.14}px 0` : 0}}>
        <Side d={L} e={eL} side="l" />
        <div style={portrait
          ? {height: 3, width: '38%', background: W.accent, opacity: 0.5}
          : {width: 3, height: '46%', background: W.accent, opacity: 0.5}} />
        <Side d={R} e={eR} side="r" />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// steps -> props walking across the set left to right, labelled underneath
export const CvgSteps: React.FC<{fields: any}> = ({fields}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {height, width} = useVideoConfig();
  const steps = fields.steps || [];
  const cues = fields.stepFrames || steps.map((_: any, i: number) => 6 + i * 18);
  const n = Math.max(steps.length, 1);
  // Portrait fix (operator report 2026-08-07: columns collided on the first FMF episode's
  // 4:5/9:16 renders). The row layout shrank column WIDTH with the frame while the label
  // font tracked HEIGHT, so portrait exploded the ratio. On portrait frames the steps now
  // stack VERTICALLY (that's where portrait's room is) with downward connectors, and all
  // type tracks the min dimension — landscape output is pixel-identical (min == height).
  const portrait = height > width;
  const M = Math.min(width, height);
  return (
    <AbsoluteFill>
      <Set src={fields.set} anchor={fields.anchor} />
      <AbsoluteFill style={{
        background: 'linear-gradient(180deg, rgba(242,237,224,.10) 0%, rgba(242,237,224,.45) 46%, rgba(242,237,224,.82) 100%)',
      }} />
      {fields.kicker ? (
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'flex-start', paddingTop: height * 0.09}}>
          <div style={{
            fontFamily: BRAND.font, fontWeight: 800, fontSize: M * 0.021, letterSpacing: 5,
            textTransform: 'uppercase', color: W.accent,
          }}>{fields.kicker}</div>
        </AbsoluteFill>
      ) : null}
      <AbsoluteFill style={portrait
        ? {flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: height * 0.012}
        : {flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: width * 0.012}}>
        {steps.map((s: any, i: number) => {
          const e = ease(frame, cues[i] ?? 6 + i * 18, 12);
          const label = typeof s === 'string' ? s : (s.title || '');
          const img = (fields.stepImages || [])[i];
          return (
            <React.Fragment key={i}>
              {i > 0 ? (
                <div style={portrait
                  ? {width: 3, height: height * 0.022, background: W.accent,
                     transform: `scaleY(${ease(frame, (cues[i] ?? 0) - 6, 10)})`, transformOrigin: 'top'}
                  : {width: width * 0.026, height: 3, background: W.accent,
                     transform: `scaleX(${ease(frame, (cues[i] ?? 0) - 6, 10)})`, transformOrigin: 'left'}} />
              ) : null}
              <div style={{
                width: portrait ? '84%' : `${72 / n}%`, textAlign: 'center',
                transform: `translateY(${(1 - e) * 20}px)`, opacity: e,
              }}>
                {img ? (
                  <Img src={staticFile(img)} style={{height: M * (portrait ? 0.16 : 0.26), width: 'auto', display: 'block', margin: '0 auto'}} />
                ) : null}
                <div style={{
                  fontFamily: BRAND.font, fontWeight: 900, fontSize: M * 0.036, color: W.ink,
                  lineHeight: 1.12, marginTop: M * 0.016,
                }}>{label}</div>
              </div>
            </React.Fragment>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// define -> term set large on the paper with the definition beneath, no tag
export const CvgDefine: React.FC<{fields: any}> = ({fields}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {height, width} = useVideoConfig();
  const e1 = ease(frame, 4, 14), e2 = ease(frame, 16, 16);
  // 2026-08-07 portrait pass: type off the min dimension; definition block widens on
  // narrow frames. Landscape identical (min == height).
  const portrait = height > width;
  const M = Math.min(width, height);
  return (
    <AbsoluteFill>
      <Set src={fields.set} anchor={fields.anchor} />
      <Cutouts items={fields.props} />
      <AbsoluteFill style={{background: 'linear-gradient(90deg, rgba(242,237,224,.92) 0%, rgba(242,237,224,.74) 46%, rgba(242,237,224,.20) 100%)'}} />
      <AbsoluteFill style={{alignItems: 'flex-start', justifyContent: 'center', padding: `0 ${width * 0.09}px`}}>
        {fields.kicker ? (
          <div style={{
            fontFamily: BRAND.font, fontWeight: 800, fontSize: M * 0.021, letterSpacing: 5,
            textTransform: 'uppercase', color: W.accent, marginBottom: M * 0.02, opacity: e1,
          }}>{fields.kicker}</div>
        ) : null}
        <div style={{
          fontFamily: BRAND.font, fontWeight: 900, fontSize: M * 0.11, lineHeight: 1, color: W.ink,
          transform: `translateY(${(1 - e1) * 22}px)`, opacity: e1, letterSpacing: -2,
        }}>{fields.term || ''}</div>
        <div style={{
          height: M * 0.012, width: '34%', background: W.accent, margin: `${M * 0.028}px 0`,
          transform: `scaleX(${e1})`, transformOrigin: 'left',
        }} />
        <div style={{
          fontFamily: BRAND.font, fontWeight: 700, fontSize: M * 0.04, lineHeight: 1.3,
          color: W.ink, maxWidth: width * (portrait ? 0.85 : 0.62), opacity: e2, transform: `translateY(${(1 - e2) * 16}px)`,
        }}>{fields.definition || ''}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
