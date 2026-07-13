import { useQuery } from '@tanstack/react-query'
import { API_BASE } from '@/lib/supabase'

export interface FluxoCarimbo {
  valor?: number
  base?: string
  fonte?: string
  janela?: string
  metodo?: string
  confianca?: string
  segmento?: string
}

export interface FluxoPedestrePayload {
  success: boolean
  confianca?: string
  fluxo_score_candidato?: number | null
  carimbo?: FluxoCarimbo
  statistics?: Record<string, number>
  geojson?: {
    type: string
    features?: Array<{
      type: string
      geometry: { type: string; coordinates: unknown }
      properties?: Record<string, unknown>
    }>
  }
  top_segments?: Array<Record<string, unknown>>
  attribution?: string
  motivo?: string
  from_cache?: boolean
}

function fluxoPedestreUrl(relatorioId: string, raioM = 2000): string {
  const base = API_BASE.replace(/\/$/, '')
  return `${base}/api/relatorios/${encodeURIComponent(relatorioId)}/fluxo-pedestre?raio_m=${raioM}`
}

export function useFluxoPedestre(relatorioId: string | undefined, enabled = true, raioM = 2000) {
  return useQuery({
    queryKey: ['fluxo-pedestre', relatorioId, raioM],
    enabled: Boolean(relatorioId) && enabled,
    queryFn: async (): Promise<FluxoPedestrePayload> => {
      const res = await fetch(fluxoPedestreUrl(relatorioId!, raioM), {
        credentials: 'include',
      })
      if (!res.ok) {
        const err = await res.text().catch(() => '')
        throw new Error(err || `fluxo-pedestre HTTP ${res.status}`)
      }
      return (await res.json()) as FluxoPedestrePayload
    },
    staleTime: 5 * 60_000,
    retry: 1,
  })
}

export function flowScoreColor(score: number): string {
  if (score >= 0.7) return '#84cc01'
  if (score >= 0.4) return '#f59e0b'
  return '#64748b'
}
