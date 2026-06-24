import React from 'react';
import {Composition} from 'remotion';
import {Short} from './Short';
import {DataViz} from './DataViz';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* create-lock-in Short: 45.71s @ 30fps, 9:16 */}
      <Composition id="Short" component={Short} durationInFrames={1372} fps={30} width={1080} height={1920} />
      {/* Project Vend data-viz beat: 32.94s @ 30fps, 16:9 */}
      <Composition id="DataViz" component={DataViz} durationInFrames={989} fps={30} width={1920} height={1080} />
    </>
  );
};
