# Low Eval Tuning

Low-difficulty QA Bench evals are tuned through metadata, not by weakening task content or embedding hidden answers in prompts.

## What Was Tuned

Each low eval now has eval-specific QA calibration in `qa_bench/rubrics.py`:

- `expectedSignals`: concrete evidence the judge should look for in diffs, artifacts, and transcripts.
- `antiPatterns`: concrete shortcuts that should reduce score when observed.
- `scoringNotes`: short notes explaining the intended QA skill.

The original fixture tasks, projects, logs, pass criteria, and fail criteria remain stable.

## Why This Is Fair

The metadata is visible in benchmark outputs and applies to every agent equally. It does not tell an agent what to do during the run; it helps the judge consistently score whether the generated tests or repairs meet the QA intent.

## Low Suite

Run all low evals with:

```bash
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=suite:qa-low BENCHMARK_EVAL_LIMIT=all ./run_benchmark.py
```

The low suite currently covers:

- immediate test authoring;
- project discovery;
- selector strategy;
- browser-context selector repair;
- metadata tags;
- assertion quality;
- implementation-vs-test repair;
- dynamic data handling;
- behavior verification;
- honest skipped-test reporting;
- root-cause repair without sleeps or swallowed failures.

## Maintenance Rule

When adding or editing low evals:

1. Keep the task realistic and vendor-neutral.
2. Add explicit pass/fail criteria.
3. Add `qaBench` capability, metrics, and difficulty.
4. Add eval-specific tuning in `LOW_EVAL_TUNING`.
5. Ensure tests prove the new eval has expected signals, anti-patterns, and scoring notes.
