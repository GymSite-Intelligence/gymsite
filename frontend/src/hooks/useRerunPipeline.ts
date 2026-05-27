/**
 * useRerunPipeline — Re-dispara o pipeline com os mesmos parâmetros do relatório.
 */
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { trackPipeline } from '@/lib/pipeline-tracker'
import { notify } from '@/lib/notify'
import {
  fetchRelatorioInputsForRerun,
  pipelineLabelFromPayload,
  submitPipelineReport,
  type PipelineReportPayload,
} from '@/lib/submit-pipeline'

interface RerunVars {
  relatorioId: string
  /** Se já carregados (ex.: viewer), evita query extra. */
  inputs?: PipelineReportPayload
}

export function useRerunPipeline() {
  const navigate = useNavigate()

  return useMutation({
    mutationFn: async ({ relatorioId, inputs }: RerunVars) => {
      const payload = inputs ?? (await fetchRelatorioInputsForRerun(relatorioId))
      const { id } = await submitPipelineReport(payload)
      return { id, payload }
    },
    onSuccess: ({ id, payload }) => {
      trackPipeline(id, pipelineLabelFromPayload(payload))
      notify.info('Pipeline iniciado', {
        description: 'Gerando nova versão com os mesmos parâmetros.',
      })
      navigate({
        to: '/relatorios/$relatorioId/aguardando',
        params: { relatorioId: id },
      })
    },
    onError: (err) => notify.error(err),
  })
}
