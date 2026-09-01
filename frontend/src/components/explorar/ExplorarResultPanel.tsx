import { Download, X } from 'lucide-react'
import { ExplorarAbsorcaoVisual } from '@/components/explorar/ExplorarAbsorcaoVisual'
import type { ExplorarTopViasResult } from '@/hooks/useExplorarTopVias'
import type { AbsorcaoMargemFrescaJSON } from '@/hooks/useRelatorioDetail'
import { cn } from '@/lib/utils'
import { explorarChrome, useExplorarSite } from './explorar-chrome'
import type { ExplorarRival } from './ExplorarMap'

function fluxoCarimboText(raw: unknown): string {
  if (raw == null) return ''
  if (typeof raw === 'string') return raw
  if (typeof raw === 'object') {
    const o = raw as { valor?: unknown; base?: string; fonte?: string; janela?: string }
    const parts = [o.valor, o.base, o.fonte, o.janela].filter((x) => x != null && x !== '')
    return parts.map(String).join(' · ')
  }
  return String(raw)
}

export function ExplorarResultPanel({
  open,
  onOpenChange,
  absorcao,
  rivals,
  baseLabel,
  loggedIn,
  pdfLoading,
  onBaixarPdf,
  emailCapturado,
  viasOn,
  topVias,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  absorcao: AbsorcaoMargemFrescaJSON
  rivals: ExplorarRival[]
  baseLabel: string
  loggedIn: boolean
  pdfLoading?: boolean
  onBaixarPdf: () => void
  emailCapturado?: boolean
  viasOn?: boolean
  topVias?: ExplorarTopViasResult
}) {
  const chrome = explorarChrome(useExplorarSite())

  if (!open) return null

  return (
    <aside
      className={cn(
        chrome,
        'pointer-events-auto absolute z-50 flex min-w-0 flex-col overflow-hidden rounded-xl border shadow-lg',
        'inset-x-3.5 top-18 bottom-auto max-h-[min(48dvh,22rem)] w-auto',
        'md:inset-auto md:bottom-20 md:right-3.5 md:top-16 md:max-h-none md:w-88 md:max-w-[calc(100vw-1.75rem)]',
      )}
      aria-label="Análise do recorte"
    >
      <header className="flex shrink-0 items-start justify-between gap-2 border-b border-border px-3.5 py-3">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-foreground">Quem ainda pode matricular neste recorte</h2>
          <p className="mt-0.5 text-[11px] leading-snug wrap-break-word text-muted-foreground">
            {baseLabel}
          </p>
        </div>
        <button
          type="button"
          aria-label="Fechar análise"
          onClick={() => onOpenChange(false)}
          className="shrink-0 rounded-md p-1 text-muted-foreground hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <X className="size-4" />
        </button>
      </header>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto px-3.5 py-3">
        <ExplorarAbsorcaoVisual absorcao={absorcao} />
        {viasOn && topVias?.status === 'ok' && topVias.top_vias.length > 0 && (
          <section className="mt-3 min-w-0 rounded-xl border border-border bg-secondary/40 p-3">
            <h3 className="explorar-label mb-2">Vias de maior fluxo</h3>
            <ul className="space-y-1 text-sm">
              {topVias.top_vias.slice(0, 3).map((v, i) => (
                <li
                  key={`${v.nome_via ?? 'via'}-${i}`}
                  className="flex min-w-0 items-baseline justify-between gap-2 border-b border-border/60 py-1.5 last:border-0"
                >
                  <span className="min-w-0 truncate font-semibold text-foreground">
                    {v.nome_via?.trim() || `Via ${i + 1}`}
                  </span>
                  <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                    {v.fluxo_score != null ? `fluxo ${v.fluxo_score}` : ''}
                  </span>
                </li>
              ))}
            </ul>
            {topVias.top_vias[0]?.fluxo_carimbo && (
              <p className="mt-2 text-[11px] font-mono text-muted-foreground/80">
                {fluxoCarimboText(topVias.top_vias[0].fluxo_carimbo)}
              </p>
            )}
          </section>
        )}
        <section className="mt-3 min-w-0 rounded-xl border border-border bg-secondary/40 p-3">
          <h3 className="explorar-label mb-2">Academias no recorte ({rivals.length})</h3>
          <ul className="space-y-1 text-sm">
            {rivals.slice(0, 12).map((r) => (
              <li
                key={`${r.nome}-${r.lat}`}
                className="flex min-w-0 items-baseline justify-between gap-2 border-b border-border/60 py-1.5 last:border-0"
              >
                <span className="min-w-0 truncate font-semibold text-foreground">{r.nome}</span>
                <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                  {r.dist_m != null ? `${r.dist_m} m` : ''}
                  {r.rating != null ? ` · ${r.rating}` : ''}
                </span>
              </li>
            ))}
            {rivals.length === 0 && (
              <li className="text-muted-foreground">Nenhuma academia no recorte.</li>
            )}
          </ul>
        </section>
        {rivals.some((r) => (r.reclamacoes?.length ?? 0) > 0) && (
          <section className="mt-3 min-w-0 rounded-xl border border-border bg-secondary/40 p-3">
            <h3 className="explorar-label mb-2">Reclamações no Google Maps (nota ≤ 3)</h3>
            <ul className="space-y-3">
              {rivals
                .filter((r) => (r.reclamacoes?.length ?? 0) > 0)
                .map((r) => (
                  <li key={`${r.nome}-recs`} className="min-w-0">
                    <p className="text-[11px] font-semibold text-foreground">{r.nome}</p>
                    <ul className="mt-1 space-y-1.5">
                      {(r.reclamacoes ?? []).slice(0, 5).map((c, i) => (
                        <li
                          key={`${r.nome}-${i}`}
                          className="rounded-md border border-border/70 bg-card px-2 py-1.5 text-[11px] leading-snug text-muted-foreground"
                        >
                          <span className="font-semibold tabular-nums text-destructive">{c.rating}★</span>
                          {' — '}
                          {c.texto}
                          {c.autor ? <span className="opacity-70"> · {c.autor}</span> : null}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
            </ul>
          </section>
        )}
      </div>

      <footer className="shrink-0 border-t border-border p-3">
        {loggedIn ? (
          <button
            type="button"
            disabled={pdfLoading}
            onClick={onBaixarPdf}
            className="explorar-cta w-full gap-2"
          >
            <Download className="size-4" />
            {pdfLoading ? 'Gerando relatório…' : 'Baixar Relatório PDF'}
          </button>
        ) : (
          <p className="text-xs leading-snug text-muted-foreground">
            {emailCapturado
              ? 'Enviamos o resumo deste recorte para o seu e-mail. Sem compromisso de compra.'
              : 'Leitura grátis no mapa.'}
          </p>
        )}
      </footer>
    </aside>
  )
}
