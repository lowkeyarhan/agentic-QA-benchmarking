# E76 Solution: Calendar Date Selection

## The Problem
The test was trying to fill the date input directly with `fill('2026-03-01')`, but the input was read-only and required using a calendar widget.

## The Fix
```typescript
// Click calendar icon to open widget
await page.locator('text=📅').click();

// Select day by visible text
await page.locator('.day').filter({ hasText: '1' }).first().click();
```

## Key Principles
1. Don't use `fill()` or `type()` on read-only date inputs
2. Click the calendar icon/trigger
3. Select date by visible text in the widget
4. Handle dynamic dates by finding "1" in the current month
