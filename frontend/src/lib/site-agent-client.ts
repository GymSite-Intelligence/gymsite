import { API_BASE } from '@/lib/supabase'
import type { AgenteApiId } from '@/config/site-agent-map'

export interface PollSiteMensagem {
  role: 'user' | 'assistant'
  content: string
  created_at: string
  agente?: AgenteApiId | null
}

export interface PollSiteResponse {
  mensagens: PollSiteMensagem[]
  status: string
  pode_gerar_relatorio: boolean
  localizacao: { cidade?: string; bairro?: string; uf?: string }
  modelo_negocio: { tipo?: string }
}

async function erroDaResposta(r: Response, fallback: string): Promise<string> {
  try {
    const ct = r.headers.get('content-type') ?? ''
    if (ct.includes('application/json')) {
      const j = await r.json()
      const msg = j?.detail ?? j?.message ?? j?.error
      if (msg) return typeof msg === 'string' ? msg : JSON.stringify(msg)
    } else {
      const t = (await r.text()).trim()
      if (t) return t.slice(0, 300)
    }
  } catch {
    /* noop */
  }
  return fallback
}

export async function conversarSite(
  mensagem: string,
  projetoId?: string,
  turnstileToken?: string,
  agente: AgenteApiId = 'degustacao',
  devToken?: string,
): Promise<{ projeto_id: string; status: string }> {
  const r = await fetch(`${API_BASE}/api/site-agent/conversar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mensagem,
      projeto_id: projetoId,
      turnstile_token: turnstileToken,
      agente,
      dev_token: devToken,
    }),
  })
  if (r.status === 403) throw new Error('Verificação anti-bot falhou. Recarregue a página.')
  if (!r.ok) throw new Error(await erroDaResposta(r, `Erro ${r.status} ao enviar.`))
  return r.json()
}

export async function pollSiteMensagens(
  projetoId: string,
  desde?: string,
): Promise<PollSiteResponse> {
  const u = new URL(`${API_BASE}/api/site-agent/conversar/${projetoId}/mensagens`)
  if (desde) u.searchParams.set('desde', desde)
  const r = await fetch(u.toString())
  if (!r.ok) throw new Error(await erroDaResposta(r, `Erro ${r.status} no polling.`))
  return r.json()
}

export async function criarAnalise(payload: {
  nome: string
  email: string
  telefone?: string
  cidade: string
  bairro: string
  uf?: string
  tipo_negocio?: string
  turnstile_token: string
  utm_source?: string
}): Promise<{
  status: string
  relatorio_id?: string
  access_token?: string
  eta_min?: number
  mensagem: string
}> {
  const r = await fetch(`${API_BASE}/api/site-agent/analise`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw new Error(`Erro ${r.status} ao gerar análise.`)
  return r.json()
}

export async function pollAnalise(
  relatorioId: string,
  token: string,
): Promise<Record<string, unknown>> {
  const r = await fetch(
    `${API_BASE}/api/site-agent/analise/${relatorioId}?token=${encodeURIComponent(token)}`,
  )
  if (!r.ok) throw new Error(`Erro ${r.status} no polling.`)
  return r.json()
}
