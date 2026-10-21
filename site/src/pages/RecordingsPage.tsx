import { useEffect, useMemo, useRef, useState } from 'react';
import {
  attemptLabel, chipOf, kpis, outcomeOf, playbackDelayMs, routingOf, SCENARIO_SUMMARIES, SCENARIO_TITLES, stepLabel, transcriptSections,
  type IndexEntry, type Recording, type TimelineEvent,
} from '../recordings/model';
import { FlowCanvas } from '../recordings/FlowCanvas';

const BASE = `${import.meta.env.BASE_URL}recordings/v2/`;
// Demo mode: the audit, disclosure, tour, routing and step panels stay in code but are hidden. Set to true to restore them.
const SHOW_DETAIL_PANELS = false;
const NOT_RELIABILITY = 'These are recorded observations of single runs on synthetic data. They show how the system behaved, not how reliable it is, and make no readiness claim.';

async function getJson<T>(file: string): Promise<T> {
  const res = await fetch(`${BASE}${file}`);
  if (!res.ok) throw new Error(`Could not load ${file} (${res.status})`);
  return (await res.json()) as T;
}

export function RecordingsPage({ scenario, runId, detail }: { scenario?: string; runId?: string; detail?: boolean }) {
  const [index, setIndex] = useState<IndexEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getJson<IndexEntry[]>('index.json').then(setIndex).catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <p role="alert">Demo showcase unavailable: {error}</p>;
  if (!index) return <p className="note">Loading demo showcase…</p>;
  const entry = scenario ? index.find((e) => e.scenario === scenario) : index[0];
  if (scenario && !entry) return <p role="alert">Unknown scenario “{scenario}”. <a href="#showcase">Back to the demo showcase</a></p>;
  if (!entry) return <p role="alert">Demo showcase unavailable: no scenarios.</p>;
  return (
    <div className={`learn-page rec-page${detail ?? SHOW_DETAIL_PANELS ? '' : ' rec-compact'}`}>
      <Selector index={index} current={entry.scenario} />
      <Viewer key={`${entry.scenario}/${runId ?? entry.selected}`} entry={entry} runId={runId} detail={detail ?? SHOW_DETAIL_PANELS} />
    </div>
  );
}

function Selector({ index, current }: { index: IndexEntry[]; current: string }) {
  const [recs, setRecs] = useState<Record<string, Recording>>({});
  useEffect(() => {
    index.forEach((e) => getJson<Recording>(e.file).then((r) => setRecs((p) => ({ ...p, [e.scenario]: r }))).catch(() => undefined));
  }, [index]);
  return (
    <nav className="rec-selector" aria-label="Choose a scenario">
      {index.map((e) => {
        const meta = SCENARIO_TITLES[e.scenario];
        const rec = recs[e.scenario];
        const out = rec ? outcomeOf(rec) : null;
        return (
          <a key={e.scenario} className={`rec-card rec-${out?.kind ?? 'other'}`} href={`#showcase/${e.scenario}`} aria-current={e.scenario === current ? 'true' : undefined}>
            <h3>{meta?.title ?? e.scenario}</h3>
            {out && <span className={`rec-chip rec-chip-${out.kind}`}>{out.label}</span>}
          </a>
        );
      })}
    </nav>
  );
}
const TOUR = [
  { id: 'kpis', title: 'Run summary', text: 'These cards count events straight from the recording: model calls, tool calls, recorded time and tokens. Nothing is estimated.' },
  { id: 'routing', title: 'Who picks the path', text: 'Decision-1 answers a routing question for each specialist. The host’s policy code, not the model, applies the routing and the final status.' },
  { id: 'player', title: 'Step through or watch', text: 'Use Back/Next to step, or Play for timed playback of the recorded timings. Skip long waits compresses idle gaps and says so.' },
  { id: 'steps', title: 'Selected step', text: 'The panel shows the exact recorded step you are on. Open the Audit trail tab for every event.' },
  { id: 'disclosure', title: 'How this run was chosen', text: 'Each replay was selected after the fact; the Runs & disclosure tab explains the rule and links the other attempts, including non-successes.' },
];

