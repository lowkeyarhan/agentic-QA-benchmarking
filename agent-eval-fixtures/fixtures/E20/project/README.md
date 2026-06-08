# Swag Labs E2E Test Suite

Comprehensive regression test suite for the Swag Labs e-commerce application using Playwright.

## Test Statistics

- **Total Tests:** 65
- **Passing:** 63
- **Skipped:** 2 (menu-related tests - known flaky selectors)
- **Failing:** 0

## Test Coverage

### Authentication Tests (`auth.spec.ts`)
- Valid user login
- Locked out user handling
- Invalid username/password scenarios
- Empty field validation
- All user types (standard, problem, performance_glitch, error, visual)
- *(Skipped: User logout - menu button selector issue)*

### Inventory/Product Tests (`inventory.spec.ts`)
- Product display verification (6 products)
- Product details validation (name, description, price, image)
- Add to cart functionality
- Remove button appearance
- Cart badge updates
- *(Skipped: Menu/sidebar functionality)*

### Product Sorting Tests (`sorting.spec.ts`)
- Sort by name (A-Z, Z-A)
- Sort by price (low-high, high-low)
- Sort option persistence
- Product count verification after sorting

### Shopping Cart Tests (`cart.spec.ts`)
- Empty cart state
- Add/remove items from cart
- Cart item details display
- Cart badge accuracy
- Continue shopping navigation
- Unique item counting

### Checkout Flow Tests (`checkout.spec.ts`)

#### Information Step
- First name validation
- Last name validation
- Postal code validation
- Form submission
- Cancel navigation

#### Overview Step
- Item display verification
- Payment information display
- Shipping information display
- Subtotal calculation
- Tax calculation
- Total calculation
- Order completion
- Cancel navigation

#### Complete Step
- Success message display
- Dispatch message display
- Return to products navigation
- Cart clearing after purchase

#### Full Checkout Flow (E2E)
- Complete purchase flow with multiple items
- Order with all 6 products
- Cart clearing verification

## Project Structure

```
saucedemo-playwright/
├── pages/
│   ├── LoginPage.ts          # Login page object model
│   ├── InventoryPage.ts      # Inventory page object model
│   ├── CartPage.ts           # Cart page object model
│   └── CheckoutPage.ts       # Checkout pages object model
├── tests/
│   ├── auth.spec.ts          # Authentication tests
│   ├── inventory.spec.ts     # Inventory/product tests
│   ├── sorting.spec.ts       # Product sorting tests
│   ├── cart.spec.ts          # Shopping cart tests
│   └── checkout.spec.ts      # Checkout flow tests
├── playwright.config.ts      # Playwright configuration
└── package.json              # Project dependencies and scripts
```

## Running Tests

```bash
# Run all tests (Chromium, Firefox, WebKit)
npm test

# Run tests on specific browser
npm test -- --project=chromium
npm test -- --project=firefox
npm test -- --project=webkit

# Run tests in headed mode
npm run test:headed

# Run tests with UI mode
npm run test:ui

# Debug tests
npm run test:debug

# View HTML report
npm run test:report
```

## Test Tags

Tests are tagged for easy filtering:
- `@auth` - Authentication tests
- `@inventory` - Inventory/product tests
- `@sorting` - Product sorting tests
- `@cart` - Shopping cart tests
- `@checkout` - Checkout tests
- `@smoke` - Critical smoke tests
- `@e2e` - End-to-end tests
- `@test_type:regression` - Regression tests

## Known Issues

1. **Menu Button Tests (2 skipped)**
   - The menu button selector `[data-test="react-burger-menu-btn"]` is not consistently clickable
   - Affects: User logout test, Menu sidebar test
   - Status: Requires investigation - possibly a timing or state issue

## Page Object Model

The test suite uses the Page Object Model pattern for maintainability:

- **LoginPage**: Handles login functionality and validation
- **InventoryPage**: Manages product browsing, sorting, and cart operations
- **CartPage**: Controls cart item management and navigation
- **CheckoutPage**: Manages the multi-step checkout process

## Configuration

Playwright is configured to:
- Run tests in parallel across multiple workers
- Capture screenshots on failure
- Record traces on retry
- Generate HTML reports
- Test on Chromium, Firefox, and WebKit
