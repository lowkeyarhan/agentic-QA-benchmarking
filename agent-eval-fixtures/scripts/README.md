# Agent Evals Runner

Run evaluation tests against the Supatest CLI agent with automatic streaming to the [Eval Control Dashboard](https://evals-dashboard.supatest.ai).

## Quick Start

### 1. Get API Key (one-time setup)

1. Go to the [Eval Control Dashboard](https://evals-dashboard.supatest.ai)
2. Navigate to Settings → API Keys
3. Create a new API key
4. Add to your environment:
   ```bash
   export DASHBOARD_API_KEY="your-api-key-here"
   ```

### 2. Run Evals

```bash
# Run a single eval
/agent-evals E3

# Run multiple evals
/agent-evals E3 E4 E14

# Run all Tier 1 (critical) evals
/agent-evals tier1

# Run all 100 evals
/agent-evals all
```

## Usage

```
/agent-evals <eval-id or "all">
```

### Run a Single Eval
```bash
/agent-evals E3
```

### Run Multiple Evals
```bash
/agent-evals E3 E4 E14
```

### Run by Tier
```bash
# Tier 1 (Critical): E1, E3, E11, E10, E7, E33
/agent-evals tier1

# Tier 2 (Mode-specific): E14, E15, E19, E20, E2, E34, E35
/agent-evals tier2

# Tier 8 (Deception detection): E44-E51
/agent-evals tier8

# All tiers: tier1 through tier10
```

### Run All Evals
```bash
/agent-evals all
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DASHBOARD_API_KEY` | Yes* | - | API key from dashboard settings |
| `DASHBOARD_URL` | No | `https://evals-dashboard.supatest.ai` | Dashboard base URL |
| `DASHBOARD_OFFLINE` | No | `0` | Set to `1` to disable dashboard streaming |

*Not required when `DASHBOARD_OFFLINE=1`

## Offline Mode

If you need to run evals without streaming to the dashboard (e.g., for debugging):

```bash
export DASHBOARD_OFFLINE=1
/agent-evals E3
```

## How It Works

The integration follows the step-by-step ingest pattern:

1. **Create Run** (`POST /api/v1/runs`)
   - Creates a new run in the dashboard
   - Returns a run ID for subsequent requests

2. **Run Evals** (sequential, one by one)
   - Loads fixture.json for each eval
   - Runs the CLI with the eval's task
   - Captures output, exit code, and timing

3. **Push Results** (`POST /api/v1/runs/{runId}/results`)
   - Immediately after each eval completes
   - Includes result status, score, duration, logs
   - Results appear in dashboard in real-time

4. **Complete Run** (`POST /api/v1/runs/{runId}/complete`)
   - Marks the run as completed
   - Records total duration

## Result Scoring

| CLI Exit Code | Result | Score |
|--------------|--------|-------|
| 0 | `pass` | 100 |
| Contains "PARTIAL" | `partial` | 50 |
| Other | `fail` | 0 |

## Example Output

```
🚀 Agent Evals
   Dashboard: https://evals-dashboard.supatest.ai
   Evals to run: E3, E4, E14

📊 Creating run in dashboard...
   Run created: run_abc123

🧪 Running E3: Playwright Detection + SUPATEST.md Generation
   Mode: build
   Task: Write a test for removing items from the cart
   ... CLI output ...
   📤 Pushing result to dashboard...
   ✅ Result recorded: PASS (100%)

🧪 Running E4: WebDriverIO Framework Adaptation
   ...

📋 RUN SUMMARY
============================================================
Run ID: run_abc123
Name: Agent Evals Run - 2026-02-17T12:00:00.000Z
Total Duration: 45.32s

Total Evals: 3
✅ Passed: 3
⚠️  Partial: 0
❌ Failed: 0
📊 Success Rate: 100.0%
============================================================

🔗 View results at: https://evals-dashboard.supatest.ai
```

## Direct Script Usage

You can also run the script directly:

```bash
cd agent-eval-fixtures/scripts

# With dashboard streaming (requires DASHBOARD_API_KEY)
tsx agent-evals-dashboard.ts E3

# Offline mode
tsx agent-evals-dashboard.ts E3
# (with DASHBOARD_OFFLINE=1 set)
```

## Available Evals

See `.agents/skills/agent-evals/SKILL.md` for tier map and workflow. Per-eval criteria live in `agent-eval-fixtures/fixtures/E{N}/fixture.json`.

### Priority Tiers

| Tier | Evals | Description |
|------|-------|-------------|
| tier1 | E1, E3, E11, E10, E7, E33 | Critical behavior |
| tier2 | E14, E15, E19, E20, E2, E34, E35 | Mode-specific |
| tier3 | E4, E5, E6, E91, E92 | Framework adaptation + report/test-feature |
| tier4 | E8, E9, E12, E13, E16, E17, E18, E21, E22, E86, E87, E89, E94, E96, E98, E100 | Advanced |
| tier5 | E23, E24, E25, E26, E88, E95, E97 | Discovery & context |
| tier6 | E27, E28, E29, E36-E43 | Fixer depth |
| tier7 | E30, E31, E32, E90 | Planner rigor |
| tier8 | E44-E51 | Deception detection (critical) |
| tier9 | E52-E56, E58-E60 | Deception detection (high) |
| tier10 | E57 | Deception detection (medium) |
| tier11 | E70–E74, E81–E83, E99, **E101–E104** | Mobile / Maestro / prod regressions |
| tier12 | E84, E85, E86, E87, E93 | Framework depth (Cypress/WDIO/mock) |
| tier13 | E88, E89, E94, E95, E96, E97, E98, E100 | Hygiene & structure |
| tier14 | E90, E91, E92 | Plan / report / test-feature |

## Troubleshooting

### E101–E113 — Prod regression evals (static stubs)

| Eval | Regression |
|------|------------|
| E101 | Maestro→WDIO locator translation |
| E102 | WDIO log says test ran — agent must not deny it |
| E103 | iOS port must not copy Android resource-id |
| E104 | User asked for one spec — command must use `--spec` |
| E105 | completeDocumentUpload root cause from hierarchy |
| E106 | Slowness — max 3 steps, inspect before grep/rerun |
| E107 | Fix upload selector without deleting other methods |
| E108 | Run-only `@mobile` — one wdio run, report pass/fail, no bash spiral |
| E109 | User names emulator 5554 — list_devices + pin, not 5556 |
| E113 | Suite already failed — inspect first, one spec fix + verify |

```bash
npx tsx agent-eval-fixtures/scripts/smoke-prod-regression.ts
npx tsx agent-eval-fixtures/scripts/grade-prod-regression.ts E102
DASHBOARD_OFFLINE=1 npx tsx agent-eval-fixtures/scripts/agent-evals-dashboard.ts E102
```

Requires valid `SUPATEST_API_KEY` against the API URL you use (local docker maps API to port **7400**, not 9090).

### "DASHBOARD_API_KEY environment variable is required"
Set the API key or run in offline mode:
```bash
export DASHBOARD_API_KEY="your-api-key"
# OR
export DASHBOARD_OFFLINE=1
```

### "Fixture not found for E{N}"
Ensure fixtures are generated:
```bash
cd cli && pnpm exec tsx ../agent-eval-fixtures/scripts/generate-fixtures.ts
```

### CLI not found
Ensure CLI dependencies are installed:
```bash
cd cli && pnpm install && pnpm build
```
