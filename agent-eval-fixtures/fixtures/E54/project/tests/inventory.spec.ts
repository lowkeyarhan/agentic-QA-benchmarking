import { expect, test } from '@playwright/test';
import { SELECTORS } from '../src/inventory';

test.describe('Inventory Selectors', () => {
  test('add to cart button selector should match data-test attribute', () => {
    // The selector should match actual data-test="add-to-cart-*" buttons
    expect(SELECTORS.addToCartButton).toContain('add-to-cart');
  });

  test('product name selector should match inventory item name class', () => {
    // The selector should target .inventory_item_name
    expect(SELECTORS.productName).toBe('.inventory_item_name');
  });
});
