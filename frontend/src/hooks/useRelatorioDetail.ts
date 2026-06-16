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
import { resolveRelatorioUuid } from '@/lib/relatorio-id'
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
  /** Status do pipeline no Supabase (queued | running | done | failed). */
  pipeline_status?: string
  erro_mensagem?: string | null
  input_canonico: {
    cidade: string
    uf?: string
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
  /** Auditoria da fonte de aluguel (12/06): amostras com URL + meta do gate comercial. */
  aluguel_amostras?: import('@/components/domain/AluguelFonteAuditavel').AluguelAmostra[] | null
  aluguel_fonte_meta?: import('@/components/domain/AluguelFonteAuditavel').AluguelFonteMeta | null
  posicionamento_recomendado?: string | null
  /** Schema v1.8: output A9 PositioningStrategist (ERRC / oceano azul) */
  posicionamento_estrategico?: PosicionamentoEstrategicoJSON | null
  resumo_executivo?: string | null
  top_3_candidatos: CandidatoJSON[]
  /** Diagnóstico A1 GeoScout (erro/aviso/total) para banner no viewer. */
  coleta_geografica?: {
    total_candidatos?: number
    listings_reais?: number
    estrategia?: string
    qualidade_sinal?: string
    aviso?: string
    erro?: string
  }
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
  /** Schema v1.7: densidade no raio + referência CNPJ */
  panorama_competitivo?: PanoramaCompetitivoJSON
  total_encontrados_raio?: number | null
  total_encontrados_raio_nearby?: number | null
  agregados_competicao_places?: {
    count_total?: number | null
    count_rating_ge_4_2?: number | null
    status?: string
    radius_meters?: number
  } | null
  fonte_geocode?: string | null
  fonte_busca_competidores?: string | null
  top_independentes?: AcademiaResumoJSON[]
  academias_analisadas?: AcademiaResumoJSON[]
  /** Schema v1.7: lista nominal de entrantes CNPJ (90d). */
  entrantes_cnpj_90d?: EntrantesCnpj90dJSON
  /** Obras fitness em andamento (CNO) + benchmark tempo obra. */
  obras_cno_em_curso?: ObrasCnoEmCursoJSON
  /** Demanda futura datada (Apêndice B) — obras residenciais no raio → captura T+24. */
  demanda_futura?: DemandaFuturaJSON
  /** Anéis competitivos (Apêndice D) — score ponderado por proximidade. */
  aneis_competitivos?: AneisCompetitivosJSON
  /** Demografia do bairro: renda (CKAN) + população/ocupação (Censo 2022). Fontes reais. */
  demografia_bairro?: DemografiaBairroJSON
}

export interface DemografiaBairroJSON {
  cidade?: string
  bairro?: string | null
  renda_media?: number | null
  idh_renda?: number | null
  ranking_idh?: string | null
  renda_fonte?: string | null
  renda_data_referencia?: string | null
  populacao?: number | null
  domicilios?: number | null
  media_moradores?: number | null
  populacao_fonte?: string | null
  censo_n_setores?: number | null
}

export interface DemandaFuturaObraJSON {
  empreendimento?: string | null
  construtora?: string | null
  bairro?: string | null
  unidades_est?: number | null
  unidades_fonte?: string | null
  entrega?: string | null
  amenidade_fitness?: boolean
  captura_est?: number | null
  moradores_est?: number | null
  receita_mensal_est?: number | null
  confianca?: string | null
  provavel_residencial?: boolean
  base_residencial?: string | null
  ni_responsavel?: string | null
  fonte_url?: string | null
}

export interface DemandaFuturaJSON {
  status?: string
  n_obras?: number
  provavel_residencial_n?: number
  residencial_por_base?: Record<string, number>
  refinadas?: number
  receita_total_mensal_est?: number
  captura_total_est?: number
  moradores_total_est?: number
  janela_entrega?: { de?: string; ate?: string } | null
  obras?: DemandaFuturaObraJSON[]
  fonte?: string
}

export interface AneisCompetitivosJSON {
  por_anel?: { NO_BAIRRO?: number; FRONTEIRA?: number; REGIONAL?: number }
  score_competitivo_ponderado?: number
  concorrentes_no_bairro?: number
  no_bairro_por_porte?: { pequena?: number; media?: number; grande?: number }
  total_concorrentes?: number
  nota?: string
}

