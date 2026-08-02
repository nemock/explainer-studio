import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

// Papercraft STAGES — a scene with a blank surface that type is rendered onto
// (operator directive 2026-08-01: "a scene where a person is standing beside their laptop,
// projecting... we can probably have three or four or more different scenes where we can put
// this kind of text into a visually attractive scene").
//
// Same architecture rule as every other substrate: Magnific generates the BLANK scene,
// Remotion renders the type. No stage asset contains a word. What is new here is that a
// stage is not a surface the caller sizes — it is a whole 16:9 illustration with ONE region
// that happens to be empty, so each asset carries a measured `zone` and the type is placed
// into it.
//
// The stages are deliberately two-colour (cream + deep navy, no accent) so every paper world
// can use them without a tint step and without importing another world's accent.

export type StageName = 'whiteboard' | 'projector' | 'presentation' | 'easel';

// zone = the blank area, in 0-1 of the frame, measured off each rendered asset.
// Keep a little margin inside the real edge so descenders never touch a torn edge.
const STAGES: Record<StageName, {src: string; zone: {x: number; y: number; w: number; h: number}}> = {
  whiteboard:   {src: 'papercraft-stages/stage_whiteboard_1.png',   zone: {x: 0.225, y: 0.09, w: 0.63, h: 0.46}},
  projector:    {src: 'papercraft-stages/stage_projector_1.png',    zone: {x: 0.165, y: 0.08, w: 0.68, h: 0.44}},
  presentation: {src: 'papercraft-stages/stage_presentation_1.png', zone: {x: 0.355, y: 0.10, w: 0.57, h: 0.44}},
  easel:        {src: 'papercraft-stages/stage_easel_1.png',        zone: {x: 0.355, y: 0.11, w: 0.27, h: 0.52}},
};

export const isStageName = (s?: string): s is StageName =>
  !!s && Object.prototype.hasOwnProperty.call(STAGES, s);

/**
 * Fit a headline into a zone. The zone is a fixed pixel box, so the only free variable is
 * type size: estimate the area the string needs at a candidate size and step down until it
 * fits. Deterministic (pure function of text + box), so renders stay reproducible.
 */
const fitSize = (text: string, boxW: number, boxH: number) => {
  const chars = Math.max(1, (text || '').length);
  // ~0.52em average advance width for this weight, 1.12 line height
  for (let s = boxH * 0.30; s > boxH * 0.055; s *= 0.94) {
    const perLine = Math.max(1, Math.floor(boxW / (s * 0.52)));
    const lines = Math.ceil(chars / perLine);
    if (lines * s * 1.12 <= boxH) return s;
  }
  return boxH * 0.055;
};

/**
 * A stage scene with content placed in its blank region.
 *
 * The scene gets a very slow push-in so it never sits frozen (the same freezedetect concern
 * the text cards have), but the type is placed in UNSCALED frame space on top, because
 * scaling the type with the scene would make it drift out of the zone.
 */
export const PaperStage: React.FC<{
  stage: StageName;
  durationInFrames?: number;
  children?: React.ReactNode;
}> = ({stage, durationInFrames = 300, children}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const def = STAGES[stage] ?? STAGES.whiteboard;
  const live = interpolate(frame, [0, durationInFrames], [1, 1.03]);
  const z = def.zone;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{transform: `scale(${live})`}}>
        <Img src={staticFile(def.src)}
             style={{width: '100%', height: '100%', objectFit: 'cover', display: 'block'}} />
      </AbsoluteFill>
      <div style={{position: 'absolute',
                   left: z.x * width, top: z.y * height, width: z.w * width, height: z.h * height,
                   display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center'}}>
        {children}
      </div>
    </AbsoluteFill>
  );
};

export const stageZonePx = (stage: StageName, width: number, height: number) => {
  const z = (STAGES[stage] ?? STAGES.whiteboard).zone;
  return {w: z.w * width, h: z.h * height};
};

export {fitSize as fitStageText};
