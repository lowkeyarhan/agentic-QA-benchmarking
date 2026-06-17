# Supatest Self-Improvement Benchmark Loop Prompt

You are working in `/Users/lowkeyarhan/Desktop/benchmark`. Your objective is to improve the local Supatest agent until it beats Cursor and every other compared agent on the QA benchmark, without gaming the benchmark.

Use `rtk` before shell commands in this workspace.

## Non-Negotiable Rules

- Do not edit benchmark fixtures, eval prompts, answer keys, scoring code, or judge logic to improve Supatest's score.
- Do not weaken tests, remove assertions, use fake assertions, add `test.only`, or add unjustified `test.skip`.
- Do not switch Supatest to a stronger model as the first lever. Improve Supatest behavior, prompts, routing, tools, telemetry, and compiled CLI correctness.
- Do not optimize only for a single known fixture by hard-coding eval IDs, file names, product names, or grader text.
- Keep changes in the Supatest repo unless a benchmark harness bug is proven. If you suspect a harness or judge bug, document it separately and continue improving real Supatest behavior.
- Every change must be validated by targeted tests, a targeted benchmark rerun, and then a full comparison run before declaring success.

## Success Criteria

You are done only when a fresh full comparison benchmark shows all of these:

- Supatest has the highest `Overall` score among all agents in the run.
- Supatest beats Cursor's `Overall` score by at least `+1.0`.
- Supatest has the highest or tied-highest `QA` score.
- Supatest has `0` failed evals on the comparison suite.
- Supatest does not regress materially on token efficiency or runtime compared with the previous Supatest run.
- The Supatest CLI is rebuilt and the benchmark is definitely using the rebuilt local binary.

If a judge anomaly is found, do not count it as success unless deterministic artifact checks also prove Supatest met the fixture contract.

## Current Baseline Context

Latest known run:

- Run ID: `20260615-133027`
- Suite: `suite:qa-low`
- Results file: `/Users/lowkeyarhan/Desktop/benchmark/results/20260615-133027/scores.md`

Baseline scores:

- Cursor: `Overall 90.1`, `QA 94.9`, `18 pass / 2 partial / 0 fail`
- Supatest: `Overall 64.1`, `QA 64.7`, `12 pass / 2 partial / 6 fail`
- Codex: `Overall 77.6`, `QA 82.7`
- Gemini: `Overall 48.2`, `QA 63.5`

Known Supatest misses from that run:

- `E3`: missed required `.supatest/SUPATEST.md` creation.
- `E7`: fixed selector/test, but did not use required browser inspection after selector failure.
- `E11`: judge marked metadata missing even though the final artifact appears to contain Playwright `tag: [...]`; treat as possible judge anomaly and verify deterministically.
- `E45`: hard-coded product IDs/names instead of capturing selected product name dynamically from the DOM.
- `E52`: pretended cart behavior was wishlist instead of honestly reporting missing wishlist feature and using a skipped TODO test.
- `E56`: hard-coded expected product-name arrays instead of dynamic discovery.
- `E58`: partial due to deterministic fixed-wait cap; all agents were capped, so inspect for a benchmark-wide issue but avoid introducing sleeps.
- `E79`: missed root cause `test.afterEach page.close()` and edited `CheckoutPage.ts` instead.

Weak metric areas:

- `metadata_quality = 0`
- `reporting_quality = 0`
- `evidence_quality = 20`
- `state_timing_reliability = 20`

Tooling symptoms:

- Supatest used many `WebSearch`/`WebFetch` calls and unrelated context tools.
- Supatest ran tests, but often stopped at local pass instead of checking the explicit fixture contract.
- Browser/tool evidence was underused when the task explicitly required it.

## Workflow Loop

Repeat this loop until the success criteria are met.

### 1. Establish The Latest Baseline

Find the latest result directory:

```bash
rtk ls -lt results
```

Read:

```bash
rtk sed -n '1,240p' results/<latest>/scores.md
rtk proxy jq '.runId, .generatedAt, .evalSelection, .agents' results/<latest>/run.json
```

Extract Supatest failures and partials:

```bash
rtk proxy jq -r '.runsByEval | to_entries[] | .value["supatest:premium"] | select(.result != "pass") | [.evalId, .evalName, .result, (.overallScorePercent|tostring), (.reason // ""), ((.failureTaxonomy // [])|join(","))] | @tsv' results/<latest>/run.json
```

For each failed or partial eval, inspect:

```bash
rtk proxy jq '.runsByEval.<EVAL_ID>["supatest:premium"] | {reason, passCriteria, failCriteria, failureTaxonomy, changedFiles, changedDiff, transcriptPath, telemetry}' results/<latest>/run.json
```

Compare against Cursor for the same eval:

```bash
rtk proxy jq '.runsByEval.<EVAL_ID>["cursor:auto"] | {reason, changedFiles, changedDiff, telemetry}' results/<latest>/run.json
```

### 2. Diagnose Root Cause Categories

For each miss, classify the cause into one of these:

- `prompt-contract`: the agent did not obey explicit pass/fail criteria.
- `task-routing`: wrong task kind/profile or irrelevant prompt blocks.
- `tool-policy`: required browser/runtime/log evidence not used, or unrelated external tools used.
- `artifact-contract`: required file, metadata, report, or final evidence omitted.
- `test-integrity`: hard-coded values, fake feature, weakened assertions, sleep, skip misuse.
- `root-cause`: agent patched symptoms instead of the actual failing cause.
- `harness-or-judge`: artifact appears correct but judge scored incorrectly.

