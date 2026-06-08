import { expect, test } from '@playwright/test';

test.describe('Login Flow', () => {
  test('should login successfully with standard user', {
    tags: ['@feature:auth', '@priority:critical', '@test_type:smoke']
  }, async ({ page }) => {
    await page.goto('/');

    // Fill login form
    await page.fill('[data-test="username"]', 'standard_user');
    await page.fill('[data-test="password"]', 'secret_sauce');
    await page.click('[data-test="login-button"]');

    // Verify successful login - should redirect to inventory page
    await expect(page).toHaveURL(/.*inventory.html/);
    await expect(page.locator('.title')).toHaveText('Products');
  });

  test('should show error for locked out user', {
    tags: ['@feature:auth', '@priority:high', '@test_type:e2e']
  }, async ({ page }) => {
    await page.goto('/');

    await page.fill('[data-test="username"]', 'locked_out_user');
    await page.fill('[data-test="password"]', 'secret_sauce');
    await page.click('[data-test="login-button"]');

    // Verify error message appears
    await expect(page.locator('[data-test="error"]')).toBeVisible();
    await expect(page.locator('[data-test="error"]')).toContainText('Epic sadface: Sorry, this user has been locked out');
  });

  test('should show error for invalid credentials', {
    tags: ['@feature:auth', '@priority:high', '@test_type:e2e']
  }, async ({ page }) => {
    await page.goto('/');

    await page.fill('[data-test="username"]', 'invalid_user');
    await page.fill('[data-test="password"]', 'wrong_password');
    await page.click('[data-test="login-button"]');

    // Verify error message appears
    await expect(page.locator('[data-test="error"]')).toBeVisible();
    await expect(page.locator('[data-test="error"]')).toContainText('Epic sadface: Username and password do not match');
  });
});
