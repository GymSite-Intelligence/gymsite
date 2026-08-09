import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { API_BASE, supabase } from '@/lib/supabase'
import { useAuth } from '@/lib/auth'

export type LlmProviderOption = 'nvidia' | 'ollama' | 'env'

export type LlmConfig = {
  provider: string
  provider_env: string
  provider_override: string | null
  source: 'redis' | 'env'
  model: string
  options: string[]
  nvidia_key_configured: boolean
  cloud_run: boolean
  ollama_allowed_on_cloud: boolean
}

async function authHeaders(): Promise<HeadersInit> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

export function useLlmConfig() {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['admin-llm-config', user?.id ?? 'anon'],
    enabled: !!user,
    queryFn: async (): Promise<LlmConfig> => {
      const res = await fetch(`${API_BASE}/api/admin/llm-config`, {
        headers: await authHeaders(),
      })
      if (!res.ok) {
        throw new Error(
          res.status === 403
            ? 'Só admin da plataforma pode ver o provedor de IA'
            : `Falha ao carregar provedor (${res.status})`,
        )
      }
      return res.json()
    },
  })
}

export function usePatchLlmConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (provider: LlmProviderOption): Promise<LlmConfig> => {
      const res = await fetch(`${API_BASE}/api/admin/llm-config`, {
        method: 'PATCH',
        headers: await authHeaders(),
        body: JSON.stringify({ provider }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(
          typeof body.detail === 'string'
            ? body.detail
            : `Falha ao gravar provedor (${res.status})`,
        )
      }
      return res.json()
    },
    onSuccess: (data) => {
      qc.setQueryData(['admin-llm-config'], data)
      qc.invalidateQueries({ queryKey: ['admin-llm-config'] })
    },
  })
}
