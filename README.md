# QA Bench

Portable QA benchmark harness for comparing Supatest, Cursor Agent, Codex, Gemini CLI, and other coding agents on real test-quality work.

QA Bench is scoped to the QA lifecycle rather than generic coding tasks. It
measures whether agents can author tests, repair failing tests, classify root
causes, use logs and runtime evidence, preserve test intent, follow project
conventions, handle mobile/browser context, and report test health clearly.

This folder is intended to be self-contained. You can move `benchmark/` to Desktop or another machine and run it there, as long as the required CLIs are installed and logged in:

```text
supatest
cursor-agent
codex
gemini
```

## QA Bench Suites

Use `BENCHMARK_EVAL_IDS=suite:<name>` to select a production QA suite without
editing fixture content:

| Suite | Purpose |
| --- | --- |
| `suite:qa-production` | Every available QA lifecycle fixture. This is the default production benchmark. |
| `suite:qa-core` | Balanced representative suite for vendor comparisons. |
| `suite:qa-smoke` | Fast sanity suite across authoring, repair, planning, runtime evidence, and mobile QA. |
| `suite:qa-lifecycle-extended` | Broad lifecycle suite covering advanced QA tasks across web, mobile, repair, reporting, evidence, and metadata workflows. |

Each eval is tagged in `summary.json`, `run.json`, and dashboard metadata with a
QA capability such as `test-authoring`, `test-repair`,
`root-cause-debugging`, `feature-validation`, `reporting-and-evidence`,
`metadata-governance`, `project-discovery`, `browser-context`, or `mobile-qa`.

Each eval also carries QA metric IDs, including `relevance`, `coverage`,
`assertion_quality`, `test_integrity`, `maintainability`, `selector_strategy`,
`state_timing_reliability`, `root_cause_accuracy`, `evidence_quality`,
`reporting_quality`, `metadata_quality`, `manual_workflow`,
`framework_adaptation`, `ci_log_analysis`, and `mobile_context`.

The judge returns the existing overall QA pass/partial/fail score plus optional
dimension scores for those metric IDs. If a judge omits metric scores, the
runner falls back to the case QA score for metric aggregation so outputs remain
backward-compatible.

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

Host-side fixture notes and answer keys such as `solution.md` stay outside the
agent workspace. The harness copies only the `project/` subtree for execution.

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
BENCHMARK_SUPATEST_MACHINE_MODE=1
```

For benchmark fairness, host-level `rtk` is hidden from the `PATH` inherited by
benchmark-launched agents by default:

```bash
BENCHMARK_HIDE_HOST_TOOLS=rtk
```

If Supatest uses RTK in a product benchmark, that support should come from the
local compiled Supatest runtime/toolchain itself, not from shared fixture
prompts or a globally leaked host `rtk`. The generated `summary.json` and
`run.json` include the active tool policy for later audit.

Supatest also needs a project scope for backend sessions. The harness uses
`BENCHMARK_SUPATEST_PROJECT_ID` first, then falls back to
`benchmark/.supatest/settings.json`. For the cleanest long-term benchmark,
use a dedicated Supatest project for benchmark sessions.

`BENCHMARK_SUPATEST_MACHINE_MODE=1` runs Supatest through its stream-json
machine interface. Keep this enabled for benchmarks because the final
stream-json result includes token and cost telemetry.

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

Supatest eval dashboard upload is also optional and separate from Confident AI.
Create an API key from the Supatest eval dashboard under **Settings → API Keys**,
then add it to `benchmark/.env`:

```bash
BENCHMARK_SUPATEST_EVAL_DASHBOARD_API_KEY=sk_eval...
BENCHMARK_SUPATEST_EVAL_DASHBOARD_URL=https://evals-dashboard.supatest.ai
BENCHMARK_SUPATEST_EVAL_DASHBOARD_RUN_NAME=Benchmark {run_id}
```

When `BENCHMARK_SUPATEST_EVAL_DASHBOARD_API_KEY` is set, the harness posts the
final scored results to `POST /api/v1/ingest` after local `scores.md`,
`summary.json`, and `run.json` are written. The upload sends one summary result
per non-blocked benchmark agent, using eval IDs such as
`summary:supatest-premium` and `summary:cursor-auto`. These summary results and
the run metadata include the same QA Avg, Token Avg, Token Usage, Overall Score,
Pass, Partial, and Fail table from `scores.md`. Set
`BENCHMARK_SUPATEST_EVAL_DASHBOARD_STRICT=1` only if an upload failure should
make the benchmark exit non-zero after writing local results.

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

The batch judge model is API-preflighted before agents run with a tiny
structured-output call. Keep `DEEPEVAL_GEMINI_MODEL` on a Gemini model that
supports Google GenAI structured output; Gemma agent model names do not belong
in that setting. If the judge provider, API key, quota, model, or structured
output path is broken, the harness exits before launching any agents. Scoring
happens at the end of all agent runs through direct judge API calls, so Google
free-tier RPM is not hammered by one request per result.
If Google quota is exhausted, switch the judge to OpenAI:

```bash
DEEPEVAL_JUDGE_PROVIDER=openai
OPENAI_API_KEY=...
DEEPEVAL_OPENAI_MODEL=gpt-5-nano
```

OpenAI API access is usage-billed separately from ChatGPT plans; use a key with
available API credits or billing enabled.

The default run executes the QA Bench production suite:

```text
Evals: suite:qa-production
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
BENCHMARK_EVAL_IDS=suite:qa-production
BENCHMARK_EXTRA_EVAL_IDS=E2,E6  # append one-off evals without replacing the suite
BENCHMARK_EVAL_LIMIT=5      # use 10, 20, 50, or all for larger runs
BENCHMARK_EVAL_OFFSET=0     # next 5: 5, next 10: 10, etc.
```

Examples:

```bash
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=suite:qa-smoke BENCHMARK_EVAL_LIMIT=all ./run_benchmark.py
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=suite:qa-core BENCHMARK_EVAL_LIMIT=all ./run_benchmark.py
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=suite:qa-production BENCHMARK_EVAL_LIMIT=20 BENCHMARK_EVAL_OFFSET=0 ./run_benchmark.py
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=suite:qa-production BENCHMARK_EVAL_LIMIT=50 BENCHMARK_EVAL_OFFSET=0 ./run_benchmark.py
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=suite:qa-production BENCHMARK_EVAL_LIMIT=all BENCHMARK_EVAL_OFFSET=0 ./run_benchmark.py
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

