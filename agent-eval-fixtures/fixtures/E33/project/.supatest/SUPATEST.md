# Test Framework Configuration

## Framework
- **Tool**: Playwright
- **Command**: `npx playwright test`
- **Config**: Default Playwright configuration

## File Structure
- **Test files**: `tests/**/*.spec.ts`
- **Page objects**: None (direct selector approach)

## Selector Strategy
The project uses `[data-test="..."]` attributes for all element selections.

**Examples:**
- `[data-test="username"]` - Username input field
- `[data-test="password"]` - Password input field
- `[data-test="login-button"]` - Login button
- `[data-test="error"]` - Error message container
- `[data-test^="add-to-cart"]` - Add to cart buttons (prefix match)
- `[data-test="inventory-item"]` - Inventory items
- `[data-test="shopping-cart-badge"]` - Cart badge counter

**Avoid:**
- CSS classes (`.title`, `.login_logo` used sparingly for non-interactive elements)
- XPath selectors
- Complex DOM traversals

## Test Structure

### Tags
All tests MUST use native Playwright tags property:
```typescript
test('test name',
  { tag: ['@feature:name', '@priority:level', '@test_type:type'] },
  async ({ page }) => { });
```

**Required tags:**
- `@feature:<name>` - Feature being tested (auth, cart, inventory, checkout)
- `@priority:<level>` - critical, high, medium, low
- `@test_type:<type>` - smoke, e2e, regression, integration

**Optional tags:**
- `@owner:email`
- `@ticket:PROJ-123`
- `@slow`
- `@flaky`

### Test Organization
- Use `test.describe()` for grouping related tests
- Use `test.beforeEach()` for common setup (navigation, login)
- Each test should be independent and self-contained

### Assertions
- Use Playwright's `expect()` for all assertions
- Prefer specific assertions: `toHaveText()`, `toHaveURL()`, `toBeVisible()`
- Wait for states explicitly: `await expect(page).toHaveURL(/pattern/)`

## Test Data

### Standard Users
- **standard_user** / secret_sauce - Normal user, all features work
- **performance_glitch_user** / secret_sauce - Works but with delays
- **problem_user** / secret_sauce - Has known bugs
- **error_user** / secret_sauce - Triggers errors

### Base URL
- https://www.saucedemo.com

## Common Patterns

### Login Flow
```typescript
await page.goto('https://www.saucedemo.com');
await page.fill('[data-test="username"]', 'standard_user');
await page.fill('[data-test="password"]', 'secret_sauce');
await page.click('[data-test="login-button"]');
await expect(page).toHaveURL(/.*inventory.html/);
```

### Add to Cart
```typescript
await page.locator('[data-test^="add-to-cart"]').first().click();
const cartBadge = page.locator('[data-test="shopping-cart-badge"]');
await expect(cartBadge).toHaveText('1');
```

### Navigation
```typescript
await page.click('[data-test="shopping-cart-link"]');
await expect(page).toHaveURL(/.*cart.html/);
```

## Running Tests

```bash
# Run all tests
npx playwright test

# Run specific file
npx playwright test tests/login.spec.ts

# Run with specific browser
npx playwright test --project=chromium

# Run in headed mode
npx playwright test --headed

# Run specific test
npx playwright test -g "test name pattern"
```
