Goal: improve Supatest's QA-agent performance and efficiency on production QA benchmark tasks without gaming the benchmark, weakening tests, changing eval content, or switching models as the first lever.

Supatest should outperform general agents by being better at the QA lifecycle:

- writing meaningful tests from product/user intent;
- repairing failing tests from logs, source, reporter artifacts, and conventions;
- diagnosing root cause accurately;
- preserving assertion intent;
- avoiding flaky waits and deceptive fixes;
- using browser/runtime evidence only when useful;
- producing clear QA evidence for humans and machine graders;
- staying token/time efficient.

## First Read

Read these files before editing:

- `cli/src/utils/task-classifier.ts`
- `cli/src/utils/harness-profile.ts`
- `cli/src/prompts/agents/base-agent.ts`
- `cli/src/prompts/blocks/test-integrity.ts`
- `cli/src/core/sdk-constants.ts`
- `cli/src/fix/context-writer.ts`
- `cli/src/modes/machine.ts`
- `cli/src/core/agent.ts`
- `cli/src/presenters/stream-json.ts`
- existing tests around prompt routing, classifier, SDK constants, and machine mode.

Do not assume the intended behavior is active just because the code exists. Verify the compiled CLI path uses it.

## Problem

Supatest has the right QA architecture, but benchmark behavior suggests the execution path can still be inefficient or under-instrumented.

Known risk areas:

1. `fix` / `test-repair` can spend too long exploring, rereading, or rerunning tests.
2. `build` / `test-authoring` can carry too much prompt/context weight.
3. Some task profiles may load blocks irrelevant to the current task.
4. The first context action may be too broad instead of task-specific.
5. Final output may not expose QA evidence clearly enough for enterprise-grade judging.
6. Telemetry may exist but not consistently fire in benchmark/headless mode.
7. The benchmark may use stale `cli/dist/index.js` unless rebuilt.

The goal is not to make Supatest "look good." The goal is to make it behave like a production QA agent.

## Scope

Implement agent-side changes only in the Supatest repo.

Do not modify benchmark eval prompts, benchmark cases, or fixtures.

Do not change model selection as part of this pass.

Do not weaken tests.

Do not allow:

- `test.skip`
- `test.only`
- `expect(true)`
- deleting meaningful assertions
- replacing real checks with smoke checks
- arbitrary sleeps as a fix
- broad test execution when a narrow verification is enough

## Required Changes

### 1. Verify Task Classification Is Used In All CLI Paths

Ensure `taskKind` and `harnessProfile` are selected before prompt assembly in:

- machine/headless mode;
- interactive mode;
- fix mode;
- build mode;
- plan mode;
- test-feature mode.

Expected mapping:

- failure logs, stack traces, flaky tests, selector errors -> `test-repair`
- write/add/create tests -> `test-authoring`
- PR/diff/changed files/affected flows -> `qa-code-verification`
- explicit runtime/browser/manual validation -> `test-feature-execution`
- read-only QA plan -> `risk-planning` or equivalent
- unknown/general implementation -> general fallback

Add or update tests proving benchmark-style prompts select the right profile.

Acceptance:

- A `fix` prompt with logs selects `test-repair`.
- A "write a Playwright test" prompt selects `test-authoring`.
- A PR/diff prompt selects `qa-code-verification`.
- A runtime feature validation prompt selects `test-feature-execution`.

### 2. Make First Context Action Deterministic By Task Kind

The first useful action should be predictable.

For `test-repair`:

1. read structured failure context/log;
2. read failing test file;
3. read directly implicated source/page object file;
4. only then consider broader search or browser evidence.

For `test-authoring`:

1. read project conventions / `SUPATEST.md`;
2. read representative existing tests;
3. read target source/page/component;
4. write focused tests.

For `qa-code-verification`:

1. read supplied diff if present;
2. otherwise use `git diff --name-only`, `git diff --stat`, and targeted hunks;
3. build changed-surface map;
4. produce affected-flow matrix.

For `test-feature-execution`:

1. inspect app/runtime only when URL or run instructions exist;
2. collect browser evidence;
3. produce report with screenshots/video/traces when required.

Add telemetry field:

```ts
firstContextAction: string;
```

Examples:

- `read-failure-log`
- `read-existing-tests`
- `read-diff`
- `open-browser`
- `read-project-conventions`

Acceptance:

- Stream JSON telemetry exposes `taskKind`, `harnessProfile`, and `firstContextAction`.

### 3. Harden `test-repair` Against Loops

This is the most important agent fix.

Implement or verify these behaviors in the `fix` / `test-repair` path:

#### File Re-Read Guard

If a file has already been read and has not changed, avoid rereading it from disk. Reuse the cached content or serve a compact summary.

Track:

```ts
repeatedFileReads: Record<string, number>;
```

Expose this in eval telemetry.

#### Structured Test Output

Do not feed full Playwright/Cypress/WDIO stdout back into the model repeatedly.

Convert test output into compact structure:

```ts
type StructuredFailure = {
  framework: "playwright" | "cypress" | "webdriverio" | "unknown";
  failingTest?: string;
  errorMessage?: string;
  stackFile?: string;
  stackLine?: number;
  assertionExpected?: string;
  assertionReceived?: string;
  selector?: string;
  screenshotPath?: string;
  tracePath?: string;
  videoPath?: string;
  rawBytesCompacted: number;
};
```

Keep raw output available in artifacts/logs, but send only structured failure context back to the model unless raw output is explicitly needed.

#### No-Write Escalation

If no file has been edited after N turns in `test-repair`, inject a hard nudge:

