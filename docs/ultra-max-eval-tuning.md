# Ultra And Max Eval Tuning

Ultra and max QA Bench evals are tuned through `qa_bench/rubrics.py` metadata, not by changing fixture prompts, projects, logs, pass criteria, or fail criteria.

## Ultra Suite

Run:

```bash
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=suite:qa-ultra BENCHMARK_EVAL_LIMIT=all ./run_benchmark.py
```

Ultra evals cover:

- WDIO and Cypress framework adaptation;
- knowing when browser context is unnecessary;
- bounded selector repair;
- minimal targeted edits;
- final full-suite regression after staged fixes;
- risk-based and journey-first planning;
- batch/single-test verification strategy;
- metadata repair;
- stale README/source-of-truth handling;
- responsive viewport tests;
- scoped API mocking;
- bug reporting from logs;
- flaky toast wait repair.

## Max Suite

Run:

```bash
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=suite:qa-max BENCHMARK_EVAL_LIMIT=all ./run_benchmark.py
```

Max evals cover:

- Maestro/mobile hierarchy inspection;
- stable selector discovery from current hierarchy;
- Appium/WDIO mobile test authoring;
- WebView context switching guidance;
- device-state-first debugging;
- Maestro-to-WDIO selector translation;
- WDIO log interpretation;
- Android-to-iOS selector porting;
- narrow WDIO run command authoring;
- production-regression root cause diagnosis;
- efficient debug plans;
- non-destructive page-object fixes;
- avoiding bash/grep/retry spirals;
- explicit emulator targeting;
- cross-platform mobile test strategy;
- system permission dialog handling.

## Fairness Rule

The tuning metadata is judge-facing only. It is used after an agent run to make the judge more consistent about objective evidence, anti-patterns, and intended QA skill. It should not be copied into agent prompts or used to add hidden answer keys.
