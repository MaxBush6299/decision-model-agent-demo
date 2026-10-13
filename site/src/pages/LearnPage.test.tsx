import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import App from '../App';
import { decisionResultSetSchema, questionCatalog } from '../contracts';
import { DecisionModelExplainer, decisionLearnUrl, mockRequest, mockResponse } from '../components/DecisionModelExplainer';
import { capture, proposalContent, routeAnswer, terminalStages, validationAnswer } from '../data/recordedCli';
import { IntroPage } from './IntroPage';
import { LearnPage } from './LearnPage';

const scrollIntoViewDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollIntoView');
beforeEach(() => {
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() });
});

afterEach(() => {
  window.history.replaceState(null, '', '/');
  vi.unstubAllGlobals();
  if (scrollIntoViewDescriptor) {
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', scrollIntoViewDescriptor);
  } else {
    Reflect.deleteProperty(HTMLElement.prototype, 'scrollIntoView');
  }
});

it('shows five reached stages, provenance, exact initial issue and terminal output without animations', () => {
  render(<LearnPage />);
  const tabs = within(screen.getByRole('tablist', { name: 'Recorded CLI steps' })).getAllByRole('tab');
  expect(tabs).toHaveLength(5);
  expect(tabs[0]).toHaveAttribute('aria-selected', 'true');
  expect(tabs.slice(1).every((tab) => tab.getAttribute('tabindex') === '-1')).toBe(true);
  expect(screen.getByText(/Recorded model calls · synthetic facts · pending human review/)).toBeVisible();
  fireEvent.click(screen.getByText('Recording details and interpretation'));
  expect(screen.getByText(/2 Decision-1 calls · 1 GPT-4.1-mini call · no retries/)).toBeVisible();
  expect(screen.getByText(capture.captureStartedAtUtc)).toBeVisible();
  expect(screen.getByText('Sanitized published capture.')).toBeVisible();
  expect(screen.getByText(/not byte-for-byte raw captures/)).toBeVisible();
  expect(screen.queryByText(/No body redactions were applied/)).not.toBeInTheDocument();
  expect(screen.getByRole('region', { name: 'Original synthetic issue' }).textContent).toBe(capture.calls[0].requestBody.state);
  expect(screen.getByRole('region', { name: 'Recorded command' }).textContent).toBe(capture.command);
  expect(screen.getByRole('region', { name: 'Actual terminal output for this step' }).textContent).toBe(terminalStages[0]);
  expect(screen.queryByRole('button', { name: 'Play' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Previous step' })).toBeDisabled();
});

it('shows accessible stage maps without changing captured evidence or mixing review origins', () => {
  render(<LearnPage />);
  const titles = [
    'Build one bounded routing question',
    'A routing choice is checked before handoff',
    'The specialist drafts advice, not an action',
    'Validate the proposal against the original issue',
    'Review origins stay distinct at the human checkpoint',
  ];
  const nodeCounts = [3, 3, 3, 4, 4];
  for (let step = 0; step < titles.length; step++) {
    fireEvent.click(screen.getByRole('tab', { name: new RegExp(`Step ${step + 1}`) }));
    const diagram = screen.getByRole('figure', { name: new RegExp(titles[step]) });
    expect(diagram).toBeVisible();
    expect(within(diagram).getAllByRole('listitem')).toHaveLength(nodeCounts[step]);
    for (const icon of diagram.querySelectorAll('svg')) {
      expect(icon).toHaveAttribute('aria-hidden', 'true');
      expect(icon).toHaveAttribute('focusable', 'false');
    }
    expect(screen.getByRole('region', { name: 'Actual terminal output for this step' }).textContent).toBe(terminalStages[step]);
    if (step === 1) expect(within(diagram).getByText(routeAnswer.choice)).toBeVisible();
    if (step === 3) {
      expect(within(diagram).getByText('original_issue')).toBeVisible();
      expect(within(diagram).getByText('Actual proposal')).toBeVisible();
      expect(within(diagram).getByText(validationAnswer.choice)).toBeVisible();
    }
    if (step === 4) {
      expect(within(diagram).getAllByText('Not triggered')).toHaveLength(2);
      expect(within(diagram).getByText('Triggered in this recording')).toBeVisible();
      expect(within(diagram).getByText('Pending')).toBeVisible();
      expect(within(diagram).getByText('No acceptance recorded; no action executed.')).toBeVisible();
    }
  }
});

it('consolidates the complete routing request, explanatory envelope and field purposes in Step 1', () => {
  render(<LearnPage />);
  const checkRequest = () => {
    const request = screen.getByRole('region', { name: 'Sanitized Decision-1 routing request JSON' });
    expect(request).toBeVisible();
    expect(request.closest('details')).toBeNull();
    expect(JSON.parse(request.textContent!)).toEqual(capture.calls[0].requestBody);
    expect(screen.getByRole('region', { name: 'Explanatory Decision-1 HTTP envelope' }).textContent).toBe(
      'POST https://example.services.ai.azure.com/providers/microsoft/v1/systemone\nAuthorization: Bearer <Entra access token>\nContent-Type: application/json',
    );
    expect(screen.getByText('https://cognitiveservices.azure.com/.default')).toBeVisible();
    const table = screen.getByRole('table', { name: 'Decision-1 request fields' });
    for (const field of ['model', 'state', 'questions', 'type', 'instructions', 'criteria']) {
      expect(within(table).getByRole('rowheader', { name: field })).toBeVisible();
    }
    expect(within(table).getByRole('row', { name: /^model\b/ })).toHaveTextContent('YOUR-DECISION-1-DEPLOYMENT');
    expect(within(table).getByRole('row', { name: /^model\b/ })).toHaveTextContent('not the underlying model name Microsoft-Decision-1');
    expect(screen.getByText(/context \+ a bounded question \+ labeled choices/)).toBeVisible();
    expect(screen.getByText('answers.route')).toBeVisible();
    expect(screen.getByText(/Headers were not captured/)).toBeVisible();
  };
  checkRequest();
  fireEvent.click(screen.getByRole('tab', { name: /Step 2/ }));
  expect(screen.queryByRole('region', { name: 'Sanitized Decision-1 routing request JSON' })).not.toBeInTheDocument();
  expect(screen.queryByRole('table', { name: 'Decision-1 request fields' })).not.toBeInTheDocument();
  expect(screen.queryByRole('region', { name: 'Explanatory Decision-1 HTTP envelope' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'See routing request' }));
  expect(screen.getByRole('tab', { name: /Step 1/ })).toHaveAttribute('aria-selected', 'true');
  expect(screen.getByRole('tabpanel')).toHaveFocus();
  checkRequest();
});

it('links to the full validation request without substituting or duplicating its issue and proposal', () => {
  render(<LearnPage />);
  fireEvent.click(screen.getByRole('tab', { name: /Step 2/ }));
  expect(screen.queryByRole('region', { name: 'Sanitized Decision-1 validation request JSON' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'See validation request and response' }));
  expect(screen.getByRole('tab', { name: /Step 4/ })).toHaveAttribute('aria-selected', 'true');
  expect(screen.getByRole('tabpanel')).toHaveFocus();
  const request = screen.getByRole('region', { name: 'Sanitized Decision-1 validation request JSON' });
  expect(request).toBeVisible();
  expect(request.closest('details')).toBeNull();
  expect(JSON.parse(request.textContent!)).toEqual(capture.calls[2].requestBody);
  expect(Object.keys(JSON.parse(request.textContent!).questions.validation.criteria)).toEqual([
    'Addresses the issue', 'Needs revision', 'Cannot determine',
  ]);
  expect(screen.queryByRole('region', { name: 'Actual validation state' })).not.toBeInTheDocument();
  expect(screen.getByText('answers.validation')).toBeVisible();
  expect(screen.getByText(/The model never executes an action/)).toBeVisible();
  expect(screen.getByRole('region', { name: 'Original issue beside validation' }).textContent).toBe(capture.calls[0].requestBody.state);
  expect(screen.getByRole('region', { name: 'Actual proposal beside validation' }).textContent).toBe(proposalContent);
});

it('preserves exact request/response strings, proposal and validation state through manual steps', () => {
  render(<LearnPage />);
  for (const [step, callIndex] of [[2, 0], [3, 1], [4, 2]]) {
    fireEvent.click(screen.getByRole('tab', { name: new RegExp(`Step ${step}`) }));
    const responseSummary = step === 3 ? 'Sanitized recorded request and response bodies' : 'Sanitized recorded response body';
    fireEvent.click(screen.getByText(responseSummary));
    if (step === 3) expect(screen.getByRole('region', { name: 'Sanitized recorded request body' }).textContent).toBe(capture.calls[callIndex].requestText);
    if (step === 4) {
      fireEvent.click(screen.getByText('Sanitized recorded Decision-1 request body'));
      expect(screen.getByRole('region', { name: 'Sanitized recorded request body' }).textContent).toBe(capture.calls[callIndex].requestText);
    }
    expect(screen.getByRole('region', { name: 'Sanitized recorded response body' }).textContent).toBe(capture.calls[callIndex].responseText);
    if (step === 3) expect(screen.getByRole('region', { name: 'Exact specialist response content' }).textContent).toBe(proposalContent);
    if (step === 4) expect(JSON.parse(screen.getByRole('region', { name: 'Sanitized Decision-1 validation request JSON' }).textContent!).state).toEqual(capture.calls[2].requestBody.state);
    expect(screen.getByRole('region', { name: 'Actual terminal output for this step' }).textContent).toBe(terminalStages[step - 1]);
    fireEvent.click(screen.getByText(responseSummary));
  }
  fireEvent.click(screen.getByRole('tab', { name: /Step 1/ }));
  fireEvent.click(screen.getByText('Sanitized recorded Decision-1 request body'));
  expect(screen.getByRole('region', { name: 'Sanitized recorded request body' }).textContent).toBe(capture.calls[0].requestText);
  fireEvent.click(screen.getByRole('tab', { name: /Step 4/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Next step' }));
  expect(screen.getByText(/Pending \(noninteractive input; no automatic acceptance\). Exit code 2/)).toBeVisible();
  expect(screen.getByText(/It did not fire in this run/)).toBeVisible();
  expect(screen.getByRole('button', { name: 'Next step' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Previous step' }));
  expect(screen.getByRole('tab', { name: /Step 4/ })).toHaveAttribute('aria-selected', 'true');
  fireEvent.click(screen.getByText('Full recorded stdout · verbatim, all reached stages'));
  expect(screen.getByRole('region', { name: 'Full recorded stdout' }).textContent).toBe(capture.stdout);
});

it('groups Step 4 as input, full rubric request and result without duplicating or hiding evidence', () => {
  render(<LearnPage />);
  fireEvent.click(screen.getByRole('tab', { name: /Step 4/ }));
  const panel = screen.getByRole('tabpanel');
  expect(within(panel).getByText('Original issue + specialist proposal → validation verdict')).toBeVisible();
  const input = within(panel).getByRole('region', { name: 'Input · Original issue + specialist proposal' });
  const rubric = within(panel).getByRole('region', { name: 'Rubric · Full validation request' });
  const result = within(panel).getByRole('region', { name: 'Result · Validation verdict, not approval' });
  expect(input.compareDocumentPosition(rubric) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(rubric.compareDocumentPosition(result) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  for (const group of [input, rubric, result]) {
    expect(within(group).getAllByRole('heading', { level: 4 })).toHaveLength(1);
    expect(group.closest('details')).toBeNull();
  }
  expect(within(input).getByRole('heading', { level: 5, name: 'Original issue · verbatim' })).toBeVisible();
  expect(within(input).getByRole('heading', { level: 5, name: 'Specialist proposal · verbatim' })).toBeVisible();
  expect(within(input).getByRole('region', { name: 'Original issue beside validation' }).textContent).toBe(capture.calls[0].requestBody.state);
  expect(within(input).getByRole('region', { name: 'Actual proposal beside validation' }).textContent).toBe(proposalContent);
  const request = within(rubric).getByRole('region', { name: 'Sanitized Decision-1 validation request JSON' });
  expect(request.closest('details')).toBeNull();
  expect(JSON.parse(request.textContent!)).toEqual(capture.calls[2].requestBody);
  expect(screen.getAllByRole('region', { name: 'Sanitized Decision-1 validation request JSON' })).toHaveLength(1);
  expect(within(rubric).getAllByRole('region', { name: 'Explanatory Decision-1 HTTP envelope' })).toHaveLength(1);
  expect(within(rubric).getAllByRole('table', { name: 'Decision-1 request fields' })).toHaveLength(1);
  expect(within(rubric).getByText(/Headers were not captured/)).toBeVisible();
  expect(within(rubric).getByText(/The model never executes an action/)).toBeVisible();
  expect(within(result).getByText(/not proof of resolution, permission, or action execution/)).toBeVisible();
  expect(within(result).getByText(/Passing validation does not bypass the approval handoff/)).toBeVisible();
  for (const [option, probability] of Object.entries(validationAnswer.probabilities)) {
    expect(within(result).getByText(option, { selector: 'dt' }).parentElement).toHaveTextContent(String(probability));
  }
  fireEvent.click(within(rubric).getByText('Sanitized recorded Decision-1 request body'));
  fireEvent.click(within(result).getByText('Sanitized response envelope · formatted for reading'));
  fireEvent.click(within(result).getByText('Sanitized recorded response body'));
  expect(within(rubric).getByRole('region', { name: 'Sanitized recorded request body' }).textContent).toBe(capture.calls[2].requestText);
  expect(JSON.parse(within(result).getByRole('region', { name: 'Formatted sanitized response JSON' }).textContent!)).toEqual(capture.calls[2].responseBody);
  expect(within(result).getByRole('region', { name: 'Sanitized recorded response body' }).textContent).toBe(capture.calls[2].responseText);
  expect(within(result).getByRole('region', { name: 'Actual terminal output for this step' }).textContent).toBe(terminalStages[3]);
});

it('keeps roving arrow/Home/End focus on the selected step picker', () => {
  render(<LearnPage />);
  const first = screen.getByRole('tab', { name: /Step 1/ });
  first.focus();
  fireEvent.keyDown(first, { key: 'ArrowRight' });
  expect(screen.getByRole('tab', { name: /Step 2/ })).toHaveFocus();
  fireEvent.keyDown(document.activeElement!, { key: 'End' });
  expect(screen.getByRole('tab', { name: /Step 5/ })).toHaveFocus();
  fireEvent.keyDown(document.activeElement!, { key: 'Home' });
  expect(first).toHaveFocus();
  fireEvent.keyDown(first, { key: 'ArrowLeft' });
  expect(screen.getByRole('tab', { name: /Step 5/ })).toHaveFocus();
});

it('explains routing probabilities as percentages without treating confidence as accuracy or approval', () => {
  render(<LearnPage />);
  fireEvent.click(screen.getByRole('tab', { name: /Step 2/ }));
  expect(screen.getByRole('heading', { name: 'How to read these scores' })).toBeVisible();
  const scores = document.querySelector('.recorded-result dl')!;
  for (const [option, value] of Object.entries(routeAnswer.probabilities)) {
    const row = screen.getByText(option, { selector: 'dt' }).parentElement!;
    expect(row).toHaveTextContent(`${(value * 100).toFixed(2)}% (raw: ${String(value)})`);
  }
  expect(scores).toBeVisible();
  expect(screen.getByText(/compared with 2.29%/)).toHaveTextContent('97.34%');
  expect(screen.getByText(/provider-reported confidence indicator/)).toHaveTextContent(String(routeAnswer.confidence));
  expect(screen.getByText(/does not define this field/)).toHaveTextContent('not measured accuracy, certainty, or a safety guarantee');
  const policy = screen.getByText(/Model choice versus effective route:/).closest('p')!;
  expect(policy).toHaveTextContent('at least 0.70 (70%) and strictly greater than every alternative');
  expect(policy).toHaveTextContent('not a confidence threshold');
  expect(policy).toHaveTextContent('missing, invalid, or tied routing evidence leads to human review');
  expect(screen.getByText(/Higher scores do not authorize actions/)).toHaveTextContent('human approval handoff still follow');
  expect(screen.getByRole('link', { name: 'Microsoft Learn: choice probabilities and interpreting decisions' })).toHaveAttribute('href', decisionLearnUrl);
  fireEvent.click(screen.getByText('Sanitized recorded response body'));
  expect(screen.getByRole('region', { name: 'Sanitized recorded response body' }).textContent).toBe(capture.calls[0].responseText);
});

it.each([0, 1])('focuses the newly rendered heading after Next and Previous activation (click detail %s)', (detail) => {
  render(<LearnPage />);
  const next = screen.getByRole('button', { name: 'Next step' });
  next.focus();
  fireEvent.click(next, { detail });
  expect(screen.getByRole('heading', { name: 'Decision-1 routing response' })).toHaveFocus();
  expect(screen.getByRole('tab', { name: /Step 2/ })).toHaveAttribute('aria-selected', 'true');
  const previous = screen.getByRole('button', { name: 'Previous step' });
  previous.focus();
  fireEvent.click(previous, { detail });
  expect(screen.getByRole('heading', { name: 'Issue and routing request' })).toHaveFocus();
  expect(screen.getByRole('tab', { name: /Step 1/ })).toHaveAttribute('aria-selected', 'true');
});

it('accounts for exactly all three completed real calls and keeps bodies, proposal and terminal slices consistent', () => {
  expect(capture.captureRun).toBe(2);
  expect(capture.provenance).toBe('recorded-live-inference');
  expect(capture.sourceSha256).toBe('180c08ee86992cc88a9b97050db7b5395d3b77aa6844221dd4101223dc287d2d');
  expect(capture.calls.map((call) => [call.sequence, call.kind, call.deployment])).toEqual([
    [1, 'decision', 'YOUR-DECISION-1-DEPLOYMENT'], [2, 'specialist', 'YOUR-GPT-4.1-MINI-DEPLOYMENT'], [3, 'decision', 'YOUR-DECISION-1-DEPLOYMENT'],
  ]);
  expect(capture.attemptedRequests).toEqual({ decision: 2, specialist: 1 });
  expect(capture.authorizedRequestBudget).toEqual({ decision: 2, specialist: 1, retries: 0 });
  for (const call of capture.calls) {
    expect(JSON.parse(call.requestText)).toEqual(call.requestBody);
    expect(JSON.parse(call.responseText)).toEqual(call.responseBody);
    expect(call.httpStatus).toBe(200);
    expect(call.status).toBe('completed');
    expect(call.clientElapsedMs).toBeGreaterThan(0);
    expect(call.redactionsApplied).toBe(true);
  }
  expect(capture.calls[2].requestBody.state).toEqual({
    original_issue: capture.calls[0].requestBody.state,
    proposal: JSON.parse(proposalContent),
  });
  expect(capture.calls[1].requestBody.messages?.[1].content).toBe(capture.calls[0].requestBody.state);
  expect(routeAnswer.choice).toBe('supply-chain');
  expect(routeAnswer.probabilities['supply-chain']).toBe(0.9734034272483898);
  expect(routeAnswer.confidence).toBe(0.964537902997853);
  expect(validationAnswer.choice).toBe('Addresses the issue');
  expect(validationAnswer.probabilities['Addresses the issue']).toBe(0.8820697540595037);
  expect(validationAnswer.confidence).toBe(0.8231046310892556);
  expect(terminalStages).toHaveLength(5);
  expect(terminalStages.join('')).toBe(capture.stdout);
  expect(capture.exitCode).toBe(2);
  expect(capture.externalActionsExecuted).toBe(false);
  expect(capture.stdout).toContain('human choice = Pending (noninteractive input; no automatic acceptance)');
  expect(capture.stdout).not.toContain('Policy-required review:');
  expect(capture.stderr).toBe('');
  expect(capture.headersCaptured).toBe(false);
  expect(capture.publication.label).toContain('Sanitized published capture');
  expect(capture.calls[0].requestBody.model).toBe('YOUR-DECISION-1-DEPLOYMENT');
  expect(capture.calls[1].requestBody.model).toBe('YOUR-GPT-4.1-MINI-DEPLOYMENT');
  expect(capture.calls[1].responseBody.id).toBe('REDACTED_RESPONSE_ID');
  expect(capture.calls[1].responseBody.system_fingerprint).toBe('REDACTED_SYSTEM_FINGERPRINT');
  expect(capture.calls[1].responseBody.routing?.serving_pipereplica).toBe('REDACTED_SERVING_REPLICA');
  const checkKeys = (value: unknown) => {
    if (value && typeof value === 'object') {
      for (const [key, child] of Object.entries(value)) {
        expect(key).not.toMatch(/^(executionContext|pythonExecutable|authorization|headers|api[_-]?key|access[_-]?token|credential|proxyUrl)$/i);
        checkKeys(child);
      }
    }
  };
  checkKeys(capture);
  expect(JSON.stringify(capture)).not.toMatch(/Bearer |https?:\/\/|C:\\\\Users/i);
});

it('keeps loading and every step offline while retaining route semantics and Home sources', async () => {
  const fetch = vi.fn().mockResolvedValue({
    ok: true, json: async () => ({ status: 'ok', executionMode: 'mock', syntheticDataOnly: true, externalActionsEnabled: false }),
  });
  vi.stubGlobal('fetch', fetch);
  window.history.replaceState(null, '', '/#learn');
  render(<App />);
  for (let index = 1; index <= 5; index++) fireEvent.click(screen.getByRole('tab', { name: new RegExp(`Step ${index}`) }));
  await act(async () => {});
  expect(fetch.mock.calls.map(([url]) => url)).toEqual([]);
  const nav = within(screen.getByRole('navigation', { name: 'Main navigation' }));
  expect(nav.getByRole('link', { name: 'Learn' })).toHaveAttribute('aria-current', 'page');
  act(() => {
    window.history.replaceState(null, '', '/#intro');
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  });
  expect(nav.getByRole('link', { name: 'Home' })).toHaveAttribute('aria-current', 'page');
  fireEvent.click(screen.getByText('Sources and context'));
  expect(screen.getByRole('link', { name: 'Follow the recorded shortage' })).toHaveAttribute('href', '#learn');
  expect(within(screen.getByRole('region', { name: 'Sources and what they support' })).getAllByRole('link')).toHaveLength(3);
});

it('preserves the catalog-derived normalized mock and historical first sample separately from Learn', () => {
  expect(Object.keys(mockRequest)).toEqual(['model', 'state', 'questions']);
  expect(JSON.parse(mockRequest.state)).toEqual({ eventId: 'synthetic-1', facts: { 'synthetic-1:fact': 'Line stopped' } });
  expect(Object.keys(mockRequest.questions)).toEqual(questionCatalog.gates.triage.questionIds);
  for (const id of questionCatalog.gates.triage.questionIds) {
    const definition = questionCatalog.questionDefinitions[id as 'event_type' | 'urgency' | 'owning_agent'];
    expect(mockRequest.questions[id]).toEqual({
      type: 'choice',
      instructions: [questionCatalog.gates.triage.instructions, definition.label, definition.instructions, '{}'].join('\n'),
      criteria: Object.fromEntries(definition.options.map((option) => [option.id, option.label])),
    });
    expect(mockResponse.results[id]).toMatchObject({
      questionId: id, selectedChoice: definition.options[0].id, confidence: 0.8,
      modelId: 'YOUR-DECISION-1-DEPLOYMENT', elapsedMs: 12, executionMode: 'mock',
    });
    expect(Object.keys(mockResponse.results[id].probabilities)).toEqual(definition.options.map((option) => option.id));
    expect(Object.values(mockResponse.results[id].probabilities).reduce((sum, value) => sum + value, 0)).toBeCloseTo(1);
  }
  expect(decisionResultSetSchema.parse(mockResponse)).toEqual(mockResponse);
  expect(mockResponse.usage).toEqual({ requestId: 'synthetic-request', inputTokens: 10, outputTokens: 5, totalTokens: 15 });
  render(<DecisionModelExplainer />);
  fireEvent.click(screen.getByText(/Developer view: mock examples \+ one approved body-shape sample/));
  expect(screen.getByText(/One specifically approved synthetic Decision-1 validation call/)).toHaveTextContent('verified request/response body shape only');
  expect(screen.getByText(/usage: snake_case/)).toHaveTextContent('input_tokens: 595');
  expect(screen.getByText(/usage: snake_case/)).toHaveTextContent('output_tokens: 3');
  expect(screen.getByText(/Response headers, provider request ID, and model version/)).toHaveTextContent('were not verified');
  expect(screen.getByText(/That Decision-1 sample did not validate specialist inference/)).toBeInTheDocument();
  expect(screen.getByText(/Local normalized fields/)).toHaveTextContent('not direct provider body field names');
  expect(screen.getByText('Show raw developer JSON examples').closest('details')).not.toHaveAttribute('open');
  fireEvent.click(screen.getByText('Show raw developer JSON examples'));
  expect(screen.getByRole('region', { name: 'Raw mock normalized response JSON' })).toBeVisible();
});

it('keeps optional broader context in Home rather than mounting the old explainer on Learn', () => {
  const { rerender } = render(<LearnPage />);
  expect(screen.queryByRole('heading', { name: 'Why is everyone talking about decision models?' })).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Microsoft Learn: Decision-1 request and response format' })).toHaveAttribute('href', decisionLearnUrl);
  rerender(<IntroPage />);
  expect(screen.getByText('Sources and what they support')).not.toBeVisible();
  fireEvent.click(screen.getByText('Sources and context'));
  expect(screen.getByRole('heading', { name: 'Sources and what they support' })).toBeVisible();
});

it('introduces input, output and ownership consistently before each diagram and evidence', () => {
  render(<LearnPage />);
  for (let step = 1; step <= 5; step++) {
    fireEvent.click(screen.getByRole('tab', { name: new RegExp(`Step ${step}`) }));
    const layer = document.querySelector('.stage-lesson')!;
    expect(layer).toBeVisible();
    expect([...layer.querySelectorAll('dt')].map((term) => term.textContent)).toEqual(['Input', 'Output', 'Who owns what']);
    expect(layer.compareDocumentPosition(screen.getByRole('figure')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  }
});
