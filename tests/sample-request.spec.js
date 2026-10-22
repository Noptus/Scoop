const { test, expect } = require('@playwright/test');

test('layout and same-page navigation remain usable', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('link', { name: 'See the brief' }).click();
  await expect(page).toHaveURL(/#example$/);
  expect(errors).toEqual([]);
});

test('invalid input cannot leave an old email request active', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('What does your team sell?').fill('Workflow tools');
  await page.getByLabel('Three target accounts').fill('Alpha\nBeta');
  await page.getByRole('button', { name: 'Copy sample request' }).click();
  await expect(page.getByRole('status')).toContainText('exactly three');
  await expect(page.getByRole('link', { name: 'Open an email draft' })).toBeHidden();
});

test('clipboard fallback and email draft preserve the reviewed request', async ({ page }) => {
  const posts = [];
  page.on('request', request => { if (request.method() === 'POST') posts.push(request.url()); });
  await page.goto('/');
  await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', {
    configurable: true, value: { writeText: async () => { throw new Error('denied'); } }
  }));
  await page.getByLabel('What does your team sell?').fill('Workflow & analytics');
  await page.getByLabel('Three target accounts').fill('Alpha\nBeta\nGamma');
  await page.getByRole('button', { name: 'Copy sample request' }).click();
  await expect(page.getByLabel('Prepared sample request')).toBeVisible();
  const link = page.getByRole('link', { name: 'Open an email draft' });
  const href = await link.getAttribute('href');
  expect(href.startsWith('mailto:raphael.caillon.engineer@gmail.com?')).toBe(true);
  expect(decodeURIComponent(href)).toContain('Workflow & analytics');
  expect(decodeURIComponent(href)).toContain('3. Gamma');
  expect(posts).toEqual([]);
  await page.getByLabel('Three target accounts').fill('Changed');
  await expect(link).toBeHidden();
});
