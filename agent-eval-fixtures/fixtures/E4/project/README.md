# SauceDemo WebdriverIO Test Suite

Complete WebdriverIO E2E test suite for Swag Labs (SauceDemo), converted from Playwright tests.

## Test Status

As of the latest run:
- ✅ **Authentication Tests**: 11/12 passing (1 skipped - logout test has known issues with menu button)
- ✅ **Sorting Tests**: 7/7 passing (100%)
- ⚠️ **Inventory Tests**: 7/11 passing (4 failing, 1 skipped)
- ⚠️ **Cart Tests**: 3/14 passing (11 failing)
- ⚠️ **Checkout Tests**: Ongoing

## Setup

```bash
npm install
```

## Running Tests

```bash
# Run all tests (headless)
npm test

# Run tests in headed mode
npm run test:headed

# Run tests in debug mode
npm run test:debug
```

## Test Structure

```
saucedemo-wdio/
├── pages/                  # Page Object Model
│   ├── LoginPage.ts
│   ├── InventoryPage.ts
│   ├── CartPage.ts
│   └── CheckoutPage.ts
├── test/
│   └── specs/             # Test files
│       ├── auth.spec.ts
│       ├── inventory.spec.ts
│       ├── cart.spec.ts
│       ├── checkout.spec.ts
│       └── sorting.spec.ts
├── wdio.conf.ts           # WebdriverIO configuration
└── package.json
```

## Key Features

- ✅ Page Object Model pattern
- ✅ WebdriverIO v9.23.0 with latest APIs
- ✅ expect-webdriverio assertion library
- ✅ Tagged tests for filtering (@auth, @cart, @checkout, @inventory, @sorting)
- ✅ Test metadata (@test_type, @priority, @smoke, @e2e)
- ✅ Supatest reporter integration

## Configuration

- **Framework**: Mocha (BDD)
- **Browser**: Chrome (headless by default)
- **Base URL**: https://www.saucedemo.com
- **Timeout**: 60000ms

## Known Issues

1. Menu button tests are flaky - marked as skipped
2. Some cart/checkout tests need debugging for element visibility timing
3. `toHaveTextContaining` was replaced with `toHaveText` due to API differences

## Next Steps

1. Debug failing cart and checkout tests
2. Add explicit waits where needed
3. Consider retry flaky tests
4. Add more test data variety
