import { defineConfig, devices } from '@playwright/test';

// This browser-only TS project does not include the Node ambient types.
declare const process: { env: Record<string, string | undefined> };

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5199/decision-model-agent-demo/', trace: 'retain-on-failure',
    ...(process.env.PLAYWRIGHT_CHANNEL ? {
      channel: process.env.PLAYWRIGHT_CHANNEL,
      launchOptions: { args: ['--hide-crash-restore-bubble', '--disable-session-crashed-bubble'] },
    } : {}),
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run dev -- --port 5199 --strictPort',
    url: 'http://127.0.0.1:5199/decision-model-agent-demo/',
    reuseExistingServer: false,
  },
});
