import React from 'react';
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import rough from 'roughjs';
import {BRAND} from '../brand';

// motion-playbook §2C — Schematic: a node-and-edge diagram that ASSEMBLES under the
// narration, with a camera that drifts to the active region ("lead the viewer's eye
// through the diagram"). Replaces StepFlow for anything non-linear.
//
// fields (all data, authored in deck.json — no per-video React):
//   nodes:  [{id, label, sub?, x, y, w?, kind?: 'good'|'bad'|'neutral'}]   x/y/w in 0-1 frame space
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

export const Schematic: React.FC<{fields: any; durationInFrames: number}> = ({fields, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps, width: W, height: H} = useVideoConfig();
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

  const nodeBox = (n: any) => {
    const w = (n.w ?? 0.2) * W;
    const h = Math.max(H * 0.085, H * 0.06 + (n.sub ? H * 0.035 : 0));
    return {x: n.x * W - w / 2, y: n.y * H - h / 2, w, h};
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

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      {fields.kicker ? (
        <div style={{position: 'absolute', top: '6%', left: 0, right: 0, textAlign: 'center',
                     fontFamily: BRAND.font, color: BRAND.green, fontWeight: 800,
                     fontSize: H * 0.024, letterSpacing: 5, textTransform: 'uppercase',
                     opacity: spring({frame, fps, config: {damping: 18}})}}>
          {fields.kicker}
        </div>
      ) : null}
      <AbsoluteFill style={{
        transform: `scale(${zoom}) translate(${(0.5 - cx) * W}px, ${(0.5 - cy) * H}px)`,
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
        {nodes.map((n) => {
          const b = nodeBox(n);
          const at = revealAt.get(n.id) ?? 0;
          const e = spring({frame: frame - at, fps, config: {damping: 15, stiffness: 120}});
          if (frame < at) return null;
          const color = kindColor(n.kind);
          return (
            <div key={n.id} style={{
              position: 'absolute', left: b.x, top: b.y, width: b.w, height: b.h,
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              borderRadius: 16, padding: `0 ${H * 0.012}px`, textAlign: 'center',
              background: fields.sketch ? 'rgba(9,13,28,.72)' : 'rgba(255,255,255,.05)',
              border: fields.sketch ? 'none' : `2px solid ${color}66`,
              boxShadow: `0 18px 60px rgba(0,0,0,.45)`,
              opacity: e,
              transform: `translateY(${interpolate(e, [0, 1], [22, 0])}px) scale(${interpolate(e, [0, 1], [0.88, 1])})`,
            }}>
              <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: H * 0.03,
                           color: BRAND.white, lineHeight: 1.08}}>
                {n.label}
              </div>
              {n.sub ? (
                <div style={{fontFamily: BRAND.font, fontWeight: 700, fontSize: H * 0.02,
                             color, marginTop: H * 0.006, lineHeight: 1.1}}>
                  {n.sub}
                </div>
              ) : null}
            </div>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
