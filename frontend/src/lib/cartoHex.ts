import { API_BASE, supabase } from '@/lib/supabase'

export type HexCountOk = {
  n_academias: number
  hex: string
  cidade: string
  fonte: string
  gerado_em: string
  base: string
}

function parseDetail(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const d = (body as { detail: unknown }).detail
    if (typeof d === 'string') return d
  }
  return fallback
}

export async function fetchHexCount(lat: number, lng: number): Promise<HexCountOk> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  const base = API_BASE.replace(/\/$/, '')
  const res = await fetch(`${base}/api/carto/hex-count`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ lat, lng }),
  })
  const raw = await res.text()
  let body: Record<string, unknown> = {}
  try {
    body = JSON.parse(raw) as Record<string, unknown>
  } catch {
    body = {}
  }
  if (!res.ok) {
    if (res.status === 405) {
      throw new Error(
        'Essa busca ainda não está no servidor da internet. No PC, deixe a API local ligada (porta 8000) — o .env.local já aponta para ela.',
      )
    }
    throw new Error(parseDetail(body, raw || `erro ${res.status}`))
  }
  if (typeof body.n_academias !== 'number') {
    throw new Error('resposta sem contagem')
  }
  return body as HexCountOk
}
