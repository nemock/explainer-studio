import React from 'react';
import {Composition} from 'remotion';
import {Video} from './Video';
import {videoSchema} from './schema';

// Single parametric composition. The Python engine passes the whole motion spec as
// props (--props=spec.json) and dimensions/duration come from those props.
export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Video"
      component={Video}
      schema={videoSchema}
      durationInFrames={90}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        width: 1080,
        height: 1920,
        fps: 30,
        durationInFrames: 90,
        audio: '',
        words: [],
        scenes: [
          {component: 'KineticHook', from: 0, durationInFrames: 90, fields: {kicker: 'Preview', headline: 'Motion engine', accent: ['engine']}},
        ],
        captionBottomPx: 230,
        captionFontSize: 62,
      }}
      calculateMetadata={({props}) => ({
        durationInFrames: props.durationInFrames,
        width: props.width,
        height: props.height,
        fps: props.fps,
      })}
    />
  );
};
