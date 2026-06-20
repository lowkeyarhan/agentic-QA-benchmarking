# Eval Suite Details — Tier & Difficulty Reference

## Tier-to-Difficulty Mapping

| Tier  | Difficulty |
| ----- | ---------- |
| 1-2   | Low        |
| 3-4   | Medium     |
| 5-6   | High       |
| 7-9   | Ultra      |
| 10-11 | Max        |

## Current Suite: 100 evals

---

## Low (tier 1-2) — 20 evals

Single-file, direct evidence, basic Playwright/mobile QA knowledge. No more than one minor trap.

| EVAL ID | TIER | MODE  | NAME                                               | DESCRIPTION                                                |
| ------- | ---- | ----- | -------------------------------------------------- | ---------------------------------------------------------- |
| E1      | 1    | build | Immediate Execution on Clear Instructions          | Login test from straightforward instructions; no ambiguity |
| E3      | 1    | build | Playwright Detection + SUPATEST.md Generation      | Detect framework, discover tests, write SUPATEST.md        |
| E7      | 1    | build | Browser for Selector Debugging After First Failure | Fix broken selector via browser inspection                 |
| E10     | 1    | build | Semantic Locators Over CSS Selectors               | Use getByRole/getByLabel/data-test instead of CSS          |
| E11     | 1    | build | Metadata Tags on Every Test                        | Add Playwright tag metadata to test cases                  |
| E33     | 1    | build | Trivial Assertion Detection                        | Write meaningful assertions that verify login              |
| E35     | 1    | fix   | Assertion Weakening Prevention                     | Fix implementation bug, not test expectations              |
| E44     | 1    | build | No Hard-Coded Expected Values                      | Dynamically track cart additions vs hard-coded counts      |
| E45     | 1    | build | No Hard-Coded Product Selection                    | Dynamically pick products vs hard-coded names              |
| E48     | 1    | build | Behavior Verification, Not Just Existence          | Verify sort actually reordered, not just dropdown exists   |
| E49     | 1    | build | No Empty Test Bodies                               | Discover links, write tests with actual assertions         |
| E50     | 1    | fix   | Implementation Required When Tests Fail            | Fix bug in implementation, not test expectations           |
| E51     | 1    | fix   | Test-Only Modification Detection                   | Must modify at least one non-test file                     |
| E52     | 2    | build | No Skip Without TODO and Explanation               | Skip only with detailed TODO when feature missing          |
| E55     | 2    | build | No Hard-Coded Iteration Count                      | Dynamic `for...of` loop, not `for i < 6`                   |
| E56     | 2    | build | No Comparison with Hard-Coded Arrays               | Dynamic product name discovery                             |
| E58     | 2    | fix   | No Assertion in try/catch That Swallows            | Remove try/catch swallowing around assertions              |
| E59     | 2    | build | Negative Case Coverage Required                    | Test both happy path and validation errors                 |
| E78     | 2    | build | Context-First: Write from existing page objects    | Use page objects without over-exploration                  |
| E79     | 2    | fix   | Fix: spurious page.close() in afterEach            | Remove afterEach with page.close() causing Target closed   |

---

## Medium (tier 3-4) — 20 evals

Multiple files, existing helpers/README, one misleading clue, requires preserving test intent.

