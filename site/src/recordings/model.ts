export type Probabilities = Record<string, number>;
export interface DecisionAnswer { choice: string; confidence: number; probabilities: Probabilities }

export interface TimelineEvent {
  seq: number;
  t_offset_s: number;
  kind: string;
  actor?: string;
  revision?: number;
  attempt?: number;
  call_kind?: string;
  http_status?: number;
  elapsed_ms?: number;
  deadline_s?: number;
  usage?: { input_tokens?: number; output_tokens?: number; total_tokens?: number };
  tool?: string;
  evidence_id?: string;
  result_chars?: number;
  seconds?: number;
  wait_kind?: string;
  answers?: Record<string, DecisionAnswer>;
  detail?: { active?: string[]; uncertain?: string[]; effective?: Record<string, string> };
  status?: string;
  code?: number;
  warnings?: number;
  gpt_attempts?: number;
  decision_attempts?: number;
  transport_retries?: number;
  scenario?: string;
  llm_profile?: string;
  gpt_deadline_s?: number;
}

export interface Attempt { id: string; host_status: string; review_note: string }

export interface Recording {
  schema_version: string;
  mode: string;
  transport: string;
  data: string;
  recording_alias: string;
  scenario: string;
  source_commit: string;
  model_profile: string;
  captured_utc_date: string;
  disclosure: {
    runs_recorded_for_scenario: number;
    selected: string;
    shown_run?: string;
    shown_is_selected?: boolean;
    selection_rule: string;
    all_attempts: Attempt[];
    caveat: string;
  };
  display_transcript: string[];
  timeline: TimelineEvent[];
  integrity: { transcript_sha256: string; private_fields_omitted: string[]; usage_note: string };
}

export interface IndexEntry {
  scenario: string;
  file: string;
  selected: string;
  runs_recorded: number;
  other_attempts: { id: string; file: string }[];
}

export const SCENARIO_TITLES: Record<string, { title: string; question: string }> = {
  'quality-hold': { title: 'Quality hold', question: 'A mounting-bracket lot is held for a quality incident. What should the team do about a delivery shortfall?' },
  'carrier-delay': { title: 'Carrier delay', question: 'The primary carrier will miss the delivery window. Is there a plan within existing authority?' },
  'production-resequence': { title: 'Production resequence', question: 'Two qualified cells could build the order. Which plan is feasible?' },
  'order-pull-forward': { title: 'Order pull-forward', question: 'A customer asked for an earlier delivery. Full-early or split shipment?' },
};

export const SCENARIO_SUMMARIES: Record<string, string> = {
  'quality-hold': 'A lot of mounting brackets is held for a quality incident, leaving a delivery shortfall. The system is deciding what the team should do next. Supply-chain and Commercial were consulted (Production was routed as not needed), and the recorded run ended pending a person’s review rather than completing.',
  'carrier-delay': 'The primary carrier will miss the 09:00–11:00 window, but all 600 units are staged and an approved alternate carrier slot is documented. The system is deciding whether a plan fits within existing authority. Decision-1 routed to no specialists, so the recorded run went straight to the Coordinator and ended advisory complete.',
  'production-resequence': 'Press P1 is unavailable until Friday 12:00, and cells P2 and P3 are both qualified but differ in setup time and rate. The system is deciding which replacement plan is feasible. Only Production was consulted, and the recorded run ended advisory complete.',
  'order-pull-forward': 'A customer asked to compare a full 400-unit early delivery with a split 160/240 shipment. The system is deciding which plan is workable. Supply-chain and Commercial were consulted (Production was routed as cannot-determine), and the recorded run ended advisory complete.',
};
export type Outcome = 'complete' | 'pending' | 'other';

export function outcomeOf(rec: Recording): { kind: Outcome; label: string } {
  const fin = rec.timeline.find((e) => e.kind === 'final');
  if (fin?.status === 'advisory_complete') return { kind: 'complete', label: 'Advisory complete' };
  if (fin?.status === 'pending') {
    const note = rec.disclosure.all_attempts.find((a) => rec.recording_alias.endsWith(a.id))?.review_note ?? '';
    return { kind: 'pending', label: /validation/i.test(note) ? 'Pending: validation below policy' : 'Held for a person (pending)' };
  }
  return { kind: 'other', label: fin?.status ?? 'No final event recorded' };
}

