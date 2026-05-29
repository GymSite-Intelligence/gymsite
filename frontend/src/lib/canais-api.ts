/**
 * Run now — probes por canal antes do pipeline completo.
 */
import { API_BASE, supabase } from '@/lib/supabase'

export type CanalId = 'places' | 'osm' | 'cnpj' | 'kimi'

export interface CanalProbePayload {
  cidade: string
  bairro: string
  uf?: string | null
  tipo_negocio?: string
  publico_alvo?: string
  raio_metros?: number
}

export interface CanalProbeResult {
  canal: string
  ok: boolean
  erro?: string | null
  total?: number
  fonte_busca_competidores?: string
  fonte_geocode?: string
  tier?: string
  preview_markdown?: string
  fontes_count?: number
  openclaw_configured?: boolean
  amostra?: unknown[]
  [key: string]: unknown
}

const CANAL_PATH: Record<CanalId, string> = {
  places: '/api/canais/places',
  osm: '/api/canais/osm',
  cnpj: '/api/canais/cnpj',
  kimi: '/api/canais/kimi-research',
}

async function authHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const {
    data: { session },
  } = await supabase.auth.getSession()
  if (session?.access_token) {
    headers.Authorization = `Bearer ${session.access_token}`
  }
  return headers
}

export async function runCanalProbe(
  canal: CanalId,
  payload: CanalProbePayload,
): Promise<CanalProbeResult> {
  const res = await fetch(`${API_BASE}${CANAL_PATH[canal]}`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify({
      cidade: payload.cidade,
      bairro: payload.bairro,
      uf: payload.uf ?? undefined,
      tipo_negocio: payload.tipo_negocio ?? 'academia',
      publico_alvo: payload.publico_alvo ?? 'premium',
      raio_metros: payload.raio_metros ?? 3000,
    }),
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`Canal ${canal}: HTTP ${res.status} — ${body.slice(0, 200)}`)
  }
  return (await res.json()) as CanalProbeResult
}

export async function fetchCanaisStatus(): Promise<{
  kimi_provider_ativo: boolean
  openclaw_configured: boolean
  maps_ok: boolean
}> {
  const res = await fetch(`${API_BASE}/api/canais/status`)
  if (!res.ok) return { kimi_provider_ativo: false, openclaw_configured: false, maps_ok: false }
  const data = (await res.json()) as Record<string, boolean>
  return {
    kimi_provider_ativo: !!data.kimi_provider_ativo,
    openclaw_configured: !!data.openclaw_configured,
    maps_ok: !!data.maps_ok,
  }
}
