import { useState } from 'react'
import { fetchExplorar } from '@/lib/explorarApi'
import { useAuth } from '@/lib/auth'
import type { AbsorcaoMargemFrescaJSON } from '@/hooks/useRelatorioDetail'
import type { ExplorarRival } from '@/components/explorar/ExplorarMap'
import type { Lente, TipoNegocioExplorar } from '@/components/explorar/explorarIso'

export type ExplorarAnaliseOk = {
  status: 'ok'
  lente: Lente
  base_espacial_label: string
  pin: { lat: number; lng: number }
  concorrentes: ExplorarRival[]
  absorcao_margem_fresca: AbsorcaoMargemFrescaJSON
  carimbo_base: string
}

export type ExplorarAnaliseQuota = {
  status: 'quota_used' | 'fila'
  mensagem: string
}

export type ExplorarAnaliseResult = ExplorarAnaliseOk | ExplorarAnaliseQuota

function authHeaders(accessToken: string | undefined, mockAuth: boolean): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (!mockAuth && accessToken) headers.Authorization = `Bearer ${accessToken}`
  return headers
}

export function useExplorarAnalise() {
  const { session, mockAuth } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ExplorarAnaliseResult | null>(null)
  const headers = authHeaders(session?.access_token, mockAuth)

  async function analisar(body: {
    lat: number
    lng: number
    lente: Lente
    tipo_negocio?: TipoNegocioExplorar
    cidade?: string
    bairro?: string
    uf?: string
    endereco?: string
    publico_alvo?: string
    area_m2?: number
    idade_min?: number
    idade_max?: number
    email?: string
    turnstile_token?: string
  }) {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchExplorar('/api/explorar/analisar', {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      })
      const data = (await res.json().catch(() => ({}))) as ExplorarAnaliseResult & {
        detail?: string
      }
      if (res.status === 403) {
        throw new Error('Verificação anti-bot falhou.')
      }
      if (!res.ok) {
        throw new Error(typeof data.detail === 'string' ? data.detail : `Erro ${res.status}`)
      }
      setResult(data)
      return data
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Falha ao analisar'
      setError(msg)
      throw e
    } finally {
      setLoading(false)
    }
  }

  async function geocode(endereco: string): Promise<{
    lat: number
    lng: number
    bairro?: string
    cidade?: string
    uf?: string
  }> {
    const res = await fetchExplorar('/api/explorar/geocode', {
      method: 'POST',
      headers,
      body: JSON.stringify({ endereco }),
    })
    const data = (await res.json().catch(() => ({}))) as {
      lat?: number
      lng?: number
      bairro?: string
      cidade?: string
      uf?: string
      detail?: string
    }
    if (!res.ok || data.lat == null || data.lng == null) {
      throw new Error(data.detail || 'Endereço não encontrado.')
    }
    return {
      lat: data.lat,
      lng: data.lng,
      bairro: data.bairro,
      cidade: data.cidade,
      uf: data.uf,
    }
  }

  return { loading, error, result, setResult, analisar, geocode }
}
