// Utils with bugs
export function formatPrice(amount: number): string {
  // BUG: Missing $ sign
  return amount.toFixed(2);
}

export function calculateTax(subtotal: number): number {
  // BUG: Wrong tax rate (should be 0.08)
  return subtotal * 0.15;
}