Do not edit until you can name the top 1-3 recurring root causes.

### 3. Improve Supatest

Work in the Supatest repo:

```bash
cd /Users/lowkeyarhan/Documents/supatest
```

Read the relevant Supatest implementation before editing. Likely areas:

- `cli/src/utils/task-classifier.ts`
- `cli/src/utils/harness-profile.ts`
- `cli/src/prompts/agents/base-agent.ts`
- `cli/src/prompts/blocks/test-integrity.ts`
- `cli/src/core/sdk-constants.ts`
- `cli/src/fix/context-writer.ts`
- `cli/src/modes/machine.ts`
- `cli/src/core/agent.ts`
- `cli/src/presenters/stream-json.ts`

High-leverage improvements to implement:

- Add a "fixture contract checklist" before final answer: required artifacts, metadata shape, forbidden anti-patterns, and verification command.
- For test authoring, require dynamic DOM capture when the request says random/available/current product/item/name.
- For missing feature requests, require honest report plus `test.skip()` with detailed TODO only when the feature is absent and the eval asks for that pattern.
- For metadata tasks, enforce Playwright object metadata shape on every `test(...)`: `{ tag: ['@feature:*', '@priority:*', '@test_type:*'] }`.
- For project-discovery tasks, create required project memory/artifact files when explicitly requested, such as `.supatest/SUPATEST.md`.
- For selector failures, require browser/runtime inspection when the prompt explicitly demands it, before guessing selectors.
- For repair tasks, inspect failure logs and remove root-cause teardown/lifecycle bugs before touching page objects or selectors.
- Ban hard-coded expected arrays unless the constants come from app source code and the prompt allows that.
- Prevent arbitrary sleeps and fixed waits from being used as repair strategy.
- Reduce unrelated `WebSearch`, `WebFetch`, and irrelevant context tools for local QA tasks.
- Expose telemetry that proves task kind, harness profile, first context action, browser evidence, writes, tests, and repeated reads.

Add or update unit tests around the changed behavior.

### 4. Build Supatest

From `/Users/lowkeyarhan/Documents/supatest`:

```bash
rtk pnpm -F @supatest/cli build
```

Make sure the compiled binary exists:

```bash
rtk ls -l /Users/lowkeyarhan/Documents/supatest/cli/dist/index.js
```

### 5. Run Targeted Benchmark Reruns First

Return to benchmark:

```bash
cd /Users/lowkeyarhan/Desktop/benchmark
```

Run only the affected Supatest evals first. Example:

```bash
rtk proxy env \
  BENCHMARK_ENV_FILE_OVERRIDE=0 \
  BENCHMARK_SUPATEST_BINARY=/Users/lowkeyarhan/Documents/supatest/cli/dist/index.js \
  BENCHMARK_EVAL_IDS=E3,E7,E11,E45,E52,E56,E58,E79 \
  BENCHMARK_AGENTS=supatest:premium \
  BENCHMARK_TIMEOUT_SECONDS=300 \
  BENCHMARK_RUN_ID=verify-supatest-targeted-$(date +%Y%m%d-%H%M%S) \
  ./run_benchmark.py
```

Analyze the new run exactly as in step 1.

If any targeted eval still fails:

- inspect Supatest transcript and changed diff;
- identify whether the new behavior reached the compiled CLI;
- patch the real recurring cause;
- rebuild;
- rerun only the still-failing targeted evals.

Do not run the full comparison after every tiny change.

### 6. Run Full Comparison Only After Targeted Passes

Once targeted failures are fixed, run the same suite as the baseline with all agents:

```bash
rtk proxy env \
  BENCHMARK_ENV_FILE_OVERRIDE=0 \
  BENCHMARK_SUPATEST_BINARY=/Users/lowkeyarhan/Documents/supatest/cli/dist/index.js \
  BENCHMARK_EVAL_IDS=suite:qa-low \
  BENCHMARK_AGENTS=supatest:premium,cursor:auto,codex:gpt-5.5,gemini:gemini-3.1-flash-lite \
  BENCHMARK_TIMEOUT_SECONDS=300 \
  BENCHMARK_RUN_ID=compare-supatest-self-improve-$(date +%Y%m%d-%H%M%S) \
  ./run_benchmark.py
```

Then read:

```bash
rtk sed -n '1,260p' results/<new-run-id>/scores.md
```

Verify the success criteria exactly.

### 7. Continue Or Stop

If Supatest is not first overall, continue the loop with the new latest run.

Prioritize remaining gaps in this order:

1. Supatest failed evals.
2. Supatest partial evals where Cursor passed.
3. QA metric scores below Cursor.
4. Token/runtime inefficiency after quality is fixed.

If the same issue repeats for three consecutive improvement cycles with no measurable score gain, stop and produce a concise blocker report with:

- exact eval IDs;
- exact artifacts;
- why Supatest behavior is still wrong or why the judge/harness is suspect;
- the next smallest implementation change.

## Required Final Report

When done, report:

- latest successful run ID;
- score table;
- Supatest delta vs Cursor and previous Supatest baseline;
- changed Supatest files;
- tests/build commands run;
- targeted rerun IDs;
- final full-comparison run ID;
- remaining risks or judge anomalies.
