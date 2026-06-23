// ============================================================
// components/icons/gymsite-icons.tsx
// Ícones dos agentes GymSite — arte real (SVG do usuário), não mais placeholder.
//
// Os arquivos .svg vivem em ./svg/ (copie a pasta docs/agente/gymsite_agents/icons/
// do repo de handoff para components/icons/svg/ no gym-insight-hub).
// Vite importa .svg como URL (default export) → renderizamos via <img>.
// `className` controla o tamanho (ex.: <IconeDados className="h-5 w-5" />).
// ============================================================

import type { ComponentType, SVGProps } from 'react'

type IconProps = { className?: string } & SVGProps<SVGSVGElement>
type Icon = ComponentType<IconProps>

// ── imports dos SVGs (URL) ──────────────────────────────────
// Setores (pipeline logado)
import dados from './svg/dados.svg'
import financeiro from './svg/financeiro.svg'
import contabilidade from './svg/contabilidade.svg'
import marketing from './svg/marketing.svg'
import conhecimento from './svg/conhecimento.svg'
// Agentes do site (degustação)
import mercado from './svg/mercado.svg'
import tecnico from './svg/tecnico.svg'
import arquiteto from './svg/arquiteto.svg'
import engenheiro from './svg/engenheiro.svg'
import regulatorio from './svg/regulatorio.svg'
// 18 agentes do pipeline (crachá por agente)
import marketing_lead_capture from './svg/marketing_lead_capture.svg'
import dados_context_builder from './svg/dados_context_builder.svg'
import dados_geoscout from './svg/dados_geoscout.svg'
import dados_demo_analyst from './svg/dados_demo_analyst.svg'
import dados_competitor_search from './svg/dados_competitor_search.svg'
import dados_competitor_analysis from './svg/dados_competitor_analysis.svg'
import dados_market_research from './svg/dados_market_research.svg'
import financeiro_estimator from './svg/financeiro_estimator.svg'
import financeiro_sensibilidade from './svg/financeiro_sensibilidade.svg'
import contabilidade_parque_cnpj from './svg/contabilidade_parque_cnpj.svg'
import contabilidade_diligencia from './svg/contabilidade_diligencia.svg'
import contabilidade_validador from './svg/contabilidade_validador.svg'
import conhecimento_rag_retriever from './svg/conhecimento_rag_retriever.svg'
import conhecimento_rag_insight from './svg/conhecimento_rag_insight.svg'
import conhecimento_rag_cross from './svg/conhecimento_rag_cross.svg'
import marketing_positioning from './svg/marketing_positioning.svg'
import marketing_report_writer from './svg/marketing_report_writer.svg'
import marketing_contact_hunter from './svg/marketing_contact_hunter.svg'

/** Fábrica: transforma uma URL de SVG num componente de ícone (<img>). */
function svgIcon(src: string, alt: string): Icon {
  const C = ({ className }: IconProps) => (
    <img src={src} alt={alt} className={className} draggable={false} />
  )
  C.displayName = `Icone(${alt})`
  return C
}

// ── Setores (usados pelo config/handoff.ts) ─────────────────
export const IconeDados = svgIcon(dados, 'Dados')
export const IconeFinanceiro = svgIcon(financeiro, 'Financeiro')
export const IconeContabilidade = svgIcon(contabilidade, 'Contabilidade')
export const IconeMarketing = svgIcon(marketing, 'Marketing')
export const IconeConhecimento = svgIcon(conhecimento, 'Conhecimento')

// ── Agentes do site (usados pelo config/handoff_site.ts) ────
export const IconeMercado = svgIcon(mercado, 'Mercado')
export const IconeTecnico = svgIcon(tecnico, 'Responsável Técnico')
export const IconeArquiteto = svgIcon(arquiteto, 'Arquiteto')
export const IconeEngenheiro = svgIcon(engenheiro, 'Engenheiro de Obra')
export const IconeRegulatorio = svgIcon(regulatorio, 'Regulatório')

// ── 18 agentes do pipeline — mapa por id (config_handoff.ts AGENTES_PIPELINE) ──
// Use AGENT_ICONS[agente.id] para crachá por agente; se faltar, caia no ícone do setor.
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
