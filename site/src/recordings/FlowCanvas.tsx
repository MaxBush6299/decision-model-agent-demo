import { FLOW_NODES, flowAt, stepLabel, type FlowNode, type TimelineEvent } from './model';

const NW = 110;
const NH = 64;
const COL = [20, 190, 360, 530, 700, 870, 1040];
const MAIN_Y = 196;
const POS: Record<FlowNode, { x: number; y: number }> = {
  request: { x: COL[0], y: MAIN_Y },
  d1: { x: COL[1], y: MAIN_Y },
  routing: { x: COL[2], y: MAIN_Y },
  'supply-chain': { x: COL[3], y: 36 },
  production: { x: COL[3], y: MAIN_Y },
  commercial: { x: COL[3], y: 356 },
  coordinator: { x: COL[4], y: MAIN_Y },
  validation: { x: COL[5], y: MAIN_Y },
  final: { x: COL[6], y: MAIN_Y },
};
const SPECIALISTS: FlowNode[] = ['supply-chain', 'production', 'commercial'];

type EdgeKind = 'request' | 'async' | 'hold';
interface Edge { id: string; from: FlowNode; to: FlowNode; label: string }
const EDGES: Edge[] = [
  { id: 'request-d1', from: 'request', to: 'd1', label: 'case' },
  { id: 'd1-routing', from: 'd1', to: 'routing', label: 'scores' },
  ...SPECIALISTS.map((s) => ({ id: `routing-${s}`, from: 'routing' as FlowNode, to: s, label: 'consult' })),
  ...SPECIALISTS.map((s) => ({ id: `${s}-coordinator`, from: s, to: 'coordinator' as FlowNode, label: 'findings' })),
  { id: 'routing-coordinator', from: 'routing', to: 'coordinator', label: 'no specialists' },
  { id: 'coordinator-validation', from: 'coordinator', to: 'validation', label: 'proposal' },
  { id: 'validation-final', from: 'validation', to: 'final', label: 'status' },
];

function path(e: Edge, bow = 0): string {
  const a = POS[e.from];
  const b = POS[e.to];
  const x1 = a.x + NW;
  const y1 = a.y + NH / 2;
  const x2 = b.x;
  const y2 = b.y + NH / 2;
  const dx = (x2 - x1) / 2;
  if (bow) return `M${x1},${y1} C${x1 + dx / 2},${y1 + bow} ${x2 - dx / 2},${y2 + bow} ${x2},${y2}`;
  return `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`;
}

function mid(e: Edge, bow = 0) {
  const a = POS[e.from];
  const b = POS[e.to];
  return { x: (a.x + NW + b.x) / 2, y: (a.y + b.y + NH) / 2 + bow * 0.75 };
}

export function payloadCaption(e: TimelineEvent): string {
  switch (e.kind) {
    case 'decision_result': {
      const first = e.answers ? Object.entries(e.answers)[0] : undefined;
      return first ? `${first[0]}: ${first[1].choice} (probability ${(first[1].probabilities[first[1].choice] * 100).toFixed(1)}%, confidence ${(first[1].confidence * 100).toFixed(0)}% reported separately)` : 'Decision-1 answer';
    }
    case 'model_call_end': return `${e.call_kind === 'decision' ? 'Decision-1' : 'GPT'} responded${e.http_status ? ` · HTTP ${e.http_status}` : ''}${e.usage ? ` · ${e.usage.input_tokens ?? 0} in / ${e.usage.output_tokens ?? 0} out tokens` : ''}`;
    case 'tool_call': return `Read-only fixture tool · evidence ${e.evidence_id ?? ''} · ${e.result_chars ?? 0} characters`;
    case 'pacing_wait': return `Local quota pacing · ${e.seconds ?? '?'} s`;
    case 'routing': return e.detail?.effective ? Object.entries(e.detail.effective).map(([n, v]) => `${n}: ${v}`).join(' · ') : 'Host routing applied';
    case 'final': return `Host status ${e.status} · warnings ${e.warnings ?? 0}`;
    default: return '';
  }
}

