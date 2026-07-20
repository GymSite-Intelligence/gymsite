import { API_BASE, supabase } from '@/lib/supabase'
import type { AgenteApiId } from '@/config/site-agent-map'
import type { ConsultorPesquisas } from '@/hooks/useConsultorChat'
import type { CarimboCitacao } from '@/components/chat/CitationStamp'

export interface PollConsultorMensagem {
  role: 'user' | 'assistant'
  content: string
  created_at: string
  agente?: AgenteApiId | null
  tool_calls?: { ferramenta: string; status: string; resumo: string }[]
  citacoes?: CarimboCitacao[]
}

export interface PollConsultorResponse {
  mensagens: PollConsultorMensagem[]
  status: string
  pode_gerar_relatorio: boolean
  localizacao: { cidade?: string; bairro?: string; uf?: string }
  modelo_negocio: Record<string, unknown>
  pesquisas_realizadas: ConsultorPesquisas
  custo_brl_ate_agora: number
  relatorio_id: string | null
}

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

async function erroDaResposta(r: Response, fallback: string): Promise<string> {
  try {
    const ct = r.headers.get('content-type') ?? ''
    if (ct.includes('application/json')) {
      const j = await r.json()
      const msg = j?.detail ?? j?.message ?? j?.error
      if (msg) return typeof msg === 'string' ? msg : JSON.stringify(msg)
    }
  } catch {
    /* noop */
  }
  return fallback
}

export async function conversarConsultor(
  mensagem: string,
  projetoId?: string | null,
  agente?: AgenteApiId,
): Promise<{ projeto_id: string; status: string }> {
  const r = await fetch(`${API_BASE}/api/consultor/conversar`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify({
      mensagem,
      projeto_id: projetoId ?? undefined,
      agente,
    }),
  })
  if (!r.ok) throw new Error(await erroDaResposta(r, `Erro ${r.status} ao enviar.`))
  return r.json()
}

export async function pollConsultorMensagens(
  projetoId: string,
  desde?: string,
): Promise<PollConsultorResponse> {
  const u = new URL(`${API_BASE}/api/consultor/projetos/${projetoId}/mensagens`)
  if (desde) u.searchParams.set('desde', desde)
  const r = await fetch(u.toString(), { headers: await authHeaders() })
  if (!r.ok) throw new Error(await erroDaResposta(r, `Erro ${r.status} no polling.`))
  return r.json()
}
