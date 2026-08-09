import { useQuery } from '@tanstack/react-query'
import {
  explorarAutocompleteBody,
  explorarAutocompleteQueryKey,
} from '@/components/explorar/explorarAutocompleteState'
import { API_BASE } from '@/lib/supabase'

export type ExplorarEnderecoSugestao = {
  placeId: string
  bairro: string
  contexto: string
  textoCompleto: string
  lat?: number
  lng?: number
}

async function fetchSugestoes(
  input: string,
  lat?: number,
  lng?: number,
): Promise<ExplorarEnderecoSugestao[]> {
  const res = await fetch(`${API_BASE.replace(/\/$/, '')}/api/explorar/autocomplete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(explorarAutocompleteBody(input, lat, lng)),
  })
  if (!res.ok) throw new Error(`autocomplete ${res.status}`)
  const data = (await res.json()) as {
    suggestions?: ExplorarEnderecoSugestao[]
  }
  return data.suggestions ?? []
}

export function useExplorarEnderecoAutocomplete(
  input: string,
  lat?: number,
  lng?: number,
) {
  const q = input.trim()
  return useQuery({
    queryKey: explorarAutocompleteQueryKey(q, lat, lng),
    queryFn: () => fetchSugestoes(q, lat, lng),
    enabled: q.length >= 3,
    staleTime: 60_000,
    retry: 0,
    meta: { silent: true },
  })
}
