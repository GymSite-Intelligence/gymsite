/**
 * Tipos do dataset de kits de equipamentos fitness.
 *
 * Granularidade: cada item é identificado por modelo (esteira RT300, flexora
 * sentada Movement, crossover dupla polia, etc.) e quantidade. Preços são
 * de catálogo público 2024 (Movement, Athletic, RHS) — descontos de volume
 * 15-35% são típicos em compras >R$ 500k mas não aplicados aqui.
 *
 * Fontes principais:
 * - Movement Equipamentos (catálogo público anual)
 * - Athletic Works (catálogo público)
 * - RHS Equipamentos (linha nacional anilhas/halteres)
 * - ACAD Brasil — Guia de Implantação 2024
 * - Smart Fit Holdings (SMFT3) — CAPEX médio por unidade Express/Standard
 */
import type { ModeloNegocio, TamanhoCodigo } from '@/data/tamanhos-por-modelo'

export type CategoriaEquipamento =
  | 'cardio'
  | 'spinning'
  | 'musc_superior'
  | 'musc_inferior'
  | 'gluteo'
  | 'core'
  | 'livre'
  | 'pesos'
  | 'funcional'
  | 'pilates'        // reformer, cadillac, barrel, chair
  | 'crossfit'       // rig, GHD, bumper plates
  | 'estetica'       // espelho, piso emborrachado (CAPEX obra mas comum em kits)
  | 'acessorios'

export interface ItemEquipamento {
  cat: CategoriaEquipamento
  nome: string
  qtd: number
  /** Modelo/referência de catálogo (ex: "Movement RT300"). Vazio quando genérico. */
  ref?: string
  /** Preço unitário em BRL (lista, sem desconto). */
  preco_un: number
  /** Fornecedor principal. */
  fornecedor?: 'Movement' | 'Athletic' | 'Life Fitness' | 'Technogym' | 'RHS' | 'Concept2' | 'Schwinn' | 'Stott' | 'Balanced Body' | 'Rogue' | 'Eleiko' | 'Generico'
  /** Notas (opcional, ex: "Opcional se tem ar central"). */
  nota?: string
}

export interface KitEquipamentos {
  tipo_negocio: ModeloNegocio
  tamanho_preset: TamanhoCodigo
  area_referencia_m2: number
  /** Descrição curta do modelo de operação assumido (ex: "Smart Fit Standard"). */
  modelo_operacao: string
  itens: ItemEquipamento[]
  /** Faixa de desconto típica em compras de volume (catálogo lista → custo real). */
  desconto_volume_pct?: [number, number] // [min, max] ex: [0.15, 0.35]
  fontes: string[]
}

/** Calcula total bruto (sem desconto) do kit. */
export function totalKit(kit: KitEquipamentos): number {
  return kit.itens.reduce((acc, item) => acc + item.qtd * item.preco_un, 0)
}

/** Calcula total por categoria. Útil pra exibir breakdown. */
export function totaisPorCategoria(
  kit: KitEquipamentos,
): { categoria: CategoriaEquipamento; total: number; itens_count: number; modelos_count: number }[] {
  const map = new Map<
    CategoriaEquipamento,
    { total: number; itens_count: number; modelos_count: number }
  >()
  for (const item of kit.itens) {
    const cur = map.get(item.cat) ?? { total: 0, itens_count: 0, modelos_count: 0 }
    cur.total += item.qtd * item.preco_un
    cur.itens_count += item.qtd
    cur.modelos_count += 1
    map.set(item.cat, cur)
  }
  return Array.from(map.entries()).map(([categoria, dados]) => ({
    categoria,
    ...dados,
  }))
}

/** Faixa de custo real estimado (catálogo - desconto típico). */
export function faixaCustoReal(kit: KitEquipamentos): [number, number] {
  const bruto = totalKit(kit)
  const [descMin, descMax] = kit.desconto_volume_pct ?? [0.15, 0.35]
  return [bruto * (1 - descMax), bruto * (1 - descMin)]
}

export const CATEGORIA_LABEL: Record<CategoriaEquipamento, string> = {
  cardio: 'Cardio',
  spinning: 'Spinning',
  musc_superior: 'Musculação superior',
  musc_inferior: 'Musculação inferior',
  gluteo: 'Glúteo / posterior',
  core: 'Core / abdominal',
  livre: 'Livre / Plate-loaded',
  pesos: 'Halteres + Anilhas',
  funcional: 'Funcional',
  pilates: 'Pilates (reformer/cadillac)',
  crossfit: 'CrossFit (rig/GHD/bumpers)',
  estetica: 'Estética / piso',
  acessorios: 'Acessórios',
}
