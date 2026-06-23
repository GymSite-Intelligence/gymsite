// ============================================================
// config/handoff.ts — Configuração dos 5 Setores + 18 Agentes
// GymSite Intelligence v2.1
//
// FIXES aplicados:
//  - Ícones substituídos pelos SVGs customizados (gymsite-icons.tsx)
//  - Tipo LucideIcon removido (ver types_handoff.ts)
//  - ordemPipeline atualizado para 18 agentes (era inconsistente com docs)
// ============================================================

import type { SetorConfig, AgenteInfo, SetorId } from '../types/handoff'
import {
  IconeDados,
  IconeFinanceiro,
  IconeContabilidade,
  IconeMarketing,
  IconeConhecimento,
} from '../components/icons/gymsite-icons'

// ============================================================
// SETORES
// ============================================================

export const SETORES: Record<SetorId, SetorConfig> = {
  dados: {
    id: 'dados',
    nome: 'Inteligência de Dados',
    nomeCurto: 'Dados',
    cor: 'blue',
    corBg: 'bg-blue-100',
    corTexto: 'text-blue-700',
    corBorda: 'border-blue-200',
    corBgHover: 'hover:bg-blue-200',
    icone: IconeDados,
    descricao: 'Demografia, geolocalização, concorrência e research',
  },
  financeiro: {
    id: 'financeiro',
    nome: 'Planejamento Financeiro',
    nomeCurto: 'Financeiro',
    cor: 'emerald',
    corBg: 'bg-emerald-100',
    corTexto: 'text-emerald-700',
    corBorda: 'border-emerald-200',
    corBgHover: 'hover:bg-emerald-200',
    icone: IconeFinanceiro,
    descricao: 'Projeções, viabilidade, payback e sensibilidade',
  },
  contabilidade: {
    id: 'contabilidade',
    nome: 'Compliance & Registry',
    nomeCurto: 'Contabilidade',
    cor: 'amber',
    corBg: 'bg-amber-100',
    corTexto: 'text-amber-700',
    corBorda: 'border-amber-200',
    corBgHover: 'hover:bg-amber-200',
    icone: IconeContabilidade,
    descricao: 'CNPJ/CNO, diligência, validação e compliance',
  },
  marketing: {
    id: 'marketing',
    nome: 'Growth & Positioning',
    nomeCurto: 'Marketing',
    cor: 'violet',
    corBg: 'bg-violet-100',
    corTexto: 'text-violet-700',
    corBorda: 'border-violet-200',
    corBgHover: 'hover:bg-violet-200',
    icone: IconeMarketing,
    descricao: 'Captação, posicionamento ERRC, relatório e prospecção',
  },
  conhecimento: {
    id: 'conhecimento',
    nome: 'Knowledge Intelligence',
    nomeCurto: 'Conhecimento',
    cor: 'rose',
    corBg: 'bg-rose-100',
    corTexto: 'text-rose-700',
    corBorda: 'border-rose-200',
    corBgHover: 'hover:bg-rose-200',
    icone: IconeConhecimento,
    descricao: 'RAG D2 Cast — expertise qualitativa do mercado fitness',
  },
}

// ============================================================
// AGENTES — 18 agentes (v2.1 real, docs diziam 17 mas inclui ContactHunter)
// ============================================================

