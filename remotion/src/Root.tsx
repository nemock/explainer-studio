import React from 'react';
import {Composition, Still} from 'remotion';
import {Video} from './Video';
import {videoSchema, type VideoProps} from './schema';
import {Thumbnail, thumbnailSchema} from './Thumbnail';
import {PaperSting} from './components/PaperSting';
import {KeepCard} from './components/KeepCard';

// Single parametric composition. The Python engine passes the whole motion spec as
// props (--props=spec.json) and dimensions/duration come from those props.
export const RemotionRoot: React.FC = () => {
  return (
    <>
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
        audioFrom: 0,
      }}
      calculateMetadata={({props}: {props: VideoProps}) => ({
        durationInFrames: props.durationInFrames,
        width: props.width,
        height: props.height,
        fps: props.fps,
      })}
    />
    <Still
      id="Thumbnail"
      component={Thumbnail}
      schema={thumbnailSchema}
      width={1280}
      height={720}
      defaultProps={{
        bands: ['MY REAL', 'AI STACK'],
        sub: 'and where it breaks',
        accent: ['where it breaks'],
        cutout: 'headshot.png',
        mirror: false,
        innerHot: '#123a4a',
        bandSize: 104,
      }}
    />
    <Composition
      id="PaperSting"
      component={PaperSting}
      durationInFrames={120}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{}}
    />
    <Composition
      id="KeepCard"
      component={KeepCard}
      durationInFrames={60}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{fields: {image: 'keep_direction.png', label: 'DIRECTION', sub: 'the calls about where the whole thing is pointed'}}}
    />
    </>
  );
};
