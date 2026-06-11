/**
 * hooks/useDeleteRelatorio.ts — Mutation pra excluir um relatório (soft delete).
 *
 * P-007: nada é apagado de verdade. Marca deleted_at; a view do dashboard e
 * as listagens filtram. Tabelas filhas (outputs, candidatos, validações)
 * permanecem intactas para auditoria. RLS (`relatorios CRUD on own org`)
 * garante que só marca da própria org.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { resolveRelatorioUuid } from '@/lib/relatorio-id'
import { USE_MOCKS } from '@/mocks'

export function useDeleteRelatorio() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (relatorioId: string): Promise<void> => {
      if (USE_MOCKS) {
        await new Promise((r) => setTimeout(r, 200))
        return
      }
      const relatorioUuid = await resolveRelatorioUuid(relatorioId)
      const { error } = await supabase
        .from('relatorios')
        .update({ deleted_at: new Date().toISOString() })
        .eq('id', relatorioUuid)
      if (error) {
        throw new Error(`Supabase: ${error.message}`)
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['relatorios'] })
      qc.invalidateQueries({ queryKey: ['relatorios-no-mapa'] })
    },
  })
}
