export type ExplorarAutocompleteListKind =
  | 'hidden'
  | 'loading'
  | 'empty'
  | 'results'
  | 'error'

export function explorarAutocompleteBody(
  q: string,
  lat?: number,
  lng?: number,
): { q: string; lat?: number; lng?: number } {
  const body: { q: string; lat?: number; lng?: number } = { q }
  if (lat != null && lng != null) {
    body.lat = lat
    body.lng = lng
  }
  return body
}

export function explorarAutocompleteQueryKey(
  q: string,
  lat?: number,
  lng?: number,
): readonly [string, string, string, string] {
  const keyQ = q.trim().toLowerCase()
  if (lat != null && lng != null) {
    return ['explorar-endereco', keyQ, lat.toFixed(3), lng.toFixed(3)]
  }
  return ['explorar-endereco', keyQ, '', '']
}

export function explorarAutocompleteListKind(opts: {
  query: string
  debounced: string
  isFetching: boolean
  suggestionCount: number
  isError: boolean
}): ExplorarAutocompleteListKind {
  const q = opts.query.trim()
  if (q.length < 3) return 'hidden'
  if (q !== opts.debounced.trim() || opts.isFetching) return 'loading'
  if (opts.isError) return 'error'
  if (opts.suggestionCount === 0) return 'empty'
  return 'results'
}
