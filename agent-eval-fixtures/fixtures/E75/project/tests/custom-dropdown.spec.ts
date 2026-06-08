import { expect, test } from '@playwright/test';

test('select Premium from custom dropdown', async ({ page }) => {
  // Navigate to the test page
  await page.goto('/custom-dropdown.html');
  
  // Custom dropdown pattern: click trigger → wait → select by text
  // Open dropdown by clicking on the trigger element (has class dropdown-trigger)
  await page.locator('.dropdown-trigger').click();
  
  // Wait for options to render
  await page.waitForTimeout(500);
  
  // Select Premium option by visible text
  await page.getByText('Premium').click();
  
  // Verify selection
  await expect(page.getByText('Selected: Premium')).toBeVisible();
});
