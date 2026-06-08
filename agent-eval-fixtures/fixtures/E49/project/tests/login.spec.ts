import { expect, test } from '@playwright/test';

test.describe('Login Functionality', () => {
  test('should login successfully with valid credentials', { tag: ['@feature:auth', '@priority:critical', '@test_type:smoke'] }, async ({ page }) => {
    await page.goto('/');
    await page.locator('[data-test="username"]').fill('standard_user');
    await page.locator('[data-test="password"]').fill('secret_sauce');
    await page.locator('[data-test="login-button"]').click();

    await expect(page).toHaveURL(/.*inventory/);
    await expect(page.locator('.title')).toHaveText('Products');
  });

  test('should show error with invalid credentials', { tag: ['@feature:auth', '@priority:high', '@test_type:e2e'] }, async ({ page }) => {
    await page.goto('/');
    await page.locator('[data-test="username"]').fill('invalid_user');
    await page.locator('[data-test="password"]').fill('wrong_password');
    await page.locator('[data-test="login-button"]').click();

    await expect(page.locator('[data-test="error"]')).toBeVisible();
    await expect(page.locator('[data-test="error"]')).toContainText('Username and password do not match');
  });

  test('should show error when username is empty', { tag: ['@feature:auth', '@priority:high', '@test_type:e2e'] }, async ({ page }) => {
    await page.goto('/');
    await page.locator('[data-test="password"]').fill('secret_sauce');
    await page.locator('[data-test="login-button"]').click();

    await expect(page.locator('[data-test="error"]')).toBeVisible();
    await expect(page.locator('[data-test="error"]')).toContainText('Username is required');
  });

  test('should show error when password is empty', { tag: ['@feature:auth', '@priority:high', '@test_type:e2e'] }, async ({ page }) => {
    await page.goto('/');
    await page.locator('[data-test="username"]').fill('standard_user');
    await page.locator('[data-test="login-button"]').click();

    await expect(page.locator('[data-test="error"]')).toBeVisible();
    await expect(page.locator('[data-test="error"]')).toContainText('Password is required');
  });
});
