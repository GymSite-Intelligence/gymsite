/**
 * Tabela de novas unidades no parque (CNPJ RFB, últimos 90 dias).
 * Contato PJ + sócio administrador (QSA) e flag de validação manual.
 */
import { useState } from 'react'
import { Building2, ExternalLink, Mail, Phone, Linkedin } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import {
  SEGMENTO_BADGE_CLASS,
  SEGMENTO_PARQUE_LABELS,
} from '@/lib/segmento-parque'
import { Checkbox } from '@/components/ui/checkbox'
import { API_BASE } from '@/lib/supabase'
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

  const validarMutation = useMutation({
    mutationFn: async ({
      cnpj,
      validado,
    }: {
      cnpj: string
      validado: boolean
    }) => {
      const res = await fetch(
        `${API_BASE}/api/relatorios/${relatorioId}/entrantes-cnpj/validacao`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
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

      {resumoSegmento && (
        <p className="text-[11px] text-muted-foreground leading-snug">
          Por segmento: {resumoSegmento}
        </p>
      )}

      {block.nota && (
        <p className="text-[11px] text-muted-foreground leading-snug">{block.nota}</p>
      )}

      <p className="text-[10px] text-muted-foreground leading-snug">
        Razão social e bairro obrigatórios para prospecção. Sem nome fantasia, exibimos a
        razão social. E-mail/telefone do sócio administrador dependem da fonte (ReceitaWS
        costuma trazer só contatos da PJ).
      </p>

      <div className="rounded-md border border-border overflow-x-auto">
        <table className="w-full text-xs min-w-[960px]">
          <thead>
            <tr className="border-b border-border bg-muted/40 text-left">
              <th className="px-2 py-2 font-mono text-[10px] w-8">OK</th>
              <th className="px-2 py-2 font-mono text-[10px]">Abertura</th>
              <th className="px-2 py-2 font-mono text-[10px]">Segmento</th>
              <th className="px-2 py-2 font-mono text-[10px]">Nome</th>
              <th className="px-2 py-2 font-mono text-[10px]">Razão social</th>
              <th className="px-2 py-2 font-mono text-[10px]">Bairro</th>
              <th className="px-2 py-2 font-mono text-[10px]">PJ (e-mail / tel)</th>
              <th className="px-2 py-2 font-mono text-[10px]">Sócio adm.</th>
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
