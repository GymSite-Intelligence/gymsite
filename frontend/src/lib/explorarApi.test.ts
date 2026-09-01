import assert from 'node:assert/strict'
import { isLoopbackApi } from './explorarApi.ts'

assert.equal(isLoopbackApi('http://127.0.0.1:8000'), true)
assert.equal(isLoopbackApi('http://localhost:5174'), true)
assert.equal(isLoopbackApi('https://api.getgymsite.com.br'), false)

console.log('explorarApi ok')
