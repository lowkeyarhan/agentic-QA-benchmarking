# Supatest Agent Improvement Prompt

Use this prompt to improve the Supatest CLI agent against QA Bench without changing benchmark answers, weakening evals, or adding Supatest-only shortcuts.

## Goal

Make Supatest perform exceptionally well on QA lifecycle tasks while reducing tokens, turns, and wall time.

The target is not just higher pass rate. Supatest should win because it behaves like a production QA agent:

- creates meaningful tests from natural-language QA requests;
- fixes failing tests without weakening assertions;
- diagnoses root causes from code, logs, reporters, browser/device context, and project conventions;
- preserves selector strategy, page objects, tags, manual markers, and metadata;
- gathers the right evidence when runtime validation is required;
- avoids broad exploration, repeated discovery, and unrelated artifact creation.

## Current Problems

### 1. Too Many Tokens From Large Repeated Prefixes

Recent benchmark runs show Supatest doing solid QA work but paying much more cache-read and wall-time cost than competitors.

Observed symptom:

- Supatest used millions of cache-read tokens across small eval subsets.
- Passing evals still cost far more than Cursor/Codex.
- A large prompt/tool/context prefix appears to be replayed every turn.

Likely cause:

- build/fix/plan/test-feature/mobile/report instructions are loaded too broadly;
- tool docs and runtime guidance are included for tasks that do not need them;
- project discovery context is not scoped tightly enough by task kind.

Required fix:

- introduce task-kind-conditional prompt loading for every mode, not only QA code verification;
- keep only the relevant blocks for `build`, `fix`, `plan`, `test-feature`, `report`, mobile, and runtime exploration;
- measure prefix token count before and after;
- keep durable project rules cacheable, but avoid caching task-specific or irrelevant context into every turn.

### 2. Fix Mode Sometimes Over-Scopes

Example benchmark behavior:

- Supatest correctly fixed selector/root-cause tasks but lost points for unnecessary file noise.

Required fix:

- for `fix` / `test-repair`, default to the smallest file set that can fix the root cause;
- preserve existing assertions unless the user explicitly asks to update expected behavior;
- do not add reports, screenshots, generated docs, or broad refactors unless the fixture asks for them;
- if a regression test is added, it must directly prove the fixed bug.

### 3. The Agent Asks Questions When Code Already Answers Them

Benchmark-shaped QA tasks usually provide enough context in the repo, logs, or task text.

Required fix:

- in headless/build/fix benchmark-shaped tasks, do not ask user questions for framework, URL, selector strategy, or expected behavior when those can be read from files/logs;
- ask only when there is no diff/log/code path or when multiple destructive interpretations are possible;
- prefer one targeted read/search before asking.

### 4. Policy Denials Waste Turns

Observed judge diagnostics include policy-denial signals.

Required fix:

- expose the effective tool policy to the model in compact form;
- after any denied command, immediately switch to an allowed equivalent;
- do not retry denied commands with small variations;
- for read-only contexts, use `rg`, `ls`, `cat`, `git diff`, and targeted file reads.

### 5. Build Mode Needs A Strong QA Authoring Checklist

Supatest should not merely create a file. It should create a real test.

Required behavior:

- discover framework/config quickly;
- read one or two representative tests/page objects when conventions exist;
- use stable selectors or existing page object methods;
- implement the requested flow;
- add meaningful assertions that would fail if the product behavior breaks;
- avoid `expect(true)`, empty bodies, broad snapshots, `.skip`, `.only`, arbitrary sleeps, and hard-coded assumptions unless the task explicitly requires a documented skip;
- run the smallest useful verification command unless the task says no-run/authoring-only.

### 6. Fix Mode Needs A Structured Repair Loop

Required loop:

1. Read the failure log and identify the root-cause category.
2. Read only the failing test and directly referenced helper/page object/app file.
3. Decide whether the bug is selector, timing, state/data setup, test code, app code, config, or environment.
4. Edit the smallest necessary file set.
5. Run a targeted verification command.
6. If still failing, use structured failure output, not raw repeated logs.
7. Stop after a bounded number of attempts and make the best evidence-backed fix.

Do not:

- weaken assertions;
- change expected values to match broken behavior;
- wrap assertions in try/catch;
- skip tests;
- add fixed sleeps;
- mock the core behavior being tested unless the task explicitly asks for mocking.

