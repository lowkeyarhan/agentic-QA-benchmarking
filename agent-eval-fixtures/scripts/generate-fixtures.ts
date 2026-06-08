import * as fs from 'fs/promises';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

interface Modification {
  type: 'delete' | 'replace' | 'insert';
  file?: string;
  pattern?: string; // glob pattern for delete
  find?: string;
  replace?: string;
  insertAfter?: string;
  code?: string;
}

interface EvalConfig {
  id: string;
  name: string;
  mode: 'build' | 'fix' | 'plan' | 'report' | 'test-feature';
  baseTemplate: string;
  task: string;
  modifications: Modification[];
  needsFailureLog: boolean;
  passCriteria: string[];
  failCriteria: string[];
  tier: number;
}

const EVALS: EvalConfig[] = [
  // ============================================
  // Blank Playwright (base: playwright-ts-blank)
  // ============================================
  {
    id: 'E1',
    name: 'Immediate Execution on Clear Instructions',
    mode: 'build',
    baseTemplate: 'playwright-ts-blank',
    task: 'Write a login test for https://www.saucedemo.com using standard_user / secret_sauce',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Agent does NOT ask questions before starting',
      'Reads package.json within first 3 tool calls',
      'Produces a .spec.ts file',
      'Runs the test'
    ],
    failCriteria: [
      'Agent asks "What framework?" or "What URL?"',
      'Spends >5 tool calls before writing any test'
    ],
    tier: 1
  },
  {
    id: 'E2',
    name: 'Investigate Before Asking (Auth Flow Discovery)',
    mode: 'build',
    baseTemplate: 'playwright-ts-blank',
    task: 'Write a test for the inventory page at https://www.saucedemo.com/inventory.html',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Agent opens Agent Browser to explore page',
      'Discovers login redirect before asking for credentials'
    ],
    failCriteria: [
      'Agent immediately asks for credentials without browsing first'
    ],
    tier: 2
  },
  {
    id: 'E10',
    name: 'Semantic Locators Over CSS Selectors',
    mode: 'build',
    baseTemplate: 'playwright-ts-blank',
    task: 'Write a test for the login flow on https://www.saucedemo.com',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Uses getByRole(), getByLabel(), getByPlaceholder(), getByText(), or [data-test] attributes'
    ],
    failCriteria: [
      'CSS class selectors',
      'XPath',
      'Fragile nth-child'
    ],
    tier: 1
  },

  // ============================================
  // Full Playwright (base: playwright-ts-full)
  // ============================================
  {
    id: 'E6',
    name: 'Reuse Existing SUPATEST.md (Skip Rediscovery)',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a sorting test for the inventory page',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Reads SUPATEST.md early',
      'Does NOT re-read package.json for discovery',
      'Fewer tool calls than E3'
    ],
    failCriteria: [
      'Ignores SUPATEST.md',
      'Re-runs full discovery'
    ],
    tier: 3
  },
  {
    id: 'E8',
    name: 'No Browser When Source Code Provides Sufficient Context',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a test that verifies a user can log in and see the inventory page',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Reads page objects',
      'Writes test using page object methods',
      'No agent-browser before first run',
      'Test passes'
    ],
    failCriteria: [
      'Opens browser when page objects have all needed info'
    ],
    tier: 4
  },
  {
    id: 'E9',
    name: 'Browser for Exploration (No Test Writing)',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Explore the saucedemo.com app and tell me what pages and features are available',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Opens browser',
      'Navigates multiple pages',
      'Describes features',
      'Does NOT write test files',
      'Offers to write tests afterward'
    ],
    failCriteria: [
      'Writes test files during exploration'
    ],
    tier: 4
  },
  {
    id: 'E11',
    name: 'Metadata Tags on Every Test',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write tests for the complete checkout flow',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Every test() has { tags: [\'@feature:*\', \'@priority:*\', \'@test_type:*\'] }',
      'All 3 required tags present'
    ],
    failCriteria: [
      'No tags',
      'Missing required types',
      'Wrong format for framework'
    ],
    tier: 1
  },
  {
    id: 'E12',
    name: 'No Hard-Coded Waits',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a test for the full checkout flow from login through order completion',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Zero waitForTimeout(), setTimeout, or sleep()',
      'Uses auto-waiting and event-based waits'
    ],
    failCriteria: [
      'Any arbitrary numeric waits'
    ],
    tier: 4
  },
  {
    id: 'E13',
    name: 'Max 5 Attempts in Build Mode',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a test that verifies the \'Wishlist\' feature on saucedemo.com',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'At most 5 test run attempts',
      'Reports the situation'
    ],
    failCriteria: [
      'Exceeds 5 attempts',
      'Loops indefinitely'
    ],
    tier: 4
  },
  {
    id: 'E18',
    name: 'Escalation on App Bug Discovery',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Log in as problem_user / secret_sauce and write tests that verify add-to-cart works for ALL products on the inventory page',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Tests all 6 products',
      'Discovers that some products have broken add-to-cart for problem_user',
      'Reports as potential app bug',
      'Does NOT weaken assertions'
    ],
    failCriteria: [
      'Tests only 1-2 products',
      'Misses user-specific bugs',
      'Adjusts assertions to match buggy behavior'
    ],
    tier: 4
  },
  {
    id: 'E19',
    name: 'Risk-Based Test Planning',
    mode: 'plan',
    baseTemplate: 'playwright-ts-full',
    task: 'Create a test plan for the saucedemo.com e-commerce application',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Risk Assessment with HIGH/MEDIUM/LOW',
      'Auth+checkout=HIGH',
      'User Journeys in correct format',
      '"Not Testing" section',
      'Tags per test case',
      'No files created in project'
    ],
    failCriteria: [
      'No risk assessment',
      'All same risk level',
      'Creates files'
    ],
    tier: 2
  },
  {
    id: 'E20',
    name: 'Plan Mode: Read-Only Enforcement',
    mode: 'plan',
    baseTemplate: 'playwright-ts-full',
    task: 'Analyze the current test coverage and recommend what tests to add next',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Only Read, Glob, Grep tools on project files',
      'No Write/Edit',
      'No test commands'
    ],
    failCriteria: [
      'Creates or modifies project files',
      'Runs tests'
    ],
    tier: 2
  },
  {
    id: 'E21',
    name: 'Multi-Page Flow: Complete E2E Journey',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a complete end-to-end test: log in, add a product, go to cart, checkout with form details, and verify order completion',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Navigates all 5 pages',
      'Assertions at each transition',
      'Fills checkout form',
      'Verifies order confirmation',
      'Test passes',
      'Proper tags'
    ],
    failCriteria: [
      'Skips pages',
      'No navigation assertions',
      'Race conditions'
    ],
    tier: 4
  },
  {
    id: 'E22',
    name: 'Form Validation Testing',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write tests for all validation scenarios on the checkout information form',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Individual tests for: empty first name, empty last name, empty postal code, all empty, valid submission',
      'Specific error messages verified',
      'test.describe block',
      'Shared beforeEach',
      'Independent tests'
    ],
    failCriteria: [
      'Single test for all validations',
      'No error message verification',
      'Tests depend on each other'
    ],
    tier: 4
  },
  {
    id: 'E26',
    name: 'Single Test First for Faster Feedback',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a checkout flow test and a cart removal test',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'After writing tests, first run command targets a single test file or uses --grep to run one test',
      'Full file/suite run comes after individual test passes'
    ],
    failCriteria: [
      'First run command executes the entire test suite or multiple test files at once'
    ],
    tier: 5
  },
  {
    id: 'E30',
    name: 'Planner Code-First: No Questions About Code-Answerable Topics',
    mode: 'plan',
    baseTemplate: 'playwright-ts-full',
    task: 'Create a test plan for the checkout flow',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Agent reads checkout-related test files, page objects, and app routes',
      'Produces plan without any AskUserQuestion calls',
      'Plan references specific components/pages found in code'
    ],
    failCriteria: [
      'Agent asks "What pages are in the checkout flow?" or "What form fields are on the checkout page?" — questions that the code answers'
    ],
    tier: 7
  },
  {
    id: 'E31',
    name: 'Planner "Not Testing" Section Shows Judgment',
    mode: 'plan',
    baseTemplate: 'playwright-ts-full',
    task: 'Create a comprehensive test plan for the entire saucedemo.com application',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Plan includes a "Not Testing" section listing at least 2 items with explicit justification',
      'Justifications reference risk level or maintenance cost'
    ],
    failCriteria: [
      'No "Not Testing" section',
      'Section exists but has no justification',
      'Plan tries to test everything'
    ],
    tier: 7
  },
  {
    id: 'E32',
    name: 'Planner Journey-First Over Element-First',
    mode: 'plan',
    baseTemplate: 'playwright-ts-full',
    task: 'Plan tests for user authentication on saucedemo.com',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Plan proposes journey tests like "User can log in and access inventory"',
      'Total test count is compact (not one test per UI element)'
    ],
    failCriteria: [
      'Plan has individual tests for each form element',
      'More than 10 tests proposed for a single auth page',
      'Tests are named after UI elements rather than user goals'
    ],
    tier: 7
  },

  // ============================================
  // Full minus SUPATEST.md (base: playwright-ts-full, delete .supatest/)
  // ============================================
  {
    id: 'E3',
    name: 'Playwright Detection + SUPATEST.md Generation',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a test for removing items from the cart',
    modifications: [
      { type: 'delete', pattern: '.supatest' }
    ],
    needsFailureLog: false,
    passCriteria: [
      'Reads package.json, detects @playwright/test',
      'Reads 2+ existing tests',
      'Writes .supatest/SUPATEST.md',
      'Writes Playwright-syntax test',
      'File name matches *.spec.ts'
    ],
    failCriteria: [
      'Skips SUPATEST.md creation',
      'Wrong framework syntax'
    ],
    tier: 1
  },
  {
    id: 'E23',
    name: 'Discovery Reads Multiple Existing Tests',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a test for the sidebar navigation menu',
    modifications: [
      { type: 'delete', pattern: '.supatest' }
    ],
    needsFailureLog: false,
    passCriteria: [
      'Before writing any test, reads at minimum 2 existing .spec.ts files and at least 1 page object',
      'SUPATEST.md documents patterns found (naming conventions, selector strategies, assertion styles)',
      'New test follows the same patterns discovered'
    ],
    failCriteria: [
      'Reads 0-1 existing test files',
      'SUPATEST.md is generic/boilerplate',
      'New test uses different patterns than the codebase'
    ],
    tier: 5
  },
  {
    id: 'E24',
    name: 'Discovery Documents Selector Strategies',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a test for the inventory page filters',
    modifications: [
      { type: 'delete', pattern: '.supatest' }
    ],
    needsFailureLog: false,
    passCriteria: [
      'SUPATEST.md explicitly mentions [data-test] as the project\'s selector strategy',
      'Documents the page object pattern',
      'New test uses [data-test] attributes matching project convention'
    ],
    failCriteria: [
      'SUPATEST.md omits selector strategy',
      'Agent uses getByRole when the existing codebase uses [data-test] exclusively'
    ],
    tier: 5
  },
  {
    id: 'E25',
    name: 'Batch Tests Before Running',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write tests for all the error users: locked_out_user, problem_user, performance_glitch_user, error_user, visual_user',
    modifications: [
      { type: 'delete', pattern: '.supatest' }
    ],
    needsFailureLog: false,
    passCriteria: [
      'Agent writes all 5+ test cases into one or more files BEFORE executing any test run',
      'First npx playwright test command appears after all tests are written'
    ],
    failCriteria: [
      'Agent writes one test, runs it, then writes the next',
      'Alternates between Write and Bash commands for each test'
    ],
    tier: 5
  },

  // ============================================
  // Broken code (base: playwright-ts-full, various modes)
  // ============================================
  {
    id: 'E7',
    name: 'Browser for Selector Debugging After First Failure',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a test that clicks the hamburger menu and selects \'About\'',
    modifications: [
      {
        type: 'replace',
        file: 'pages/LoginPage.ts',
        find: '[data-test="username"]',
        replace: '[data-test="wrong-selector"]'
      }
    ],
    needsFailureLog: false,
    passCriteria: [
      'On first selector failure, runs agent-browser open then agent-browser snapshot -i',
      'Updates selector',
      'Test passes'
    ],
    failCriteria: [
      'Multiple selector guesses without opening browser'
    ],
    tier: 1
  },
  {
    id: 'E14',
    name: 'Fix Mode: Max 3 Attempts + Browser After Selector Failure',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing tests',
    modifications: [
      {
        type: 'replace',
        file: 'pages/LoginPage.ts',
        find: '[data-test="username"]',
        replace: '[data-test="wrong-selector"]'
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'Reads error, categorizes as "Selector"',
      'Uses Agent Browser',
      'Max 3 attempts',
      'Produces fix report'
    ],
    failCriteria: [
      'Exceeds 3 attempts',
      'Never opens browser',
      'Weakens assertions'
    ],
    tier: 2
  },
  {
    id: 'E15',
    name: 'Fix Mode: Minimal Targeted Changes',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing test',
    modifications: [
      {
        type: 'replace',
        file: 'pages/LoginPage.ts',
        find: '[data-test="username"]',
        replace: '[data-test="wrong-selector"]'
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'Edits only the broken line',
      'Uses Edit tool',
      'Other tests untouched',
      'Runs failing test first'
    ],
    failCriteria: [
      'Rewrites entire file',
      'Changes passing tests',
      'Uses test.skip()'
    ],
    tier: 2
  },
  {
    id: 'E16',
    name: 'Full Suite Regression After Individual Fixes',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing tests',
    modifications: [
      {
        type: 'replace',
        file: 'pages/LoginPage.ts',
        find: '[data-test="username"]',
        replace: '[data-test="wrong-selector"]'
      },
      {
        type: 'replace',
        file: 'pages/CartPage.ts',
        find: '[data-test="checkout"]',
        replace: '[data-test="wrong-checkout"]'
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'Fixes one at a time',
      'After all fixed, runs full suite',
      'Reports "X/Y passing"'
    ],
    failCriteria: [
      'Never runs full suite after fixes'
    ],
    tier: 4
  },
  {
    id: 'E17',
    name: 'Autonomous on Selector/Timing Issues',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a test for adding a product to the cart and verifying the cart badge updates',
    modifications: [
      {
        type: 'replace',
        file: 'pages/LoginPage.ts',
        find: '[data-test="username"]',
        replace: '[data-test="wrong-selector"]'
      }
    ],
    needsFailureLog: false,
    passCriteria: [
      'Fixes timing issues autonomously',
      'No AskUserQuestion',
      'Iterates until pass or max attempts'
    ],
    failCriteria: [
      'Asks user about timing/selector issues',
      'Adds waitForTimeout()'
    ],
    tier: 4
  },
  {
    id: 'E27',
    name: 'Fixer Categorizes Root Cause Before Fixing',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing tests',
    modifications: [
      {
        type: 'insert',
        file: 'tests/cart.spec.ts',
        insertAfter: 'await loginPage.login(\'standard_user\', \'secret_sauce\');',
        code: '\n    // Timing bug: clicking without waiting for page to fully load\n    await page.click(\'.inventory_item:first-child .btn_inventory\');'
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'Agent\'s reasoning identifies the root cause category (e.g., "Timing" or "State") before making changes',
      'Fix matches the category (adds wait/assertion, not selector change)',
      'Report includes root cause category'
    ],
    failCriteria: [
      'Agent jumps to editing code without analysis',
      'Applies wrong fix category (e.g., changes selector for a timing issue)'
    ],
    tier: 6
  },
  {
    id: 'E28',
    name: 'Fixer Does Not Weaken Assertions',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing test',
    modifications: [
      {
        type: 'replace',
        file: 'pages/CheckoutPage.ts',
        find: 'Thank you for your order!',
        replace: 'Order Confirmed!'
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'Agent corrects the test expectation to match actual app behavior OR identifies it as a real app change and reports',
      'Does NOT use toContain() instead of toHaveText()',
      'Does NOT add .not',
      'Does NOT use test.skip()'
    ],
    failCriteria: [
      'Weakens strict assertion to loose match',
      'Adds test.skip()',
      'Wraps in try/catch that swallows errors',
      'Changes toHaveText to toContainText to make a partial match pass'
    ],
    tier: 6
  },
  {
    id: 'E29',
    name: 'Fixer Adds Tags to Untagged Tests',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing tests',
    modifications: [
      {
        type: 'replace',
        file: 'tests/auth.spec.ts',
        find: 'test(\'@auth @smoke @test_type:regression Valid user can login successfully\'',
        replace: 'test(\'Valid user can login successfully\''
      },
      {
        type: 'replace',
        file: 'pages/LoginPage.ts',
        find: '[data-test="username"]',
        replace: '[data-test="user-name"]'
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'After fixing the broken selector, agent also adds { tags: [\'@feature:auth\', \'@priority:...\', \'@test_type:...\'] } to the previously untagged test'
    ],
    failCriteria: [
      'Fixes the selector but leaves the test without tags'
    ],
    tier: 6
  },

  // ============================================
  // Assertion integrity evals (base: playwright-ts-full, fix mode)
  // ============================================
  {
    id: 'E36',
    name: 'Fix Mode: Don\'t Change Count Assertion (Fix Add-to-Cart Selector)',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing tests',
    modifications: [
      {
        type: 'replace',
        file: 'pages/InventoryPage.ts',
        find: '[data-test="add-to-cart-${productId}"]',
        replace: '[data-test="add-cart-${productId}"]'
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'Traces count mismatch back to broken add-to-cart selector in InventoryPage.ts',
      'Fixes the selector pattern in getAddToCartButton()',
      'Cart count assertion stays assertCartItemCount(1)',
      'Does NOT change expected count values in test assertions'
    ],
    failCriteria: [
      'Changes assertCartItemCount(1) to assertCartItemCount(0)',
      'Adds test.skip() to cart tests',
      'Removes or weakens cart item count assertions',
      'Changes test expectations instead of fixing the selector'
    ],
    tier: 6
  },
  {
    id: 'E37',
    name: 'Fix Mode: Don\'t Remove Product Name Assertion (Fix Product Name Selector)',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing tests',
    modifications: [
      {
        type: 'replace',
        file: 'pages/InventoryPage.ts',
        find: '.inventory_item_name',
        replace: '.inventory_item_label'
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'Identifies broken CSS selector in getProductNames() and getCartItemNames()',
      'Fixes selector back to .inventory_item_name',
      'Product name assertions and expected arrays remain unchanged'
    ],
    failCriteria: [
      'Changes expected product name array to match empty/wrong data',
      'Removes product name matching assertions',
      'Weakens toEqual to toContain or removes product name checks',
      'Adds test.skip() to inventory tests'
    ],
    tier: 6
  },
  {
    id: 'E38',
    name: 'Fix Mode: Don\'t Weaken URL Assertion (Fix Navigation Selector)',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing tests',
    modifications: [
      {
        type: 'replace',
        file: 'pages/CartPage.ts',
        find: 'this.checkoutButton = page.locator(\'[data-test="checkout"]\');',
        replace: 'this.checkoutButton = page.locator(\'[data-test="continue-shopping"]\');'
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'Identifies that checkoutButton selector points to wrong element in CartPage.ts',
      'Fixes selector back to [data-test="checkout"]',
      'URL assertion checking for "checkout-step-one" remains unchanged'
    ],
    failCriteria: [
      'Changes URL assertion to expect "inventory.html" instead of "checkout-step-one"',
      'Removes or weakens the URL assertion',
      'Wraps URL assertion in try/catch'
    ],
    tier: 6
  },
  {
    id: 'E39',
    name: 'Fix Mode: Don\'t Change Price Sort Assertion (Fix Price Parser)',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing tests',
    modifications: [
      {
        type: 'replace',
        file: 'pages/InventoryPage.ts',
        find: "return prices.map(p => parseFloat(p.replace('$', '')));",
        replace: 'return prices.map(p => parseFloat(p));'
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'Identifies that getProductPrices() fails to strip "$" before parsing',
      'Restores the replace(\'$\', \'\') call in the parseFloat chain',
      'Sort order assertions remain unchanged'
    ],
    failCriteria: [
      'Removes or weakens sort order assertions in sorting.spec.ts',
      'Changes toEqual to a weaker matcher',
      'Modifies expected price arrays or sort logic in tests',
      'Adds NaN handling in tests instead of fixing the parser'
    ],
    tier: 6
  },
  {
    id: 'E40',
    name: 'Fix Mode: Don\'t Remove Error Message Assertion (Fix Error Selector)',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing tests',
    modifications: [
      {
        type: 'replace',
        file: 'pages/CheckoutPage.ts',
        find: 'this.errorMessage = page.locator(\'[data-test="error"]\');',
        replace: 'this.errorMessage = page.locator(\'[data-test="error-message"]\');'
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'Identifies broken error message selector in CheckoutPage.ts',
      'Fixes selector back to [data-test="error"]',
      'Error message text assertions (toContainText) remain unchanged'
    ],
    failCriteria: [
      'Removes error message assertions from checkout tests',
      'Changes toContainText to toBeVisible (loses text verification)',
      'Adds try/catch around error message assertions',
      'Skips checkout validation tests'
    ],
    tier: 6
  },
  {
    id: 'E41',
    name: 'Fix Mode: Don\'t Change Subtotal Assertion (Fix Amount Parser)',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing tests',
    modifications: [
      {
        type: 'replace',
        file: 'pages/CheckoutPage.ts',
        find: "async asyncGetSubtotal() {\n    const text = await this.subtotalLabel.textContent();\n    return text ? parseFloat(text.replace('Item total: $', '')) : 0;\n  }",
        replace: "async asyncGetSubtotal() {\n    const text = await this.subtotalLabel.textContent();\n    // Bug: parsing the wrong prefix causes NaN\n    const cleaned = text ? text.replace('Subtotal: ', '') : '0';\n    return parseFloat(cleaned);\n  }"
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'Identifies wrong text prefix in asyncGetSubtotal() parser',
      'Fixes replace prefix back to \'Item total: $\'',
      'Subtotal assertions (toBe(29.99), toBeCloseTo) remain unchanged'
    ],
    failCriteria: [
      'Changes expected subtotal value to match NaN or wrong number',
      'Removes math verification assertions',
      'Uses toBeGreaterThan(0) instead of exact value check',
      'Adds NaN fallback in test instead of fixing parser'
    ],
    tier: 6
  },
  {
    id: 'E42',
    name: 'Fix Mode: Don\'t Skip Tests (Fix Import Path)',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing tests',
    modifications: [
      {
        type: 'replace',
        file: 'tests/cart.spec.ts',
        find: "import { CartPage } from '../pages/CartPage';",
        replace: "import { CartPage } from '../pages/ShoppingCartPage';"
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'Fixes import path back to ../pages/CartPage',
      'All cart test assertions remain completely unchanged',
      'Does NOT create a new ShoppingCartPage.ts file'
    ],
    failCriteria: [
      'Creates a new ShoppingCartPage.ts with simplified/weakened methods',
      'Adds test.skip() to cart tests',
      'Rewrites cart tests without page objects (inlines assertions)',
      'Removes cart tests entirely'
    ],
    tier: 6
  },
  {
    id: 'E43',
    name: 'Fix Mode: Don\'t Downgrade Equality (Fix Whitespace in Data Extraction)',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing tests',
    modifications: [
      {
        type: 'replace',
        file: 'pages/CartPage.ts',
        find: "return await this.page.locator('.inventory_item_name').allTextContents();",
        replace: "return (await this.page.locator('.inventory_item_name').allTextContents()).map(n => '  ' + n);"
      }
    ],
    needsFailureLog: true,
    passCriteria: [
      'Identifies whitespace issue in getCartItemNames() in CartPage.ts',
      'Removes the .map() that prepends whitespace OR adds .trim() in the page object',
      'Test assertions remain with exact product name strings'
    ],
    failCriteria: [
      'Changes toContain(\'Sauce Labs Backpack\') to toContain(\'Backpack\') (partial match)',
      'Adds .trim() in the test file instead of fixing the page object',
      'Uses regex matching in test assertions for "flexibility"',
      'Weakens strict equality to partial matching in test expectations'
    ],
    tier: 6
  },

  // ============================================
  // WebDriverIO (base: wdio-ts-full)
  // ============================================
  {
    id: 'E4',
    name: 'WebDriverIO Framework Adaptation',
    mode: 'build',
    baseTemplate: 'wdio-ts-full',
    task: 'Write a test that verifies sorting products by price low to high',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Detects WDIO from package.json and wdio.conf.ts',
      'Uses describe/it syntax',
      'Uses $() / $$() selectors',
      'Tags in title string'
    ],
    failCriteria: [
      'Generates Playwright code in a WDIO project',
      'Uses { tags } format'
    ],
    tier: 3
  },

  // ============================================
  // Cypress (base: cypress-ts-full)
  // ============================================
  {
    id: 'E5',
    name: 'Cypress Framework Adaptation',
    mode: 'build',
    baseTemplate: 'cypress-ts-full',
    task: 'Write a test for the cart page - adding and removing items',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Uses cy.get(), cy.visit(), cy.should()',
      'File matches *.cy.ts',
      'Placed in cypress/e2e/'
    ],
    failCriteria: [
      'Uses async/await (Cypress is chain-based)',
      'Uses page.locator()'
    ],
    tier: 3
  },

  // ============================================
  // Mobile / device-state feedback (SUP-25)
  // base: maestro-ios-blank — requires macOS + booted iOS simulator
  // ============================================
  {
    id: 'E70',
    name: 'Mobile Tool Selection — Inspect Foreground App',
    mode: 'build',
    baseTemplate: 'maestro-ios-blank',
    task: "What's on the phone screen right now? List 5 UI elements I can target with their identifiers.",
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Calls mcp__maestro__inspect_view_hierarchy or inspect_screen within first 2 tool calls',
      'Calls mcp__maestro__take_screenshot at least once',
      'Reports 5 elements with at least 3 carrying accessibility identifiers',
      'Does NOT shell out to adb / xcrun / appium via Bash'
    ],
    failCriteria: [
      'Uses Bash to call adb shell or xcrun simctl for inspection',
      'Falls back to "no devices available" without calling mcp__maestro__list_devices',
      'Writes a Maestro YAML flow (this fixture is exploration-only)'
    ],
    tier: 11
  },
  {
    id: 'E71',
    name: 'Mobile Selector Preference — Stable IDs Over XPath',
    mode: 'build',
    baseTemplate: 'maestro-ios-blank',
    task: "I'm writing an Appium test that needs to tap the 'General' row in iOS Settings. Give me one selector.",
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Calls mcp__maestro__inspect_view_hierarchy or inspect_screen at least once',
      'Returned selector references General (e.g. com.apple.settings.general or accessibility label "General")',
      'Prefers resource-id or accessibility-label over XPath',
      'Justification mentions stability / breakage resistance'
    ],
    failCriteria: [
      'Returns an XPath selector as the primary recommendation when a resource-id was available',
      'Hallucinates a selector without inspecting the live device',
      'Uses Bash to grep for selectors instead of mcp__maestro__inspect_view_hierarchy'
    ],
    tier: 11
  },

  // ============================================
  // Mobile / SauceLabs MyDemoApp on Android (SUP-25 deep evals)
  // base: maestro-ios-blank (template is platform-agnostic; runner needs
  //   MyDemoApp installed on a booted Android emulator on the catalog screen)
  // ============================================
  {
    id: 'E72',
    name: 'Mobile Multi-Element Discovery on Real App Catalog',
    mode: 'build',
    baseTemplate: 'maestro-ios-blank',
    task: "On the connected Android emulator there is a shopping app open on its product catalog screen. I'm writing an Appium test. Give me selectors for: (a) the hamburger / menu icon, (b) the cart icon, (c) the sort icon, (d) the first product card, (e) the first product's title text. For each, return one stable selector.",
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Calls mcp__maestro__inspect_view_hierarchy or inspect_screen at least once',
      'Returns 5 distinct selectors (one per requested element)',
      'Selectors include the real resource-ids (menuIV, cartRL or cartIV, sortIV, titleTV) — not fabricated',
      'No XPath as primary when a resource-id was available in the hierarchy'
    ],
    failCriteria: [
      'Skips inspection and guesses generic selectors',
      'Returns fewer than 5 selectors (incomplete coverage)',
      'Returns "android.widget.ImageView" or class-name selectors instead of resource-id when resource-ids exist'
    ],
    tier: 11
  },
  {
    id: 'E73',
    name: 'Mobile Multi-Step Login Walkthrough',
    mode: 'build',
    baseTemplate: 'maestro-ios-blank',
    task: "On the booted Android emulator the SauceLabs MyDemoApp is open. Walk me through logging in as 'bob@example.com' / '10203040'. Navigate through the screens, identify the relevant form fields and buttons, and at each step tell me what you're tapping and what selector you'd use in an Appium test.",
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Calls mcp__maestro__inspect_view_hierarchy or inspect_screen at multiple steps (not just once at the start)',
      'Identifies menu → login navigation correctly',
      'Identifies username / password fields and login button with stable selectors',
      'Reports what changed on screen after each action'
    ],
    failCriteria: [
      'Inspects once at the start, then narrates the rest from memory without re-inspecting',
      'Uses screenshots as the only verification mechanism (screenshots without hierarchy = guessing)',
      'Fabricates selectors for screens it never inspected'
    ],
    tier: 11
  },
  {
    id: 'E74',
    name: 'Mobile Real Test Authoring with Discovered Selectors',
    mode: 'build',
    baseTemplate: 'maestro-ios-blank',
    task: "Write a WebdriverIO + Appium test in TypeScript for the SauceLabs MyDemoApp running on the booted Android emulator. The test should: log in as bob@example.com / 10203040, navigate back to the catalog, tap the first product, tap 'Add to cart', open the cart, and assert that the cart contains 1 item. Use real selectors taken from the live app's view hierarchy — do not fabricate any selector.",
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Calls mcp__maestro__inspect_view_hierarchy or inspect_screen on multiple screens during selector discovery',
      'Produced test file contains real resource-ids from the live app (e.g. com.saucelabs.mydemoapp.android:id/menuIV, cartRL, titleTV)',
      'Uses WebdriverIO accessibility-id / resource-id selector syntax, not Maestro YAML',
      'Test flow logically matches the requested steps'
    ],
    failCriteria: [
      'Test contains fabricated/guessed selectors (e.g. //div[@id=...] or unrelated package names)',
      'Generates a Maestro YAML flow instead of a WDIO test',
      'Skips inspection and writes the test entirely from training-data assumptions about MyDemoApp'
    ],
    tier: 11
  },
  {
    id: 'E81',
    name: 'Mobile WebView Guidance — Context Switch Recommended',
    mode: 'build',
    baseTemplate: 'maestro-ios-blank',
    task: "The SauceLabs MyDemoApp on the booted Android emulator has a WebView screen accessible from the menu (called 'WebView'). Explain how I would interact with elements inside the WebView in an Appium test — for example, tapping a link inside the WebView. What's the right approach?",
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      "Explains that mcp__maestro__inspect_view_hierarchy / inspect_screen / Maestro doesn't descend into WebView DOM",
      "Recommends Appium's context-switch (e.g. driver.getContexts() / driver.switchContext('WEBVIEW_...'))",
      'Mentions that web-style selectors (CSS / DOM) work inside WebView context, native selectors outside'
    ],
    failCriteria: [
      'Claims you can use mcp__maestro__inspect_view_hierarchy to read WebView DOM',
      'Suggests authoring a Maestro YAML flow for WebView interaction',
      'Misses the context-switch concept entirely'
    ],
    tier: 11
  },
  {
    id: 'E83',
    name: 'Mobile Test Debug — Inspect Device Before Re-running',
    mode: 'build',
    baseTemplate: 'maestro-ios-blank',
    task: "I just ran an Appium test against the booted Android emulator (SauceLabs MyDemoApp) and it failed. The test is supposed to add the first product to the cart but it fails on the 'Add to cart' step with:\n\n  Error: An element could not be located on the page using the given search parameters.\n     selector: ~Tap to add product to cart\n     at ProductsListPage.addFirstToCart (test/pages/products.page.ts:42)\n     at test/specs/cart.spec.ts:12\n\n  Spec Files: 0 passed, 1 failed, 1 total (100% completed) in 00:00:14\n\nThe selector worked last week. Help me figure out what's wrong.",
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Calls mcp__maestro__inspect_view_hierarchy, inspect_screen, or take_screenshot BEFORE suggesting a re-run',
      'Identifies the actual selector (or unexpected state) from live device state',
      'Recommends a fix based on live device state, not guessed selectors'
    ],
    failCriteria: [
      'First response is "re-run the test" without inspecting',
      'Edits .spec.ts or page object before inspecting the device',
      'Greps logs / re-runs > 1 time before any mcp__maestro__* call',
      'Adds waits/sleeps as primary fix without inspection',
      'Yak-shaves into adb / xcrun / find / curl Bash commands'
    ],
    tier: 11
  },
  {
    id: 'E82',
    name: 'Mobile Failure-Mode Debugging — Use Device State First',
    mode: 'build',
    baseTemplate: 'maestro-ios-blank',
    task: "I'm trying to use the SauceLabs MyDemoApp on the booted Android emulator. I tapped 'Add to cart' on a product but the cart count in the header doesn't seem to update. Help me figure out what's wrong.",
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Calls mcp__maestro__inspect_view_hierarchy and/or take_screenshot to look at current state BEFORE hypothesizing',
      'Identifies the actual cart-count element and reports its current value/state from the live device',
      'Distinguishes between possible causes (e.g. cart-count rendered but with wrong selector, vs. cart genuinely empty, vs. wrong screen)'
    ],
    failCriteria: [
      'Hypothesizes causes without inspecting the device first',
      'Asks the user to debug it themselves before doing any device-state inspection',
      'Recommends shelling out to adb logcat instead of using mcp__maestro__inspect_view_hierarchy'
    ],
    tier: 11
  },

  // ============================================
  // E84–E100: Gap-fill evals (suite expansion to 100)
  // ============================================
  {
    id: 'E84',
    name: 'Cypress Fix: Wrong Login Selector',
    mode: 'fix',
    baseTemplate: 'cypress-ts-full',
    task: 'Fix the failing Cypress auth tests',
    modifications: [
      {
        type: 'replace',
        file: 'cypress/pages/LoginPage.ts',
        find: '[data-test="login-button"]',
        replace: '[data-test="login-btn"]',
      },
    ],
    needsFailureLog: true,
    passCriteria: [
      'Fixes selector in cypress/pages/LoginPage.ts',
      'Keeps Cypress chain syntax (cy.get, cy.should)',
      'Auth tests pass',
    ],
    failCriteria: [
      'Converts project to Playwright',
      'Uses page.locator() or async/await test style',
      'Weakens login assertions',
    ],
    tier: 3,
  },
  {
    id: 'E85',
    name: 'WDIO Fix: Wrong Login Selector',
    mode: 'fix',
    baseTemplate: 'wdio-ts-full',
    task: 'Fix the failing WebdriverIO auth tests',
    modifications: [
      {
        type: 'replace',
        file: 'pages/LoginPage.ts',
        find: '[data-test="username"]',
        replace: '[data-test="user-name"]',
      },
    ],
    needsFailureLog: true,
    passCriteria: [
      'Fixes username selector in pages/LoginPage.ts',
      'Uses WebdriverIO $() syntax',
      'Auth specs pass',
    ],
    failCriteria: [
      'Rewrites tests in Playwright',
      'Uses cy.get() or page.locator()',
    ],
    tier: 3,
  },
  {
    id: 'E86',
    name: 'Accessibility: Login via Roles and Labels',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write an accessibility-focused login test for saucedemo.com using getByRole, getByLabel, or other accessible locators — avoid CSS class selectors',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Uses getByRole, getByLabel, getByPlaceholder, or getByTestId',
      'No CSS class-only selectors for form fields',
      'Test passes',
    ],
    failCriteria: [
      'Uses .login-box or other fragile CSS classes as primary locators',
      'Uses XPath',
    ],
    tier: 4,
  },
  {
    id: 'E87',
    name: 'Network Mock via page.route',
    mode: 'build',
    baseTemplate: 'playwright-ts-blank',
    task: 'Write a Playwright test for https://www.saucedemo.com that uses page.route to intercept the inventory API and assert the page shows exactly 2 mocked products',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Uses page.route() or context.route() to mock API response',
      'Asserts mocked product count or names on page',
      'Test runs and passes',
    ],
    failCriteria: [
      'No network interception — hits live API only',
      'Mocks so aggressively the login flow breaks without handling it',
    ],
    tier: 4,
  },
  {
    id: 'E88',
    name: 'No Hardcoded Credentials in Spec',
    mode: 'build',
    baseTemplate: 'playwright-ts-blank',
    task: 'Write a CI-ready login test for https://www.saucedemo.com. Credentials must not be hardcoded as string literals in the .spec.ts file — use environment variables or a dedicated auth helper',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'No plain-text password/username literals in the spec file',
      'Uses process.env, dotenv, or imported auth constants from a non-spec file',
      'Test passes',
    ],
    failCriteria: [
      'Hardcodes standard_user / secret_sauce directly in the spec',
      'Embeds credentials in test title or comments only but still in spec file',
    ],
    tier: 5,
  },
  {
    id: 'E89',
    name: 'Replace waitForTimeout with Proper Wait',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing auth test — remove flaky timing workarounds and use proper Playwright waits',
    modifications: [
      {
        type: 'replace',
        file: 'pages/LoginPage.ts',
        find: '[data-test="login-button"]',
        replace: '[data-test="login-btn"]',
      },
      {
        type: 'replace',
        file: 'tests/auth.spec.ts',
        find: "await loginPage.login('standard_user', 'secret_sauce');",
        replace: "await page.waitForTimeout(5000);\n    await loginPage.login('standard_user', 'secret_sauce');",
      },
    ],
    needsFailureLog: true,
    passCriteria: [
      'Fixes broken login-button selector in LoginPage.ts',
      'Removes page.waitForTimeout from test',
      'Uses expect().toBeVisible() or equivalent explicit wait',
    ],
    failCriteria: [
      'Keeps waitForTimeout as primary wait strategy',
      'Increases timeout value instead of fixing selector',
    ],
    tier: 4,
  },
  {
    id: 'E90',
    name: 'API vs E2E Test Strategy',
    mode: 'plan',
    baseTemplate: 'playwright-ts-full',
    task: 'Create a test plan for saucedemo.com that separates what should be tested via API contract tests vs browser E2E tests. Do not write or run any tests.',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Produces a written plan document',
      'Distinguishes API-level vs UI-level coverage',
      'Does NOT run npx playwright test',
      'Does NOT create .spec.ts files',
    ],
    failCriteria: [
      'Runs tests or writes spec files',
      'Only lists UI tests with no API layer analysis',
    ],
    tier: 7,
  },
  {
    id: 'E91',
    name: 'Report: Cypress to Playwright Migration Session',
    mode: 'report',
    baseTemplate: 'playwright-ts-full',
    task: "This session migrated 4 Cypress tests to Playwright:\n\n1. **auth.cy.ts → auth.spec.ts** - Migrated login tests, converted cy.get() to getByTestId()\n2. **cart.cy.ts → cart.spec.ts** - Migrated cart tests, created CartPage page object\n3. **checkout.cy.ts → checkout.spec.ts** - Migrated checkout flow\n4. **cypress.config.ts removed** - Replaced with playwright.config.ts\n\n### Files Changed\n- `tests/auth.spec.ts` (new)\n- `tests/cart.spec.ts` (new)\n- `tests/checkout.spec.ts` (new)\n- `pages/CartPage.ts` (new)\n- `playwright.config.ts` (new)\n- Removed `cypress/` directory\n\n### Final Status\nAll 4 migrated test files passing. SUPATEST.md updated with Playwright patterns.",
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Creates .supatest/reports/*/index.html',
      'HTML is self-contained',
      'Documents migration mapping (Cypress → Playwright)',
      'Does NOT run tests or create spec files',
    ],
    failCriteria: [
      'Runs test commands',
      'Creates or modifies .spec.ts files during report',
      'Missing migration summary section',
    ],
    tier: 3,
  },
  {
    id: 'E92',
    name: 'Test-Feature: Inventory Sort Dropdown',
    mode: 'test-feature',
    baseTemplate: 'playwright-ts-full',
    task: 'Test the inventory sort dropdown on saucedemo.com (standard_user / secret_sauce). Verify Name (A→Z), Name (Z→A), and Price (low→high) sort correctly. Write automation tests and generate a report with screenshots.',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Tests at least 3 sort options',
      'Runs tests and they pass',
      'Generates HTML report at .supatest/reports/*/index.html',
      'Report includes screenshots',
    ],
    failCriteria: [
      'Skips sort verification',
      'No report generated',
      'Uses AskUserQuestion in headless mode',
    ],
    tier: 3,
  },
  {
    id: 'E93',
    name: 'Cypress Fix: Stay in Cypress Framework',
    mode: 'fix',
    baseTemplate: 'cypress-ts-full',
    task: 'Fix the failing cart test in cypress/e2e/cart.cy.ts',
    modifications: [
      {
        type: 'replace',
        file: 'cypress/pages/CartPage.ts',
        find: '[data-test="checkout"]',
        replace: '[data-test="checkout-btn"]',
      },
    ],
    needsFailureLog: true,
    passCriteria: [
      'Fixes selector in cypress/pages/CartPage.ts',
      'Keeps *.cy.ts files and Cypress APIs',
      'Cart test passes',
    ],
    failCriteria: [
      'Creates Playwright .spec.ts files',
      'Adds playwright.config.ts',
      'Deletes cypress/ directory',
    ],
    tier: 3,
  },
  {
    id: 'E94',
    name: 'Parallel-Safe Cart Test',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a cart test that is safe to run in parallel workers — each test must use its own session and not depend on shared cart state from other tests',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Test logs in fresh or uses isolated context',
      'Does not assume empty cart from prior test run',
      'Uses unique product or cleans up its own cart state',
      'Test passes',
    ],
    failCriteria: [
      'Assumes cart is empty without logging in first',
      'Relies on test execution order',
    ],
    tier: 4,
  },
  {
    id: 'E95',
    name: 'Fix Broken baseURL in Config',
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing tests — something in the Playwright config is wrong',
    modifications: [
      {
        type: 'replace',
        file: 'playwright.config.ts',
        find: "baseURL: 'https://www.saucedemo.com'",
        replace: "baseURL: 'https://www.saucedemo.com.invalid'",
      },
    ],
    needsFailureLog: true,
    passCriteria: [
      'Fixes baseURL in playwright.config.ts',
      'Does not disable tests or skip suite',
      'Auth or smoke test passes after fix',
    ],
    failCriteria: [
      'Hardcodes full URLs in every test instead of fixing config',
      'Sets baseURL to localhost without justification',
    ],
    tier: 5,
  },
  {
    id: 'E96',
    name: 'test.step for Readable Checkout Flow',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a checkout test using test.step() to structure the flow into clear steps: login, add item, open cart, checkout, fill form, confirm order',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Uses test.step() with named steps',
      'At least 4 distinct steps',
      'Full checkout flow passes',
    ],
    failCriteria: [
      'No test.step() usage',
      'Single monolithic test with no step structure',
    ],
    tier: 4,
  },
  {
    id: 'E97',
    name: "Don't Comment Out Failing Assertion",
    mode: 'fix',
    baseTemplate: 'playwright-ts-full',
    task: 'Fix the failing cart test',
    modifications: [
      {
        type: 'replace',
        file: 'tests/cart.spec.ts',
        find: `    await inventoryPage.goToCart();

    await cartPage.assertCartItemCount(1);

    const itemNames = await cartPage.getCartItemNames();`,
        replace: `    await inventoryPage.goToCart();

    // await cartPage.assertCartItemCount(1);

    const itemNames = await cartPage.getCartItemNames();`,
      },
      {
        type: 'replace',
        file: 'pages/InventoryPage.ts',
        find: 'add-to-cart-${productId}',
        replace: 'add-cart-${productId}',
      },
    ],
    needsFailureLog: true,
    passCriteria: [
      'Fixes add-to-cart selector in InventoryPage.ts',
      'Restores cart count assertion (uncomments or re-adds)',
      'Test passes with assertion intact',
    ],
    failCriteria: [
      'Leaves assertion commented out',
      'Removes assertion entirely',
      'Changes expected count to 0',
    ],
    tier: 5,
  },
  {
    id: 'E98',
    name: 'Configure Trace on First Retry',
    mode: 'build',
    baseTemplate: 'playwright-ts-blank',
    task: 'Write a simple login test for saucedemo.com AND update playwright.config.ts to enable trace: on-first-retry and screenshot: only-on-failure',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Updates playwright.config.ts with trace and screenshot settings',
      'Login test passes',
      'Does not set trace: off or trace: on for every run without reason',
    ],
    failCriteria: [
      'Ignores config — only writes test file',
      'Disables tracing entirely',
    ],
    tier: 4,
  },
  {
    id: 'E99',
    name: 'Mobile: list_devices Before Inspect',
    mode: 'build',
    baseTemplate: 'maestro-ios-blank',
    task: 'I want to inspect the connected Android emulator and list UI elements on screen. Before inspecting, confirm which devices are available.',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Calls mcp__maestro__list_devices before inspect_view_hierarchy or inspect_screen',
      'Reports available device(s)',
      'Then inspects and lists UI elements',
    ],
    failCriteria: [
      'Skips list_devices and goes straight to inspect',
      'Uses adb shell via Bash for device listing',
      'Assumes device without checking availability',
    ],
    tier: 11,
  },
  {
    id: 'E100',
    name: 'Logout Test and SUPATEST.md Update',
    mode: 'build',
    baseTemplate: 'playwright-ts-full',
    task: 'Write a logout test using existing page objects. After adding the test, update .supatest/SUPATEST.md with the logout flow and selectors discovered',
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Uses existing LoginPage/InventoryPage patterns',
      'Writes logout test that passes',
      'Updates SUPATEST.md with logout section',
    ],
    failCriteria: [
      'Uses raw locators ignoring existing page objects',
      'Does not update SUPATEST.md',
      'Re-runs full discovery from scratch ignoring existing docs',
    ],
    tier: 4,
  },
  {
    id: 'E101',
    name: 'Mobile Maestro→WDIO Locator Translation (Prod Regression)',
    mode: 'build',
    baseTemplate: 'maestro-ios-wdio-stub',
    task: `This is a WebdriverIO + Appium iOS page-object stub (see pages/settings.screen.ts for the ~accessibilityId style).

Read references/lumpsum-inspect-snippet.json — real inspect_screen output with THREE elements carrying a11y "mfAddStock" and no button/type field on those rows. Maestro tapped the first icon using references/maestro-tap-snippet.yaml (index: 0).

Implement tapFirstSchemeAddIcon() in pages/lumpsum.screen.ts:
- Use WebdriverIO Appium selectors faithful to the hierarchy (a11y labels, not invented types)
- Disambiguate the first mfAddStock the same way Maestro used index 0
- Do NOT add XCUIElementTypeButton or other types unless the JSON shows them for that element
- Match the ~accessibilityId style from settings.screen.ts

Authoring only — do not run npm install, wdio, or tsc. Edit pages/lumpsum.screen.ts only.`,
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Reads references/lumpsum-inspect-snippet.json before editing',
      'Uses ~mfAddStock or label predicate without invented XCUIElementType',
      'Disambiguates first duplicate (nth/index/$$[0]) matching Maestro index: 0',
      'Does not hardcode session-specific folio or fund values',
    ],
    failCriteria: [
      'Uses -ios predicate string with XCUIElementTypeButton when hierarchy had no type',
      'Single $(\'~mfAddStock\') with no index disambiguation on a list with three matches',
      'Skips reference JSON and guesses selectors from training data',
      'Runs npm install or wdio instead of implementing the page object',
    ],
    tier: 11,
  },
  {
    id: 'E102',
    name: 'WDIO Log Interpretation — Test Ran (Prod Regression)',
    mode: 'build',
    baseTemplate: 'wdio-log-interpret-stub',
    task: `Read references/wdio-success-log.txt — a real WebdriverIO run that completed with "Spec Files: 1 passed, 1 total".

The user says: "The test ran, but the agent keeps saying the test hasn't actually started."

Edit run-analysis.md only:
- Set didRun to yes/no based on the log (not user frustration)
- Set passed and failed counts from the log
- Write one sentence summary explaining whether the test executed

Do NOT run wdio or bash. Do NOT claim the test failed to start when the log shows completion.`,
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Reads references/wdio-success-log.txt',
      'Acknowledges test ran with 1 passed',
      'Does not say test never started / did not run',
    ],
    failCriteria: [
      'Claims test has not started despite Spec Files line',
      'Reports 0 passed or incorrect counts',
      'Runs bash/wdio instead of analyzing the log',
    ],
    tier: 11,
  },
  {
    id: 'E103',
    name: 'iOS Port From Android — Hierarchy Not Copy-Paste (Prod Regression)',
    mode: 'build',
    baseTemplate: 'android-ios-port-stub',
    task: `pages/android/login.screen.ts shows the Android tapLogin() using resource-id.

Port tapLogin() to pages/ios/login.screen.ts for iOS:
- Read references/ios-login-inspect-snippet.json (a11y SignInButton on iOS)
- Use WebdriverIO ~accessibilityId style — NOT Android UiSelector/resource-id
- Do NOT copy com.fundsindia or btn_login from the Android file

Authoring only — edit pages/ios/login.screen.ts only. Do not run wdio or inspect a live device (reference JSON is the iOS evidence).`,
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Reads ios-login-inspect-snippet.json',
      'Uses ~SignInButton or equivalent iOS a11y selector',
      'Does not copy Android resource-id into iOS file',
    ],
    failCriteria: [
      'Copies android=new UiSelector().resourceId(...) to iOS',
      'Guesses selector without reference JSON',
      'Leaves tapLogin throwing Not implemented',
    ],
    tier: 11,
  },
  {
    id: 'E104',
    name: 'WDIO Run Scope — Single Spec Only (Prod Regression)',
    mode: 'build',
    baseTemplate: 'wdio-run-scope-stub',
    task: `This project has test/specs/cart.spec.ts and test/specs/checkout.spec.ts. wdio.conf.ts runs all specs via a glob.

The user asked: "Run ONLY test/specs/cart.spec.ts with workers=1."

Write the exact npx wdio command to run-command.txt (one line). Must:
- Target cart.spec.ts only (use --spec)
- NOT run checkout.spec.ts or test/specs/**/*.spec.ts
- Include --workers=1

Do NOT execute the command — authoring only.`,
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Command includes --spec and cart.spec.ts',
      'Does not use full-suite glob',
      'Includes workers=1',
    ],
    failCriteria: [
      'Runs entire suite (glob or no --spec)',
      'Includes checkout.spec.ts',
      'Executes wdio instead of writing run-command.txt',
    ],
    tier: 11,
  },
  {
    id: 'E105',
    name: 'Root Cause Diagnosis — completeDocumentUploadScreen (Prod Regression)',
    mode: 'build',
    baseTemplate: 'mobile-root-cause-stub',
    task: `Read references/wdio-failure.log and references/inspect-upload-screen.json.

The test fails in completeDocumentUpload() with ~UploadButton. The user has been debugging for a day with no root cause.

Edit root-cause.md only:
- Identify failing method and wrong selector from the log
- Identify correct selector from inspect JSON (SubmitUpload)
- Explain root cause in one sentence
- Propose a one-line selector fix

Do NOT suggest grep/tail/rerun loops. Do NOT run bash or wdio.`,
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Names ~UploadButton as wrong selector',
      'Cites SubmitUpload from inspect JSON',
      'Identifies completeDocumentUpload failure',
      'No grep/rerun loop as primary fix',
    ],
    failCriteria: [
      'Vague root cause without hierarchy evidence',
      'Suggests log-grep debug spiral',
      'Wrong selector left unmentioned',
    ],
    tier: 11,
  },
  {
    id: 'E106',
    name: 'Efficient Debug Plan — No Slowness Loop (Prod Regression)',
    mode: 'build',
    baseTemplate: 'mobile-efficient-debug-stub',
    task: `Read references/wdio-failure.log. The user complained the agent is too slow.

One test run already failed. Write debug-plan.md with **exactly 3 steps** (numbered 1–3):
- Step 1 MUST be mcp__maestro__inspect_screen or inspect_view_hierarchy (device state) — NOT grep/tail on logs
- At most ONE step may rerun the test (after inspect)
- No bash log-scraping steps

Authoring only — do not run commands.`,
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Exactly 3 steps',
      'Step 1 is device inspect',
      'At most one rerun mentioned',
    ],
    failCriteria: [
      'More than 3 steps',
      'Step 1 is grep/tail/rerun',
      'Multiple rerun steps',
    ],
    tier: 11,
  },
  {
    id: 'E107',
    name: 'Non-Destructive Fix — Keep Working Methods (Prod Regression)',
    mode: 'build',
    baseTemplate: 'mobile-nondestructive-fix-stub',
    task: `pages/document-upload.screen.ts has working fillShipping(), submitOrder(), and verifyConfirmation().

Only completeDocumentUpload() is broken — it uses ~UploadButton but references/inspect-upload-screen.json shows a11y SubmitUpload.

Fix completeDocumentUpload() ONLY:
- Use ~SubmitUpload from the inspect JSON
- Keep fillShipping, submitOrder, verifyConfirmation unchanged

Edit pages/document-upload.screen.ts only. Authoring only.`,
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'All four methods still present',
      'completeDocumentUpload uses ~SubmitUpload',
      'No ~UploadButton left',
    ],
    failCriteria: [
      'Removed working methods while fixing upload',
      'Still uses ~UploadButton',
      'Rewrote entire file / deleted unrelated code',
    ],
    tier: 11,
  },
  {
    id: 'E108',
    name: 'Stop WDIO/bash Spiral on @mobile Run (Prod Regression)',
    mode: 'build',
    baseTemplate: 'mobile-run-strategy-stub',
    task: `The user asked: "Run \`@mobile/tests/android/b2c-onboarding-android.spec.ts\` and report pass/fail counts only — do not fix code."

Write run-strategy.md only (authoring — do not execute wdio or bash):
- At most **one** wdio run step
- Report pass/fail from the Spec Files summary line
- No grep/tail log-scraping loops
- ≤4 numbered steps total`,
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Single wdio run in plan',
      'Reports pass/fail from output',
      'No grep/tail spiral',
    ],
    failCriteria: [
      'Multiple wdio reruns',
      'grep/tail as primary steps',
      'More than 4 steps',
    ],
    tier: 11,
  },
  {
    id: 'E109',
    name: 'Pin Emulator When User Names 5554 (Prod Regression)',
    mode: 'build',
    baseTemplate: 'mobile-device-pin-stub',
    task: `Two emulators are connected (see references/devices-list.json): emulator-5554 and emulator-5556.

The user said: "On **emulator-5554**, tap the Analysis tab and report what you see."

Write device-plan.md only (authoring — do not run commands):
- Step 1: mcp__maestro__list_devices
- Select **emulator-5554** (port 5554) — not 5556
- Then inspect on that device`,
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'list_devices before inspect',
      'Pins emulator-5554',
      'Does not target 5556',
    ],
    failCriteria: [
      'Skips list_devices',
      'Uses adb devices',
      'Acts on emulator-5556',
    ],
    tier: 11,
  },
  {
    id: 'E113',
    name: 'Suite Path — Inspect Before Full Re-run (Prod Regression)',
    mode: 'build',
    baseTemplate: 'mobile-suite-next-steps-stub',
    task: `Read references/prior-failure.log — a full \`@mobile/tests/android/onboarding/**\` suite run already failed (48 specs).

Write next-steps.md only (authoring — do not run wdio/bash):
- Step 1 MUST be mcp__maestro__inspect_screen or inspect_view_hierarchy
- Propose fixing **one** failing spec, then **one** targeted --spec rerun
- Do NOT rerun the full suite glob as step 1
- ≤4 numbered steps`,
    modifications: [],
    needsFailureLog: false,
    passCriteria: [
      'Inspect first',
      'Single-spec fix and verify',
      'No full-suite rerun as step 1',
    ],
    failCriteria: [
      'Rerun **/*.spec as first step',
      'Skips inspect',
      'Multiple full-suite reruns',
    ],
    tier: 11,
  },
];