Built-in command templates exist for Cursor, Codex, and Gemini. Cursor and
Gemini built-ins use `--output-format stream-json` so token metadata is emitted
when the CLI exposes it. For any other agent, add it to `BENCHMARK_AGENTS` and
set `BENCHMARK_<AGENT>_CMD`. Custom templates support these placeholders:

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

Use a comma-separated `BENCHMARK_EVAL_IDS` value for a targeted debug subset.
For reusable QA comparisons, prefer one of the named suites above so run
metadata can identify the benchmark scope.

Use `BENCHMARK_EXTRA_EVAL_IDS` when you want to keep the base suite/subset but
manually add specific evals for a run. Extras support comma-separated eval IDs
or `suite:<name>`, are deduped, and are appended after `BENCHMARK_EVAL_LIMIT`
and `BENCHMARK_EVAL_OFFSET` are applied.

```bash
BENCHMARK_ENV_FILE_OVERRIDE=0 BENCHMARK_EVAL_IDS=suite:qa-smoke BENCHMARK_EXTRA_EVAL_IDS=E2,E6 ./run_benchmark.py
```

Example targeted debug subset:

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
timeouts, or judge budget. Use `BENCHMARK_EVAL_IDS=suite:qa-production` for the
full QA Bench production run, or `BENCHMARK_EVAL_IDS=all` when you explicitly
want every available fixture without suite labeling.

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

Each run also includes a top-level `qaBench` object in `summary.json` and
`run.json`. It records the suite name, QA Bench version, per-eval capability,
metric IDs, metric definitions, capability definitions, and aggregate scores by
agent/capability/metric/difficulty/mode. `scores.md` mirrors the most important
parts as QA Bench capability, metric, and difficulty tables.

Each result also includes `telemetry` when the agent emits structured JSON or
NDJSON events. The parser summarizes model/provider hints, turns, SDK duration,
token/cost counters, tool counts, first tool, first shell command, command
categories, policy denials, and whether the run wrote files, ran tests, used a
browser/runtime tool, or asked the user. Malformed JSON lines are counted but do
not fail the benchmark run. Supatest benchmark launches set
`SUPATEST_EVAL_TELEMETRY=1` by default; set
`BENCHMARK_SUPATEST_EVAL_TELEMETRY=0` to disable that diagnostic stream.

Each result includes a `failureTaxonomy` array. These labels are heuristic and
diagnostic rather than score replacements; examples include `timeout`,
`agent-error`, `judge-error`, `missing-artifact`, `missing-verification`,
`grader-fail`, `over-tooling`, `wrong-route`, `env-auth`, and
`missing-token-usage`.

