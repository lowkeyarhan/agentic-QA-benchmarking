import { expect, test } from '@playwright/test';

test.describe('Checkout Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login and add item to cart
    await page.goto('/');
    await page.fill('[data-test="username"]', 'standard_user');
    await page.fill('[data-test="password"]', 'secret_sauce');
    await page.click('[data-test="login-button"]');
    await page.click('.inventory_item button:has-text("Add to cart")');
    await page.click('.shopping_cart_link');
  });

  test('should complete full checkout flow', {
    tags: ['@feature:checkout', '@priority:critical', '@test_type:e2e']
  }, async ({ page }) => {
    // Start checkout
    await page.click('[data-test="checkout"]');
    await expect(page).toHaveURL(/.*checkout-step-one.html/);

    // Fill checkout information
    await page.fill('[data-test="firstName"]', 'John');
    await page.fill('[data-test="lastName"]', 'Doe');
    await page.fill('[data-test="postalCode"]', '12345');
    await page.click('[data-test="continue"]');

    // Verify overview page
    await expect(page).toHaveURL(/.*checkout-step-two.html/);
    await expect(page.locator('.cart_item')).toHaveCount(1);

    // Complete order
    await page.click('[data-test="finish"]');
    await expect(page).toHaveURL(/.*checkout-complete.html/);
    await expect(page.locator('.complete-header')).toHaveText('Thank you for your order!');
  });

  test('should show error for missing checkout information', {
    tags: ['@feature:checkout', '@priority:high', '@test_type:e2e']
  }, async ({ page }) => {
    await page.click('[data-test="checkout"]');

    // Try to continue without filling form
    await page.click('[data-test="continue"]');

    // Verify error message
    await expect(page.locator('[data-test="error"]')).toBeVisible();
    await expect(page.locator('[data-test="error"]')).toContainText('Error: First Name is required');
  });

  test('should cancel checkout and return to cart', {
    tags: ['@feature:checkout', '@priority:medium', '@test_type:e2e']
  }, async ({ page }) => {
    await page.click('[data-test="checkout"]');
    await page.click('[data-test="cancel"]');

    // Verify back on cart page
    await expect(page).toHaveURL(/.*cart.html/);
  });

  test('should cancel from overview and return to inventory', {
    tags: ['@feature:checkout', '@priority:medium', '@test_type:e2e']
  }, async ({ page }) => {
    await page.click('[data-test="checkout"]');
    await page.fill('[data-test="firstName"]', 'John');
    await page.fill('[data-test="lastName"]', 'Doe');
    await page.fill('[data-test="postalCode"]', '12345');
    await page.click('[data-test="continue"]');
    await page.click('[data-test="cancel"]');

    // Verify back on inventory page
    await expect(page).toHaveURL(/.*inventory.html/);
  });

  test('should verify order total on overview page', {
    tags: ['@feature:checkout', '@priority:high', '@test_type:e2e']
  }, async ({ page }) => {
    // Get item price from cart
    const itemPrice = await page.locator('.inventory_item_price').textContent();

    await page.click('[data-test="checkout"]');
    await page.fill('[data-test="firstName"]', 'John');
    await page.fill('[data-test="lastName"]', 'Doe');
    await page.fill('[data-test="postalCode"]', '12345');
    await page.click('[data-test="continue"]');

    // Verify item total
    const itemTotal = await page.locator('.summary_subtotal_label').textContent();
    expect(itemTotal).toContain(itemPrice!.replace('$', ''));

    // Verify total includes tax
    const total = await page.locator('.summary_total_label').textContent();
    expect(total).toContain('Total: $');
  });
});
