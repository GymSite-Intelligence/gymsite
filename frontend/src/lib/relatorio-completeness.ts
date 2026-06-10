import type { RelatorioDetail } from '@/hooks/useRelatorioDetail'
import type { RelatorioResumo, RelatorioStatus } from '@/types/domain'

export const EMPTY_VIEWER_MSG =
  'Relatório vazio: pipeline concluiu sem conteúdo. Use «Gerar novamente» para reprocessar.'

/** Listagem sem join de outputs — indica relatório sem A6 persistido. */
export function isRelatorioResumoLikelyEmpty(r: RelatorioResumo): boolean {
  return (
    r.veredito == null &&
    r.score_top1_candidato == null &&
    r.score_bairro == null &&
    r.modelo_recomendado == null
  )
}

/** Exibir «Gerar novamente» na listagem / dashboard. */
export function needsRelatorioRerun(r: RelatorioResumo): boolean {
  if (r.status === 'failed' || r.status === 'done') return true
  if (r.status === 'running' || r.status === 'queued') {
    return isRelatorioResumoLikelyEmpty(r)
  }
  return false
}

/**
 * Viewer e cards: permite reprocessar quando falhou, concluiu, ou ficou sem conteúdo
 * (inclui `running` órfão com outputs vazios).
 */
export function canRerunRelatorio(
  status: RelatorioStatus | string | undefined,
  opts?: { contentEmpty?: boolean },
): boolean {
  if (status === 'failed' || status === 'done') return true
  if (status === 'cancelled') return false
  if (opts?.contentEmpty) return true
  return false
}

function hasText(value: unknown, minLen: number): boolean {
  return typeof value === 'string' && value.trim().length >= minLen
}

/** Viewer não tem conteúdo utilizável (outputs/cenários/scores/resumo ausentes). */
export function isRelatorioContentEmpty(data: RelatorioDetail): boolean {
  const out = data.output_consolidado
  const hasScores =
    out.score_bairro != null ||
    out.scores_regionais?.demografico != null ||
    out.scores_regionais?.competitivo != null ||
    out.scores_regionais?.concorrencia != null ||
    out.scores_regionais?.viabilidade != null
  const hasCenarios =
    out.viabilidade_3_cenarios != null &&
    Object.keys(out.viabilidade_3_cenarios).length > 0
  const hasCandidatos = (out.top_3_candidatos?.length ?? 0) > 0
  const hasConcorrentes = (out.competitors_set?.length ?? 0) > 0
  const hasBairros = (out.bairros_alternativos?.length ?? 0) > 0
  const hasResumo = hasText(out.resumo_executivo, 40)
  const hasVeredito =
    typeof out.veredito === 'string' &&
    out.veredito.length > 0 &&
    out.veredito !== 'REPROVADO'

  return !(
    hasScores ||
    hasCenarios ||
    hasCandidatos ||
    hasConcorrentes ||
    hasBairros ||
    hasResumo ||
    hasVeredito
  )
}

export function relatorioViewerErrorMessage(data: RelatorioDetail): string | undefined {
  const status = data.pipeline_status
  // Em execução ainda não há outputs — não confundir com relatório vazio.
  if (status === 'queued' || status === 'running') {
    return undefined
  }
  if (status === 'failed') {
    return data.erro_mensagem ?? EMPTY_VIEWER_MSG
  }
  if (status === 'done' && isRelatorioContentEmpty(data)) {
    return data.erro_mensagem ?? EMPTY_VIEWER_MSG
  }
  return undefined
}

/** Viewer deve redirecionar para a tela de espera enquanto o pipeline roda. */
export function shouldRedirectToAguardando(
  status: RelatorioStatus | string | undefined,
): boolean {
  return status === 'queued' || status === 'running'
}

/** Atalho para ViewerError.showRerun */
export function shouldShowRerunInViewer(data: RelatorioDetail): boolean {
  return canRerunRelatorio(data.pipeline_status, {
    contentEmpty: isRelatorioContentEmpty(data),
  })
}
