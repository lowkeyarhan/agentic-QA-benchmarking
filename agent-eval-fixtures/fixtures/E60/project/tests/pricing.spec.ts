import { expect, test } from '@playwright/test';
import { calculateItemPrice, EXPECTED_PRICES } from '../src/pricing';

test.describe('Pricing', () => {
  test('should calculate discounted backpack price correctly', () => {
    const basePrice = 49.99;
    const discount = 20.00;
    const finalPrice = calculateItemPrice(basePrice, discount);

    // This expectation is CORRECT - implementation has bug
    // Expected: 49.99 - 20.00 = 29.99
    // Actual (buggy): 29.98
    expect(finalPrice).toBe(EXPECTED_PRICES.backpack);
  });
});
