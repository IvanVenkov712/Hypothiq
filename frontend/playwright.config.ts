import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './test',
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    channel: process.platform === 'win32' ? 'msedge' : undefined,
    viewport: { width: 1280, height: 960 },
    // Daily bar labels must stay the same even west of UTC.
    timezoneId: 'America/Los_Angeles',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 4173 --strictPort',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: !process.env.CI,
  },
})