function Viewer({ entry, runId, detail }: { entry: IndexEntry; runId?: string; detail: boolean }) {
  const showId = runId ?? entry.selected;
  const file = showId === entry.selected ? entry.file : entry.other_attempts.find((o) => o.id === showId)?.file;
  const [rec, setRec] = useState<Recording | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'overview' | 'audit' | 'runs'>('overview');
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(4);
  const [skipWaits, setSkipWaits] = useState(true);
  const [tour, setTour] = useState<number | null>(null);
  const [started, setStarted] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [livePane, setLivePane] = useState(() => { try { return sessionStorage.getItem('showcase-live-pane') === 'open'; } catch { return false; } });
  const toggleLive = () => { const n = !livePane; setLivePane(n); try { sessionStorage.setItem('showcase-live-pane', n ? 'open' : 'closed'); } catch { /* ignore */ } };

  useEffect(() => {
    if (!file) { setError(`Run ${showId} is not part of this recording set.`); return; }
    getJson<Recording>(file).then(setRec).catch((e: Error) => setError(e.message));
  }, [file, showId]);

  const timeline = rec?.timeline ?? [];
  useEffect(() => {
    if (!playing || !rec || idx >= timeline.length - 1) { if (playing && rec) setPlaying(false); return; }
    const id = window.setTimeout(() => setIdx((i) => i + 1), playbackDelayMs(timeline[idx], timeline[idx + 1], speed, skipWaits));
    return () => window.clearTimeout(id);
  }, [playing, idx, speed, skipWaits, rec, timeline]);

  const sections = useMemo(() => (rec ? transcriptSections(rec) : []), [rec]);
  const termRef = useRef<HTMLDivElement>(null);
  const current: TimelineEvent | undefined = timeline[idx];
  useEffect(() => { const t = termRef.current; if (t) t.scrollTop = t.scrollHeight; }, [idx, drawer]);

  if (error) return <p role="alert">{error} <a href="#showcase">Back to the demo showcase</a></p>;
  if (!rec || !current) return <p className="note">Loading recording…</p>;

  const meta = SCENARIO_TITLES[entry.scenario];
  const out = outcomeOf(rec);
  const k = kpis(rec);
  const routing = routingOf(rec);
  const focus = (id: string) => (tour !== null && TOUR[tour].id === id ? ' tour-focus' : '');
  const revealed = sections.filter((s) => s.revealAt <= current.seq);
  const atEnd = idx >= timeline.length - 1;
  const isSelected = rec.disclosure.shown_is_selected !== false;
  const donut = donutSegments(routing);

  return (
    <div className="rec-viewer">
      <header className="rec-viewer-head">
        <div>
          {detail && <p className="eyebrow">Demo showcase · replay of {showId} · captured {rec.captured_utc_date}</p>}
          <h2>{meta?.title ?? entry.scenario} <span className={`rec-chip rec-chip-${out.kind}`}>{out.label}</span>{detail && <> <span className="badge">Recorded live</span> <span className="badge">Synthetic data</span> <span className="badge">No live calls</span></>}</h2>
          <p className="learn-deck">{meta?.question}</p>
          {SCENARIO_SUMMARIES[entry.scenario] && <p className="rec-summary">{SCENARIO_SUMMARIES[entry.scenario]}</p>}
        </div>
        {detail && <button type="button" className="rec-tour-btn" onClick={() => setTour(tour === null ? 0 : null)}>{tour === null ? 'Tour' : 'Close tour'}</button>}
      </header>
      {detail && tour !== null && (
        <aside className="rec-tour" role="dialog" aria-label="Guided tour">
          <strong>{TOUR[tour].title}</strong> <span className="note">({tour + 1}/{TOUR.length})</span>
          <p>{TOUR[tour].text}</p>
          <button type="button" disabled={tour === 0} onClick={() => setTour(tour - 1)}>Previous</button>
          {tour < TOUR.length - 1
            ? <button type="button" onClick={() => setTour(tour + 1)}>Next</button>
            : <button type="button" onClick={() => setTour(null)}>Done</button>}
        </aside>
      )}

      {detail && <div className="rec-disclosure-banner" data-tour="disclosure">
        {isSelected
          ? <>This replay was <strong>selected</strong> after the fact; other attempts, where they exist, are listed under Runs &amp; disclosure.</>
          : <>Showing <strong>{showId}</strong>, a <strong>non-selected</strong> attempt. The selected run is <a href={`#showcase/${entry.scenario}`}>{rec.disclosure.selected}</a>.</>}
        {' '}<a href="#showcase" onClick={(e) => { e.preventDefault(); setTab('runs'); }}>See all attempts</a>. {NOT_RELIABILITY}
      </div>}

      {detail && <div role="tablist" className="rec-tabs" aria-label="Recorded run views">
        {([['overview', 'Overview'], ['audit', 'Audit trail'], ['runs', 'Runs & disclosure']] as const).map(([id, label]) => (
          <button key={id} role="tab" type="button" aria-selected={tab === id} onClick={() => setTab(id)}>{label}</button>
        ))}
      </div>}

      {tab === 'overview' && (
        <div className="rec-overview">
          <div className="rec-top">
            <section className="rec-stage" aria-label="Request flow stage">
              <FlowCanvas timeline={timeline} idx={idx} />
              <div className="rec-controls" role="group" aria-label="Playback controls">
                <button type="button" onClick={() => { setPlaying(false); setIdx(0); setStarted(false); }}>Restart</button>
                <button type="button" disabled={idx === 0} onClick={() => { setPlaying(false); setStarted(true); setIdx(idx - 1); }}>Back</button>
                <button type="button" disabled={atEnd} onClick={() => { setPlaying(false); setStarted(true); setIdx(idx + 1); }}>Next</button>
                <button type="button" onClick={() => { if (atEnd) setIdx(0); setStarted(true); setPlaying(!playing); }}>{playing ? 'Pause' : 'Play'}</button>
                <label>Speed <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>{[1, 2, 4, 8, 16].map((s) => <option key={s} value={s}>{s}×</option>)}</select></label>
                <label><input type="checkbox" checked={skipWaits} onChange={(e) => setSkipWaits(e.target.checked)} /> Skip long waits (compressed)</label>
              </div>
              <p className="rec-clock" aria-live="polite">Step {idx + 1} of {timeline.length} · recorded time {current.t_offset_s.toFixed(1)} s{skipWaits ? ' · long gaps compressed in playback' : ''}</p>
              <p className="rec-footnote">{isSelected ? 'Replay of a real recorded run, selected after the fact.' : 'Replay of a real recorded attempt that was not the selected run.'}</p>
            </section>
            <div             className={`rec-livewrap${livePane ? ' open' : ''}`}>              <button type="button" className="rec-live-tab" aria-expanded={livePane} aria-controls="rec-live-pane" onClick={toggleLive}>
                <span className="rec-live-tab-title">Live step {livePane ? '›' : '‹'}</span>
                {started && <span className={`rec-tag tag-${chipOf(current)}`}>{chipOf(current)}</span>}
                {started && !livePane && <span className="rec-live-tab-actor">{stepLabel(current)}</span>}
              </button>
              {livePane && <div id="rec-live-pane" className="rec-livebody"><LiveStep e={current} started={started} /></div>}
            </div>
          </div>

          <section className={`rec-kpis${focus('kpis')}`} aria-label="Run summary" title="Counts come from the recorded debug events. Token usage is as returned by the service; a request without usage counts as zero here.">
            <Kpi label="Host outcome" value={out.label} tone={out.kind} />
            <Kpi label="Decision-1 calls" value={String(k.decision)} tone="d1" />
            <Kpi label="GPT calls" value={String(k.gpt)} tone="llm" />
            <Kpi label="Tool calls" value={String(k.tools)} tone="tool" />
            <Kpi label="Recorded time" value={`${k.wallSeconds.toFixed(0)} s`} sub={`${k.waitSeconds.toFixed(0)} s local pacing`} tone="wait" />
            <Kpi label="Tokens in / out" value={`${k.inputTokens.toLocaleString()} / ${k.outputTokens.toLocaleString()}`} tone="wait" />
          </section>

          {detail && <section className={`rec-routing${focus('routing')}`} aria-label="Decision-1 routing">
            <h3>Decision-1 routing → outcomes</h3>
            {routing ? (
              <div className="rec-flow">
                <svg viewBox="0 0 120 120" role="img" aria-label={`Routing: ${routing.consult.length} consulted, ${routing.skipped.length} skipped, ${routing.uncertain.length} uncertain`} className="rec-donut">
                  {donut.map((s) => <circle key={s.cls} className={s.cls} cx="60" cy="60" r="40" fill="none" strokeWidth="18" strokeDasharray={`${s.len} ${251.33 - s.len}`} strokeDashoffset={-s.off} transform="rotate(-90 60 60)" />)}
                  <text x="60" y="58" textAnchor="middle" className="rec-donut-n">{routing.consult.length + routing.skipped.length + routing.uncertain.length}</text>
                  <text x="60" y="74" textAnchor="middle" className="rec-donut-l">routed</text>
                </svg>
                <div className="rec-lanes">
                  <Lane cls="skip" title="Skipped by host" names={routing.skipped} note="Decision-1 said the specialist was not needed." />
                  <Lane cls="llm" title="Consulted: LLM writes" names={routing.consult} note="A specialist agent ran with synthetic read-only tools." />
                  <Lane cls="hold" title="Uncertain: conservative path" names={routing.uncertain} note="Cannot-determine is not a business verdict." />
                </div>
                <div className={`rec-final rec-final-${out.kind}`}>
                  <strong>{out.label}</strong>
                  <span>Final status set by host policy code.</span>
                </div>
              </div>
            ) : <p className="note">No routing event was recorded for this run.</p>}
            <p className="rec-caption">Policy code, not the model, picks the path. Decision-1 never approves an action, and “advisory complete” is not execution, safety certification or customer commitment. Probability and confidence are separate fields (see the Audit trail).</p>
          </section>}

          {detail && <aside className={`rec-selected${focus('steps')}`} aria-label="Selected step">
            <h3>Selected step</h3>
            <StepDetail e={current} />
            <h4>Steps</h4>
            <ol className="rec-steps">
              {timeline.map((e, i) => (
                <li key={e.seq} className={i === idx ? 'on' : i < idx ? 'done' : ''}>
                  <button type="button" aria-current={i === idx ? 'step' : undefined} onClick={() => { setPlaying(false); setStarted(true); setIdx(i); }}>
                    <span className={`rec-tag tag-${chipOf(e)}`}>{chipOf(e)}</span> {stepLabel(e)}
                  </button>
                </li>
              ))}
            </ol>
          </aside>}

          <section className={`rec-drawer${drawer ? ' open' : ''}${focus('player')}`} aria-label="Replay">
            <button type="button" className="rec-drawer-toggle" aria-expanded={drawer} onClick={() => setDrawer(!drawer)}>{drawer ? 'Hide terminal' : 'Show terminal'}</button>
            {drawer && (
              <>
                <div className="rec-terminal" ref={termRef} tabIndex={0} role="log" aria-label="Terminal transcript">
                  {revealed.map((s, i) => (
                    <pre key={`${s.title}-${i}`} className={`rec-term-sec${i === revealed.length - 1 ? ' active' : ''}`} data-section={s.title}>{s.lines.join('\n')}</pre>
                  ))}
                  <span className="rec-cursor" aria-hidden="true">▌</span>
                </div>
                <p className="rec-caption">Sections of the sanitized transcript appear when their matching recorded step completes; the capture has no per-line timing, so none is invented within a section.</p>
              </>
            )}
          </section>
        </div>
      )}

      {tab === 'audit' && <Audit rec={rec} />}
      {tab === 'runs' && <Runs entry={entry} rec={rec} showId={showId} focus={focus('disclosure')} />}
    </div>
  );
}