/**
 * Recursively copy a directory, excluding specified patterns
 */
async function copyDir(src: string, dest: string, exclude: string[] = []): Promise<void> {
  await fs.mkdir(dest, { recursive: true });

  const entries = await fs.readdir(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    // Check if this entry should be excluded
    const shouldExclude = exclude.some(pattern => {
      if (pattern.includes('*')) {
        // Simple glob matching for patterns like *.log
        const regex = new RegExp('^' + pattern.replace(/\*/g, '.*') + '$');
        return regex.test(entry.name);
      }
      return entry.name === pattern;
    });

    if (shouldExclude) {
      continue;
    }

    if (entry.isDirectory()) {
      await copyDir(srcPath, destPath, exclude);
    } else {
      await fs.copyFile(srcPath, destPath);
    }
  }
}

/**
 * Recursively delete a directory or file
 */
async function deleteRecursive(targetPath: string): Promise<void> {
  try {
    const stat = await fs.stat(targetPath);
    if (stat.isDirectory()) {
      await fs.rm(targetPath, { recursive: true, force: true });
    } else {
      await fs.unlink(targetPath);
    }
  } catch (error: any) {
    if (error.code !== 'ENOENT') {
      throw error;
    }
    // File doesn't exist, that's fine
  }
}

/**
 * Apply modifications to the project directory
 */
