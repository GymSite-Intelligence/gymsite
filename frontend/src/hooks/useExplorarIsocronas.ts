import { useQuery } from '@tanstack/react-query'
import { fetchExplorar } from '@/lib/explorarApi'
import type { ModoDesloc } from '@/components/explorar/explorarIso'

export type ExplorarIsoRings = {
  m5: [number, number][]
  m10: [number, number][]
  m15: [number, number][]
  fonte?: string
}

async function fetchIsocronas(
  lat: number,
  lng: number,
  modo: ModoDesloc,
): Promise<ExplorarIsoRings> {
  const res = await fetchExplorar('/api/explorar/isocronas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lat, lng, modo }),
  })
  if (!res.ok) {
    throw new Error('Não deu para calcular o tempo de rua.')
  }
  return res.json() as Promise<ExplorarIsoRings>
}

export function useExplorarIsocronas(
  pin: { lat: number; lng: number } | null,
  modo: ModoDesloc,
  enabled: boolean,
) {
  return useQuery({
    queryKey: ['explorar-isocronas', pin?.lat.toFixed(5), pin?.lng.toFixed(5), modo],
    queryFn: () => fetchIsocronas(pin!.lat, pin!.lng, modo),
    enabled: Boolean(enabled && pin),
    staleTime: 30 * 60_000,
    retry: 1,
    meta: { silent: true },
  })
}
