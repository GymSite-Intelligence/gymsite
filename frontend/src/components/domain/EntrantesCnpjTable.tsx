/**
 * Tabela de novas unidades no parque (CNPJ RFB, últimos 90 dias).
 */
import { Building2, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  CONFIANCA_HINT,
  SEGMENTO_BADGE_CLASS,
  SEGMENTO_PARQUE_LABELS,
} from '@/lib/segmento-parque'
import type { EntrantesCnpj90dJSON } from '@/hooks/useRelatorioDetail'

export interface EntrantesCnpjTableProps {
  block?: EntrantesCnpj90dJSON | null
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

export function EntrantesCnpjTable({ block, className }: EntrantesCnpjTableProps) {
  if (!block || block.status === 'indisponivel') return null
  const lista = block.entrantes ?? []
  if (lista.length === 0) return null

  const porSegmento = block.novas_unidades_90d_por_segmento
  const resumoSegmento =
    porSegmento && Object.keys(porSegmento).length > 0
      ? Object.entries(porSegmento)
          .filter(([, n]) => n > 0)
          .sort(([, a], [, b]) => b - a)
          .map(
            ([k, n]) =>
              `${SEGMENTO_PARQUE_LABELS[k] ?? k}: ${n}`,
          )
          .join(' · ')
      : null

  return (
    <div className={cn('space-y-3', className)}>
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground flex items-center gap-1.5">
          <Building2 size={12} />
          Novas unidades (90 dias)
        </h4>
        <span className="text-xs font-mono text-muted-foreground tabular-nums">
          {block.total ?? lista.length} unidades · cutoff {formatData(block.cutoff)}
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

      <div className="rounded-md border border-border overflow-x-auto">
        <table className="w-full text-xs min-w-[640px]">
          <thead>
            <tr className="border-b border-border bg-muted/40 text-left">
              <th className="px-2 py-2 font-mono text-[10px]">Abertura</th>
              <th className="px-2 py-2 font-mono text-[10px]">Segmento</th>
              <th className="px-2 py-2 font-mono text-[10px]">Nome fantasia</th>
              <th className="px-2 py-2 font-mono text-[10px]">CNPJ</th>
              <th className="px-2 py-2 font-mono text-[10px]">Endereço</th>
              <th className="px-2 py-2 font-mono text-[10px]">CEP</th>
            </tr>
          </thead>
          <tbody>
            {lista.map((e) => {
              const nome =
                e.nome_fantasia?.trim() ||
                (e.razao_social_indisponivel ? '(sem nome fantasia)' : '—')
              const endereco = e.endereco || ''
              return (
                <tr
                  key={e.cnpj}
                  className="border-b border-border last:border-0 hover:bg-muted/30"
                >
                  <td className="px-2 py-2 whitespace-nowrap tabular-nums">
                    {formatData(e.data_abertura)}
                  </td>
                  <td className="px-2 py-2 whitespace-nowrap">
                    {e.segmento_operacao ? (
                      <span
                        className={cn(
                          'inline-block rounded px-1.5 py-0.5 text-[10px] font-mono',
                          SEGMENTO_BADGE_CLASS[e.segmento_operacao] ??
                            SEGMENTO_BADGE_CLASS.outro,
                        )}
                      >
                        {CONFIANCA_HINT[e.segmento_confianca ?? ''] ?? ''}
                        {e.segmento_label ??
                          SEGMENTO_PARQUE_LABELS[e.segmento_operacao] ??
                          e.segmento_operacao}
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="px-2 py-2 font-medium max-w-[200px]">{nome}</td>
                  <td className="px-2 py-2 font-mono whitespace-nowrap">
                    {e.cnpj_formatado || e.cnpj}
                  </td>
                  <td className="px-2 py-2 text-muted-foreground max-w-[280px]">
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
                  <td className="px-2 py-2 font-mono whitespace-nowrap">{e.cep ?? '—'}</td>
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
