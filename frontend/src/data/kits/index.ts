/**
 * Catálogo unificado de kits — 20 combinações (4 modelos × 5 tamanhos).
 *
 * Lookup principal: `getKit(modelo, tamanho)` retorna o KitEquipamentos
 * correspondente. Helper `kitParaCenarioFinanceiro()` calcula o total
 * pra usar como CAPEX equipamentos em vez de R$/m² genérico.
 */
import type { ModeloNegocio, TamanhoCodigo } from '@/data/tamanhos-por-modelo'
import { totalKit, faixaCustoReal, type KitEquipamentos } from './types'

import {
  ACADEMIA_PP,
  ACADEMIA_P,
  ACADEMIA_M,
  ACADEMIA_G,
  ACADEMIA_GG,
} from './academia'
import {
  CROSSFIT_PP,
  CROSSFIT_P,
  CROSSFIT_M,
  CROSSFIT_G,
  CROSSFIT_GG,
} from './crossfit-box'
import {
  PILATES_PP,
  PILATES_P,
  PILATES_M,
  PILATES_G,
  PILATES_GG,
} from './studio-pilates'
import {
  FUNCIONAL_PP,
  FUNCIONAL_P,
  FUNCIONAL_M,
  FUNCIONAL_G,
  FUNCIONAL_GG,
} from './studio-funcional'

export const CATALOGO_KITS: Record<
  ModeloNegocio,
  Record<TamanhoCodigo, KitEquipamentos>
> = {
  academia: {
    pp: ACADEMIA_PP,
    p: ACADEMIA_P,
    m: ACADEMIA_M,
    g: ACADEMIA_G,
    gg: ACADEMIA_GG,
  },
  crossfit_box: {
    pp: CROSSFIT_PP,
    p: CROSSFIT_P,
    m: CROSSFIT_M,
    g: CROSSFIT_G,
    gg: CROSSFIT_GG,
  },
  studio_pilates: {
    pp: PILATES_PP,
    p: PILATES_P,
    m: PILATES_M,
    g: PILATES_G,
    gg: PILATES_GG,
  },
  studio_funcional: {
    pp: FUNCIONAL_PP,
    p: FUNCIONAL_P,
    m: FUNCIONAL_M,
    g: FUNCIONAL_G,
    gg: FUNCIONAL_GG,
  },
  // "outro" reusa academia como fallback razoável
  outro: {
    pp: ACADEMIA_PP,
    p: ACADEMIA_P,
    m: ACADEMIA_M,
    g: ACADEMIA_G,
    gg: ACADEMIA_GG,
  },
}

export function getKit(
  modelo: ModeloNegocio,
  tamanho: TamanhoCodigo,
): KitEquipamentos | null {
  return CATALOGO_KITS[modelo]?.[tamanho] ?? null
}

/**
 * Retorna o tamanho do kit ajustado pelo modelo financeiro.
 *
 * Regra:
 * - Low Cost: usa tamanho 1 abaixo do selecionado (mais econômico)
 * - Mid Market: usa o tamanho selecionado (caso-base)
 * - Premium: usa tamanho 1 acima (mais robusto)
 *
 * Clamp nas bordas: PP não desce; GG não sobe.
 *
 * Ex (tamanho base = M):
 *   low → P,  mid → M,  premium → G
 *
 * Ex (tamanho base = PP):
 *   low → PP, mid → PP, premium → P
 */
const ORDEM_TAMANHOS: TamanhoCodigo[] = ['pp', 'p', 'm', 'g', 'gg']

export function getTamanhoParaModeloFinanceiro(
  tamanhoBase: TamanhoCodigo,
  modeloFinanceiro: 'low' | 'mid' | 'premium',
): TamanhoCodigo {
  const idx = ORDEM_TAMANHOS.indexOf(tamanhoBase)
  if (idx < 0) return tamanhoBase
  if (modeloFinanceiro === 'low') {
    return ORDEM_TAMANHOS[Math.max(0, idx - 1)]
  }
  if (modeloFinanceiro === 'premium') {
    return ORDEM_TAMANHOS[Math.min(ORDEM_TAMANHOS.length - 1, idx + 1)]
  }
  return tamanhoBase
}

/**
 * Pega o kit ajustado pelo modelo financeiro.
 * Returns null se a combinação (modelo, tamanho) não existe.
 */
export function getKitParaModeloFinanceiro(
  modelo: ModeloNegocio,
  tamanhoBase: TamanhoCodigo,
  modeloFinanceiro: 'low' | 'mid' | 'premium',
): KitEquipamentos | null {
  const tamanho = getTamanhoParaModeloFinanceiro(tamanhoBase, modeloFinanceiro)
  return getKit(modelo, tamanho)
}

/** Retorna 3 valores: bruto + faixa real estimada com desconto de volume. */
export function kitParaCenarioFinanceiro(
  modelo: ModeloNegocio,
  tamanho: TamanhoCodigo,
): { bruto: number; estimado_min: number; estimado_max: number; kit: KitEquipamentos } | null {
  const kit = getKit(modelo, tamanho)
  if (!kit) return null
  const bruto = totalKit(kit)
  const [min, max] = faixaCustoReal(kit)
  return {
    bruto,
    estimado_min: min,
    estimado_max: max,
    kit,
  }
}

export * from './types'
export {
  ACADEMIA_PP,
  ACADEMIA_P,
  ACADEMIA_M,
  ACADEMIA_G,
  ACADEMIA_GG,
  CROSSFIT_PP,
  CROSSFIT_P,
  CROSSFIT_M,
  CROSSFIT_G,
  CROSSFIT_GG,
  PILATES_PP,
  PILATES_P,
  PILATES_M,
  PILATES_G,
  PILATES_GG,
  FUNCIONAL_PP,
  FUNCIONAL_P,
  FUNCIONAL_M,
  FUNCIONAL_G,
  FUNCIONAL_GG,
}