export const AGENTES_PIPELINE: AgenteInfo[] = [
  // MARKETING — Entrada
  { id: 'marketing_lead_capture', nome: 'Captação de Lead', setor: 'marketing', descricao: 'Coleta dados do visitante e qualifica o lead', ordemPipeline: 1 },

  // DADOS — Fase 1
  { id: 'dados_context_builder', nome: 'Context Builder', setor: 'dados', descricao: 'Consolida contexto de mercado (ticket, aluguel, tendência, CNPJ)', ordemPipeline: 2 },
  { id: 'dados_geoscout', nome: 'Geo Scout', setor: 'dados', descricao: 'Mapeia zonas comerciais e candidatos de localização', ordemPipeline: 3 },

  // DADOS — Fase 2 (paralelo)
  { id: 'dados_demo_analyst', nome: 'Demo Analyst', setor: 'dados', descricao: 'Analisa demografia IBGE, renda, perfil populacional', ordemPipeline: 4 },
  { id: 'dados_competitor_search', nome: 'Competitor Search', setor: 'dados', descricao: 'Busca e enriquece dados de concorrentes (Google Maps)', ordemPipeline: 5 },
  { id: 'dados_competitor_analysis', nome: 'Competitor Analysis', setor: 'dados', descricao: 'Analisa gaps, dores, saturação e oferta dos concorrentes', ordemPipeline: 6 },
  { id: 'dados_market_research', nome: 'Market Research', setor: 'dados', descricao: 'Pesquisa on-demand com Google Search Grounding', ordemPipeline: 7 },

  // FINANCEIRO — Fase 2 (paralelo)
  { id: 'financeiro_estimator', nome: 'Financial Estimator', setor: 'financeiro', descricao: 'Calcula 3 cenários: CAPEX, OPEX, payback, margem', ordemPipeline: 8 },
  { id: 'financeiro_sensibilidade', nome: 'Stress Test', setor: 'financeiro', descricao: 'Executa 3 stress tests de sensibilidade financeira', ordemPipeline: 9 },

  // CONTABILIDADE — Fase 3
  { id: 'contabilidade_parque_cnpj', nome: 'Parque CNPJ', setor: 'contabilidade', descricao: 'Estrutura dados cadastrais CNPJ/CNO do setor fitness', ordemPipeline: 10 },
  { id: 'contabilidade_diligencia', nome: 'Due Diligence', setor: 'contabilidade', descricao: 'Checklist de diligência imobiliária e legal', ordemPipeline: 11 },
  { id: 'contabilidade_validador', nome: 'Validador Cruzado', setor: 'contabilidade', descricao: 'Valida coerência financeira, demográfica e competitiva', ordemPipeline: 12 },

  // CONHECIMENTO — Fase 4 (RAG)
  { id: 'conhecimento_rag_retriever', nome: 'RAG Retriever', setor: 'conhecimento', descricao: 'Busca contexto qualitativo nas transcrições D2 Cast', ordemPipeline: 13 },
  { id: 'conhecimento_rag_insight', nome: 'Insight Engine', setor: 'conhecimento', descricao: 'Conecta conhecimento D2 Cast à decisão de negócio', ordemPipeline: 14 },
  { id: 'conhecimento_rag_cross', nome: 'Cross Reference', setor: 'conhecimento', descricao: 'Cruza dados quantitativos com expertise qualitativa', ordemPipeline: 15 },

  // MARKETING — Consolidação
  { id: 'marketing_positioning', nome: 'Positioning Strategist', setor: 'marketing', descricao: 'Framework ERRC + GAPs + ticket + veredito final', ordemPipeline: 16 },
  { id: 'marketing_report_writer', nome: 'Report Writer', setor: 'marketing', descricao: 'Consolida e narra o relatório executivo completo', ordemPipeline: 17 },
  { id: 'marketing_contact_hunter', nome: 'Contact Hunter', setor: 'marketing', descricao: 'Identifica decisor, canal e script de prospecção', ordemPipeline: 18 },
]

// ============================================================
// HELPERS
// ============================================================

export function getSetorConfig(agenteId: string): SetorConfig | undefined {
  const agente = AGENTES_PIPELINE.find((a) => a.id === agenteId)
  if (!agente) return undefined
  return SETORES[agente.setor]
}

export function getAgente(agenteId: string): AgenteInfo | undefined {
  return AGENTES_PIPELINE.find((a) => a.id === agenteId)
}

export function getAgentesPorSetor(setorId: SetorId): AgenteInfo[] {
  return AGENTES_PIPELINE.filter((a) => a.setor === setorId)
}
