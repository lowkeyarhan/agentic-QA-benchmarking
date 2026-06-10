# Agent Benchmark

Portable benchmark harness for comparing Supatest, Cursor Agent, Codex, and Gemini CLI against copied Supatest eval fixtures.

This folder is intended to be self-contained. You can move `benchmark/` to Desktop or another machine and run it there, as long as the required CLIs are installed and logged in:

```text
supatest
cursor-agent
codex
gemini
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
```

`BENCHMARK_SUPATEST_PROJECT_ID` is optional. Leave it blank for isolated local
benchmarks. The harness intentionally does not inherit `.supatest/settings.json`
or `SUPATEST_PROJECT_ID`, so an interactive Supatest project such as `aiden`
does not leak into benchmark runs. Set `BENCHMARK_SUPATEST_PROJECT_ID` only if
you intentionally want Supatest sessions reported under a specific Supatest
project.

To benchmark a local compiled Supatest instead of the globally installed
production package, build it and point the harness at the compiled binary:

```bash
cd /Users/lowkeyarhan/Documents/supatest
pnpm install
pnpm -F @supatest/cli build
```

Then set this in `benchmark/.env`:

```bash
BENCHMARK_SUPATEST_BINARY=/Users/lowkeyarhan/Documents/supatest/cli/dist/index.js
BENCHMARK_SUPATEST_MODEL=premium
```

Supatest also needs a project scope for backend sessions. The harness uses
`BENCHMARK_SUPATEST_PROJECT_ID` first, then falls back to
`benchmark/.supatest/settings.json`. For the cleanest long-term benchmark,
use a dedicated Supatest project for benchmark sessions.

Confident AI dashboard upload is optional and separate from local benchmark
scoring. Local scoring does not require `CONFIDENT_API_KEY`. If you want to use
DeepEval tools manually, log DeepEval into the benchmark dotenv file:

```bash
cd /Users/lowkeyarhan/Desktop/benchmark
.venv/bin/deepeval login --save=dotenv:.env
```

The command prompts for a Confident AI API key from `https://app.confident-ai.com`.
After a benchmark run, open the latest combined DeepEval report with:

```bash
.venv/bin/deepeval view
```

## Run

```bash
./run_benchmark.py
```

Dry run:

```bash
./run_benchmark.py --dry-run
```

Live-device evals are preflighted before agents run. If an eval requires
runtime Maestro inspection and the matching Android/iOS device is not visible,
the harness records `blocked` for every agent on that eval instead of scoring it
as an agent failure. Use `BENCHMARK_DISABLE_PREFLIGHT=1` only when you
intentionally want to bypass that guard.

The batch judge model is config-preflighted before agents run. Keep
`DEEPEVAL_GEMINI_MODEL` on a Gemini model that supports Google GenAI structured
output; Gemma agent model names do not belong in that setting. If the judge
provider or API key is missing, the harness exits before launching any agents.
Scoring happens once at the end of all agent runs with one direct judge API
call, so Google free-tier RPM is not hammered by one request per result.
If Google quota is exhausted, switch the judge to OpenAI:

```bash
DEEPEVAL_JUDGE_PROVIDER=openai
OPENAI_API_KEY=...
DEEPEVAL_OPENAI_MODEL=gpt-5-nano
```

OpenAI API access is usage-billed separately from ChatGPT plans; use a key with
available API credits or billing enabled.

The default run executes every fixture present under `agent-eval-fixtures/fixtures`:

```text
Evals: all
Agents: supatest [premium], cursor [auto], codex [default], gemini [gemini-3.1-flash-lite]
Parallelism: 3
Timeout: 600s per agent run
```

The checked-in default agent list is:

```bash
BENCHMARK_AGENTS=supatest,cursor,codex,gemini
```

By default `benchmark/.env` overrides exported shell variables so local runs are
reproducible. For a one-off shell override, run with:

```bash
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=E3 ./run_benchmark.py
```

Use `BENCHMARK_EVAL_LIMIT` and `BENCHMARK_EVAL_OFFSET` to run the fixture suite
in fixed-size batches:

```bash
BENCHMARK_EVAL_IDS=all
BENCHMARK_EVAL_LIMIT=5      # use 10, 20, 50, or all for larger runs
BENCHMARK_EVAL_OFFSET=0     # next 5: 5, next 10: 10, etc.
```

Examples:

