# Eval And Benchmark Interaction Changes

This is a simple summary of the changes made to QA Bench to test agent
interaction quality by difficulty.

## Eval Changes

- Added `qaBench` metadata to eval fixtures.
- Each eval now has a capability, metric IDs, and difficulty.
- Added difficulty suites:
  - `suite:qa-low`
  - `suite:qa-medium`
  - `suite:qa-high`
  - `suite:qa-ultra`
  - `suite:qa-max`
- Each difficulty suite has 20 evals.
- Added judge tuning in `qa_bench/rubrics.py`.
- The tuning lists expected signals, bad shortcuts, and scoring notes.
- The tuning is judge-facing only; it is not added to the agent prompt.

## Benchmark Changes

- The default production benchmark now runs the QA Bench production suite.
- The runner can select evals by suite, for example `suite:qa-high`.
- Results now include QA Bench capability, metric, difficulty, and mode data.
- Scores are aggregated by agent, capability, metric, difficulty, and mode.
- Added deterministic artifact checks outside the LLM judge.
- These checks catch shortcuts like skipped tests, weak assertions, fixed waits,
  swallowed failures, missing verification, and changing files in plan-only tasks.
- Supatest and custom agent commands can receive `{difficulty}` and
  `{max_iterations}` placeholders.
- Max iterations now scale by difficulty:

| Difficulty | Max iterations |
| ---------- | -------------: |
| `low`      |             75 |
| `medium`   |             95 |
| `high`     |            120 |
| `ultra`    |            150 |
| `max`      |            180 |

## What Each Difficulty Tests

- `low`: basic QA behavior, simple test authoring, selector fixes, and honest
  reporting.
- `medium`: bounded exploration, reuse of existing setup, feature validation,
  reports, and avoiding conditional skips.
- `high`: robust waits, deeper project discovery, root-cause repair, preserving
  assertions, and avoiding shortcuts.
- `ultra`: framework adaptation, stale evidence handling, staged verification,
  scoped mocking, and complex browser workflows.
- `max`: mobile QA, Appium/WDIO/Maestro work, view hierarchy inspection, device
  targeting, log interpretation, and non-destructive fixes.

## Main Goal

The benchmark now checks whether agents adjust their behavior to the task
difficulty: inspect first, use the right evidence, keep edits scoped, verify
properly, and avoid shortcuts.
