import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page, baseURL }) => {
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== new URL(baseURL!).origin || url.pathname.startsWith('/api/')) return route.abort();
    return route.continue();
  });
});

test('Home opens the recorded shortage by keyboard, preserves history, and makes no backend requests', async ({ page }) => {
  const backendRequests: string[] = [];
  page.on('request', (request) => {
    if (/^\/(api|health)\b/.test(new URL(request.url()).pathname)) backendRequests.push(request.url());
  });
  await page.goto('./');
  const nav = page.getByRole('navigation', { name: 'Main navigation' });
  await expect(nav.getByRole('link', { name: 'Home', exact: true })).toHaveAttribute('aria-current', 'page');
  const action = page.getByRole('link', { name: 'Follow the recorded shortage' });
  await action.focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/#learn$/);
  await expect(page.getByRole('tab', { name: /Step 1/ })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('region', { name: 'Original synthetic issue' })).toBeVisible();
  await page.goBack();
  await expect(action).toBeVisible();
  expect(backendRequests).toEqual([]);
});

for (const width of [320, 768, 1440]) {
  test(`${width}px Home teaches before the demo and preserves images and source disclosure`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('./');
    const action = page.getByRole('link', { name: 'Follow the recorded shortage' });
    await expect(action).toBeVisible();
    const actionBox = (await action.boundingBox())!;
    expect(actionBox.height).toBeGreaterThanOrEqual(44);
    let previousY = -1;
    for (const name of [
      'What is a decision model?',
      'Context in. A bounded answer out.',
      'Different jobs, useful together',
      'Where it fits in an agent',
      'Useful estimates, not guarantees',
    ]) {
      const section = page.getByRole('region', { name });
      await expect(section).toBeVisible();
      const box = (await section.boundingBox())!;
      expect(box.y).toBeGreaterThan(previousY);
      expect(box.y + box.height).toBeLessThan(actionBox.y);
      previousY = box.y;
    }
    await expect(page.getByText(/supply context, a bounded question, and allowed answers/)).toBeVisible();
    await expect(page.getByText(/not the selected-choice probability or permission to act/)).toBeVisible();
    await expect(page.getByText(/not a claim that one replaces the other/)).toBeVisible();
    await expect(page.getByText(/A person retains approval authority/)).toBeVisible();
    await expect(page.getByText(/Errors, bias, outdated knowledge/)).toBeVisible();
    await expect(page.locator('.home-teaching-panel')).toHaveCount(3);
    const fills: string[] = [];
    const panelEvidence = [];
    for (const [selector, fill] of [
      ['.home-panel-basics', 'color-mix(in srgb, var(--learn-blue) 22%, var(--learn-paper))'],
      ['.home-panel-complement', 'color-mix(in srgb, var(--learn-blue) 12%, var(--learn-paper))'],
      ['.home-panel-rules', 'color-mix(in srgb, var(--learn-amber) 18%, var(--learn-paper))'],
    ]) {
      const panel = page.locator(selector);
      const box = (await panel.boundingBox())!;
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width);
      const appearance = await panel.evaluate((element, expectedFill) => {
        const style = getComputedStyle(element);
        const probe = document.createElement('span');
        probe.style.backgroundColor = expectedFill;
        element.append(probe);
        const expected = getComputedStyle(probe).backgroundColor;
        probe.remove();
        const context = document.createElement('canvas').getContext('2d')!;
        const rgba = (color: string) => {
          context.clearRect(0, 0, 1, 1);
          context.fillStyle = color;
          context.fillRect(0, 0, 1, 1);
          return Array.from(context.getImageData(0, 0, 1, 1).data);
        };
        const luminance = (color: string) => rgba(color).slice(0, 3).reduce((sum, channel, i) => {
          const s = channel / 255;
          return sum + (s <= .04045 ? s / 12.92 : ((s + .055) / 1.055) ** 2.4) * [.2126, .7152, .0722][i];
        }, 0);
        const contrast = (color: string) => {
          const values = [luminance(color), luminance(style.backgroundColor)].sort((a, b) => b - a);
          return (values[0] + .05) / (values[1] + .05);
        };
        return {
          fill: style.backgroundColor,
          expected,
          alpha: rgba(style.backgroundColor)[3],
          radius: style.borderRadius,
          padding: parseFloat(style.paddingLeft),
          contrasts: Array.from(element.querySelectorAll('h3, h4, p, a')).map((text) => contrast(getComputedStyle(text).color)),
          linkDecoration: getComputedStyle(element.querySelector('a')!).textDecorationLine,
          childrenInside: Array.from(element.querySelectorAll('h3, h4, p, a')).every((text) => {
            const child = text.getBoundingClientRect();
            const parent = element.getBoundingClientRect();
            return child.left >= parent.left && child.right <= parent.right;
          }),
        };
      }, fill);
      expect(appearance.fill).toBe(appearance.expected);
      expect(appearance.alpha).toBe(255);
      expect(appearance.radius).toBe('0px');
      expect(appearance.padding).toBeGreaterThanOrEqual(20);
      expect(appearance.childrenInside).toBe(true);
      expect(appearance.linkDecoration).toContain('underline');
      for (const ratio of appearance.contrasts) expect(ratio).toBeGreaterThanOrEqual(4.5);
      fills.push(appearance.fill);
      const link = panel.getByRole('link');
      await link.focus();
      await page.keyboard.press('Shift+Tab');
      await page.keyboard.press('Tab');
      await expect(link).toBeFocused();
      const focus = await link.evaluate((element) => {
        const style = getComputedStyle(element);
        const ink = getComputedStyle(element.closest('.intro-page')!).getPropertyValue('--learn-ink').trim();
        const probe = document.createElement('span');
        probe.style.color = ink;
        element.append(probe);
        const expectedColor = getComputedStyle(probe).color;
        probe.remove();
        return { visible: element.matches(':focus-visible'), width: style.outlineWidth, style: style.outlineStyle, offset: style.outlineOffset, color: style.outlineColor, expectedColor };
      });
      expect(focus.visible).toBe(true);
      expect(focus.width).toBe('3px');
      expect(focus.style).toBe('solid');
      expect(focus.offset).toBe('4px');
      expect(focus.color).toBe(focus.expectedColor);
      panelEvidence.push({ selector, box, appearance, focus });
    }
    expect(new Set(fills).size).toBe(3);
    await testInfo.attach(`home-panel-checks-${width}`, {
      body: JSON.stringify({ width, panels: panelEvidence }, null, 2),
      contentType: 'application/json',
    });
    for (const selector of ['.intro-how', '.home-launchpad', '.beginner-jobs article']) {
      for (const element of await page.locator(selector).all()) {
        expect(await element.evaluate((node) => getComputedStyle(node).backgroundColor)).toBe('rgba(0, 0, 0, 0)');
      }
    }
    for (const [selector, source] of [
      ['.home-hero-image', '/decision-model-agent-demo/home/decision-switchboard.png'],
      ['.home-photo', '/decision-model-agent-demo/home/branching-tracks.png'],
    ]) {
      const image = page.locator(selector);
      await expect(image).toHaveAttribute('src', source);
      await image.scrollIntoViewIfNeeded();
      await expect.poll(() => image.evaluate((element) => (element as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
      const box = (await image.boundingBox())!;
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width);
      const preservesPortrait = selector === '.home-hero-image';
      expect(await image.evaluate((element) => getComputedStyle(element).objectFit)).toBe(preservesPortrait ? 'contain' : 'cover');
      if (preservesPortrait) {
        expect(await image.evaluate((element) => getComputedStyle(element).aspectRatio)).toBe('4 / 5');
        expect(box.width / box.height).toBeCloseTo(896 / 1120, 2);
        const composition = await page.locator('.home-hero').evaluate((hero) => {
          const art = hero.querySelector('.home-hero-art')!;
          const copy = hero.querySelector('.home-hero-copy')!;
          const image = hero.querySelector('.home-hero-image')!;
          const rect = (element: Element) => {
            const box = element.getBoundingClientRect();
            return { x: box.x, y: box.y, width: box.width, height: box.height, right: box.right, bottom: box.bottom };
          };
          return { hero: rect(hero), art: rect(art), copy: rect(copy), image: rect(image), position: getComputedStyle(art).position, scrim: getComputedStyle(art, '::after').backgroundImage };
        });
        expect(composition.position).toBe('absolute');
        expect(composition.art).toEqual(composition.hero);
        expect(composition.scrim).toContain('linear-gradient');
        expect(composition.copy.y).toBeLessThan(composition.art.bottom);
        expect(composition.copy.right).toBeGreaterThan(composition.art.x);
        expect(composition.image.right).toBeLessThanOrEqual(composition.hero.right + 1);
        expect(composition.image.bottom).toBeLessThanOrEqual(composition.hero.bottom + 1);
        expect(composition.hero.height).toBeLessThanOrEqual(620);
        expect(composition.image.y + composition.image.height * .33).toBeGreaterThanOrEqual(composition.hero.y);
        await testInfo.attach(`home-hero-composition-${width}`, { body: JSON.stringify(composition, null, 2), contentType: 'application/json' });
      }
    }
    await page.screenshot({ path: testInfo.outputPath(`home-${width}.png`), fullPage: true });
    const summary = page.getByText('Sources and context', { exact: true });
    const sources = page.getByRole('region', { name: 'Sources and what they support' });
    await expect(sources).not.toBeVisible();
    await summary.focus();
    await page.keyboard.press('Enter');
    await expect(sources).toBeVisible();
    await expect(sources.getByRole('link')).toHaveCount(3);
    await expect(page.getByText(/original AI-generated illustrations/)).toBeVisible();
    expect(await page.locator('body').innerText()).not.toMatch(/LOCAL MOCK|HARD BLOCKED|Developer view|optional local Live|workspace/i);
    expect(await page.evaluate(() => Math.max(document.body.scrollWidth, document.documentElement.scrollWidth))).toBeLessThanOrEqual(width);
    await summary.focus();
    await page.keyboard.press('Space');
    await expect(sources).not.toBeVisible();
  });
}

test('publishes descriptive preview metadata at the approved project Pages origin', async ({ page }) => {
  await page.goto('./');
  await expect(page).toHaveTitle('Decision models, in practice — follow a recorded shortage');
  await expect(page.locator('meta[name="description"]')).toHaveAttribute('content', /synthetic factory shortage/);
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute('content', 'https://maxbush6299.github.io/decision-model-agent-demo/home/decision-switchboard.png');
  await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute('content', 'summary_large_image');
  await expect(page.locator('meta[property="og:url"]')).toHaveAttribute('content', 'https://maxbush6299.github.io/decision-model-agent-demo/');
});
