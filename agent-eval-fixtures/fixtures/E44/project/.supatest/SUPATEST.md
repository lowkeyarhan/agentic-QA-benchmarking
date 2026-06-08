# Test Framework Discovery

## Framework
- **Framework**: Playwright v1.40.0
- **Test Command**: `npm test` or `npx playwright test`
- **Base URL**: https://www.saucedemo.com

## Test Structure
- **Test Directory**: `./tests`
- **File Pattern**: `*.spec.ts`
- **Config**: `playwright.config.ts`

## Application
- **Type**: E-commerce demo site (SauceDemo)
- **Main Flows**:
  - Login (standard_user / secret_sauce)
  - Product inventory
  - Shopping cart
  - Checkout

## Selector Strategy
Since no existing tests are present, use **semantic/role-based selectors** for stability:
- `page.getByRole('button', { name: 'Login' })`
- `page.getByRole('textbox', { name: 'Username' })`
- `page.getByTestId()` if data-testid attributes are available
- Avoid CSS classes which are fragile

## Notes
- Fresh project with no existing tests
- Multiple user types available (standard_user, problem_user, etc.)
- Focus on e2e flows for core functionality