> You have enough context. Stop exploring. Either make the smallest valid repair now or explain why this is an application bug. Do not run more broad discovery.

Recommended default: `N = 12`.

Expose telemetry:

```ts
noWriteTurnCount: number;
repairEscalationTriggered: boolean;
```

#### Verification Boundaries

After a repair, run the narrowest relevant command first:

- exact test file;
- exact grep/title when available;
- no full suite unless narrow command passes or the project requires it.

Acceptance:

- A test-repair task cannot run until timeout without either editing a file or producing a clear app-bug explanation.
- Repeated reads and repeated broad test commands are visible in telemetry.
- Raw test output is compacted before being reintroduced to the model.

### 4. Trim Prompt Profiles By Task Kind

Audit prompt assembly. Each task kind should load only relevant blocks.

`test-authoring` should include:

- test authoring rules;
- project conventions;
- selector/page-object conventions;
- test integrity;
- narrow verification;
- final QA evidence format.

It should not include unrelated runtime/report/mobile/manual-heavy blocks unless explicitly requested.

`test-repair` should include:

- failure diagnosis;
- structured logs;
- preserve assertions;
- selector/timing/data/app-bug taxonomy;
- narrow verification;
- no deceptive fixes;
- final repair evidence format.

It should not include broad test planning or feature-reporting blocks unless needed.

`qa-code-verification` should include:

- diff-first behavior;
- changed-surface map;
- affected-flow matrix;
- relevance/coverage/coherence;
- read-only policy.

It should not include write/edit/browser/test execution instructions unless requested.

`test-feature-execution` should include:

- runtime/browser validation;
- screenshots/video/report expectations;
- manual/automation evidence;
- feature-level QA report.

Acceptance:

- Add a prompt-size diagnostic per profile.
- Premium tier prompt profile should not load every block unconditionally.
- Prompt token estimate should be materially lower than the legacy all-purpose prompt.

Expose:

```ts
promptProfileTokenEstimate: number
loadedPromptBlocks: string[]
```

### 5. Improve Final Output For QA Judging

Final answers should be structured and evidence-rich.

For `test-repair`, final output should include:

```md
## Root Cause

...

## Fix Applied

- Changed file:
- What changed:
- Why this preserves the original assertion intent:

## Verification

- Command:
- Result:

## QA Classification

- selector issue | timing issue | state issue | data issue | app bug | config issue | assertion bug

## Residual Risk

...
```

For `test-authoring`:

```md
## Tests Added

- File:
- Scenario:
- User flow:
- Assertions:

## Coverage

- Happy path:
- Edge/error/loading states:
- Regression covered:

## Verification

- Command:
- Result:

## Residual Risk

...
```

For `qa-code-verification`:

```md
| Changed surface | Evidence from diff | Affected user flow | Risk | Test to add/update | Why this covers the change |
| --------------- | ------------------ | ------------------ | ---- | ------------------ | -------------------------- |
```

Acceptance:

- The judge can identify generated tests, repaired tests, preserved assertions, root cause, and verification without reading the entire transcript.

### 6. Strengthen Telemetry In Headless/Benchmark Mode

When `SUPATEST_EVAL_TELEMETRY=1`, Stream JSON must emit safe diagnostic events.

Required fields:

```ts
type SupatestEvalTelemetry = {
  taskKind: string;
  harnessProfile: string;
  selectedModel?: string;
  resolvedModel?: string;
  promptProfileTokenEstimate?: number;
  loadedPromptBlocks?: string[];
  firstContextAction?: string;
  toolCounts?: Record<string, number>;
  repeatedFileReads?: Record<string, number>;
  deniedCommands?: string[];
  normalizedCommands?: string[];
  rawTestOutputBytesCompacted?: number;
  didWrite?: boolean;
  didRunTests?: boolean;
  didUseBrowser?: boolean;
  noWriteTurnCount?: number;
  repairEscalationTriggered?: boolean;
};
```

Do not emit secrets, raw env, API keys, full prompt text, or massive logs.

Acceptance:

- Benchmark runs can explain why Supatest won/lost without reading unstructured transcript.
- Timeout runs still include partial telemetry.

### 7. Add Tests

Add focused tests for:

- task classifier;
- harness profile selection;
- prompt block loading by task kind;
- test-repair no-write escalation;
- repeated file-read guard;
- structured test-output compaction;
- stream JSON telemetry;
- command policy for QA verification and test repair.

Commands to validate:

```bash
pnpm -F @supatest/cli type-check
pnpm -F @supatest/cli test
pnpm -F @supatest/cli build
```

After build, confirm benchmark uses:

```bash
BENCHMARK_SUPATEST_BINARY=/Users/lowkeyarhan/Documents/supatest/cli/dist/index.js
```

## Success Criteria

Supatest is improved when:

1. `test-repair` tasks stop timing out from exploration loops.
2. `build` tasks create meaningful tests with fewer turns.
3. prompt profile size drops significantly per task kind.
4. final answers expose QA evidence clearly.
5. telemetry explains routing, first action, tools, writes, test runs, and failure mode.
6. Supatest remains stricter than general agents about assertion integrity and non-deceptive fixes.
7. benchmark comparison becomes easier to debug without reading full transcripts.

## Non-Goals

Do not:

- modify benchmark cases;
- tune evals to favor Supatest;
- switch models;
- weaken test integrity rules;
- suppress failures;
- hide raw logs/artifacts;
- optimize only for token count at the cost of QA quality.

The final result should make Supatest behave like a fast, production-grade QA engineer: classify the task, gather the minimum correct context, make the smallest valid test-quality change, verify narrowly, and report clear evidence.
