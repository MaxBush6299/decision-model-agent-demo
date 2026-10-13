import { expect, test } from '@playwright/test';
import { capture, proposalContent, terminalStages } from '../src/data/recordedCli';

test.beforeEach(async ({ page, baseURL }) => {
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== new URL(baseURL!).origin || url.pathname.startsWith('/api/')) return route.abort();
    if (url.pathname === '/health') return route.fulfill({
      json: { status: 'ok', executionMode: 'mock', syntheticDataOnly: true, externalActionsEnabled: false },
    });
    return route.continue();
  });
});

test('Learn preserves all recorded raw bodies and terminal output without new model calls', async ({ page, baseURL }) => {
  const forbiddenRequests: string[] = [];
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith('/api/') || url.origin !== new URL(baseURL!).origin) forbiddenRequests.push(request.url());
  });
  await page.goto('./#learn');
  const nav = page.getByRole('navigation', { name: 'Main navigation' });
  await expect(nav.getByRole('link', { name: 'Learn', exact: true })).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('heading', { name: 'Follow the recorded shortage' })).toBeVisible();
  await expect(page.getByRole('tab')).toHaveCount(5);
  await expect(page.getByRole('tab', { name: /Step 1/ })).toHaveAttribute('aria-selected', 'true');
  expect(await page.getByRole('region', { name: 'Recorded command' }).textContent()).toBe(capture.command);
  for (let index = 0; index < 5; index++) {
    await page.getByRole('tab', { name: new RegExp(`Step ${index + 1}`) }).click();
    expect(await page.getByRole('region', { name: 'Actual terminal output for this step' }).textContent()).toBe(terminalStages[index]);
    if (index === 0 || index === 3) {
      const call = capture.calls[index === 0 ? 0 : 2];
      const request = page.getByRole('region', { name: `Sanitized Decision-1 ${index === 0 ? 'routing' : 'validation'} request JSON` });
      await expect(request).toBeVisible();
      expect(JSON.parse((await request.textContent())!)).toEqual(call.requestBody);
      await expect(page.getByRole('table', { name: 'Decision-1 request fields' })).toBeVisible();
      await page.getByText('Sanitized recorded Decision-1 request body', { exact: true }).click();
      expect(await page.getByRole('region', { name: 'Sanitized recorded request body' }).textContent()).toBe(call.requestText);
      await page.getByText('Sanitized recorded Decision-1 request body', { exact: true }).click();
    }
    if (index === 1) {
      await expect(page.getByRole('region', { name: 'Sanitized Decision-1 routing request JSON' })).toHaveCount(0);
      await expect(page.getByRole('table', { name: 'Decision-1 request fields' })).toHaveCount(0);
    }
    if (index > 0 && index < 4) {
      const call = capture.calls[index - 1];
      const summary = index === 2 ? 'Sanitized recorded request and response bodies' : 'Sanitized recorded response body';
      await page.getByText(summary, { exact: true }).click();
      if (index === 2) expect(await page.getByRole('region', { name: 'Sanitized recorded request body' }).textContent()).toBe(call.requestText);
      expect(await page.getByRole('region', { name: 'Sanitized recorded response body' }).textContent()).toBe(call.responseText);
      await page.getByText(summary, { exact: true }).click();
    }
    if (index === 2) expect(await page.getByRole('region', { name: 'Exact specialist response content' }).textContent()).toBe(proposalContent);
    if (index === 3) expect(JSON.parse((await page.getByRole('region', { name: 'Sanitized Decision-1 validation request JSON' }).textContent())!).state).toEqual(capture.calls[2].requestBody.state);
  }
  await expect(page.getByText(/Pending \(noninteractive input; no automatic acceptance\). Exit code 2/)).toBeVisible();
  await page.getByText('Full recorded stdout · verbatim, all reached stages', { exact: true }).click();
  expect(await page.getByRole('region', { name: 'Full recorded stdout' }).textContent()).toBe(capture.stdout);
  expect(forbiddenRequests).toEqual([]);
});

