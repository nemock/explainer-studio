import React from 'react';
import {AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame} from 'remotion';
import type {VideoProps} from './schema';
import {Background} from './components/Background';
import {Captions} from './components/Captions';
import {KineticHook} from './components/KineticHook';
import {StatCounter} from './components/StatCounter';
import {TalkingScene} from './components/TalkingScene';
import {Hero3D} from './components/Hero3D';
import {KineticHeadline, Quote, PunchWord, Reframe, BuildList, SideBySide, Timeline} from './components/TextScenes';
import {Figure, Footage} from './components/Media';
import {CTA} from './components/CTA';
import {BrandSting, StepFlow} from './components/Extras';
import {DrawLine, Waterfall, Pictograph, Ring, Funnel} from './components/DataViz2';

// the component catalog (motion-playbook §2). Unknown -> TalkingScene (captions-led).
const REGISTRY: Record<string, React.FC<any>> = {
  Hero3D,
  BrandSting,
  StepFlow,
  DrawLine,
  Waterfall,
  Pictograph,
  Ring,
  Funnel,
  KineticHook,
  KineticHeadline,
  StatCounter,
  Quote,
  PunchWord,
  Reframe,
  BuildList,
  SideBySide,
  Timeline,
  Figure,
  Footage,
  CTA,
  TalkingScene,
};

// motivated cross-fade so beats connect instead of hard-cutting (timing stays exact:
// scenes keep their absolute from/duration; only opacity ramps).
const SceneWrap: React.FC<{durationInFrames: number; children: React.ReactNode}> = ({durationInFrames, children}) => {
  const frame = useCurrentFrame();
  const f = 7;
  const opacity = interpolate(
    frame,
    [0, f, durationInFrames - f, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );
  // warm light-leak flash on entrance (motion-playbook §2G) — a touch of produced polish
  const leak = interpolate(frame, [0, 5, 16], [0, 0.4, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{opacity}}>
      {children}
      <AbsoluteFill style={{background: 'radial-gradient(60% 50% at 68% 28%, rgba(255,205,130,.5) 0%, rgba(255,205,130,0) 70%)', mixBlendMode: 'screen', opacity: leak, pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};

export const Video: React.FC<VideoProps> = (props) => {
  const {audio, words, scenes, captionBottomPx, captionFontSize, audioFrom} = props;
  return (
    <AbsoluteFill style={{backgroundColor: '#090d1c'}}>
      <Background />
      {scenes.map((scene, i) => {
        const Comp = REGISTRY[scene.component] || TalkingScene;
        return (
          <Sequence key={i} from={scene.from} durationInFrames={scene.durationInFrames} layout="none">
            <SceneWrap durationInFrames={scene.durationInFrames}>
              <Comp fields={scene.fields || {}} durationInFrames={scene.durationInFrames} />
            </SceneWrap>
          </Sequence>
        );
      })}
      <Captions words={words} bottomPx={captionBottomPx} fontSize={captionFontSize} />
      {audio ? (
        <Sequence from={audioFrom || 0} layout="none">
          <Audio src={staticFile(audio)} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};