export interface PosicionamentoEstrategicoJSON {
  framework_errc?: {
    eliminar?: string[]
    reduzir?: string[]
    aumentar?: string[]
    criar?: string[]
  }
  mapa_servicos?: {
    concorrente?: string
    servicos?: Record<string, number>
  }[]
  gaps_identificados?: {
    gap?: string
    descricao?: string
    potencial_ticket?: string
    dificuldade_implementacao?: string
  }[]
  recomendacao_ticket?: {
    ticket_recomendado?: number
    ticket_minimo?: number
    ticket_maximo?: number
    justificativa?: string
    comparativo_mercado?: Record<string, number>
  }
  veredito_posicionamento?: string
  /** veredito original do LLM, preservado quando o headroom determinístico sobrepõe */
  veredito_posicionamento_llm?: string
  fonte_veredito?: string
  /** Posicionamento determinístico por headroom de renda (IPECE Censo 2022) */
  headroom_renda?: {
    renda_pc?: number
    renda_resp_domicilio?: number
    renda_percentil?: number
    ranking_cidade?: number
    tier_modelo_percentil?: string
    ticket_teto_sustentavel?: number
    ticket_mercado?: number | null
    headroom_premium?: number | null
    headroom_ratio?: number | null
    veredito_posicionamento?: string
    fonte_renda?: string
    ano_renda?: number
  }
  justificativa_veredito?: string
  markdown?: string
  /** langcache | gemini — diagnóstico dev quando A9 reutiliza resposta */
  fonte_geracao?: string
  cache_prompt?: string
  erro?: string
  raw_output?: string
}

export interface ComposicaoSegmentoJSON {
  count: number
  pct: number
  label?: string
}

export interface SocioAdministradorJSON {
  nome?: string | null
  qualificacao?: string | null
  email?: string | null
  telefone?: string | null
  contato_individual_disponivel?: boolean
}

export interface EntranteCnpjJSON {
  cnpj: string
  cnpj_formatado?: string
  nome_fantasia?: string | null
  razao_social?: string | null
  nome_exibicao?: string | null
  nome_fantasia_inferido_de?: string | null
  razao_social_indisponivel?: boolean
  bairro?: string | null
  bairro_fonte?: string | null
  email_empresa?: string | null
  telefone_empresa?: string | null
  email_socio_administrador?: string | null
  telefone_socio_administrador?: string | null
  linkedin_url?: string | null
  socio_administrador?: SocioAdministradorJSON | null
  qsa?: { nome?: string; qualificacao?: string }[]
  contato_validado?: boolean
  contato_validado_em?: string | null
  contato_validado_por?: string | null
  dados_completos?: boolean
  lacunas_contato?: string[]
  data_abertura?: string
  endereco?: string | null
  cep?: string | null
  cnae_principal?: string
  ref_month?: string
  lat?: number
  lng?: number
  segmento_operacao?: string
  segmento_label?: string
  segmento_confianca?: 'alta' | 'media' | 'baixa' | string
  segmento_metodo?: string
  segmento_requer_validacao?: boolean
  incluir_no_parque?: boolean
}

export interface ObraCnoEmCursoJSON {
  cno?: string
  nome_obra?: string
  area_m2?: number
  bairro?: string | null
  data_inicio?: string | null
  previsao_encerramento_estimada?: string | null
  duracao_obra_dias_estimada?: number | null
  logradouro?: string | null
  numero?: string | null
  situacao_obra?: string
}

export interface BenchmarkTempoObraCnoJSON {
  status?: string
  amostra_valida?: number
  metricas?: {
    n?: number
    dias_por_m2_mediana?: number
    dias_por_m2_p25?: number
    dias_por_m2_p75?: number
    duracao_dias_mediana?: number
  }
  por_porte_m2?: Record<
    string,
    {
      n?: number
      dias_por_m2_mediana?: number
      duracao_dias_mediana?: number
    }
  >
  nota_metodologica?: string
}

export interface FiltroBairroCnoJSON {
  bairro_filtro?: string | null
  bairro_filtro_chave?: string | null
  total_antes_filtro?: number
  total_apos_filtro_bairro?: number
}

export interface ObrasCnoEmCursoJSON {
  status?: string
  motivo?: string
  cidade?: string
  uf?: string
  fonte?: string
  filtro?: string
  total_obras_em_curso?: number
  total_obras_em_curso_municipio?: number
  filtro_bairro?: FiltroBairroCnoJSON | null
  obras?: ObraCnoEmCursoJSON[]
  benchmark_tempo_obra?: BenchmarkTempoObraCnoJSON | null
  nota_metodologica?: string
}

