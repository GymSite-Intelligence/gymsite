/**
 * Anéis competitivos (Apêndice D) — score PONDERADO por proximidade.
 * Corrige a densidade inflada pela força do vizinho (NO_BAIRRO 1.0 / FRONTEIRA 0.5 / REGIONAL 0.2).
 */
import { Target } from 'lucide-react'
import type { AneisCompetitivosJSON } from '@/hooks/useRelatorioDetail'

const ANEIS: { key: 'NO_BAIRRO' | 'FRONTEIRA' | 'REGIONAL'; label: string; peso: string; cls: string }[] = [
  { key: 'NO_BAIRRO', label: 'No bairro', peso: '×1.0', cls: 'bg-veredito-reprovado/15 text-veredito-reprovado' },
  { key: 'FRONTEIRA', label: 'Fronteira (≤2km)', peso: '×0.5', cls: 'bg-veredito-ressalvas/15 text-veredito-ressalvas' },
  { key: 'REGIONAL', label: 'Regional', peso: '×0.2', cls: 'bg-muted text-muted-foreground' },
]

export function AneisCompetitivosCard({ block }: { block: AneisCompetitivosJSON }) {
  if (!block || block.total_concorrentes === undefined) {
    return <p className="text-sm text-muted-foreground">Sem dados de anéis competitivos.</p>
  }
  const porAnel = block.por_anel ?? {}
  const portes = block.no_bairro_por_porte ?? {}

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 rounded-lg border bg-card px-4 py-2">
          <Target className="size-5 text-chart-1" />
          <div>
            <div className="text-lg font-bold">{block.score_competitivo_ponderado ?? '—'}</div>
            <div className="text-[11px] text-muted-foreground">score competitivo ponderado</div>
          </div>
        </div>
        <div className="text-sm text-muted-foreground">
          {block.total_concorrentes} concorrentes no raio · <span className="font-medium text-foreground">{block.concorrentes_no_bairro ?? 0}</span> no bairro
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {ANEIS.map((a) => (
          <div key={a.key} className={`rounded-lg px-3 py-2 ${a.cls}`}>
            <div className="text-xl font-bold">{porAnel[a.key] ?? 0}</div>
            <div className="text-[11px]">{a.label} <span className="opacity-70">{a.peso}</span></div>
          </div>
        ))}
      </div>

      {(porAnel.NO_BAIRRO ?? 0) > 0 && (
        <div className="text-sm text-muted-foreground">
          No bairro por porte: <span className="text-foreground">grande {portes.grande ?? 0}</span> ·
          média {portes.media ?? 0} · pequena {portes.pequena ?? 0}
        </div>
      )}

      <p className="text-[11px] text-muted-foreground">{block.nota}</p>
    </div>
  )
}
