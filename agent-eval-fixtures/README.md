# Agent Eval Fixtures

This directory contains **31 self-contained fixtures** for agent evals. Each fixture represents a specific evaluation scenario that can be run independently using the Supatest CLI.

## Directory Structure

```
agent-eval-fixtures/
├── README.md
├── scripts/
│   ├── generate-fixtures.ts      # Generate fixture directories from base templates
│   ├── capture-failure-logs.ts   # Capture test failure logs for fix-mode evals
│   └── validate-fixtures.ts      # Validate all fixtures have required files
├── base-templates/
│   ├── playwright-ts-full/       # Full Playwright + TypeScript project with page objects
│   ├── playwright-ts-blank/      # Minimal Playwright + TypeScript project
│   └── wdio-ts-full/             # Full WebdriverIO + TypeScript project
└── fixtures/
    ├── E1/
    │   ├── project/              # The test project (copied from base template)
    │   └── fixture.json          # Eval metadata (id, name, mode, task)
    ├── E14/
    │   ├── project/              # Project with intentionally broken tests
    │   ├── failure.log           # Captured test failure output
    │   └── fixture.json
    └── ...
```

## Setup

Install dependencies for each fixture you want to run:

```bash
cd agent-eval-fixtures/fixtures/E3/project
npm install
```

Or install for all fixtures:

```bash
for dir in agent-eval-fixtures/fixtures/*/project; do
  (cd "$dir" && npm install)
done
```

## Running Evals

All evals are run using the Supatest CLI in development mode. The CLI must be run from the `cli/` directory.

### Build Mode (Discovery Evals)

Build mode is for evals where the agent discovers and writes new tests.

```bash
cd cli && NODE_ENV=development npx tsx src/index.ts "<task>" \
  --headless --mode build \
  --cwd /path/to/agent-eval-fixtures/fixtures/E{N}/project \
  --verbose
```

**Example: E3 (Discovery eval)**

```bash
cd cli && NODE_ENV=development npx tsx src/index.ts "Write a test that verifies the user can add a product to the cart" \
  --headless --mode build \
  --cwd /Users/prasad/Documents/code/supatest/agent-eval-fixtures/fixtures/E3/project \
  --verbose
```

### Fix Mode (Debugging Evals)

Fix mode is for evals where the agent must fix failing tests. Requires the `--logs` flag pointing to the failure log.

```bash
cd cli && NODE_ENV=development npx tsx src/index.ts "Fix the failing tests" \
  --headless --mode fix \
  --logs /path/to/agent-eval-fixtures/fixtures/E{N}/failure.log \
  --cwd /path/to/agent-eval-fixtures/fixtures/E{N}/project \
  --verbose
```

**Example: E14 (Fix mode with failure.log)**

```bash
cd cli && NODE_ENV=development npx tsx src/index.ts "Fix the failing tests" \
  --headless --mode fix \
  --logs /Users/prasad/Documents/code/supatest/agent-eval-fixtures/fixtures/E14/failure.log \
  --cwd /Users/prasad/Documents/code/supatest/agent-eval-fixtures/fixtures/E14/project \
  --verbose
```

### Plan Mode

Plan mode is for evals where the agent creates a test plan without executing tests.

```bash
cd cli && NODE_ENV=development npx tsx src/index.ts "<task>" \
  --headless --mode plan \
  --cwd /path/to/agent-eval-fixtures/fixtures/E{N}/project \
  --verbose
```

**Example: E19 (Plan mode)**

```bash
cd cli && NODE_ENV=development npx tsx src/index.ts "Create a test plan for the checkout flow" \
  --headless --mode plan \
  --cwd /Users/prasad/Documents/code/supatest/agent-eval-fixtures/fixtures/E19/project \
  --verbose
```

## Regenerating Fixtures

To regenerate fixtures from base templates:

```bash
cd agent-eval-fixtures/scripts
npx tsx generate-fixtures.ts
```

To regenerate a specific fixture:

```bash
npx tsx generate-fixtures.ts E14
```

## Capturing Failure Logs

Fix-mode evals (E14, E15, E16, E27, E28, E29) require a `failure.log` file that contains the actual test failure output. To capture/update these logs:

```bash
cd agent-eval-fixtures/scripts

# Capture all fix-mode eval logs
npx tsx capture-failure-logs.ts

# Capture for a specific eval
npx tsx capture-failure-logs.ts E14
```

This script will:

1. Install dependencies in the fixture's project directory
2. Run the tests (expecting them to fail)
3. Save the failure output to `failure.log`

## Validating Fixtures

To validate that all fixtures have the required files:

```bash
cd agent-eval-fixtures/scripts
npx tsx validate-fixtures.ts
```

This checks:

- `fixture.json` exists and has required fields (evalId, name, mode, task)
- `project/` directory exists with a valid `package.json`
- `failure.log` exists for fix-mode evals

## Eval Modes Summary

| Eval IDs | Mode  | Description                                                     |
| -------- | ----- | --------------------------------------------------------------- |
| E1-E13   | build | Write new tests based on task description                       |
| E14-E16  | fix   | Fix failing tests using failure.log                             |
| E17-E18  | build | Additional build mode evals                                     |
| E19-E26  | plan  | Create test plans without execution                             |
| E27-E29  | fix   | Additional fix mode evals                                       |
| E30-E32  | build | Advanced build mode evals                                       |
| E78      | build | Context-first: write from page objects without over-exploration |
| E79      | fix   | Fix spurious page.close() in afterEach causing Target closed    |
| E80      | fix   | Fix silent try/catch shouldContinue error swallowing            |

## fixture.json Schema

Each fixture contains a `fixture.json` with the following structure:

```json
{
  "evalId": "E14",
  "name": "Fix broken login test selector",
  "mode": "fix",
  "task": "Fix the failing tests",
  "baseTemplate": "playwright-ts-full",
  "expectedOutcome": "Login test passes with corrected selector"
}
```

## Notes

- All paths in CLI commands should be absolute paths
- The `--headless` flag runs the browser in headless mode
- The `--verbose` flag enables detailed logging
- Fix mode evals must have broken code in the project that causes test failures
- The `failure.log` must reflect the actual failure from the broken code
