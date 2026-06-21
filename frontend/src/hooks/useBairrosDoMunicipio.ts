/**
 * useBairrosDoMunicipio — lista completa de bairros via backend (cache Places→DB).
 *
 * Antes: 12 chamadas paralelas ao Google Places NO BROWSER por município, toda
 * sessão (~R$0,20/município, sem persistência). Agora: 1 GET a
 * /api/municipios/bairros — o backend varre o Places UMA vez por município,
 * persiste em `bairros_municipio` e serve do DB nos acessos seguintes
 * (grátis/instantâneo). Ver tools/bairros_municipio.py.
 *
 * A busca por texto digitado é client-side sobre esta lista (sem mais Places por
 * tecla — useBairroAutocomplete foi removido).
 */
import { useQuery } from '@tanstack/react-query'
import { API_BASE } from '@/lib/supabase'

export interface BairroSugestao {
  placeId: string
  bairro: string
  contexto: string
  textoCompleto: string
}

interface BairrosResponse {
  bairros: BairroSugestao[]
  fonte: string
  harvested: boolean
  erro?: string
}

async function fetchTodosBairros(
  municipio: string,
  uf: string,
): Promise<BairroSugestao[]> {
  const base = API_BASE.replace(/\/$/, '')
  const url = `${base}/api/municipios/bairros?municipio=${encodeURIComponent(
    municipio,
  )}&uf=${encodeURIComponent(uf)}`
  const res = await fetch(url)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Bairros ${res.status}: ${text}`)
  }
  const data = (await res.json()) as BairrosResponse
  // erro com lista vazia = Places falhou no harvest (chave/billing) — propaga
  // pra UI exibir, igual ao comportamento anterior.
  if (data.erro && (!data.bairros || data.bairros.length === 0)) {
    throw new Error(data.erro)
  }
  return data.bairros || []
}

export function useBairrosDoMunicipio(
  municipio: string,
  uf: string,
  options: { enabled?: boolean } = {},
) {
  // Hook só dispara quando município/UF estão setados E o caller não desativou.
  // Caller desativa em modo "cidade inteira" pra não queimar quota Places.
  const externalEnabled = options.enabled ?? true
  const enabled = externalEnabled && municipio.length >= 2 && uf.length === 2
  return useQuery({
    queryKey: ['bairros-municipio', municipio.toLowerCase(), uf.toLowerCase()],
    queryFn: () => fetchTodosBairros(municipio, uf),
    enabled,
    staleTime: Infinity,
    gcTime: Infinity, // mantém em memória pra navegação volta/avança
    retry: 1,
    meta: { silent: true },
  })
}
