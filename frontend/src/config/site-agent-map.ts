/**
 * Mapa API id (catalog.py / poll `agente`) → UI EspecialistaId.
 * Mercado pinado (`mercado`) — evita roteador→Mercado→self-transfer (NVIDIA/LiteLLM).
 */
import type { EspecialistaId } from '@/config/consultor-agentes'

export type AgenteApiId =
  | 'degustacao'
  | 'mercado'
  | 'responsavel_tecnico'
  | 'regulatorio'
  | 'arquiteto'
  | 'engenheiro_obra'

const API_TO_UI: Record<AgenteApiId, EspecialistaId | null> = {
  degustacao: null,
  mercado: 'mercado',
  responsavel_tecnico: 'tecnico',
  regulatorio: 'regulatorio',
  arquiteto: 'arquiteto',
  engenheiro_obra: 'engenheiro',
}

const UI_TO_API: Record<EspecialistaId, AgenteApiId> = {
  mercado: 'mercado',
  tecnico: 'responsavel_tecnico',
  regulatorio: 'regulatorio',
  arquiteto: 'arquiteto',
  engenheiro: 'engenheiro_obra',
}

export function uiIdFromApi(agente?: string | null): EspecialistaId | null {
  if (!agente) return null
  return API_TO_UI[agente as AgenteApiId] ?? null
}

export function apiIdFromUi(id: EspecialistaId): AgenteApiId {
  return UI_TO_API[id]
}

export function isAgenteApiId(v: string): v is AgenteApiId {
  return v in API_TO_UI
}