### 7. Project Discovery Should Be Cached And Reused

Required fix:

- cache framework, test command, selector strategy, page object map, and existing test conventions per project/fixture hash;
- reuse the discovery artifact across turns and repeat benchmark cases;
- do not regenerate `SUPATEST.md` when the same valid artifact already exists;
- store enough to reduce reads, not a giant context blob.

## Scope

In scope:

- Supatest CLI harness/task classification;
- prompt block routing by task kind;
- tool-policy-aware behavior;
- build-mode and fix-mode QA checklists;
- compact project discovery cache;
- structured test result parsing;
- pre-final QA self-check;
- telemetry for task kind, first action, tool counts, token usage, denied commands, and files touched.

Out of scope:

- changing benchmark expected answers to favor Supatest;
- model switching as the first fix;
- adding hidden answer keys into prompts;
- weakening real QA requirements;
- changing eval fixtures after seeing a run unless the change improves fairness/coverage for all agents.

## Desired Harness Profiles

### `test-authoring`

Load only:

- framework detection;
- project conventions;
- selector/page-object strategy;
- assertion quality;
- targeted verification.

Avoid:

- browser runtime instructions unless selectors cannot be determined from code;
- mobile/device blocks unless mobile framework is detected;
- reporting/evidence upload blocks unless requested.

### `test-repair`

Load only:

- failure-log analysis;
- root-cause taxonomy;
- assertion preservation;
- minimal edit policy;
- targeted verification;
- structured retry loop.

Avoid:

- broad project discovery after root cause is known;
- report generation unless requested;
- full-suite reruns before a targeted fix passes.

### `risk-planning`

Read-only:

- diff/source/log/context analysis;
- affected flows;
- test matrix;
- Not Testing / risk tradeoffs.

Do not write files or run tests unless explicitly requested.

### `feature-validation`

Use runtime evidence when requested:

- browser/device inspection;
- screenshots/video/traces where available;
- concise report with coverage, bugs found, and residual risks.

Do not apply this heavy workflow to ordinary `build` or `fix` tasks.

## Pre-Final QA Self-Check

Before final response, the agent should internally verify:

- no `waitForTimeout`, `sleep`, or arbitrary fixed waits were introduced;
- no `.skip`, `.only`, empty test body, or `expect(true)` was introduced;
- assertions prove the requested user behavior;
- existing assertion intent was preserved;
- selectors follow project strategy;
- tests use existing page objects when expected;
- only relevant files changed;
- targeted verification was run or a blocker was reported;
- final answer states what changed and what was verified.

## Token Efficiency Targets

Track these per benchmark task:

- first context action;
- first write turn;
- total turns;
- total tokens;
- cache-read tokens;
- tool count by tool;
- files read more than once without changing;
- denied commands;
- raw test output bytes resent to the model.

Targets:

- reduce cached prefix size by at least 40%;
- reduce average build/fix turns by at least 25%;
- avoid reading unchanged files more than once per session;
- replace raw repeated test output with structured `{test, error, file, line, stack}` summaries.

## Acceptance Criteria

Supatest should improve without benchmark-case changes:

- QA score stays high or improves;
- token average improves materially;
- wall time improves materially;
- low-difficulty build tasks pass with strong assertions and stable selectors;
- low-difficulty fix tasks preserve assertions and edit the actual root-cause file;
- high/ultra repair tasks no longer timeout from open-ended loops;
- telemetry explains first action, tool path, changed files, and failure taxonomy.

## Validation Commands

Run Supatest checks from the Supatest repo:

```bash
pnpm -F @supatest/cli type-check
pnpm -F @supatest/cli test
pnpm -F @supatest/cli build
```

Run benchmark slices from this repo:

```bash
BENCHMARK_EVAL_IDS=suite:qa-low ./run_benchmark.py
BENCHMARK_EVAL_IDS=E12,E25,E40 ./run_benchmark.py
BENCHMARK_EVAL_IDS=E48,E50,E118 ./run_benchmark.py
```

For judge-only prompt changes, re-score existing artifacts instead of rerunning agents:

```bash
./run_benchmark.py --score-existing <run-id>
```

## Reporting Requirements

For every improvement PR, attach:

- changed files;
- type-check/test/build output;
- before/after benchmark run IDs;
- QA average, token average, time, and overall score;
- capability/metric breakdown;
- failure taxonomy changes;
- known residual risks.
