import { expect, test } from '@playwright/test';

test.describe('Product Inventory', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('textbox', { name: 'Username' }).fill('standard_user');
    await page.getByRole('textbox', { name: 'Password' }).fill('secret_sauce');
    await page.getByRole('button', { name: 'Login' }).click();
    await expect(page).toHaveURL(/.*inventory/);
  });

  test('should display products on inventory page', { tag: ['@feature:inventory', '@priority:critical', '@test_type:smoke'] }, async ({ page }) => {
    // Verify products are visible
    const products = page.locator('[data-test="inventory-item"]').or(page.locator('.inventory_item'));
    const count = await products.count();
    expect(count).toBeGreaterThan(0);

    // Verify each product has name, description, price, and add to cart button
    const firstProduct = products.first();
    await expect(firstProduct.locator('[data-test="inventory-item-name"]')).or(firstProduct.locator('.inventory_item_name')).toBeVisible();
    await expect(firstProduct.locator('[data-test="inventory-item-price"]')).or(firstProduct.locator('.inventory_item_price')).toBeVisible();
  });

  test('should add product to cart', { tag: ['@feature:cart', '@priority:high', '@test_type:e2e'] }, async ({ page }) => {
    // Get initial cart count
    const cartBadge = page.locator('[data-test="shopping-cart-badge"]').or(page.locator('.shopping_cart_badge'));
    const initialCount = await cartBadge.count() > 0 ? await cartBadge.textContent() : '0';

    // Add first product to cart
    const firstAddButton = page.locator('[data-test="add-to-cart"]').or(page.getByRole('button', { name: /add to cart/i })).first();
    await firstAddButton.click();

    // Verify cart badge updated
    await expect(cartBadge).toBeVisible();
    const newCount = await cartBadge.textContent();
    expect(parseInt(newCount || '0')).toBe(parseInt(initialCount || '0') + 1);
  });

  test('should remove product from cart', { tag: ['@feature:cart', '@priority:high', '@test_type:e2e'] }, async ({ page }) => {
    // Add product to cart first
    const firstAddButton = page.locator('[data-test="add-to-cart"]').or(page.getByRole('button', { name: /add to cart/i })).first();
    await firstAddButton.click();

    const cartBadge = page.locator('[data-test="shopping-cart-badge"]').or(page.locator('.shopping_cart_badge'));
    await expect(cartBadge).toBeVisible();
    const countAfterAdd = await cartBadge.textContent();

    // Remove product from cart
    const firstRemoveButton = page.locator('[data-test="remove"]').or(page.getByRole('button', { name: /remove/i })).first();
    await firstRemoveButton.click();

    // Verify cart badge updated
    const countAfterRemove = await cartBadge.count();
    if (countAfterRemove > 0) {
      const newCount = await cartBadge.textContent();
      expect(parseInt(newCount || '0')).toBe(parseInt(countAfterAdd || '0') - 1);
    }
  });

  test('should sort products by name A to Z', { tag: ['@feature:inventory', '@priority:medium', '@test_type:e2e'] }, async ({ page }) => {
    const sortDropdown = page.locator('[data-test="product-sort-container"]').or(page.locator('.product_sort_container'));
    await sortDropdown.selectOption('az');

    // Get all product names
    const productNames = await page.locator('[data-test="inventory-item-name"]').or(page.locator('.inventory_item_name')).allTextContents();

    // Verify sorted A to Z
    const sortedNames = [...productNames].sort();
    expect(productNames).toEqual(sortedNames);
  });

  test('should sort products by price low to high', { tag: ['@feature:inventory', '@priority:medium', '@test_type:e2e'] }, async ({ page }) => {
    const sortDropdown = page.locator('[data-test="product-sort-container"]').or(page.locator('.product_sort_container'));
    await sortDropdown.selectOption('lohi');

    // Get all product prices
    const priceElements = await page.locator('[data-test="inventory-item-price"]').or(page.locator('.inventory_item_price')).allTextContents();
    const prices = priceElements.map(p => parseFloat(p.replace('$', '')));

    // Verify sorted low to high
    const sortedPrices = [...prices].sort((a, b) => a - b);
    expect(prices).toEqual(sortedPrices);
  });
});
