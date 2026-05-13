/**
 * useBairroAutocomplete — autocomplete de bairros via Google Places API (proxy Vite).
 *
 * Diferente de useMunicipioAutocomplete (que carrega tudo de uma vez), aqui
 * não dá pra cachear a lista inteira de bairros: a Places API retorna sob
 * demanda. Cache fica por (municipio + uf + input) e expira após 1h.
 *
 * Padrão de uso:
 *   const { sugestoes, isFetching } = useBairroAutocomplete({
 *     input: 'tama',
 *     municipio: 'Eusébio',
 *     uf: 'CE',
 *   })
 *
 * Debounce de 250ms recomendado no caller (não embutido aqui pra manter o hook puro).
 */
import { useQuery } from '@tanstack/react-query'

export interface BairroSugestao {
  placeId: string
  bairro: string
  contexto: string
  textoCompleto: string
}

interface AutocompleteRequest {
  input: string
  municipio: string
  uf: string
  lat?: number
  lng?: number
}

interface AutocompleteResponse {
  suggestions: BairroSugestao[]
  error?: string
}

async function fetchBairros(
  req: AutocompleteRequest,
): Promise<BairroSugestao[]> {
  const res = await fetch('/api/places-autocomplete', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Places proxy ${res.status}: ${text}`)
  }
  const data = (await res.json()) as AutocompleteResponse
  if (data.error) throw new Error(data.error)
  return data.suggestions || []
}

export function useBairroAutocomplete(req: AutocompleteRequest) {
  const enabled =
    req.input.trim().length >= 2 && !!req.municipio && req.municipio.length >= 2
  return useQuery({
    queryKey: [
      'places-bairros',
      req.municipio?.toLowerCase(),
      req.uf?.toLowerCase(),
      req.input.toLowerCase().trim(),
    ],
    queryFn: () => fetchBairros(req),
    enabled,
    staleTime: 60 * 60 * 1000, // 1h — bairros não mudam frequentemente
    retry: 1,
    // Places Autocomplete pode falhar transitoriamente.
    // Não dispara toast global — UI mostra "sem sugestões" sem ruído.
    meta: { silent: true },
  })
}
