/**
 * types/domain.ts — Tipos derivados manualmente do schema SQL (db/schema.sql).
 *
 * Quando o projeto Supabase estiver ativo, este arquivo será SUBSTITUÍDO por:
 *   npx supabase gen types typescript --project-id <ref> > src/types/database.ts
 *
 * E os tipos abaixo virarão re-exports tipo:
 *   export type RelatorioRow = Database['public']['Tables']['relatorios']['Row']
 *
 * Por enquanto, definimos manual pra alimentar os mocks e componentes.
 */

// ============================================================================
// ENUMS (espelham os ENUM types do Postgres)
// ============================================================================

export type Veredito =
  | 'APROVADO'
  | 'APROVADO COM RESSALVAS'
  | 'INVESTIGAR MAIS'
  | 'REPROVADO'

/** A9 — veredito de posicionamento estratégico (oceano azul / ERRC). */
export type VereditoOceano = 'OCEANO_AZUL' | 'TRANSICAO' | 'VERMELHO'

export type MarketWave = 'red' | 'transition' | 'blue'

export type RelatorioStatus = 'queued' | 'running' | 'done' | 'failed' | 'cancelled'

export type NegocioTipo =
  | 'academia'
  | 'crossfit_box'
  | 'studio_pilates'
  | 'studio_funcional'
  | 'outro'

export type CenarioModelo = 'low' | 'mid' | 'premium'

export type ViabilidadeStatus = 'ALTO' | 'MEDIO' | 'BAIXO' | 'INVIAVEL'

export type PrioridadeBairro = 'ALTA' | 'MEDIA' | 'BAIXA'

/**
 * Taxonomia fechada de dores (DORES_TAXONOMIA do classificador semântico A3a).
 * 14 categorias + fallback 'outra'.
 */
export type CategoriaDor =
  | 'lotacao'
  | 'equipamento_problema'
  | 'climatizacao'
  | 'limpeza_higiene'
  | 'atendimento_ruim'
  | 'preco_alto'
  | 'contrato_abusivo'
  | 'estacionamento'
  | 'estrutura_envelhecida'
  | 'ruido_alto'
  | 'horarios_limitados'
  | 'ausencia_servico'
  | 'seguranca'
  | 'outra'

export type SinalReview = 'positivo' | 'neutro' | 'negativo'
export type ConfiancaClassificacao = 'alta' | 'media' | 'baixa'

// ============================================================================
// JSONB shapes (não tipados pelo Supabase gen)
// ============================================================================

export interface ReviewJSON {
  rating: number
  quote_pt_br?: string
  quote_original?: string
  quote_curta?: string
  idioma_original?: string
  autor: string
  data_relativa?: string
  categoria_dor: CategoriaDor
  sinal?: SinalReview
  confianca_classificacao?: ConfiancaClassificacao
}

export interface ContatoDecisorJSON {
  tipo_ponto: string
  decisor_identificado: string
  empresa?: string
  telefone?: string
  email?: string
  whatsapp_link?: string
  canal_recomendado: 'WHATSAPP' | 'LIGACAO' | 'EMAIL' | 'LINKEDIN'
  observacao_canal?: string
  melhor_horario: string
  script_abordagem: string
  nivel_confianca_contato: 'ALTO' | 'MEDIO' | 'BAIXO'
  proximos_passos: string[]
}

// ============================================================================
// Table Rows (espelham as 9 tabelas do schema)
// ============================================================================

export interface Organization {
  id: string
  nome: string
  slug: string
  plano: 'free' | 'pro' | 'enterprise'
  limite_relatorios_mes: number
  created_at: string
  updated_at: string
}

export interface RelatorioRow {
  id: string
  org_id: string
  user_id: string | null
  tipo_relatorio: string
  status: RelatorioStatus
  adk_run_id: string | null
  tempo_execucao_segundos: number | null
  tokens_total: number | null
  custo_brl: number | null
  data_execucao: string | null
  created_at: string
  updated_at: string
  schema_version: string
  markdown_completo: string | null
  erro_mensagem: string | null
  notas_usuario: string | null
}

