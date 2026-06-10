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
