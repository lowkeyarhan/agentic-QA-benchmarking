# Agent Benchmark

Portable benchmark harness for comparing Supatest, Cursor Agent, and Codex against copied Supatest eval fixtures.

This folder is intended to be self-contained. You can move `benchmark/` to Desktop or another machine and run it there, as long as the required CLIs are installed and logged in:

```text
supatest
cursor-agent
codex
```

## Layout

```text
benchmark/
├── run_benchmark.py
├── .env
├── .env.example
├── .venv/
├── agent-eval-fixtures/
│   ├── fixtures/
│   ├── base-templates/
│   └── scripts/
├── runs/
└── results/
```

Agents never edit the source fixtures directly. Each run copies from:

```text
agent-eval-fixtures/fixtures/<eval-id>/project
```

into:

```text
runs/<run-id>/case-###/<agent>/project
```

## Setup

From inside this folder:

```bash
cp .env.example .env
```

The first run creates `.venv/` and installs Python dependencies automatically. If you move this folder after `.venv/` already exists, recreate it:

```bash
rm -rf .venv
./run_benchmark.py --dry-run
```

Edit `.env` and set:

```bash
GOOGLE_API_KEY=...
BENCHMARK_SUPATEST_PROJECT_ID=...
```

If `supatest` is not on your `PATH`, set:

```bash
BENCHMARK_SUPATEST_BINARY=/opt/homebrew/bin/supatest
```

## Run

```bash
./run_benchmark.py
```

Dry run:

```bash
./run_benchmark.py --dry-run
```

The default run executes every fixture present under `agent-eval-fixtures/fixtures`:

```text
Evals: all
Agents: supatest, cursor, codex
Parallelism: 3
Timeout: 600s per agent run
```

Use a comma-separated `BENCHMARK_EVAL_IDS` value for a smaller smoke or hard
suite. This seven-task subset is useful when you want a quick complex pass
without running the full fixture set:

| Eval | Coverage                                                                      |
| ---- | ----------------------------------------------------------------------------- |
| E18  | Build: all-product `problem_user` testing with app-bug escalation             |
| E25  | Build: batch multiple user-type tests before running                          |
| E29  | Fix: repair failing tests and add required metadata tags                      |
| E31  | Plan: comprehensive application test plan with explicit non-goals             |
| E43  | Fix: preserve strict equality while correcting whitespace extraction          |
| E77  | Fix: integrate a user-provided selector snippet into a reusable pattern       |
| E101 | Prod regression: translate Maestro/iOS hierarchy evidence into WDIO selectors |

Edit `.env` or the defaults at the top of `run_benchmark.py` to change that.
Use `BENCHMARK_EVAL_IDS=all` to include every available fixture.

## Output

```text
results/<run-id>/scores.md
results/<run-id>/summary.json
results/<run-id>/run.json
runs/<run-id>/case-###/<agent>/transcript.log
```

Each `results/<run-id>/` folder contains only three files:

- `scores.md` - human-readable score table
- `summary.json` - run metadata plus aggregate summary stats
- `run.json` - full individual case results grouped by eval and agent

Detailed transcripts and copied projects stay under `runs/<run-id>/case-###/...`.
The `case-###` folder names avoid exposing eval IDs to the agents while the
result JSON maps each case back to its eval ID.

## Scoring

Non-timeout runs are scored through the same DeepEval judge path for every
agent. Before judging, the harness removes agent names, local absolute paths,
benchmark credentials, spinner noise, and repeated terminal status redraws from
the evidence. The judge prompt instructs the model to score only against the
task and fixture pass/fail criteria, not against a specific CLI, product, model,
company, cost profile, or agent type.
