import assert from 'node:assert/strict'
import { parseLugarExplorar, ufFromText } from './ufs-brasil.ts'

assert.equal(ufFromText('Centro, Navegantes, SC'), 'SC')
assert.equal(ufFromText('Centro, Navegantes, sc'), 'SC')
assert.equal(ufFromText('Centro, Navegantes, Santa Catarina'), 'SC')
assert.equal(ufFromText('Centro, Pirapora, MG'), 'MG')

const scSigla = parseLugarExplorar('Centro, Navegantes, SC')
assert.equal(scSigla.bairro, 'Centro')
assert.equal(scSigla.cidade, 'Navegantes')
assert.equal(scSigla.uf, 'SC')

const scNome = parseLugarExplorar('Centro, Navegantes, Santa Catarina')
assert.equal(scNome.bairro, 'Centro')
assert.equal(scNome.cidade, 'Navegantes')
assert.equal(scNome.uf, 'SC')

const trailing = parseLugarExplorar('Centro, Navegantes SC')
assert.equal(trailing.cidade, 'Navegantes')
assert.equal(trailing.uf, 'SC')

console.log('ufs-brasil parse ok')
