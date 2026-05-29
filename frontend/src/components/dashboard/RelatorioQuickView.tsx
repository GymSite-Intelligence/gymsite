/**
 * RelatorioQuickView — drawer lateral com mini-dashboard de um relatório.
 *
 * Carrega o relatório completo (useRelatorioDetail) lazy ao abrir.
 * Mostra: KPIs financeiros, scores, mapa mini, heatmap de pico e CTA.
 */
import { useNavigate } from '@tanstack/react-router'
import { Map, Marker } from 'pigeon-maps'
import { ExternalLink } from 'lucide-react'
import { useRelatorioDetail } from '@/hooks/useRelatorioDetail'
import { FinanceiroKpiStrip } from '@/components/domain/FinanceiroKpiStrip'
import { ScoreGauge } from '@/components/domain/ScoreGauge'
import { VeredictoBadge } from '@/components/domain/VeredictoBadge'
import { StatusPipelineBadge } from '@/components/domain/StatusPipelineBadge'
import { PopularTimesHeatmap } from './PopularTimesHeatmap'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
// import { cn } from '@/lib/utils'

export interface RelatorioQuickViewProps {
  relatorioId: string | null
  onClose: () => void
}

export function RelatorioQuickView({ relatorioId, onClose }: RelatorioQuickViewProps) {
  const navigate = useNavigate()
  const { data, isLoading } = useRelatorioDetail(relatorioId ?? undefined)

  const open = relatorioId != null

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto p-0">
        {isLoading || !data ? (
          <div className="p-6 space-y-6">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        ) : (
          <QuickViewContent
            data={data}
            onVerCompleto={() =>
              navigate({
                to: '/relatorios/$relatorioId',
                params: { relatorioId: data.id },
              })
            }
          />
        )}
      </SheetContent>
    </Sheet>
  )
}

function QuickViewContent({
  data,
  onVerCompleto,
}: {
  data: NonNullable<ReturnType<typeof useRelatorioDetail>['data']>
  onVerCompleto: () => void
}) {
  const out = data.output_consolidado
  const inp = data.input_canonico
  const cenarioMid = out.viabilidade_3_cenarios?.mid

  const top1 = out.top_3_candidatos?.[0]
  const hasCoords = top1 && top1.lat != null && top1.lng != null

  const scoresRegionais = out.scores_regionais

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <SheetHeader className="px-6 pt-6 pb-4 pr-12 border-b border-border">
        <div className="min-w-0">
          <SheetTitle className="truncate">
            {inp.bairro} <span className="text-muted-foreground font-normal">·</span>{' '}
            {inp.cidade}
          </SheetTitle>
          <p className="text-xs text-muted-foreground mt-1 font-mono">
            {new Date(data.data_execucao).toLocaleDateString('pt-BR')} · {data.id.slice(0, 8)}
          </p>
        </div>
        <div className="flex items-center gap-2 mt-2">
          <VeredictoBadge veredito={out.veredito} />
          <StatusPipelineBadge status={'done'} />
        </div>
      </SheetHeader>

      {/* KPIs Financeiros */}
      <div className="px-6">
        <FinanceiroKpiStrip
          areaM2Min={inp.area_m2_min}
          areaM2Max={inp.area_m2_max}
          aluguelMensal={out.aluguel_mensal}
          cenarioMid={cenarioMid}
        />
      </div>

      {/* Scores */}
      <div className="px-6 grid grid-cols-2 gap-3">
        <ScoreGauge variant="card" value={out.score_bairro} label="Score Bairro" />
        <ScoreGauge
          variant="card"
          value={out.score_top1_candidato}
          label="Score Top 1 Candidato"
        />
      </div>
      <div className="px-6 space-y-3">
        <ScoreGauge
          value={scoresRegionais?.demografico ?? null}
          label="Demográfico"
        />
        <ScoreGauge
          value={scoresRegionais?.competitivo ?? scoresRegionais?.concorrencia ?? null}
          label="Competitivo"
        />
        <ScoreGauge
          value={scoresRegionais?.viabilidade ?? null}
          label="Viabilidade"
        />
      </div>

      {/* Mini Mapa */}
      {hasCoords && (
        <div className="px-6">
          <h3 className="text-xs uppercase tracking-wider font-mono text-muted-foreground mb-2">
            Top 1 Candidato
          </h3>
          <div className="rounded-lg border border-border overflow-hidden h-[200px]">
            <Map
              defaultCenter={[top1.lat!, top1.lng!]}
              defaultZoom={16}
              attribution={false}
              mouseEvents={false}
              touchEvents={false}
            >
              <Marker anchor={[top1.lat!, top1.lng!]} />
            </Map>
          </div>
          <div className="mt-2 space-y-0.5">
            <p className="text-sm font-medium">{top1.nome}</p>
            <p className="text-xs text-muted-foreground">{top1.endereco}</p>
            <div className="flex items-center gap-3 text-[10px] text-muted-foreground font-mono">
              <span>Score GS {top1.score_geoscout.toFixed(1)}</span>
              <span>Anc {top1.score_ancoragem.toFixed(1)}</span>
              {top1.area_estimada_m2 ? <span>{top1.area_estimada_m2} m²</span> : null}
            </div>
          </div>
        </div>
      )}

      {/* Heatmap de horários de pico */}
      {out.competitors_set && out.competitors_set.length > 0 && (
        <div className="px-6">
          <PopularTimesHeatmap
            competidores={out.competitors_set}
            agregacao="mean"
            compact
          />
        </div>
      )}

      {/* Competitivo rápido */}
      {out.competitors_set && out.competitors_set.length > 0 && (
        <div className="px-6">
          <h3 className="text-xs uppercase tracking-wider font-mono text-muted-foreground mb-2">
            Panorama competitivo
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <MiniKpi label="Concorrentes" value={String(out.total_concorrentes_analisados ?? 0)} />
            <MiniKpi label="Saturação" value={out.nivel_saturacao ?? '—'} />
            <MiniKpi
              label="Rating médio"
              value={
                out.rating_medio_concorrentes != null
                  ? `★ ${out.rating_medio_concorrentes.toFixed(1)}`
                  : '—'
              }
            />
            <MiniKpi
              label="Modelo recomendado"
              value={out.modelo_recomendado ?? '—'}
            />
          </div>
        </div>
      )}

      {/* CTA */}
      <div className="px-6 pt-2">
        <Button onClick={onVerCompleto} className="w-full">
          Abrir relatório completo <ExternalLink size={14} className="ml-1.5" />
        </Button>
      </div>
    </div>
  )
}

function MiniKpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2">
      <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
        {label}
      </p>
      <p className="mt-0.5 text-sm font-semibold">{value}</p>
    </div>
  )
}
