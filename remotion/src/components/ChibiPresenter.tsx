import React from 'react';
import {Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

// ChibiPresenter — the operator as a small paper-cutout presenter standing beside the
// content, on EVERY scene (operator directive 2026-08-07).
//
// Three rules the operator set, and how each is kept:
//
//  1. "The chibi should always be on top" — the viewer reads the presenter as Dave
//     presenting the information, so it renders ABOVE the scene, the annotations AND the
//     captions. Video.tsx mounts this layer last, after <Captions>.
//  2. "The chibi should never be obscuring content" — Video.tsx scales the whole content
//     layer to (1 - laneFrac) with a left origin, so no component can draw into the
//     presenter's lane. That is a guarantee from the layout, not a per-slide judgement.
//     Components position from useVideoConfig() rather than from their container, so an
//     inset would clip them; a transform preserves every component's internal pixel math.
//  3. "There should be a margin between the subtitles and the chibi" — the pose is
//     bottom-anchored ABOVE the caption block (its top edge, allowing two caption lines)
//     plus a margin, and Captions separately reserves the lane so a long caption can
//     never grow sideways under the presenter either.
//
// Geometry note: poses come from v2/poses_normalized_tight, where every pose is drawn on
// one 2720x2400 canvas at a common character size with feet on a common baseline. So the
// canvas is what gets positioned (that is what makes poses interchangeable), and the
// character occupies a measured ~0.912 of the canvas height. Sizing is expressed as the
// CHARACTER's height so "18-22% of frame height" in the brand doc means what it says.
export const CANVAS_ASPECT = 2720 / 2400; // 1.133
export const CHAR_FRAC_OF_CANVAS = 0.912; // measured across all 72 normalized poses
export const EDGE_FRAC = 0.012; // right margin from the frame edge
export const GUTTER_FRAC = 0.03; // clear space between content and the presenter

// Canvas width as a fraction of frame WIDTH, for a given character height (frac of HEIGHT).
export const canvasWidthFrac = (charHeightFrac: number, width: number, height: number) =>
  ((charHeightFrac / CHAR_FRAC_OF_CANVAS) * CANVAS_ASPECT * height) / width;

// The content layer is scaled to this so nothing can reach the presenter's lane.
export const laneFrac = (charHeightFrac: number, width: number, height: number) =>
  canvasWidthFrac(charHeightFrac, width, height) + GUTTER_FRAC;

export const ChibiPresenter: React.FC<{
  pose: string;
  charHeightFrac: number;
  captionTopPx: number;
  flip?: boolean;
}> = ({pose, charHeightFrac, captionTopPx, flip}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  if (!pose) return null;

  const canvasH = (charHeightFrac / CHAR_FRAC_OF_CANVAS) * height;
  const canvasW = canvasH * CANVAS_ASPECT;
  // captionTopPx is the distance from the frame BOTTOM to the top of the caption block.
  // Feet sit a clear margin above that line, so a caption can never reach the presenter.
  const bottom = captionTopPx + height * 0.012;
  const right = width * EDGE_FRAC;

  // Stop-motion settle: a hand-placed cutout drops the last few pixels and holds. Paper
  // stays still by design (Video.tsx), so this is the only motion the presenter carries.
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
        right,
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
          // grounds the cutout on the page like the other paper objects
          filter: `drop-shadow(0 ${height * 0.006}px ${height * 0.008}px rgba(90,70,40,.28))`,
        }}
      />
    </div>
  );
};
