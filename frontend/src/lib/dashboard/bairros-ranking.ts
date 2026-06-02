/**
 * Ranking de bairros no dashboard — agregação client-side sobre v_relatorios_resumo.
 *
 * Mantém compatibilidade com filtros do dashboard (cidade, veredito, período).
 * View `v_bairros_aggregate` só cobre relatórios `done` sem esses filtros.
 */
import type { RelatorioResumo } from '@/types/domain'
import { isVereditoAprovado } from '@/lib/dashboard/veredito-groups'

export const BAIRROS_RANKING_LIMIT = 10

/** Mínimo de relatórios no bairro líder para gerar insight automático. */
export const BAIRROS_RANKING_MIN_INSIGHT_COUNT = 3

export const BAIRROS_RANKING_COPY = {
  title: 'Top bairros analisados',
  description: 'Ranking por score médio do top candidato',
  emptyTitle: 'Top bairros',
  emptyMessage: 'Nenhum bairro analisado ainda.',
} as const

export interface BairroRankItem {
  bairro: string
  cidade: string
  uf: string | null
  count: number
  scoreMedio: number | null
  aprovacaoPct: number
}

function normText(s: string): string {
  return s.trim().replace(/\s+/g, ' ')
}

/** Chave estável — evita duplicar o mesmo bairro por UF vazia vs "RJ" ou espaços. */
function groupKey(r: RelatorioResumo): string {
  const bairro = normText(r.bairro).toLowerCase()
  const cidade = normText(r.cidade).toLowerCase()
  const uf = (r.uf ?? '').trim().toUpperCase()
  return `${bairro}|${cidade}|${uf}`
}

function displayFromGroup(rows: RelatorioResumo[]): {
  bairro: string
  cidade: string
  uf: string | null
} {
  const ref = rows[0]
  const uf = (ref.uf ?? '').trim().toUpperCase()
  return {
    bairro: normText(ref.bairro),
    cidade: normText(ref.cidade),
    uf: uf || null,
  }
}

function mean(nums: number[]): number | null {
  if (nums.length === 0) return null
  return nums.reduce((a, b) => a + b, 0) / nums.length
}

export function computeBairrosRanking(rows: RelatorioResumo[]): BairroRankItem[] {
  const map = new Map<string, RelatorioResumo[]>()
  for (const r of rows) {
    const key = groupKey(r)
    const arr = map.get(key) ?? []
    arr.push(r)
    map.set(key, arr)
  }

  const result: BairroRankItem[] = []
  for (const arr of map.values()) {
    const { bairro, cidade, uf } = displayFromGroup(arr)
    const concluidos = arr.filter((r) => r.status === 'done')
    const scores = concluidos
      .map((r) => r.score_top1_candidato)
      .filter((s): s is number => s != null)
    const aprovados = concluidos.filter((r) => isVereditoAprovado(r.veredito))

    result.push({
      bairro,
      cidade,
      uf,
      count: arr.length,
      scoreMedio: mean(scores),
      aprovacaoPct:
        concluidos.length > 0
          ? Math.round((aprovados.length / concluidos.length) * 100)
          : 0,
    })
  }

  return result
    .sort((a, b) => (b.scoreMedio ?? 0) - (a.scoreMedio ?? 0))
    .slice(0, BAIRROS_RANKING_LIMIT)
}

export interface BairroMaisAnalisadoInsight {
  titulo: string
  descricao: string
}

/** Texto do insight “bairro mais analisado” (null se abaixo do limiar). */
export function buildBairroMaisAnalisadoInsight(
  ranking: BairroRankItem[],
): BairroMaisAnalisadoInsight | null {
  const top = ranking[0]
  if (!top || top.count < BAIRROS_RANKING_MIN_INSIGHT_COUNT) return null
  return {
    titulo: `${top.bairro} é o bairro mais analisado`,
    descricao: `${top.count} relatórios · score médio ${top.scoreMedio?.toFixed(1) ?? '—'}`,
  }
}