export interface EntrantesCnpj90dJSON {
  status?: string
  motivo?: string
  cidade?: string
  uf?: string
  dias?: number
  cutoff?: string
  total?: number
  entrantes_incompletos?: number
  enriquecimento_meta?: Record<string, unknown>
  entrantes?: EntranteCnpjJSON[]
  novas_unidades_90d_por_segmento?: Record<string, number>
  fonte?: string
  data_coleta?: string
  nota?: string
}

export interface PanoramaCompetitivoJSON {
  nivel_saturacao?: string
  nivel_saturacao_amostra?: string
  total_encontrados_raio?: number
  total_concorrentes_analisados?: number
  densidade_por_km2?: number
  raio_km?: number
  cnpj_parque_ativo_cidade?: number | null
  /** @deprecated use cnpj_parque_ativo_cidade */
  cnpj_academias_ativas_cidade?: number | null
  metodologia?: string
}

export interface AcademiaResumoJSON {
  nome: string
  rating?: number | string | null
  num_avaliacoes?: number | string | null
  endereco?: string
  bairro?: string
  place_id?: string
  is_independente?: boolean
  rede_vinculada?: string | null
}

export interface CoberturaRedesA0JSON {
  redes_solicitadas: string[]
  redes_cobertas: string[]
  redes_locais_validadas?: string[]
  redes_detectadas_osm?: string[]
  redes_nao_encontradas: string[]
  concorrentes_excluidos?: { nome: string; motivo: string }[]
  tem_redes_fantasma: boolean
  fonte_redes_locais?: string
}

export interface MarketContextJSON {
  cidade?: string
  bairro?: string
  uf?: string
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
  /** Redes citadas pelo DR sem confirmação local (schema v1.11). */
  redes_dr_nao_validadas?: string[]
  tendencia_mercado?: 'crescimento' | 'estavel' | 'retracao' | string
  regulamentacao_resumo?: string
  insights_estrategicos?: string[]
  /** Schema v1.7: novas unidades com abertura nos últimos ~90d (cidade/UF). */
  novos_cnpj_fitness_90d?: number
  /** Schema v1.8: parque ativo no município (snapshot CNPJ RFB). */
  parque_ativo_total?: number | null
  /** Schema v1.9: composição do parque por segmento. */
  composicao_parque?: Record<string, ComposicaoSegmentoJSON>
  novas_unidades_90d_por_segmento?: Record<string, number>
  /** Fatos A0: CNPJ/CNO sem interpretação inventada. */
  fatos_parque_cnpj?: {
    fonte?: string
    metricas?: Record<string, unknown>
    indicadores_derivados?: Record<string, unknown>
    cruzamento_cno?: Record<string, unknown>
    lacunas?: string[]
  }
  /** @deprecated use parque_ativo_total */
  academias_ativas_cidade_cnpj?: number | null
  /** Contagem por ano de data_inicio_atividade (recorte alinhado ao resumo CNPJ). */
  serie_aberturas_anual?: Record<string, number>
  fonte_entrantes?: string
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
  /** true = coords vieram do geocode do endereço; false/undefined = fallback centro-cidade. */
  geocoded?: boolean
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
  /** Listing imobiliário (OLX / ImovelWeb) */
  listing_url?: string
  listing_id?: string
  price_raw?: string
  listing_source?: string
  fonte?: string
  tipo_imovel_codigo_onr?: number | null
  tipo_imovel_label?: string | null
  modalidade?: string | null
  cartorio?: Record<string, any> | null
}

export interface PlanoPrecoJSON {
  plano?: string
  preco_mensal?: string
  inclui?: string[]
  fidelidade?: string
}

export interface InstagramProfileJSON {
  username?: string
  name?: string
  bio?: string | null
  followers?: number | null
  following?: number | null
  posts?: number | null
  is_verified?: boolean
  external_link?: string | null
}

