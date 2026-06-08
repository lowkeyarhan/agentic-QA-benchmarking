# Test Framework Documentation

## Framework
- **Test Runner**: Playwright v1.40.0
- **Test Command**: `npm test` or `npx playwright test`
- **Application Under Test**: https://www.saucedemo.com

## File Patterns
- **Test Files**: `tests/**/*.spec.ts`
- **Naming Convention**: `<feature>.spec.ts` (e.g., `login.spec.ts`, `cart.spec.ts`)

## Selector Strategy
This project uses **data-test attributes** as the primary selector strategy:
- `[data-test="username"]` - Login form username field
- `[data-test="password"]` - Login form password field
- `[data-test="login-button"]` - Login button
- `[data-test="product-sort-container"]` - Product sorting dropdown
- `[data-test="checkout"]` - Checkout button
- `[data-test="firstName"]`, `[data-test="lastName"]`, `[data-test="postalCode"]` - Checkout form fields
- `[data-test="continue"]`, `[data-test="finish"]`, `[data-test="cancel"]` - Checkout navigation buttons

### Secondary Selectors
When data-test attributes are not available, use:
- **CSS Classes**: `.inventory_item`, `.cart_item`, `.shopping_cart_badge`
- **Text Content**: `button:has-text("Add to cart")`, `button:has-text("Remove")`
- **Semantic Locators**: Page.locator() with role/text when appropriate

## Page Object Pattern
No page objects are currently used. Tests are written directly in spec files using Playwright's Page API.

## Test Structure
```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Common setup (e.g., login)
  });

  test('test description', {
    tags: ['@feature:name', '@priority:level', '@test_type:type']
  }, async ({ page }) => {
    // Test implementation
  });
});
```

## Tagging Strategy
Tests use native Playwright tags in the test options:
- **@feature**: Component being tested (auth, inventory, cart, checkout)
- **@priority**: critical | high | medium | low
- **@test_type**: smoke | e2e | regression | integration | unit

## Test Users
- **standard_user** / secret_sauce - Normal user with full functionality
- **locked_out_user** / secret_sauce - User that gets locked out error
- **problem_user** / secret_sauce - User with known UI issues
- **performance_glitch_user** / secret_sauce - User with slow performance

## Application Structure
SauceDemo is a demo e-commerce site with:
1. **Login Page** (`/`) - Authentication
2. **Inventory Page** (`/inventory.html`) - Product listing with sorting
3. **Cart Page** (`/cart.html`) - Shopping cart management
4. **Checkout Pages**:
   - Step 1 (`/checkout-step-one.html`) - Enter shipping info
   - Step 2 (`/checkout-step-two.html`) - Order overview
   - Complete (`/checkout-complete.html`) - Order confirmation

## Notes
- Tests run in headless mode by default
- Trace is captured on first retry for debugging
- Tests use `baseURL` from config, so use relative paths (e.g., `page.goto('/')`)
