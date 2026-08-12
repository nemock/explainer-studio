import React from 'react';
import {Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

// ChibiPresenter — the operator as a small paper-cutout presenter, on EVERY scene.
//
// v2 (2026-08-07, same day): the presenter is an OVERLAY IN the scene, not a lane
// BESIDE it. v1 scaled the whole content layer left to reserve him a strip of cream,
// and the operator rejected it on sight: "it looks clumsy how the actual scene has now
// simply been reduced, and effectively the character is standing offstage. They look
// like they are very separate items and have no relationship to each other." The scene
// now fills the frame exactly as it did before the presenter existed, and he stands in
// a bottom corner ON TOP of it — small, part of the action, not staging beside it.
//
// The operator's rules, and how each is kept:
//
//  1. "Part of the action, not randomly chosen" — the character must FACE THE CONTENT.
//     A pose that points or looks off-frame reads as a mistake (his screenshot: the
//     pointing pose on the right edge, pointing further right at nothing). The engine
//     knows each pose's facing and either seats him on the side where his gesture aims
//     inward, or mirrors him (`flip`) so it does — the operator's own suggested fixes.
//  2. "Always on top" — mounted by Video.tsx after captions, above everything.
//  3. "Never obscuring any important part of the visual" — no reserved lane anymore, so
//     this is now placement, not layout: the engine picks the emptier bottom corner per
//     scene (schematic nodes, figure marks — see _chibi_side) and a deck slide can
//     override with `chibiSide`. He is small (18-22% of frame height) and the paper
//     compositions keep their lower corners quiet by design.
//  4. Margin above the captions — feet sit above the caption block's top line plus a
//     gap, so a caption can never touch him.
export const CANVAS_ASPECT = 2720 / 2400; // normalized pose canvas, measured
export const CHAR_FRAC_OF_CANVAS = 0.912; // character height / canvas height, all 72 poses
export const EDGE_FRAC = 0.015; // horizontal inset from the frame edge

export const ChibiPresenter: React.FC<{
  pose: string;
  charHeightFrac: number;
  captionTopPx: number;
  side?: 'left' | 'right';
  flip?: boolean;
}> = ({pose, charHeightFrac, captionTopPx, side = 'right', flip}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  if (!pose) return null;

  const canvasH = (charHeightFrac / CHAR_FRAC_OF_CANVAS) * height;
  const canvasW = canvasH * CANVAS_ASPECT;
  // captionTopPx = distance from the frame bottom to the caption block's top line.
  const bottom = captionTopPx + height * 0.012;
  const inset = width * EDGE_FRAC;

  // Stop-motion settle: the cutout drops its last few pixels and holds. This is the
  // only motion he carries — paper stays still by design (Video.tsx).
  const drop = interpolate(frame, [0, 6], [height * 0.012, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const opacity = interpolate(frame, [0, 3], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        ...(side === 'left' ? {left: inset} : {right: inset}),
        bottom,
        width: canvasW,
        height: canvasH,
        opacity,
        transform: `translateY(${drop}px)${flip ? ' scaleX(-1)' : ''}`,
        pointerEvents: 'none',
      }}
    >
      <Img
        src={staticFile(pose)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          filter: `drop-shadow(0 ${height * 0.006}px ${height * 0.008}px rgba(90,70,40,.28))`,
        }}
      />
    </div>
  );
};
