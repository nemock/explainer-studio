import React from 'react';
import {AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useAudioData, visualizeAudio} from '@remotion/media-utils';
import {BRAND} from '../brand';

// motion-playbook §2G — true audio-reactive accents. Both handle the sting audio offset:
// the narration starts at `audioFrom` (frames), so we sample at (absoluteFrame - audioFrom).

// Global ambient equalizer — a subtle bar row along the bottom that pulses with the voice
// the whole video (rendered behind the captions). Absolute frame, so no Sequence offset.
export const ReactiveStrip: React.FC<{audio: string; audioFrom: number}> = ({audio, audioFrom}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const data = useAudioData(staticFile(audio));
  if (!data) return null;
  const f = frame - (audioFrom || 0);
  if (f < 0) return null;
  const bins = visualizeAudio({fps, frame: f, audioData: data, numberOfSamples: 32});
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', pointerEvents: 'none'}}>
      <div style={{display: 'flex', alignItems: 'flex-end', gap: width * 0.004, width: '96%', height: '13%', opacity: 0.22, mixBlendMode: 'screen'}}>
        {bins.map((v, i) => (
          <div key={i} style={{flex: 1, height: `${Math.min(100, v * 600)}%`, background: BRAND.green, borderRadius: 3}} />
        ))}
      </div>
    </AbsoluteFill>
  );
};

// Dedicated hero waveform scene — a big mirrored equalizer reacting to the voice, with an
// optional kicker/headline. fields:{kicker,headline,audio}. sceneFrom+audioFrom passed by
// the dispatcher so sampling stays aligned to the audio under the sting offset.
export const Waveform: React.FC<{fields: any; durationInFrames: number; sceneFrom?: number; audioFrom?: number}> =
({fields, sceneFrom = 0, audioFrom = 0}) => {
  const local = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const data = useAudioData(staticFile(fields.audio));
  const intro = spring({frame: local, fps, config: {damping: 18}});
  const f = sceneFrom + local - audioFrom;
  const bins = data && f >= 0 ? visualizeAudio({fps, frame: f, audioData: data, numberOfSamples: 64}) : new Array(64).fill(0);
  const H = height * 0.34;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
      {fields.kicker ? (
        <div style={{fontFamily: BRAND.font, color: BRAND.green, fontWeight: 800, fontSize: height * 0.024, letterSpacing: 5, textTransform: 'uppercase', opacity: intro, marginBottom: height * 0.03}}>{fields.kicker}</div>
      ) : null}
      {fields.headline ? (
        <div style={{fontFamily: BRAND.font, color: BRAND.white, fontWeight: 900, fontSize: height * 0.06, textAlign: 'center', opacity: intro, marginBottom: height * 0.03, textShadow: '0 10px 50px rgba(0,0,0,.6)'}}>{fields.headline}</div>
      ) : null}
      <div style={{display: 'flex', alignItems: 'center', gap: height * 0.006, height: H, width: '78%', opacity: intro}}>
        {bins.map((v, i) => {
          const h = Math.max(height * 0.01, Math.min(H, v * height * 5));
          return <div key={i} style={{flex: 1, height: h, background: i % 2 ? BRAND.green : BRAND.white, borderRadius: 4, alignSelf: 'center'}} />;
        })}
      </div>
    </AbsoluteFill>
  );
};
