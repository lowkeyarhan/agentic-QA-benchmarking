# Medium And High Eval Tuning

Medium and high QA Bench evals are tuned through shared metadata in `qa_bench/rubrics.py`.

No fixture task text, project code, logs, pass criteria, or fail criteria were changed. The tuning layer gives the judge structured evidence to look for after an agent run.

## Medium Suite

Run:

```bash
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=suite:qa-medium BENCHMARK_EVAL_LIMIT=all ./run_benchmark.py
```

Medium evals cover:

- investigate-before-asking behavior;
- reuse of existing `SUPATEST.md`;
- browser exploration without file creation;
- bounded retry/attempt behavior;
- app-bug discovery without assertion weakening;
- read-only planning;
- form validation coverage;
- test repair without conditional skips;
- report generation from session facts;
- manual-only and automation feature-validation modes;
- calendar/custom-widget repair.

## High Suite

Run:

```bash
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=suite:qa-high BENCHMARK_EVAL_LIMIT=all ./run_benchmark.py
```

High evals cover:

- no arbitrary waits;
- autonomous selector/timing recovery;
- deeper project discovery;
- selector-strategy documentation;
- batch authoring before execution;
- root-cause categorization before repair;
- assertion preservation;
- data/state repair;
- page-object selector/parser fixes;
- no over-mocking core behavior;
- exact assertion strength;
- scoped visual checks;
- custom dropdown interaction;
- removal of error-swallowing patterns.

## Tuning Contract

For every medium/high eval, `qa_bench/rubrics.py` should provide:

- `expectedSignals`: what objective evidence should appear in changed files, reports, artifacts, or transcript;
- `antiPatterns`: shortcuts that should lower the score;
- `scoringNotes`: the intended QA skill being measured.

This metadata is judge-facing only. It calibrates scoring for every agent equally and should not be injected into the agent prompt.