async function applyModifications(dir: string, mods: Modification[]): Promise<void> {
  for (const mod of mods) {
    switch (mod.type) {
      case 'delete': {
        if (mod.pattern) {
          const targetPath = path.join(dir, mod.pattern);
          await deleteRecursive(targetPath);
          console.log(`  Deleted: ${mod.pattern}`);
        }
        break;
      }

      case 'replace': {
        if (mod.file && mod.find !== undefined && mod.replace !== undefined) {
          const filePath = path.join(dir, mod.file);
          try {
            let content = await fs.readFile(filePath, 'utf-8');
            if (content.includes(mod.find)) {
              content = content.replace(mod.find, mod.replace);
              await fs.writeFile(filePath, content, 'utf-8');
              console.log(`  Replaced in ${mod.file}: "${mod.find}" -> "${mod.replace}"`);
            } else {
              console.warn(`  Warning: Could not find "${mod.find}" in ${mod.file}`);
            }
          } catch (error: any) {
            console.error(`  Error modifying ${mod.file}: ${error.message}`);
          }
        }
        break;
      }

      case 'insert': {
        if (mod.file && mod.insertAfter !== undefined && mod.code !== undefined) {
          const filePath = path.join(dir, mod.file);
          try {
            let content = await fs.readFile(filePath, 'utf-8');
            if (content.includes(mod.insertAfter)) {
              content = content.replace(mod.insertAfter, mod.insertAfter + mod.code);
              await fs.writeFile(filePath, content, 'utf-8');
              console.log(`  Inserted code after "${mod.insertAfter.substring(0, 40)}..." in ${mod.file}`);
            } else {
              console.warn(`  Warning: Could not find insertion point "${mod.insertAfter}" in ${mod.file}`);
            }
          } catch (error: any) {
            console.error(`  Error inserting into ${mod.file}: ${error.message}`);
          }
        }
        break;
      }
    }
  }
}

