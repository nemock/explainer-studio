import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {BRAND} from './brand';
import {z} from 'zod';

// Brand YouTube thumbnail as a Remotion <Still> (1280x720). Replicates the channel
// template from thumbnail-playbook.md: navy radial gradient with a lighter cool hotspot
// behind the subject, the operator cut out bottom-right (drop-shadow + bottom fade),
// a 1-2 line red-band keyword headline top-left, and a white sub-line with the payoff
// words in green. Prop-driven so one component renders every video's A/B pair.
export const thumbnailSchema = z.object({
  bands: z.array(z.string()),            // 1-2 keyword lines (red bands)
  sub: z.string(),                       // supporting line
  accent: z.array(z.string()),           // substrings of `sub` rendered green
  cutout: z.string(),                    // staticFile name of the transparent PNG
  mirror: z.boolean().default(false),    // flip the cutout horizontally (A/B variety)
  innerHot: z.string().default('#1a2750'), // inner radial hotspot (thumbnail-playbook §5)
  bandSize: z.number().default(104),
});
export type ThumbnailProps = z.infer<typeof thumbnailSchema>;

// wrap any accent substring of `text` in green (case-insensitive, first match each)
const colorize = (text: string, accents: string[]) => {
  if (!accents.length) return text;
  const esc = accents.map((a) => a.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const re = new RegExp(`(${esc.join('|')})`, 'ig');
  return text.split(re).map((part, i) =>
    accents.some((a) => a.toLowerCase() === part.toLowerCase())
      ? <span key={i} style={{color: BRAND.green}}>{part}</span>
      : <React.Fragment key={i}>{part}</React.Fragment>
  );
};

export const Thumbnail: React.FC<ThumbnailProps> = ({
  bands, sub, accent, cutout, mirror, innerHot, bandSize,
}) => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: BRAND.navyOut,
        backgroundImage: `radial-gradient(135% 120% at 74% 42%, ${innerHot} 0%, ${BRAND.navyMid} 58%, ${BRAND.navyOut} 100%)`,
        fontFamily: BRAND.font,
      }}
    >
      {/* subject cutout, bottom-right, bleeding off the edge, bottom 16% faded */}
      <div
        style={{
          position: 'absolute', right: -180, bottom: 0, height: 700,
          WebkitMaskImage: 'linear-gradient(to top, transparent 0%, black 16%)',
          maskImage: 'linear-gradient(to top, transparent 0%, black 16%)',
          transform: mirror ? 'scaleX(-1)' : 'none',
        }}
      >
        <Img
          src={staticFile(cutout)}
          style={{height: '100%', filter: 'drop-shadow(0 0 54px rgba(0,0,0,.6))'}}
        />
      </div>

      {/* headline + sub, top-left */}
      <div style={{position: 'absolute', left: 56, top: 96, zIndex: 2, width: 770}}>
        {bands.map((b, i) => (
          <div key={i} style={{marginTop: i === 0 ? 0 : 14}}>
            <span
              style={{
                display: 'inline-block', background: BRAND.red, color: '#fff',
                fontSize: bandSize, fontWeight: 900, letterSpacing: '-.02em',
                padding: '8px 26px', borderRadius: 14, lineHeight: 1.04,
                boxShadow: '0 16px 60px rgba(255,77,77,.4)',
              }}
            >
              {b}
            </span>
          </div>
        ))}
        <div
          style={{
            marginTop: 40, fontSize: 50, fontWeight: 900, color: BRAND.white,
            lineHeight: 1.2, textShadow: '0 3px 18px rgba(0,0,0,.7)', maxWidth: 680,
          }}
        >
          {colorize(sub, accent)}
        </div>
      </div>
    </AbsoluteFill>
  );
};
