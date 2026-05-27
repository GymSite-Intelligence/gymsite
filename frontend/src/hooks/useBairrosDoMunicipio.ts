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
import { PLACES_AUTOCOMPLETE_URL } from '@/lib/places-api'

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

function _isFatalPlacesError(msg: string) {
  const m = msg.toLowerCase()
  return (
    m.includes('google_maps_api_key') ||
    m.includes('maps_api_key') ||
    m.includes('request_denied') ||
    m.includes('places api retornou 403') ||
    m.includes('places api retornou 401') ||
    m.includes('places api (new) nao habilitada') ||
    m.includes('api key bloqueada')
  )
}

async function fetchPrefixo(
  prefixo: string,
  municipio: string,
  uf: string,
): Promise<BairroSugestao[]> {
  try {
    const res = await fetch(PLACES_AUTOCOMPLETE_URL, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ input: prefixo, municipio, uf }),
    })
    if (!res.ok) return []
    const data = (await res.json()) as AutocompleteResp
    if (data.error && _isFatalPlacesError(data.error)) {
      throw new Error(data.error)
    }
    return data.suggestions || []
  } catch (err) {
    if (err instanceof Error && _isFatalPlacesError(err.message)) throw err
    return []
  }
}

async function fetchTodosBairros(
  municipio: string,
  uf: string,
): Promise<BairroSugestao[]> {
  // Disparo paralelo de todas as letras. Quando Places está mal-configurado
  // (chave ausente/sem billing), preferimos falhar com erro visível em vez de
  // mostrar "lista vazia" e deixar o usuário no escuro.
  const resultados = await Promise.allSettled(
    PREFIXOS_BUSCA.map((p) => fetchPrefixo(p, municipio, uf)),
  )

  // Dedup por placeId (preferido) ou textoCompleto
  const visto = new Map<string, BairroSugestao>()
  for (const r of resultados) {
    if (r.status !== 'fulfilled') continue
    for (const b of r.value) {
      const key = b.placeId || b.textoCompleto
      if (!visto.has(key)) visto.set(key, b)
    }
  }

  // Se nenhuma chamada retornou bairros e pelo menos uma falhou de forma "fatal",
  // propaga o erro pra UI exibir mensagem (ex.: REQUEST_DENIED / chave ausente).
  if (visto.size === 0) {
    const fatal = resultados.find(
      (r) => r.status === 'rejected' && r.reason instanceof Error,
    )
    const fatalMsg =
      fatal && fatal.status === 'rejected' && fatal.reason instanceof Error
        ? fatal.reason.message
        : null
    if (fatalMsg) throw new Error(fatalMsg)
  }

  // Ordena alfabeticamente pra UX previsível no dropdown
  return Array.from(visto.values()).sort((a, b) =>
    a.bairro.localeCompare(b.bairro, 'pt-BR'),
  )
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
    // Places Autocomplete pode falhar transitoriamente em retry/timeout.
    // Não dispara toast global — UI já mostra estado vazio sem ruído.
    meta: { silent: true },
  })
}