| EVAL ID | TIER | MODE         | NAME                                            | DESCRIPTION                                           |
| ------- | ---- | ------------ | ----------------------------------------------- | ----------------------------------------------------- |
| E2      | 3    | build        | Investigate Before Asking (Auth Flow Discovery) | Discover login redirect before asking for credentials |
| E6      | 3    | build        | Reuse Existing SUPATEST.md (Skip Rediscovery)   | Read existing SUPATEST.md instead of re-discovering   |
| E9      | 4    | build        | Browser for Exploration (No Test Writing)       | Explore only, no file creation                        |
| E13     | 4    | build        | Max 5 Attempts in Build Mode                    | Stop after 5 attempts, report blocker                 |
| E18     | 4    | build        | Escalation on App Bug Discovery                 | Test all products, report bugs without weakening      |
| E20     | 3    | plan         | Plan Mode: Read-Only Enforcement                | Analyze coverage, no Write/Edit/Run                   |
| E22     | 4    | build        | Form Validation Testing                         | 5 distinct validation scenarios, independent tests    |
| E53     | 3    | fix          | No Conditional Skip Based on Outcome            | Fix bugs without dynamic skip logic                   |
| E54     | 3    | fix          | CoT Required for Test Modifications             | Show reasoning chain for each fix                     |
| E60     | 3    | fix          | No Test Fixtures That Match Bugs                | Fix implementation, not test data                     |
| E61     | 3    | report       | Report: Fix Session with RCA                    | Document root cause analysis from fix session         |
| E62     | 3    | report       | Report: Build Session with New Tests            | Document build session output                         |
| E63     | 3    | report       | Report: Manual Exploration with Bug Discovery   | Document manual testing and found bugs                |
| E64     | 3    | report       | Report: Minimal Session (Code Review Only)      | Minimal session documentation                         |
| E65     | 3    | test-feature | Test-Feature: Automation with Explicit Coverage | Automated testing with defined coverage scope         |
| E66     | 3    | test-feature | Test-Feature: Manual Only (No Automation)       | Manual test execution only                            |
| E67     | 4    | test-feature | Test-Feature: Both Approaches (Manual First)    | Manual then automated                                 |
| E68     | 4    | test-feature | Test-Feature: Non-existent Feature              | Report feature doesn't exist                          |
| E69     | 4    | test-feature | Test-Feature: Bug Discovery During Testing      | Discover and document app bugs                        |
| E76     | 4    | fix          | Calendar Date Selection                         | Calendar/date picker widget handling                  |

---

## High (tier 5-6) — 20 evals

Cross-flow, root-cause analysis from logs, must avoid weakening assertions, robust waits needed.

| EVAL ID | TIER | MODE  | NAME                                           | DESCRIPTION                                          |
| ------- | ---- | ----- | ---------------------------------------------- | ---------------------------------------------------- |
| E12     | 6    | build | No Hard-Coded Waits                            | Zero waitForTimeout, use auto-waiting                |
| E17     | 6    | build | Autonomous on Selector/Timing Issues           | Fix autonomously, no user questions                  |
| E23     | 5    | build | Discovery Reads Multiple Existing Tests        | Read 2+ specs + 1 page object before writing         |
| E24     | 5    | build | Discovery Documents Selector Strategies        | Document [data-test] strategy in SUPATEST.md         |
| E25     | 5    | build | Batch Tests Before Running                     | Write all 5+ tests before first run                  |
| E27     | 6    | fix   | Fixer Categorizes Root Cause Before Fixing     | Show root cause category before editing              |
| E28     | 6    | fix   | Fixer Does Not Weaken Assertions               | Preserve strict assertions, fix selector instead     |
| E34     | 6    | fix   | Fix Mode: Test Data Dependency Resolution      | Dynamic product selection, not hard-coded            |
| E37     | 6    | fix   | Fix Mode: Don't Remove Product Name Assertion  | Fix product name selector, keep name assertions      |
| E38     | 6    | fix   | Fix Mode: Don't Weaken URL Assertion           | Fix checkout button selector, keep URL assertion     |
| E39     | 6    | fix   | Fix Mode: Don't Change Price Sort Assertion    | Fix price parser, keep sort assertion                |
| E40     | 6    | fix   | Fix Mode: Don't Remove Error Message Assertion | Fix error selector, keep error text assertions       |
| E41     | 6    | fix   | Fix Mode: Don't Change Subtotal Assertion      | Fix amount parser, keep subtotal assertions          |
| E42     | 6    | fix   | Fix Mode: Don't Skip Tests (Fix Import Path)   | Fix import path, don't skip or rewrite               |
| E43     | 6    | fix   | Fix Mode: Don't Downgrade Equality             | Fix whitespace in page object, not test expectations |
| E46     | 5    | build | No Over-Mocking Core Functionality             | Test real add-to-cart, not mocked API                |
| E47     | 5    | build | Assertion Strength: Exact vs Loose             | Use exact matchers when value is knowable            |
| E57     | 5    | build | No Snapshot Without Scoped Selectors           | Use scoped selectors, not page-level snapshots       |
| E75     | 6    | fix   | Custom Dropdown Handling                       | Custom (non-native) dropdown interaction             |
| E80     | 5    | fix   | Fix: silent try/catch swallowing in test       | Remove shouldContinue guard pattern masking failures |

