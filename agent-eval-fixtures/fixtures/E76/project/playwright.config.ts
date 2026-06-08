import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  use: {
    baseURL: 'http://localhost:3001',
    headless: true,
  },
  webServer: {
    command: 'npx http-server -p 3001',
    port: 3001,
    reuseExistingServer: true,
  },
});
