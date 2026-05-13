/**
 * lib/queryClient.ts — TanStack Query client singleton.
 *
 * Defaults pensados pro GymSite:
 * - staleTime 30s: relatórios não mudam rápido. Evita refetch ao trocar de aba.
 * - retry 2: API Supabase tem 99.9% uptime, 2 tentativas são suficientes.
 * - refetchOnWindowFocus false: padrão TanStack é true; em dashboards corporativos
 *   isso atrapalha (refetch toda vez que volta da aba do email).
 *
 * Error handling global:
 * - QueryCache.onError: toast.error automático quando uma query falha,
 *   mesmo se a página não estiver renderizando o erro. Evita "tela vazia
 *   sem feedback" típico de fetch silenciosamente falhado.
 * - MutationCache.onError: idem pra mutations.
 * - Cada query/mutation pode opt-out via meta: { silent: true }.
 */
import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query'
import { extractErrorMessage, notify } from './notify'

function shouldNotify(meta: Record<string, unknown> | undefined): boolean {
  if (!meta) return true
  return meta.silent !== true
}

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (err, query) => {
      if (!shouldNotify(query.meta)) return
      notify.error(err, {
        description:
          (query.meta?.errorContext as string | undefined) ??
          'Não conseguimos carregar os dados.',
      })
    },
  }),
  mutationCache: new MutationCache({
    onError: (err, _vars, _ctx, mutation) => {
      if (!shouldNotify(mutation.meta)) return
      notify.error(extractErrorMessage(err))
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
})
