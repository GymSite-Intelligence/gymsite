/**
 * useRerunPipeline — Re-dispara o pipeline com os mesmos parâmetros do relatório.
 *
 * Uma mutation compartilhada (mutationKey) + dedupe por payload evita 2 POSTs
 * quando o usuário dá duplo clique ou há race antes de isPending=true.
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

export interface RerunResult {
  id: string
  payload: PipelineReportPayload
}

/** POSTs em voo com a mesma localização/área — coalesce duplo clique. */
const inflightByPayload = new Map<string, Promise<RerunResult>>()

function payloadDedupeKey(p: PipelineReportPayload): string {
  return [
    p.cidade,
    p.uf ?? '',
    p.bairro,
    p.area_m2_min,
    p.area_m2_max,
    p.tipo_negocio ?? 'academia',
    p.publico_alvo ?? '',
    p.genero_alvo ?? '',
    p.tamanho_preset ?? '',
    String(p.estacionamento_obrigatorio ?? true),
    p.a0_research_provider ?? 'auto',
  ].join('|')
}

async function runRerunOnce(
  relatorioId: string,
  inputs?: PipelineReportPayload,
): Promise<RerunResult> {
  const payload = inputs ?? (await fetchRelatorioInputsForRerun(relatorioId))
  const key = payloadDedupeKey(payload)
  const existing = inflightByPayload.get(key)
  if (existing) return existing

  const promise = submitPipelineReport(payload).then((res) => ({
    id: res.id,
    payload,
  }))
  inflightByPayload.set(key, promise)
  try {
    return await promise
  } finally {
    if (inflightByPayload.get(key) === promise) {
      inflightByPayload.delete(key)
    }
  }
}

export function useRerunPipeline() {
  const navigate = useNavigate()

  return useMutation({
    mutationKey: ['rerun-pipeline'],
    mutationFn: ({ relatorioId, inputs }: RerunVars) =>
      runRerunOnce(relatorioId, inputs),
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
