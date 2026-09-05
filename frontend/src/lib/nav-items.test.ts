import assert from 'node:assert/strict'
import { test } from 'node:test'
import { getSidebarNavItems } from './nav-items.ts'

test('tenant menu hides mapa atlas assistente llm', () => {
  const tos = getSidebarNavItems(false).map((i) => i.to)
  for (const bad of ['/mapa', '/market-atlas', '/assistente', '/admin/llm', '/custos']) {
    assert.equal(tos.includes(bad), false, bad)
  }
  assert.equal(tos.includes('/crm'), true)
  assert.equal(tos.includes('/carto-hex'), true)
  assert.equal(tos.includes('/cno-obras'), true)
  assert.equal(tos.includes('/consultor'), true)
})

test('admin menu adds only custos', () => {
  const tos = getSidebarNavItems(true).map((i) => i.to)
  assert.equal(tos.includes('/custos'), true)
  assert.equal(tos.includes('/admin/llm'), false)
})
