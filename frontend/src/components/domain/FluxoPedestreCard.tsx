/**
 * FluxoPedestreCard — leitura do bloco fluxo_pedestre (sintaxe espacial / movimento natural).
 */
import { Route } from 'lucide-react'

import type { FluxoPedestreJSON } from '@/hooks/useRelatorioDetail'
import { Badge } from '@/components/ui/badge'
import { CitationStamp } from '@/components/chat/CitationStamp'

function scoreVariant(score: number): 'success' | 'warning' | 'secondary' {
  if (score >= 70) return 'success'
  if (score >= 40) return 'warning'
  return 'secondary'
}

export function FluxoPedestreCard({ block }: { block: FluxoPedestreJSON }) {
  if (!block || block.confianca === 'indisponivel') {
    return (
      <p className="text-sm text-muted-foreground">
        Fluxo estrutural indisponível — malha viária OSM não carregou para este ponto (timeout ou
        área sem rede walk).
      </p>
    )
  }

  const score = block.fluxo_score
  const stats = block.statistics ?? {}
  const top = (block.top_segments ?? []).slice(0, 5)
  const carimbo = block.carimbo

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Route size={16} className="text-primary" />
          <span className="text-xs font-mono uppercase tracking-wider">Fluxo estrutural</span>
        </div>
        {typeof score === 'number' && (
          <Badge variant={scoreVariant(score)} mono>
            {score}/100
          </Badge>
        )}
        {block.fluxo_segmento && (
          <span className="text-xs text-muted-foreground">
            Segmento do candidato: <strong className="text-foreground">{block.fluxo_segmento}</strong>
          </span>
        )}
      </div>

      {block.leitura && (
        <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-line">
          {block.leitura}
        </p>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {stats.total_segments != null && (
          <Stat label="Segmentos" value={String(stats.total_segments)} />
        )}
        {stats.mean_flow_score != null && (
          <Stat label="Flow médio" value={Number(stats.mean_flow_score).toFixed(3)} />
        )}
        {stats.max_flow_score != null && (
          <Stat label="Flow máx." value={Number(stats.max_flow_score).toFixed(3)} />
        )}
        {block.confianca && <Stat label="Confiança" value={block.confianca} />}
      </div>

      {top.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground mb-2">
            Artérias com maior fluxo previsto
          </p>
          <ul className="space-y-1 text-sm">
            {top.map((seg, i) => {
              const name =
                typeof seg.street_name === 'string'
                  ? seg.street_name
                  : typeof seg.name === 'string'
                    ? seg.name
                    : `Segmento ${i + 1}`
              const fs =
                seg.flow_score != null ? Number(seg.flow_score).toFixed(3) : '—'
              return (
                <li
                  key={`${name}-${i}`}
                  className="flex justify-between gap-2 border-b border-border/50 py-1 last:border-0"
                >
                  <span className="truncate">{name}</span>
                  <span className="font-mono text-xs text-muted-foreground shrink-0">{fs}</span>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {carimbo && (
        <CitationStamp
          citacao={{
            valor: carimbo.valor != null ? String(carimbo.valor) : undefined,
            base: carimbo.base,
            fonte: carimbo.fonte,
            janela: carimbo.janela,
          }}
        />
      )}

      <p className="text-[10px] text-muted-foreground">© OpenStreetMap contributors</p>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-muted/40 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
        {label}
      </div>
      <div className="mt-0.5 text-sm font-semibold">{value}</div>
    </div>
  )
}
