/**
 * hooks/useRelatorioDetail.ts — Carrega o relatório completo (JSON canônico v1.1+).
 *
 * Diferente de useRelatorios (lista resumida), este retorna o output_consolidado
 * inteiro com top_3_candidatos, competitors_set, viabilidade_3_cenarios,
 * bairros_alternativos, etc. Usado pelo viewer.
 *
 * Modo real: consulta GET /api/relatorios/{id} (backend FastAPI), que faz join
 * de 9 tabelas Supabase e retorna estrutura flat. Aqui reshape pra árvore
 * RelatorioDetail (`output_consolidado.top_3_candidatos`, etc) que o viewer
 * já consome desde os mocks.
 */
import { useQuery } from '@tanstack/react-query'
import { getMockRelatorioRaw, USE_MOCKS } from '@/mocks'
import { useAuth } from '@/lib/auth'
import { supabase } from '@/lib/supabase'

/**
 * Shape do JSON canônico v1.1 retornado pelo pipeline A6.
 * Mantém estrutura aninhada do JSON real (não achata) — viewer navega
 * pelas seções acessando output_consolidado.*.
 */
export interface RelatorioDetail {
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
    /** Schema v1.5: preset Smart Fit-style */
    tamanho_preset?: 'pp' | 'p' | 'm' | 'g' | 'gg'
    tipo_negocio?: string
    estacionamento_obrigatorio?: boolean
  }
  output_consolidado: OutputConsolidado
  metadata_execucao?: Record<string, unknown>
}

export interface OutputConsolidado {
  veredito: 'APROVADO' | 'APROVADO COM RESSALVAS' | 'INVESTIGAR MAIS' | 'REPROVADO'
  score_bairro: number | null
  score_top1_candidato: number | null
  scores_regionais?: {
    demografico?: number
    competitivo?: number
    concorrencia?: number
    viabilidade?: number
  }
  nivel_saturacao?: string | null
  rating_medio_concorrentes?: number | null
  total_concorrentes_analisados?: number
  modelo_recomendado: string | null
  aluguel_mensal: number | null
  aluguel_mediana_m2_observado?: number | null
  aluguel_min_m2_observado?: number | null
  aluguel_max_m2_observado?: number | null
  fonte_aluguel?: string | null
  posicionamento_recomendado?: string | null
  resumo_executivo?: string | null
  top_3_candidatos: CandidatoJSON[]
  competitors_set?: CompetidorJSON[]
  viabilidade_3_cenarios?: Record<'low' | 'mid' | 'premium', CenarioJSON>
  bairros_alternativos?: BairroAlternativoJSON[]
  /**
   * Schema v1.5: aviso quando A6 detectou que o `bairro` informado é na
   * verdade município da RM da `cidade`. Quando presente, viewer deve
   * renderizar callout no topo da seção "Bairros Alternativos".
   */
  aviso_geografico?: string | null
  cidade_efetiva?: string | null
  cidade_foi_corrigida?: boolean
  dores_dominantes?: DorDominanteJSON[]
  servicos_nao_oferecidos?: string[]
  distribuicao_geografica?: DistribuicaoBairroJSON[]
  alertas_financeiros?: string[]
  contato_decisor?: Record<string, unknown>
  /** Schema v1.2: market_context completo do A0 Deep Research */
  market_context?: MarketContextJSON
  /**
   * Schema v1.4: cobertura A0 — confronta redes listadas pelo Deep Research
   * (`market_context.principais_redes_concorrentes`) contra o que a busca
   * georreferenciada do A3a validou no raio do bairro alvo. Quando
   * `tem_redes_fantasma=true`, o relatório deve sinalizar que o DR
   * generalizou players regionais como locais.
   */
  cobertura_redes_a0?: CoberturaRedesA0JSON
}

export interface CoberturaRedesA0JSON {
  redes_solicitadas: string[]
  redes_cobertas: string[]
  redes_nao_encontradas: string[]
  concorrentes_excluidos?: { nome: string; motivo: string }[]
  tem_redes_fantasma: boolean
}

