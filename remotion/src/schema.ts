import {z} from 'zod';

// One aligned word (rebased to 0 at the clip start).
export const wordSchema = z.object({
  word: z.string(),
  start: z.number(),
  end: z.number(),
});

// One visual scene: a component name + its time window + its data fields.
// `fields` is intentionally permissive — each component validates its own shape.
export const sceneSchema = z.object({
  component: z.string(),
  from: z.number(), // start frame
  durationInFrames: z.number(),
  fields: z.any().default({}),
});

// The whole motion spec. The Python engine writes this as the Remotion props file.
export const videoSchema = z.object({
  width: z.number().default(1080),
  height: z.number().default(1920),
  fps: z.number().default(30),
  durationInFrames: z.number().default(300),
  audio: z.string().default(''), // filename inside the --public-dir
  words: z.array(wordSchema).default([]),
  scenes: z.array(sceneSchema).default([]),
  captionBottomPx: z.number().default(160),
  captionFontSize: z.number().default(56),
});

export type VideoProps = z.infer<typeof videoSchema>;
export type Word = z.infer<typeof wordSchema>;
