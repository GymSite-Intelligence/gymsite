/**
 * useApiHealth — ping periódico GET /health da API FastAPI.
 */
import { useQuery } from '@tanstack/react-query'
import { fetchExplorar } from '@/lib/explorarApi'
import { API_BASE } from '@/lib/supabase'

export interface ApiHealth {
  status: string
  service: string
}

export function useApiHealth() {
  return useQuery({
    queryKey: ['api-health', API_BASE],
    queryFn: async (): Promise<ApiHealth> => {
      const res = await fetchExplorar('/health', {
        signal: AbortSignal.timeout(8000),
      })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      return (await res.json()) as ApiHealth
    },
    refetchInterval: 30_000,
    retry: 1,
    meta: { silent: true },
  })
}
