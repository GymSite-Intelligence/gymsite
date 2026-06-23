// ============================================================
// components/icons/gymsite-icons.tsx
// Ícones dos agentes GymSite (arte SVG real). Vite importa .svg como URL →
// renderizamos via <img>. `className` controla o tamanho.
// SVGs em ./agent-svg/ (copiados de docs/agente/gymsite_agents/icons/).
// ============================================================
import type { ComponentType } from 'react'

type IconProps = { className?: string }
export type Icon = ComponentType<IconProps>

// Setores (pipeline)
import dados from './agent-svg/dados.svg'
import financeiro from './agent-svg/financeiro.svg'
import contabilidade from './agent-svg/contabilidade.svg'
import marketing from './agent-svg/marketing.svg'
import conhecimento from './agent-svg/conhecimento.svg'
// Site
import mercado from './agent-svg/mercado.svg'
import tecnico from './agent-svg/tecnico.svg'
import arquiteto from './agent-svg/arquiteto.svg'
import engenheiro from './agent-svg/engenheiro.svg'
import regulatorio from './agent-svg/regulatorio.svg'
// 18 do pipeline
import marketing_lead_capture from './agent-svg/marketing_lead_capture.svg'
import dados_context_builder from './agent-svg/dados_context_builder.svg'
import dados_geoscout from './agent-svg/dados_geoscout.svg'
import dados_demo_analyst from './agent-svg/dados_demo_analyst.svg'
import dados_competitor_search from './agent-svg/dados_competitor_search.svg'
import dados_competitor_analysis from './agent-svg/dados_competitor_analysis.svg'
import dados_market_research from './agent-svg/dados_market_research.svg'
import financeiro_estimator from './agent-svg/financeiro_estimator.svg'
import financeiro_sensibilidade from './agent-svg/financeiro_sensibilidade.svg'
import contabilidade_parque_cnpj from './agent-svg/contabilidade_parque_cnpj.svg'
import contabilidade_diligencia from './agent-svg/contabilidade_diligencia.svg'
import contabilidade_validador from './agent-svg/contabilidade_validador.svg'
import conhecimento_rag_retriever from './agent-svg/conhecimento_rag_retriever.svg'
import conhecimento_rag_insight from './agent-svg/conhecimento_rag_insight.svg'
import conhecimento_rag_cross from './agent-svg/conhecimento_rag_cross.svg'
import marketing_positioning from './agent-svg/marketing_positioning.svg'
import marketing_report_writer from './agent-svg/marketing_report_writer.svg'
import marketing_contact_hunter from './agent-svg/marketing_contact_hunter.svg'

function svgIcon(src: string, alt: string): Icon {
  const C = ({ className }: IconProps) => (
    <img src={src} alt={alt} className={className} draggable={false} />
  )
  C.displayName = `Icone(${alt})`
  return C
}

// Setores
export const IconeDados = svgIcon(dados, 'Dados')
export const IconeFinanceiro = svgIcon(financeiro, 'Financeiro')
export const IconeContabilidade = svgIcon(contabilidade, 'Contabilidade')
export const IconeMarketing = svgIcon(marketing, 'Marketing')
export const IconeConhecimento = svgIcon(conhecimento, 'Conhecimento')
// Site
export const IconeMercado = svgIcon(mercado, 'Mercado')
export const IconeTecnico = svgIcon(tecnico, 'Responsável Técnico')
export const IconeArquiteto = svgIcon(arquiteto, 'Arquiteto')
export const IconeEngenheiro = svgIcon(engenheiro, 'Engenheiro de Obra')
export const IconeRegulatorio = svgIcon(regulatorio, 'Regulatório')

// 18 do pipeline — por id
export const AGENT_ICONS: Record<string, Icon> = {
  marketing_lead_capture: svgIcon(marketing_lead_capture, 'Captação de Lead'),
  dados_context_builder: svgIcon(dados_context_builder, 'Context Builder'),
  dados_geoscout: svgIcon(dados_geoscout, 'Geo Scout'),
  dados_demo_analyst: svgIcon(dados_demo_analyst, 'Demo Analyst'),
  dados_competitor_search: svgIcon(dados_competitor_search, 'Competitor Search'),
  dados_competitor_analysis: svgIcon(dados_competitor_analysis, 'Competitor Analysis'),
  dados_market_research: svgIcon(dados_market_research, 'Market Research'),
  financeiro_estimator: svgIcon(financeiro_estimator, 'Financial Estimator'),
  financeiro_sensibilidade: svgIcon(financeiro_sensibilidade, 'Stress Test'),
  contabilidade_parque_cnpj: svgIcon(contabilidade_parque_cnpj, 'Parque CNPJ'),
  contabilidade_diligencia: svgIcon(contabilidade_diligencia, 'Due Diligence'),
  contabilidade_validador: svgIcon(contabilidade_validador, 'Validador Cruzado'),
  conhecimento_rag_retriever: svgIcon(conhecimento_rag_retriever, 'RAG Retriever'),
  conhecimento_rag_insight: svgIcon(conhecimento_rag_insight, 'Insight Engine'),
  conhecimento_rag_cross: svgIcon(conhecimento_rag_cross, 'Cross Reference'),
  marketing_positioning: svgIcon(marketing_positioning, 'Positioning Strategist'),
  marketing_report_writer: svgIcon(marketing_report_writer, 'Report Writer'),
  marketing_contact_hunter: svgIcon(marketing_contact_hunter, 'Contact Hunter'),
}