function LiveStep({ e, started }: { e: TimelineEvent; started: boolean }) {
  if (!started) {
    return <aside className="rec-live" aria-label="Live step"><h3>Live step</h3><p className="rec-live-idle">Press play to watch this recorded run step by step.</p></aside>;
  }
  const tag = chipOf(e);
  return (
    <aside className="rec-live" aria-label="Live step">
      <h3>Live step</h3>
      <div className="rec-detail" aria-live="polite">
        <p><span className={`rec-tag tag-${tag}`}>{tag}</span> <strong>{stepLabel(e)}</strong></p>
        <p className="note">Recorded at {e.t_offset_s.toFixed(1)} s{e.elapsed_ms !== undefined ? ` · took ${(e.elapsed_ms / 1000).toFixed(2)} s` : ''}{e.http_status ? ` · HTTP ${e.http_status}` : ''}</p>
        {e.answers && Object.entries(e.answers).map(([name, a]) => (
          <div key={name} className="rec-answer">
            <p><strong>{name}</strong>: {a.choice}</p>
            {Object.entries(a.probabilities).sort((x, y) => y[1] - x[1]).map(([c, p]) => (
              <div className="rec-bar" key={c}><span>{c}</span><i style={{ width: `${(p * 100).toFixed(1)}%` }} /><b>{(p * 100).toFixed(1)}%</b></div>
            ))}
          </div>
        ))}
        {e.kind === 'routing' && e.detail?.effective && <p>Routing: {Object.entries(e.detail.effective).map(([n, v]) => `${n}: ${v}`).join('; ')}</p>}
        {e.kind === 'tool_call' && <p>Evidence <code>{e.evidence_id}</code> · {e.result_chars} characters returned (fixture, read-only).</p>}
        {e.usage && <p>Usage: {e.usage.input_tokens ?? 0} in / {e.usage.output_tokens ?? 0} out</p>}
        {e.kind === 'final' && <p>Host status <strong>{e.status}</strong> (code {e.code}) · warnings {e.warnings}</p>}
        {e.kind === 'pacing_wait' && <p>Local quota pacing before the next request.</p>}
      </div>
      <p className="rec-caption">From the recorded event, not a re-enactment.</p>
    </aside>
  );
}
function donutSegments(r: ReturnType<typeof routingOf>) {
  if (!r) return [];
  const total = r.consult.length + r.skipped.length + r.uncertain.length || 1;
  const C = 251.33;
  const parts = [{ cls: 'seg-skip', n: r.skipped.length }, { cls: 'seg-llm', n: r.consult.length }, { cls: 'seg-hold', n: r.uncertain.length }];
  let off = 0;
  return parts.filter((p) => p.n > 0).map((p) => { const len = (p.n / total) * C; const seg = { cls: p.cls, len, off }; off += len; return seg; });
}

