import { expect, test } from '@playwright/test';
import { calculateTax, formatPrice } from '../src/utils';

test.describe('Utility Functions', () => {
  test('should format price with dollar sign', () => {
    // Correct expectation - implementation has bug
    expect(formatPrice(29.99)).toBe('$29.99');
  });

  test('should calculate 8% tax', () => {
    // Correct expectation - implementation has bug
    expect(calculateTax(100)).toBeCloseTo(8.00, 2);
  });
});
