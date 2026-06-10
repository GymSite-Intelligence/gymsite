/**
 * Config Maps JavaScript — chave via backend (nunca VITE_* no bundle).
 */
import { API_BASE } from '@/lib/supabase'

export interface MapsJsConfig {
  configured: boolean
  key: string
  map_id: string
}

let _cache: MapsJsConfig | null = null

function mapsJsConfigUrl(): string {
  const devBase = (import.meta.env.VITE_API_BASE as string | undefined)?.trim()
  if (import.meta.env.DEV && !devBase) {
    return '/api/config/maps-js'
  }
  const base = (devBase || API_BASE).replace(/\/$/, '')
  return `${base}/api/config/maps-js`
}

export async function fetchMapsJsConfig(): Promise<MapsJsConfig> {
  if (_cache) return _cache
  const res = await fetch(mapsJsConfigUrl(), {
    credentials: 'include',
  })
  if (!res.ok) {
    return { configured: false, key: '', map_id: '' }
  }
  const data = (await res.json()) as MapsJsConfig
  _cache = {
    configured: Boolean(data.configured && data.key),
    key: data.key ?? '',
    map_id: (data.map_id ?? '').trim(),
  }
  return _cache
}

/** Map ID do Vite (opcional) sobrescreve resposta do servidor. */
export function mapsMapIdFromEnv(): string {
  return (import.meta.env.VITE_GOOGLE_MAPS_MAP_ID as string | undefined)?.trim() ?? ''
}
