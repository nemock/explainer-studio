import React from 'react';
import {AbsoluteFill, Easing, Img, Video, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useInk} from '../ink';

// The on-camera cold open — real Dave inside the paper world.
// Spec: references/paper-world/ON-CAMERA-COLD-OPEN.md (operator directive 2026-08-12).
//
// WHY A HOLE AND NOT AN OVERLAY. Dave's brief turns on one sentence: "the monitor's screen
// is a cutout — a hole in the papercraft with the real video behind it, inset a couple of
// pixels so the paper bezel casts its usual soft shadow over the footage edge. The seam is
// the whole illusion; do not butt them flush." Compositing footage ON TOP of a green
// rectangle cannot produce that seam — the video's hard edge lands over the paper and the
// bezel never overlaps it. So `tools/key_screen.py` cuts a genuinely transparent hole in
// the plate, and the layer order here puts the paper ABOVE the footage. The bezel's own
// antialiased edge then falls across the video, which is the entire effect.
//
// WHY THE CAMERA MOVES RATHER THAN CUTS. Same spec: "Do not cut. Pull back and out." The
// scene rests pushed in far enough that the screen fills `screenWidthFrac` of the frame
// (Dave: "most of the screen"), then retreats to the full desk over the last beat so the
// next slide arrives in the space that opens. A hard cut would throw away the reason for
// building the set at all.
//
// CONTINUITY ACROSS SCENES. The cold open spans more than one script segment, and the deck
// is 1:1 with segments, so the same take plays across consecutive scenes. `startAtSec` is
// the offset into the source file for THIS scene; remotion_engine computes it from the
// scene's narration start so the take runs continuously instead of restarting each slide.
//
// The chibi presenter is excluded on these scenes — real Dave and a cartoon Dave in one
// frame is two versions of the same person (spec, "The chibi presenter is EXCLUDED").

type Rect = {x0: number; y0: number; x1: number; y1: number};

const DEFAULT_SCREEN: Rect = {x0: 0.243, y0: 0.146, x1: 0.754, y1: 0.636};

