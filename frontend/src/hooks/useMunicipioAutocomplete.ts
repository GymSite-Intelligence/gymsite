/**
 * useMunicipioAutocomplete — busca municípios IBGE com fallback estático.
 *
 * Estratégia:
 * 1. Tenta IBGE Localidades API (fonte canônica, cacheado infinito por UF).
 * 2. Timeout 8s + 1 retry. Se falhar (caso observado em 2026-05-11), cai
 *    automaticamente pro fallback hardcoded em `data/municipios-fallback.ts`.
 * 3. Filtra client-side por substring case+accent-insensitive.
 *
 * Exibe até MAX_OPTIONS municípios no dropdown (scroll via Combobox max-h-72).
 * CE: 184 • RJ: 92 • BA: 417 • SP: 645 • MG: 853
 * Estados com > 300 municípios precisam de busca por texto pra refinar.
 *
 * Fonte exposta no return (`fonte: 'ibge' | 'fallback'`) pra UI sinalizar
 * ao usuário se está vendo a lista completa ou só os ~50 do cache local.
 */
import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { MUNICIPIOS_FALLBACK } from '@/data/municipios-fallback'

export interface MunicipioIBGE {
  id: number
  nome: string
  uf: string
  uf_nome: string
}

interface IBGEMunicipioRaw {
  id: number
  nome: string
  microrregiao?: {
    mesorregiao?: {
      UF?: {
        sigla?: string
        nome?: string
      }
    }
  }
  'regiao-imediata'?: {
    'regiao-intermediaria'?: {
      UF?: {
        sigla?: string
        nome?: string
      }
    }
  }
}

function normalizar(s: string): string {
  return s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
}

async function fetchMunicipios(uf: string): Promise<MunicipioIBGE[]> {
  const url = `https://servicodados.ibge.gov.br/api/v1/localidades/estados/${uf}/municipios`
  const ctrl = new AbortController()
  const timeoutId = setTimeout(() => ctrl.abort(), 8000)
  try {
    const res = await fetch(url, { signal: ctrl.signal })
    if (!res.ok) throw new Error(`IBGE retornou ${res.status}`)
    const data = (await res.json()) as IBGEMunicipioRaw[]
    return data.map((m) => {
      const ufObj =
        m.microrregiao?.mesorregiao?.UF ||
        m['regiao-imediata']?.['regiao-intermediaria']?.UF ||
        {}
      return {
        id: m.id,
        nome: m.nome,
        uf: ufObj.sigla || uf,
        uf_nome: ufObj.nome || '',
      }
    })
  } finally {
    clearTimeout(timeoutId)
  }
}

/** Máx de itens no dropdown — cobre todos os estados exceto SP (645) e MG (853). */
const MAX_OPTIONS = 300

export function useMunicipioAutocomplete(query: string, uf: string = '') {
  const enabled = uf.length === 2

  const {
    data: todosIbge,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['ibge-municipios', uf],
    queryFn: () => fetchMunicipios(uf),
    enabled,
    staleTime: Infinity,
    gcTime: Infinity,
    retry: 1,
    // IBGE pode estar fora do ar / lento — o hook tem fallback automático
    // pro dataset estático. Não dispara toast global de erro.
    meta: { silent: true },
  })

  // Fonte efetiva: IBGE quando disponível, fallback hardcoded em caso de erro.
  // Fallback é filtrado pra UF atual pra não inflar a lista com cidades de outras UFs.
  const todos = useMemo<MunicipioIBGE[]>(() => {
    if (todosIbge) return todosIbge
    if (isError) return MUNICIPIOS_FALLBACK.filter((m) => m.uf === uf)
    return []
  }, [todosIbge, isError, uf])

  const fonte: 'ibge' | 'fallback' | 'idle' = todosIbge
    ? 'ibge'
    : isError
      ? 'fallback'
      : 'idle'

  const sugestoes = useMemo(() => {
    const q = normalizar(query)
    if (q.length === 0) {
      // Sem filtro: lista alfabética completa (cap pra não estourar DOM em SP/MG)
      return [...todos]
        .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
        .slice(0, MAX_OPTIONS)
    }
    // Com filtro: retorna todos os matches (estados menores ficam < 30 resultados;
    // SP/MG com substring longa também ficam razoáveis)
    return todos
      .filter((m) => normalizar(m.nome).includes(q))
      .sort((a, b) => {
        const aStart = normalizar(a.nome).startsWith(q) ? 0 : 1
        const bStart = normalizar(b.nome).startsWith(q) ? 0 : 1
        if (aStart !== bStart) return aStart - bStart
        return a.nome.localeCompare(b.nome, 'pt-BR')
      })
      .slice(0, MAX_OPTIONS)
  }, [todos, query])

  return {
    sugestoes,
    isLoading: enabled && isLoading && !isError,
    enabled,
    total: todos.length,
    fonte,
  }
}
