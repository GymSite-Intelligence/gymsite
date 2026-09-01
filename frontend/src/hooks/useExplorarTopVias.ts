import { useQuery } from '@tanstack/react-query'
import { fetchExplorar } from '@/lib/explorarApi'

export type ExplorarTopVia = {
  nome_via?: string
  fluxo_score?: number
  coords?: [number, number][]
  fluxo_carimbo?: Record<string, unknown>
}

export type ExplorarTopViasResult = {
  status: 'ok' | 'indisponivel'
  top_vias: ExplorarTopVia[]
  confianca?: string
}

async function fetchTopVias(
  lat: number,
  lng: number,
  bairro: string | undefined,
): Promise<ExplorarTopViasResult> {
  try {
    const res = await fetchExplorar('/api/explorar/top-vias', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lng, bairro }),
    })
    if (!res.ok) {
      return { status: 'indisponivel', top_vias: [] }
    }
    return (await res.json()) as ExplorarTopViasResult
  } catch {
    return { status: 'indisponivel', top_vias: [] }
  }
}

export function useExplorarTopVias(
  pin: { lat: number; lng: number } | null,
  bairro: string | undefined,
  enabled: boolean,
) {
  return useQuery({
    queryKey: ['explorar-top-vias', pin?.lat, pin?.lng, bairro],
    queryFn: () => fetchTopVias(pin!.lat, pin!.lng, bairro),
    enabled: Boolean(enabled && pin),
    staleTime: 30 * 60_000,
    retry: 1,
    meta: { silent: true },
  })
}