export const PaperMonitor: React.FC<{fields: any}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, width, height, durationInFrames} = useVideoConfig();
  const ink = useInk();

  const plate: string = fields.set || 'papercraft/desk_monitor.png';
  const video: string | undefined = fields.video;
  const s: Rect = fields.screen || DEFAULT_SCREEN;

  const cx = (s.x0 + s.x1) / 2;
  const cy = (s.y0 + s.y1) / 2;
  const sw = s.x1 - s.x0;
  const sh = s.y1 - s.y0;

  // Rest framing: push in until the screen occupies `screenWidthFrac` of the frame.
  // Dave's brief is 55-70%; below ~half it reads as a picture-in-picture gimmick, above
  // ~three quarters the paper stops registering.
  const targetW: number = fields.screenWidthFrac ?? 0.62;
  const restScale = targetW / sw;

  // The retreat. Only the LAST on-camera scene sets pullBack — the earlier ones hold.
  const pullFrames = fields.pullBack ? Math.round((fields.pullBackSecs ?? 1.8) * fps) : 0;
  const pullStart = Math.max(0, durationInFrames - pullFrames);
  const ease = Easing.bezier(0.16, 1, 0.3, 1);

  // House "breathing" so the shot is never dead-static (motion-playbook §1).
  const breathe = interpolate(frame, [0, durationInFrames], [1, 1.02], {extrapolateRight: 'clamp'});
  // retreat 1 -> 1/restScale, i.e. all the way back to the plate's own framing
  const retreat = pullFrames
    ? interpolate(frame, [pullStart, durationInFrames - 1], [1, 1 / restScale],
                  {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease})
    : 1;
  // ...and un-centre in step, so we end on the whole desk rather than a shifted crop
  const centring = pullFrames
    ? interpolate(frame, [pullStart, durationInFrames - 1], [1, 0],
                  {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease})
    : 1;

  const scale = restScale * breathe * retreat;
  const tx = (0.5 - cx) * width * centring;
  const ty = (0.5 - cy) * height * centring;

  const pct = (v: number) => `${v * 100}%`;
  // The footage is laid a little WIDER than the hole so its own edge finishes underneath
  // the paper — that overlap is the seam the spec asks for, and it also guarantees no
  // sliver of background can show at the corners.
  //
  // 0.012 rather than a hairline: at 0.004 the placeholder's edge marker was still
  // visible inside the hole on a rendered still (navy | edge | footage, with the bezel
  // touching the footage instead of covering it). ~23px of overlap at 1920 costs nothing
  // but the outermost pixels of the take, which is exactly why the spec says to shoot
  // "flat and slightly wide so the crop into the monitor's aspect does not cut his head".
  const bleed: number = fields.bleed ?? 0.012;
  // paper stuck on the glass: [{image, at:[x,y], w, rotate?, tint?}] in plate space
  const patches: any[] = fields.patches ?? [];

  // The backdrop is a safety net only: the camera never scales below 1.0, so the plate
  // always covers the frame. It exists so a mis-authored `screenWidthFrac` shows paper
  // rather than black.
  return (
    <AbsoluteFill style={{backgroundColor: ink.paper ? '#f4ecd6' : '#0d1428', overflow: 'hidden'}}>
      <AbsoluteFill
        style={{
          // scale about the screen's own centre, then slide that centre to frame centre
          transformOrigin: `${cx * 100}% ${cy * 100}%`,
          transform: `translate(${tx}px, ${ty}px) scale(${scale})`,
        }}
      >
        {/* 1. the footage, clipped to the screen rect — BELOW the paper.
               `zIndex` is load-bearing, not decoration. This div is positioned and the
               plate below is an in-flow <Img>, and CSS paints positioned boxes ABOVE
               in-flow ones whatever the source order says — so without explicit z-index
               the footage renders ON TOP of the paper and the bezel never overlaps it.
               That cost two rounds of chasing a phantom geometry error here; the giveaway
               was that widening the bleed made the leak slightly WORSE rather than better.
               `isolation` keeps the grade's blend modes from reaching the paper too. */}
        <div
          style={{
            position: 'absolute', zIndex: 1, isolation: 'isolate',
            left: pct(s.x0 - bleed), top: pct(s.y0 - bleed),
            width: pct(sw + bleed * 2), height: pct(sh + bleed * 2),
            overflow: 'hidden',
            background: '#e9e0c8', // a blank paper screen if no take is wired up yet
          }}
        >
          {video ? (
            <Video
              src={staticFile(video)}
              muted
              trimBefore={Math.round((fields.startAtSec ?? 0) * fps)}
              style={{
                width: '100%', height: '100%', objectFit: 'cover',
                // grade toward the world: desaturate a little, soften contrast, warm it.
                // "Do not stylise or posterise — it will actually be me."
                filter: 'saturate(0.94) contrast(0.93) brightness(1.04)',
              }}
            />
          ) : null}

          {/* lift the blacks so the footage sits against cream instead of punching a
              hole in it — a screen blend raises the shadows without touching highlights */}
          <AbsoluteFill style={{background: '#f4ecd6', mixBlendMode: 'screen', opacity: 0.10}} />
          {/* and a gentle warm cast on top of that */}
          <AbsoluteFill style={{background: '#d8a24a', mixBlendMode: 'soft-light', opacity: 0.16}} />

          {/* 2. the bezel's shadow falling INTO the recess. This is the "inset a couple of
                 pixels" the spec asks for: the paper reads as sitting in front of the
                 footage, not flush against it. Heavier from the top, like every other
                 shadow in this world. */}
          <AbsoluteFill
            style={{
              boxShadow: `inset 0 ${height * 0.012}px ${height * 0.022}px rgba(20,12,40,.42),
                          inset 0 0 ${height * 0.010}px rgba(20,12,40,.30)`,
            }}
          />
        </div>

        {/* 3. the papercraft set, hole already cut, ON TOP of the footage.
               Positioned + z-index 2 so it genuinely wins the paint order (see above).
               The plate is cropped to the comp aspect by tools/key_screen.py, so `cover`
               is a no-op and the measured hole rect lines up with the footage exactly. */}
        <AbsoluteFill style={{zIndex: 2}}>
          <Img src={staticFile(plate)}
               style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </AbsoluteFill>

        {/* 4. `patches` — paper stuck ON the glass, above everything.
               A physical sticky note on a monitor sits on the screen, so this layer is
               above both the footage and the bezel and may overlap the frame, which is
               what sells it as an object in the room rather than a rectangle pasted on.
               Coordinates are PLATE space like `screen`, so a patch rides the camera and
               stays put on the monitor through the push-in and the pull-back.
               Built for #57, where the camera burned a maker's watermark into the top-left
               of the take and cropping it out would have cost half the frame width. */}
        {patches.map((p: any, i: number) => {
          const src = staticFile(p.image);
          const tint = p.tint ?? '#efe4c8';
          return (
            <div key={`patch${i}`} style={{
              position: 'absolute', zIndex: 3,
              left: pct(p.at[0]), top: pct(p.at[1]), width: pct(p.w),
              transform: `translate(-50%, -50%) rotate(${p.rotate ?? 0}deg)`,
              filter: 'drop-shadow(0 6px 12px rgba(20,12,40,.45))',
            }}>
              <div style={{position: 'relative'}}>
                {/* desaturate first: the library stock is generated yellow, and multiplying
                    straight over it lands somewhere other than the palette value asked for
                    (a pastel blue comes out sage). Same two-step as PaperNote. */}
                <Img src={src} style={{width: '100%', height: 'auto', display: 'block',
                                       filter: 'grayscale(1) brightness(1.18)'}} />
                {/* the multiply half, masked to the paper's own alpha so the tint stops at
                    the torn edge instead of painting a rectangle over the shot */}
                <div style={{
                  position: 'absolute', inset: 0, background: tint, mixBlendMode: 'multiply',
                  WebkitMaskImage: `url(${src})`, maskImage: `url(${src})`,
                  WebkitMaskSize: '100% 100%', maskSize: '100% 100%',
                  WebkitMaskRepeat: 'no-repeat', maskRepeat: 'no-repeat',
                }} />
              </div>
            </div>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
