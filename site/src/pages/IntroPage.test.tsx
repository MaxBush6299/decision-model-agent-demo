import { fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';
import { decisionAnnouncementUrl, decisionLearnUrl, jevContextUrl } from '../components/DecisionModelExplainer';
import { IntroPage } from './IntroPage';

it('opens with a conceptual introduction and puts the recorded case after teaching', () => {
  render(<IntroPage />);
  expect(screen.getByRole('heading', { name: 'Explore how decision models work' })).toBeVisible();
  const action = screen.getByRole('link', { name: 'Dive into how it works' });
  expect(action).toHaveAttribute('href', '#learn');
  expect(document.querySelectorAll('a[href="#learn"]')).toHaveLength(1);
  expect(screen.getByRole('heading', { name: 'Learn: how decision models work' })).toBeVisible();
  expect(document.querySelector('a[href="#run"], a[href="#compare"]')).toBeNull();
  expect(document.querySelector('.home-hero a[href="#learn"]')).toBeNull();
  for (const name of [
    'What is a decision model?',
    'Context in. A bounded answer out.',
    'Different jobs, useful together',
    'Where it fits in an agent',
    'Useful estimates, not guarantees',
  ]) {
    const heading = screen.getByRole('heading', { name });
    expect(heading).toBeVisible();
    expect(heading.compareDocumentPosition(action) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  }
});

it('retains original decorative illustrations supporting the introduction', () => {
  const { container } = render(<IntroPage />);
  const hero = container.querySelector('.home-hero-image');
  const supporting = container.querySelector('.home-photo');
  expect(hero).toHaveAttribute('src', `${import.meta.env.BASE_URL}home/decision-switchboard.png`);
  expect(hero).toHaveAttribute('width', '896');
  expect(hero).toHaveAttribute('height', '1120');
  expect(hero).toHaveAttribute('alt', '');
  expect(container.querySelectorAll('.home-hero-image')).toHaveLength(1);
  expect(hero?.parentElement).toHaveClass('home-hero-art');
  expect(hero?.parentElement).toHaveAttribute('aria-hidden', 'true');
  expect(container.querySelector('.home-hero-copy h2')).toHaveTextContent('Explore how decision models work');
  expect(container.querySelector('.home-hero-copy .learn-deck')).toHaveTextContent('Some AI writes an answer. A decision model helps choose among known answers. Start with what that means, then follow how a decision model, a language model, software rules, and a person work together.');
  expect(supporting).toHaveAttribute('src', `${import.meta.env.BASE_URL}home/branching-tracks.png`);
  expect(supporting).toHaveAttribute('alt', '');
  expect(supporting).toHaveAttribute('loading', 'lazy');
  expect(document.querySelectorAll('.intro-page > section h3')).toHaveLength(6);
  expect(screen.getByRole('heading', { name: 'What is a decision model?' })).toBeVisible();
});

it('highlights only the definition, complementary roles, and existing responsibility rules', () => {
  const { container } = render(<IntroPage />);
  expect(container.querySelectorAll('.home-teaching-panel')).toHaveLength(3);
  for (const [name, className] of [
    ['What is a decision model?', 'home-panel-basics'],
    ['Different jobs, useful together', 'home-panel-complement'],
    ['Useful estimates, not guarantees', 'home-panel-rules'],
  ]) {
    const panel = screen.getByRole('heading', { name }).closest('.home-teaching-panel');
    expect(panel).toHaveClass(className);
    expect(panel?.querySelector('.home-teaching-panel')).toBeNull();
    expect(within(panel as HTMLElement).getByRole('link')).toHaveAttribute('href', decisionLearnUrl);
  }
  expect(container.querySelector('.home-photo')?.closest('.home-teaching-panel')).toBeNull();
  expect(screen.getByRole('region', { name: 'Context in. A bounded answer out.' })).not.toHaveClass('home-teaching-panel');
  expect(screen.getByRole('region', { name: 'Where it fits in an agent' })).not.toHaveClass('home-teaching-panel');
  expect(container.querySelector('.home-launchpad')).not.toHaveClass('home-teaching-panel');
});

it('teaches the input, output, complementary roles, authority, and limitations without disclosures', () => {
  render(<IntroPage />);
  const basics = within(screen.getByRole('region', { name: 'What is a decision model?' }));
  expect(basics.getByText(/supply context, a bounded question, and allowed answers/)).toBeVisible();
  expect(basics.getByText(/structured choice and probabilities for the options/)).toBeVisible();
  const flow = within(screen.getByRole('region', { name: 'Context in. A bounded answer out.' }));
  expect(flow.getAllByRole('listitem')).toHaveLength(4);
  expect(flow.getByText(/not the selected-choice probability or permission to act/)).toBeVisible();
  expect(flow.getByText(/Calibration means checking that estimates match outcomes/)).toBeVisible();
  const roles = within(screen.getByRole('region', { name: 'Different jobs, useful together' }));
  expect(roles.getByText(/draft, summarize, rewrite, or explain/)).toBeVisible();
  expect(roles.getByText(/not a claim that one replaces the other/)).toBeVisible();
  const agent = within(screen.getByRole('region', { name: 'Where it fits in an agent' }));
  expect(agent.getAllByRole('listitem')).toHaveLength(4);
  expect(agent.getByText(/Ordinary application code validates the result/)).toBeVisible();
  expect(agent.getByText(/not proof of resolution or approval/)).toBeVisible();
  expect(agent.getByText(/A person retains approval authority/)).toBeVisible();
  const limits = within(screen.getByRole('region', { name: 'Useful estimates, not guarantees' }));
  expect(limits.getByText(/Errors, bias, outdated knowledge/)).toBeVisible();
  expect(limits.getByText(/Test on representative examples/)).toBeVisible();
  expect(limits.getByRole('link', { name: /Limitations and workload validation/ })).toHaveAttribute('href', decisionLearnUrl);
});

it('keeps source context in a native disclosure without internal development plumbing', () => {
  render(<IntroPage />);
  const summary = screen.getByText('Sources and context');
  expect(summary.closest('details')).not.toHaveAttribute('open');
  expect(screen.getByText('Sources and what they support')).not.toBeVisible();
  fireEvent.click(summary);
  const sources = within(screen.getByRole('region', { name: 'Sources and what they support' }));
  expect(sources.getAllByRole('link')).toHaveLength(3);
  expect(sources.getByRole('link', { name: /L1/ })).toHaveAttribute('href', decisionLearnUrl);
  expect(sources.getByRole('link', { name: /M1/ })).toHaveAttribute('href', decisionAnnouncementUrl);
  expect(sources.getByRole('link', { name: /N1/ })).toHaveAttribute('href', jevContextUrl);
  expect(sources.getByText(/original AI-generated illustrations, created with MAI-Image-2.5/)).toBeVisible();
  expect(document.body.textContent).not.toMatch(/LOCAL MOCK|HARD BLOCKED|Developer view|optional local Live|workspace/i);
  fireEvent.click(summary);
  expect(screen.getByText('Sources and what they support')).not.toBeVisible();
});

it('links Home to the Demo showcase without readiness or live claims', () => {
  render(<IntroPage />);
  const links = screen.getAllByRole('link', { name: /Open the Demo showcase|Explore the scenarios/ });
  expect(links).toHaveLength(2);
  links.forEach((l) => expect(l).toHaveAttribute('href', '#showcase'));
  expect(screen.getByRole('heading', { name: 'Demo showcase' })).toBeVisible();
  expect(screen.queryByText(/selected after the fact|makes no new model calls|One recorded case/)).toBeNull();
  expect(document.body.textContent).not.toMatch(/production-ready|is reliable/);
});
