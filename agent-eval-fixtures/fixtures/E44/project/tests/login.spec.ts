import { expect, test } from '@playwright/test';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should login successfully with valid credentials', { tag: ['@feature:auth', '@priority:critical', '@test_type:smoke'] }, async ({ page }) => {
    // Login with standard user
    await page.getByRole('textbox', { name: 'Username' }).fill('standard_user');
    await page.getByRole('textbox', { name: 'Password' }).fill('secret_sauce');
    await page.getByRole('button', { name: 'Login' }).click();

    // Verify successful login - should be on inventory page
    await expect(page).toHaveURL(/.*inventory/);
    await expect(page.getByRole('heading', { name: 'Products' })).toBeVisible();
  });

  test('should show error for invalid credentials', { tag: ['@feature:auth', '@priority:high', '@test_type:e2e'] }, async ({ page }) => {
    await page.getByRole('textbox', { name: 'Username' }).fill('invalid_user');
    await page.getByRole('textbox', { name: 'Password' }).fill('wrong_password');
    await page.getByRole('button', { name: 'Login' }).click();

    // Verify error message
    const errorMessage = page.getByRole('alert').or(page.locator('[data-test="error"]'));
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText('Username and password do not match');
  });

  test('should require username and password', { tag: ['@feature:auth', '@priority:high', '@test_type:e2e'] }, async ({ page }) => {
    // Try login without credentials
    await page.getByRole('button', { name: 'Login' }).click();

    const errorMessage = page.getByRole('alert').or(page.locator('[data-test="error"]'));
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText('Username is required');
  });

  test('should logout successfully', { tag: ['@feature:auth', '@priority:medium', '@test_type:e2e'] }, async ({ page }) => {
    // Login first
    await page.getByRole('textbox', { name: 'Username' }).fill('standard_user');
    await page.getByRole('textbox', { name: 'Password' }).fill('secret_sauce');
    await page.getByRole('button', { name: 'Login' }).click();
    await expect(page).toHaveURL(/.*inventory/);

    // Logout
    await page.getByRole('button', { name: 'Open Menu' }).or(page.locator('#react-burger-menu-btn')).click();
    await page.getByRole('link', { name: 'Logout' }).or(page.locator('#logout_sidebar_link')).click();

    // Verify back on login page
    await expect(page).toHaveURL(/.*saucedemo\.com\/?$/);
    await expect(page.getByRole('textbox', { name: 'Username' })).toBeVisible();
  });
});
