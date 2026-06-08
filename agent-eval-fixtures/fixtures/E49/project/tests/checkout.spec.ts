import { expect, test } from '@playwright/test';

test.describe('Checkout Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.locator('[data-test="username"]').fill('standard_user');
    await page.locator('[data-test="password"]').fill('secret_sauce');
    await page.locator('[data-test="login-button"]').click();
    await expect(page).toHaveURL(/.*inventory/);
  });

  test('should complete checkout successfully', { tag: ['@feature:checkout', '@priority:critical', '@test_type:e2e'] }, async ({ page }) => {
    // Add item to cart
    await page.locator('[data-test="add-to-cart-sauce-labs-backpack"]').click();

    // Go to cart
    await page.locator('.shopping_cart_link').click();
    await expect(page).toHaveURL(/.*cart/);

    // Proceed to checkout
    await page.locator('[data-test="checkout"]').click();
    await expect(page).toHaveURL(/.*checkout-step-one/);

    // Fill checkout information
    await page.locator('[data-test="firstName"]').fill('John');
    await page.locator('[data-test="lastName"]').fill('Doe');
    await page.locator('[data-test="postalCode"]').fill('12345');
    await page.locator('[data-test="continue"]').click();

    // Verify checkout overview
    await expect(page).toHaveURL(/.*checkout-step-two/);
    await expect(page.locator('.title')).toHaveText('Checkout: Overview');

    // Complete checkout
    await page.locator('[data-test="finish"]').click();

    // Verify order confirmation
    await expect(page).toHaveURL(/.*checkout-complete/);
    await expect(page.locator('.complete-header')).toHaveText('Thank you for your order!');
    await expect(page.locator('.shopping_cart_badge')).not.toBeVisible();
  });

  test('should show error when checkout fields are empty', { tag: ['@feature:checkout', '@priority:high', '@test_type:e2e'] }, async ({ page }) => {
    // Add item to cart
    await page.locator('[data-test="add-to-cart-sauce-labs-backpack"]').click();

    // Go to cart
    await page.locator('.shopping_cart_link').click();
    await page.locator('[data-test="checkout"]').click();

    // Try to continue without filling fields
    await page.locator('[data-test="continue"]').click();

    await expect(page.locator('[data-test="error"]')).toBeVisible();
    await expect(page.locator('[data-test="error"]')).toContainText('First Name is required');
  });

  test('should show correct item total in checkout overview', { tag: ['@feature:checkout', '@priority:high', '@test_type:e2e'] }, async ({ page }) => {
    // Add item to cart
    await page.locator('[data-test="add-to-cart-sauce-labs-backpack"]').click();

    // Go to cart and checkout
    await page.locator('.shopping_cart_link').click();
    await page.locator('[data-test="checkout"]').click();

    // Fill checkout information
    await page.locator('[data-test="firstName"]').fill('John');
    await page.locator('[data-test="lastName"]').fill('Doe');
    await page.locator('[data-test="postalCode"]').fill('12345');
    await page.locator('[data-test="continue"]').click();

    // Verify item total is displayed
    const itemTotal = await page.locator('.summary_subtotal_label').textContent();
    expect(itemTotal).toContain('$');
    expect(itemTotal).toContain('29.99');
  });

  test('should allow canceling checkout at step one', { tag: ['@feature:checkout', '@priority:medium', '@test_type:e2e'] }, async ({ page }) => {
    // Add item to cart
    await page.locator('[data-test="add-to-cart-sauce-labs-backpack"]').click();

    // Go to cart and checkout
    await page.locator('.shopping_cart_link').click();
    await page.locator('[data-test="checkout"]').click();

    // Cancel checkout
    await page.locator('[data-test="cancel"]').click();

    // Should be back at cart
    await expect(page).toHaveURL(/.*cart/);
    await expect(page.locator('.shopping_cart_badge')).toHaveText('1');
  });

  test('should allow canceling checkout at step two', { tag: ['@feature:checkout', '@priority:medium', '@test_type:e2e'] }, async ({ page }) => {
    // Add item to cart
    await page.locator('[data-test="add-to-cart-sauce-labs-backpack"]').click();

    // Go to cart and checkout
    await page.locator('.shopping_cart_link').click();
    await page.locator('[data-test="checkout"]').click();

    // Fill checkout information
    await page.locator('[data-test="firstName"]').fill('John');
    await page.locator('[data-test="lastName"]').fill('Doe');
    await page.locator('[data-test="postalCode"]').fill('12345');
    await page.locator('[data-test="continue"]').click();

    // Cancel at overview step
    await page.locator('[data-test="cancel"]').click();

    // Should be back at inventory
    await expect(page).toHaveURL(/.*inventory/);
  });
});
