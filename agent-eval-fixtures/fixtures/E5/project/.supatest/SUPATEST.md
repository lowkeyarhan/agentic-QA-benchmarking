# Test Suite Discovery

## Framework
- **Name**: Cypress
- **Language**: TypeScript
- **Version**: 15.x

## Project Structure
```
cypress/
├── e2e/           # Test files (*.cy.ts)
├── fixtures/      # Test data
├── pages/         # Page Object classes
└── support/       # Commands and setup
```

## Test Files
- `cypress/e2e/auth.cy.ts` - Authentication tests (11 tests)
- `cypress/e2e/cart.cy.ts` - Shopping cart tests (10 tests)
- `cypress/e2e/checkout.cy.ts` - Checkout flow tests (18 tests)
- `cypress/e2e/inventory.cy.ts` - Inventory page tests (10 tests)
- `cypress/e2e/sorting.cy.ts` - Product sorting tests (7 tests)

## Page Objects
- `LoginPage` - Login form interactions
- `InventoryPage` - Product listing, cart, menu
- `CartPage` - Cart management
- `CheckoutPage` - Checkout flow (info, overview, complete)

## Selector Strategy
Uses `[data-test="..."]` attributes consistently:
- `[data-test="username"]`
- `[data-test="password"]`
- `[data-test="login-button"]`
- `[data-test="add-to-cart-{product-id}"]`
- `[data-test="remove-{product-id}"]`
- `[data-test="checkout"]`
- `[data-test="continue"]`
- `[data-test="finish"]`

## Tagging Convention
Tags are embedded in test titles (Cypress standard):
- `@auth`, `@cart`, `@checkout`, `@inventory`, `@sorting` - feature tags
- `@smoke` - smoke tests
- `@e2e` - end-to-end flows
- `@test_type:regression` - test type

Example: `it('@smoke @test_type:regression Valid user can login', ...)`

## Running Tests
```bash
# Run all tests headlessly
npm run test

# Open Cypress UI
npm run cy:open

# Run specific test file
npx cypress run --spec "cypress/e2e/auth.cy.ts"
```

## Base URL
https://www.saucedemo.com

## Test Users
- `standard_user` / `secret_sauce` - Normal user
- `locked_out_user` / `secret_sauce` - Locked account
- `problem_user` / `secret_sauce` - Has UI bugs
- `performance_glitch_user` / `secret_sauce` - Slow responses
- `error_user` / `secret_sauce` - Produces errors
- `visual_user` / `secret_sauce` - Visual differences
