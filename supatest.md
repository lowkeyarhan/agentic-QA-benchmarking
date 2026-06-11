# Supatest Agent

Supatest is a QA-focused E2E testing agent. Its job is not just to edit code: it is designed to build, debug, and fix browser/mobile test suites using test evidence, project conventions, runtime state, and narrow verification loops.

## What Supatest Does

- Creates E2E tests from user journeys, product requirements, and existing project patterns.
- Debugs failing tests by reading logs, traces, screenshots, browser or device state, app code, fixtures, and page objects.
- Fixes tests with minimal targeted changes while preserving the intent of the original assertion.
- Plans coverage like a senior QA engineer, prioritizing business risk and important user flows over raw code coverage.
- Runs in CLI/headless workflows for local development and CI, including log-driven fixing.
- Adapts to the test framework already present in the repo instead of forcing a new framework.

## Why It Is QA-Focused

Supatest is prompted around a QA workflow rather than a general coding workflow. Its core loop is to classify the task, identify the source of truth, make the smallest useful change, observe the result, and verify with the narrowest relevant test command.

Important QA-specific behaviors include:

- Treating `SUPATEST.md`, existing tests, fixtures, page objects, app source, logs, screenshots, traces, and browser/device snapshots as evidence.
- Reading existing tests before creating new ones so selectors, assertions, naming, and structure match the project.
- Preferring stable selectors such as test ids, accessibility labels, resource ids, and existing page-object helpers.
- Avoiding fabricated selectors and avoiding repeated blind reruns when runtime inspection is needed.
- Preserving test integrity by not weakening assertions, skipping tests, hiding product bugs, or changing expected behavior just to make a test pass.
- Escalating likely application bugs instead of silently converting them into test changes.
- Handling dynamic data by creating or isolating test data instead of relying on brittle seeded state.
- Supporting browser and mobile test debugging, including DOM/device hierarchy inspection before selector fixes.

## Difference From General Agents

General coding agents are optimized for broad software tasks: editing files, implementing features, refactoring, or answering questions. They may solve a failing test by changing application code, changing test code, or stopping after a plausible patch.

Supatest is narrower by design. It treats tests as the primary artifact, keeps the user journey and assertion intent central, and uses QA evidence before editing. For benchmark tasks, this means Supatest should have an advantage when the task requires creating meaningful E2E coverage, fixing flaky or broken tests, preserving assertions, diagnosing selector/runtime failures, and proving the result with a targeted test run.

## Local Sources Inspected

- `/Users/lowkeyarhan/Documents/supatest/README.md`
- `/Users/lowkeyarhan/Documents/supatest/cli/README.md`
- `/Users/lowkeyarhan/Documents/supatest/cli/src/prompts/agents/base-agent.ts`
- `/Users/lowkeyarhan/Documents/supatest/cli/src/prompts/agents/planner.ts`
- `/Users/lowkeyarhan/Documents/supatest/cli/src/prompts/blocks/mobile.ts`

Goal:
Transform the existing Supatest benchmark eval suite into a much more realistic, complex, and
varied real-world QA testing benchmark with exactly 100 eval fixtures.

Important repo context:

- Follow AGENTS.md and /Users/lowkeyarhan/.codex/RTK.md.
- Prefix shell commands with `rtk`.
- Fixture root: `agent-eval-fixtures/fixtures/`
- Each eval lives at `agent-eval-fixtures/fixtures/<EVAL_ID>/`
- Each eval must contain a valid `fixture.json`.
- The harness copies only `<eval>/project/` into benchmark runs.
- Host-side answer keys, failure logs, stale references, and evaluator-only notes can live
  outside `project/`, but the agent only sees `project/` plus injected failure logs.
- Scoring uses `task`, `passCriteria`, `failCriteria`, changed files, diffs, and transcript
  evidence. Therefore every eval must be concretely judgeable.

