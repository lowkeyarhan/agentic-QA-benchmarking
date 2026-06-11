# Supatest Reporter Integration

This project is integrated with the Supatest Playwright reporter for real-time test result streaming to the Supatest dashboard.

## Setup

### 1. Install Dependencies

The local Supatest reporter is already installed from:
```
../supatest/playwright-reporter
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
# Required: Your Supatest API key
SUPATEST_API_KEY=sk_live_your_api_key_here

# Required: Your Supatest project ID
SUPATEST_PROJECT_ID=proj_your_project_id_here

# Optional: Custom API URL (for local development)
SUPATEST_API_URL=http://localhost:3000

# Optional: Enable dry run mode (tests run but data isn't uploaded)
SUPATEST_DRY_RUN=false
```

### 3. Get API Credentials

#### For Local Development:

1. Start your local Supatest API server
2. Use `http://localhost:3000` as `SUPATEST_API_URL`
3. Get your API key and project ID from the local dashboard

#### For Production:

1. Go to [Supatest Dashboard](https://supatest.dev)
2. Create a project or use an existing one
3. Copy your API key from project settings
4. Copy your project ID from the project URL

## Usage

### Run Tests with Supatest Reporter

```bash
# Run all tests (automatically uses .env configuration)
npm test

# Run specific browser
npm test -- --project=chromium

# Run specific test file
npm test -- tests/auth.spec.ts

# Run tests matching a pattern
npm test -- --grep "@smoke"
```

### Dry Run Mode

To test without uploading data:

```bash
# Set dry run in .env
SUPATEST_DRY_RUN=true

# Or override via command line
SUPATEST_DRY_RUN=true npm test
```

### Disable Reporter Temporarily

To run tests without the Supatest reporter:

```bash
# Remove or rename .env file temporarily
mv .env .env.bak

# Or unset the API key
SUPATEST_API_KEY="" npm test
```

## Configuration Options

The reporter is configured in `playwright.config.ts`:

```typescript
[
  '@supatest/playwright-reporter',
  {
    apiKey: process.env.SUPATEST_API_KEY,        // Required
    projectId: process.env.SUPATEST_PROJECT_ID,  // Required
    apiUrl: process.env.SUPATEST_API_URL,        // Optional (defaults to https://api.supatest.dev)
    uploadAssets: true,                           // Upload screenshots/videos/traces
    maxConcurrentUploads: 5,                      // Max parallel uploads
    retryAttempts: 3,                             // Upload retry attempts
    timeoutMs: 30000,                            // Upload timeout
    dryRun: process.env.SUPATEST_DRY_RUN === 'true', // Test mode
  }
]
```

## Features

### Automatic Data Collection

- **Test Results**: Status, duration, retries, flaky detection
- **Test Steps**: Nested step hierarchy with timing
- **Errors**: Stack traces and failure details
- **Console Output**: stdout/stderr during tests
- **Attachments**: Screenshots, videos, traces

### Environment Context

- OS information (platform, architecture, RAM)
- Node.js version
- Playwright configuration
- Browser details per project
- CI/CD detection (GitHub Actions, GitLab, Jenkins, etc.)
- Git context (branch, commit, author, message)

### Performance

- Non-blocking uploads (tests continue while uploading)
- Concurrent uploads (configurable)
- Automatic retry with exponential backoff
- Graceful error handling (upload failures don't block tests)

## Updating the Reporter

To update to the latest version of the local reporter:

```bash
# Rebuild the reporter in the supatest directory
cd ../supatest/playwright-reporter
pnpm build

# Reinstall in this project
cd ../saucedemo-playwright
npm install ../supatest/playwright-reporter
```

## Troubleshooting

### Reporter Not Uploading

1. Check that `.env` file exists and is configured
2. Verify `SUPATEST_API_KEY` and `SUPATEST_PROJECT_ID` are set
3. Check API URL is accessible:
   ```bash
   curl $SUPATEST_API_URL/health
   ```
4. Enable dry run to test configuration:
   ```bash
   SUPATEST_DRY_RUN=true npm test
   ```

### Environment Variables Not Loading

1. Ensure `.env` is in the project root
2. Check that `dotenv.config()` is called in `playwright.config.ts`
3. Try loading explicitly:
   ```bash
   NODE_ENV=development npm test
   ```

### Upload Failures

1. Check network connectivity to API URL
2. Verify API key is valid and has upload permissions
3. Check file size limits (traces can be large)
4. Review reporter logs for specific errors
5. Try increasing `timeoutMs` or `retryAttempts`

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps

      - name: Run tests
        env:
          SUPATEST_API_KEY: ${{ secrets.SUPATEST_API_KEY }}
          SUPATEST_PROJECT_ID: ${{ secrets.SUPATEST_PROJECT_ID }}
          SUPATEST_API_URL: https://api.supatest.dev
        run: npm test
```

Add secrets in GitHub repository settings:
- `SUPATEST_API_KEY`
- `SUPATEST_PROJECT_ID`

### GitLab CI Example

```yaml
test:
  script:
    - npm ci
    - npx playwright install --with-deps
    - npm test
  variables:
    SUPATEST_API_KEY: $SUPATEST_API_KEY
    SUPATEST_PROJECT_ID: $SUPATEST_PROJECT_ID
    SUPATEST_API_URL: https://api.supatest.dev
```

## Support

For issues or questions:
- GitHub Issues: [supatest-ai/supatest](https://github.com/supatest-ai/supatest/issues)
- Documentation: [supatest.dev](https://supatest.dev)
