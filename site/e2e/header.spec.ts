import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page, baseURL }) => {
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== new URL(baseURL!).origin || /^\/(api|health)\b/.test(url.pathname)) return route.abort();
    return route.continue();
  });
});

for (const width of [320, 768, 1440]) {
  for (const [hash, current] of [['#intro', 'Home'], ['#learn', 'Learn']]) {
    test(`${width}px ${current} has a compact editorial header`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(`./${hash}`);
      const header = page.locator('.workspace-header');
      const wordmark = header.getByRole('link', { name: 'Decision Models', exact: true });
      const nav = header.getByRole('navigation', { name: 'Main navigation' });
      await expect(header.getByRole('heading', { level: 1 })).toHaveText('Decision Models');
      await expect(wordmark).toHaveAttribute('href', '#intro');
      await expect(nav.getByRole('link')).toHaveText(['Home', 'Learn']);
      await expect(nav.locator('[aria-current="page"]')).toHaveText(current);
      await expect(header.getByRole('button')).toHaveCount(0);
      const headerBox = (await header.boundingBox())!;
      expect(headerBox.height).toBeLessThanOrEqual(70);
      const links = await header.getByRole('link').all();
      for (const link of links) {
        await expect(link).toBeVisible();
        const box = (await link.boundingBox())!;
        expect(box.width).toBeGreaterThanOrEqual(44);
        expect(box.height).toBeGreaterThanOrEqual(44);
        expect(box.x).toBeGreaterThanOrEqual(headerBox.x);
        expect(box.x + box.width).toBeLessThanOrEqual(headerBox.x + headerBox.width);
        expect(box.y).toBeGreaterThanOrEqual(headerBox.y);
        expect(box.y + box.height).toBeLessThanOrEqual(headerBox.y + headerBox.height);
      }
      const wordmarkBox = (await wordmark.boundingBox())!;
      const navBox = (await nav.boundingBox())!;
      expect(navBox.x).toBeGreaterThanOrEqual(wordmarkBox.x + wordmarkBox.width + 8);
      expect(Math.abs(wordmarkBox.y + wordmarkBox.height / 2 - navBox.y - navBox.height / 2)).toBeLessThan(1);
      const appearance = await header.evaluate((element) => {
        const style = getComputedStyle(element);
        const luminance = (color: string) => {
          const channels = color.match(/\d+/g)!.slice(0, 3).map(Number);
          return channels.reduce((sum, channel, i) => {
            const s = channel / 255;
            return sum + (s <= .04045 ? s / 12.92 : ((s + .055) / 1.055) ** 2.4) * [.2126, .7152, .0722][i];
          }, 0);
        };
        return {
          position: style.position,
          background: style.backgroundColor,
          divider: style.borderBottomWidth,
          contrasts: Array.from(element.querySelectorAll('a')).map((link) => {
            const values = [luminance(getComputedStyle(link).color), luminance(style.backgroundColor)].sort((a, b) => b - a);
            return (values[0] + .05) / (values[1] + .05);
          }),
          overflow: document.documentElement.scrollWidth > window.innerWidth,
        };
      });
      expect(appearance.position).toBe('static');
      expect(appearance.background).toBe('rgb(244, 241, 233)');
      expect(appearance.divider).toBe('1px');
      expect(appearance.overflow).toBe(false);
      for (const contrast of appearance.contrasts) expect(contrast).toBeGreaterThanOrEqual(4.5);
      await page.screenshot({ path: testInfo.outputPath(`${current.toLowerCase()}-${width}.png`) });
      await testInfo.attach('header-layout', { body: JSON.stringify({ headerBox, wordmarkBox, navBox, appearance }, null, 2), contentType: 'application/json' });
      await page.evaluate(() => window.scrollTo(0, 500));
      expect((await header.boundingBox())!.y).toBeLessThan(0);
    });
  }

  test(`${width}px header works by keyboard and the wordmark returns Home`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('./');
    const header = page.locator('.workspace-header');
    const wordmark = header.getByRole('link', { name: 'Decision Models', exact: true });
    const home = header.getByRole('link', { name: 'Home', exact: true });
    const learn = header.getByRole('link', { name: 'Learn', exact: true });
    for (const link of [wordmark, home, learn]) {
      await page.keyboard.press('Tab');
      await expect(link).toBeFocused();
      expect(await link.evaluate((element) => {
        const style = getComputedStyle(element);
        return { visible: element.matches(':focus-visible'), style: style.outlineStyle, width: style.outlineWidth, color: style.outlineColor };
      })).toEqual({ visible: true, style: 'solid', width: '3px', color: 'rgb(36, 52, 67)' });
    }
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/#learn$/);
    await expect(learn).toHaveAttribute('aria-current', 'page');
    await expect(page.getByRole('tab', { name: /Step 1/ })).toHaveAttribute('aria-selected', 'true');
    await wordmark.focus();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/#intro$/);
    await expect(home).toHaveAttribute('aria-current', 'page');
    await expect(page.getByRole('heading', { name: 'Explore how decision models work' })).toBeVisible();
    await page.goBack();
    await expect(learn).toHaveAttribute('aria-current', 'page');
  });
}
