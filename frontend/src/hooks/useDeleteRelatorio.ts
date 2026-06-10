/**
 * hooks/useDeleteRelatorio.ts — Mutation pra deletar um relatório.
 *
 * Usa Supabase JS direto. RLS (`relatorios CRUD on own org`) garante que só
 * deleta da própria org. Schema tem `on delete cascade` em todas as filhas
 * (inputs, outputs, candidatos, competidores, cenarios, sensibilidade,
 * bairros_alt), então uma única chamada limpa tudo.
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
        .delete()
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
