/**
 * Helpers de ID de relatório.
 *
 * No Supabase, `relatorios.id` é UUID. O pipeline grava o id legado
 * `rpt_<unix_ts>` em `adk_run_id`. Mocks locais usam `rpt_*` como id.
 */
import { supabase } from '@/lib/supabase'

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

const LEGACY_MOCK_ID_RE = /^rpt_\d+$/

export function isRelatorioUuid(id: string): boolean {
  return UUID_RE.test(id)
}

export function isLegacyMockRelatorioId(id: string): boolean {
  return LEGACY_MOCK_ID_RE.test(id)
}

/** Filtra ids seguros pra colunas uuid (evita 400 do PostgREST). */
export function filterRelatorioUuids(ids: string[]): string[] {
  return ids.filter(isRelatorioUuid)
}

/**
 * Normaliza id da URL para UUID do Supabase.
 * Aceita UUID direto ou `adk_run_id` legado (`rpt_*`).
 */
export async function resolveRelatorioUuid(id: string): Promise<string> {
  if (isRelatorioUuid(id)) return id

  if (isLegacyMockRelatorioId(id)) {
    const { data, error } = await supabase
      .from('relatorios')
      .select('id')
      .eq('adk_run_id', id)
      .is('deleted_at', null)
      .maybeSingle()
    if (error) throw new Error(`Supabase: ${error.message}`)
    if (data?.id) return data.id as string

    throw new Error(
      'Relatório de demonstração (id rpt_* legado). Volte à listagem e abra um relatório real, ou recarregue a página (Ctrl+Shift+R) para limpar o cache.',
    )
  }

  throw new Error(`ID de relatório inválido: ${id}`)
}
