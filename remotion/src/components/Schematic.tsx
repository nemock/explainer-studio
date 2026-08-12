import React from 'react';
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import rough from 'roughjs';
import {BRAND} from '../brand';
import {useInk, PAPER_SHADOW} from '../ink';
import {PaperNote, PaperSheet, fitNote, NOTE_PASTEL, PASTEL_CYCLE, NotePastel} from './PaperNote';

// motion-playbook §2C — Schematic: a node-and-edge diagram that ASSEMBLES under the
// narration, with a camera that drifts to the active region ("lead the viewer's eye
// through the diagram"). Replaces StepFlow for anything non-linear.
//
// fields (all data, authored in deck.json — no per-video React):
//   nodes:  [{id, label, sub?, x, y, w?, kind?: 'good'|'bad'|'neutral',
//            pastel?: 'yellow'|'blue'|'pink'|'green'}]   x/y/w in 0-1 frame space
//            (pastel pins the paper-note color; use it when nodes are PEERS and the
//             decorative cycle would wrongly imply they are different kinds of thing)
//   edges:  [{from, to, label?, kind?}]
//   stageTimes: (number|null)[]  — cue frames per stage (Python-resolved)
//   stages: [{reveal: [node or "<from>-><to>" edge ids]}]  — assembly order
//   camera: [{center: [x,y], zoom, stage}]  — optional camera keys, applied at stage times
//   sketch?: true  — rough hand-drawn node outlines instead of clean cards
// Nodes/edges NOT named by any stage reveal at their index's even-stagger fallback.
//
// Determinism: rough generation is seeded per element; camera + reveals are pure
// functions of frame.

const seedFrom = (s: string) => {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 2147483645) + 1;
};

const kindColor = (kind?: string) =>
  kind === 'bad' ? BRAND.red : kind === 'neutral' ? 'rgba(245,247,255,.55)' : BRAND.green;

