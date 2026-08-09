// ============================================================
// config/agentes.ts — mapa ferramenta(tool) → agente, p/ o crachá do consultor.
// O backend devolve `acoes_executadas: [{ferramenta, status, resumo}]` por turno;
// cada ferramenta = um agente que "agiu". Aqui mapeamos pra ícone + rótulo + cor.
// ============================================================
import {
  AGENT_ICONS,
  IconeTecnico,
  IconeMercado,
  type Icon,
} from '@/components/icons/gymsite-icons'

export type SetorId = 'dados' | 'financeiro' | 'contabilidade' | 'marketing' | 'conhecimento' | 'tecnico'

export interface SetorStyle {
  bg: string
  text: string
  ring: string
}

/** Classes Tailwind por setor (chip do crachá). */
export const SETOR_STYLE: Record<SetorId, SetorStyle> = {
  dados: { bg: 'bg-sky-100', text: 'text-sky-700', ring: 'ring-sky-200' },
  financeiro: { bg: 'bg-emerald-100', text: 'text-emerald-700', ring: 'ring-emerald-200' },
  contabilidade: { bg: 'bg-amber-100', text: 'text-amber-700', ring: 'ring-amber-200' },
  marketing: { bg: 'bg-violet-100', text: 'text-violet-700', ring: 'ring-violet-200' },
  conhecimento: { bg: 'bg-rose-100', text: 'text-rose-700', ring: 'ring-rose-200' },
  tecnico: { bg: 'bg-amber-100', text: 'text-amber-700', ring: 'ring-amber-200' },
}

export interface AgenteMeta {
  label: string
  setor: SetorId
  icone: Icon
  /** Mascote PNG (marca) quando for um dos 5 especialistas. */
  img?: string
}

/** Nome da ferramenta (consultor_engine) → agente. */
export const TOOL_TO_AGENTE: Record<string, AgenteMeta> = {
  pesquisar_contexto_mercado: {
    label: 'Contexto de Mercado',
    setor: 'dados',
    icone: AGENT_ICONS.dados_context_builder,
    img: '/agentes/mercado.png',
  },
  buscar_pontos_comerciais: {
    label: 'Pontos Comerciais',
    setor: 'dados',
    icone: AGENT_ICONS.dados_geoscout,
    img: '/agentes/mercado.png',
  },
  analisar_demografia: {
    label: 'Demografia',
    setor: 'dados',
    icone: AGENT_ICONS.dados_demo_analyst,
    img: '/agentes/mercado.png',
  },
  pesquisar_concorrentes: {
    label: 'Concorrentes',
    setor: 'dados',
    icone: AGENT_ICONS.dados_competitor_search,
    img: '/agentes/mercado.png',
  },
  analisar_reviews_e_dores: {
    label: 'Reviews & Dores',
    setor: 'dados',
    icone: AGENT_ICONS.dados_competitor_analysis,
    img: '/agentes/mercado.png',
  },
  mapear_oferta_e_servicos: {
    label: 'Oferta & Serviços',
    setor: 'dados',
    icone: AGENT_ICONS.dados_market_research,
    img: '/agentes/mercado.png',
  },
  estimar_investimento: {
    label: 'Investimento',
    setor: 'financeiro',
    icone: AGENT_ICONS.financeiro_estimator,
    img: '/agentes/mercado.png',
  },
  gerar_relatorio_formal: {
    label: 'Relatório Formal',
    setor: 'marketing',
    icone: AGENT_ICONS.marketing_report_writer,
  },
  consultar_base_conhecimento: {
    label: 'Base de Conhecimento',
    setor: 'conhecimento',
    icone: AGENT_ICONS.conhecimento_rag_retriever,
  },
  consultar_catalogos_equipamentos: {
    label: 'Equipamentos',
    setor: 'tecnico',
    icone: IconeTecnico,
    img: '/agentes/tecnico.png',
  },
}

export function agenteDaFerramenta(ferramenta: string): AgenteMeta | undefined {
  return TOOL_TO_AGENTE[ferramenta]
}

export const ICONE_CONSULTOR: Icon = IconeMercado

export function mascoteDaMensagem(acoes?: { ferramenta: string }[]): Icon {
  const comAgente = acoes?.find((a) => TOOL_TO_AGENTE[a.ferramenta])
  return comAgente ? TOOL_TO_AGENTE[comAgente.ferramenta].icone : ICONE_CONSULTOR
}

/** Chave de `pesquisas_realizadas` → agente (ícone + cor), para o painel lateral
 * do consultor. É AQUI que o "handoff" vive: cada pesquisa acende seu ícone. */
export const PESQUISA_AGENTE: Record<string, { setor: SetorId; icone: Icon; img?: string }> = {
  mercado: { setor: 'dados', icone: AGENT_ICONS.dados_context_builder, img: '/agentes/mercado.png' },
  demografia: { setor: 'dados', icone: AGENT_ICONS.dados_demo_analyst, img: '/agentes/mercado.png' },
  concorrentes: { setor: 'dados', icone: AGENT_ICONS.dados_competitor_search, img: '/agentes/mercado.png' },
  reviews: { setor: 'dados', icone: AGENT_ICONS.dados_competitor_analysis, img: '/agentes/mercado.png' },
  oferta_concorrentes: { setor: 'dados', icone: AGENT_ICONS.dados_market_research, img: '/agentes/mercado.png' },
  pontos_comerciais: { setor: 'dados', icone: AGENT_ICONS.dados_geoscout, img: '/agentes/mercado.png' },
  investimento: { setor: 'financeiro', icone: AGENT_ICONS.financeiro_estimator, img: '/agentes/mercado.png' },
}
