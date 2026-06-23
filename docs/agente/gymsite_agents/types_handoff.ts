// ============================================================
// types/handoff.ts — Tipagens do Sistema de Handoff Badges
// GymSite Intelligence v2.1 — 5 Setores
// FIX: icone tipado como ComponentType genérico (suporta SVG + Lucide)
// ============================================================

import type { ComponentType, SVGProps } from 'react'

export type SetorId = 'dados' | 'financeiro' | 'contabilidade' | 'marketing' | 'conhecimento'

export type AgenteStatus = 'idle' | 'entrando' | 'ativo' | 'saindo' | 'completo' | 'erro'

// FIX: era LucideIcon — impedia uso de SVGs importados via SVGR.
// ComponentType<{ className?: string }> funciona com Lucide E com React SVG components.
export type IconComponent = ComponentType<{ className?: string } & SVGProps<SVGSVGElement>>

export interface SetorConfig {
  id: SetorId
  nome: string
  nomeCurto: string
  cor: string
  corBg: string
  corTexto: string
  corBorda: string
  corBgHover: string
  icone: IconComponent
  descricao: string
}

export interface AgenteInfo {
  id: string
  nome: string
  setor: SetorId
  descricao: string
  ordemPipeline: number
}

export interface HandoffState {
  agenteAtivoId: string | null
  agenteAnteriorId: string | null
  agenteEntrandoId: string | null
  status: 'idle' | 'transicionando'
  progresso: number
  timestampInicio: number | null
  erro: string | null
}

export interface HandoffEvent {
  fromAgenteId: string | null
  toAgenteId: string
  tipo: 'inicio' | 'handoff' | 'completo' | 'erro'
  payload?: Record<string, unknown>
}

export interface HandoffBadgeProps {
  state: HandoffState
  agentes: AgenteInfo[]
  setores: Record<SetorId, SetorConfig>
  onAgenteClick?: (agenteId: string) => void
  className?: string
}

export interface HandoffTimelineProps {
  agentes: AgenteInfo[]
  setores: Record<SetorId, SetorConfig>
  state: HandoffState
  className?: string
}
