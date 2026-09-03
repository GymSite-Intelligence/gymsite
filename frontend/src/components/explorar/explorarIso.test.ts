import assert from 'node:assert/strict'
import { influenceFeatureCollection, tileProvider } from './explorarIso.ts'

const iso = {
  m5: [[-7.06, -34.84], [-7.07, -34.84], [-7.07, -34.85]] as [number, number][],
}

const bairro = influenceFeatureCollection(-7.067, -34.844, 'bairro', iso)
assert.equal(
  bairro.features.some((f) => f.properties?.key === 'lente'),
  false,
)
assert.equal(
  bairro.features.some((f) => f.properties?.key === 'm5'),
  true,
)

const umKm = influenceFeatureCollection(-7.067, -34.844, '1km', iso)
assert.equal(
  umKm.features.some((f) => f.properties?.key === 'lente'),
  true,
)

const claroUrl = tileProvider('claro')(100, 50, 12)
assert.ok(claroUrl.includes('tile.openstreetmap.org'))
assert.ok(!claroUrl.includes('basemaps.cartocdn.com'))

console.log('explorarIso camada ok')
