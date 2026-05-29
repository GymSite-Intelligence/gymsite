import { test, expect } from '@playwright/test'

test('capture console errors on dashboard', async ({ page }) => {
  const errors: string[] = []
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text())
    }
  })
  page.on('pageerror', err => {
    errors.push(err.message)
  })

  await page.goto('http://localhost:5174/dashboard')
  await page.waitForTimeout(8000)

  console.log('ERRORS:', JSON.stringify(errors, null, 2))
  expect(errors).toHaveLength(0)
})
