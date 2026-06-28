import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../brand';

// motion-playbook §2B — a grid of hero numbers, each springing in on a stagger.
// fields: {kicker, stats:[{value, label, kind?}], source?}. kind: good->green, bad->red, else white.
// Values are shown as-authored strings ($1, $2.2B, 93%) so abbreviated figures render cleanly.
const tone = (k?: string) => (k === 'bad' ? BRAND.red : k === 'good' ? BRAND.green : BRAND.white);

export const StatGrid: React.FC<{fields: any; durationInFrames: number}> = ({fields}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const stats: any[] = fields.stats || [];
  const cols = stats.length === 4 ? 2 : Math.min(Math.max(stats.length, 1), 3);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '0 7%'}}>
      {fields.kicker ? (
        <div style={{fontFamily: BRAND.font, color: BRAND.green, fontWeight: 800, fontSize: height * 0.024,
          letterSpacing: 5, textTransform: 'uppercase', textAlign: 'center', marginBottom: height * 0.055}}>
          {fields.kicker}
        </div>
      ) : null}
      <div style={{display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: `${height * 0.05}px ${height * 0.1}px`, width: '100%', maxWidth: '90%'}}>
        {stats.map((s, i) => {
          const e = spring({frame: frame - 8 - i * 7, fps, config: {damping: 18}});
          return (
            <div key={i} style={{textAlign: 'center', opacity: e, transform: `translateY(${(1 - e) * 26}px)`}}>
              <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: height * 0.12, lineHeight: 1,
                color: tone(s.kind), textShadow: '0 12px 60px rgba(0,0,0,.55)', fontVariantNumeric: 'tabular-nums'}}>
                {s.value}
              </div>
              <div style={{fontFamily: BRAND.font, fontWeight: 800, fontSize: height * 0.026, letterSpacing: 1,
                color: BRAND.white, opacity: 0.82, marginTop: height * 0.014}}>
                {s.label}
              </div>
            </div>
          );
        })}
      </div>
      {fields.source ? (
        <div style={{position: 'absolute', bottom: height * 0.05, left: 0, right: 0, textAlign: 'center',
          fontFamily: BRAND.font, fontSize: height * 0.018, color: 'rgba(245,247,255,.45)'}}>
          {fields.source}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
