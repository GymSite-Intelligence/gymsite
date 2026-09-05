import { test, expect } from '@playwright/test'

async function openReport(page: import('@playwright/test').Page) {
  const relatorioId = process.env.E2E_RELATORIO_ID?.trim()
  if (relatorioId) {
    await page.goto(`/relatorios/${relatorioId}`)
    return
  }

  await page.goto('/relatorios')
  const reportLink = page
    .locator('a[href^="/relatorios/"]')
    .filter({ hasNotText: /novo|aguardando/i })
    .first()
  await expect(reportLink).toBeVisible({ timeout: 30_000 })
  await reportLink.click()
  await page.waitForURL(/\/relatorios\/[^/]+$/)
}

test.describe('report CAPEX strip', () => {
  test('hides Consórcio and Kit de Equipamentos', async ({ page }) => {
    await openReport(page)
    await expect(page.getByText(/Consórcio/i)).toHaveCount(0)
    await expect(page.getByText(/Kit de Equipamentos/i)).toHaveCount(0)
  })

  test('matches expected CAPEX when E2E_EXPECTED_CAPEX is set', async ({ page }) => {
    const expected = process.env.E2E_EXPECTED_CAPEX?.trim()
    test.skip(!expected, 'E2E_EXPECTED_CAPEX not set')

    await openReport(page)
    const capexKpi = page.locator('text=CAPEX mid').locator('xpath=ancestor::div[contains(@class,"rounded")]').first()
    await expect(capexKpi).toContainText(expected!)
  })
})
