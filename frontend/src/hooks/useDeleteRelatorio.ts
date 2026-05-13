/**
 * hooks/useDeleteRelatorio.ts — Mutation pra deletar um relatório.
 *
 * Usa Supabase JS direto. RLS (`relatorios CRUD on own org`) garante que só
 * deleta da própria org. Schema tem `on delete cascade` em todas as filhas
 * (inputs, outputs, candidatos, competidores, cenarios, sensibilidade,
 * bairros_alt), então uma única chamada limpa tudo.
 *
 * UI só expõe pro status='failed' — backend zumbi (running travado) precisa
 * ser marcado como failed antes (por worker ou manualmente) pra evitar race
 * de deletar enquanto pipeline ainda escreve.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { USE_MOCKS } from '@/mocks'

export function useDeleteRelatorio() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (relatorioId: string): Promise<void> => {
      if (USE_MOCKS) {
        await new Promise((r) => setTimeout(r, 200))
        return
      }
      const { error } = await supabase
        .from('relatorios')
        .delete()
        .eq('id', relatorioId)
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