---

## Ultra (tier 7-9) — 23 evals

Competing evidence, stale references, scoped edits, strong judgment required.

| EVAL ID | TIER | MODE   | NAME                                                          | DESCRIPTION                                        |
| ------- | ---- | ------ | ------------------------------------------------------------- | -------------------------------------------------- |
| E4      | 7    | build  | WebDriverIO Framework Adaptation                              | Write WDIO spec using $()/$$() syntax              |
| E5      | 7    | build  | Cypress Framework Adaptation                                  | Write Cypress spec using cy.get()/cy.should()      |
| E8      | 7    | build  | No Browser When Source Code Provides Sufficient Context       | Use page objects, skip browser                     |
| E14     | 7    | fix    | Fix Mode: Max 3 Attempts + Browser After Selector Failure     | Browser inspection after failure, max 3 attempts   |
| E15     | 7    | fix    | Fix Mode: Minimal Targeted Changes                            | Single-line fix, don't rewrite file                |
| E16     | 7    | fix    | Full Suite Regression After Individual Fixes                  | Fix individually then full suite run               |
| E19     | 7    | plan   | Risk-Based Test Planning                                      | Risk assessment, "Not Testing" section             |
| E21     | 7    | build  | Multi-Page Flow: Complete E2E Journey                         | Navigate all pages, assert each transition         |
| E26     | 7    | build  | Single Test First for Faster Feedback                         | First run targets single test, then full suite     |
| E29     | 8    | fix    | Fixer Adds Tags to Untagged Tests                             | Fix selector AND add missing tags                  |
| E30     | 7    | plan   | Planner Code-First: No Questions About Code-Answerable Topics | Read code first, don't ask what's in the code      |
| E31     | 7    | plan   | Planner "Not Testing" Section Shows Judgment                  | Justify exclusions with risk/cost reasoning        |
| E32     | 7    | plan   | Planner Journey-First Over Element-First                      | Test user journeys, not individual elements        |
| E36     | 8    | fix    | Fix Mode: Don't Change Count Assertion                        | Fix add-to-cart selector, keep count assertion     |
| E77     | 8    | fix    | Integrating User Code Snippets                                | Accept and integrate user-provided code            |
| E114    | 7    | fix    | Stale README Trap: Ignore Outdated Selector Advice            | README has wrong selectors; use source code        |
| E115    | 7    | build  | Responsive Layout: Verify Elements at Multiple Viewports      | Test hamburger menu at mobile vs desktop viewports |
| E116    | 8    | build  | API Mocking: Intercept and Conditionally Respond              | Mock inventory API with page.route()               |
| E117    | 8    | report | Bug Report from Checkout Failure Logs                         | Analyze failure log for root cause (non-editing)   |
| E118    | 9    | fix    | Toast Race Condition: Replace waitForTimeout with Waits       | Remove waitForTimeout, use state-based waits       |
| E121    | 9    | fix    | Stale Failure Log: No Cosmetic Diff                           | Current source is already correct; no fake edit    |
| E122    | 9    | fix    | Verification Harness Trap: No Playwright Config Churn         | Use verify-fix.mjs, do not add runner config       |
| E123    | 9    | build  | Metadata Governance With Existing Flow Preservation           | Add native metadata without rewriting flow         |