export interface MarketContextJSON {
  cidade?: string
  bairro?: string
  ticket_medio_mercado?: string
  aluguel_medio_m2?: string
  renda_media_bairro?: string
  faixa_etaria_predominante?: string
  /** Schema v1.4+: calibra ticket, mix e benchmarks no A4. Default "misto". */
  genero_alvo?:
    | 'misto'
    | 'predominantemente_feminino'
    | 'predominantemente_masculino'
    | 'exclusivamente_feminino'
    | 'exclusivamente_masculino'
  /** Schema v1.5: preset Smart Fit-style PP/P/M/G/GG. */
  tamanho_preset?: 'pp' | 'p' | 'm' | 'g' | 'gg'
  /** Schema v1.5: replicado pra contexto (já existe em input_canonico). */
  tipo_negocio?: string
  principais_redes_concorrentes?: string[]
  tendencia_mercado?: 'crescimento' | 'estavel' | 'retracao' | string
  regulamentacao_resumo?: string
  insights_estrategicos?: string[]
  fonte?: string
  data_coleta?: string
  cached?: boolean
}

export interface CandidatoJSON {
  nome: string
  endereco: string
  area_estimada_m2: number
  lat?: number
  lng?: number
  score_geoscout: number
  score_ancoragem: number
  motivo: string
  polos_geradores: string[]
  street_view_url?: string
  estimativa_visibilidade?: string
  avenida_principal?: boolean
  qualidade_sinal?: string
  status?: string
  place_id?: string
  tipos?: string[]
  /** Contact Data (Places API New) — disponível desde v1.2 com FieldMask fix */
  telefone?: string
  website?: string
  tem_24h?: boolean
}

export interface CompetidorJSON {
  nome: string
  rating_oficial?: number
  rating_geral?: number
  num_avaliacoes?: number
  endereco?: string
  bairro_concorrente?: string
  tem_24h?: boolean
  /** Contact data (Places API) — Fase 2 popula */
  telefone?: string | null
  website?: string | null
  whatsapp_link?: string | null
  /**
   * Popular times — 7 dias × 24 horas (% movimento). Vem do
   * `popular_times_tool` (Playwright scraping da DOM do Maps).
   * Estrutura: { domingo: { '00': 0, '01': 0, ..., '23': 5 }, ... }
   */
  horarios_pico?: Record<string, Record<string, number>> | null
  /** Resumo textual ex: "Segunda 19h (87%)" */
  pico_semanal?: string | null
  reviews_traduzidas?: ReviewJSON[]
  reviews?: ReviewJSON[]
}

export interface ReviewJSON {
  rating?: number
  quote_pt_br?: string
  quote_original?: string
  quote_curta?: string
  idioma_original?: string
  autor?: string
  data_relativa?: string
  categoria_dor?: string
  sinal?: 'positivo' | 'neutro' | 'negativo'
}

/**
 * CenarioJSON — schema v2 do A4 FinancialEstimator.
 *
 * Mudanças vs v1:
 * - matriculas {cons, real, agres} substitui alunos_projetados (que era pico, não matrículas)
 * - capacidade_simultanea_pico vira métrica separada (verificação de conforto físico)
 * - custos_detalhados expande pra 12 linhas
 * - capex_detalhado quebra investimento
 * - sensibilidade traz 3 stress tests
 * - tir_anual_pct + vpl_5_anos pra decisão de investimento
 *
 * Campos v1 (capacidade_maxima_alunos, alunos_projetados, etc) preservados
 * pra compat com mocks antigos — sempre prefira os novos.
 */
export interface CenarioJSON {
  modelo: string
  modelo_key?: 'low' | 'mid' | 'premium'
  ticket_medio: number
  descricao?: string
  exemplos_redes?: string

  // ── Demanda v2 ──
  matriculas?: {
    conservador: { valor: number; matr_por_m2: number; premissa: string }
    realista:    { valor: number; matr_por_m2: number; premissa: string }
    agressivo:   { valor: number; matr_por_m2: number; premissa: string }
  }
  matriculas_recomendada?: 'conservador' | 'realista' | 'agressivo'
  capacidade_simultanea_pico?: number
  frequencia_semanal_aluno?: number
  pico_share?: number
  alunos_pico_calculado?: number
  folga_capacidade_pct?: number

  // ── Receita ──
  ticket_realizado_estimado?: number
  taxa_inadimplencia?: number
  taxa_cancelamento_mensal?: number
  receita_mensal: number

