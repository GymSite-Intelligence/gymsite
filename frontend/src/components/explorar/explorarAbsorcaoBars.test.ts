import assert from 'node:assert/strict'
import { explorarBarPercents, explorarIntPt } from './explorarAbsorcaoBars.ts'

assert.deepEqual(explorarBarPercents([0, 0, 0]), [0, 0, 0])
assert.deepEqual(explorarBarPercents([2100, 14200, 8400]), [15, 100, 59])
assert.deepEqual(explorarBarPercents([-100, 50]), [0, 100])
assert.equal(explorarIntPt(2100), '2.100')
assert.equal(explorarIntPt(null), '—')
assert.equal(explorarIntPt(undefined), '—')

console.log('explorarAbsorcaoBars ok')
