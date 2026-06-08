# SUPATEST.md

## Project Context

This project tests a web application with custom UI components that have dynamic IDs.

## Common Patterns

### Clicking Custom Buttons

When encountering buttons with dynamic IDs (like `#submit-btn-{random}`), use this pattern:

```typescript
// ❌ DON'T: Use dynamic IDs
await page.locator('#submit-btn-12345').click();

// ✅ DO: Use data attribute + text combination
await page.locator('[data-testid="submit-button"]').click();
// OR
await page.getByRole('button', { name: /submit/i }).click();
```

### Working Code Snippet from Previous Session

```typescript
// This is the working code that was provided by the user
// Use this pattern for buttons with dynamic IDs:

async clickDynamicButton(page: Page, buttonText: string): Promise<void> {
  // Use cursor pointer attribute which is consistent
  await page.locator('[cursor="pointer"]').filter({ hasText: buttonText }).click();
}

// Or simpler:
await page.locator('button[cursor="pointer"]').first().click();
```

## Important Notes

- Dynamic IDs change on every page load
- The `cursor="pointer"` attribute is reliable for clickable elements
- Button text is stable and should be used for selection