  // ── Custos detalhados (12 linhas v2) ──
  custos_detalhados?: {
    aluguel: number
    condominio: number
    iptu: number
    energia: number
    agua: number
    internet: number
    folha: number
    manutencao: number
    contabilidade: number
    sistema_gestao: number
    seguro: number
    outros: number
  }
  custos_fixos_total?: number
  marketing_pct_faturamento?: number
  marketing_mensal?: number
  custos_totais?: number

  // ── Resultado ──
  lucro_mensal_estimado: number
  margem_percentual?: number
  alunos_break_even?: number

  // ── Investimento ──
  capex_detalhado?: {
    equipamentos: number
    obra_adaptacao: number
    projeto_arquitetonico: number
    alvara_e_taxas: number
    /** Schema v1.6: frete dos equipamentos via ANTT 6.034/2024 */
    frete_equipamentos?: number
    frete_detalhes?: {
      frete_piso_antt: number
      frete_estimado_real: number
      margem_broker_pct: number
      distancia_km: number
      eixos: number
      tipo_veiculo: string
      pct_do_capex_equipamentos: number
      fonte: string
    }
    contingencia_pct: number
    contingencia_valor: number
    total: number
    fonte_equipamentos?: string
    fonte_frete?: string
  }
  capex_total?: number
  capital_giro_meses?: number
  capital_giro?: number
  investimento_total?: number
  payback_meses: number
  tir_anual_pct?: number | null
  vpl_5_anos?: number

  // ── Risco ──
  sensibilidade?: SensibilidadeStress[]

  // ── Veredito ──
  viabilidade: 'ALTO' | 'MEDIO' | 'BAIXO' | 'INVIAVEL'
  justificativa?: string

  // ── Backward-compat v1 (preservado pra mocks antigos) ──
  capacidade_maxima_alunos?: number
  alunos_projetados?: number
  custos_fixos?: number
  capex_estimado?: number
}

export interface SensibilidadeStress {
  id: 'aluguel_mais_20pct' | 'matriculas_menos_30pct' | 'ticket_menos_15pct'
  label: string
  lucro_mensal: number
  margem_percentual?: number
  payback_meses: number
  viabilidade: 'ALTO' | 'MEDIO' | 'BAIXO' | 'INVIAVEL'
}

export interface BairroAlternativoJSON {
  bairro: string
  motivo: string
  status?: string
  prioridade_ajustada?: string
  ticket_sugerido?: string
  concorrentes_no_bairro?: number
  academias_existentes?: string[]
}

export interface DorDominanteJSON {
  dor: string
  mencoes: number
  mencionado_por?: { academia: string; vezes: number }[]
}

export interface DistribuicaoBairroJSON {
  bairro: string
  count: number
  academias: string[]
}

/**
 * Reshape do payload backend (flat: header + listas separadas) → árvore
 * RelatorioDetail aninhada que o viewer espera (output_consolidado.*).
 *
 * Backend retorna:
 *   { id, header, input_canonico, output_consolidado, candidatos[],
 *     competidores[], cenarios[], sensibilidade[], bairros_alternativos[] }
 *
 * Viewer espera:
 *   { id, data_execucao, input_canonico, output_consolidado: {
 *       veredito, score_*, top_3_candidatos[], competitors_set[],
 *       viabilidade_3_cenarios: {low, mid, premium}, bairros_alternativos[], ... }}
 */
type BackendPayload = {
  id: string
  header: Record<string, unknown>
  input_canonico: Record<string, unknown> | null
  output_consolidado: Record<string, unknown> | null
  candidatos: Record<string, unknown>[]
  competidores: Record<string, unknown>[]
  cenarios: Record<string, unknown>[]
  sensibilidade: Record<string, unknown>[]
  bairros_alternativos: Record<string, unknown>[]
}

/** Converte string/numeric (Postgres numeric vem como string em JSON) pra number. */
function _num(v: unknown): number {
  if (v == null) return 0
  if (typeof v === 'number') return v
  const n = parseFloat(String(v))
  return Number.isFinite(n) ? n : 0
}

