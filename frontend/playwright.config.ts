import { defineConfig, devices } from '@playwright/test'

const baseURL = process.env.E2E_BASE_URL ?? 'https://gymsite.com.br'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['list']],
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    ...devices['Desktop Chrome'],
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    {
      name: 'tenant',
      testMatch: /nav-crm\.spec\.ts|relatorio-capex\.spec\.ts|consultor-shell\.spec\.ts/,
      grep: /tenant sidebar|visits \/crm|report CAPEX|consultor page/,
      use: { storageState: 'e2e/.auth/tenant.json' },
      dependencies: ['setup'],
    },
    {
      name: 'admin',
      testMatch: /nav-crm\.spec\.ts/,
      grep: /admin sidebar/,
      use: { storageState: 'e2e/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'public',
      testMatch: /consultor-shell\.spec\.ts/,
      grep: /degustacao shell/,
      use: { storageState: { cookies: [], origins: [] } },
      dependencies: ['setup'],
    },
  ],
})
