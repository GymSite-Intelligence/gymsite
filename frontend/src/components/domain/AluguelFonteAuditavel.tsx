/**
 * AluguelFonteAuditavel — a fonte do aluguel deixa de ser uma string de fé
 * ("Portais | N=33") e vira evidência expansível: cada anúncio com preço,
 * m², R$/m², portal e URL clicável (12/06).
 *
 * Gate comercial visível: badge com a categoria e quantos anúncios
 * residenciais foram DESCARTADOS da mediana (proxy residencial superestima
 * aluguel comercial grande em ~2-3×).
 */
import { useState } from 'react'
import { ChevronDown, ChevronUp, ExternalLink, ShieldCheck } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface AluguelAmostra {
  price_reais?: number
  area_m2?: number
  r_m2?: number
  url?: string
  portal?: string
  categoria?: string
}

export interface AluguelFonteMeta {
  fonte?: string
  n_validos?: number
  confianca?: string
  categoria_gate?: string
  descartadas_residenciais?: number
  faixa_rs_m2?: { p25?: number; mediana?: number; p75?: number }
  coletado_em?: string
}

const fmtBRL = (v?: number) =>
  v != null
    ? v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
    : '—'

export function AluguelFonteAuditavel({
  fonte,
  medianaM2,
  amostras,
  meta,
  className,
}: {
  fonte?: string | null
  medianaM2?: number | null
  amostras?: AluguelAmostra[] | null
  meta?: AluguelFonteMeta | null
  className?: string
}) {
  const [aberto, setAberto] = useState(false)
  const lista = amostras ?? []

  if (!fonte && lista.length === 0) return null

  return (
    <div className={cn('text-[10px] font-mono text-muted-foreground', className)}>
      <button
        type="button"
        onClick={() => lista.length > 0 && setAberto(!aberto)}
        className={cn(
          'inline-flex items-center gap-1',
          lista.length > 0 && 'hover:text-foreground cursor-pointer',
        )}
      >
        fonte aluguel: {fonte ?? meta?.fonte ?? '—'}
        {meta?.n_validos != null && <> | N={meta.n_validos}</>}
        {medianaM2 != null && <> · R$ {Number(medianaM2).toFixed(2)}/m²</>}
        {lista.length > 0 && (aberto ? <ChevronUp size={11} /> : <ChevronDown size={11} />)}
      </button>

      {meta?.categoria_gate === 'comercial' && (
        <span className="ml-2 inline-flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400">
          <ShieldCheck size={10} /> só comercial
          {(meta.descartadas_residenciais ?? 0) > 0 && (
            <span className="text-muted-foreground">
              {' '}({meta.descartadas_residenciais} residenciais descartados)
            </span>
          )}
        </span>
      )}

      {aberto && lista.length > 0 && (
        <div className="mt-2 rounded-md border border-border bg-muted/20 p-2 max-h-64 overflow-y-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="text-left text-muted-foreground/70 uppercase">
                <th className="pr-2 pb-1">Anúncio</th>
                <th className="pr-2 pb-1 text-right">Preço</th>
                <th className="pr-2 pb-1 text-right">m²</th>
                <th className="pr-2 pb-1 text-right">R$/m²</th>
                <th className="pb-1">Portal</th>
              </tr>
            </thead>
            <tbody>
              {lista.map((a, i) => (
                <tr key={i} className="border-t border-border/50">
                  <td className="pr-2 py-0.5">
                    {a.url ? (
                      <a
                        href={a.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-0.5 text-primary hover:underline"
                      >
                        ver anúncio <ExternalLink size={9} />
                      </a>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="pr-2 py-0.5 text-right tabular-nums">{fmtBRL(a.price_reais)}</td>
                  <td className="pr-2 py-0.5 text-right tabular-nums">{a.area_m2 ?? '—'}</td>
                  <td className="pr-2 py-0.5 text-right tabular-nums font-medium">
                    {a.r_m2 != null ? `R$ ${Number(a.r_m2).toFixed(2)}` : '—'}
                  </td>
                  <td className="py-0.5 uppercase">{a.portal ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {meta?.coletado_em && (
            <p className="mt-1.5 text-muted-foreground/60">
              coletado em {meta.coletado_em.slice(0, 10)} · preços de anúncio (asking) — valor
              fechado costuma ficar 5-10% abaixo
            </p>
          )}
        </div>
      )}
    </div>
  )
}
