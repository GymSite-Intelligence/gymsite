/**
 * Tabela de novas unidades no parque (CNPJ RFB, últimos 90 dias).
 * Contato PJ + sócio administrador (QSA) e flag de validação manual.
 */
import { useState } from 'react'
import { Building2, ExternalLink, Mail, Phone, Linkedin, Sparkles, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import {
  SEGMENTO_BADGE_CLASS,
  SEGMENTO_PARQUE_LABELS,
} from '@/lib/segmento-parque'
import { Checkbox } from '@/components/ui/checkbox'
import { API_BASE, supabase } from '@/lib/supabase'
import type { EntrantesCnpj90dJSON } from '@/hooks/useRelatorioDetail'

export interface EntrantesCnpjTableProps {
  block?: EntrantesCnpj90dJSON | null
  relatorioId?: string
  className?: string
}

function formatData(iso: string | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR')
  } catch {
    return iso
  }
}

function mapsUrl(endereco: string, cep?: string | null): string {
  const q = [endereco, cep].filter(Boolean).join(', ')
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`
}

function ContatoCell({
  email,
  telefone,
}: {
  email?: string | null
  telefone?: string | null
}) {
  if (!email && !telefone) {
    return <span className="text-muted-foreground">—</span>
  }
  return (
    <div className="flex flex-col gap-0.5">
      {email && (
        <a
          href={`mailto:${email}`}
          className="inline-flex items-center gap-1 hover:text-foreground"
        >
          <Mail size={10} />
          <span className="truncate max-w-[140px]">{email}</span>
        </a>
      )}
      {telefone && (
        <span className="inline-flex items-center gap-1 font-mono tabular-nums">
          <Phone size={10} />
          {telefone}
        </span>
      )}
    </div>
  )
}

export function EntrantesCnpjTable({
  block,
  relatorioId,
  className,
}: EntrantesCnpjTableProps) {
  const queryClient = useQueryClient()
  const [localValidado, setLocalValidado] = useState<Record<string, boolean>>({})
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set())

  const [enriquecendoCnpj, setEnriquecendoCnpj] = useState<string | null>(null)

  const enriquecerMutation = useMutation({
    mutationFn: async ({ cnpj }: { cnpj: string }) => {
      const { data: sessionData } = await supabase.auth.getSession()
      const token = sessionData.session?.access_token
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers.Authorization = `Bearer ${token}`

      const res = await fetch(
        `${API_BASE}/api/relatorios/${relatorioId}/entrantes-cnpj/enriquecer`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ cnpj, usar_apollo: true }),
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(
          (err as { detail?: string }).detail || `HTTP ${res.status}`,
        )
      }
      return res.json()
    },
    onMutate: ({ cnpj }) => setEnriquecendoCnpj(cnpj),
    onSettled: () => setEnriquecendoCnpj(null),
    onSuccess: (data) => {
      if (relatorioId) {
        void queryClient.invalidateQueries({ queryKey: ['relatorio', relatorioId] })
      }
      const meta = (data as { meta?: Record<string, unknown> })?.meta
      if (meta && typeof window !== 'undefined') {
        const parts: string[] = []
        if (meta.receita_fonte) parts.push(`Receita: ${meta.receita_fonte}`)
        if (meta.receita_motivo) parts.push(String(meta.receita_motivo))
        if (meta.apollo_habilitado) {
          parts.push(
            meta.apollo_ok ? 'Apollo: contato encontrado' : 'Apollo: sem e-mail/LinkedIn',
          )
        } else if (meta.apollo_habilitado === false) {
          parts.push('Apollo: desligado (sem APOLLO_API_KEY)')
        }
        if (parts.length) {
          window.alert(`Enriquecimento\n${parts.join('\n')}`)
        }
      }
    },
  })

  const validarMutation = useMutation({
    mutationFn: async ({
      cnpj,
      validado,
    }: {
      cnpj: string
      validado: boolean
    }) => {
      const { data: sessionData } = await supabase.auth.getSession()
      const token = sessionData.session?.access_token
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers.Authorization = `Bearer ${token}`

      const res = await fetch(
        `${API_BASE}/api/relatorios/${relatorioId}/entrantes-cnpj/validacao`,
        {
          method: 'PATCH',
          headers,
          body: JSON.stringify({ cnpj, validado }),
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(
          (err as { detail?: string }).detail || `HTTP ${res.status}`,
        )
      }
      return res.json()
    },
    onSuccess: () => {
      if (relatorioId) {
        void queryClient.invalidateQueries({ queryKey: ['relatorio', relatorioId] })
      }
    },
  })

  const enviarProspeccaoMutation = useMutation({
    mutationFn: async (cnpjs: string[]) => {
      const { data: sessionData } = await supabase.auth.getSession()
      const token = sessionData.session?.access_token
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers.Authorization = `Bearer ${token}`

      const res = await fetch(
        `${API_BASE}/api/relatorios/${relatorioId}/entrantes-cnpj/prospeccao`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ cnpjs, cidade: block?.cidade ?? 'Fortaleza', uf: block?.uf ?? 'CE' }),
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(
          (err as { detail?: string }).detail || `HTTP ${res.status}`,
        )
      }
      return res.json() as Promise<{
        ok: boolean
        inseridos: string[]
        atualizados: string[]
        erros: { cnpj: string; motivo: string }[]
        total_enviados: number
      }>
    },
    onSuccess: (data) => {
      setSelecionados(new Set())
      void queryClient.invalidateQueries({ queryKey: ['prospeccao', 'oportunidades'] })
      const parts: string[] = []
      if (data.inseridos.length) parts.push(`${data.inseridos.length} inseridos`)
      if (data.atualizados.length) parts.push(`${data.atualizados.length} já existiam`)
      if (data.erros.length) parts.push(`${data.erros.length} erros`)
      window.alert(`Prospecção\n${parts.join(' | ')}`)
    },
    onError: (err) => {
      window.alert(`Erro ao enviar para prospecção: ${err.message}`)
    },
  })

  if (!block || block.status === 'indisponivel') return null
  const lista = block.entrantes ?? []
  if (lista.length === 0) return null

  const porSegmento = block.novas_unidades_90d_por_segmento
  const resumoSegmento =
    porSegmento && Object.keys(porSegmento).length > 0
      ? Object.entries(porSegmento)
          .filter(([, n]) => n > 0)
          .sort(([, a], [, b]) => b - a)
          .map(([k, n]) => `${SEGMENTO_PARQUE_LABELS[k] ?? k}: ${n}`)
          .join(' · ')
      : null

  const incompletos = block.entrantes_incompletos ?? 0

  return (
    <div className={cn('space-y-3', className)}>
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground flex items-center gap-1.5">
          <Building2 size={12} />
          Novas unidades (90 dias)
        </h4>
        <span className="text-xs font-mono text-muted-foreground tabular-nums">
          {block.total ?? lista.length} unidades · cutoff {formatData(block.cutoff)}
          {incompletos > 0 && ` · ${incompletos} com lacunas`}
        </span>
      </header>

      {selecionados.size > 0 && (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            className="h-7 text-[10px] gap-1"
            disabled={enviarProspeccaoMutation.isPending}
            onClick={() => enviarProspeccaoMutation.mutate(Array.from(selecionados))}
          >
            <Send size={10} />
            {enviarProspeccaoMutation.isPending
              ? 'Enviando…'
              : `Enviar ${selecionados.size} para Prospecção`}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-[10px]"
            onClick={() => setSelecionados(new Set())}
          >
            Limpar
          </Button>
        </div>
      )}

      {resumoSegmento && (
        <p className="text-[11px] text-muted-foreground leading-snug">
          Por segmento: {resumoSegmento}
        </p>
      )}

      {block.nota && (
        <p className="text-[11px] text-muted-foreground leading-snug">{block.nota}</p>
      )}

      <p className="text-[10px] text-muted-foreground leading-snug">
        Lista vem do snapshot RFB (90 dias). Razão social é carregada automaticamente;
        QSA (sócio administrador) e contato do decisor (Apollo) são enriquecidos no pipeline
        quando disponíveis. Use <strong>Enriquecer</strong> por linha para forçar uma nova
        consulta ou quando os dados estiverem incompletos.
      </p>

      <div className="rounded-md border border-border overflow-x-auto">
        <table className="w-full text-xs min-w-[960px]">
          <thead>
            <tr className="border-b border-border bg-muted/40 text-left">
              <th className="px-2 py-2 font-mono text-[10px] w-8">
                <Checkbox
                  checked={selecionados.size > 0 && selecionados.size === lista.length}
                  onCheckedChange={(checked) => {
                    if (checked === true) {
                      setSelecionados(new Set(lista.map((e) => e.cnpj)))
                    } else {
                      setSelecionados(new Set())
                    }
                  }}
                  aria-label="Selecionar todos"
                />
              </th>
              <th className="px-2 py-2 font-mono text-[10px] w-8">OK</th>
              <th className="px-2 py-2 font-mono text-[10px]">Abertura</th>
              <th className="px-2 py-2 font-mono text-[10px]">Segmento</th>
              <th className="px-2 py-2 font-mono text-[10px]">Nome</th>
              <th className="px-2 py-2 font-mono text-[10px]">Razão social</th>
              <th className="px-2 py-2 font-mono text-[10px]">Bairro</th>
              <th className="px-2 py-2 font-mono text-[10px]">PJ (e-mail / tel)</th>
              <th className="px-2 py-2 font-mono text-[10px]">Sócio adm.</th>
              <th className="px-2 py-2 font-mono text-[10px] w-24">Ação</th>
              <th className="px-2 py-2 font-mono text-[10px]">CNPJ</th>
              <th className="px-2 py-2 font-mono text-[10px]">Endereço</th>
            </tr>
          </thead>
          <tbody>
            {lista.map((e) => {
              const nome =
                e.nome_exibicao?.trim() ||
                e.nome_fantasia?.trim() ||
                e.razao_social?.trim() ||
                '—'
              const razao = e.razao_social?.trim() || '—'
              const bairro = e.bairro?.trim() || '—'
              const endereco = e.endereco || ''
              const socioNome = e.socio_administrador?.nome
              const validado =
                localValidado[e.cnpj] ?? Boolean(e.contato_validado)
              const canToggle = Boolean(relatorioId)

              return (
                <tr
                  key={e.cnpj}
                  className={cn(
                    'border-b border-border last:border-0 hover:bg-muted/30',
                    !e.dados_completos && 'bg-veredito-investigar/5',
                  )}
                >
                  <td className="px-2 py-2 align-top">
                    <Checkbox
                      checked={selecionados.has(e.cnpj)}
                      disabled={enviarProspeccaoMutation.isPending}
                      onCheckedChange={(checked) => {
                        setSelecionados((prev) => {
                          const next = new Set(prev)
                          if (checked === true) next.add(e.cnpj)
                          else next.delete(e.cnpj)
                          return next
                        })
                      }}
                      aria-label={`Selecionar ${nome} para prospecção`}
                    />
                  </td>
                  <td className="px-2 py-2 align-top">
                    <Checkbox
                      checked={validado}
                      disabled={!canToggle || validarMutation.isPending}
                      onCheckedChange={(checked) => {
                        const v = checked === true
                        setLocalValidado((prev) => ({ ...prev, [e.cnpj]: v }))
                        if (canToggle) {
                          validarMutation.mutate({ cnpj: e.cnpj, validado: v })
                        }
                      }}
                      aria-label={`Validar contato ${nome}`}
                    />
                  </td>
                  <td className="px-2 py-2 whitespace-nowrap tabular-nums align-top">
                    {formatData(e.data_abertura)}
                  </td>
                  <td className="px-2 py-2 whitespace-nowrap align-top">
                    {e.segmento_operacao ? (
                      <span
                        className={cn(
                          'inline-block rounded px-1.5 py-0.5 text-[10px] font-mono',
                          SEGMENTO_BADGE_CLASS[e.segmento_operacao] ??
                            SEGMENTO_BADGE_CLASS.outro,
                        )}
                      >
                        {e.segmento_label ??
                          SEGMENTO_PARQUE_LABELS[e.segmento_operacao] ??
                          e.segmento_operacao}
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="px-2 py-2 font-medium max-w-[160px] align-top">
                    {nome}
                    {e.nome_fantasia_inferido_de === 'razao_social' && (
                      <span className="block text-[9px] text-muted-foreground font-mono">
                        via razão social
                      </span>
                    )}
                  </td>
                  <td
                    className={cn(
                      'px-2 py-2 max-w-[160px] align-top',
                      !e.razao_social && 'text-veredito-reprovado',
                    )}
                  >
                    {razao}
                  </td>
                  <td
                    className={cn(
                      'px-2 py-2 whitespace-nowrap align-top',
                      !e.bairro && 'text-veredito-reprovado',
                    )}
                  >
                    {bairro}
                  </td>
                  <td className="px-2 py-2 align-top">
                    <ContatoCell
                      email={e.email_empresa}
                      telefone={e.telefone_empresa}
                    />
                  </td>
                  <td className="px-2 py-2 align-top max-w-[180px]">
                    <div className="flex flex-col gap-0.5">
                      {socioNome && (
                        <span className="block text-[10px] font-medium mb-0.5 line-clamp-1">
                          {socioNome}
                        </span>
                      )}
                      <ContatoCell
                        email={e.email_socio_administrador}
                        telefone={e.telefone_socio_administrador}
                      />
                      {e.linkedin_url && (
                        <a
                          href={e.linkedin_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[10px] text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 mt-0.5 font-medium"
                        >
                          <Linkedin size={10} className="shrink-0" />
                          <span className="truncate max-w-[140px]">LinkedIn</span>
                        </a>
                      )}
                    </div>
                  </td>
                  <td className="px-2 py-2 align-top">
                    {canToggle && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-7 text-[10px] gap-1"
                        disabled={
                          enriquecerMutation.isPending &&
                          enriquecendoCnpj === e.cnpj
                        }
                        onClick={() =>
                          enriquecerMutation.mutate({ cnpj: e.cnpj })
                        }
                      >
                        <Sparkles size={10} />
                        {enriquecendoCnpj === e.cnpj ? '…' : 'Enriquecer'}
                      </Button>
                    )}
                  </td>
                  <td className="px-2 py-2 font-mono whitespace-nowrap align-top">
                    {e.cnpj_formatado || e.cnpj}
                  </td>
                  <td className="px-2 py-2 text-muted-foreground max-w-[220px] align-top">
                    {endereco ? (
                      <a
                        href={mapsUrl(endereco, e.cep)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 hover:text-foreground underline-offset-2 hover:underline"
                      >
                        <span className="line-clamp-2">{endereco}</span>
                        <ExternalLink size={10} className="shrink-0" />
                      </a>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {block.fonte && (
        <p className="text-[10px] font-mono text-muted-foreground">Fonte: {block.fonte}</p>
      )}
    </div>
  )
}
