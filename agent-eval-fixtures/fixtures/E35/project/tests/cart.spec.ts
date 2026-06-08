import { expect, test } from '@playwright/test';
import { ShoppingCart } from '../src/cart';

test.describe('Shopping Cart', () => {
  let cart: ShoppingCart;

  test.beforeEach(() => {
    cart = new ShoppingCart();
  });

  test('calculates correct total with tax', { tag: ['@feature:cart', '@priority:high', '@test_type:unit'] }, () => {
    cart.addItem({ name: 'Product A', price: 50, quantity: 1 });
    cart.addItem({ name: 'Product B', price: 40, quantity: 1 });
    
    const total = cart.calculateTotal();
    
    // Subtotal: 50 + 40 = 90
    // Tax: 90 * 0.1 = 9
    // Total: 90 + 9 = 99
    expect(total).toBe(99);
  });

  test('handles multiple quantities correctly', { tag: ['@feature:cart', '@priority:medium', '@test_type:unit'] }, () => {
    cart.addItem({ name: 'Product A', price: 20, quantity: 3 });
    
    const total = cart.calculateTotal();
    
    // Subtotal: 20 * 3 = 60
    // Tax: 60 * 0.1 = 6
    // Total: 60 + 6 = 66
    expect(total).toBe(66);
  });
});
