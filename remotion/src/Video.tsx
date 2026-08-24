import React from 'react';
import {AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame} from 'remotion';
import type {VideoProps} from './schema';
import {Background} from './components/Background';
import {PaperBackground} from './components/PaperBackground';
import {Captions} from './components/Captions';
import {SourceLines} from './components/SourceLine';
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
import {BRGPaperSting} from './components/BRGPaperSting';
import {KeepCard} from './components/KeepCard';
import {PaperHook} from './components/PaperHook';
import {PaperMonitor} from './components/PaperMonitor';
import {PaperSetHook, PaperPopCard, PaperCounter} from './components/PaperSet';
import {PaperStatement, PaperDefine, PaperPunch, PaperReframe} from './components/PaperText';
// Circumvent scene family (2026-07-30): the paper IS the slide, no cards.
import {CvgScene, CvgPunch, CvgList, CvgCompare, CvgSteps, CvgDefine, CvgCta, CvgReframe} from './components/Circumvent';
import {PaperStairs, PaperCompare, PaperSteps, PaperList, PaperBookCTA} from './components/PaperData';
import {TearReveal} from './components/PaperWorld';
import {DrawLine, Waterfall, Pictograph, Ring, Funnel} from './components/DataViz2';
import {ReactiveStrip, Waveform} from './components/Audio';
import {PaperAtom, ElementStat, DiscoveryCard, PeriodicSlot, PaperWord, PaperFire, PaperProp, PaperFootage, PaperCTA, PaperMolecule, SketchbookPage} from './components/Chem';
import {InkProvider, isPaperTheme} from './ink';
import {WorldProvider} from './components/PaperWorld';
import {ChibiPresenter} from './components/ChibiPresenter';

