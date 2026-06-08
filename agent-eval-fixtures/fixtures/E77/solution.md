# E77 Solution: Integrating User Code Snippets

## The Problem
The test was using a hardcoded ID `locator('#submit-btn-12345')` which changed on every page load. The SUPATEST.md file contained a working code snippet showing how to handle this.

## The Fix
```typescript
// Read SUPATEST.md for the pattern
// Create a reusable helper based on the snippet:
async function clickDynamicButton(page: any, buttonText: string): Promise<void> {
  // Use stable cursor pointer attribute instead of dynamic ID
  await page.locator('[cursor="pointer"]').filter({ hasText: buttonText }).click();
}

// Use in test
test('click button', async ({ page }) => {
  await clickDynamicButton(page, 'Submit Form');
  // ...
});
```

## Key Principles
1. Read SUPATEST.md for working patterns
2. Create reusable helpers from snippets
3. Use stable attributes instead of dynamic IDs
4. Don't just paste inline - refactor properly