export interface RelatorioInputs {
  relatorio_id: string
  cidade: string
  uf: string | null
  bairro: string
  area_m2_min: number
  area_m2_max: number
  publico_alvo: string
  tipo_negocio: NegocioTipo
  estacionamento_obrigatorio: boolean
  bairros_indicados: string[]
  metadados: Record<string, unknown>
}

export interface RelatorioOutputs {
  relatorio_id: string
  veredito: Veredito
  score_bairro: number | null
  score_top1_candidato: number | null
  score_demografico: number | null
  score_concorrencia: number | null
  score_viabilidade: number | null
  nivel_saturacao: string | null
  rating_medio_concorrentes: number | null
  total_concorrentes_analisados: number | null
  modelo_recomendado: string | null
  aluguel_mensal: number | null
  fonte_aluguel: string | null
  aluguel_min_m2: number | null
  aluguel_max_m2: number | null
  aluguel_mediana_m2: number | null
  queries_aluguel_com_dados: number
  posicionamento_recomendado: string | null
  resumo_executivo: string | null
  justificativa_financeira: string | null
  contato_decisor: ContatoDecisorJSON | null
  market_context: Record<string, unknown> | null
  alertas: string[]
}

export interface CandidatoRow {
  id: string
  relatorio_id: string
  posicao: number
  nome: string
  endereco: string | null
  place_id: string | null
  tipo: string | null
  area_estimada_m2: number | null
  lat: number | null
  lng: number | null
  score_geoscout: number | null
  score_ancoragem: number | null
  score_geral: number | null
  motivo: string | null
  estimativa_visibilidade: string | null
  avenida_principal: boolean | null
  qualidade_sinal: string | null
  polos_geradores: string[]
  tipos_google: string[]
  street_view_url: string | null
  status_business: string | null
  proximo_passo: string | null
  tipo_imovel_codigo_onr: number | null
  tipo_imovel_label: string | null
  modalidade: string | null
  cartorio: Record<string, any> | null
  created_at: string
}

export interface CompetidorRow {
  id: string
  relatorio_id: string
  nome: string
  endereco: string | null
  bairro_concorrente: string | null
  place_id: string | null
  rating_oficial: number | null
  num_avaliacoes: number | null
  tem_24h: boolean
  reviews: ReviewJSON[]
  horarios_pico: Record<string, unknown> | null
  pico_semanal: string | null
  atividade_marketing: Record<string, unknown> | null
  origem_busca: 'nearby' | 'expandida_a0'
  created_at: string
}

export interface CenarioFinanceiroRow {
  id: string
  relatorio_id: string
  modelo: CenarioModelo
  ticket_medio: number | null
  capacidade_maxima_alunos: number | null
  alunos_projetados: number | null
  alunos_break_even: number | null
  receita_mensal: number | null
  custos_fixos: number | null
  marketing_mensal: number | null
  custos_totais: number | null
  lucro_mensal_estimado: number | null
  margem_percentual: number | null
  capex_estimado: number | null
  capital_giro: number | null
  investimento_total: number | null
  payback_meses: number | null
  viabilidade: ViabilidadeStatus | null
}

export interface BairroAlternativoRow {
  id: string
  relatorio_id: string
  bairro: string
  motivo: string | null
  status_competitivo: string | null
  ticket_sugerido: string | null
  prioridade: PrioridadeBairro
  concorrentes_no_bairro: number | null
  academias_existentes: string[]
  metodologia: string | null
  ordem: number
}

// ============================================================================
// View row (v_relatorios_resumo) — usada na listagem
// ============================================================================

export interface RelatorioResumo {
  id: string
  org_id: string
  user_id: string | null
  tipo_relatorio: string
  status: RelatorioStatus
  data_execucao: string | null
  tempo_execucao_segundos: number | null
  custo_brl: number | null
  cidade: string
  uf: string | null
  bairro: string
  area_m2_min: number
  area_m2_max: number
  publico_alvo: string
  tipo_negocio: NegocioTipo
  veredito: Veredito | null
  score_bairro: number | null
  score_top1_candidato: number | null
  modelo_recomendado: string | null
  aluguel_mediana_m2: number | null
  nivel_saturacao: string | null
  veredito_posicionamento?: VereditoOceano | null
  ticket_recomendado?: number | null
  gaps_count?: number | null
  market_wave?: MarketWave | null
  market_tier_qwen?: string | null
  created_at: string
}
