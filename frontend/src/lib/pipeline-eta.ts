/**
 * ETA de pipeline — derivado de mediana/P75 em relatórios `done` (Supabase).
 * Atualizar após mudanças relevantes de performance; ver `scripts/analise_tempo_relatorios.py`.
 */
/** Mediana histórica ≈ 9,4 min (jun/2026, n≈36). */
export const PIPELINE_ETA_MIN_TYPICAL = 10

/** P75 histórico ≈ 18 min — texto conservador. */
export const PIPELINE_ETA_MIN_P75 = 18

/** Faixa exibida em formulários (entre P25 e mediana arredondada). */
export const PIPELINE_ETA_RANGE_LABEL = '8–15 min'

export function pipelineEtaTypicalLabel(): string {
  return `~${PIPELINE_ETA_MIN_TYPICAL} min`
}

export function pipelineEtaRangeLabel(): string {
  return PIPELINE_ETA_RANGE_LABEL
}

/** Uma linha para telas de espera. */
export function pipelineEtaWaitingLine(): string {
  return `Pipeline completo costuma levar ${pipelineEtaTypicalLabel()} (até ~${PIPELINE_ETA_MIN_P75} min em picos)`
}

/** Banner de fila / monitor global. */
export function pipelineEtaBackgroundLine(): string {
  return `Gerando relatório em background (${pipelineEtaTypicalLabel()})`
}

export function pipelineEtaConcurrentWarning(): string {
  return `Pipelines simultâneos podem demorar mais que ${PIPELINE_ETA_MIN_TYPICAL} min`
}
