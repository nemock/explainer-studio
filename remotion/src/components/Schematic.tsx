import React from 'react';
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import rough from 'roughjs';
import {BRAND} from '../brand';
import {useInk, PAPER_SHADOW} from '../ink';
import {PaperNote, PaperSheet, fitNote, NOTE_PASTEL, PASTEL_CYCLE, NotePastel} from './PaperNote';
import {useWorld} from './PaperWorld';
import {AnnotateOverlay} from './Annotate';
import {useTypeScale, useHeadingFamily} from '../type';

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

const kindColor = (kind: string | undefined, danger: string) =>
  kind === 'bad' ? danger : kind === 'neutral' ? 'rgba(245,247,255,.55)' : BRAND.green;

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
  // Sizes (type, padding, strokes) scale off the SHORT side, the paper world's M
  // (usePaperLayout); positions stay frame fractions of W and H. Sizing off H set 58px
  // type in a 184px note on a 9:16 Short: labels wrapped to five lines, the paper fit
  // grew each note into a strip ~900px tall, and the strips covered the kicker
  // (plg-guide module 6, 2026-09-23). In 16:9, U === H, so landscape is unchanged.
  const U = Math.min(W, H);
  const ink = useInk();
  // Edge-label tags are cream paper. On a dark-page world ink.body is light (it is the type on
  // the dark ground), which left the tag blank; there the tag takes the world's card ink.
  const world = useWorld();
  const tagInk = world.page ? world.ink : ink.body;
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
  const {on: phone, ts, floor} = useTypeScale();
  const headFamily = useHeadingFamily();
  const fLabel0 = ts('label', U * 0.03), fSub0 = ts('sub', U * 0.02);
  const sizeBox = (n: any, wPx: number, fLabel: number, fSub: number, noSquare = false) => {
    const w = wPx;
    const padX = U * 0.014;                    // matches the rendered horizontal padding
    const inner = Math.max(1, w - padX * 2);
    // rough wrapped-line count: chars * (em width) / usable width, min 1 line
    const linesOf = (txt: any, f: number, em: number) =>
      Math.max(1, Math.ceil((String(txt ?? '').length * f * em) / inner));
    const lLab = linesOf(n.label, fLabel, 0.55);        // 900-weight runs wide
    const lSub = n.sub ? linesOf(n.sub, fSub, 0.50) : 0;
    // slightly generous line-heights vs the render (1.08/1.1) so we never under-size
    const content = lLab * fLabel * 1.10 + (lSub ? U * 0.006 + lSub * fSub * 1.15 : 0);
    let h = Math.max(U * 0.085, content + U * 0.028);   // + breathing room top/bottom
    if (n.shape === 'square' && !noSquare) h = Math.max(h, w);  // true square, real-post-it look
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
    return {w, h, fit, lLab, lSub};
  };

  // LAYOUT. Unscaled worlds: exactly the authored geometry (centre n.x*W, n.y*H, width n.w).
  // Phone type (visual upgrade 2026-11-01): the bigger type needs bigger notes, and the
  // diagram should use the space rather than sit as postage stamps in a blank frame
  // (operator, #79). So each note widens up to 1.3x its authored width, capped short of its
  // row neighbour; then the whole group is fitted (uniform scale, at most 1.2x, centred)
  // into the band between the heading and the captions. Relative placement is kept, so the
  // author's composition survives; only its scale and centring change. Two passes, because
  // a scaled width changes the wrapped height.
  type Box = {x: number; y: number; w: number; h: number; cx: number; cy: number; fit: any; lLab: number; lSub: number};
  const {boxes, fLabel, fSub, mapPt} = React.useMemo(() => {
    const out = new Map<string, Box>();
    if (!phone || H > W) {
      nodes.forEach((n) => {
        const s = sizeBox(n, (n.w ?? 0.2) * W, fLabel0, fSub0);
        out.set(n.id, {x: n.x * W - s.w / 2, y: n.y * H - s.h / 2, w: s.w, h: s.h,
                       cx: n.x * W, cy: n.y * H, fit: s.fit, lLab: s.lLab, lSub: s.lSub});
      });
      return {boxes: out, fLabel: fLabel0, fSub: fSub0, mapPt: (x: number, y: number) => [x, y]};
    }
    const width0 = (n: any) => {
      const a = (n.w ?? 0.2) * W;
      const mates = nodes.filter((m) => m !== n && Math.abs(m.y - n.y) < 0.12);
      const dx = mates.length ? Math.min(...mates.map((m) => Math.abs(m.x - n.x))) * W : Infinity;
      const cap = Math.min(0.36 * W, dx * 0.9);
      // a square note grows in BOTH directions, so widening it eats the vertical room the
      // rows need (#79 s04); squares take the uniform group growth only
      return n.shape === 'square' ? a : Math.max(a, Math.min(cap, a * 1.3));
    };
    const top = H * 0.06 + (fields.kicker ? ts('heading', 0) * 1.2 + H * 0.035 : 0);
    const R = {x0: W * 0.05, x1: W * 0.95, y0: top, y1: H * 0.73};
    // A layout at growth k: sizes from k-scaled widths, centres spread by k about C (the
    // authored group's centre). Coordinates relative to C until the final placement.
    const build = (k: number, fl: number, fs: number, C: {x: number; y: number}) =>
      nodes.map((n) => ({n, ...sizeBox(n, width0(n) * k, fl, fs),
                         rx: (n.x * W - C.x) * k, ry: (n.y * H - C.y) * k}));
    const bbox = (L: ReturnType<typeof build>) => {
      const B = {x0: Math.min(...L.map((l) => l.rx - l.w / 2)), x1: Math.max(...L.map((l) => l.rx + l.w / 2)),
                 y0: Math.min(...L.map((l) => l.ry - l.h / 2)), y1: Math.max(...L.map((l) => l.ry + l.h / 2))};
      return {...B, cx: (B.x0 + B.x1) / 2, cy: (B.y0 + B.y1) / 2,
              fit: Math.min((R.x1 - R.x0) / Math.max(1, B.x1 - B.x0), (R.y1 - R.y0) / Math.max(1, B.y1 - B.y0))};
    };
    // pass 1: the authored layout at natural size -> how much it may grow (<= 1.2x)
    const B1 = bbox(build(1, fLabel0, fSub0, {x: 0, y: 0}));
    const C = {x: B1.cx, y: B1.cy};
    const k = Math.min(B1.fit, 1.2);
    // pass 2: re-size at that growth with the fonts scaled along (never under the floor)
    const fl = Math.min(fLabel0 * 1.15, Math.max(floor('label'), fLabel0 * k));
    const fs = Math.min(fSub0 * 1.15, Math.max(floor('sub'), fSub0 * k));
    const L = build(k, fl, fs, C);
    const B = bbox(L);
    const s2 = Math.min(1, B.fit);          // wrapping may have grown it past the band
    const rcx = (R.x0 + R.x1) / 2, rcy = (R.y0 + R.y1) / 2;
    const place = (rx: number, ry: number) => [rcx + (rx - B.cx) * s2, rcy + (ry - B.cy) * s2];
    // Growth is not uniform (notes widen 1.3x and the bigger type wraps taller), so notes the
    // author set apart can now touch: s04 on #79 put its "rule" note across the row above it.
    // Only the notes in a collision give way, so one tight pair does not shrink the whole
    // diagram (s17): a forced square stops being square first (it grows in both directions),
    // then each colliding note shrinks about its own centre until the pair clears by a gap.
    // Pairs that already overlapped as authored (f < 0.5) are deliberate stacks; left alone.
    const gap = U * 0.025;
    const placed = L.map((l) => {
      const [cx, cy] = place(l.rx, l.ry);
      return {l, cx, cy, w: l.w * s2, h: l.h * s2, noSquare: false};
    });
    const fOf = (a: typeof placed[0], b: typeof placed[0]) => Math.max(
      (Math.abs(a.cx - b.cx) - gap) / ((a.w + b.w) / 2),
      (Math.abs(a.cy - b.cy) - gap) / ((a.h + b.h) / 2));
    const pairs = () => placed.flatMap((a, i) => placed.slice(i + 1).map((b) => [a, b] as const));
    // squares give way TOGETHER: they are usually peers, and one short note in a row of
    // squares reads as a different kind of thing (s04's middle switch did)
    const squareHit = pairs().some(([a, b]) => {
      const f = fOf(a, b);
      return f < 1 && f >= 0.5 && (a.l.n.shape === 'square' || b.l.n.shape === 'square');
    });
    if (squareHit) {
      placed.filter((p) => p.l.n.shape === 'square').forEach((p) => {
        p.noSquare = true;
        p.h = sizeBox(p.l.n, p.w, fl * s2, fs * s2, true).h;
      });
    }
    const fNode = new Map(placed.map((p) => [p, 1]));
    pairs().forEach(([a, b]) => {
      const f = fOf(a, b);
      if (f >= 1 || f < 0.5) return;
      fNode.set(a, Math.min(fNode.get(a)!, f));
      fNode.set(b, Math.min(fNode.get(b)!, f));
    });
    // one type size for the whole diagram, set by its most-shrunk note (never under the floor)
    const fMin = Math.min(...Array.from(fNode.values()));
    const flF = Math.max(floor('label'), fl * s2 * fMin), fsF = Math.max(floor('sub'), fs * s2 * fMin);
    placed.forEach((p) => {
      // re-fit the height to the text at its FINAL size: type stops at its floor while the
      // box keeps shrinking, so a scaled height can be shorter than its own words
      const w = p.w * fNode.get(p)!;
      const r = sizeBox(p.l.n, w, flF, fsF, p.noSquare);
      out.set(p.l.n.id, {x: p.cx - w / 2, y: p.cy - r.h / 2, w, h: r.h, cx: p.cx, cy: p.cy,
                         fit: r.fit, lLab: r.lLab, lSub: r.lSub});
    });
    // any authored frame point (camera centres) through the same transform
    const mapPt = (x: number, y: number) => place((x - C.x) * k, (y - C.y) * k);
    return {boxes: out, fLabel: flF, fSub: fsF, mapPt};
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, W, H, phone, fLabel0, fSub0, fields.kicker, ink.paper, fields.sketch]);
  const nodeBox = (n: any) => boxes.get(n.id)!;
  const nodeById = React.useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  // `target` annotations -> frame geometry from the node's box. A circle clears the note
  // with room for the tilt; an underline sits just under it.
  const anchored = React.useMemo(() => (fields.nodeAnnotations || []).flatMap((a: any) => {
    const b = boxes.get(a.target);
    if (!b) return [];
    if (a.kind === 'strike') {
      // across the LABEL, one stroke per wrapped line (the label sits above any sub-line in
      // the note's centred text block; same metrics as sizeBox)
      const subH = b.lSub ? U * 0.006 + b.lSub * fSub * 1.1 : 0;
      const top = b.cy - (b.lLab * fLabel * 1.08 + subH) / 2;
      return Array.from({length: b.lLab}, (_, i) => {
        const y = (top + (i + 0.55) * fLabel * 1.08) / H;
        return {...a, from: [(b.x + b.w * 0.12) / W, y], to: [(b.x + b.w * 0.88) / W, y]};
      });
    }
    if (a.kind === 'underline') {
      return [{...a, at: [b.cx / W, (b.y + b.h) / H + 0.018], w: (b.w * 0.8) / W}];
    }
    const pad = a.kind === 'circle' ? [1.28, 1.42] : [1.1, 1.16];
    return [{...a, at: [b.cx / W, b.cy / H], w: (b.w * pad[0]) / W, h: (b.h * pad[1]) / H}];
  }), [fields.nodeAnnotations, boxes, W, H, U, fLabel, fSub]);

  // camera: piecewise moves between {center, zoom} keys at their stage times
  const cam = React.useMemo(() => {
    const keys = (fields.camera || [])
      .map((c: any) => ({
        at: c.stage != null && stageTimes[c.stage] != null ? (stageTimes[c.stage] as number)
            : c.at != null ? c.at : 0,
        cx: (c.center?.[0] ?? 0.5), cy: (c.center?.[1] ?? 0.5), zoom: c.zoom ?? 1,
      }))
      .map((c: any) => {
        if (!phone || H > W) return c;
        const [x, y] = mapPt(c.cx * W, c.cy * H);
        return {...c, cx: x / W, cy: y / H};
      })
      .sort((a: any, b: any) => a.at - b.at);
    return [{at: 0, cx: 0.5, cy: 0.5, zoom: 1}, ...keys];
  }, [fields.camera, stageTimes, phone, mapPt, W, H]);
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


  // seeded sketch outlines (computed once — pure of frame)
  const sketchPaths = React.useMemo(() => {
    if (!fields.sketch) return new Map<string, {d: string}[]>();
    const gen = rough.generator();
    const m = new Map<string, {d: string}[]>();
    nodes.forEach((n) => {
      const b = nodeBox(n);
      const dr = gen.rectangle(b.x, b.y, b.w, b.h,
        {seed: seedFrom(`node:${n.id}`), roughness: 1.6, bowing: 1.2,
         stroke: kindColor(n.kind, (ink.danger ?? BRAND.red)), strokeWidth: Math.max(2.5, U * 0.004)});
      m.set(n.id, gen.toPaths(dr).map((p) => ({d: p.d})));
    });
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fields.sketch, nodes, W, H, boxes]);

  // paper edges: hand-drawn navy Sharpie lines (seeded, pure of frame; drawn on via dashoffset)
  const roughEdges = React.useMemo(() => {
    const m = new Map<string, {d: string; len: number}>();
    if (!ink.paper) return m;
    const gen = rough.generator();
    edges.forEach((e) => {
      const a = boxes.get(e.from), b = boxes.get(e.to);
      if (!a || !b) return;
      const [x1, y1, x2, y2] = [a.cx, a.cy, b.cx, b.cy];
      const dr = gen.line(x1, y1, x2, y2, {
        seed: seedFrom(`edge:${e.from}->${e.to}`), roughness: 2, bowing: 2.4,
        stroke: ink.body, strokeWidth: Math.max(3, U * 0.0055),
      });
      const d = gen.toPaths(dr).map((p) => p.d).join(' ');
      m.set(`${e.from}->${e.to}`, {d, len: Math.hypot(x2 - x1, y2 - y1) * 2.4});
    });
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ink.paper, ink.body, edges, boxes, W, H]);

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      {fields.kicker && phone ? (
        // phone type: the kicker is the slide's only headline, so it is set as one (operator
        // 2026-11-01) instead of small green caps alone at the top of an empty frame
        <div style={{position: 'absolute', top: '6%', left: '6%', right: '6%', textAlign: 'center',
                     fontFamily: headFamily, color: ink.body, fontWeight: 900,
                     fontSize: ts('heading', 0), lineHeight: 1.08, letterSpacing: -0.5,
                     textWrap: 'balance' as any,
                     opacity: spring({frame, fps, config: {damping: 18}})}}>
          {fields.kicker}
        </div>
      ) : fields.kicker ? (
        <div style={{position: 'absolute', top: '6%', left: 0, right: 0, textAlign: 'center',
                     fontFamily: BRAND.font, color: ink.accent, fontWeight: 800,
                     fontSize: U * 0.030, letterSpacing: 4, textTransform: 'uppercase',
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
            const a = boxes.get(e.from);
            const b = boxes.get(e.to);
            if (!a || !b) return null;
            const at = revealAt.get(`${e.from}->${e.to}`) ?? 0;
            const t = interpolate(frame, [at, at + Math.round(0.6 * fps)], [0, 1],
                                  {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
            if (t <= 0) return null;
            const [x1, y1, x2, y2] = [a.cx, a.cy, b.cx, b.cy];
            const len = Math.hypot(x2 - x1, y2 - y1);
            const angle = Math.atan2(y2 - y1, x2 - x1);
            const color = kindColor(e.kind, (ink.danger ?? BRAND.red));
            const head = Math.max(14, U * 0.024);
            if (ink.paper) {
              // hand-drawn navy Sharpie connector, drawn on with the reveal
              const re = roughEdges.get(`${e.from}->${e.to}`);
              const sw = Math.max(3, U * 0.0055);
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
                      strokeWidth={Math.max(2.5, U * 0.0045)} strokeLinecap="round"
                      strokeDasharray={`${U * 0.012} ${U * 0.011}`}
                      style={{filter: `drop-shadow(0 0 8px ${color}55)`}} />
                <g opacity={t > 0.92 ? 1 : 0} stroke={color} strokeWidth={Math.max(2.5, U * 0.0045)}
                   strokeLinecap="round" fill="none">
                  <line x1={x2} y1={y2} x2={x2 - head * Math.cos(angle - 0.45)} y2={y2 - head * Math.sin(angle - 0.45)} />
                  <line x1={x2} y1={y2} x2={x2 - head * Math.cos(angle + 0.45)} y2={y2 - head * Math.sin(angle + 0.45)} />
                </g>
                {e.label && len > W * 0.08 ? (
                  <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - U * 0.012} textAnchor="middle"
                        opacity={t > 0.85 ? 1 : 0}
                        style={{fontFamily: BRAND.font, fontStyle: 'italic', fontWeight: 700,
                                fontSize: U * 0.021, fill: color}}>
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
              <path key={`${n.id}${j}`} d={p.d} fill="none" stroke={kindColor(n.kind, (ink.danger ?? BRAND.red))}
                    strokeWidth={Math.max(2.5, U * 0.004)} strokeLinecap="round" opacity={e} />
            ));
          }) : null}
        </svg>
        {/* node cards */}
        {nodes.map((n, ni) => {
          const b = nodeBox(n);
          const at = revealAt.get(n.id) ?? 0;
          const e = spring({frame: frame - at, fps, config: {damping: 15, stiffness: 120}});
          if (frame < at) return null;
          const color = kindColor(n.kind, (ink.danger ?? BRAND.red));
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
                  shadow={`0 ${Math.round(U * 0.012)}px ${Math.round(U * 0.022)}px rgba(12,4,24,.34)`}
                >
                  <div style={{padding: `0 ${U * 0.022}px`, textAlign: 'center'}}>
                    <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: fLabel,
                                 color: '#2c1e4e', lineHeight: 1.08}}>
                      {n.label}
                    </div>
                    {n.sub ? (
                      <div style={{fontFamily: BRAND.font, fontWeight: 700, fontSize: fSub,
                                   color: darken(NOTE_PASTEL[pastel], 0.42),
                                   marginTop: U * 0.006, lineHeight: 1.1}}>
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
              borderRadius: 16, padding: `0 ${U * 0.014}px`, textAlign: 'center',
              background: fields.sketch ? 'rgba(9,13,28,.72)' : ink.cardBg,
              border: fields.sketch ? 'none' : `2px solid ${color}66`,
              boxShadow: ink.paper && !fields.sketch ? PAPER_SHADOW : `0 18px 60px rgba(0,0,0,.45)`,
              opacity: e,
              transform: `translateY(${interpolate(e, [0, 1], [22, 0])}px) scale(${interpolate(e, [0, 1], [0.88, 1])})`,
            }}>
              <div style={{fontFamily: BRAND.font, fontWeight: 900, fontSize: fLabel,
                           color: fields.sketch ? BRAND.white : ink.body, lineHeight: 1.08}}>
                {n.label}
              </div>
              {n.sub ? (
                <div style={{fontFamily: BRAND.font, fontWeight: 700, fontSize: fSub,
                             color: color, marginTop: U * 0.006, lineHeight: 1.1}}>
                  {n.sub}
                </div>
              ) : null}
            </div>
          );
        })}
        {/* edge labels as cream chips ON TOP of the notes (paper) — never buried under a node */}
        {ink.paper ? edges.map((e, i) => {
          if (!e.label) return null;
          const a = boxes.get(e.from), b = boxes.get(e.to);
          if (!a || !b) return null;
          const at = revealAt.get(`${e.from}->${e.to}`) ?? 0;
          const t = interpolate(frame, [at, at + Math.round(0.6 * fps)], [0, 1],
                                {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          if (t < 0.9) return null;
          const mx = (a.cx + b.cx) / 2 / W, my = (a.cy + b.cy) / 2 / H;
          return (
            // a small paper tag, not a flat cream pill. These sit directly ON the note
            // substrates, so a drawn chip is the most exposed synthetic surface on the slide.
            <div key={`el${i}`} style={{
              position: 'absolute', left: mx * W, top: my * H, transform: 'translate(-50%, -50%)',
              color: tagInk, borderRadius: 8,
              padding: `${U * 0.007}px ${U * 0.017}px`, whiteSpace: 'nowrap',
              fontFamily: BRAND.font, fontStyle: 'italic', fontWeight: 800, fontSize: fSub,
              boxShadow: '0 4px 14px rgba(0,0,0,.2)',
              opacity: interpolate(t, [0.9, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
            }}>
              <PaperSheet id={`edgelbl:${e.from}->${e.to}`} family="card_tag" radius={8} edge={7} tint="#fbf5df" />
              <span style={{position: 'relative'}}>{e.label}</span>
            </div>
          );
        }) : null}
        {/* node-anchored annotations (`target`): drawn around the node's laid-out box, inside
            the camera, so a circle lands on its note wherever layout put it */}
        {anchored.length ? <AnnotateOverlay annotations={anchored} /> : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
