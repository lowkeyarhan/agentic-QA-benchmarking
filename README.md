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
runs/<run-id>/<eval-id>/<agent>/project
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

The default run executes:

```text
Evals: E1, E3, E7, E11, E15
Agents: supatest, cursor, codex
Parallelism: 3
Timeout: 450s per agent run
```

This five-task core suite is meant to stay lightweight while covering enough
variety to compare the three agents:

| Eval | Coverage |
| --- | --- |
| E1 | Light: clear build task, starts immediately, writes and runs a login test |
| E3 | Light/medium: framework detection, existing-test discovery, `SUPATEST.md` generation |
| E7 | Medium: selector failure handling with browser-assisted debugging |
| E11 | Medium: complete checkout coverage with required Playwright metadata tags |
| E15 | Medium fix-mode: minimal targeted repair without rewriting passing tests |

Edit `.env` or the defaults at the top of `run_benchmark.py` to change that.

## Output

```text
results/<run-id>/run.json
results/<run-id>/scores.md
results/<run-id>/summary.json
results/<run-id>/<eval-id>/<agent>.json
runs/<run-id>/<eval-id>/<agent>/transcript.log
```

`run.json` is the combined machine-readable artifact for a run. It includes
run metadata, aggregate summary stats, the eval-by-agent matrix, and all
individual case results in one file.
