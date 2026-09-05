import { test, expect } from '@playwright/test'

test('consultor page renders especialistas shell', async ({ page }) => {
  await page.goto('/consultor')
  await expect(page.getByTestId('especialistas-shell')).toBeVisible({ timeout: 30_000 })
})

test('degustacao shell on public page', async ({ page }) => {
  await page.goto('/degustacao')
  await expect(page.getByTestId('especialistas-shell')).toBeVisible({ timeout: 30_000 })
})
