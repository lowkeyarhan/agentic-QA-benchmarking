import { test, expect } from '@playwright/test';
import { calculateSubtotal, calculateTotal } from '../src/cart';
import type { CartItem } from '../src/cart';

test.describe('Cart Total Calculation', () => {
  test('should calculate correct total for items with tax', () => {
    const items: CartItem[] = [
      { name: 'Widget', price: 49.99, quantity: 1 },
      { name: 'Gadget', price: 5.98, quantity: 1 },
    ];
    const subtotal = calculateSubtotal(items);
    expect(subtotal).toBeCloseTo(55.97, 2);

    const total = calculateTotal(subtotal);
    expect(total).toBeCloseTo(60.45, 2);
  });

  test('should calculate correct total for single item', () => {
    const items: CartItem[] = [
      { name: 'Widget', price: 49.99, quantity: 1 },
    ];
    const subtotal = calculateSubtotal(items);
    expect(subtotal).toBeCloseTo(49.99, 2);

    const total = calculateTotal(subtotal);
    expect(total).toBeCloseTo(53.99, 2);
  });
});
