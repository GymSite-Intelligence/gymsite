import { useCallback, useRef, useState } from 'react'
import { conversarSite, pollSiteMensagens } from '@/lib/site-agent-client'
import type { AgenteApiId } from '@/config/site-agent-map'
import { apiIdFromUi, isAgenteApiId } from '@/config/site-agent-map'
import type { EspecialistaId } from '@/config/consultor-agentes'

export interface SitePrefill {
  cidade?: string
  bairro?: string
  uf?: string
  tipoNegocio?: string
}

const VALIDOS: AgenteApiId[] = [
  'degustacao',
  'mercado',
  'responsavel_tecnico',
  'regulatorio',
  'arquiteto',
  'engenheiro_obra',
]

function agenteInicial(): AgenteApiId {
  if (typeof window === 'undefined') return 'degustacao'
  const a = new URLSearchParams(window.location.search).get('agente')
  if (a && isAgenteApiId(a)) return a
  return 'degustacao'
}

export function useSiteChat() {
  const [carregando, setCarregando] = useState(false)
  const [podeGerar, setPodeGerar] = useState(false)
  const [temProjeto, setTemProjeto] = useState(false)
  const [prefill, setPrefill] = useState<SitePrefill>({})
  const [agente, setAgenteApi] = useState<AgenteApiId>(agenteInicial)
  const projetoId = useRef<string | undefined>(undefined)
  const devToken = useRef<string | undefined>(
    typeof window !== 'undefined'
      ? (new URLSearchParams(window.location.search).get('dev_token') ?? undefined)
      : undefined,
  )

  const setAgentePorUi = useCallback((id: EspecialistaId) => {
    setAgenteApi(apiIdFromUi(id))
  }, [])

  const enviar = useCallback(
    async (texto: string, turnstileToken?: string) => {
      if (!texto.trim() || carregando) return null
      setCarregando(true)
      const desde = new Date().toISOString()
      try {
        const token = projetoId.current ? undefined : turnstileToken
        const { projeto_id } = await conversarSite(
          texto,
          projetoId.current,
          token,
          agente,
          devToken.current,
        )
        projetoId.current = projeto_id
        setTemProjeto(true)

        const t0 = Date.now()
        while (Date.now() - t0 < 240_000) {
          await new Promise((r) => setTimeout(r, 2500))
          const p = await pollSiteMensagens(projeto_id, desde)
          const ans = p.mensagens.filter((x) => x.role === 'assistant')
          if (ans.length) {
            const ultima = ans[ans.length - 1]
            setPodeGerar(p.pode_gerar_relatorio)
            setPrefill({
              cidade: p.localizacao?.cidade,
              bairro: p.localizacao?.bairro,
              uf: p.localizacao?.uf,
              tipoNegocio: p.modelo_negocio?.tipo,
            })
            return {
              role: 'assistant' as const,
              content: ultima.content,
              agenteId: ultima.agente ?? null,
              citacoes: ultima.citacoes,
            }
          }
        }
        return {
          role: 'assistant' as const,
          content: 'A análise demorou mais que o esperado. Tente de novo.',
          agenteId: null,
        }
      } finally {
        setCarregando(false)
      }
    },
    [carregando, agente],
  )

  return {
    carregando,
    podeGerar,
    temProjeto,
    prefill,
    agente,
    setAgenteApi,
    setAgentePorUi,
    projetoId,
    enviar,
    temBypass: Boolean(devToken.current),
    agentesValidos: VALIDOS,
  }
}
