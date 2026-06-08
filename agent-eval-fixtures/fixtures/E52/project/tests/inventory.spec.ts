import { expect, test } from '@playwright/test';

test.describe('Inventory Page', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/');
    await page.fill('[data-test="username"]', 'standard_user');
    await page.fill('[data-test="password"]', 'secret_sauce');
    await page.click('[data-test="login-button"]');
    await expect(page).toHaveURL(/.*inventory.html/);
  });

  test('should display inventory items', {
    tags: ['@feature:inventory', '@priority:critical', '@test_type:smoke']
  }, async ({ page }) => {
    // Verify inventory items are displayed
    const inventoryItems = page.locator('.inventory_item');
    await expect(inventoryItems).toHaveCount(6);

    // Verify first item has expected elements
    const firstItem = inventoryItems.first();
    await expect(firstItem.locator('.inventory_item_name')).toBeVisible();
    await expect(firstItem.locator('.inventory_item_price')).toBeVisible();
    await expect(firstItem.locator('button')).toContainText('Add to cart');
  });

  test('should sort products by name A to Z', {
    tags: ['@feature:inventory', '@priority:medium', '@test_type:e2e']
  }, async ({ page }) => {
    // Select sort option
    await page.selectOption('[data-test="product-sort-container"]', 'az');

    // Get all product names
    const productNames = await page.locator('.inventory_item_name').allTextContents();

    // Verify they are sorted A-Z
    const sortedNames = [...productNames].sort();
    expect(productNames).toEqual(sortedNames);
  });

  test('should sort products by name Z to A', {
    tags: ['@feature:inventory', '@priority:medium', '@test_type:e2e']
  }, async ({ page }) => {
    await page.selectOption('[data-test="product-sort-container"]', 'za');

    const productNames = await page.locator('.inventory_item_name').allTextContents();

    // Verify they are sorted Z-A
    const sortedNames = [...productNames].sort().reverse();
    expect(productNames).toEqual(sortedNames);
  });

  test('should sort products by price low to high', {
    tags: ['@feature:inventory', '@priority:medium', '@test_type:e2e']
  }, async ({ page }) => {
    await page.selectOption('[data-test="product-sort-container"]', 'lohi');

    const prices = await page.locator('.inventory_item_price').allTextContents();
    const numericPrices = prices.map(p => parseFloat(p.replace('$', '')));

    // Verify ascending order
    const sortedPrices = [...numericPrices].sort((a, b) => a - b);
    expect(numericPrices).toEqual(sortedPrices);
  });

  test('should sort products by price high to low', {
    tags: ['@feature:inventory', '@priority:medium', '@test_type:e2e']
  }, async ({ page }) => {
    await page.selectOption('[data-test="product-sort-container"]', 'hilo');

    const prices = await page.locator('.inventory_item_price').allTextContents();
    const numericPrices = prices.map(p => parseFloat(p.replace('$', '')));

    // Verify descending order
    const sortedPrices = [...numericPrices].sort((a, b) => b - a);
    expect(numericPrices).toEqual(sortedPrices);
  });
});