for (const width of [320, 768, 1440]) {
  test(`${width}px keeps every recorded stage and expanded raw JSON within the page`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('./#learn');
    await expect(page.getByText(/Recorded model calls · synthetic facts · pending human review/)).toBeVisible();
    const rail = page.getByRole('tablist');
    expect(await rail.evaluate((element) => getComputedStyle(element).overflowX)).toBe('auto');
    for (let step = 1; step <= 5; step++) {
      await page.getByRole('tab', { name: new RegExp(`Step ${step}`) }).click();
      const panel = page.getByRole('tabpanel');
      await expect(panel.locator('.stage-lesson')).toBeVisible();
      await expect(panel.locator('.stage-lesson dt')).toHaveText(['Input', 'Output', 'Who owns what']);
      if (step === 4) {
        const context = panel.locator('.validation-evidence');
        const issue = context.getByRole('region', { name: 'Original issue beside validation' });
        const proposal = context.getByRole('region', { name: 'Actual proposal beside validation' });
        const request = panel.getByRole('region', { name: 'Sanitized Decision-1 validation request JSON' });
        expect(await issue.textContent()).toBe(capture.calls[0].requestBody.state);
        expect(await proposal.textContent()).toBe(proposalContent);
        const issueBox = (await issue.boundingBox())!;
        const proposalBox = (await proposal.boundingBox())!;
        const requestBox = (await request.boundingBox())!;
        if (width > 768) expect(proposalBox.x).toBeGreaterThanOrEqual(issueBox.x + issueBox.width);
        else expect(proposalBox.y).toBeGreaterThan(issueBox.y);
        expect(requestBox.y).toBeGreaterThan(Math.max(issueBox.y + issueBox.height, proposalBox.y + proposalBox.height));
        expect(requestBox.width).toBeGreaterThanOrEqual(issueBox.width);
      }
      const diagram = panel.getByRole('figure');
      await expect(diagram).toBeVisible();
      await expect(diagram.getByRole('list', { name: 'Responsibilities and handoffs' })).toBeVisible();
      for (const node of await diagram.getByRole('listitem').all()) {
        await expect(node).toBeVisible();
        const box = await node.boundingBox();
        expect(box!.x).toBeGreaterThanOrEqual(0);
        expect(box!.x + box!.width).toBeLessThanOrEqual(width);
      }
      for (const summary of await panel.locator('summary').all()) await summary.click();
      for (const region of await panel.locator('pre[role="region"]').all()) {
        await region.focus();
        await expect(region).toBeFocused();
        const box = await region.boundingBox();
        expect(box!.x).toBeGreaterThanOrEqual(0);
        expect(box!.x + box!.width).toBeLessThanOrEqual(width);
        expect(await region.evaluate((element) => getComputedStyle(element).whiteSpace)).toBe('pre-wrap');
      }
      expect(await page.evaluate(() => Math.max(document.body.scrollWidth, document.documentElement.scrollWidth))).toBeLessThanOrEqual(width);
    }
    await page.getByText('Full recorded stdout · verbatim, all reached stages', { exact: true }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await page.screenshot({ path: testInfo.outputPath(`learn-${width}.png`), fullPage: true });
  });
}

for (const width of [390, 1440]) {
  test(`${width}px Step 4 keeps Input Rubric Result readable with expanded evidence`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('./#learn');
    await page.getByRole('tab', { name: /Step 4/ }).click();
    const panel = page.getByRole('tabpanel');
    const groups = [
      panel.getByRole('region', { name: 'Input · Original issue + specialist proposal' }),
      panel.getByRole('region', { name: 'Rubric · Full validation request' }),
      panel.getByRole('region', { name: 'Result · Validation verdict, not approval' }),
    ];
    await expect(panel.getByText('Original issue + specialist proposal → validation verdict')).toBeVisible();
    let previousBottom = 0;
    for (const group of groups) {
      await expect(group).toBeVisible();
      expect(await group.evaluate((element) => getComputedStyle(element).borderLeftWidth)).toBe('0px');
      const box = (await group.boundingBox())!;
      expect(box.y).toBeGreaterThan(previousBottom);
      previousBottom = box.y + box.height;
    }
    const request = groups[1].getByRole('region', { name: 'Sanitized Decision-1 validation request JSON' });
    expect(await request.evaluate((element) => element.closest('details'))).toBeNull();
    expect(JSON.parse((await request.textContent())!)).toEqual(capture.calls[2].requestBody);
    await expect(panel.getByRole('table', { name: 'Decision-1 request fields' })).toHaveCount(1);
    await expect(panel.getByRole('region', { name: 'Explanatory Decision-1 HTTP envelope' })).toHaveCount(1);
    await panel.getByRole('heading', { name: 'Decision-1 validation', exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath(`after-${width}.png`), fullPage: true });
    for (const summary of await panel.locator('summary').all()) await summary.click();
    expect(await groups[1].getByRole('region', { name: 'Sanitized recorded request body' }).textContent()).toBe(capture.calls[2].requestText);
    expect(await groups[2].getByRole('region', { name: 'Sanitized recorded response body' }).textContent()).toBe(capture.calls[2].responseText);
    expect(await groups[2].getByRole('region', { name: 'Actual terminal output for this step' }).textContent()).toBe(terminalStages[3]);
    for (const region of await panel.locator('pre[role="region"]').all()) {
      await region.focus();
      await expect(region).toBeFocused();
      const box = (await region.boundingBox())!;
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width);
      expect(await region.evaluate((element) => getComputedStyle(element).whiteSpace)).toBe('pre-wrap');
      await region.press('Control+End');
      await expect.poll(() => region.evaluate((element) => element.scrollHeight - element.clientHeight - element.scrollTop)).toBeLessThanOrEqual(1);
      await region.evaluate((element) => { element.scrollTop = 0; });
    }
    expect(await page.evaluate(() => Math.max(document.body.scrollWidth, document.documentElement.scrollWidth))).toBeLessThanOrEqual(width);
    await panel.getByRole('heading', { name: 'Decision-1 validation', exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath(`after-expanded-${width}.png`), fullPage: true });
    await page.getByRole('button', { name: 'Next step', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Human review', exact: true })).toBeFocused();
    await page.getByRole('button', { name: 'Previous step', exact: true }).click();
    const heading = page.getByRole('heading', { name: 'Decision-1 validation', exact: true });
    await expect(heading).toBeFocused();
    await expect(heading).toBeInViewport({ ratio: 1 });
  });
}