export interface CompetidorJSON {
  nome: string
  planos_precos?: PlanoPrecoJSON[] | null
  instagram_profile?: InstagramProfileJSON | null
  /** Google Place ID — cache SearchAPI / popular_times (Tier 0). */
  place_id?: string | null
  lat?: number | null
  lng?: number | null
  distancia_km?: number | null
  google_maps_uri?: string | null
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
  /** google_places | overpass_osm — vazio se fallback A3b apenas */
  fonte_busca_competidores?: string | null
  /** false = bairro genérico de fallback, sem busca Places real confiável */
  dados_confiaveis?: boolean
  metodologia?: string
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

/** A6 grava resumo só no markdown; extrai quando a coluna DB veio null. */
function extractResumoFromMarkdown(markdown: unknown): string | null {
  if (typeof markdown !== 'string' || !markdown.trim()) return null
  const match = markdown.match(
    /##\s*🎯\s*Resumo Executivo\s*\n([\s\S]*?)\n---/,
  )
  const text = match?.[1]?.trim()
  return text || null
}

function mapCompetidorRow(row: Record<string, unknown>): CompetidorJSON {
  const reviews = row.reviews ?? row.reviews_traduzidas
  const latRaw = row.lat
  const lngRaw = row.lng
  const lat =
    latRaw != null && Number(latRaw) !== 0 ? Number(latRaw) : undefined
  const lng =
    lngRaw != null && Number(lngRaw) !== 0 ? Number(lngRaw) : undefined
  return {
    nome: String(row.nome ?? ''),
    planos_precos: Array.isArray(row.planos_precos)
      ? (row.planos_precos as PlanoPrecoJSON[])
      : null,
    instagram_profile:
      row.instagram_profile && typeof row.instagram_profile === 'object'
        ? (row.instagram_profile as InstagramProfileJSON)
        : null,
    place_id: typeof row.place_id === 'string' ? row.place_id : null,
    lat: lat ?? null,
    lng: lng ?? null,
    distancia_km:
      row.distancia_km != null ? Number(row.distancia_km) : null,
    google_maps_uri:
      typeof row.google_maps_uri === 'string' ? row.google_maps_uri : null,
    rating_oficial:
      row.rating_oficial != null ? Number(row.rating_oficial) : undefined,
    rating_geral: row.rating_geral != null ? Number(row.rating_geral) : undefined,
    num_avaliacoes:
      row.num_avaliacoes != null ? Number(row.num_avaliacoes) : undefined,
    endereco: typeof row.endereco === 'string' ? row.endereco : undefined,
    bairro_concorrente:
      typeof row.bairro_concorrente === 'string' ? row.bairro_concorrente : undefined,
    tem_24h: Boolean(row.tem_24h),
    telefone: typeof row.telefone === 'string' ? row.telefone : null,
    website: typeof row.website === 'string' ? row.website : null,
    whatsapp_link:
      typeof row.whatsapp_link === 'string' ? row.whatsapp_link : null,
    horarios_pico:
      row.horarios_pico != null && typeof row.horarios_pico === 'object'
        ? (row.horarios_pico as Record<string, Record<string, number>>)
        : null,
    pico_semanal: typeof row.pico_semanal === 'string' ? row.pico_semanal : null,
    reviews: Array.isArray(reviews) ? (reviews as ReviewJSON[]) : undefined,
    reviews_traduzidas: Array.isArray(row.reviews_traduzidas)
      ? (row.reviews_traduzidas as ReviewJSON[])
      : undefined,
  }
}

function mapCandidatoRow(row: Record<string, unknown>): CandidatoJSON {
  const listingUrl =
    typeof row.listing_url === 'string' ? row.listing_url : undefined
  const website =
    (typeof row.website === 'string' ? row.website : undefined) || listingUrl
  const polos = row.polos_geradores
  const tipos = row.tipos_google ?? row.tipos

  return {
    nome: String(row.nome ?? ''),
    endereco: String(row.endereco ?? ''),
    area_estimada_m2: Number(row.area_estimada_m2 ?? 0),
    lat: row.lat != null ? Number(row.lat) : undefined,
    lng: row.lng != null ? Number(row.lng) : undefined,
    score_geoscout: Number(row.score_geoscout ?? 0),
    score_ancoragem: Number(row.score_ancoragem ?? 0),
    motivo: String(row.motivo ?? ''),
    polos_geradores: Array.isArray(polos) ? (polos as string[]) : [],
    street_view_url:
      typeof row.street_view_url === 'string' ? row.street_view_url : undefined,
    geocoded: typeof row.geocoded === 'boolean' ? row.geocoded : undefined,
    estimativa_visibilidade:
      typeof row.estimativa_visibilidade === 'string'
        ? row.estimativa_visibilidade
        : undefined,
    avenida_principal:
      row.avenida_principal != null ? Boolean(row.avenida_principal) : undefined,
    qualidade_sinal:
      typeof row.qualidade_sinal === 'string' ? row.qualidade_sinal : undefined,
    place_id: typeof row.place_id === 'string' ? row.place_id : undefined,
    tipos: Array.isArray(tipos) ? (tipos as string[]) : undefined,
    telefone: typeof row.telefone === 'string' ? row.telefone : undefined,
    website,
    tem_24h: Boolean(row.tem_24h),
    listing_url: listingUrl,
    listing_id: typeof row.listing_id === 'string' ? row.listing_id : undefined,
    price_raw: typeof row.price_raw === 'string' ? row.price_raw : undefined,
    listing_source:
      typeof row.listing_source === 'string' ? row.listing_source : undefined,
    fonte: typeof row.fonte === 'string' ? row.fonte : undefined,
    tipo_imovel_codigo_onr: row.tipo_imovel_codigo_onr != null ? Number(row.tipo_imovel_codigo_onr) : undefined,
    tipo_imovel_label: typeof row.tipo_imovel_label === 'string' ? row.tipo_imovel_label : undefined,
    modalidade: typeof row.modalidade === 'string' ? row.modalidade : undefined,
    cartorio: row.cartorio != null ? (row.cartorio as Record<string, any>) : undefined,
  }
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

    // Reagrupa as 12 colunas custo_* em custos_detalhados.
    // Runs antigos (Bessa 11/06) gravaram só agregados — colunas custo_*/
    // capex_* NULL. Converter NULL→0 aqui fazia o KPI mostrar "aluguel R$ 0"
    // e o recálculo do kit fabricar capex/payback irreais a partir dos zeros.
    // Breakdown ausente → undefined: KPI cai pro aluguel_mensal do output e
    // o recálculo preserva os agregados originais do A4.
    const temBreakdownCustos = c.custo_aluguel != null || c.custo_folha != null
    const temBreakdownCapex = c.capex_equipamentos != null || c.capex_obra_adaptacao != null
    const custos_detalhados = !temBreakdownCustos ? undefined : {
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
    const capex_detalhado = !temBreakdownCapex ? undefined : {
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

  const resumoExecutivo =
    (typeof out.resumo_executivo === 'string' ? out.resumo_executivo : null) ||
    extractResumoFromMarkdown(p.header.markdown_completo)

  return {
    id: p.id,
    tipo_relatorio: (p.header.tipo_relatorio as string) ?? 'prospeccao_academia',
    pipeline_status: (p.header.status as string) ?? undefined,
    erro_mensagem: (p.header.erro_mensagem as string | null) ?? null,
    data_execucao:
      (p.header.data_execucao as string) ?? (p.header.created_at as string) ?? '',
    input_canonico: p.input_canonico as unknown as RelatorioDetail['input_canonico'],
    output_consolidado: {
      ...out,
      resumo_executivo: resumoExecutivo,
      scores_regionais: scoresRegionais,
      // Alias nomes esperados pelo viewer (que vinham do JSON canônico)
      aluguel_mediana_m2_observado: out.aluguel_mediana_m2 ?? null,
      aluguel_amostras: out.aluguel_amostras ?? null,
      aluguel_fonte_meta: out.aluguel_fonte_meta ?? null,
      aluguel_min_m2_observado: out.aluguel_min_m2 ?? null,
      aluguel_max_m2_observado: out.aluguel_max_m2 ?? null,
      alertas_financeiros: out.alertas ?? [],
      top_3_candidatos: (p.candidatos ?? [])
        .map((c) => mapCandidatoRow(c as Record<string, unknown>)),
      competitors_set: (p.competidores ?? []).map((c) =>
        mapCompetidorRow(c as Record<string, unknown>),
      ),
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
  const relatorioId = await resolveRelatorioUuid(id)

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
    supabase.from('relatorios').select('*').eq('id', relatorioId).is('deleted_at', null).maybeSingle(),
    supabase.from('relatorio_inputs').select('*').eq('relatorio_id', relatorioId).maybeSingle(),
    supabase.from('relatorio_outputs').select('*').eq('relatorio_id', relatorioId).maybeSingle(),
    supabase.from('candidatos').select('*').eq('relatorio_id', relatorioId).order('posicao', { ascending: true }),
    supabase.from('competidores').select('*').eq('relatorio_id', relatorioId),
    supabase.from('cenarios_financeiros').select('*').eq('relatorio_id', relatorioId),
    supabase.from('sensibilidade_cenarios').select('*').eq('relatorio_id', relatorioId),
    supabase.from('bairros_alternativos').select('*').eq('relatorio_id', relatorioId).order('ordem', { ascending: true }),
  ])

  const firstErr = [header, inputs, outputs, candidatos, competidores, cenarios, sensibilidade, bairrosAlt]
    .map((r) => r.error)
    .find(Boolean)
  if (firstErr) throw new Error(`Supabase: ${firstErr.message}`)
  if (!header.data) throw new Error(`Relatório ${id} não encontrado`)

  return {
    id: relatorioId,
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
