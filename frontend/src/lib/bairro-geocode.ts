/**
 * Geocode bairro+cidade via backend (pin do mapa = localidade do relatório).
 */
import { API_BASE } from '@/lib/supabase'
import { localidadeKey } from '@/lib/map-fly-to'

export interface BairroCoords {
  lat: number
  lng: number
}

const mem = new Map<string, BairroCoords | null>()

function geocodeBaseUrl(): string {
  const devBase = (import.meta.env.VITE_API_BASE as string | undefined)?.trim()
  if (import.meta.env.DEV && !devBase) {
    return ''
  }
  return (devBase || API_BASE).replace(/\/$/, '')
}

function geocodeUrl(bairro: string, cidade: string, uf: string | null): string {
  const q = new URLSearchParams({
    bairro,
    cidade,
    ...(uf ? { uf } : {}),
  })
  return `${geocodeBaseUrl()}/api/geocode/bairro?${q.toString()}`
}

const GEOCODE_TIMEOUT_MS = 12_000

async function fetchWithTimeout(
  url: string,
  init?: RequestInit,
): Promise<Response> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), GEOCODE_TIMEOUT_MS)
  try {
    return await fetch(url, { ...init, signal: ctrl.signal })
  } finally {
    clearTimeout(timer)
  }
}

export async function fetchBairroCoords(
  bairro: string,
  cidade: string,
  uf: string | null | undefined,
): Promise<BairroCoords | null> {
  const key = localidadeKey(bairro, cidade)
  if (mem.has(key)) return mem.get(key) ?? null

  const res = await fetchWithTimeout(geocodeUrl(bairro, cidade, uf ?? null), {
    credentials: 'include',
  })
  if (!res.ok) {
    mem.set(key, null)
    return null
  }
  const data = (await res.json()) as { lat?: number; lng?: number; error?: string }
  if (data.error || typeof data.lat !== 'number' || typeof data.lng !== 'number') {
    mem.set(key, null)
    return null
  }
  const coords = { lat: data.lat, lng: data.lng }
  mem.set(key, coords)
  return coords
}

export async function fetchBairroCoordsBatch(
  items: Array<{ bairro: string; cidade: string; uf: string | null | undefined }>,
): Promise<Map<string, BairroCoords>> {
  const unique: Array<{
    key: string
    bairro: string
    cidade: string
    uf: string | null | undefined
  }> = []
  const seen = new Set<string>()
  for (const it of items) {
    const key = localidadeKey(it.bairro, it.cidade)
    if (seen.has(key)) continue
    seen.add(key)
    unique.push({ key, bairro: it.bairro, cidade: it.cidade, uf: it.uf })
  }

  const results = await Promise.all(
    unique.map(async ({ key, bairro, cidade, uf }) => {
      const c = await fetchBairroCoords(bairro, cidade, uf)
      return { key, c }
    }),
  )

  const out = new Map<string, BairroCoords>()
  for (const { key, c } of results) {
    if (c) out.set(key, c)
  }
  return out
}
