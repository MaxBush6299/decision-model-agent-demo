import { expect, test } from '@playwright/test';

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

test('selected Learn tabs retain readable computed colors and contrast on hover and keyboard focus', async ({ page }) => {
  await page.goto('./#learn');
  const tabs = page.getByRole('tablist', { name: 'Recorded CLI steps' }).getByRole('tab');
  for (let index = 0; index < 5; index += 1) {
    const tab = tabs.nth(index);
    await tab.click();
    await tab.hover();
    await tab.focus();
    await expect(tab).toHaveAttribute('aria-selected', 'true');
    const colors = await tab.evaluate((element) => {
      const style = getComputedStyle(element);
      const label = getComputedStyle(element.querySelector('span')!);
      const luminance = (color: string) => {
        const [r, g, b] = color.match(/\d+/g)!.slice(0, 3).map((value) => {
          const s = Number(value) / 255;
          return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      };
      const contrast = (foreground: string, background: string) => {
        const a = luminance(foreground);
        const b = luminance(background);
        return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      };
      return {
        foreground: style.color, background: style.backgroundColor, label: label.color,
        textContrast: contrast(style.color, style.backgroundColor),
        labelContrast: contrast(label.color, style.backgroundColor),
      };
    });
    expect(colors.foreground).toBe('rgb(255, 255, 255)');
    expect(colors.background).toBe('rgb(36, 79, 114)');
    expect(colors.label).toBe('rgb(217, 230, 239)');
    expect(colors.textContrast).toBeGreaterThanOrEqual(4.5);
    expect(colors.labelContrast).toBeGreaterThanOrEqual(4.5);
  }
});

test('mid-step reduced-motion toggles never advance the recorded walkthrough or start animations', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.clock.install();
  await page.goto('./#learn');
  await page.getByRole('button', { name: 'Next step', exact: true }).click();
  const tab = page.getByRole('tab', { name: /Step 2/ });
  for (const reducedMotion of ['reduce', 'no-preference'] as const) {
    await page.emulateMedia({ reducedMotion });
    await page.clock.runFor(5000);
    await expect(tab).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByRole('button', { name: 'Play', exact: true })).toHaveCount(0);
    expect(await page.getByRole('tabpanel').evaluate((element) => element.getAnimations({ subtree: true }).length)).toBe(0);
  }
});

test('keyboard Next from validation lands on final human-review panel and continues to raw terminal', async ({ page }) => {
  await page.goto('./#learn');
  await page.getByRole('tab', { name: /Step 4/ }).focus();
  await page.keyboard.press('Enter');
  await page.getByRole('button', { name: 'Next step', exact: true }).focus();
  await page.keyboard.press('Enter');
  const panel = page.getByRole('tabpanel', { name: /Step 5/ });
  await expect(panel.getByRole('heading', { name: 'Human review' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(panel.getByRole('region', { name: 'Actual terminal output for this step' })).toBeFocused();
  await expect(page.getByRole('link', { name: 'Return to Home' })).toHaveAttribute('href', '#intro');
});