function Kpi({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone: string }) {
  return <div className={`rec-kpi kpi-${tone}`}><span className="rec-kpi-label">{label}</span><strong>{value}</strong>{sub && <span className="rec-kpi-sub">{sub}</span>}</div>;
}

function Lane({ cls, title, names, note }: { cls: string; title: string; names: string[]; note: string }) {
  return (
    <div className={`rec-lane lane-${cls}`}>
      <strong>{title} ({names.length})</strong>
      <span>{names.length ? names.join(', ') : 'none'}</span>
      <small>{note}</small>
    </div>
  );
}

function StepDetail({ e }: { e: TimelineEvent }) {
  return (
    <div className="rec-detail" aria-live="polite">
      <p><span className={`rec-tag tag-${chipOf(e)}`}>{chipOf(e)}</span> <strong>{stepLabel(e)}</strong></p>
      <p className="note">Recorded at {e.t_offset_s.toFixed(1)} s{e.elapsed_ms !== undefined ? ` · request took ${(e.elapsed_ms / 1000).toFixed(2)} s` : ''}{e.http_status ? ` · HTTP ${e.http_status}` : ''}</p>
      {e.answers && Object.entries(e.answers).map(([name, a]) => (
        <div key={name} className="rec-answer">
          <p><strong>{name}</strong>: {a.choice} <span className="note">(model-reported confidence {(a.confidence * 100).toFixed(0)}%, separate from probability)</span></p>
          {Object.entries(a.probabilities).sort((x, y) => y[1] - x[1]).map(([c, p]) => (
            <div className="rec-bar" key={c}><span>{c}</span><i style={{ width: `${(p * 100).toFixed(1)}%` }} /><b>{(p * 100).toFixed(1)}%</b></div>
          ))}
        </div>
      ))}
      {e.kind === 'routing' && e.detail?.effective && <p>Effective routing: {Object.entries(e.detail.effective).map(([n, v]) => `${n}: ${v}`).join('; ')}</p>}
      {e.kind === 'tool_call' && <p>Evidence <code>{e.evidence_id}</code> · {e.result_chars} characters returned. Fixture, read-only.</p>}
      {e.usage && <p>Usage: {e.usage.input_tokens ?? 0} in / {e.usage.output_tokens ?? 0} out</p>}
      {e.kind === 'final' && <p>Host status <strong>{e.status}</strong> (code {e.code}) · GPT attempts {e.gpt_attempts} · Decision-1 attempts {e.decision_attempts} · transport retries {e.transport_retries} · warnings {e.warnings}</p>}
      {e.kind === 'pacing_wait' && <p>Local quota pacing before the next request (the demo paces itself to stay within its rate limit).</p>}
      <p className="rec-caption">Provenance: this step comes from the recorded run, not from a generated re-enactment.</p>
    </div>
  );
}

