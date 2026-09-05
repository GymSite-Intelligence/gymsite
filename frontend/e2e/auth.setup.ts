import { mkdir } from 'node:fs/promises'
import { test as setup, expect } from '@playwright/test'

const AUTH_DIR = 'e2e/.auth'

function requireEnv(name: string): string {
  const value = process.env[name]?.trim()
  if (!value) {
    throw new Error(
      `Missing required E2E env var ${name}. ` +
        'Set E2E_USER_EMAIL, E2E_USER_PASSWORD, E2E_ADMIN_EMAIL, E2E_ADMIN_PASSWORD. ' +
        'Optional: E2E_BASE_URL, E2E_RELATORIO_ID, E2E_EXPECTED_CAPEX.',
    )
  }
  return value
}

async function loginAndSave(
  page: import('@playwright/test').Page,
  email: string,
  password: string,
  storagePath: string,
) {
  await page.goto('/login')
  await page.getByPlaceholder('voce@empresa.com').fill(email)
  await page.getByPlaceholder('Sua senha').fill(password)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await page.waitForURL(/\/(relatorios|dashboard)/, { timeout: 30_000 })
  await expect(page.locator('[data-sidebar="sidebar"]')).toBeVisible()
  await page.context().storageState({ path: storagePath })
}

setup('authenticate tenant', async ({ page }) => {
  const email = requireEnv('E2E_USER_EMAIL')
  const password = requireEnv('E2E_USER_PASSWORD')
  await mkdir(AUTH_DIR, { recursive: true })
  await loginAndSave(page, email, password, `${AUTH_DIR}/tenant.json`)
})

setup('authenticate admin', async ({ page }) => {
  const email = requireEnv('E2E_ADMIN_EMAIL')
  const password = requireEnv('E2E_ADMIN_PASSWORD')
  await mkdir(AUTH_DIR, { recursive: true })
  await loginAndSave(page, email, password, `${AUTH_DIR}/admin.json`)
})