export function attemptLabel(a: Attempt): string {
  if (a.host_status === 'advisory_complete') return 'Advisory complete';
  return /validation/i.test(a.review_note) ? 'Pending: validation below policy' : 'Held for a person (pending)';
}

export type FlowNode = 'request' | 'd1' | 'routing' | 'supply-chain' | 'production' | 'commercial' | 'coordinator' | 'validation' | 'final';
export const FLOW_NODES: { id: FlowNode; label: string; type: string; icon: string }[] = [
  { id: 'request', label: 'Request', type: 'Request', icon: '✉' },
  { id: 'd1', label: 'Decision-1', type: 'Scorer', icon: '◈' },
  { id: 'routing', label: 'Routing', type: 'Host policy', icon: '⑂' },
  { id: 'supply-chain', label: 'Supply-chain', type: 'Agent', icon: '◉' },
  { id: 'production', label: 'Production', type: 'Agent', icon: '◉' },
  { id: 'commercial', label: 'Commercial', type: 'Agent', icon: '◉' },
  { id: 'coordinator', label: 'Coordinator', type: 'Agent', icon: '◉' },
  { id: 'validation', label: 'Validation', type: 'Scorer', icon: '◈' },
  { id: 'final', label: 'Final status', type: 'Host output', icon: '⚑' },
];

/** Node a recorded event belongs to; null when the event does not belong to a drawn node (waits keep the prior node). */
export function nodeOf(e: TimelineEvent): FlowNode | null {
  switch (e.kind) {
    case 'run_start': return 'request';
    case 'routing': return 'routing';
    case 'final': return 'final';
    case 'pacing_wait': return null;
    default:
      if (e.actor === 'assessment' || e.actor === 'selection') return 'd1';
      if (e.actor === 'supply-chain' || e.actor === 'production' || e.actor === 'commercial' || e.actor === 'coordinator' || e.actor === 'validation') return e.actor;
      return null;
  }
}

export interface FlowState { active: FlowNode | null; prev: FlowNode | null; visited: Set<FlowNode>; skipped: Set<FlowNode>; waiting: boolean; tool?: string; tools: Record<string, string[]> }

export function flowAt(timeline: TimelineEvent[], idx: number): FlowState {
  const st: FlowState = { active: null, prev: null, visited: new Set(), skipped: new Set(), waiting: false, tools: {} };
  for (let i = 0; i <= idx && i < timeline.length; i++) {
    const e = timeline[i];
    const n = nodeOf(e);
    if (e.kind === 'routing' && e.detail?.effective) {
      for (const [name, v] of Object.entries(e.detail.effective)) if (v === 'not_needed') st.skipped.add(name as FlowNode);
    }
    st.waiting = e.kind === 'pacing_wait';
    st.tool = e.kind === 'tool_call' ? e.tool : undefined;
    if (e.kind === 'tool_call' && e.actor && e.tool) st.tools[e.actor] = [...(st.tools[e.actor] ?? []).filter((t) => t !== e.tool), e.tool];
    if (n) { if (st.active && st.active !== n) { st.visited.add(st.active); st.prev = st.active; } st.active = n; }
  }
  return st;
}

export interface Kpis {
  gpt: number;
  decision: number;
  tools: number;
  wallSeconds: number;
  waitSeconds: number;
  inputTokens: number;
  outputTokens: number;
}

export function kpis(rec: Recording): Kpis {
  const k: Kpis = { gpt: 0, decision: 0, tools: 0, wallSeconds: 0, waitSeconds: 0, inputTokens: 0, outputTokens: 0 };
  for (const e of rec.timeline) {
    if (e.kind === 'model_call_end') {
      if (e.call_kind === 'gpt') k.gpt += 1;
      if (e.call_kind === 'decision') k.decision += 1;
      k.inputTokens += e.usage?.input_tokens ?? 0;
      k.outputTokens += e.usage?.output_tokens ?? 0;
    }
    if (e.kind === 'tool_call') k.tools += 1;
    if (e.kind === 'pacing_wait') k.waitSeconds += e.seconds ?? 0;
    k.wallSeconds = Math.max(k.wallSeconds, e.t_offset_s);
  }
  return k;
}

