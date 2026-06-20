import { expect, test } from '@playwright/test';
import { SELECTORS } from '../src/selectors';

test.describe('Product selectors', () => {
  test('add button selector contains add-to-cart', () => {
    expect(SELECTORS.addButton).toContain('add-to-cart');
  });

  test('product name selector targets inventory item name', () => {
    expect(SELECTORS.productName).toBe('.inventory_item_name');
  });
});
