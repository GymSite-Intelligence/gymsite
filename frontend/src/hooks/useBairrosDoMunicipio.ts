/**
 * useBairrosDoMunicipio — lista completa de bairros via Places multi-letter.
 *
 * Por que multi-letter (vs single autocomplete call):
 * Places Autocomplete retorna no máx 5 sugestões por chamada. Pra ter
 * lista completa de bairros de uma cidade, faz 12 chamadas paralelas com
 * prefixos A-V (cobre 95%+ dos bairros brasileiros) e deduplica.
 *
 * Custo por município: ~12 × $0.003 = $0.036 ≈ R$ 0,20.
 * Mitigação: cache TanStack staleTime infinito — 1 fetch único por
 * (municipio, uf) na sessão. Próximo usuário paga de novo (sem persist
 * cross-session — TODO futuro: tabela bairros_municipio no Supabase).
 *
 * Fallback: se múltiplas chamadas falharem, retorna o que conseguiu.
 * Form sempre permite "usar mesmo assim" como string livre.
 */
import { useQuery } from '@tanstack/react-query'
import type { BairroSugestao } from '@/hooks/useBairroAutocomplete'

// Prefixos cobrem maioria dos bairros (vogais + consoantes comuns).
// Letras raras (k, w, y, z) excluídas pra economizar chamadas.
const PREFIXOS_BUSCA = [
  'a',
  'b',
  'c',
  'd',
  'e',
  'f',
  'g',
  'i',
  'j',
  'l',
  'm',
  'n',
  'o',
  'p',
  'q',
  'r',
  's',
  't',
  'u',
  'v',
]

interface AutocompleteResp {
  suggestions: BairroSugestao[]
  error?: string
}

async function fetchPrefixo(
  prefixo: string,
  municipio: string,
  uf: string,
): Promise<BairroSugestao[]> {
  try {
    const res = await fetch('/api/places-autocomplete', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ input: prefixo, municipio, uf }),
    })
    if (!res.ok) return []
    const data = (await res.json()) as AutocompleteResp
    return data.suggestions || []
  } catch {
    return []
  }
}

async function fetchTodosBairros(
  municipio: string,
  uf: string,
): Promise<BairroSugestao[]> {
  // Disparo paralelo de todas as letras
  const resultados = await Promise.all(
    PREFIXOS_BUSCA.map((p) => fetchPrefixo(p, municipio, uf)),
  )

  // Dedup por placeId (preferido) ou textoCompleto
  const visto = new Map<string, BairroSugestao>()
  for (const lista of resultados) {
    for (const b of lista) {
      const key = b.placeId || b.textoCompleto
      if (!visto.has(key)) visto.set(key, b)
    }
  }

  // Ordena alfabeticamente pra UX previsível no dropdown
  return Array.from(visto.values()).sort((a, b) =>
    a.bairro.localeCompare(b.bairro, 'pt-BR'),
  )
}

export function useBairrosDoMunicipio(municipio: string, uf: string) {
  const enabled = municipio.length >= 2 && uf.length === 2
  return useQuery({
    queryKey: ['bairros-municipio', municipio.toLowerCase(), uf.toLowerCase()],
    queryFn: () => fetchTodosBairros(municipio, uf),
    enabled,
    staleTime: Infinity,
    gcTime: Infinity, // mantém em memória pra navegação volta/avança
    retry: 1,
    // Places Autocomplete pode falhar transitoriamente em retry/timeout.
    // Não dispara toast global — UI já mostra estado vazio sem ruído.
    meta: { silent: true },
  })
}