```bash
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=all BENCHMARK_EVAL_LIMIT=5 BENCHMARK_EVAL_OFFSET=0 ./run_benchmark.py
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=all BENCHMARK_EVAL_LIMIT=10 BENCHMARK_EVAL_OFFSET=0 ./run_benchmark.py
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=all BENCHMARK_EVAL_LIMIT=20 BENCHMARK_EVAL_OFFSET=0 ./run_benchmark.py
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=all BENCHMARK_EVAL_LIMIT=50 BENCHMARK_EVAL_OFFSET=0 ./run_benchmark.py
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=all BENCHMARK_EVAL_LIMIT=all BENCHMARK_EVAL_OFFSET=0 ./run_benchmark.py
```

You can run model variants directly from `.env` by putting the model after a
colon. The harness reuses the family command template and records each variant
separately:

```bash
BENCHMARK_AGENTS=supatest:premium,cursor:auto,codex:gpt-5.5,gemini:gemini-3.1-flash-lite
```

For plain agent names, set family model defaults:

```bash
BENCHMARK_SUPATEST_MODEL=premium
BENCHMARK_CURSOR_MODEL=auto
BENCHMARK_CODEX_MODEL=gpt-5.5
BENCHMARK_GEMINI_MODEL=gemini-3.1-flash-lite
```

Built-in command templates exist for Cursor, Codex, and Gemini. For any other
agent, add it to `BENCHMARK_AGENTS` and set `BENCHMARK_<AGENT>_CMD`. Custom
templates support these placeholders:

```bash
BENCHMARK_QA_PRO_MODEL=qa-large
BENCHMARK_QA_PRO_CMD='qa-pro run --model {model} --cwd {cwd} {prompt}'
BENCHMARK_AGENTS=supatest,qa-pro
```

`{model_arg}` expands to `--model <model>` when a model is selected, otherwise
empty. `{model}` expands to only the shell-quoted model value.

Prompt profile also affects score separation:

```bash
BENCHMARK_PROMPT_PROFILE=qa       # shared QA coaching for every agent
BENCHMARK_PROMPT_PROFILE=minimal  # task + mode + cwd boundary
BENCHMARK_PROMPT_PROFILE=raw      # fixture task only, plus failure log when present
```

Use `qa` when measuring task ability under a common QA frame. Use `raw` or
`minimal` when you want product-specific agent behavior to show through more
clearly.

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

Edit `.env` to change the evals, agents, models, prompt profile, parallelism,
timeouts, or judge budget. Use `BENCHMARK_EVAL_IDS=all` to include every
available fixture.

## Output

During execution, each agent line is printed once when that process exits, with
the score marked `pending`. After all agent runs finish, the harness makes one
batch judge API call and prints the final ordered score table.

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

Each result in `run.json` also includes deterministic `artifactChecks` and
`artifactWarnings`, independent of the LLM judge. These record whether the agent
actually changed test files, implementation/page files, markdown outputs, noisy
files only, Supatest memory, verification commands, and rate-limit evidence.

Detailed transcripts and copied projects stay under `runs/<run-id>/case-###/...`.
The `case-###` folder names avoid exposing eval IDs to the agents while the
result JSON maps each case back to its eval ID.

## Scoring

Runs are scored with one direct batch judge call after every agent run has
finished. Timeouts remain hard failures. Judge/runtime errors are recorded as
`unscored` and excluded from averages instead of being counted as agent
failures. Before judging, the harness removes agent names, local absolute paths,
benchmark credentials, spinner noise, and repeated terminal status redraws from
the evidence. The judge scores only against the task and fixture pass/fail
criteria, not against a specific CLI, product, model, company, cost profile, or
agent type.

For large runs, the batch prompt budget matters more than a DeepEval process
timeout. Defaults are:

```bash
BENCHMARK_BATCH_TOTAL_CASE_CHARS=180000
BENCHMARK_BATCH_CASE_CHARS=5000
BENCHMARK_JUDGE_BATCH_SIZE=
```

A 100-eval x 4-agent run has 400 judged cases. With the defaults, each case is
trimmed to about 450 characters in a single judge call, which can flatten scores
because the judge sees too little evidence. Prefer:

```bash
BENCHMARK_JUDGE_BATCH_SIZE=25
```

That keeps the per-case budget near the configured 5000 characters while making
several sequential judge calls. Raise process timeouts only if a judge request
actually times out after chunking. Score cells show satisfied pass checks and
triggered fail checks as `<passed>p/<failed>f result`, for example
`7p/0f pass`.
