import { API_BASE, supabase } from '@/lib/supabase'

// Obra CNO em curso (proxy residencial) — colunas úteis do endpoint /api/cno/obras.
export interface CnoObra {
  id_cno: string
  nome: string | null
  area_m2: number | null
  tipo_logradouro: string | null
  logradouro: string | null
  numero_logradouro: string | null
  bairro: string | null
  sigla_uf: string | null
  id_municipio: number | null
  cep: string | null
  situacao: string | null
  em_curso: boolean
  data_inicio: string | null
  data_situacao: string | null
}

export interface BuscaObrasParams {
  uf: string
  municipioId?: number
  bairro?: string
  residencial?: boolean
}

async function authHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const {
    data: { session },
  } = await supabase.auth.getSession()
  if (session?.access_token) headers.Authorization = `Bearer ${session.access_token}`
  return headers
}

export async function buscarObrasCno(
  params: BuscaObrasParams,
): Promise<{ total: number; obras: CnoObra[] }> {
  const q = new URLSearchParams({ uf: params.uf })
  if (params.municipioId) q.set('municipio_id', String(params.municipioId))
  if (params.bairro) q.set('bairro', params.bairro)
  if (params.residencial === false) q.set('residencial', 'false')
  const res = await fetch(`${API_BASE}/api/cno/obras?${q.toString()}`, {
    headers: await authHeaders(),
  })
  if (!res.ok) throw new Error(`Erro ${res.status} ao buscar obras do CNO.`)
  return res.json()
}
