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
  const {durationInFrames, width, height} = useVideoConfig();
  const W = useWorld();
  if (!src) return <AbsoluteFill style={{backgroundColor: W.paper}} />;
  const t = durationInFrames ? frame / durationInFrames : 0;
  const scale = 1.06 + t * 0.05;             // slow push in
  const drift = interpolate(t, [0, 1], [0, -12]);
  const resolved = staticFile(src);

  // PORTRAIT (2026-08-30). The sets are 16:9 scenes — a wide arrangement of furniture on
  // a ground line, under a deliberately empty wall that exists so type has somewhere to
  // live. `objectFit: cover` into a 9:16 frame keeps only the middle **32%** of that
  // width (0.5625 / 1.787), which is not a crop so much as a different picture: on
  // set_desk_night it lands on the laptop and the page stack, cuts both in half at the
  // frame edge, and throws away the lamp, the plant, the mug and the window. That is the
  // severed-prop defect in the 2026-08-30 framing audit, and it is also where much of
  // the empty top band came from, since the wall got scaled up with everything else.
  //
  // So portrait fits the scene to WIDTH instead. Nothing is severed, the whole
  // arrangement reads, and it sits on the bottom where a ground line belongs. The space
  // above is filled from a blurred copy of the SAME art rather than a colour constant:
  // measured across all four FWF sets, the top row is near-uniform deep violet (channel
  // spread 20-49), so the blurred fill and the band's own top meet with no visible seam,
  // and it stays correct if the art is ever regenerated. Blur, not a plain copy, because
  // an unblurred backdrop shows stretched furniture peeking above the band.
  //
  // Landscape is untouched: a 1.787 set in a 1.778 frame is already a whole-scene fit.
  if (height > width) {
    // Origin bottom-centre so the push-in grows out of the ground line. Range kept to
    // 1.025 deliberately — the outermost props (the lamp) start ~1.5% from the image
    // edge, and a larger push would start clipping the very objects this fix recovers.
    const pScale = 1.0 + t * 0.025;
    return (
      <AbsoluteFill style={{overflow: 'hidden', backgroundColor: W.paper}}>
        {/* `cover` maps the whole image HEIGHT into the frame (the width is what gets
            cropped), so a merely-scaled backdrop still contains the desk and the floor,
            and blurring that gave a pale wash that met the band's deep violet top in a
            hard horizontal seam — visibly worse than the crop it replaced. Zooming to
            3.2 from the top edge keeps only the image's top ~31%, which is wall on all
            four sets, so the fill is the wall's own colour and the join disappears. */}
        <Img
          src={resolved}
          style={{
            width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top',
            transform: `scale(${3.2 + t * 0.06})`, transformOrigin: 'top center',
            filter: 'blur(40px) saturate(0.95)',
          }}
        />
        <Img
          src={resolved}
          style={{
            position: 'absolute', left: 0, right: 0, bottom: 0,
            width: '100%', height: 'auto',
            transform: `scale(${pScale})`, transformOrigin: 'bottom center',
          }}
        />
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: W.paper}}>
      <Img
        src={resolved}
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
}> = ({src, at, place: placeRaw, size, flip, baseline}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const s = spring({frame: frame - at, fps, config: {damping: 13, stiffness: 200}});
  const W = useWorld();
  // Default baseline clears the caption band on portrait (operator report 2026-08-07:
  // the caption pill landed ON the chibi presenter at 4:5). Portrait captions occupy
  // the lower ~16%, so cutouts default to feet at 0.80 there; landscape keeps 0.92.
  // An explicit deck `baseline` always wins.
  const base = baseline ?? (height > width ? 0.80 : 0.92);
  const h = height * size;
  // Portrait re-centering (operator direction 2026-08-06): decks are composed for 16:9,
  // and on a 4:5/9:16 render the same `place` fraction crowds the type block or the
  // frame edge. Compress horizontal placement toward center on narrow frames so the
  // composition stays center-weighted without per-aspect deck authoring.
  const place = width < height ? 0.5 + (placeRaw - 0.5) * 0.72 : placeRaw;
  return (
    <div style={{
      position: 'absolute', left: `${place * 100}%`, top: height * base,
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

// Kicker size (2026-08-30, operator: "I don't understand why it is so tiny. We've got
// plenty of vertical space").
//
// Kickers were `M * 0.021`, and M is the MIN dimension — the WIDTH in portrait. That is
// the right rule for a headline, which has to survive a narrow frame, but on a kicker it
// meant 22.7px of type in a 1920-tall frame next to an 84px headline. CvgPunch and
// CvgCta had already gone their own way and size off `height` (42-46px), so the small
// ones were an inconsistency rather than a decision.
//
// It cannot be a flat bump, because kicker length varies enormously — but the FIRST
// version of this got the constraint wrong and is worth recording, because the mistake
// is easy to repeat. It capped the size so the kicker fitted on ONE line. Nothing forces
// one line: the kicker is an ordinary block and wraps. So a long kicker like "40% OF
// SURVEYED CASES INVOLVED A LITIGANT USING AI" (49 chars) was pinned to the old 22.7px
// to avoid a horizontal overflow that would never have happened, in a frame with a
// thousand pixels of unused height above it. Operator, on seeing it: "I can barely read
// that myself. Why, when there is so much available space...".
//
// The budget is therefore AREA, not line width: allow the type to wrap to two lines and
// size it to fit that. Two rather than one because the vertical room is genuinely there,
// and not more than two because a kicker is a label — at three lines it stops reading as
// one and starts competing with the headline.
//
// Uppercase 800-weight runs ~0.62em, plus the tracking, which is a per-character cost
// and so is subtracted before dividing. The floor is the old size, so no kicker is ever
// SMALLER than it is today: this can only grow type, never shrink it.
const KICKER_LINES = 2;
const kickerSize = (text: string, M: number, width: number, portrait: boolean): number => {
  const base = M * 0.021;
  if (!portrait) return base;
  const n = Math.max(1, (text || '').length);
  const usable = width * 0.86;              // frame minus the type block's side padding
  const fits = ((KICKER_LINES * usable) / n - 5) / 0.62;
  return Math.max(base, Math.min(M * 0.034, fits));
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
  // Headline size is LENGTH-AWARE, the idiom CvgPunch / CvgCta / CvgCompare already use
  // (2026-08-11). Until 2026-08-12 this was a single boolean with two sizes, so anything
  // past ~110 chars overran the block box and printed off the top of the frame. FMF
  // 2026-08-07 shipped its COVER slide that way (s1, 230 chars, "Boston Scientific's"
  // clipped at the frame edge) and nothing caught it. The first two tiers reproduce the
  // old boolean exactly, so every headline that fit before renders pixel-identical.
  // Boundaries come from RENDERED evidence, not arithmetic. The block box is 47.5% of
  // height and 4:5 (1350px) binds, not 9:16 — but a character-width estimate off that box
  // put the limit at 165, and the renders disagree: WSC 2026-08-12 s23 fits at 173 chars,
  // FMF 2026-08-07 s1 clips at 233. So the first step sits at 185, between the two
  // measured points and leaning safe. Everything that fit before still renders at exactly
  // its old size; only genuine overflow steps down. Re-tune from stills, never from a
  // formula, and check 4:5 rather than 9:16.
  const hLen = (headline || '').length;
  const hSize = hLen <= 48 ? 0.078
    : hLen <= 185 ? 0.062
    : hLen <= 240 ? 0.052
    : hLen <= 320 ? 0.044
    : 0.038;
  const P = paperRgb(W.paper);
  // Portrait pass 2026-08-07: type tracks the min dimension (landscape identical), and
  // the text block widens on narrow frames — 62% of a portrait width wastes the room.
  const portrait = height > width;
  const M = Math.min(width, height);
  // Portrait pass 2026-08-11 (operator, FTT 08-11 slide 1: "the text is crammed way to
  // the top of the screen, even though there is plenty of room in the middle... the font
  // doesn't need to be so tiny"). Two portrait-only changes; landscape stays identical.
  //
  // 1. A `top` band no longer pins the block to the frame edge. The top scrim already
  //    fades to nothing at 56% of height, so that band IS the type's room — the block now
  //    centres inside it instead of sitting at its ceiling. This closes the dead strip
  //    between the headline and the set's subject without printing over the artwork.
  // 2. Type tracks the min dimension, which on portrait is the WIDTH. That sizes the
  //    block as if the frame were 1080 square and leaves a 1080x1920 frame visibly
  //    under-set. Scale type up on portrait rather than leaving the room empty.
  const TS = portrait ? 1.18 : 1;
  const topBand = band === 'top' && portrait;
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
        justifyContent: band === 'top' && !portrait ? 'flex-start' : 'center',
        // Portrait: reserve the caption band (lower ~16%) so a centered block can never
        // run under the caption pill (operator report 2026-08-07). On a portrait `top`
        // band the reserve is the whole lower 44% instead, which is what turns the top
        // scrim into the block's box so it can centre inside it (2026-08-11).
        padding: portrait
          ? `${height * 0.085}px ${width * 0.075}px ${height * (topBand ? 0.44 : 0.18)}px`
          : `${height * 0.085}px ${width * 0.075}px`,
      }}>
        <div style={{
          maxWidth: width * (portrait ? 0.85 : 0.62),
          transform: `translateY(${(1 - e) * 22}px) scale(${scale})`, opacity: e,
          textAlign: align,
        }}>
          {kicker ? (
            <div style={{
              fontFamily: BRAND.font, fontWeight: 800, fontSize: kickerSize(kicker, M, width, portrait), letterSpacing: 5,
              textTransform: 'uppercase', color: W.accent, marginBottom: M * 0.016,
            }}>{kicker}</div>
          ) : null}
          {headline ? (
            <div style={{
              fontFamily: BRAND.font, fontWeight: 900, fontSize: M * hSize * TS,
              lineHeight: 1.06, color: W.ink, letterSpacing: -0.5,
            }}>{colorize(headline, accent, W.accent)}</div>
          ) : null}
          {sub ? (
            <div style={{
              fontFamily: BRAND.font, fontWeight: 700, fontSize: M * 0.026 * TS, color: W.accent,
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
  // past the safe area at 16:9. Sized off the min dimension (2026-08-07 portrait pass),
  // then HARD-CAPPED to the frame width the way CvgCta fits its headline — the length
  // steps alone let "Irreversible" (12 chars) bleed past a 1080px-wide frame edge to
  // edge (operator screenshot, FMF 4:5).
  //
  // 2026-08-30: the cap used a flat 0.52em per character, which is an AVERAGE and so
  // cannot bound a word made of wide glyphs. Measured from renders: FWF 2026-08-29 s7
  // "MAXIMUM" clipped both frame edges at 9:16, and FWF 2026-08-30 s6 "UNREAD" clipped
  // the U and the D. Both are all-caps runs of wide letters (M/W ~0.95em, most caps
  // ~0.68em, I ~0.30em), so their real width is 0.62-0.68em per character and the cap
  // never bound. A per-character sum fixes it without over-shrinking narrow words the
  // way a single safer constant would: "MAXIMUM" measures 5.19em and steps down hard,
  // while a same-length word of narrow glyphs keeps its size. Re-tune the table from
  // rendered stills, never from a formula.
  const EM_WIDE = 0.95;   // M W
  const EM_NARROW = 0.60; // E F L T J
  const EM_THIN = 0.30;   // I
  const emWidth = (w: string) => {
    let sum = 0;
    for (const ch of w.toUpperCase()) {
      if (ch === 'M' || ch === 'W') sum += EM_WIDE;
      else if (ch === 'I') sum += EM_THIN;
      else if ('EFLTJ'.includes(ch)) sum += EM_NARROW;
      else if (ch === ' ') sum += 0.28;
      else sum += 0.68;
    }
    return Math.max(0.5, sum);
  };
  const M = Math.min(width, height);
  const stepped = M * (word.length > 16 ? 0.105 : word.length > 12 ? 0.15 : word.length > 7 ? 0.2 : 0.26);
  // 0.88 not 0.9: the old budget left no room for the negative letterSpacing rounding
  // that put "UNREAD" a few pixels over an already-too-generous cap.
  const size = Math.min(stepped, (width * 0.88) / emWidth(word));
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
            color: fields.kind === 'bad' ? (W.neutral ?? `${W.ink}8A`) : W.ink, letterSpacing: -2,
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
  const portrait = height > width;
  return (
    <AbsoluteFill>
      <Set src={fields.set} anchor={fields.anchor} />
      <Cutouts items={fields.props} />
      {/* Legibility scrim. The landscape ramp reaches zero at 62% of the width, which
          was safe while the text block was landscape-narrow and sat inside it.
          Portrait pads only 7.5% a side (below), so items run to 92.5% — well past
          where this scrim has faded to nothing — and any item long enough to cross 62%
          printed ink-on-ink over the dark half of the set. Measured on FWF 2026-08-29
          slide 9: "behind", "first" and "migration, end" were unreadable, ink (43,18,66)
          on ground (47,21,60), about 1.1:1.

          So portrait gets its own ramp that never fully clears. It bottoms out at .60,
          which over the darkest ground in these worlds composites to roughly 6:1 against
          the ink — clear of WCAG AA with room for a darker set later. Landscape keeps
          the original ramp byte-for-byte, so Circumvent's 16:9 is untouched. */}
      <AbsoluteFill style={{
        background: portrait
          ? 'linear-gradient(90deg, rgba(242,237,224,.93) 0%, rgba(242,237,224,.86) 45%, rgba(242,237,224,.72) 75%, rgba(242,237,224,.60) 100%)'
          : 'linear-gradient(90deg, rgba(242,237,224,.92) 0%, rgba(242,237,224,.70) 34%, rgba(242,237,224,0) 62%)',
      }} />
      <AbsoluteFill style={{justifyContent: 'center',
                            padding: width < height
                              ? `0 ${width * 0.075}px ${height * 0.18}px`
                              : `0 ${width * 0.075}px`}}>
        {fields.kicker ? (
          <div style={{
            fontFamily: BRAND.font, fontWeight: 800, fontSize: kickerSize(fields.kicker, M, width, portrait), letterSpacing: 5,
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
              {/* `ordered: false` swaps the index badge for a plain paper chip. A statgrid
                  routes here on the Cvg worlds (no counter component exists), and numbering
                  three statistics 1/2/3 reads as a ranking they do not have. */}
              <div style={{
                width: M * (fields.ordered === false ? 0.022 : 0.052), height: M * 0.052,
                background: W.accent, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: BRAND.font, fontWeight: 900, fontSize: M * 0.026, color: W.paper,
                transform: `rotate(${i % 2 ? 1.6 : -1.4}deg)`,
              }}>{fields.ordered === false ? '' : i + 1}</div>
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
  // Portrait value size is LENGTH-AWARE (2026-08-11), the same idiom CvgPunch and CvgCta
  // already use. A flat bump big enough to fix FTT's ~60-char halves pushed FMF's ~75-char
  // halves to within 30px of the frame edge. Both sides step together off the LONGER
  // value so the two halves never render at different sizes.
  const vMax = Math.max(String(L.value || '').length, String(R.value || '').length);
  const pSize = vMax > 70 ? 0.056 : 0.066;
  const Side: React.FC<{d: any; e: number; side: 'l' | 'r'}> = ({d, e, side}) => (
    <div style={{
      // `flex: 1` is right in LANDSCAPE, where the container is a row and this makes two
      // equal-width columns. In PORTRAIT the container is a column, so flex:1 made each
      // side grow to fill half the available HEIGHT and then centre ~247px of content
      // inside a ~680px box: about 216px of dead ground above AND below each side, which
      // is what produced the ~435px chasm between the two halves (measured, FWF
      // 2026-08-30 s3). Portrait sides are now content-height and the separation is an
      // explicit gap on the container, so it is a design number instead of a leftover.
      flex: portrait ? '0 0 auto' : 1,
      // Content-height sides no longer stretch on the cross axis, so state the width or
      // a long value sizes to max-content and stops wrapping the way it does today.
      width: portrait ? '100%' : undefined,
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      transform: `translateY(${(1 - e) * 24}px)`, opacity: e,
      // Wider side gutter on portrait: at the bumped size a long value otherwise kisses
      // the frame edge (FMF proof, 2026-08-11).
      padding: `0 ${width * (portrait ? 0.05 : 0.03)}px`,
    }}>
      <div style={{
        // Same class as a kicker — a short uppercase label with tracking — so it takes
        // the same sizer (2026-08-30 audit). It was M * 0.028, about 30px at 1080 and
        // roughly 10.8pt on a phone, sitting under a 60-71px value: the kicker bug in a
        // second place. Compare slides appear about once per deck (237 across 236), so
        // this is not an edge case. kickerSize keeps it length-aware and floors it at
        // the old size, so no label shrinks.
        fontFamily: BRAND.font, fontWeight: 800,
        fontSize: kickerSize(d.title || d.label || '', M, width, portrait), letterSpacing: 4,
        textTransform: 'uppercase', color: d.kind === 'bad' ? (W.neutral ?? `${W.ink}8A`) : W.accent, marginBottom: M * 0.018,
        // `label` accepted alongside `title` (2026-08-30). A survey of 440 decks found
        // `title` used 702 times and `label` 12, all in recent FWF dailies — those
        // episodes shipped compare slides with NO labels at all, because an unread key
        // becomes '' and prints nothing. CvgList already accepts `it.title || it.label`,
        // so this only brings CvgCompare in line with a convention the deck authors were
        // reasonably already using.
      }}>{d.title || d.label || ''}</div>
      <div style={{
        // Portrait halves are short AND sit above the caption band — 0.072 wrapped long
        // values into the captions (operator screenshot, FMF 4:5). Stepped down on
        // portrait for that, then partly back up 2026-08-11: 0.054 was over-corrected and
        // read as tiny type floating in clear space (operator, FTT 08-11 slide 2). The
        // caption clearance now comes from the container's bottom padding, not from
        // shrinking the type.
        fontFamily: BRAND.font, fontWeight: 900, fontSize: M * (portrait ? pSize : 0.072), lineHeight: 1.08,
        color: W.ink, textAlign: 'center', opacity: d.kind === 'bad' ? 0.62 : 1,
        // `text` accepted alongside `value` for the same reason. FMF 2026-08-28 s12
        // authored `label` + `text`, so NEITHER key was read and the whole compare slide
        // rendered as a divider and two underlines with no words on it. That shipped.
      }}>{d.value || d.text || ''}</div>
      <div style={{
        marginTop: M * 0.026, width: '46%', height: M * 0.011,
        background: d.kind === 'bad' ? (W.neutral ?? `${W.ink}8A`) : W.accent, transform: `scaleX(${e})`,
      }} />
    </div>
  );
  return (
    <AbsoluteFill>
      <Set src={fields.set} anchor={fields.anchor} />
      <AbsoluteFill style={{background: 'rgba(242,237,224,.70)'}} />
      {fields.kicker ? (
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'flex-start',
                              paddingTop: height * (portrait ? 0.07 : 0.1)}}>
          <div style={{
            fontFamily: BRAND.font, fontWeight: 800, fontSize: kickerSize(fields.kicker, M, width, portrait), letterSpacing: 5,
            textTransform: 'uppercase', color: W.accent,
          }}>{fields.kicker}</div>
        </AbsoluteFill>
      ) : null}
      <AbsoluteFill style={{flexDirection: portrait ? 'column' : 'row', alignItems: 'center',
                            justifyContent: 'center',
                            // The separation between the two halves, now that they are
                            // content-height. Big enough to read as two things, small
                            // enough that they read as one comparison.
                            gap: portrait ? height * 0.045 : 0,
                            // Bottom padding clears the caption band on portrait (the pill
                            // sits in the lower ~16% and ate the second side's last line).
                            // Top padding tightened 2026-08-11 so the kicker and the first
                            // half stop reading as two disconnected blocks, and again
                            // 2026-08-30: with content-height sides the pair centres as a
                            // group, so the old 0.10 pushed it low and left a wide empty
                            // strip under the kicker.
                            padding: portrait ? `${height * 0.06}px 0 ${height * 0.19}px` : 0}}>
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
            fontFamily: BRAND.font, fontWeight: 800, fontSize: kickerSize(fields.kicker, M, width, portrait), letterSpacing: 5,
            textTransform: 'uppercase', color: W.accent,
          }}>{fields.kicker}</div>
        </AbsoluteFill>
      ) : null}
      <AbsoluteFill style={portrait
        ? {flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: height * 0.012,
           paddingBottom: height * 0.18}
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
      <AbsoluteFill style={{alignItems: 'flex-start', justifyContent: 'center',
                            padding: portrait
                              ? `0 ${width * 0.09}px ${height * 0.18}px`
                              : `0 ${width * 0.09}px`}}>
        {fields.kicker ? (
          <div style={{
            fontFamily: BRAND.font, fontWeight: 800, fontSize: kickerSize(fields.kicker, M, width, portrait), letterSpacing: 5,
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

// reframe -> the beat where a sentence changes. The Paper* family does this on two
// stacked cards (PaperReframe); here the paper IS the slide, so the old phrase is struck
// with an accent strip laid straight on the scene and the new line lands beneath it.
//
// Why this exists (2026-08-20): `reframe` had no branch in `_circumvent_scene` at all and
// fell through to the CvgScene catch-all, which prints only `headline` — so before/strike/
// after were dropped and the slide held the frame showing a kicker and nothing else. TTD
// 2026-08-13 s8 shipped into the blocked state that way (~5.9s of empty card at the exact
// beat the episode pivots on). Same defect class as the stat/statgrid drop fixed
// 2026-08-12; the catch-all has now swallowed three types, so anything added to the deck
// vocabulary needs a branch here, not a fall-through.
//
// All three authored fields render, which the Paper* version does not do — PaperReframe
// accepts `strike` and never draws it, striking the whole `before` line instead. The
// three-part reading is what the decks actually author: `before` is the lead-in that
// stands, `strike` is the phrase being negated, `after` is what replaces it. A deck that
// omits `strike` falls back to the two-part reading and strikes `before` itself.
export const CvgReframe: React.FC<{fields: any}> = ({fields}) => {
  const W = useWorld();
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const cf = fields.cueFrames || {};
  const at = cf.in ?? 3;
  const hit = cf.hit ?? at + 2;
  const e = ease(frame, at);
  // the strip draws across the old phrase, then the new line lands on the beat
  const struck = interpolate(frame, [hit + 12, hit + 22], [0, 1],
                             {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const land = ease(frame, hit + 24, 16);
  const portrait = height > width;
  const M = Math.min(width, height);
  const TS = portrait ? 1.18 : 1;
  const P = paperRgb(W.paper);
  const before = fields.before || '';
  const strikeText = fields.strike || '';
  const afterText = fields.after || '';
  // Length-aware sizing, the idiom SceneType / CvgPunch / CvgCta already use: step down
  // rather than overrun the block box. Tuned against 4:5, the binding aspect.
  const fit = (s: string, base: number) => {
    const n = (s || '').length;
    const f = n <= 40 ? 1 : n <= 90 ? 0.8 : n <= 150 ? 0.64 : n <= 230 ? 0.52 : 0.44;
    return M * base * f * TS;
  };
  // With no `strike` authored, the struck phrase IS `before` (PaperReframe's reading).
  const leadLine = strikeText ? before : '';
  const struckLine = strikeText || before;
  return (
    <AbsoluteFill>
      <Set src={fields.set} anchor={fields.anchor} />
      <Cutouts items={fields.props} />
      <AbsoluteFill style={{
        background: `linear-gradient(180deg, rgba(${P},0) 0%, rgba(${P},.76) 22%, rgba(${P},.76) 78%, rgba(${P},0) 100%)`,
        opacity: 0.98,
      }} />
      <AbsoluteFill style={{
        alignItems: 'flex-start', justifyContent: 'center',
        padding: portrait
          ? `${height * 0.085}px ${width * 0.075}px ${height * 0.18}px`
          : `${height * 0.085}px ${width * 0.075}px`,
      }}>
        <div style={{
          maxWidth: width * (portrait ? 0.85 : 0.62),
          transform: `translateY(${(1 - e) * 22}px)`, opacity: e,
        }}>
          {fields.kicker ? (
            <div style={{
              fontFamily: BRAND.font, fontWeight: 800, fontSize: kickerSize(fields.kicker, M, width, portrait), letterSpacing: 5,
              textTransform: 'uppercase', color: W.accent, marginBottom: M * 0.016,
            }}>{fields.kicker}</div>
          ) : null}
          {leadLine ? (
            <div style={{
              fontFamily: BRAND.font, fontWeight: 900, fontSize: fit(leadLine, 0.046),
              lineHeight: 1.1, color: W.ink, letterSpacing: -0.5, marginBottom: M * 0.018,
            }}>{leadLine}</div>
          ) : null}
          {struckLine ? (
            <div style={{
              display: 'inline-block', position: 'relative',
              fontFamily: BRAND.font, fontWeight: 900, fontSize: fit(struckLine, 0.056),
              lineHeight: 1.1, color: W.ink, letterSpacing: -0.5,
              opacity: interpolate(struck, [0, 1], [1, 0.42]),
            }}>
              {struckLine}
              {/* an accent strip laid over the phrase, not a text-decoration: it has to
                  read as something placed on the scene, in the world's annotation color */}
              <div style={{
                position: 'absolute', left: 0, top: '54%', width: '100%',
                height: Math.max(3, M * 0.008), background: W.accent, borderRadius: 2,
                transform: `scaleX(${struck.toFixed(3)})`, transformOrigin: 'left center',
              }} />
            </div>
          ) : null}
          {afterText ? (
            <div style={{
              fontFamily: BRAND.font, fontWeight: 900, fontSize: fit(afterText, 0.068),
              lineHeight: 1.06, color: W.ink, letterSpacing: -0.5,
              marginTop: M * 0.026,
              transform: `translateY(${(1 - land) * 18}px)`, opacity: land,
            }}>{colorize(afterText, fields.accent, W.accent)}</div>
          ) : null}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
