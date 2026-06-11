import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';

// Load environment variables from .env file
dotenv.config();

// Build reporters array
const reporters: any[] = [['html']];

// Add Supatest reporter if API key is configured
if (process.env.SUPATEST_API_KEY) {
  reporters.push([
    '@supatest/playwright-reporter',
    {
      apiKey: process.env.SUPATEST_API_KEY,
      projectId: process.env.SUPATEST_PROJECT_ID,
      apiUrl: process.env.SUPATEST_API_URL || 'https://api.supatest.dev',
      uploadAssets: true,
      maxConcurrentUploads: 5,
      retryAttempts: 3,
      timeoutMs: 30000,
      dryRun: process.env.SUPATEST_DRY_RUN === 'true',
    },
  ]);
}

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: reporters,
  use: {
    baseURL: 'https://www.saucedemo.com',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
});