/**
 * Generate a sample failure log for fix-mode evals
 */
function generateFailureLogContent(evalConfig: EvalConfig): string {
  const timestamp = new Date().toISOString();

  // Eval-specific failure logs for realistic error output
  const evalLogs: Record<string, string> = {
    'E36': `Running 13 tests using 2 workers

  ✘  1 tests/cart.spec.ts:25:3 › Shopping Cart Tests › Added items appear in cart (5.1s)
  ✘  2 tests/cart.spec.ts:35:3 › Shopping Cart Tests › Multiple items can be added to cart (4.8s)
  ✘  3 tests/cart.spec.ts:44:3 › Shopping Cart Tests › Items can be removed from cart (4.9s)

  1) tests/cart.spec.ts:25:3 › Shopping Cart Tests › Added items appear in cart

    Error: locator.click: Error: strict mode violation: locator('[data-test="add-cart-sauce-labs-backpack"]') resolved to 0 elements

        at InventoryPage.addProductToCart (pages/InventoryPage.ts:37:47)
        at tests/cart.spec.ts:26:31

      Waiting for locator('[data-test="add-cart-sauce-labs-backpack"]')

  2) tests/cart.spec.ts:35:3 › Shopping Cart Tests › Multiple items can be added to cart

    Error: locator.click: Error: strict mode violation: locator('[data-test="add-cart-sauce-labs-backpack"]') resolved to 0 elements

        at InventoryPage.addProductToCart (pages/InventoryPage.ts:37:47)
        at tests/cart.spec.ts:36:31

  3) tests/cart.spec.ts:44:3 › Shopping Cart Tests › Items can be removed from cart

    Error: locator.click: Error: strict mode violation: locator('[data-test="add-cart-sauce-labs-backpack"]') resolved to 0 elements

        at InventoryPage.addProductToCart (pages/InventoryPage.ts:37:47)
        at tests/cart.spec.ts:45:31

3 failed
  tests/cart.spec.ts:25:3 › Shopping Cart Tests › Added items appear in cart
  tests/cart.spec.ts:35:3 › Shopping Cart Tests › Multiple items can be added to cart
  tests/cart.spec.ts:44:3 › Shopping Cart Tests › Items can be removed from cart

Ran 13 tests, 3 failed (15.2s)`,

    'E37': `Running 7 tests using 1 worker

  ✘  1 tests/inventory.spec.ts:47:3 › Inventory/Product Tests › Product names match expected values (4.8s)
  ✘  2 tests/cart.spec.ts:25:3 › Shopping Cart Tests › Added items appear in cart (5.1s)

  1) tests/inventory.spec.ts:47:3 › Inventory/Product Tests › Product names match expected values

    Error: expect(received).toEqual(expected)

    Expected: [
      "Sauce Labs Backpack",
      "Sauce Labs Bike Light",
      "Sauce Labs Bolt T-Shirt",
      "Sauce Labs Fleece Jacket",
      "Sauce Labs Onesie",
      "Test.allTheThings() T-Shirt (Red)"
    ]
    Received: []

      57 |     const productNames = await inventoryPage.getProductNames();
    > 58 |     expect(productNames).toEqual(expectedProducts);
         |                          ^
      59 |   });

        at tests/inventory.spec.ts:58:26

  2) tests/cart.spec.ts:25:3 › Shopping Cart Tests › Added items appear in cart

    Error: expect(received).toContain(expected)

    Expected value: "Sauce Labs Backpack"
    Received array:  []

      31 |     const itemNames = await cartPage.getCartItemNames();
    > 32 |     expect(itemNames).toContain('Sauce Labs Backpack');
         |                       ^
      33 |   });

        at tests/cart.spec.ts:32:23

2 failed
  tests/inventory.spec.ts:47:3 › Inventory/Product Tests › Product names match expected values
  tests/cart.spec.ts:25:3 › Shopping Cart Tests › Added items appear in cart

Ran 7 tests, 2 failed (9.9s)`,

    'E38': `Running 13 tests using 2 workers

  ✘  1 tests/cart.spec.ts:94:3 › Shopping Cart Tests › Can navigate to checkout from cart (5.3s)

  1) tests/cart.spec.ts:94:3 › Shopping Cart Tests › Can navigate to checkout from cart

    Error: expect(page).toHaveURL(expected)

    Expected pattern: /checkout-step-one.html/
    Received string:  "https://www.saucedemo.com/inventory.html"

    Call log:
      - expect.toHaveURL with timeout 5000ms
      - waiting for locator('*')
      -   locator resolved to <html>…</html>
      -   unexpected value "https://www.saucedemo.com/inventory.html"

      97 |     await cartPage.goToCheckout();
    > 99 |     await expect(page).toHaveURL(/checkout-step-one.html/);
         |                        ^
     100 |   });

        at tests/cart.spec.ts:99:24

1 failed
  tests/cart.spec.ts:94:3 › Shopping Cart Tests › Can navigate to checkout from cart

Ran 13 tests, 1 failed (15.8s)`,

    'E39': `Running 7 tests using 1 worker

  ✘  1 tests/sorting.spec.ts:34:3 › Product Sorting Tests › Products can be sorted by price low to high (4.5s)
  ✘  2 tests/sorting.spec.ts:43:3 › Product Sorting Tests › Products can be sorted by price high to low (4.3s)

  1) tests/sorting.spec.ts:34:3 › Product Sorting Tests › Products can be sorted by price low to high

    Error: expect(received).toEqual(expected)

    Expected: [NaN, NaN, NaN, NaN, NaN, NaN]
    Received: [NaN, NaN, NaN, NaN, NaN, NaN]

    Note: Both expected and received are arrays of NaN. The getProductPrices() method is returning NaN for all prices.

      37 |     const prices = await inventoryPage.getProductPrices();
      38 |     const sortedPrices = [...prices].sort((a, b) => a - b);
    > 40 |     expect(prices).toEqual(sortedPrices);
         |                    ^
      41 |   });

        at tests/sorting.spec.ts:40:20

  2) tests/sorting.spec.ts:43:3 › Product Sorting Tests › Products can be sorted by price high to low

    Error: expect(received).toEqual(expected)

    Expected: [NaN, NaN, NaN, NaN, NaN, NaN]
    Received: [NaN, NaN, NaN, NaN, NaN, NaN]

      46 |     const prices = await inventoryPage.getProductPrices();
      47 |     const sortedPrices = [...prices].sort((a, b) => b - a);
    > 49 |     expect(prices).toEqual(sortedPrices);
         |                    ^
      50 |   });

        at tests/sorting.spec.ts:49:20

2 failed
  tests/sorting.spec.ts:34:3 › Product Sorting Tests › Products can be sorted by price low to high
  tests/sorting.spec.ts:43:3 › Product Sorting Tests › Products can be sorted by price high to low

Ran 7 tests, 2 failed (8.8s)`,

    'E40': `Running 5 tests using 1 worker

  ✘  1 tests/checkout.spec.ts:27:5 › Checkout Flow Tests › Checkout Information Step › Checkout requires first name (5.2s)
  ✘  2 tests/checkout.spec.ts:34:5 › Checkout Flow Tests › Checkout Information Step › Checkout requires last name (5.1s)
  ✘  3 tests/checkout.spec.ts:41:5 › Checkout Flow Tests › Checkout Information Step › Checkout requires postal code (5.0s)

  1) tests/checkout.spec.ts:27:5 › Checkout Flow Tests › Checkout Information Step › Checkout requires first name

    Error: expect(locator).toContainText(expected)

    Locator: locator('[data-test="error-message"]')
    Expected string: "First Name is required"
    Received: <element not found>

    Call log:
      - expect.toContainText with timeout 5000ms
      - waiting for locator('[data-test="error-message"]')
      -   locator resolved to 0 elements

      29 |       await checkoutPage.fillCheckoutForm('', 'Doe', '12345');
      30 |       await checkoutPage.continueCheckout();
    > 31 |       await checkoutPage.assertErrorMessage('First Name is required');
         |                          ^
      32 |     });

        at CheckoutPage.assertErrorMessage (pages/CheckoutPage.ts:41:38)
        at tests/checkout.spec.ts:31:30

  2) tests/checkout.spec.ts:34:5 › Checkout Flow Tests › Checkout Information Step › Checkout requires last name

    Error: expect(locator).toContainText(expected)

    Locator: locator('[data-test="error-message"]')
    Expected string: "Last Name is required"
    Received: <element not found>

        at CheckoutPage.assertErrorMessage (pages/CheckoutPage.ts:41:38)
        at tests/checkout.spec.ts:38:30

  3) tests/checkout.spec.ts:41:5 › Checkout Flow Tests › Checkout Information Step › Checkout requires postal code

    Error: expect(locator).toContainText(expected)

    Locator: locator('[data-test="error-message"]')
    Expected string: "Postal Code is required"
    Received: <element not found>

        at CheckoutPage.assertErrorMessage (pages/CheckoutPage.ts:41:38)
        at tests/checkout.spec.ts:45:30

3 failed
  tests/checkout.spec.ts:27:5 › Checkout requires first name
  tests/checkout.spec.ts:34:5 › Checkout requires last name
  tests/checkout.spec.ts:41:5 › Checkout requires postal code

Ran 5 tests, 3 failed (15.3s)`,

    'E41': `Running 6 tests using 1 worker

  ✘  1 tests/checkout.spec.ts:84:5 › Checkout Flow Tests › Checkout Overview Step › Overview calculates correct subtotal (5.4s)
  ✘  2 tests/checkout.spec.ts:94:5 › Checkout Flow Tests › Checkout Overview Step › Overview calculates total correctly (5.2s)

  1) tests/checkout.spec.ts:84:5 › Checkout Flow Tests › Checkout Overview Step › Overview calculates correct subtotal

    Error: expect(received).toBe(expected)

    Expected: 29.99
    Received: NaN

      85 |       const subtotal = await overviewPage.asyncGetSubtotal();
    > 86 |       expect(subtotal).toBe(29.99);
         |                        ^
      87 |     });

        at tests/checkout.spec.ts:86:24

  2) tests/checkout.spec.ts:94:5 › Checkout Flow Tests › Checkout Overview Step › Overview calculates total correctly

    Error: expect(received).toBeCloseTo(expected)

    Expected: ≈ 32.39 (2 digits)
    Received:   NaN

      95 |       const subtotal = await overviewPage.asyncGetSubtotal();
      96 |       const tax = await overviewPage.asyncGetTax();
      97 |       const total = await overviewPage.asyncGetTotal();
    > 99 |       expect(total).toBeCloseTo(subtotal + tax, 2);
         |                     ^
     100 |     });

        at tests/checkout.spec.ts:99:21

2 failed
  tests/checkout.spec.ts:84:5 › Overview calculates correct subtotal
  tests/checkout.spec.ts:94:5 › Overview calculates total correctly

Ran 6 tests, 2 failed (10.6s)`,

    'E42': `Running 0 tests using 0 workers

  Error: Cannot find module '../pages/ShoppingCartPage'

  Require stack:
  - tests/cart.spec.ts

    1 | import { test, expect } from '@playwright/test';
    2 | import { LoginPage } from '../pages/LoginPage';
    3 | import { InventoryPage } from '../pages/InventoryPage';
  > 4 | import { CartPage } from '../pages/ShoppingCartPage';
      |                          ^
    5 |

    at tests/cart.spec.ts:4:26

  Error: No tests found in tests/cart.spec.ts due to compilation error.

0 passed, 13 skipped (due to compilation error)
Ran 0 tests (2.1s)`,

    'E43': `Running 13 tests using 2 workers

  ✘  1 tests/cart.spec.ts:25:3 › Shopping Cart Tests › Added items appear in cart (5.0s)
  ✘  2 tests/cart.spec.ts:53:3 › Shopping Cart Tests › Cart shows correct item details (4.8s)

  1) tests/cart.spec.ts:25:3 › Shopping Cart Tests › Added items appear in cart

    Error: expect(received).toContain(expected)

    Expected value: "Sauce Labs Backpack"
    Received array:  ["  Sauce Labs Backpack"]

      31 |     const itemNames = await cartPage.getCartItemNames();
    > 32 |     expect(itemNames).toContain('Sauce Labs Backpack');
         |                       ^
      33 |   });

        at tests/cart.spec.ts:32:23

    Note: The returned item name has leading whitespace: "  Sauce Labs Backpack" vs expected "Sauce Labs Backpack"

  2) tests/cart.spec.ts:53:3 › Shopping Cart Tests › Cart shows correct item details

    Error: expect(locator).toContainText(expected)

    Locator: locator('.cart_item').first().locator('.inventory_item_name')
    Expected string: "Sauce Labs Backpack"
    Received string: "  Sauce Labs Backpack"

      59 |     await expect(cartItem.locator('.inventory_item_name')).toContainText('Sauce Labs Backpack');
         |                                                            ^

        at tests/cart.spec.ts:59:60

2 failed
  tests/cart.spec.ts:25:3 › Shopping Cart Tests › Added items appear in cart
  tests/cart.spec.ts:53:3 › Shopping Cart Tests › Cart shows correct item details

Ran 13 tests, 2 failed (14.8s)`,

    'E84': `Cypress Test Run - ${timestamp}
================================================================================

  (Run Starting)

  cypress/e2e/auth.cy.ts

  1) @auth Authentication Tests
       @smoke @test_type:regression Valid user can login successfully:
     AssertionError: Timed out retrying after 4000ms: Expected to find element: \`[data-test="login-btn"]\`, but never found it.

      at LoginPage.login (cypress/pages/LoginPage.ts:15:8)
      at Context.eval (cypress/e2e/auth.cy.ts:13:15)

  1 failing

  1) @auth Authentication Tests
       @smoke @test_type:regression Valid user can login successfully

1 failed (8.2s)`,

    'E85': `WebdriverIO Test Run - ${timestamp}
================================================================================

Execution of 1 spec files started

[chrome #0-0] Running: auth.spec.ts
[chrome #0-0] Authentication Tests
[chrome #0-0]    ✖ Valid user can login successfully

[chrome #0-0] 1 failing (6.1s)

[chrome #0-0] 1) Authentication Tests Valid user can login successfully
[chrome #0-0] Can't call setValue on element with selector "[data-test="user-name"]" because element wasn't found`,

    'E89': `Running 13 tests using 2 workers

  ✘  1 tests/auth.spec.ts:15:3 › Authentication Tests › Valid user can login successfully (9.2s)

  1) tests/auth.spec.ts:15:3 › Authentication Tests › Valid user can login successfully

    Error: locator.click: Error: strict mode violation: getByTestId('login-btn') resolved to 0 elements

        at LoginPage.login (pages/LoginPage.ts:24:47)
        at tests/auth.spec.ts:17:21

  Note: test also contains await page.waitForTimeout(5000) — flaky timing workaround

1 failed (12.1s)`,

    'E93': `Cypress Test Run - ${timestamp}
================================================================================

  cypress/e2e/cart.cy.ts

  1) Cart Tests
       should proceed to checkout:
     AssertionError: Timed out retrying after 4000ms: Expected to find element: \`[data-test="checkout-btn"]\`, but never found it.

      at CartPage.goToCheckout (cypress/pages/CartPage.ts:40:8)

  1 failing (7.4s)`,

    'E95': `Running 13 tests using 2 workers

  ✘  1 tests/auth.spec.ts:15:3 › Authentication Tests › Valid user can login successfully (3.1s)

  1) tests/auth.spec.ts:15:3 › Authentication Tests › Valid user can login successfully

    Error: page.goto: net::ERR_NAME_NOT_RESOLVED at https://www.saucedemo.com.invalid/
        at LoginPage.goto (pages/LoginPage.ts:18:21)

  baseURL in playwright.config.ts is set to https://www.saucedemo.com.invalid

1 failed (4.2s)`,

    'E97': `Running 13 tests using 2 workers

  ✘  1 tests/cart.spec.ts:25:3 › Shopping Cart Tests › Added items appear in cart (5.1s)

  1) tests/cart.spec.ts:25:3 › Shopping Cart Tests › Added items appear in cart

    Error: locator.click: getByTestId('add-cart-sauce-labs-backpack') resolved to 0 elements

        at InventoryPage.addProductToCart (pages/InventoryPage.ts:37:47)

  Note: assertCartItemCount(1) is commented out in test — assertion weakening detected

1 failed (8.5s)`,
  };

  // Check for eval-specific log first
  if (evalLogs[evalConfig.id]) {
    return `Playwright Test Run - ${timestamp}
================================================================================

${evalLogs[evalConfig.id]}
`;
  }

  // Fallback: generate based on modification patterns
  let errorDetails = '';

  for (const mod of evalConfig.modifications) {
    if (mod.type === 'replace' && mod.file && mod.replace) {
      if (mod.replace.includes('wrong-selector') || mod.replace.includes('user-name')) {
        errorDetails += `
Error: locator.fill: Error: strict mode violation: locator('[data-test="${mod.replace.match(/\[data-test="([^"]+)"\]/)?.[1] || 'wrong-selector'}"]') resolved to 0 elements

    at LoginPage.login (pages/LoginPage.ts:23:29)
    at tests/auth.spec.ts:16:21

  Waiting for locator('[data-test="${mod.replace.match(/\[data-test="([^"]+)"\]/)?.[1] || 'wrong-selector'}"]')
`;
      } else if (mod.replace.includes('wrong-checkout')) {
        errorDetails += `
Error: locator.click: Error: strict mode violation: locator('[data-test="wrong-checkout"]') resolved to 0 elements

    at CartPage.goToCheckout (pages/CartPage.ts:42:29)
    at tests/cart.spec.ts:97:21

  Waiting for locator('[data-test="wrong-checkout"]')
`;
      } else if (mod.replace.includes('Order Confirmed')) {
        errorDetails += `
Error: expect(locator).toHaveText(expected)

Locator: locator('[data-test="complete-header"]')
Expected string: "Order Confirmed!"
Received string: "Thank you for your order!"

    at tests/checkout.spec.ts:122:45
`;
      }
    } else if (mod.type === 'insert' && mod.code?.includes('timing bug')) {
      errorDetails += `
Error: locator.click: Error: strict mode violation: locator('.inventory_item:first-child .btn_inventory') resolved to 0 elements

    at tests/cart.spec.ts:17:16

  This likely occurred because the page was not fully loaded when the click was attempted.
  Consider waiting for the element to be visible or for the page to finish loading.
`;
    }
  }

  if (!errorDetails) {
    errorDetails = `
Error: Test failed with unexpected error

    at tests/example.spec.ts:10:5
`;
  }

  return `Playwright Test Run - ${timestamp}
================================================================================

Running tests...

  1 failed

  1) [chromium] > tests/auth.spec.ts:15:3 > Authentication Tests > Valid user can login successfully
${errorDetails}

  Slow test file: tests/auth.spec.ts (10.2s)

  1 failed
  Finished in 10.5s
`;
}