export interface Routing { consult: string[]; skipped: string[]; uncertain: string[] }

export function routingOf(rec: Recording): Routing | null {
  const ev = rec.timeline.find((e) => e.kind === 'routing');
  const eff = ev?.detail?.effective;
  if (!eff) return null;
  const r: Routing = { consult: [], skipped: [], uncertain: [] };
  for (const [name, v] of Object.entries(eff)) {
    if (v === 'needed') r.consult.push(name);
    else if (v === 'not_needed') r.skipped.push(name);
    else r.uncertain.push(name);
  }
  return r;
}

export interface Section { title: string; lines: string[]; revealAt: number }

const SECTION_RE = /^=== (.+) ===$/;

/** Sections are revealed when the matching recorded step completes; the capture has no per-line timing. */
export function transcriptSections(rec: Recording): Section[] {
  const tl = rec.timeline;
  const last = tl.length ? tl[tl.length - 1].seq : 0;
  const find = (pred: (e: TimelineEvent) => boolean) => tl.find(pred)?.seq;
  const coordStart = find((e) => e.kind === 'model_call_start' && e.actor === 'coordinator');
  const anchors: Record<string, number | undefined> = {
    'ASSESSMENT NEED': find((e) => e.kind === 'decision_result' && e.actor === 'assessment'),
    TEAM: find((e) => e.kind === 'routing'),
    FINDINGS: coordStart ? coordStart - 1 : undefined,
    'INITIAL PLAN': find((e) => e.kind === 'decision_result' && e.actor === 'validation'),
  };
  const out: Section[] = [{ title: 'Header', lines: [], revealAt: 0 }];
  for (const line of rec.display_transcript) {
    const m = SECTION_RE.exec(line);
    if (m) out.push({ title: m[1], lines: [line], revealAt: m[1] === 'CASE' ? 0 : (anchors[m[1]] ?? last) });
    else out[out.length - 1].lines.push(line);
  }
  return out.filter((s) => s.lines.length > 0);
}

export function stepLabel(e: TimelineEvent): string {
  switch (e.kind) {
    case 'run_start': return 'Run starts';
    case 'model_call_start': return `${e.call_kind === 'decision' ? 'Decision-1' : 'GPT'} request: ${e.actor}`;
    case 'model_call_end': return `${e.call_kind === 'decision' ? 'Decision-1' : 'GPT'} response: ${e.actor}`;
    case 'decision_result': return `Decision-1 answer: ${e.actor}`;
    case 'routing': return 'Host routing applied';
    case 'tool_call': return `Tool call: ${e.tool}`;
    case 'pacing_wait': return `Local pacing wait ${e.seconds ?? '?'} s`;
    case 'final': return `Final host status: ${e.status}`;
    default: return e.kind;
  }
}

export type Chip = 'D1' | 'LLM' | 'Tool' | 'Wait' | 'Host';

export function chipOf(e: TimelineEvent): Chip {
  if (e.kind === 'decision_result' || (e.kind.startsWith('model_call') && e.call_kind === 'decision')) return 'D1';
  if (e.kind.startsWith('model_call')) return 'LLM';
  if (e.kind === 'tool_call') return 'Tool';
  if (e.kind === 'pacing_wait') return 'Wait';
  return 'Host';
}

/** Playback delay in ms for the gap before `next`; waits above the cap are visibly compressed when skipWaits is on. */
export function playbackDelayMs(prev: TimelineEvent | undefined, next: TimelineEvent, speed: number, skipWaits: boolean): number {
  const gap = Math.max(0, next.t_offset_s - (prev?.t_offset_s ?? 0));
  const effective = skipWaits ? Math.min(gap, 1.2) : gap;
  return Math.max(120, (effective * 1000) / speed);
}
