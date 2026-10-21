import { act, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import App from './App';

beforeEach(() => {
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
});

afterEach(() => {
  window.history.replaceState(null, '', '/');
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function setup() {
  const fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function navigate(hash: string) {
  act(() => {
    window.history.replaceState(null, '', `/${hash}`);
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  });
}

const nav = () => within(screen.getByRole('navigation', { name: 'Main navigation' }));

it.each(['/', '/#intro', '/workspace/?lesson=start'])('opens Home for %s without rewriting the URL', (url) => {
  window.history.replaceState(null, '', url);
  const fetchMock = setup();
  render(<App />);
  expect(window.location.pathname + window.location.search + window.location.hash).toBe(url);
  expect(screen.getByRole('heading', { level: 1, name: 'Decision Models' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Decision Models' })).toHaveAttribute('href', '#intro');
  expect(screen.getByRole('heading', { name: 'Explore how decision models work' })).toBeInTheDocument();
  expect(screen.queryByText(/Synthetic evidence only\. No external actions executed\./)).not.toBeInTheDocument();
  expect(nav().getAllByRole('link').map((link) => link.textContent)).toEqual(['Home', 'Learn', 'Demo showcase']);
  expect(nav().getByRole('link', { name: 'Home' })).toHaveAttribute('aria-current', 'page');
  expect(nav().getByRole('link', { name: 'Learn' })).not.toHaveAttribute('aria-current');
  expect(screen.getByRole('link', { name: 'Dive into how it works' })).toHaveAttribute('href', '#learn');
  expect(document.querySelector('a[href="#run"], a[href="#compare"]')).toBeNull();
  expect(fetchMock).not.toHaveBeenCalled();
});

it('opens the recorded Learn walkthrough for #learn with no API calls', () => {
  window.history.replaceState(null, '', '/#learn');
  const fetchMock = setup();
  render(<App />);
  expect(window.location.hash).toBe('#learn');
  expect(nav().getByRole('link', { name: 'Learn' })).toHaveAttribute('aria-current', 'page');
  expect(nav().getByRole('link', { name: 'Home' })).not.toHaveAttribute('aria-current');
  expect(screen.getByRole('link', { name: 'Decision Models' })).toHaveAttribute('href', '#intro');
  expect(screen.getByRole('heading', { name: 'Follow the recorded shortage' })).toBeInTheDocument();
  expect(screen.getAllByRole('tab')).toHaveLength(5);
  expect(screen.getByText(/Recorded model calls · synthetic facts · pending human review/)).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
});

it('updates the active route on hash changes and returns to Home when the hash is cleared', () => {
  window.history.replaceState(null, '', '/');
  setup();
  render(<App />);
  for (const [hash, label, heading] of [
    ['#learn', 'Learn', 'Follow the recorded shortage'],
    ['#intro', 'Home', 'Explore how decision models work'],
    ['#learn', 'Learn', 'Follow the recorded shortage'],
    ['', 'Home', 'Explore how decision models work'],
  ]) {
    navigate(hash);
    expect(window.location.hash).toBe(hash);
    expect(nav().getByRole('link', { name: label })).toHaveAttribute('aria-current', 'page');
    expect(nav().getAllByRole('link').filter((l) => l.getAttribute('aria-current') === 'page')).toHaveLength(1);
    expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument();
  }
});

it.each(['#run', '#compare', '#unexpected'])('resolves removed or unknown %s to Learn with no Run or Compare UI', (hash) => {
  window.history.replaceState(null, '', `/${hash}`);
  const fetchMock = setup();
  render(<App />);
  expect(window.location.hash).toBe('#learn');
  expect(screen.getByRole('heading', { name: 'Follow the recorded shortage' })).toBeInTheDocument();
  expect(nav().getAllByRole('link').map((l) => l.textContent)).toEqual(['Home', 'Learn', 'Demo showcase']);
  expect(screen.queryByRole('button', { name: /start|live|replay/i })).not.toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: /API connectivity/ })).not.toBeInTheDocument();
  navigate('#compare');
  expect(window.location.hash).toBe('#learn');
  expect(fetchMock).not.toHaveBeenCalled();
});
it('switches between demo-showcase routes and keeps legacy #recordings links working on hash change without falling back to Learn', async () => {
  window.history.replaceState(null, '', '/#recordings');
  const fetchMock = vi.fn(async () => ({ ok: true, status: 200, json: async () => [] }));
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);
  expect(await screen.findByRole('alert')).toBeTruthy();
  navigate('#recordings/nope');
  expect(await screen.findByRole('alert')).toBeTruthy();
  expect(window.location.hash).toBe('#showcase/nope');
});

it('scrolls to the top when the route changes', () => {
  setup();
  const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  render(<App />);
  navigate('#learn');
  expect(scroll).toHaveBeenCalledWith(0, 0);
  scroll.mockClear();
  navigate('#intro');
  expect(scroll).toHaveBeenCalledWith(0, 0);
});