function adaptBackendToDetail(p: BackendPayload): RelatorioDetail {
  const out = (p.output_consolidado ?? {}) as Record<string, unknown>
  const sens = p.sensibilidade ?? []

  // Agrupa cenarios por modelo + injeta sensibilidade correspondente.
  // O schema do Postgres é FLAT (custo_aluguel, capex_equipamentos, ...) mas
  // o viewer espera estrutura aninhada (custos_detalhados.aluguel, etc).
  // Aqui reagrupamos antes de devolver.
  const cenariosByModelo: Partial<Record<'low' | 'mid' | 'premium', unknown>> = {}
  for (const c of p.cenarios) {
    const modelo = c.modelo as 'low' | 'mid' | 'premium'
    if (!modelo) continue
    // Remapeia colunas DB → tipo TS esperado pelo viewer.
    // Importante: o row do DB tem `id` (uuid PK) e `stress_id` (enum
    // 'aluguel_mais_20pct'|...). O viewer espera o ENUM, então prioriza
    // stress_id sobre o uuid. Mesmo pra label.
    const stresses = sens
      .filter((s) => s.cenario_id === c.id || s.modelo === modelo)
      .map((s) => ({
        ...s,
        id: s.stress_id ?? s.id,
        label: s.stress_label ?? s.label,
        lucro_mensal: _num(s.lucro_mensal),
        margem_percentual: s.margem_percentual != null ? _num(s.margem_percentual) : undefined,
        payback_meses:
          typeof s.payback_meses === 'number'
            ? s.payback_meses
            : _num(s.payback_meses),
        viabilidade: s.viabilidade,
      }))

    // Reagrupa as 12 colunas custo_* em custos_detalhados
    const custos_detalhados = {
      aluguel:         _num(c.custo_aluguel),
      condominio:      _num(c.custo_condominio),
      iptu:            _num(c.custo_iptu),
      energia:         _num(c.custo_energia),
      agua:            _num(c.custo_agua),
      internet:        _num(c.custo_internet),
      folha:           _num(c.custo_folha),
      manutencao:      _num(c.custo_manutencao),
      contabilidade:   _num(c.custo_contabilidade),
      sistema_gestao:  _num(c.custo_sistema_gestao),
      seguro:          _num(c.custo_seguro),
      outros:          _num(c.custo_outros),
    }

    // Reagrupa as 6 colunas capex_* em capex_detalhado
    const capex_detalhado = {
      equipamentos:           _num(c.capex_equipamentos),
      obra_adaptacao:         _num(c.capex_obra_adaptacao),
      projeto_arquitetonico:  _num(c.capex_projeto_arquitetonico),
      alvara_e_taxas:         _num(c.capex_alvara_e_taxas),
      contingencia_pct:       _num(c.capex_contingencia_pct),
      contingencia_valor:     _num(c.capex_contingencia_valor),
      total:                  _num(c.capex_total),
    }

    // Matriculas (3 cenários conservador/realista/agressivo) também são flat
    const matriculas =
      c.matriculas_conservador != null ||
      c.matriculas_realista != null ||
      c.matriculas_agressivo != null
        ? {
            conservador: {
              valor: _num(c.matriculas_conservador),
              matr_por_m2: _num(c.matr_por_m2_realista),
              premissa: '',
            },
            realista: {
              valor: _num(c.matriculas_realista),
              matr_por_m2: _num(c.matr_por_m2_realista),
              premissa: '',
            },
            agressivo: {
              valor: _num(c.matriculas_agressivo),
              matr_por_m2: _num(c.matr_por_m2_realista),
              premissa: '',
            },
          }
        : undefined

    cenariosByModelo[modelo] = {
      ...c,
      modelo_key: modelo,
      custos_detalhados,
      capex_detalhado,
      matriculas,
      sensibilidade: stresses,
    }
  }

  // Reconstrói scores_regionais (tree) a partir dos campos flat do DB
  // (relatorio_outputs.score_demografico/concorrencia/viabilidade). O viewer
  // consome `out.scores_regionais` mas o Supabase só guarda flat.
  const scoresRegionais = {
    demografico: out.score_demografico as number | null | undefined,
    concorrencia: out.score_concorrencia as number | null | undefined,
    competitivo: out.score_concorrencia as number | null | undefined, // alias
    viabilidade: out.score_viabilidade as number | null | undefined,
  }

  return {
    id: p.id,
    tipo_relatorio: (p.header.tipo_relatorio as string) ?? 'prospeccao_academia',
    data_execucao:
      (p.header.data_execucao as string) ?? (p.header.created_at as string) ?? '',
    input_canonico: p.input_canonico as unknown as RelatorioDetail['input_canonico'],
    output_consolidado: {
      ...out,
      scores_regionais: scoresRegionais,
      // Alias nomes esperados pelo viewer (que vinham do JSON canônico)
      aluguel_mediana_m2_observado: out.aluguel_mediana_m2 ?? null,
      aluguel_min_m2_observado: out.aluguel_min_m2 ?? null,
      aluguel_max_m2_observado: out.aluguel_max_m2 ?? null,
      alertas_financeiros: out.alertas ?? [],
      top_3_candidatos: (p.candidatos ?? []).slice(0, 3),
      // Competidores: passa direto (DB já tem rating_oficial, reviews jsonb,
      // bairro_concorrente, tem_24h). Telefone/website/whatsapp_link saem
      // como undefined até a Fase 2 do A3a enrichment.
      competitors_set: p.competidores ?? [],
      viabilidade_3_cenarios: cenariosByModelo,
      // Mapeia colunas flat do DB pros nomes esperados pelo viewer.
      // DB: prioridade, status_competitivo / Viewer: prioridade_ajustada, status
      bairros_alternativos: (p.bairros_alternativos ?? []).map((b) => ({
        ...b,
        prioridade_ajustada: b.prioridade_ajustada ?? b.prioridade,
        status: b.status ?? b.status_competitivo,
      })),
    } as unknown as OutputConsolidado,
    metadata_execucao: {
      schema_version: p.header.schema_version,
      adk_run_id: p.header.adk_run_id,
    },
  }
}

