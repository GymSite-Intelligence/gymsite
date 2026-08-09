/** URLs canônicas — same-origin em www.gymsite.com.br. */

export const APP_ORIGIN =
  typeof window !== 'undefined' ? window.location.origin : 'https://www.gymsite.com.br'

export function explorarHref(): string {
  return '/explorar'
}

export function appLoginHref(): string {
  return '/login'
}

export type DegustacaoSearch = {
  agente?: string
  abrir?: 'formulario'
  dev_token?: string
  pid?: string
}

export function degustacaoHref(search: DegustacaoSearch = {}): string {
  const p = new URLSearchParams()
  if (search.agente) p.set('agente', search.agente)
  if (search.abrir) p.set('abrir', search.abrir)
  if (search.dev_token) p.set('dev_token', search.dev_token)
  const q = p.toString()
  return `/degustacao${q ? `?${q}` : ''}`
}

export function legacyAbrirToDegustacaoSearch(
  params: URLSearchParams,
): DegustacaoSearch | null {
  const abrir = params.get('abrir')
  if (
    abrir !== 'diagnostico-interno' &&
    abrir !== 'chat' &&
    abrir !== 'analise' &&
    abrir !== 'formulario'
  ) {
    return null
  }
  const next: DegustacaoSearch = {}
  if (abrir === 'analise' || abrir === 'formulario') next.abrir = 'formulario'
  const agente = params.get('agente')
  if (agente) next.agente = agente
  const dev = params.get('dev_token')
  if (dev) next.dev_token = dev
  return next
}

export function parseDegustacaoSearch(
  search: Record<string, unknown>,
): DegustacaoSearch {
  return {
    agente: typeof search.agente === 'string' ? search.agente : undefined,
    abrir: search.abrir === 'formulario' ? ('formulario' as const) : undefined,
    dev_token: typeof search.dev_token === 'string' ? search.dev_token : undefined,
    pid: typeof search.pid === 'string' ? search.pid : undefined,
  }
}

export function legacyAbrirToDegustacaoSearchFromRecord(
  search: Record<string, unknown>,
): DegustacaoSearch | null {
  const params = new URLSearchParams()
  if (typeof search.abrir === 'string') params.set('abrir', search.abrir)
  if (typeof search.agente === 'string') params.set('agente', search.agente)
  if (typeof search.dev_token === 'string') params.set('dev_token', search.dev_token)
  return legacyAbrirToDegustacaoSearch(params)
}