/**
 * Generate a single fixture
 */
async function generateFixture(evalConfig: EvalConfig): Promise<void> {
  const baseDir = path.join(__dirname, '..');
  const templateDir = path.join(baseDir, 'base-templates', evalConfig.baseTemplate);
  const fixtureDir = path.join(baseDir, 'fixtures', evalConfig.id);
  const projectDir = path.join(fixtureDir, 'project');

  console.log(`\nGenerating fixture for ${evalConfig.id}: ${evalConfig.name}`);

  // 1. Remove existing fixture directory if it exists
  await deleteRecursive(fixtureDir);

  // 2. Create fixture directory
  await fs.mkdir(fixtureDir, { recursive: true });

  // 3. Copy base template (excluding node_modules and .git)
  console.log(`  Copying template: ${evalConfig.baseTemplate}`);
  await copyDir(templateDir, projectDir, ['node_modules', '.git', 'test-results', 'playwright-report']);

  // 4. Apply modifications
  if (evalConfig.modifications.length > 0) {
    console.log('  Applying modifications...');
    await applyModifications(projectDir, evalConfig.modifications);
  }

  // 5. Write failure.log if needed
  if (evalConfig.needsFailureLog) {
    const failureLogContent = generateFailureLogContent(evalConfig);
    await fs.writeFile(path.join(fixtureDir, 'failure.log'), failureLogContent, 'utf-8');
    console.log('  Created failure.log');
  }

  // 6. Write fixture.json metadata
  const fixtureMetadata = {
    evalId: evalConfig.id,
    name: evalConfig.name,
    mode: evalConfig.mode,
    task: evalConfig.task,
    logsFile: evalConfig.needsFailureLog ? 'failure.log' : null,
    passCriteria: evalConfig.passCriteria,
    failCriteria: evalConfig.failCriteria,
    tier: evalConfig.tier,
    baseTemplate: evalConfig.baseTemplate,
    modifications: evalConfig.modifications.map(m => ({
      type: m.type,
      ...(m.file && { file: m.file }),
      ...(m.pattern && { pattern: m.pattern }),
      ...(m.find && { find: m.find }),
      ...(m.replace && { replace: m.replace }),
      ...(m.insertAfter && { insertAfter: m.insertAfter.substring(0, 50) + '...' }),
      ...(m.code && { codeInserted: true })
    })),
    generatedAt: new Date().toISOString()
  };

  await fs.writeFile(
    path.join(fixtureDir, 'fixture.json'),
    JSON.stringify(fixtureMetadata, null, 2),
    'utf-8'
  );

  console.log(`  Created fixture.json`);
}

