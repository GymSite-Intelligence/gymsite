import assert from 'node:assert/strict'
import {
  cartoBuscaEmbedUrl,
  influenceFeatureCollection,
  mapLibreStyle,
  recorteWkt,
  topViasToFeatureCollection,
} from './explorarIso.ts'

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

const claro = mapLibreStyle('claro')
assert.equal(mapLibreStyle('claro'), claro)
assert.ok(JSON.stringify(claro).includes('openstreetmap.org'))
assert.ok(JSON.stringify(claro).includes('gs-overlay-anchor'))
const escuro = mapLibreStyle('escuro')
assert.equal(mapLibreStyle('escuro'), escuro)
assert.ok(JSON.stringify(escuro).includes('openstreetmap.org'))
const sat = mapLibreStyle('satelite')
assert.equal(mapLibreStyle('satelite'), sat)
assert.ok(JSON.stringify(sat).includes('World_Imagery'))

const fc = topViasToFeatureCollection([
  { nome_via: 'Rua A', fluxo_score: 90, coords: [[-38.48, -3.74], [-38.49, -3.75]] },
  { nome_via: 'Sem linha', fluxo_score: 10 },
])
assert.equal(fc.features.length, 1)
assert.equal(fc.features[0].geometry.type, 'LineString')

const wkt = recorteWkt(-26.9, -48.65, '1km', 8)
assert.ok(wkt.startsWith('POLYGON(('))
assert.match(wkt, /POLYGON\(\(/)
const plain = cartoBuscaEmbedUrl('https://clausa.app.carto.com/map/abc', {
  lente: '1km',
})
assert.equal(plain, 'https://clausa.app.carto.com/map/abc')
const withPin = cartoBuscaEmbedUrl('https://clausa.app.carto.com/map/abc', {
  lat: -26.9,
  lng: -48.65,
  lente: '1km',
  search: 'Navegantes, centro',
})
assert.ok(withPin.includes('lat=-26.9'))
assert.ok(withPin.includes('layers=0%2C1') || withPin.includes('layers=0,1'))
assert.ok(withPin.includes('mask='))
assert.ok(withPin.includes('search='))

console.log('explorarIso camada ok')