function Audit({ rec }: { rec: Recording }) {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <section aria-label="Audit trail">
      <h3>Audit trail</h3>
      <p className="rec-caption">Every allow-listed event captured for this run, in order. Private identifiers, message bodies and endpoints are omitted ({rec.integrity.private_fields_omitted.join(', ')}). Transcript SHA-256 of the private capture: <code>{rec.integrity.transcript_sha256.slice(0, 16)}…</code></p>
      <table className="rec-table">
        <thead><tr><th>#</th><th>Time (s)</th><th>Type</th><th>Event</th><th>Detail</th></tr></thead>
        <tbody>
          {rec.timeline.map((e) => (
            <tr key={e.seq}>
              <td>{e.seq}</td><td>{e.t_offset_s.toFixed(1)}</td>
              <td><span className={`rec-tag tag-${chipOf(e)}`}>{chipOf(e)}</span></td>
              <td>{stepLabel(e)}</td>
              <td>
                {e.http_status ? `HTTP ${e.http_status} ` : ''}{e.elapsed_ms !== undefined ? `${e.elapsed_ms} ms ` : ''}{e.usage ? `${e.usage.input_tokens ?? 0}/${e.usage.output_tokens ?? 0} tok ` : ''}
                <button type="button" aria-expanded={open === e.seq} onClick={() => setOpen(open === e.seq ? null : e.seq)}>{open === e.seq ? 'Hide' : 'Raw'}</button>
                {open === e.seq && <pre>{JSON.stringify(e, null, 2)}</pre>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Runs({ entry, rec, showId, focus }: { entry: IndexEntry; rec: Recording; showId: string; focus: string }) {
  const d = rec.disclosure;
  return (
    <section className={`rec-runs${focus}`} aria-label="Runs and disclosure">
      <h3>Selection and other attempts</h3>
      <p>The replay shown by default (<strong>{d.selected}</strong>) was <strong>selected after the fact</strong> by an independent semantic review. Rule: {d.selection_rule}. Selection favors the displayed replay, so it is not a representative sample.</p>
      <ul className="rec-attempts">
        {d.all_attempts.map((a) => {
          const link = a.id === entry.selected ? `#showcase/${entry.scenario}` : `#showcase/${entry.scenario}/${a.id}`;
          return (
            <li key={a.id}>
              <a href={link} aria-current={a.id === showId ? 'true' : undefined}>{a.id}</a>{' '}
              <span className={`rec-chip rec-chip-${a.host_status === 'advisory_complete' ? 'complete' : 'pending'}`}>{attemptLabel(a)}</span>{' '}
              {a.id === d.selected && <span className="badge">Selected</span>} <span className="note">Review: {a.review_note}</span>
            </li>
          );
        })}
      </ul>
      <p>{d.caveat} {NOT_RELIABILITY}</p>
      <p className="note">Source commit {rec.source_commit}; model profile {rec.model_profile}; transport {rec.transport}; mode {rec.mode}.</p>
    </section>
  );
}
