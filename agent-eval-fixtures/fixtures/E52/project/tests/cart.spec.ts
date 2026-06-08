import { expect, test } from '@playwright/test';

test.describe('Cart Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/');
    await page.fill('[data-test="username"]', 'standard_user');
    await page.fill('[data-test="password"]', 'secret_sauce');
    await page.click('[data-test="login-button"]');
    await expect(page).toHaveURL(/.*inventory.html/);
  });

  test('should add item to cart', {
    tags: ['@feature:cart', '@priority:critical', '@test_type:e2e']
  }, async ({ page }) => {
    // Add first item to cart
    await page.click('.inventory_item button:has-text("Add to cart")');

    // Verify button text changed to "Remove"
    await expect(page.locator('.inventory_item button').first()).toHaveText('Remove');

    // Verify cart badge shows 1 item
    await expect(page.locator('.shopping_cart_badge')).toHaveText('1');
  });

  test('should remove item from cart on inventory page', {
    tags: ['@feature:cart', '@priority:high', '@test_type:e2e']
  }, async ({ page }) => {
    // Add item to cart
    await page.click('.inventory_item button:has-text("Add to cart")');
    await expect(page.locator('.shopping_cart_badge')).toHaveText('1');

    // Remove item
    await page.click('.inventory_item button:has-text("Remove")');

    // Verify badge is gone
    await expect(page.locator('.shopping_cart_badge')).not.toBeVisible();
  });

  test('should view cart with added items', {
    tags: ['@feature:cart', '@priority:critical', '@test_type:e2e']
  }, async ({ page }) => {
    // Add two items to cart
    await page.click('.inventory_item button:has-text("Add to cart")');
    await page.locator('.inventory_item').nth(1).locator('button:has-text("Add to cart")').click();

    // Navigate to cart
    await page.click('.shopping_cart_link');
    await expect(page).toHaveURL(/.*cart.html/);

    // Verify both items in cart
    const cartItems = page.locator('.cart_item');
    await expect(cartItems).toHaveCount(2);
  });

  test('should remove item from cart page', {
    tags: ['@feature:cart', '@priority:high', '@test_type:e2e']
  }, async ({ page }) => {
    // Add items and navigate to cart
    await page.click('.inventory_item button:has-text("Add to cart")');
    await page.locator('.inventory_item').nth(1).locator('button:has-text("Add to cart")').click();
    await page.click('.shopping_cart_link');

    // Remove first item
    await page.locator('.cart_item').first().locator('button:has-text("Remove")').click();

    // Verify only one item remains
    await expect(page.locator('.cart_item')).toHaveCount(1);
  });

  test('should continue shopping from cart', {
    tags: ['@feature:cart', '@priority:medium', '@test_type:e2e']
  }, async ({ page }) => {
    await page.click('.shopping_cart_link');
    await page.click('[data-test="continue-shopping"]');

    // Verify back on inventory page
    await expect(page).toHaveURL(/.*inventory.html/);
  });
});
