import { test, expect } from '@playwright/test';

test('select 1st day of current month from calendar', async ({ page }) => {
  await page.goto('/public/calendar-widget.html');

  // This test is failing - can't fill date directly
  await page.locator('#dateInput').fill('2026-03-01');

  await expect(page.locator('#result')).toContainText('Date selected:');
});
