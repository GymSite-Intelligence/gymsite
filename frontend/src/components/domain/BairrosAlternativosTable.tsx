/**
 * BairrosAlternativosTable — bairros sugeridos quando score baixo.
 *
 * Cada linha tem: bairro, motivo, status competitivo (emoji), ticket,
 * prioridade (badge colorida), academias existentes (expansível inline).
 */
import { cn } from '@/lib/utils'
import type { BairroAlternativoJSON } from '@/hooks/useRelatorioDetail'

export interface BairrosAlternativosTableProps {
  bairros: BairroAlternativoJSON[] | undefined
  className?: string
}

const PRIORIDADE_COLOR: Record<string, string> = {
  ALTA: 'bg-veredito-aprovado text-white',
  MEDIA: 'bg-veredito-ressalvas text-black',
  BAIXA: 'bg-veredito-reprovado text-white',
}

function statusEmoji(status: string | undefined): string {
  if (!status) return '⚪'
  if (status.includes('🔴') || /muito.?saturad/i.test(status)) return '🔴'
  if (status.includes('🟡') || /1.?concorrente/i.test(status)) return '🟡'
  if (status.includes('🟢') || /sem.?concorrente/i.test(status)) return '🟢'
  return '⚪'
}

export function BairrosAlternativosTable({
  bairros,
  className,
}: BairrosAlternativosTableProps) {
  if (!bairros || bairros.length === 0) {
    return (
      <div className={cn('rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground', className)}>
        Sem bairros alternativos sugeridos.
      </div>
    )
  }

  return (
    <div className={cn('rounded-lg border border-border bg-card overflow-hidden', className)}>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono border-b border-border bg-muted/20">
              <th className="text-left p-3 font-medium">Bairro</th>
              <th className="text-left p-3 font-medium">Motivo</th>
              <th className="text-left p-3 font-medium">Status competitivo</th>
              <th className="text-center p-3 font-medium">Ticket</th>
              <th className="text-center p-3 font-medium">Prioridade</th>
              <th className="text-left p-3 font-medium">Fonte</th>
            </tr>
          </thead>
          <tbody>
            {bairros.map((b, i) => {
              const prioridade = b.prioridade_ajustada ?? 'MEDIA'
              const colorClass = PRIORIDADE_COLOR[prioridade] ?? PRIORIDADE_COLOR.MEDIA
              return (
                <tr key={i} className="border-b border-border last:border-b-0 hover:bg-muted/30">
                  <td className="p-3 font-semibold text-sm align-top">{b.bairro}</td>
                  <td className="p-3 text-xs text-muted-foreground align-top max-w-[280px]">
                    {b.motivo}
                  </td>
                  <td className="p-3 text-xs align-top">
                    <div className="flex items-start gap-1.5">
                      <span aria-hidden>{statusEmoji(b.status)}</span>
                      <div className="space-y-1">
                        <span className="text-muted-foreground capitalize">
                          {(b.status ?? '—').replace(/🔴|🟡|🟢/g, '').trim() || '—'}
                        </span>
                        {b.academias_existentes && b.academias_existentes.length > 0 && (
                          <details className="font-mono text-[10px]">
                            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                              ver {b.concorrentes_no_bairro ?? b.academias_existentes.length}{' '}
                              {(b.concorrentes_no_bairro ?? b.academias_existentes.length) === 1 ? 'academia' : 'academias'}
                            </summary>
                            <ul className="mt-1 space-y-0.5 pl-3">
                              {b.academias_existentes.slice(0, 8).map((a, j) => (
                                <li key={j} className="text-muted-foreground/80">· {a}</li>
                              ))}
                              {b.academias_existentes.length > 8 && (
                                <li className="text-muted-foreground/60 italic">
                                  + {b.academias_existentes.length - 8} mais
                                </li>
                              )}
                            </ul>
                          </details>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="p-3 text-center text-xs font-mono">
                    {b.ticket_sugerido ?? 'mid'}
                  </td>
                  <td className="p-3 text-center">
                    <span
                      className={cn(
                        'inline-block px-2 py-0.5 rounded text-[10px] font-semibold font-mono',
                        colorClass,
                      )}
                    >
                      {prioridade}
                    </span>
                  </td>
                  <td className="p-3 text-[10px] font-mono text-muted-foreground align-top max-w-[140px]">
                    {b.fonte_busca_competidores === 'overpass_osm' ? (
                      <span title={b.metodologia}>OSM (Maps off)</span>
                    ) : b.fonte_busca_competidores === 'cnpj_rfb' ? (
                      <span title={b.metodologia}>CNPJ RFB</span>
                    ) : b.fonte_busca_competidores === 'google_places' ? (
                      'Google Places'
                    ) : b.dados_confiaveis === false ? (
                      <span className="text-veredito-investigar">Estimativa A3*</span>
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
    </div>
  )
}
