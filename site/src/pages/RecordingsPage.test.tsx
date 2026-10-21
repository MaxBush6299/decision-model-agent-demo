import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { RecordingsPage } from './RecordingsPage';
import { chipOf, kpis, outcomeOf, routingOf, transcriptSections, type Recording } from '../recordings/model';

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
  expect(await screen.findByText(/Watch real runs/)).toBeTruthy();
  expect(screen.getAllByText('Open replay')).toHaveLength(4);
  expect(screen.getAllByText(/runs? recorded/).length).toBeGreaterThanOrEqual(4);
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
