import { test, expect } from '@playwright/test';

test('click the custom submit button', async ({ page }) => {
  await page.goto('/public/custom-button.html');

  // This selector is failing - the button has a dynamic ID
  await page.locator('#submit-btn-12345').click();

  await expect(page.locator('#result')).toContainText('Form submitted successfully!');
});
