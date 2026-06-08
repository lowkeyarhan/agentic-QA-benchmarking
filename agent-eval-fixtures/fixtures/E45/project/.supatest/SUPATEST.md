# Test Framework Configuration

## Framework
- **Framework**: Playwright
- **Test Command**: `npm test` or `npx playwright test`
- **Base URL**: https://www.saucedemo.com

## File Patterns
- **Test Directory**: `./tests`
- **Test Files**: `*.spec.ts`
- **Config**: `playwright.config.ts`

## Naming Conventions
- Test files: `*.spec.ts` (e.g., `cart.spec.ts`, `login.spec.ts`)
- Test descriptions: Use descriptive names with test.describe and test

## Selector Strategy
This project uses **data-test attributes** as the primary selector strategy:
- Form inputs: `[data-test="username"]`, `[data-test="password"]`
- Buttons: `[data-test="login-button"]`, `[data-test^="add-to-cart-"]`, `[data-test^="remove-"]`
- Dynamic IDs: Products use data-test with product IDs (e.g., `add-to-cart-sauce-labs-backpack`)

Secondary selectors:
- Classes for layout elements: `.shopping_cart_badge`, `.inventory_item_name`, `.cart_item`
- XPath for navigating DOM structure when needed

## Test Structure
```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup (login, navigation)
  });

  test('test description', { tag: ['@feature:name', '@priority:level', '@test_type:type'] }, async ({ page }) => {
    // Test implementation
  });
});
```

## Authentication
- **Username**: standard_user
- **Password**: secret_sauce
- Login form uses data-test attributes: `[data-test="username"]`, `[data-test="password"]`, `[data-test="login-button"]`

## Tags
Tests use Playwright's native tags property in test options:
```typescript
test('name', { tag: ['@feature:cart', '@priority:high', '@test_type:e2e'] }, async ({ page }) => {});
```

Required tags: @feature:name, @priority:critical|high|medium|low, @test_type:smoke|e2e|regression|integration|unit

## Notes
- All tests start from the base URL (https://www.saucedemo.com)
- Tests should use `beforeEach` for common setup like authentication
- The site has 6 products available on the inventory page
- Cart badge updates immediately when products are added/removed
