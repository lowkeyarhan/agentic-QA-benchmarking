import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  use: {
    baseURL: 'http://localhost:3002',
    headless: true,
  },
  webServer: {
    command: 'npx http-server -p 3002',
    port: 3002,
    reuseExistingServer: true,
  },
});
