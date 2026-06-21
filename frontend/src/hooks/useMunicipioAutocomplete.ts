/**
 * useMunicipioAutocomplete — busca municípios num dataset ESTÁTICO local.
 *
 * Antes dependia do IBGE Localidades API (client-side) com fallback hardcoded de
 * ~55 cidades — quando o IBGE caía, o usuário via só 9 municípios de CE. Agora os
 * 5570+ municípios vêm de `data/municipios-brasil.ts` (gerado do BigQuery
 * basedosdados, ver _gen_municipios.py): 100% offline, instantâneo, sem fetch,
 * sem dependência externa. Filtra client-side por substring case+accent-insensitive.
 *
 * Mantém a mesma API de retorno (sugestoes/total/fonte) do hook antigo pra não
 * mexer no NovoRelatorioPage. `fonte` agora é sempre 'local'.
 */
import { useMemo } from 'react'
import { MUNICIPIOS_BRASIL } from '@/data/municipios-brasil'
import { UFS_BRASIL } from '@/data/ufs-brasil'

export interface MunicipioIBGE {
  id: number
  nome: string
  uf: string
  uf_nome: string
}

function normalizar(s: string): string {
  return s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
}

/** Máx de itens no dropdown — cobre todos os estados exceto SP (645) e MG (853). */
const MAX_OPTIONS = 300

const UF_NOME = new Map(UFS_BRASIL.map((u) => [u.sigla, u.nome]))

export function useMunicipioAutocomplete(query: string, uf: string = '') {
  const enabled = uf.length === 2

  // Municípios da UF, já no formato MunicipioIBGE (uf_nome derivado de UFS_BRASIL).
  const todos = useMemo<MunicipioIBGE[]>(() => {
    if (!enabled) return []
    const ufNome = UF_NOME.get(uf) ?? ''
    return MUNICIPIOS_BRASIL.filter((m) => m.uf === uf).map((m) => ({
      id: m.id,
      nome: m.nome,
      uf: m.uf,
      uf_nome: ufNome,
    }))
  }, [enabled, uf])

  const sugestoes = useMemo(() => {
    const q = normalizar(query)
    if (q.length === 0) {
      // Sem filtro: lista alfabética completa (cap pra não estourar DOM em SP/MG)
      return [...todos]
        .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
        .slice(0, MAX_OPTIONS)
    }
    // Com filtro: prioriza prefixo, depois substring.
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
    isLoading: false,
    enabled,
    total: todos.length,
    fonte: 'local' as const,
  }
}
