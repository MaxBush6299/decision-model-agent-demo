import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { RecordingsPage } from './RecordingsPage';
import { chipOf, flowAt, kpis, outcomeOf, routingOf, transcriptSections, type Recording } from '../recordings/model';

const dir = join(process.cwd(), 'public', 'recordings', 'v2');
const load = <T,>(f: string) => JSON.parse(readFileSync(join(dir, f), 'utf8')) as T;

function mockFetch() {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    const file = String(url).split('/recordings/v2/')[1];
    return { ok: true, status: 200, json: async () => load(file) };
  }));
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it('derives outcomes, counts and routing from recordings', () => {
  const q = load<Recording>('quality-hold.json');
  expect(outcomeOf(q).kind).toBe('pending');
  expect(kpis(q).gpt).toBe(5);
  expect(kpis(q).decision).toBe(3);
  expect(routingOf(q)).not.toBeNull();
  expect(outcomeOf(load<Recording>('order-pull-forward.json')).kind).toBe('complete');
  expect(transcriptSections(q).length).toBeGreaterThan(0);
  expect(q.timeline.every((e) => ['D1', 'LLM', 'Tool', 'Wait', 'Host'].includes(chipOf(e)))).toBe(true);
});

it('lists the four scenarios with run counts', async () => {
  mockFetch();
  render(<RecordingsPage />);
  expect(await screen.findByText(/Pick a replay/)).toBeTruthy();
  expect(screen.getAllByText(/Watch replay/)).toHaveLength(4);
});

it('shows disclosure and steps through a recording', async () => {
  mockFetch();
  render(<RecordingsPage scenario="order-pull-forward" />);
  expect(await screen.findByText(/selected/i, { selector: 'strong' })).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Next' }));
  expect(screen.getByText(/Step 2 of/)).toBeTruthy();
  fireEvent.click(screen.getByRole('tab', { name: 'Audit trail' }));
  expect(screen.getByRole('table')).toBeTruthy();
  fireEvent.click(screen.getByRole('tab', { name: 'Runs & disclosure' }));
  expect(screen.getByText(/not a representative sample/)).toBeTruthy();
});

it('discloses a non-selected pending attempt', async () => {
  mockFetch();
  render(<RecordingsPage scenario="carrier-delay" runId="C01" />);
  expect(await screen.findByText(/non-selected/)).toBeTruthy();
  expect(screen.getAllByText(/Held for a person|pending/i).length).toBeGreaterThan(0);
});

it('rejects unknown scenarios', async () => {
  mockFetch();
  render(<RecordingsPage scenario="nope" />);
  expect(await screen.findByRole('alert')).toBeTruthy();
});

it('relabels validation-below-policy pending runs and lights nodes from events', async () => {
  const c01 = load<Recording>('carrier-delay.C01.json');
  expect(outcomeOf(c01).label).toBe('Pending: validation below policy');
  expect(outcomeOf(load<Recording>('production-resequence.P01.json')).label).toBe('Pending: validation below policy');
  expect(outcomeOf(load<Recording>('quality-hold.json')).label).toBe('Held for a person (pending)');
  const q = load<Recording>('quality-hold.json');
  const end = flowAt(q.timeline, q.timeline.length - 1);
  expect(end.active).toBe('final');
  expect(end.skipped.has('production' as never)).toBe(true);
  expect(end.visited.has('coordinator')).toBe(true);
  expect(flowAt(q.timeline, 0).active).toBe('request');
});

it('every recording opens', async () => {
  mockFetch();
  const ids: [string, string | undefined][] = [['quality-hold', undefined], ['carrier-delay', undefined], ['carrier-delay', 'C01'], ['production-resequence', undefined], ['production-resequence', 'P01'], ['order-pull-forward', undefined]];
  for (const [s, r] of ids) {
    const { unmount } = render(<RecordingsPage scenario={s} runId={r} />);
    expect(await screen.findByRole('group', { name: 'Request flow' })).toBeTruthy();
    unmount();
  }
});

it('flow canvas shows tools, parallel specialists and the no-specialist path from recorded events only', async () => {
  const { FlowCanvas } = await import('../recordings/FlowCanvas');
  const o = load<Recording>('order-pull-forward.json');
  const lastIdx = o.timeline.length - 1;
  const { container, rerender } = render(<FlowCanvas timeline={o.timeline} idx={lastIdx} />);
  expect(container.querySelectorAll('[data-node]').length).toBe(9);
  expect(container.querySelectorAll('.rec-toolchip').length).toBeGreaterThan(0);
  expect(container.querySelector('[data-edge="routing-coordinator"]')).toBeNull();
  const c = load<Recording>('carrier-delay.json');
  rerender(<FlowCanvas timeline={c.timeline} idx={c.timeline.length - 1} />);
  expect(container.querySelector('[data-edge="routing-coordinator"]')).not.toBeNull();
  expect(container.querySelectorAll('.rec-toolchip').length).toBe(0);
  expect(container.querySelector('[data-node="production"]')?.getAttribute('class')).toContain('node-ghost');
});
