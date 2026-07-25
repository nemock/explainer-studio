import React from 'react';
import {AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame} from 'remotion';
import type {VideoProps} from './schema';
import {Background} from './components/Background';
import {PaperBackground} from './components/PaperBackground';
import {Captions} from './components/Captions';
import {KineticHook} from './components/KineticHook';
import {StatCounter} from './components/StatCounter';
import {StatGrid} from './components/StatGrid';
import {TalkingScene} from './components/TalkingScene';
import {Hero3D} from './components/Hero3D';
import {KineticHeadline, DefineTerm, Quote, PunchWord, Reframe, BuildList, SideBySide, Timeline} from './components/TextScenes';
import {Figure, Footage} from './components/Media';
import {AnnotateOverlay} from './components/Annotate';
import {Schematic} from './components/Schematic';
import {CTA} from './components/CTA';
import {BrandSting, StepFlow} from './components/Extras';
import {PaperSting} from './components/PaperSting';
import {KeepCard} from './components/KeepCard';
import {PaperHook} from './components/PaperHook';
import {PaperSetHook, PaperPopCard, PaperCounter} from './components/PaperSet';
import {PaperStatement, PaperDefine, PaperPunch} from './components/PaperText';
import {PaperStairs, PaperCompare, PaperSteps, PaperList, PaperBookCTA} from './components/PaperData';
import {TearReveal} from './components/PaperWorld';
import {DrawLine, Waterfall, Pictograph, Ring, Funnel} from './components/DataViz2';
import {ReactiveStrip, Waveform} from './components/Audio';
import {PaperAtom, ElementStat, DiscoveryCard, PeriodicSlot, PaperWord, PaperFire, PaperProp, PaperCTA, PaperMolecule} from './components/Chem';
import {InkProvider, isPaperTheme} from './ink';

// the component catalog (motion-playbook §2). Unknown -> TalkingScene (captions-led).
const REGISTRY: Record<string, React.FC<any>> = {
  Hero3D,
  BrandSting,
  PaperSting,
  KeepCard,
  PaperHook,
  // Papercraft Motion (papercraft-motion-spec.md; migration map in
  // papercraft-motion-migration.md §3)
  PaperSetHook,
  PaperPopCard,
  PaperCounter,
  PaperStatement,
  PaperDefine,
  PaperPunch,
  PaperStairs,
  PaperCompare,
  PaperSteps,
  PaperList,
  PaperBookCTA,
  StepFlow,
  DrawLine,
  Waterfall,
  Pictograph,
  Ring,
  Funnel,
  Waveform,
  KineticHook,
  KineticHeadline,
  DefineTerm,
  StatCounter,
  StatGrid,
  Quote,
  PunchWord,
  Reframe,
  BuildList,
  SideBySide,
  Timeline,
  Figure,
  Footage,
  Schematic,
  CTA,
  // Cut & Bond paper chemistry kit
  PaperAtom,
  ElementStat,
  DiscoveryCard,
  PeriodicSlot,
  PaperWord,
  PaperFire,
  PaperProp,
  PaperCTA,
  PaperMolecule,
  TalkingScene,
};