Primary objective:
Create or modify the fixture suite so there are exactly 100 high-quality evals covering realistic
QA work across web, mobile, API, accessibility, visual, flaky test debugging, CI/test
infrastructure, selector repair, regression analysis, test planning, and evidence-based
reporting.

Difficulty distribution:

- 20 Low
- 20 Medium
- 20 High
- 20 Ultra
- 20 Max

Map these to fixture `tier` values:

- Low: tier 1-2
- Medium: tier 3-4
- High: tier 5-6
- Ultra: tier 7-9
- Max: tier 10-11

Do not make every eval hard in the same way. Difficulty should vary by:

- number of files involved
- ambiguity of the evidence
- presence of stale or misleading references
- selector complexity
- requirement to preserve existing assertions
- need to infer root cause from logs
- mobile/web/device constraints
- command restrictions
- cross-browser or cross-platform behavior
- risk of over-fixing, weakening tests, or changing production code incorrectly

Required eval types:
Include a broad mix of modes:

- `build`: author new tests or page objects
- `fix`: repair failing tests without weakening intent
- `plan`: produce a careful testing or device plan only
- `report`: analyze logs/artifacts and report root cause
- `test-feature`: exercise a feature and create useful test coverage

Include these categories across the 100 evals:

- Playwright TypeScript web QA
- custom UI widgets: dropdowns, calendars, virtualized lists, modals, drag/drop
- auth and session behavior
- checkout/cart/e-commerce workflows
- flaky waits and async UI state
- API/network mocking boundaries
- visual and accessibility regressions
- mobile WebdriverIO/Appium page objects
- Maestro/mobile device targeting and hierarchy inspection
- Android vs iOS selector portability
- stale docs or stale fixture references
- CI-only failures
- browser-specific bugs
- test data isolation
- localization/timezone/currency issues
- permission, camera, file upload, and deep-link flows
- negative-path testing
- evidence-only investigation tasks where editing is forbidden

Quality bar for every eval:
Each eval must feel like a real QA task a production team would hand to an agent. Avoid toy tasks
unless they are intentionally Low difficulty.

For every fixture:

1. `fixture.json` must be valid JSON.
2. `evalId` must match the directory name.
3. `name` must be specific and descriptive.
4. `mode` must be one of the harness-supported modes.
5. `task` must be clear enough for an agent but may include realistic ambiguity.
6. `passCriteria` must be concrete, observable, and judgeable from changed files, diffs,
   transcript, or logs.
7. `failCriteria` must catch common bad agent behavior.
8. `project/` must be self-contained and runnable or inspectable.
9. If `logsFile` is set, that log must exist.
10. If the task says “authoring only” or “do not run commands,” the pass/fail criteria must
    enforce that.
11. Do not depend on live external services, internet access, or credentials.
12. Do not create evals where the correct solution is to delete assertions, skip tests, use
    `expect(true)`, or broadly mock away the behavior under test.

Make evals harder by adding realistic traps, not by making them impossible:

- stale reference files that should not be trusted
- misleading failure logs with one useful line hidden inside noise
- old selectors that almost match but are wrong
- mobile hierarchies where Android and iOS differ
- flaky timeout symptoms whose root cause is missing state synchronization
- tests that pass locally but fail under a specific browser/project
- README advice that is outdated and must be ignored
- multiple similar devices where the user named one exact target
- forbidden broad selectors or fragile XPath
- existing helper abstractions that should be reused, not bypassed
- generated artifacts that should not be edited
- command-order requirements, such as write all tests before first run

Difficulty definitions:
Low:

- One primary file.
- Direct evidence.
- No more than one minor trap.
- Should be solvable with basic Playwright/mobile QA knowledge.
- Example: fix a locator after reading a simple failure log.

Medium:

- Two to three files.
- Requires reading existing helpers or README.
- Has one misleading clue.
- Requires preserving test intent.
- Example: repair a custom dropdown test without using native `selectOption`.

