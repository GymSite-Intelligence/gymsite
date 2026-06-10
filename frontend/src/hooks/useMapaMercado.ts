import { useQuery } from '@tanstack/react-query'
import { API_BASE } from '@/lib/supabase'

export interface MapaMercadoSite {
  lat: number
  lng: number
  label?: string
}

export interface MapaMercadoConcorrente {
  nome?: string
  place_id?: string | null
  lat: number
  lng: number
  distancia_km?: number | null
  rating?: number | null
  bairro_concorrente?: string | null
  google_maps_uri?: string | null
}

export interface MapaMercadoEntrante {
  cnpj?: string
  nome_exibicao?: string | null
  bairro?: string | null
  lat: number
  lng: number
  peso_heatmap?: number
  data_abertura?: string
  segmento_operacao?: string
}

export interface MapaMercadoBounds {
  ne: { lat: number; lng: number }
  sw: { lat: number; lng: number }
}

export interface MapaMercadoPayload {
  cidade: string
  uf: string
  bairro_estudo?: string
  municipio: {
    centro?: { lat: number; lng: number }
    bounds?: MapaMercadoBounds
    error?: string
    endereco?: string
  }
  bounds_municipio?: MapaMercadoBounds | null
  site?: MapaMercadoSite | null
  concorrentes: MapaMercadoConcorrente[]
  entrantes: MapaMercadoEntrante[]
  entrantes_total_filtrado?: number
  entrantes_com_coord?: number
}

function mapaMercadoUrl(relatorioId: string): string {
  return `${API_BASE.replace(/\/$/, '')}/api/relatorios/${encodeURIComponent(relatorioId)}/mapa-mercado`
}

export function useMapaMercado(relatorioId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ['mapa-mercado', relatorioId],
    enabled: Boolean(relatorioId) && enabled,
    queryFn: async (): Promise<MapaMercadoPayload> => {
      const res = await fetch(mapaMercadoUrl(relatorioId!), {
        credentials: 'include',
      })
      if (!res.ok) {
        const err = await res.text()
        throw new Error(err || `mapa-mercado HTTP ${res.status}`)
      }
      const data: unknown = await res.json()
      return data as MapaMercadoPayload
    },
    staleTime: 10 * 60_000,
    retry: 1,
    meta: { silent: true },
  })
}