test('keyboard arrows, boundaries, manual Next and native raw disclosure work with reduced motion', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.clock.install();
  await page.goto('./#unknown');
  await expect(page).toHaveURL(/#learn$/);
  const tab = (step: number) => page.getByRole('tab', { name: new RegExp(`Step ${step}`) });
  await tab(1).focus();
  await page.keyboard.press('ArrowRight');
  await expect(tab(2)).toBeFocused();
  await page.keyboard.press('End');
  await expect(tab(5)).toBeFocused();
  await page.keyboard.press('Home');
  await expect(tab(1)).toBeFocused();
  await page.keyboard.press('ArrowLeft');
  await expect(tab(5)).toBeFocused();
  await page.keyboard.press('ArrowUp');
  await expect(tab(4)).toBeFocused();
  const next = page.getByRole('button', { name: 'Next step', exact: true });
  await next.focus();
  await page.keyboard.press('Space');
  await expect(page.getByRole('heading', { name: 'Human review', exact: true })).toBeFocused();
  await page.clock.runFor(5000);
  await expect(tab(5)).toHaveAttribute('aria-selected', 'true');
  await expect(next).toBeDisabled();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('region', { name: 'Actual terminal output for this step' })).toBeFocused();
  const summary = page.getByText('Full recorded stdout · verbatim, all reached stages', { exact: true });
  await summary.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('region', { name: 'Full recorded stdout' })).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('region', { name: 'Full recorded stdout' })).toBeFocused();
  await expect(page.getByRole('button', { name: 'Play' })).toHaveCount(0);
});

for (const width of [390, 1440]) {
  for (const reducedMotion of ['no-preference', 'reduce'] as const) {
    test(`${width}px stage navigation reorients Next and Previous from the bottom (${reducedMotion})`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ reducedMotion });
      await page.goto('./#learn');
      const panel = page.getByRole('tabpanel');
      const assertStageOpening = async (name: string) => {
        const heading = panel.getByRole('heading', { name, exact: true });
        await expect(heading).toBeFocused();
        await expect(heading).toBeInViewport({ ratio: 1 });
        const box = await heading.boundingBox();
        expect(box!.y).toBeGreaterThanOrEqual(0);
        expect(box!.y).toBeLessThan(60);
        await expect(panel.locator('.stage-lesson dt').first()).toBeInViewport();
        expect(await heading.evaluate((element) => {
          const rect = element.getBoundingClientRect();
          return element.contains(document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2));
        })).toBe(true);
      };
      const next = page.getByRole('button', { name: 'Next step', exact: true });
      await next.scrollIntoViewIfNeeded();
      expect(await panel.getByRole('heading', { name: 'Issue and routing request', exact: true })
        .evaluate((element) => element.getBoundingClientRect().bottom)).toBeLessThan(0);
      await next.click();
      await assertStageOpening('Decision-1 routing response');
      await expect(page.getByRole('tab', { name: /Step 2/ })).toHaveAttribute('aria-selected', 'true');
      const previous = page.getByRole('button', { name: 'Previous step', exact: true });
      await previous.scrollIntoViewIfNeeded();
      expect(await panel.getByRole('heading', { name: 'Decision-1 routing response', exact: true })
        .evaluate((element) => element.getBoundingClientRect().bottom)).toBeLessThan(0);
      await previous.click();
      await assertStageOpening('Issue and routing request');
      await expect(page.getByRole('tab', { name: /Step 1/ })).toHaveAttribute('aria-selected', 'true');
    });
  }
}

test('320px keeps main navigation visible without overflow on every route', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto('./');
  const nav = page.getByRole('navigation', { name: 'Main navigation' });
  const labels = ['Home', 'Learn'];
  for (const label of labels) {
    await nav.getByRole('link', { name: label, exact: true }).click();
    for (const name of labels) {
      const link = nav.getByRole('link', { name, exact: true });
      await expect(link).toBeVisible();
      const box = await link.boundingBox();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(320);
    }
    expect(await page.evaluate(() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth))).toBeLessThanOrEqual(320);
  }
});