// the component catalog (motion-playbook §2). Unknown -> TalkingScene (captions-led).
const REGISTRY: Record<string, React.FC<any>> = {
  Hero3D,
  BrandSting,
  PaperSting,
  BRGPaperSting,
  KeepCard,
  PaperHook,
  // on-camera cold open: real Dave behind a cut hole in the paper set
  PaperMonitor,
  // Papercraft Motion (papercraft-motion-spec.md; migration map in
  // papercraft-motion-migration.md §3)
  PaperSetHook,
  PaperPopCard,
  PaperCounter,
  PaperStatement,
  PaperDefine,
  PaperPunch,
  PaperReframe,
  CvgScene,
  CvgPunch,
  CvgCta,
  CvgList,
  CvgCompare,
  CvgSteps,
  CvgDefine,
  CvgReframe,
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
  PaperFootage,
  PaperCTA,
  PaperMolecule,
  SketchbookPage,
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

// Components that own the WHOLE FRAME — they paint their own full-bleed background (or are
// full-bleed art), and several already compose portrait themselves. The portrait caption
// reserve below is skipped for these: shrinking their box would crop the art or cut their
// background off in a hard line across the lower frame, and for the self-composing ones it
// would double-reserve space they already hold back.
//
//  - brand bumpers + full-bleed art/media: BrandSting, PaperSting, BRGPaperSting, PaperHook,
//    PaperSetHook, Hero3D, Footage
//  - self-composed portrait layouts: the Cvg* family (caption padding + stacked layouts),
//    KeepCard (shrinks and centres its own card in portrait)
//  - the papercraft table family: PaperTable IS their frame, so it must run edge to edge.
//    They hold the caption band back inside themselves instead — usePaperLayout's `reserve`,
//    plus min-dimension type and stacked portrait layouts (the pass they got 2026-08-07).
//
// Everything else (the Cut & Bond chemistry kit, figures, text scenes, data viz) lays content
// out on the page and lifts cleanly.
const FULL_BLEED = new Set([
  'BrandSting', 'PaperSting', 'BRGPaperSting', 'PaperHook', 'PaperMonitor', 'Hero3D', 'Footage', 'KeepCard',
  'CvgScene', 'CvgPunch', 'CvgCta', 'CvgList', 'CvgCompare', 'CvgSteps', 'CvgDefine', 'CvgReframe',
  'PaperSetHook', 'PaperPopCard', 'PaperCounter', 'PaperStatement', 'PaperDefine',
  'PaperPunch', 'PaperStairs', 'PaperCompare', 'PaperSteps', 'PaperList', 'PaperBookCTA',
]);

// Paper worlds whose sheet is BRG's cooler cream (#f5f0eb) rather than the FWF/nemock
// warm sheet (#f4ecd6). Additive list — a new BRG-palette series joins it, nothing moves.
// plg-guide joined 2026-08-11: its themes.py bg is #f5f0eb and its Magnific art was generated
// against #f5f0eb, so without this entry every generated figure sits on a visibly different
// cream and reads as a patch pasted onto the page.
const BRG_CREAM_THEMES = ['brg-deep-dive', 'wte-guide', 'plg-guide'];
// Circumvent's sheet is a warmer kraft cream than either neighbour (PALETTE.md).
const CIRCUMVENT_CREAM = '#f2ede0';

export const Video: React.FC<VideoProps> = (props) => {
  const {audio, words, scenes, captionBottomPx, captionFontSize, audioFrom, width, height, theme, captionAccent, showCaptions, presenter} = props;
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
  // Chibi presenter (operator directive 2026-08-07, revised same day): Dave stands IN
  // the scene as a small overlay in a bottom corner — the scene fills the frame exactly
  // as it did before he existed. The v1 reserved-lane approach (content scaled left)
  // was rejected by the operator: it read as the character "standing offstage",
  // separate from the action. Placement does the not-obscuring work now: the engine
  // picks the emptier corner per scene and flips the pose to face the content.
  const chibiOn = Boolean(presenter?.enabled && scenes.some((s) => (s as any).chibi));
  const charH = presenter?.charHeightFrac || 0.18;
  // Distance from the frame BOTTOM to the top of the caption block, allowing two lines.
  const captionTopPx = captionBottomPx + captionFontSize * 2.9;
  return (
    <InkProvider theme={theme}>
    <WorldProvider theme={theme}>
    {/* base page: BRG's cream is a shade cooler than the FWF sheet; every other theme
        keeps its exact prior value so no existing render moves. */}
    <AbsoluteFill style={{backgroundColor: paper ? (theme === 'circumvent' ? CIRCUMVENT_CREAM : BRG_CREAM_THEMES.includes(theme || '') ? '#f5f0eb' : '#f4ecd6') : '#090d1c'}}>
      {paper ? <PaperBackground /> : <Background />}
      {scenes.map((scene, i) => {
        const Comp = REGISTRY[scene.component] || TalkingScene;
        const inset = FULL_BLEED.has(scene.component) ? 0 : contentBottom;
        return (
          <Sequence key={i} from={scene.from} durationInFrames={scene.durationInFrames} layout="none">
            <SceneWrap durationInFrames={scene.durationInFrames} paper={paper} tear={(scene as any).tear ? `tear${i}` : null}>
              {/* Content layer — full frame. The presenter overlays it (v2, 2026-08-07);
                  the v1 lane scale that shrank this layer beside him was rejected by the
                  operator as "the character standing offstage". */}
              <AbsoluteFill style={{
                bottom: inset,
                // `height: 'auto'` is what makes the inset REAL. AbsoluteFill's own defaults
                // include height:100%, and CSS drops `bottom` when top+height are both set —
                // so from the day this line was written (2026-07-16) until 2026-08-07 the
                // portrait reserve silently did nothing and every 9:16 render kept its
                // content centred in the full frame. Letting the top/bottom pair size the
                // box is the fix.
                ...(inset ? {height: 'auto'} : {}),
              }}>
                <Comp fields={scene.fields || {}} durationInFrames={scene.durationInFrames} sceneFrom={scene.from} audioFrom={audioFrom} />
                {/* narration-cued hand-drawn annotations (motion-playbook §2H) — full-frame
                    coordinate space, on top of the scene, under the captions */}
                {(scene as any).annotations?.length ? <AnnotateOverlay annotations={(scene as any).annotations} /> : null}
              </AbsoluteFill>
            </SceneWrap>
          </Sequence>
        );
      })}
      {audio && !paper ? <ReactiveStrip audio={audio} audioFrom={audioFrom || 0} /> : null}
      {showCaptions !== false ? <Captions words={words} bottomPx={captionBottomPx} fontSize={captionFontSize} theme={theme} accentColor={captionAccent} /> : null}
      {/* On-screen source citations (operator 2026-08-12). Mounted here, NOT per
          component, so every slide type is covered and the caption clearance is
          reasoned about in one place. See components/SourceLine.tsx. */}
      <SourceLines scenes={scenes} captionBottomPx={captionBottomPx} />
      {/* The presenter mounts LAST so he is above the scene, the annotations AND the
          captions: the viewer reads him as Dave presenting, not as scene furniture
          (operator directive 2026-08-07). He stands IN the scene as a corner overlay;
          the engine picks the emptier corner and faces him toward the content. */}
      {chibiOn
        ? scenes.map((scene, i) =>
            (scene as any).chibi ? (
              <Sequence key={`chibi${i}`} from={scene.from} durationInFrames={scene.durationInFrames} layout="none">
                <ChibiPresenter
                  pose={(scene as any).chibi}
                  charHeightFrac={(scene as any).chibiH || charH}
                  captionTopPx={captionTopPx}
                  side={(scene as any).chibiSide}
                  flip={(scene as any).chibiFlip}
                />
              </Sequence>
            ) : null
          )
        : null}
      {audio ? (
        <Sequence from={audioFrom || 0} layout="none">
          <Audio src={staticFile(audio)} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
    </WorldProvider>
    </InkProvider>
  );
};
