# Test Framework Discovery

## Framework
- **Framework**: Playwright (TypeScript)
- **Test Command**: `npm test` or `npx playwright test`
- **Test Files**: `tests/**/*.spec.ts`

## Project Structure
- `/tests` - Test files
- `/pages` - Page Object Model classes
- `playwright.config.ts` - Playwright configuration

## Naming Conventions
- Test files: `*.spec.ts`
- Page objects: PascalCase (e.g., `LoginPage.ts`, `InventoryPage.ts`)
- Test descriptions: Descriptive sentences with tag prefixes

## Selector Strategy
- **Primary**: `[data-test="selector-name"]` attributes (e.g., `[data-test="username"]`, `[data-test="add-to-cart-sauce-labs-backpack"]`)
- **Secondary**: CSS classes for layout elements (e.g., `.inventory_item`, `.cart_item`)
- **Product IDs**: kebab-case product names (e.g., `sauce-labs-backpack`, `sauce-labs-bike-light`)

## Test Patterns
- Uses Page Object Model pattern
- Page objects instantiated in `beforeEach` hook
- Login performed in `beforeEach` for most tests
- Assertions use `expect()` from Playwright
- Tagging: Tests use title-based tags like `@auth @smoke @test_type:regression`

## Available Page Objects
- `LoginPage` - Authentication
- `InventoryPage` - Product listing
- `CartPage` - Shopping cart
- `CheckoutPage` - Checkout flow

## Test Users
- `standard_user` / `secret_sauce` - Normal user
- `problem_user` / `secret_sauce` - User with UI bugs
- `error_user` / `secret_sauce` - User with API errors
- `locked_out_user` / `secret_sauce` - Locked account
- `performance_glitch_user` / `secret_sauce` - Slow performance
- `visual_user` / `secret_sauce` - Visual bugs

## Common Selectors
- Login: `[data-test="username"]`, `[data-test="password"]`, `[data-test="login-button"]`
- Cart: `[data-test="shopping-cart-link"]`, `.shopping_cart_badge`
- Products: `[data-test="add-to-cart-{product-id}"]`, `[data-test="remove-{product-id}"]`
- Buttons: `[data-test="checkout"]`, `[data-test="continue-shopping"]`