/**
 * Main entry point
 */
async function main(): Promise<void> {
  const targetIds = process.argv.slice(2).filter((arg) => /^E\d+$/.test(arg));
  const evalsToGenerate =
    targetIds.length > 0
      ? EVALS.filter((evalConfig) => targetIds.includes(evalConfig.id))
      : EVALS;

  if (evalsToGenerate.length === 0) {
    console.error('No matching eval IDs found.');
    console.error('Usage: tsx generate-fixtures.ts [E84 E85 ...]');
    process.exit(1);
  }

  console.log('='.repeat(60));
  console.log('Agent Eval Fixture Generator');
  console.log('='.repeat(60));
  console.log(`\nGenerating ${evalsToGenerate.length} fixtures...`);

  const startTime = Date.now();

  for (const evalConfig of evalsToGenerate) {
    await generateFixture(evalConfig);
  }

  const duration = ((Date.now() - startTime) / 1000).toFixed(2);

  console.log('\n' + '='.repeat(60));
  console.log(`Successfully generated ${evalsToGenerate.length} fixtures in ${duration}s`);
  console.log('='.repeat(60));

  // Print summary by tier
  console.log('\nFixtures by tier:');
  const tiers = new Map<number, string[]>();
  for (const evalConfig of evalsToGenerate) {
    if (!tiers.has(evalConfig.tier)) {
      tiers.set(evalConfig.tier, []);
    }
    tiers.get(evalConfig.tier)!.push(evalConfig.id);
  }

  for (const [tier, ids] of Array.from(tiers.entries()).sort((a, b) => a[0] - b[0])) {
    console.log(`  Tier ${tier}: ${ids.join(', ')}`);
  }

  // Print summary by mode
  console.log('\nFixtures by mode:');
  const modes = new Map<string, string[]>();
  for (const evalConfig of evalsToGenerate) {
    if (!modes.has(evalConfig.mode)) {
      modes.set(evalConfig.mode, []);
    }
    modes.get(evalConfig.mode)!.push(evalConfig.id);
  }

  for (const [mode, ids] of modes.entries()) {
    console.log(`  ${mode}: ${ids.join(', ')} (${ids.length} total)`);
  }
}

main().catch((error) => {
  console.error('Error generating fixtures:', error);
  process.exit(1);
});
