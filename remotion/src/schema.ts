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
  // Chibi presenter pose for this scene: the staged filename in the public dir. The
  // engine assigns one to EVERY scene (authored `chibi` on the deck slide, else the
  // neutral rotation) — see remotion_engine._assign_chibi.
  chibi: z.string().optional(),
  chibiFlip: z.boolean().optional(),
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
  audioFrom: z.number().default(0), // narration starts here (frames) — leaves room for an intro sting
  // Visual world. '' (default) = the navy studio world. 'paper' = the Cut & Bond
  // off-white paper world (PaperBackground + ink-on-paper captions). Set per project.
  theme: z.string().default(''),
  // Optional caption active-word color (e.g. the element's category accent). Empty ->
  // the theme default (navy: green, paper: coral).
  captionAccent: z.string().default(''),
  // Chibi presenter layer (operator directive 2026-08-07). charHeightFrac is the
  // CHARACTER's height as a fraction of frame height (brand spec: 0.18-0.22), not the
  // pose canvas — the canvas carries transparent padding and a common foot baseline.
  presenter: z
    .object({
      enabled: z.boolean().default(false),
      charHeightFrac: z.number().default(0.18),
    })
    .optional(),
});

export type VideoProps = z.infer<typeof videoSchema>;
export type Word = z.infer<typeof wordSchema>;
