/**
 * RelatorioCard — linha clicável da listagem.
 *
 * Mostra header (cidade/bairro, tipo, área) + veredito + score top1 +
 * status pipeline + ações.
 */
import { Link } from '@tanstack/react-router'
import { VeredictoBadge } from './VeredictoBadge'
import { StatusPipelineBadge } from './StatusPipelineBadge'
import { DeleteRelatorioButton } from './DeleteRelatorioButton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { RelatorioResumo } from '@/types/domain'

function formatData(iso: string | null): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
    })
  } catch {
    return iso.slice(0, 10)
  }
}

function formatScore(s: number | null): string {
  if (s == null) return '—'
  return s.toFixed(1)
}

const TIPO_NEGOCIO_LABEL: Record<string, string> = {
  academia: 'Academia',
  crossfit_box: 'Box CrossFit',
  studio_pilates: 'Studio Pilates',
  studio_funcional: 'Studio Funcional',
  outro: 'Outro',
}

export interface RelatorioCardProps {
  relatorio: RelatorioResumo
  className?: string
}

export function RelatorioCard({ relatorio, className }: RelatorioCardProps) {
  const score = relatorio.score_top1_candidato
  const scoreColor =
    score == null
      ? 'text-muted-foreground'
      : score >= 8.0
        ? 'text-veredito-aprovado'
        : score >= 6.0
          ? 'text-veredito-ressalvas'
          : score >= 4.0
            ? 'text-veredito-investigar'
            : 'text-veredito-reprovado'

  return (
    <article
      className={cn(
        'group grid grid-cols-12 items-center gap-3 p-4 rounded-lg border border-border bg-card hover:bg-muted/40 transition-colors',
        className,
      )}
    >
      {/* Data */}
      <div className="col-span-2 sm:col-span-1 font-mono text-xs text-muted-foreground">
        {formatData(relatorio.data_execucao)}
      </div>

      {/* Local + tipo */}
      <div className="col-span-10 sm:col-span-4 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <h3 className="font-semibold text-sm truncate">
            {relatorio.bairro}
            <span className="text-muted-foreground font-normal">
              {' · '}
              {relatorio.cidade}
              {relatorio.uf ? ` / ${relatorio.uf}` : ''}
            </span>
          </h3>
        </div>
        <p className="text-xs text-muted-foreground">
          {TIPO_NEGOCIO_LABEL[relatorio.tipo_negocio] ?? relatorio.tipo_negocio}
          {' · '}
          <span className="font-mono">
            {relatorio.area_m2_min}-{relatorio.area_m2_max} m²
          </span>
          {' · '}
          público {relatorio.publico_alvo}
        </p>
      </div>

      {/* Veredito + Status */}
      <div className="col-span-6 sm:col-span-3 flex items-center gap-2 flex-wrap">
        {relatorio.veredito && (
          <VeredictoBadge veredito={relatorio.veredito} size="sm" />
        )}
        {relatorio.status !== 'done' && (
          <StatusPipelineBadge status={relatorio.status} />
        )}
      </div>

      {/* Score Top 1 */}
      <div className="col-span-3 sm:col-span-2 text-right">
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono">
          Top 1
        </div>
        <div className={cn('font-mono font-semibold tabular-nums', scoreColor)}>
          {formatScore(score)}
        </div>
      </div>

      {/* Ação */}
      <div className="col-span-3 sm:col-span-2 flex justify-end items-center gap-1">
        {relatorio.status === 'failed' && (
          <DeleteRelatorioButton
            relatorioId={relatorio.id}
            label={`${relatorio.bairro} · ${relatorio.cidade}`}
          />
        )}
        <Button variant="outline" size="sm" asChild>
          <Link to="/relatorios/$relatorioId" params={{ relatorioId: relatorio.id }}>
            Ver
          </Link>
        </Button>
      </div>
    </article>
  )
}