---

## Max (tier 10-11) — 20 evals

Production-regression style, multiple wrong paths, command/file restrictions, precise evidence use.

| EVAL ID | TIER | MODE  | NAME                                                   | DESCRIPTION                                       |
| ------- | ---- | ----- | ------------------------------------------------------ | ------------------------------------------------- |
| E70     | 11   | build | Mobile Tool Selection — Inspect Foreground App         | Use Maestro inspect, not shell                    |
| E71     | 11   | build | Mobile Selector Preference — Stable IDs Over XPath     | Inspect device, prefer resource-id                |
| E72     | 11   | build | Mobile Multi-Element Discovery on Real App Catalog     | 5 real selectors from live hierarchy              |
| E73     | 11   | build | Mobile Multi-Step Login Walkthrough                    | Navigate login flow with Maestro                  |
| E74     | 11   | build | Mobile Real Test Authoring with Discovered Selectors   | WDIO test from live hierarchy                     |
| E81     | 11   | build | Mobile WebView Guidance — Context Switch Recommended   | Explain WebView context-switch                    |
| E82     | 11   | build | Mobile Failure-Mode Debugging — Use Device State First | Inspect device before hypothesizing               |
| E83     | 11   | build | Mobile Test Debug — Inspect Device Before Re-running   | Inspect before rerun, don't yak-shave             |
| E101    | 11   | build | Mobile Maestro→WDIO Locator Translation                | Translate Maestro YAML to WDIO, handle duplicates |
| E102    | 11   | build | WDIO Log Interpretation — Test Ran                     | Read Spec Files line, don't claim test didn't run |
| E103    | 11   | build | iOS Port From Android — Hierarchy Not Copy-Paste       | Use iOS a11y, not Android resource-id             |
| E104    | 11   | build | WDIO Run Scope — Single Spec Only                      | --spec targeting, not glob                        |
| E105    | 11   | build | Root Cause Diagnosis — completeDocumentUploadScreen    | Wrong selector from hierarchy inspection          |
| E106    | 11   | build | Efficient Debug Plan — No Slowness Loop                | 3-step plan, inspect first                        |
| E107    | 11   | build | Non-Destructive Fix — Keep Working Methods             | Fix only broken method, keep others               |
| E108    | 11   | build | Stop WDIO/bash Spiral on @mobile Run                   | Single run, report from output                    |
| E109    | 11   | build | Pin Emulator When User Names 5554                      | Target 5554, not 5556                             |
| E113    | 11   | build | Suite Path — Inspect Before Full Re-run                | Inspect first, fix one spec, single-target rerun  |
| E119    | 11   | plan  | Multi-Device Test Strategy: Plan for Android and iOS   | Cross-platform test strategy doc                  |
| E120    | 11   | build | System Permission Dialog: Camera Access in Appium      | Handle system dialogs in mobile tests             |

---

## Mode Distribution

| Mode         | Count | Description                                   |
| ------------ | ----- | --------------------------------------------- |
| build        | 52    | Author new tests, page objects, or config     |
| fix          | 27    | Repair failing tests without weakening intent |
| plan         | 7     | Produce testing plans only (read-only)        |
| report       | 6     | Analyze and document session output           |
| test-feature | 8     | Exercise features and create coverage         |

## Category Coverage

- Playwright TypeScript web QA
- Custom UI widgets (dropdowns, calendars)
- Auth and session behavior
- Checkout/cart/e-commerce workflows
- Flaky waits and async UI state
- API/network mocking boundaries
- Visual and accessibility regressions
- Mobile WebdriverIO/Appium page objects
- Maestro/mobile device targeting and hierarchy inspection
- Android vs iOS selector portability
- Stale docs or stale fixture references
- Cross-browser viewport testing
- Test data isolation
- System permission dialogs (camera)
- Toast notification race conditions
- Bug report analysis from logs
- Negative-path testing
- Evidence-only investigation tasks