// motivated cross-fade so beats connect instead of hard-cutting (timing stays exact:
// scenes keep their absolute from/duration; only opacity ramps).
const SceneWrap: React.FC<{durationInFrames: number; paper?: boolean; tear?: string | null; children: React.ReactNode}> = ({durationInFrames, paper, tear, children}) => {
  const frame = useCurrentFrame();
  const f = 7;
  const opacity = interpolate(
    frame,
    [0, f, durationInFrames - f, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );
  // warm light-leak flash on entrance (motion-playbook §2G) — a touch of produced polish.
  // Skipped in the paper world: a screen-blend flash blows out an off-white surface.
  const leak = interpolate(frame, [0, 5, 16], [0, 0.4, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  // No global paper "breathe"/drift. An earlier attempt drifted the whole content layer to
  // satisfy the QA freeze detector; on BOTH paper channels it read as the frame swirling —
  // Cut & Bond called it a "ship-on-water" bob, and the deep dives made a viewer nauseous
  // (operator feedback 2026-07-16). Paper stays STILL by design; motion comes only from each
  // component's own entrance + narration-cued annotations. The QA dead-air warning on held
  // cards is an accepted trait of the calm paper aesthetic, not a defect to animate away.
  return (
    <AbsoluteFill style={{opacity: tear ? 1 : opacity}}>
      {children}
      {paper ? null : (
        <AbsoluteFill style={{background: 'radial-gradient(60% 50% at 68% 28%, rgba(255,205,130,.5) 0%, rgba(255,205,130,0) 70%)', mixBlendMode: 'screen', opacity: leak, pointerEvents: 'none'}} />
      )}
      {/* act-boundary tear (papercraft-motion-spec.md §4): the incoming scene is revealed
          as two ink halves part along a seeded seam; replaces the cross-fade for this scene */}
      {tear ? <TearReveal seed={tear} /> : null}
    </AbsoluteFill>
  );
};

export const Video: React.FC<VideoProps> = (props) => {
  const {audio, words, scenes, captionBottomPx, captionFontSize, audioFrom, width, height, theme, captionAccent} = props;
  // Paper worlds: 'nemock-deep-dive' (Dave's deep dives) and 'cut-bond' (Cut & Bond).
  // Everything else ('midnight', the ISO 14971 series) keeps the navy brand.
  const paper = isPaperTheme(theme);
  // In portrait (Shorts), centered scene content collides with the burned-in captions
  // in the lower third while the top sits empty. Reserve the caption zone so content
  // centers in the upper area. Cut & Bond reserves MORE (operator 2026-07-16: push the
  // animation up into the top two-thirds, let captions drop low). Landscape (deep dives)
  // is unaffected (inset = 0).
  // Portrait (Shorts): reserve the bottom THIRD for captions and let the scene content live
  // in the upper two-thirds, so a single element settles around the top-third line instead of
  // being pinned high with a dead middle (operator direction 2026-07-16). Landscape = 0.
  const contentBottom = height > width ? Math.round(height * (theme === 'cut-bond' ? 0.36 : 0.34)) : 0;
  return (
    <InkProvider theme={theme}>
    <AbsoluteFill style={{backgroundColor: paper ? '#f4ecd6' : '#090d1c'}}>
      {paper ? <PaperBackground /> : <Background />}
      {scenes.map((scene, i) => {
        const Comp = REGISTRY[scene.component] || TalkingScene;
        return (
          <Sequence key={i} from={scene.from} durationInFrames={scene.durationInFrames} layout="none">
            <SceneWrap durationInFrames={scene.durationInFrames} paper={paper} tear={(scene as any).tear ? `tear${i}` : null}>
              <AbsoluteFill style={{bottom: contentBottom}}>
                <Comp fields={scene.fields || {}} durationInFrames={scene.durationInFrames} sceneFrom={scene.from} audioFrom={audioFrom} />
              </AbsoluteFill>
              {/* narration-cued hand-drawn annotations (motion-playbook §2H) — full-frame
                  coordinate space, on top of the scene, under the captions */}
              {(scene as any).annotations?.length ? <AnnotateOverlay annotations={(scene as any).annotations} /> : null}
            </SceneWrap>
          </Sequence>
        );
      })}
      {audio && !paper ? <ReactiveStrip audio={audio} audioFrom={audioFrom || 0} /> : null}
      <Captions words={words} bottomPx={captionBottomPx} fontSize={captionFontSize} theme={theme} accentColor={captionAccent} />
      {audio ? (
        <Sequence from={audioFrom || 0} layout="none">
          <Audio src={staticFile(audio)} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
    </InkProvider>
  );
};
