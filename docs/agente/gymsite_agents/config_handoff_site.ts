// ============================================================
// config/handoff_site.ts — versão SITE (degustação pública da landing)
// GymSite Intelligence — 5 agentes especialistas (ADK agents_site/)
//
// Difere do config/handoff.ts (pipeline LOGADO A0–A9, 18 agentes sequenciais):
// aqui é ROTEAMENTO (1 hop) — o roteador transfere via transfer_to_agent para
// UM especialista. Cada agente = 1 "setor" com ícone/cor/textos próprios.
//
// Os `id` batem com os nomes dos sub-agentes ADK em agents_site/agent.py
// (ResponsavelTecnico, Arquiteto, EngenheiroObra, Regulatorio, Mercado) — é o
// valor mandado no campo `agente` do POST /conversar e devolvido no badge.
// ============================================================

import type { IconComponent } from '../types/handoff'
import {
  IconeTecnico,
  IconeArquiteto,
  IconeEngenheiro,
  IconeRegulatorio,
  IconeMercado,
} from '../components/icons/gymsite-icons'

export type AgenteSiteId =
  | 'ResponsavelTecnico'
  | 'Arquiteto'
  | 'EngenheiroObra'
  | 'Regulatorio'
  | 'Mercado'

export interface AgenteSiteConfig {
  id: AgenteSiteId
  nome: string
  nomeCurto: string
  cor: string
  corBg: string
  corTexto: string
  corBorda: string
  corBgHover: string
  icone: IconComponent
  descricao: string
  /** Textos por agente para o chat da landing (seletor de ícones). */
  saudacao: string
  placeholder: string
  exemplo: string
}

export const AGENTES_SITE: Record<AgenteSiteId, AgenteSiteConfig> = {
  Mercado: {
    id: 'Mercado',
    nome: 'Mercado & Viabilidade',
    nomeCurto: 'Mercado',
    cor: 'violet',
    corBg: 'bg-violet-100',
    corTexto: 'text-violet-700',
    corBorda: 'border-violet-200',
    corBgHover: 'hover:bg-violet-200',
    icone: IconeMercado,
    descricao: 'Concorrência, saturação do bairro e potencial do ponto',
    saudacao: 'Quer saber se vale a pena abrir uma academia aí? Me diga a cidade e o bairro.',
    placeholder: 'Ex.: tem concorrente no Cocó, Fortaleza?',
    exemplo: 'Quantos concorrentes existem num raio de 1,5 km do bairro Cocó, em Fortaleza?',
  },
  ResponsavelTecnico: {
    id: 'ResponsavelTecnico',
    nome: 'Responsável Técnico',
    nomeCurto: 'Técnico',
    cor: 'amber',
    corBg: 'bg-amber-100',
    corTexto: 'text-amber-700',
    corBorda: 'border-amber-200',
    corBgHover: 'hover:bg-amber-200',
    icone: IconeTecnico,
    descricao: 'Que equipamento comprar, quanto cabe e quais fornecedores',
    saudacao: 'Monto o mix de equipamentos da sua academia. Qual o porte, o tipo e o público?',
    placeholder: 'Ex.: o que comprar para 300 m² de musculação?',
    exemplo: 'Quero montar 300 m² de musculação, público wellness 25-45. Que mix sugere?',
  },
  Arquiteto: {
    id: 'Arquiteto',
    nome: 'Arquiteto',
    nomeCurto: 'Arquiteto',
    cor: 'sky',
    corBg: 'bg-sky-100',
    corTexto: 'text-sky-700',
    corBorda: 'border-sky-200',
    corBgHover: 'hover:bg-sky-200',
    icone: IconeArquiteto,
    descricao: 'Zonas, fluxos, vestiários/sanitários, acessibilidade e projeto',
    saudacao: 'Desenho o espaço da sua academia: zonas, fluxos e ambientes. Qual a metragem?',
    placeholder: 'Ex.: quantos banheiros para 200 pessoas?',
    exemplo: 'Como organizar as zonas de uma academia de 300 m²? Qual o fluxo ideal?',
  },
  EngenheiroObra: {
    id: 'EngenheiroObra',
    nome: 'Engenheiro de Obra',
    nomeCurto: 'Engenheiro',
    cor: 'slate',
    corBg: 'bg-slate-100',
    corTexto: 'text-slate-700',
    corBorda: 'border-slate-200',
    corBgHover: 'hover:bg-slate-200',
    icone: IconeEngenheiro,
    descricao: 'Estrutura/laje, instalações, licenças e obra (retrofit × zero)',
    saudacao: 'Vejo se a obra viabiliza: estrutura, instalações e licenças. Vai adaptar um ponto ou construir do zero?',
    placeholder: 'Ex.: a laje aguenta os equipamentos?',
    exemplo: 'Vou adaptar uma loja existente para academia — a laje aguenta os equipamentos?',
  },
  Regulatorio: {
    id: 'Regulatorio',
    nome: 'Regulatório',
    nomeCurto: 'Regulatório',
    cor: 'emerald',
    corBg: 'bg-emerald-100',
    corTexto: 'text-emerald-700',
    corBorda: 'border-emerald-200',
    corBgHover: 'hover:bg-emerald-200',
    icone: IconeRegulatorio,
    descricao: 'CREF, responsável técnico, Lei 9.696, anuidade e licenças',
    saudacao: 'Tiro suas dúvidas legais para abrir academia: CREF, licenças, quem pode dar aula.',
    placeholder: 'Ex.: preciso de registro no CREF?',
    exemplo: 'Preciso de registro no CREF e responsável técnico para abrir academia?',
  },
}

/** Ordem de exibição no seletor da landing (Mercado primeiro = porta de entrada). */
export const ORDEM_SITE: AgenteSiteId[] = [
  'Mercado',
  'ResponsavelTecnico',
  'Arquiteto',
  'EngenheiroObra',
  'Regulatorio',
]

export function getAgenteSite(id: string): AgenteSiteConfig | undefined {
  return (AGENTES_SITE as Record<string, AgenteSiteConfig>)[id]
}

export const AGENTE_SITE_DEFAULT: AgenteSiteId = 'Mercado'
