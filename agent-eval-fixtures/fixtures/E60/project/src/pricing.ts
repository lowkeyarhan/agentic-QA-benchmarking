// Pricing module with calculation bug
export function calculateItemPrice(basePrice: number, discount: number): number {
  // BUG: Floating point error - should use proper rounding
  return basePrice - discount - 0.01; // Off by one cent
}

export const EXPECTED_PRICES = {
  backpack: 29.99,
};
