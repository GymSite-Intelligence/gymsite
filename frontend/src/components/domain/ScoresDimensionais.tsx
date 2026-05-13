/**
 * ScoresDimensionais — grid das 3 dimensões regionais + 2 cards
 * (Score Bairro / Score Top 1 Candidato).
 *
 * Layout:
 *   ┌──────────────────────────────────┬────────────┬────────────┐
 *   │ Demográfico   ████▓░░ 7.0  BOM   │ Score      │ Score Top 1│
 *   │ Competitivo   ███░░░░ 3.8  CRÍT  │ Bairro     │ Candidato  │
 *   │ Viabilidade   ░░░░░░░ 0.0  CRÍT  │   3.6      │    4.5     │
 *   └──────────────────────────────────┴────────────┴────────────┘
 */
import { ScoreGauge } from './ScoreGauge'
import { cn } from '@/lib/utils'
import type { OutputConsolidado } from '@/hooks/useRelatorioDetail'

export interface ScoresDimensionaisProps {
  scoreBairro: number | null
  scoreTop1: number | null
  scoresRegionais: OutputConsolidado['scores_regionais']
  className?: string
}

export function ScoresDimensionais({
  scoreBairro,
  scoreTop1,
  scoresRegionais,
  className,
}: ScoresDimensionaisProps) {
  const demografico = scoresRegionais?.demografico ?? null
  const competitivo =
    scoresRegionais?.competitivo ?? scoresRegionais?.concorrencia ?? null
  const viabilidade = scoresRegionais?.viabilidade ?? null

  // UI Lote 3: grid 3 colunas com altura uniforme via h-full.
  // Antes: 3 colunas com proporção [1fr_auto_auto] e alturas desiguais.
  // Agora: 3 colunas iguais (md+) com items-stretch, todos com h-full.
  return (
    <section
      className={cn(
        'grid grid-cols-1 md:grid-cols-3 gap-4 items-stretch',
        className,
      )}
      aria-label="Scores regionais"
    >
      {/* Coluna 1 — 3 dimensões em barras */}
      <div className="rounded-lg border border-border bg-card p-5 h-full flex flex-col">
        <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-mono mb-4">
          Dimensões Regionais
        </h3>
        <div className="space-y-4 flex-1 flex flex-col justify-around">
          <ScoreGauge value={demografico} label="Demográfico" />
          <ScoreGauge value={competitivo} label="Competitivo" />
          <ScoreGauge value={viabilidade} label="Viabilidade" />
        </div>
      </div>

      {/* Coluna 2 — Score Bairro (3 dim) */}
      <ScoreGauge
        variant="card"
        value={scoreBairro}
        label="Score Bairro"
        className="h-full flex flex-col justify-between"
      />

      {/* Coluna 3 — Score Top 1 Candidato (4 dim, base do veredito) */}
      <ScoreGauge
        variant="card"
        value={scoreTop1}
        label="Score Top 1 Candidato"
        className="h-full flex flex-col justify-between"
      />
    </section>
  )
}
