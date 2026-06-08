# E75 Solution: Custom Dropdown Handling

## The Problem
The test was using `getByRole('combobox').selectOption('Premium')` which only works for native `<select>` elements. The dropdown was a custom component built with divs.

## The Fix
```typescript
// Open dropdown by clicking the trigger (use class or visible text)
await page.locator('.dropdown-trigger').click();

// Wait for options to render
await page.waitForTimeout(500);

// Select option by visible text
await page.getByText('Premium').click();
```

## Key Principles
1. Don't use `selectOption()` on custom dropdowns
2. Click the trigger element first
3. Wait for options to appear
4. Select by visible text using `getByText()`
