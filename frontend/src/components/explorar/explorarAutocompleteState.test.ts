import assert from 'node:assert/strict'
import {
  explorarAutocompleteBody,
  explorarAutocompleteListKind,
  explorarAutocompleteQueryKey,
} from './explorarAutocompleteState.ts'

assert.deepEqual(explorarAutocompleteBody('Bessa'), { q: 'Bessa' })
assert.deepEqual(explorarAutocompleteBody('Bessa', -3.74, -38.48), {
  q: 'Bessa',
  lat: -3.74,
  lng: -38.48,
})

assert.doesNotThrow(() => explorarAutocompleteQueryKey('Bessa'))
assert.deepEqual([...explorarAutocompleteQueryKey('Bessa')], [
  'explorar-endereco',
  'bessa',
  '',
  '',
])
assert.deepEqual(
  [...explorarAutocompleteQueryKey('Bessa', -7.0666675, -34.8436065)],
  ['explorar-endereco', 'bessa', '-7.067', '-34.844'],
)

assert.equal(
  explorarAutocompleteListKind({
    query: 'Bessa',
    debounced: '',
    isFetching: false,
    suggestionCount: 0,
    isError: false,
  }),
  'loading',
)
assert.equal(
  explorarAutocompleteListKind({
    query: 'Bessa',
    debounced: 'Bessa',
    isFetching: true,
    suggestionCount: 0,
    isError: false,
  }),
  'loading',
)
assert.equal(
  explorarAutocompleteListKind({
    query: 'Bessa',
    debounced: 'Bessa',
    isFetching: false,
    suggestionCount: 0,
    isError: false,
  }),
  'empty',
)
assert.equal(
  explorarAutocompleteListKind({
    query: 'Bessa',
    debounced: 'Bessa',
    isFetching: false,
    suggestionCount: 2,
    isError: false,
  }),
  'results',
)
assert.equal(
  explorarAutocompleteListKind({
    query: 'Bessa',
    debounced: 'Bessa',
    isFetching: false,
    suggestionCount: 0,
    isError: true,
  }),
  'error',
)
assert.equal(
  explorarAutocompleteListKind({
    query: 'Be',
    debounced: 'Be',
    isFetching: false,
    suggestionCount: 0,
    isError: false,
  }),
  'hidden',
)

console.log('explorarAutocompleteState ok')
