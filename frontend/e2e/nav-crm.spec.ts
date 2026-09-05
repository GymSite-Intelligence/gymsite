import { test, expect } from '@playwright/test'

const HIDDEN_NAV = ['Mapa', 'Market Atlas', 'Assistente', 'Provedor de IA'] as const
const TENANT_NAV = ['CRM', 'Hex CARTO', 'Obras CNO'] as const

function sidebar(page: import('@playwright/test').Page) {
  return page.locator('[data-sidebar="sidebar"]')
}

test.describe('tenant sidebar', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard')
    await expect(sidebar(page)).toBeVisible()
  })

  test('hides deprecated nav items and shows CRM Hex CNO', async ({ page }) => {
    const nav = sidebar(page)
    for (const label of HIDDEN_NAV) {
      await expect(nav.getByRole('link', { name: label })).toHaveCount(0)
      await expect(nav.getByText(label, { exact: true })).toHaveCount(0)
    }
    for (const label of TENANT_NAV) {
      await expect(nav.getByRole('link', { name: label })).toBeVisible()
    }
  })

  test('visits /crm and legacy /mapa route', async ({ page }) => {
    await page.goto('/crm')
    await expect(page).toHaveURL(/\/crm/)
    await expect(page.getByRole('heading', { name: 'CRM' })).toBeVisible()

    const mapaResponse = await page.goto('/mapa')
    expect(mapaResponse?.status()).toBe(200)
    await expect(page).toHaveURL(/\/mapa/)
  })
})

test.describe('admin sidebar', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard')
    await expect(sidebar(page)).toBeVisible()
  })

  test('shows Custos and hides Provedor de IA', async ({ page }) => {
    const nav = sidebar(page)
    await expect(nav.getByRole('link', { name: 'Custos' })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Provedor de IA' })).toHaveCount(0)
    await expect(nav.getByText('Provedor de IA', { exact: true })).toHaveCount(0)
  })
})