Run-level `summary.json` and `run.json` include `reproducibility` metadata with
the benchmark git SHA/branch/dirty state, fixture content hashes, selected agent
models, timeout/parallelism, prompt profile, judge batch size, and environment
mode. They also include aggregate `diagnostics` for failure taxonomy counts and
per-agent tool/first-action summaries.

Each result also includes `tokenUsage` when the agent transcript or usage
sidecar exposes token data. Known token usage is scored separately from task
correctness: within each eval, the lowest known token total receives a token
efficiency score of `100`, and other known runs receive `best_tokens /
agent_tokens`. Unknown usage remains `n/a`.

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

The judge receives changed-file excerpts and deterministic artifact checks, not
just the process exit code. It is instructed to penalize lazy or deceptive test
changes such as `expect(true)`, assertion weakening, over-mocking the behavior
under test, fabricated selectors, and unsupported success claims.

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

## Token Usage

Token usage is extracted from agent transcripts and common usage sidecars such
as `usage.json`, `token-usage.json`, `telemetry.json`, and `cli.log` in the run
folder. The parser understands common fields such as `input_tokens`,
`output_tokens`, `total_tokens`, `prompt tokens`, `completion tokens`, and Codex
CLI footers like `tokens used`.

For the built-in agents, the next run attempts to emit machine-readable usage:

- Supatest runs with `BENCHMARK_SUPATEST_MACHINE_MODE=1`, sending the prompt over
  stdin and reading the final stream-json `usage` payload.
- Cursor runs with `--output-format stream-json`.
- Gemini runs with `--output-format stream-json`, including Gemini
  `usage_metadata` when the CLI exposes it.
- Codex keeps using the CLI footer parser because it already emits `tokens used`.

The `scores.md` aggregate table includes:

- `QA Avg` - average judge score for correctness
- `Token Avg` - average relative token-efficiency score
- `Token Usage` - summed known total tokens
- `Cache Read` - summed known cached input tokens read by the provider
- `Cache Create` - summed known cache creation input tokens
- `Overall Score` - weighted combined score for ranking agents
- `Pass`, `Partial`, `Fail` - result distribution for each agent

By default, `Overall` is calculated as:

```text
overall = QA average * 0.7 + token efficiency average * 0.3
```

Change the QA weight in `.env` if you want token efficiency to matter more or
less. Token efficiency receives the remaining weight:

```bash
BENCHMARK_OVERALL_QA_WEIGHT=0.7
```

Token efficiency is calculated per eval from QA-passing baseline runs only:

```text
token efficiency = best_passing_tokens / agent_tokens * 100
```

`best_passing_tokens` ignores agents below
`BENCHMARK_TOKEN_BASELINE_QA_THRESHOLD`, so an agent that crashes quickly cannot
become the "most efficient" baseline. Runs below the QA threshold are capped at
their QA score for token efficiency. If token usage is unknown, token efficiency
is `0`, so the overall score still exists but the token component is penalized.

```bash
BENCHMARK_TOKEN_BASELINE_QA_THRESHOLD=0.8
```

The harness does not hard-code provider prices. To estimate cost, set per-agent
rates in `.env`:

```bash
BENCHMARK_TOKEN_PRICE_CODEX_INPUT_PER_1M=
BENCHMARK_TOKEN_PRICE_CODEX_OUTPUT_PER_1M=
BENCHMARK_TOKEN_PRICE_CODEX_TOTAL_PER_1M=
```

Agent-specific inline variants are also supported, so
`codex:gpt-5.5` can use `BENCHMARK_TOKEN_PRICE_CODEX_GPT_5_5_TOTAL_PER_1M`
before falling back to `BENCHMARK_TOKEN_PRICE_CODEX_TOTAL_PER_1M`.

If an agent or proxy hides usage, leave it blank to receive a zero efficiency
score, or set an explicit trusted fallback in `.env`:

```bash
BENCHMARK_TOKEN_USAGE_FALLBACK_SUPATEST_TOKENS=
BENCHMARK_TOKEN_USAGE_FALLBACK_CURSOR_TOKENS=
BENCHMARK_TOKEN_USAGE_FALLBACK_CODEX_TOKENS=
BENCHMARK_TOKEN_USAGE_FALLBACK_GEMINI_TOKENS=
BENCHMARK_TOKEN_USAGE_FALLBACK_TOKENS=
```
