/**
 * mocks/index.ts — Importa os 6 JSONs canônicos v1.1 do pipeline ADK
 * e expõe utilitários pra alimentar hooks de query enquanto Supabase
 * não está ativo.
 *
 * Quando VITE_USE_MOCKS=true, useRelatorios e useRelatorioDetail leem daqui.
 * Quando =false, leem do Supabase. Toggle em src/lib/supabase.ts.
 */
import type { RelatorioResumo, RelatorioStatus, Veredito } from '@/types/domain'

// Vite resolve `import.meta.glob` em build-time, então os 6 JSONs viram
// um Record { '/src/mocks/relatorios/rpt_*.json': {...} } sem fetch runtime.
const RAW_REPORTS = import.meta.glob('./relatorios/*.json', {
  eager: true,
  import: 'default',
}) as Record<string, RawRelatorioJSON>

/**
 * Subset mínimo do JSON canônico usado pelo loader de mocks. Campos novos
 * (schema v1.4: cobertura_redes_a0, genero_alvo) ficam tipados aqui pra
 * que mocks malformados gerem erro de compile em vez de silêncio.
 *
 * Tipos completos: ver `hooks/useRelatorioDetail.ts` (RelatorioDetail).
 */
interface RawRelatorioJSON {
  id: string
  tipo_relatorio: string
  data_execucao: string
  input_canonico: {
    cidade: string
    bairro: string
    area_m2_min: number
    area_m2_max: number
    publico_alvo?: string
    /** Schema v1.4 */
    genero_alvo?: string
    /** Schema v1.5: PP|P|M|G|GG */
    tamanho_preset?: string
    tipo_negocio?: string
    estacionamento_obrigatorio?: boolean
  }
  output_consolidado: {
    veredito: Veredito
    score_bairro: number | null
    score_top1_candidato: number | null
    scores_regionais?: {
      demografico?: number
      competitivo?: number
      concorrencia?: number
      viabilidade?: number
    }
    modelo_recomendado: string | null
    aluguel_mensal: number | null
    aluguel_mediana_m2_observado?: number | null
    nivel_saturacao?: string | null
    /** Schema v1.2+ */
    market_context?: {
      genero_alvo?: string
      tamanho_preset?: string
      tipo_negocio?: string
      [k: string]: unknown
    }
    /** Schema v1.4 */
    cobertura_redes_a0?: {
      redes_solicitadas: string[]
      redes_cobertas: string[]
      redes_nao_encontradas: string[]
      tem_redes_fantasma: boolean
      concorrentes_excluidos?: { nome: string; motivo: string }[]
    }
  }
  metadata_execucao?: Record<string, unknown> & { schema_version?: string }
}

export const RAW_MOCKS: RawRelatorioJSON[] = Object.values(RAW_REPORTS)

/**
 * Converte um JSON canônico v1.1 do filesystem para o formato `RelatorioResumo`
 * (linha da view v_relatorios_resumo). Tabelas relacionadas ficam disponíveis
 * via `getMockRelatorioDetail(id)` quando o viewer for implementado.
 */
export function toRelatorioResumo(raw: RawRelatorioJSON): RelatorioResumo {
  const inp = raw.input_canonico
  const out = raw.output_consolidado
  // O id do pipeline é "rpt_<unix_ts>" — não é UUID. Pra mocks, usamos como id.
  // No Supabase real, a coluna `adk_run_id` guarda esse valor e `id` é UUID.
  return {
    id: raw.id,
    org_id: '00000000-0000-0000-0000-000000000001',
    user_id: null,
    tipo_relatorio: raw.tipo_relatorio,
    status: 'done' satisfies RelatorioStatus,
    data_execucao: raw.data_execucao,
    tempo_execucao_segundos: null,
    custo_brl: null,
    cidade: inp.cidade,
    uf: null,
    bairro: inp.bairro,
    area_m2_min: inp.area_m2_min,
    area_m2_max: inp.area_m2_max,
    publico_alvo: inp.publico_alvo ?? '25-40',
    // biome-ignore lint/suspicious/noExplicitAny: ENUM string lookup
    tipo_negocio: (inp.tipo_negocio as any) ?? 'academia',
    veredito: out.veredito,
    score_bairro: out.score_bairro,
    score_top1_candidato: out.score_top1_candidato,
    modelo_recomendado: out.modelo_recomendado,
    aluguel_mediana_m2: out.aluguel_mediana_m2_observado ?? null,
    nivel_saturacao: out.nivel_saturacao ?? null,
    created_at: raw.data_execucao,
  }
}

export function getMockRelatoriosResumo(): RelatorioResumo[] {
  return RAW_MOCKS
    .map(toRelatorioResumo)
    .sort((a, b) => {
      const da = a.data_execucao ?? ''
      const db = b.data_execucao ?? ''
      return db.localeCompare(da)  // mais recente primeiro
    })
}

export function getMockRelatorioRaw(id: string): RawRelatorioJSON | undefined {
  return RAW_MOCKS.find((r) => r.id === id)
}

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== 'false'
