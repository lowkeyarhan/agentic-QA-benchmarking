import { expect, test } from '@playwright/test';

test.describe('Inventory Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.locator('[data-test="username"]').fill('standard_user');
    await page.locator('[data-test="password"]').fill('secret_sauce');
    await page.locator('[data-test="login-button"]').click();
    await expect(page).toHaveURL(/.*inventory/);
  });

  test('should display product list', { tag: ['@feature:inventory', '@priority:critical', '@test_type:smoke'] }, async ({ page }) => {
    const products = page.locator('.inventory_item');
    await expect(products).toHaveCount(6);
  });

  test('should add item to cart', { tag: ['@feature:cart', '@priority:critical', '@test_type:e2e'] }, async ({ page }) => {
    await page.locator('[data-test="add-to-cart-sauce-labs-backpack"]').click();

    await expect(page.locator('.shopping_cart_badge')).toHaveText('1');
    await expect(page.locator('[data-test="remove-sauce-labs-backpack"]')).toBeVisible();
  });

  test('should remove item from cart', { tag: ['@feature:cart', '@priority:high', '@test_type:e2e'] }, async ({ page }) => {
    await page.locator('[data-test="add-to-cart-sauce-labs-backpack"]').click();
    await expect(page.locator('.shopping_cart_badge')).toHaveText('1');

    await page.locator('[data-test="remove-sauce-labs-backpack"]').click();

    await expect(page.locator('.shopping_cart_badge')).not.toBeVisible();
    await expect(page.locator('[data-test="add-to-cart-sauce-labs-backpack"]')).toBeVisible();
  });

  test('should navigate to cart page', { tag: ['@feature:cart', '@priority:high', '@test_type:e2e'] }, async ({ page }) => {
    await page.locator('.shopping_cart_link').click();

    await expect(page).toHaveURL(/.*cart/);
    await expect(page.locator('.title')).toHaveText('Your Cart');
  });

  test('should sort products by name A to Z', { tag: ['@feature:inventory', '@priority:medium', '@test_type:e2e'] }, async ({ page }) => {
    await page.locator('[data-test="product-sort-container"]').selectOption('az');

    const productNames = await page.locator('.inventory_item_name').allTextContents();
    const sortedNames = [...productNames].sort();
    expect(productNames).toEqual(sortedNames);
  });

  test('should sort products by name Z to A', { tag: ['@feature:inventory', '@priority:medium', '@test_type:e2e'] }, async ({ page }) => {
    await page.locator('[data-test="product-sort-container"]').selectOption('za');

    const productNames = await page.locator('.inventory_item_name').allTextContents();
    const sortedNames = [...productNames].sort().reverse();
    expect(productNames).toEqual(sortedNames);
  });

  test('should sort products by price low to high', { tag: ['@feature:inventory', '@priority:medium', '@test_type:e2e'] }, async ({ page }) => {
    await page.locator('[data-test="product-sort-container"]').selectOption('lohi');

    const prices = await page.locator('.inventory_item_price').allTextContents();
    const numericPrices = prices.map(p => parseFloat(p.replace('$', '')));
    const sortedPrices = [...numericPrices].sort((a, b) => a - b);
    expect(numericPrices).toEqual(sortedPrices);
  });

  test('should sort products by price high to low', { tag: ['@feature:inventory', '@priority:medium', '@test_type:e2e'] }, async ({ page }) => {
    await page.locator('[data-test="product-sort-container"]').selectOption('hilo');

    const prices = await page.locator('.inventory_item_price').allTextContents();
    const numericPrices = prices.map(p => parseFloat(p.replace('$', '')));
    const sortedPrices = [...numericPrices].sort((a, b) => b - a);
    expect(numericPrices).toEqual(sortedPrices);
  });
});
