/**
 * submit-pipeline.ts — Dispara POST /api/relatorios (stub + pipeline ADK).
 *
 * Usado pelo form de novo relatório e pelo botão "Gerar novamente".
 */
import { API_BASE, supabase } from '@/lib/supabase'
import { resolveRelatorioUuid } from '@/lib/relatorio-id'

export interface PipelineReportPayload {
  cidade: string
  uf?: string | null
  bairro: string
  area_m2_min: number
  area_m2_max: number
  tamanho_preset?: string | null
  publico_alvo?: string | null
  genero_alvo?: string | null
  tipo_negocio?: string | null
  estacionamento_obrigatorio?: boolean | null
  a0_research_provider?: 'gemini' | 'kimi' | 'auto' | string | null
}

interface RelatorioInputsRow {
  cidade: string
  uf: string | null
  bairro: string
  area_m2_min: number
  area_m2_max: number
  tamanho_preset: string | null
  publico_alvo: string | null
  genero_alvo: string | null
  tipo_negocio: string | null
  estacionamento_obrigatorio: boolean | null
}

function rowToPayload(row: RelatorioInputsRow): PipelineReportPayload {
  return {
    cidade: row.cidade,
    uf: row.uf,
    bairro: row.bairro,
    area_m2_min: row.area_m2_min,
    area_m2_max: row.area_m2_max,
    tamanho_preset: row.tamanho_preset ?? 'm',
    publico_alvo: row.publico_alvo ?? '25-40',
    genero_alvo: row.genero_alvo ?? 'misto',
    tipo_negocio: row.tipo_negocio ?? 'academia',
    estacionamento_obrigatorio: row.estacionamento_obrigatorio ?? true,
  }
}

/** Carrega inputs salvos de um relatório existente (para re-run). */
export async function fetchRelatorioInputsForRerun(
  relatorioId: string,
): Promise<PipelineReportPayload> {
  const rid = await resolveRelatorioUuid(relatorioId)
  const { data, error } = await supabase
    .from('relatorio_inputs')
    .select(
      'cidade, uf, bairro, area_m2_min, area_m2_max, tamanho_preset, publico_alvo, genero_alvo, tipo_negocio, estacionamento_obrigatorio',
    )
    .eq('relatorio_id', rid)
    .maybeSingle()
  if (error) throw new Error(`Supabase: ${error.message}`)
  if (!data) {
    throw new Error('Parâmetros do relatório não encontrados — não é possível gerar novamente.')
  }
  return rowToPayload(data as RelatorioInputsRow)
}

export async function submitPipelineReport(
  payload: PipelineReportPayload,
): Promise<{ id: string }> {
  const {
    data: { session },
  } = await supabase.auth.getSession()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (session?.access_token) {
    headers.Authorization = `Bearer ${session.access_token}`
  }

  const res = await fetch(`${API_BASE}/api/relatorios`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      cidade: payload.cidade,
      uf: payload.uf ?? undefined,
      bairro: payload.bairro,
      area_m2_min: payload.area_m2_min,
      area_m2_max: payload.area_m2_max,
      tamanho_preset: payload.tamanho_preset ?? 'm',
      publico_alvo: payload.publico_alvo ?? '25-40',
      genero_alvo: payload.genero_alvo ?? 'misto',
      tipo_negocio: payload.tipo_negocio ?? 'academia',
      estacionamento_obrigatorio: payload.estacionamento_obrigatorio ?? true,
      a0_research_provider: payload.a0_research_provider ?? 'auto',
    }),
  })

  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`API ${res.status}: ${body.slice(0, 200)}`)
  }

  const { id } = (await res.json()) as { id: string }
  return { id }
}

/** Label curto pra toast / pipeline tracker. */
export function pipelineLabelFromPayload(payload: PipelineReportPayload): string {
  const local = payload.bairro ? ` · ${payload.bairro}` : ''
  return `${payload.cidade}${local}`
}
