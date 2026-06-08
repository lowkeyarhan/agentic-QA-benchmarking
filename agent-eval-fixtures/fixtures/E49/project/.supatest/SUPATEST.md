# Test Framework: Playwright

## Framework
- **Framework**: Playwright
- **Test command**: `npm test` or `npx playwright test`
- **Config**: `playwright.config.ts`
- **Test directory**: `./tests`

## Base URL
- https://www.saucedemo.com

## Test Credentials
- standard_user / secret_sauce

## File Patterns
- Test files: `*.spec.ts`
- Page objects: None (no page object pattern detected - this is a blank project)

## Selector Strategy
This is a blank project with no existing tests. Based on Playwright best practices:
- Use semantic locators: `getByRole()`, `getByLabel()`, `getByText()`, `getByPlaceholder()`
- Prefer `getByRole('link', { name: '...' })` for links
- Use CSS selectors only when semantic locators aren't feasible

## Test Structure
- Use Playwright's `test()` function from `@playwright/test`
- Include required metadata tags using the `tags` property
- Required tags: `@feature`, `@priority`, `@test_type`

## Notes
- No existing tests to reference for patterns
- This is a blank template project
