import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile} from 'remotion';
import type {VideoProps} from './schema';
import {Background} from './components/Background';
import {Captions} from './components/Captions';
import {KineticHook} from './components/KineticHook';
import {StatCounter} from './components/StatCounter';
import {TalkingScene} from './components/TalkingScene';

// scene component registry (motion-playbook §2). Unknown component -> TalkingScene.
const REGISTRY: Record<string, React.FC<any>> = {
  KineticHook,
  StatCounter,
  TalkingScene,
};

export const Video: React.FC<VideoProps> = (props) => {
  const {audio, words, scenes, captionBottomPx, captionFontSize} = props;
  return (
    <AbsoluteFill>
      <Background />
      {scenes.map((scene, i) => {
        const Comp = REGISTRY[scene.component] || TalkingScene;
        return (
          <Sequence key={i} from={scene.from} durationInFrames={scene.durationInFrames} layout="none">
            <Comp fields={scene.fields || {}} durationInFrames={scene.durationInFrames} />
          </Sequence>
        );
      })}
      <Captions words={words} bottomPx={captionBottomPx} fontSize={captionFontSize} />
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};
