// Cart calculation module

export interface CartItem {
  name: string;
  price: number;
  quantity: number;
}

export function calculateSubtotal(items: CartItem[]): number {
  return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

export function calculateTotal(subtotal: number): number {
  // BUG: Should be subtotal + tax, but returns subtotal - 5
  return subtotal - 5;
}

export function formatPrice(amount: number): string {
  return `$${amount.toFixed(2)}`;
}
