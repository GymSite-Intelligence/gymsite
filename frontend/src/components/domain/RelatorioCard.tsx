/**
 * RelatorioCard — linha clicável da listagem.
 *
 * Mostra header (cidade/bairro, tipo, área) + veredito + score top1 +
 * status pipeline + ações.
 */
import { Link, useNavigate } from '@tanstack/react-router'
import { useState, type MouseEvent } from 'react'
import { Download, Pencil } from 'lucide-react'
import { VeredictoBadge } from './VeredictoBadge'
import { StatusPipelineBadge } from './StatusPipelineBadge'
import { DeleteRelatorioButton } from './DeleteRelatorioButton'
import { RerunPipelineButton } from './RerunPipelineButton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { fetchRelatorioInputsForRerun } from '@/lib/submit-pipeline'
import { notify } from '@/lib/notify'
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
  const navigate = useNavigate()
  const [editando, setEditando] = useState(false)
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
        // Desktop: usa grid-cols-12 "safe" + min-width na coluna de ações
        // pra manter os botões alinhados entre cards.
        'group grid grid-cols-1 gap-3 p-4 rounded-lg border border-border bg-card hover:bg-muted/40 transition-colors sm:grid-cols-12 sm:items-center',
        className,
      )}
    >
      {/* Data */}
      <div className="font-mono text-xs text-muted-foreground sm:col-span-1 sm:min-w-[72px]">
        {formatData(relatorio.data_execucao)}
      </div>

      {/* Local + tipo */}
      <div className="min-w-0 sm:col-span-4">
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
      <div className="flex items-center gap-2 flex-wrap sm:col-span-3">
        {relatorio.veredito && (
          <VeredictoBadge veredito={relatorio.veredito} size="sm" />
        )}
        {relatorio.status !== 'done' && (
          <StatusPipelineBadge status={relatorio.status} />
        )}
      </div>

      {/* Score Top 1 */}
      <div className="text-left sm:col-span-1 sm:text-right">
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono">
          Top 1
        </div>
        <div className={cn('font-mono font-semibold tabular-nums', scoreColor)}>
          {formatScore(score)}
        </div>
      </div>

      {/* Ação */}
      <div className="flex flex-wrap justify-start items-center gap-1 sm:col-span-3 sm:min-w-[380px] sm:flex-nowrap sm:justify-end sm:gap-2">
        {relatorio.status === 'failed' && (
          <DeleteRelatorioButton
            relatorioId={relatorio.id}
            label={`${relatorio.bairro} · ${relatorio.cidade}`}
          />
        )}
        {(relatorio.status === 'done' || relatorio.status === 'failed') && (
          <RerunPipelineButton
            relatorioId={relatorio.id}
            status={relatorio.status}
            label="Gerar novamente"
            stopPropagation
          />
        )}
        {relatorio.status === 'done' && (
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 shrink-0"
            asChild
            title="Baixar PDF (abre impressão)"
          >
            <Link
              to="/relatorios/$relatorioId"
              params={{ relatorioId: relatorio.id }}
              search={{ print: '1' }}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e: MouseEvent) => e.stopPropagation()}
            >
              <Download size={14} />
              PDF
            </Link>
          </Button>
        )}
        {(relatorio.status === 'done' || relatorio.status === 'failed') && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-1.5 shrink-0"
            disabled={editando}
            onClick={async (e: MouseEvent) => {
              e.stopPropagation()
              if (editando) return
              setEditando(true)
              const t = notify.loading('Carregando parâmetros do relatório…')
              try {
                const inputs = await fetchRelatorioInputsForRerun(relatorio.id)
                t.success('Parâmetros carregados')
                navigate({
                  to: '/relatorios/new',
                  search: {
                    cidade: inputs.cidade,
                    uf: inputs.uf ?? undefined,
                    bairro: inputs.bairro,
                    area_m2_min: inputs.area_m2_min,
                    area_m2_max: inputs.area_m2_max,
                    tamanho_preset: inputs.tamanho_preset ?? undefined,
                    publico_alvo: inputs.publico_alvo ?? undefined,
                    genero_alvo: inputs.genero_alvo ?? undefined,
                    tipo_negocio: inputs.tipo_negocio ?? undefined,
                    estacionamento_obrigatorio:
                      inputs.estacionamento_obrigatorio ?? undefined,
                    edit_relatorio_id: relatorio.id,
                  },
                })
              } catch (err) {
                t.error(err)
              } finally {
                setEditando(false)
              }
            }}
            title="Editar parâmetros e gerar uma nova versão"
          >
            <Pencil size={14} />
            Editar
          </Button>
        )}
        <Button variant="outline" size="sm" asChild className="shrink-0">
          <Link to="/relatorios/$relatorioId" params={{ relatorioId: relatorio.id }}>
            Ver
          </Link>
        </Button>
      </div>
    </article>
  )
}
