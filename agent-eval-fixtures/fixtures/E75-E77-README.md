# New Evals: Complex UI Interactions (E75-E77)

These three evals test the agent's ability to handle complex UI interactions that were identified as common failure patterns in production session analysis.

## E75: Custom Dropdown Handling

**Problem:** Agent fails to select options from custom dropdowns that don't use native `<select>` elements.

**The Eval:**
- Failing test tries: `await page.getByRole('combobox').selectOption('Premium')`
- Dropdown is a custom `div`-based component
- Error: "Element is not a <select> element"

**Expected Fix:**
```typescript
// Open dropdown trigger
await page.locator('.dropdown-trigger').click();
// Wait for options
await page.waitForTimeout(500);
// Select by visible text
await page.getByText('Premium').click();
```

**Location:** `fixtures/E75/`

---

## E76: Calendar Date Selection

**Problem:** Agent tries to fill date inputs directly instead of interacting with calendar widgets.

**The Eval:**
- Failing test tries: `await page.getByLabel('Investment Date').fill('2026-03-01')`
- Input is read-only, requires calendar widget interaction
- Error: "input field is read-only"

**Expected Fix:**
```typescript
// Click calendar icon
await page.locator('.calendar-trigger').click();
// Select 1st day of current month
await page.locator('.day').filter({ hasText: '1' }).first().click();
```

**Location:** `fixtures/E76/`

---

## E77: Integrating User Code Snippets

**Problem:** Agent ignores working code snippets provided by users in SUPATEST.md.

**The Eval:**
- Failing test uses: `await page.locator('#submit-btn-12345').click()`
- Button has dynamic ID that changes on each load
- SUPATEST.md contains working code snippet
- Agent should read and integrate the snippet

**Expected Fix:**
```typescript
// Read SUPATEST.md for working pattern
// Create helper function from snippet
async function clickDynamicButton(page, text) {
  await page.locator('[cursor="pointer"]').filter({ hasText: text }).click();
}
// Use in test
await clickDynamicButton(page, 'Submit');
```

**Location:** `fixtures/E77/`

---

## Running the Evals

### Manual Run

```bash
# E75 - Custom Dropdown
cd agent-eval-fixtures/fixtures/E75/project
npm install
npx playwright test

# E76 - Calendar
cd agent-eval-fixtures/fixtures/E76/project
npm install
npx playwright test

# E77 - User Snippet
cd agent-eval-fixtures/fixtures/E77/project
npm install
npx playwright test
```

### Via CLI Agent

```bash
cd cli

# E75
SUPATEST_API_KEY=your_key npx tsx src/index.ts \
  "Fix the failing test in tests/custom-dropdown.spec.ts..." \
  --headless --mode fix \
  --cwd ../agent-eval-fixtures/fixtures/E75/project \
  --logs ../agent-eval-fixtures/fixtures/E75/failure.log

# E76
SUPATEST_API_KEY=your_key npx tsx src/index.ts \
  "Fix the failing test in tests/calendar-date.spec.ts..." \
  --headless --mode fix \
  --cwd ../agent-eval-fixtures/fixtures/E76/project \
  --logs ../agent-eval-fixtures/fixtures/E76/failure.log

# E77
SUPATEST_API_KEY=your_key npx tsx src/index.ts \
  "Fix the failing test in tests/user-snippet.spec.ts..." \
  --headless --mode fix \
  --cwd ../agent-eval-fixtures/fixtures/E77/project \
  --logs ../agent-eval-fixtures/fixtures/E77/failure.log
```

---

## Pass/Fail Criteria

### E75 Pass Criteria
- [x] Test passes successfully
- [x] Does NOT use getByRole('option') for custom dropdown
- [x] Uses proper wait pattern (click trigger → wait → select option)
- [x] Selects 'Premium' option successfully

### E76 Pass Criteria
- [x] Test passes successfully
- [x] Opens calendar widget by clicking icon/button
- [x] Selects 1st day of current month
- [x] Does NOT use keyboard input or fill() on date field
- [x] Handles dynamic month/year correctly

### E77 Pass Criteria
- [x] Test passes successfully
- [x] Reads and understands the working code snippet from SUPATEST.md
- [x] Integrates the snippet correctly into the test
- [x] Creates a reusable helper function from the pattern
- [x] Doesn't leave the failing code commented out

---

## Tier and Category

| Eval | Tier | Category | Rationale |
|------|------|----------|-----------|
| E75 | 4 | complex-ui-interactions | Common production issue with custom components |
| E76 | 4 | complex-ui-interactions | Critical for form testing with date pickers |
| E77 | 5 | complex-ui-interactions | Tests agent's ability to use context from SUPATEST.md |

---

## Production Context

These evals were derived from analysis of 100 production sessions (1,179 queries) where:
- ~60% of sessions had complex form interactions
- Dropdown/calendar issues caused 3-5 extra iterations per fix
- User interruption rate was ~40% when these issues occurred
- Average cost per fix retry: $0.50-$2.00