// Paper-world schematic: nodes read as colored sticky notes (Dave 2026-07-18 — the cream
// cards + white dotted edges had no contrast on the cream page). Edges are hand-drawn navy
// Sharpie lines (see the ink.paper branches). The notes themselves stopped being CSS on
// 2026-07-31: they are now real generated paper substrates, and the four cycled colours
// live in PaperNote's PASTEL_CYCLE.
const darken = (hex: string, f: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgb(${Math.round(((n >> 16) & 255) * f)},${Math.round(((n >> 8) & 255) * f)},${Math.round((n & 255) * f)})`;
};
// deterministic small tilt per node so the notes look hand-placed, not gridded
const tiltFor = (id: string) => ((seedFrom(id) % 7) - 3) * 0.7; // ~ -2.1°..+2.1°

export const Schematic: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, width: W, height: H} = useVideoConfig();
  const ink = useInk();
  const nodes: any[] = fields.nodes || [];
  const edges: any[] = fields.edges || [];
  const stages: any[] = fields.stages || [];
  const stageTimes: (number | null)[] = fields.stageTimes || [];

  // element id -> reveal frame (stage cue, else even stagger across the scene)
  const revealAt = React.useMemo(() => {
    const m = new Map<string, number>();
    const per = durationInFrames / Math.max(1, (stages.length || nodes.length + edges.length) + 1);
    stages.forEach((st, si) => {
      const at = stageTimes[si] != null ? (stageTimes[si] as number) : si * per;
      (st.reveal || []).forEach((id: string) => m.set(id, at));
    });
    let fallbackIdx = 0;
    const fallback = () => (fallbackIdx++) * per;
    nodes.forEach((n) => { if (!m.has(n.id)) m.set(n.id, stages.length ? 0 : fallback()); });
    edges.forEach((e) => {
      const id = `${e.from}->${e.to}`;
      if (!m.has(id)) {
        const later = Math.max(m.get(e.from) ?? 0, m.get(e.to) ?? 0);
        m.set(id, stages.length ? later : fallback());
      }
    });
    return m;
  }, [nodes, edges, stages, stageTimes, durationInFrames]);

  // camera: piecewise moves between {center, zoom} keys at their stage times
  const cam = React.useMemo(() => {
    const keys = (fields.camera || [])
      .map((c: any) => ({
        at: c.stage != null && stageTimes[c.stage] != null ? (stageTimes[c.stage] as number)
            : c.at != null ? c.at : 0,
        cx: (c.center?.[0] ?? 0.5), cy: (c.center?.[1] ?? 0.5), zoom: c.zoom ?? 1,
      }))
      .sort((a: any, b: any) => a.at - b.at);
    return [{at: 0, cx: 0.5, cy: 0.5, zoom: 1}, ...keys];
  }, [fields.camera, stageTimes]);
  const MOVE = Math.round(0.9 * fps);
  let cx = 0.5, cy = 0.5, zoom = 1;
  for (let i = 0; i < cam.length; i++) {
    const k = cam[i];
    const t = interpolate(frame, [k.at, k.at + MOVE], [0, 1],
                          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
                           easing: Easing.bezier(0.16, 1, 0.3, 1)});
    cx = cx + (k.cx - cx) * t;
    cy = cy + (k.cy - cy) * t;
    zoom = zoom + (k.zoom - zoom) * t;
  }

  // Notes size themselves to their CONTENT (operator directive 2026-07-28, #52: long
  // labels/subs were overflowing the fixed-height notes — "It matches them against a
  // playbook" and the redlining definition both spilled past their edges). The old
  // formula ignored text length entirely, so anything that wrapped past two lines ran
  // out of the note. Estimate the wrapped line count from the node's own width and the
  // rendered font sizes, then grow the box to fit.
  //   n.w      — width, frame-width fraction (unchanged)
  //   n.h      — explicit height override, frame-height fraction (wins over everything)
  //   n.shape  — 'square' for a chunky real-post-it note; there is usually plenty of
  //              empty canvas, so bigger notes are cheap and read better.
  const nodeBox = (n: any) => {
    const w = (n.w ?? 0.2) * W;
    const padX = H * 0.014;                    // matches the rendered horizontal padding
    const inner = Math.max(1, w - padX * 2);
    const fLabel = H * 0.03, fSub = H * 0.02;  // must track the font sizes used below
    // rough wrapped-line count: chars * (em width) / usable width, min 1 line
    const linesOf = (txt: any, f: number, em: number) =>
      Math.max(1, Math.ceil((String(txt ?? '').length * f * em) / inner));
    const lLab = linesOf(n.label, fLabel, 0.55);        // 900-weight runs wide
    const lSub = n.sub ? linesOf(n.sub, fSub, 0.50) : 0;
    // slightly generous line-heights vs the render (1.08/1.1) so we never under-size
    const content = lLab * fLabel * 1.10 + (lSub ? H * 0.006 + lSub * fSub * 1.15 : 0);
    let h = Math.max(H * 0.085, content + H * 0.028);   // + breathing room top/bottom
    if (n.shape === 'square') h = Math.max(h, w);       // true square, real-post-it look
    if (n.h) h = n.h * H;                               // explicit override wins
    // Paper mode: the substrate's real aspect sets the height, so the generated paper is
    // never squashed to fit a box (papercraft-substrate-plan.md §3 — stretching smears the
    // grain and mushes the torn edge). fitNote only ever picks paper no wider than the text
    // needs, so this grows the box; the surplus is blank note. An explicit n.h still wins.
    let fit;
    if (ink.paper && !fields.sketch) {
      fit = fitNote(`schem:${n.id}`, w / h);
      if (!n.h) h = w / fit.aspect;
    }
    return {x: n.x * W - w / 2, y: n.y * H - h / 2, w, h, fit};
  };
  const nodeById = React.useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  // seeded sketch outlines (computed once — pure of frame)
  const sketchPaths = React.useMemo(() => {
    if (!fields.sketch) return new Map<string, {d: string}[]>();
    const gen = rough.generator();
    const m = new Map<string, {d: string}[]>();
    nodes.forEach((n) => {
      const b = nodeBox(n);
      const dr = gen.rectangle(b.x, b.y, b.w, b.h,
        {seed: seedFrom(`node:${n.id}`), roughness: 1.6, bowing: 1.2,
         stroke: kindColor(n.kind), strokeWidth: Math.max(2.5, H * 0.004)});
      m.set(n.id, gen.toPaths(dr).map((p) => ({d: p.d})));
    });
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fields.sketch, nodes, W, H]);

  // paper edges: hand-drawn navy Sharpie lines (seeded, pure of frame; drawn on via dashoffset)
  const roughEdges = React.useMemo(() => {
    const m = new Map<string, {d: string; len: number}>();
    if (!ink.paper) return m;
    const gen = rough.generator();
    edges.forEach((e) => {
      const a = nodeById.get(e.from), b = nodeById.get(e.to);
      if (!a || !b) return;
      const [x1, y1, x2, y2] = [a.x * W, a.y * H, b.x * W, b.y * H];
      const dr = gen.line(x1, y1, x2, y2, {
        seed: seedFrom(`edge:${e.from}->${e.to}`), roughness: 2, bowing: 2.4,
        stroke: ink.body, strokeWidth: Math.max(3, H * 0.0055),
      });
      const d = gen.toPaths(dr).map((p) => p.d).join(' ');
      m.set(`${e.from}->${e.to}`, {d, len: Math.hypot(x2 - x1, y2 - y1) * 2.4});
    });
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ink.paper, ink.body, edges, nodeById, W, H]);

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      {fields.kicker ? (
        <div style={{position: 'absolute', top: '6%', left: 0, right: 0, textAlign: 'center',
                     fontFamily: BRAND.font, color: ink.accent, fontWeight: 800,
                     fontSize: H * 0.030, letterSpacing: 4, textTransform: 'uppercase',
                     opacity: spring({frame, fps, config: {damping: 18}})}}>
          {fields.kicker}
        </div>
      ) : null}
      <AbsoluteFill style={{
        // camera transform + a slow ambient breathing so the diagram is never fully frozen,
        // even with no camera keys or during the sparse pre-reveal stretch (paper freezedetect).
        transform: `scale(${zoom * interpolate(frame, [0, durationInFrames], [1, 1.02])}) `
          + `translate(${(0.5 - cx) * W}px, ${(0.5 - cy) * H - interpolate(frame, [0, durationInFrames], [0, 6])}px)`,
        transformOrigin: '50% 50%',
      }}>
        {/* edges under nodes */}
        <svg width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
          {edges.map((e, i) => {
            const a = nodeById.get(e.from);
            const b = nodeById.get(e.to);
            if (!a || !b) return null;
            const at = revealAt.get(`${e.from}->${e.to}`) ?? 0;
            const t = interpolate(frame, [at, at + Math.round(0.6 * fps)], [0, 1],
                                  {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
            if (t <= 0) return null;
            const [x1, y1, x2, y2] = [a.x * W, a.y * H, b.x * W, b.y * H];
            const len = Math.hypot(x2 - x1, y2 - y1);
            const angle = Math.atan2(y2 - y1, x2 - x1);
            const color = kindColor(e.kind);
            const head = Math.max(14, H * 0.024);
            if (ink.paper) {
              // hand-drawn navy Sharpie connector, drawn on with the reveal
              const re = roughEdges.get(`${e.from}->${e.to}`);
              const sw = Math.max(3, H * 0.0055);
              return (
                <g key={i}>
                  {re ? (
                    <path d={re.d} fill="none" stroke={ink.body} strokeWidth={sw}
                          strokeLinecap="round" strokeLinejoin="round"
                          strokeDasharray={re.len} strokeDashoffset={re.len * (1 - t)} />
                  ) : null}
                  <g opacity={t > 0.92 ? 1 : 0} stroke={ink.body} strokeWidth={sw}
                     strokeLinecap="round" fill="none">
                    <line x1={x2} y1={y2} x2={x2 - head * Math.cos(angle - 0.45)} y2={y2 - head * Math.sin(angle - 0.45)} />
                    <line x1={x2} y1={y2} x2={x2 - head * Math.cos(angle + 0.45)} y2={y2 - head * Math.sin(angle + 0.45)} />
                  </g>
                  {/* paper edge labels render in a top chip layer (below), never buried under notes */}
                </g>
              );
            }
            const hx = x1 + (x2 - x1) * t;
            const hy = y1 + (y2 - y1) * t;
            return (
              <g key={i}>
                <line x1={x1} y1={y1} x2={hx} y2={hy} stroke={color}
                      strokeWidth={Math.max(2.5, H * 0.0045)} strokeLinecap="round"
                      strokeDasharray={`${H * 0.012} ${H * 0.011}`}
                      style={{filter: `drop-shadow(0 0 8px ${color}55)`}} />
                <g opacity={t > 0.92 ? 1 : 0} stroke={color} strokeWidth={Math.max(2.5, H * 0.0045)}
                   strokeLinecap="round" fill="none">
                  <line x1={x2} y1={y2} x2={x2 - head * Math.cos(angle - 0.45)} y2={y2 - head * Math.sin(angle - 0.45)} />
                  <line x1={x2} y1={y2} x2={x2 - head * Math.cos(angle + 0.45)} y2={y2 - head * Math.sin(angle + 0.45)} />
                </g>
                {e.label && len > W * 0.08 ? (
                  <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - H * 0.012} textAnchor="middle"
                        opacity={t > 0.85 ? 1 : 0}
                        style={{fontFamily: BRAND.font, fontStyle: 'italic', fontWeight: 700,
                                fontSize: H * 0.021, fill: color}}>
                    {e.label}
                  </text>
                ) : null}
              </g>
            );
          })}
          {/* sketch-mode node outlines live in the same svg, above edges */}
          {fields.sketch ? nodes.map((n) => {
            const at = revealAt.get(n.id) ?? 0;
            const e = spring({frame: frame - at, fps, config: {damping: 15, stiffness: 120}});
            if (frame < at) return null;
            return (sketchPaths.get(n.id) || []).map((p, j) => (
              <path key={`${n.id}${j}`} d={p.d} fill="none" stroke={kindColor(n.kind)}
                    strokeWidth={Math.max(2.5, H * 0.004)} strokeLinecap="round" opacity={e} />
            ));
          }) : null}
        </svg>
        {/* node cards */}
        {nodes.map((n, ni) => {
          const b = nodeBox(n);
          const at = revealAt.get(n.id) ?? 0;
          const e = spring({frame: frame - at, fps, config: {damping: 15, stiffness: 120}});
          if (frame < at) return null;
          const color = kindColor(n.kind);
          const note = ink.paper && !fields.sketch;   // post-it treatment
          // color-by-kind when the node carries semantic good/bad (e.g. jagged-frontier
          // inside=green / outside=coral); otherwise cycle the decorative post-it palette.
          // Paper mode: a real generated post-it substrate carries the node, and the type
          // is laid on top (papercraft-substrate-plan.md). The CSS card below is kept for
          // the non-paper themes, which have no substrate library of their own.
          if (note) {
            // An explicit n.pastel WINS over both the kind mapping and the decorative cycle.
            // The cycle assumes nodes are unrelated boxes; when they are a SET OF PEERS (the
            // four decisions in plg-guide module 1), four different colors actively say
            // "these are four different kinds of thing" and the reader believes it. Pinning
            // the color lets an author say "same kind, one of them lit" — which is what a
            // person highlighting one card in a set actually looks like.
            const pastel: NotePastel = (n.pastel as NotePastel)
              || (n.kind === 'good' ? 'green' : n.kind === 'bad' ? 'pink'
                  : PASTEL_CYCLE[ni % PASTEL_CYCLE.length]);
            return (
              <div key={n.id} style={{
                position: 'absolute', left: b.x, top: b.y, width: b.w, height: b.h,
                opacity: e,
                transform: `translateY(${interpolate(e, [0, 1], [22, 0])}px) scale(${interpolate(e, [0, 1], [0.88, 1])}) rotate(${tiltFor(n.id)}deg)`,
              }}>
                <PaperNote
                  id={`schem:${n.id}`}
                  aspect={b.w / b.h}
                  family={b.fit?.family}
                  pastel={pastel}
                  shadow={`0 ${Math.round(H * 0.012)}px ${Math.round(H * 0.022)}px rgba(12,4,24,.34)`}
                >
                  <div style={{padding: `0 ${H * 0.022}px`, textAlign: 'center'}}>
                    <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: H * 0.03,
                                 color: '#2c1e4e', lineHeight: 1.08}}>
                      {n.label}
                    </div>
                    {n.sub ? (
                      <div style={{fontFamily: BRAND.font, fontWeight: 700, fontSize: H * 0.02,
                                   color: darken(NOTE_PASTEL[pastel], 0.42),
                                   marginTop: H * 0.006, lineHeight: 1.1}}>
                        {n.sub}
                      </div>
                    ) : null}
                  </div>
                </PaperNote>
              </div>
            );
          }
          // sketch mode + the non-paper themes: the original drawn card
          return (
            <div key={n.id} style={{
              position: 'absolute', left: b.x, top: b.y, width: b.w, height: b.h,
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              borderRadius: 16, padding: `0 ${H * 0.014}px`, textAlign: 'center',
              background: fields.sketch ? 'rgba(9,13,28,.72)' : ink.cardBg,
              border: fields.sketch ? 'none' : `2px solid ${color}66`,
              boxShadow: ink.paper && !fields.sketch ? PAPER_SHADOW : `0 18px 60px rgba(0,0,0,.45)`,
              opacity: e,
              transform: `translateY(${interpolate(e, [0, 1], [22, 0])}px) scale(${interpolate(e, [0, 1], [0.88, 1])})`,
            }}>
              <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: H * 0.03,
                           color: fields.sketch ? BRAND.white : ink.body, lineHeight: 1.08}}>
                {n.label}
              </div>
              {n.sub ? (
                <div style={{fontFamily: BRAND.font, fontWeight: 700, fontSize: H * 0.02,
                             color: color, marginTop: H * 0.006, lineHeight: 1.1}}>
                  {n.sub}
                </div>
              ) : null}
            </div>
          );
        })}
        {/* edge labels as cream chips ON TOP of the notes (paper) — never buried under a node */}
        {ink.paper ? edges.map((e, i) => {
          if (!e.label) return null;
          const a = nodeById.get(e.from), b = nodeById.get(e.to);
          if (!a || !b) return null;
          const at = revealAt.get(`${e.from}->${e.to}`) ?? 0;
          const t = interpolate(frame, [at, at + Math.round(0.6 * fps)], [0, 1],
                                {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          if (t < 0.9) return null;
          const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
          return (
            // a small paper tag, not a flat cream pill. These sit directly ON the note
            // substrates, so a drawn chip is the most exposed synthetic surface on the slide.
            <div key={`el${i}`} style={{
              position: 'absolute', left: mx * W, top: my * H, transform: 'translate(-50%, -50%)',
              color: ink.body, borderRadius: 8,
              padding: `${H * 0.007}px ${H * 0.017}px`, whiteSpace: 'nowrap',
              fontFamily: BRAND.font, fontStyle: 'italic', fontWeight: 800, fontSize: H * 0.02,
              boxShadow: '0 4px 14px rgba(0,0,0,.2)',
              opacity: interpolate(t, [0.9, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
            }}>
              <PaperSheet id={`edgelbl:${e.from}->${e.to}`} family="card_tag" radius={8} edge={7} tint="#fbf5df" />
              <span style={{position: 'relative'}}>{e.label}</span>
            </div>
          );
        }) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