High:

- Multiple files or cross-flow behavior.
- Requires root-cause analysis from logs or app behavior.
- Must avoid weakening assertions.
- May require adding robust waits, fixtures, or page object updates.
- Example: checkout failure caused by async cart update and stale page object method.

Ultra:

- Several competing sources of evidence.
- Stale docs/references are present.
- Requires scoped edits and strong judgment.
- May involve web plus API mocking, mobile selectors, or CI-specific constraints.
- Example: port Android page object to iOS using current hierarchy while ignoring stale selector
  notes.

Max:

- Production-regression style.
- Multiple plausible wrong paths.
- Strong command/file restrictions.
- Requires precise evidence use and minimal, maintainable edits.
- Often plan/report/mobile/device-specific.
- Example: user names emulator-5554; eval includes emulator-5556 trap and stale device notes.

Implementation instructions:

1. Inspect the current fixture suite before editing.
2. Count current evals and identify gaps in difficulty, category, and mode coverage.
3. Decide whether to upgrade existing evals, add new evals, or both.
4. Ensure the final suite has exactly 100 evals.
5. Prefer reusing existing base templates when appropriate:
   - `playwright-ts-full`
   - mobile stubs
   - android/iOS port stubs
   - device-plan stubs
6. Add new fixture projects only when they materially improve benchmark coverage.
7. Keep each fixture compact enough for agents to inspect within benchmark timeouts.
8. Avoid huge generated files unless the eval specifically tests large-log triage.
9. Keep answer-key or evaluator-only files outside `project/`.
10. Preserve harness compatibility.

Pass/fail criteria style:
Good pass criteria examples:

- “Uses the current iOS accessibility selector from `references/ios-login-inspect-snippet.json`.”
- “Preserves the existing checkout total assertion.”
- “First test run occurs only after all requested test cases are authored.”
- “Targets `emulator-5554`, not `emulator-5556`.”
- “Does not modify production source files.”
- “Uses a web-first assertion for visible toast state instead of fixed timeout.”

Bad pass criteria examples:

- “Does a good job.”
- “Improves the tests.”
- “Handles edge cases.”
- “Makes it better.”
- “Uses best practices.”

Common fail criteria to include where relevant:

- Deletes or weakens meaningful assertions.
- Adds `test.skip`, `test.only`, or `expect(true)`.
- Uses fixed sleeps instead of state-based waits.
- Invents selectors not present in evidence.
- Uses stale references when current evidence exists.
- Modifies forbidden files.
- Runs commands when task says authoring-only.
- Creates unrelated files.
- Over-mocks the feature under test.
- Changes production code when only tests/page objects should change.
- Claims success without running or inspecting when verification was required.

Verification requirements:
After editing the suite:

1. Run a fixture count and confirm exactly 100 evals.
2. Validate every `fixture.json` parses.
3. Confirm every fixture has a `project/` directory.
4. Confirm every `logsFile` path exists when configured.
5. Confirm `evalId` matches directory name.
6. Confirm every fixture has non-empty `task`, `passCriteria`, and `failCriteria`.
7. Confirm the difficulty distribution is exactly:
   - 20 Low
   - 20 Medium
   - 20 High
   - 20 Ultra
   - 20 Max
8. Run the benchmark dry run if available.
9. Run the Python/unit validation tests if they are present and reasonably scoped.
10. Report exactly what changed, including new eval IDs and any upgraded eval IDs.

Deliverables:

- Updated fixture suite under `agent-eval-fixtures/fixtures/`
- Exactly 100 valid evals
- A short `EVAL_SUITE_UPGRADE_REPORT.md` summarizing:
  - total eval count
  - difficulty distribution
  - mode distribution
  - category distribution
  - new eval IDs
  - upgraded eval IDs
  - validation commands run
  - any known limitations

Do not stop after proposing a plan. Implement the changes, validate them, and provide a concise
final summary with the verification results.