export function FlowCanvas({ timeline, idx }: { timeline: TimelineEvent[]; idx: number }) {
  const st = flowAt(timeline, idx);
  const cur = timeline[idx];
  const routedEv = timeline.find((e) => e.kind === 'routing');
  const effective = routedEv?.detail?.effective ?? {};
  const none = Boolean(routedEv) && SPECIALISTS.every((s) => effective[s] === 'not_needed' || effective[s] === undefined);
  const fin = timeline.find((e) => e.kind === 'final');
  const holdFinal = fin?.status === 'pending';
  const seen = (n: FlowNode) => st.active === n || st.visited.has(n);

  const edgeState = (e: Edge): { active: boolean; done: boolean; ghost: boolean; kind: EdgeKind } => {
    const ghost = st.skipped.has(e.to) || st.skipped.has(e.from) || (e.id === 'routing-coordinator' && !(none && seen('routing')));
    let active = false;
    if (e.from === 'routing' && SPECIALISTS.includes(e.to)) active = st.active === e.to;
    else if (SPECIALISTS.includes(e.from) && e.to === 'coordinator') active = st.active === 'coordinator' && st.visited.has(e.from);
    else active = st.prev === e.from && st.active === e.to;
    const done = seen(e.from) && seen(e.to) && !active;
    const kind: EdgeKind = e.id === 'validation-final' && holdFinal ? 'hold' : st.waiting && active ? 'async' : 'request';
    return { active, done, ghost, kind };
  };

  const nodeFill = (n: FlowNode) => {
    if (st.skipped.has(n)) return 'ghost';
    if (st.active === n) return 'active';
    if (st.visited.has(n)) return 'visited';
    return 'idle';
  };

  return (
    <div className="rec-canvas" role="group" aria-label="Request flow">
      <svg viewBox="0 0 1190 470" role="img" aria-label="Request flow canvas" className="rec-svg">
        <defs>
          {(['request', 'async', 'hold'] as EdgeKind[]).map((k) => (
            <marker key={k} id={`arrow-${k}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" className={`arrow arrow-${k}`} />
            </marker>
          ))}
        </defs>
        {EDGES.map((e) => {
          const s = edgeState(e);
          const bow = e.id === 'routing-coordinator' ? 150 : 0;
          const d = path(e, bow);
          const m = mid(e, bow);
          return (
            <g key={e.id} className={`rec-edge edge-${s.kind}${s.active ? ' active' : ''}${s.done ? ' done' : ''}${s.ghost ? ' ghost' : ''}`} data-edge={e.id}>
              <path d={d} className="edge-line" markerEnd={`url(#arrow-${s.kind})`} />
              {s.active && <path d={d} className="edge-flow" />}
              {s.active && <circle r="5" className="edge-pulse"><animateMotion dur="1.4s" repeatCount="indefinite" path={d} /></circle>}
              {!s.ghost && <text x={m.x} y={m.y - 8} textAnchor="middle" className="edge-label">{e.label}</text>}
            </g>
          );
        })}
        {FLOW_NODES.map((n) => {
          const p = POS[n.id];
          const state = nodeFill(n.id);
          const tools = SPECIALISTS.includes(n.id) ? (st.tools[n.id] ?? []) : [];
          return (
            <g key={n.id} className={`rec-gnode node-${state} type-${n.type.split(' ')[0].toLowerCase()}`} data-node={n.id} aria-current={st.active === n.id ? 'step' : undefined} transform={`translate(${p.x},${p.y})`}>
              <rect width={NW} height={NH} rx="14" className="node-card" />
              <circle cx="20" cy="20" r="11" className="node-icon-bg" />
              <text x="20" y="25" textAnchor="middle" className="node-icon">{n.icon}</text>
              <text x="38" y="24" className="node-type">{n.type.toUpperCase()}</text>
              <text x="12" y="48" className="node-name">{n.label}</text>
              {state === 'ghost' && <text x="12" y="60" className="node-note">skipped by host</text>}
              {state === 'active' && st.waiting && <text x={NW / 2} y={NH + 16} textAnchor="middle" className="node-wait">⏳ local pacing wait</text>}
              {tools.map((t, i) => (
                <g key={t} transform={`translate(0,${NH + 10 + i * 20})`} className={`rec-toolchip${st.active === n.id && st.tool === t ? ' on' : ''}`}>
                  <rect width={NW} height="16" rx="8" />
                  <text x="9" y="12">⚙ {t}</text>
                </g>
              ))}
            </g>
          );
        })}
      </svg>
      <p className="rec-payload" aria-live="polite"><strong>{stepLabel(cur)}</strong>{payloadCaption(cur) ? ` — ${payloadCaption(cur)}` : ''}</p>
    </div>
  );
}