/**
 * Carrega detail via Supabase JS direto — 7 queries em paralelo (uma por
 * tabela filha). RLS filtra automaticamente pelo org_id do user logado.
 */
async function fetchDetailFromSupabase(id: string): Promise<BackendPayload> {
  const [
    header,
    inputs,
    outputs,
    candidatos,
    competidores,
    cenarios,
    sensibilidade,
    bairrosAlt,
  ] = await Promise.all([
    supabase.from('relatorios').select('*').eq('id', id).maybeSingle(),
    supabase.from('relatorio_inputs').select('*').eq('relatorio_id', id).maybeSingle(),
    supabase.from('relatorio_outputs').select('*').eq('relatorio_id', id).maybeSingle(),
    supabase.from('candidatos').select('*').eq('relatorio_id', id).order('posicao', { ascending: true }),
    supabase.from('competidores').select('*').eq('relatorio_id', id),
    supabase.from('cenarios_financeiros').select('*').eq('relatorio_id', id),
    supabase.from('sensibilidade_cenarios').select('*').eq('relatorio_id', id),
    supabase.from('bairros_alternativos').select('*').eq('relatorio_id', id).order('ordem', { ascending: true }),
  ])

  const firstErr = [header, inputs, outputs, candidatos, competidores, cenarios, sensibilidade, bairrosAlt]
    .map((r) => r.error)
    .find(Boolean)
  if (firstErr) throw new Error(`Supabase: ${firstErr.message}`)
  if (!header.data) throw new Error(`Relatório ${id} não encontrado`)

  return {
    id,
    header: header.data as Record<string, unknown>,
    input_canonico: (inputs.data as Record<string, unknown> | null) ?? null,
    output_consolidado: (outputs.data as Record<string, unknown> | null) ?? null,
    candidatos: (candidatos.data ?? []) as Record<string, unknown>[],
    competidores: (competidores.data ?? []) as Record<string, unknown>[],
    cenarios: (cenarios.data ?? []) as Record<string, unknown>[],
    sensibilidade: (sensibilidade.data ?? []) as Record<string, unknown>[],
    bairros_alternativos: (bairrosAlt.data ?? []) as Record<string, unknown>[],
  }
}

export function useRelatorioDetail(id: string | undefined) {
  const { user } = useAuth()
  const enabled = !!id && (USE_MOCKS || !!user)

  return useQuery({
    queryKey: ['relatorio', id, user?.id ?? 'anon'],
    enabled,
    queryFn: async (): Promise<RelatorioDetail> => {
      if (USE_MOCKS) {
        await new Promise((r) => setTimeout(r, 50))
        const raw = getMockRelatorioRaw(id!)
        if (!raw) throw new Error(`Relatório não encontrado: ${id}`)
        return raw as RelatorioDetail
      }
      const payload = await fetchDetailFromSupabase(id!)
      return adaptBackendToDetail(payload)
    },
  })
}
