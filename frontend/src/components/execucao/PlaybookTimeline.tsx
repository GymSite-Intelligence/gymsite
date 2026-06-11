/**
 * PlaybookTimeline — linha do tempo das etapas (gantt simplificado).
 *
 * Barras por etapa entre data_inicio e data_prevista_conclusao, na ordem do
 * plano (que já é topológica — dependências ficam visíveis pelo encadeamento
 * das datas). Linha vertical marca hoje. Sem edição por arrasto (decisão da
 * spec F2); clicar na barra abre a ficha da etapa.
 */
import { useMemo } from 'react'
import { Badge } from '@/components/ui/badge'
import type { Tarefa } from '@/hooks/usePlaybook'
import { CATEGORIA_COR, CATEGORIA_LABEL } from '@/components/execucao/PlaybookKanban'

const DIA_MS = 24 * 60 * 60 * 1000

function dataLocal(iso: string): Date {
  return new Date(`${iso.slice(0, 10)}T12:00:00`)
}

const BARRA_COR: Record<string, string> = {
  IMOBILIARIO: 'bg-blue-400',
  LEGAL: 'bg-red-400',
  OBRAS: 'bg-orange-400',
  EQUIPAMENTOS: 'bg-purple-400',
  TECNOLOGIA: 'bg-cyan-400',
  RH: 'bg-green-400',
  MARKETING: 'bg-pink-400',
  FINANCEIRO: 'bg-yellow-400',
  OPERACIONAL: 'bg-gray-400',
  OUTRO: 'bg-gray-400',
}

export function PlaybookTimeline({
  tarefas,
  onAbrir,
}: {
  tarefas: Tarefa[]
  onAbrir: (tarefaId: string) => void
}) {
  const comDatas = useMemo(
    () =>
      tarefas
        .filter((t) => t.data_inicio && t.data_prevista_conclusao && t.status !== 'CANCELADA')
        .sort((a, b) => a.ordem - b.ordem),
    [tarefas],
  )

  const { inicio, totalDias, meses, hojePct } = useMemo(() => {
    if (comDatas.length === 0) {
      return { inicio: new Date(), totalDias: 1, meses: [] as { rotulo: string; pct: number }[], hojePct: null as number | null }
    }
    const min = new Date(Math.min(...comDatas.map((t) => dataLocal(t.data_inicio!).getTime())))
    const max = new Date(Math.max(...comDatas.map((t) => dataLocal(t.data_prevista_conclusao!).getTime())))
    const dias = Math.max(1, Math.round((max.getTime() - min.getTime()) / DIA_MS) + 7)

    const marcas: { rotulo: string; pct: number }[] = []
    const m = new Date(min.getFullYear(), min.getMonth(), 1, 12)
    while (m <= max) {
      const pct = ((m.getTime() - min.getTime()) / DIA_MS / dias) * 100
      if (pct >= 0) {
        marcas.push({
          rotulo: m.toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' }),
          pct,
        })
      }
      m.setMonth(m.getMonth() + 1)
    }

    const hoje = new Date()
    const pctHoje = ((hoje.getTime() - min.getTime()) / DIA_MS / dias) * 100
    return {
      inicio: min,
      totalDias: dias,
      meses: marcas,
      hojePct: pctHoje >= 0 && pctHoje <= 100 ? pctHoje : null,
    }
  }, [comDatas])

  if (comDatas.length === 0) {
    return <p className="py-10 text-center text-sm text-muted-foreground">Nenhuma etapa com datas para mostrar.</p>
  }

  return (
    <div className="overflow-x-auto pb-6">
      <div className="min-w-[640px]">
        <div className="relative mb-1 ml-[220px] h-5 border-b text-[10px] text-muted-foreground">
          {meses.map((m) => (
            <span key={m.rotulo + m.pct} className="absolute top-0" style={{ left: `${m.pct}%` }}>
              {m.rotulo}
            </span>
          ))}
        </div>

        <div className="relative">
          {hojePct != null && (
            <div
              className="pointer-events-none absolute top-0 bottom-0 z-10 w-px bg-red-500"
              style={{ left: `calc(220px + (100% - 220px) * ${hojePct / 100})` }}
              aria-label="Hoje"
            />
          )}

          <div className="flex flex-col gap-1">
            {comDatas.map((t) => {
              const ini = dataLocal(t.data_inicio!)
              const fim = dataLocal(t.data_prevista_conclusao!)
              const offPct = ((ini.getTime() - inicio.getTime()) / DIA_MS / totalDias) * 100
              const durPct = Math.max(
                1,
                ((fim.getTime() - ini.getTime()) / DIA_MS / totalDias) * 100,
              )
              const concluida = t.status === 'CONCLUIDA'
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => onAbrir(t.id)}
                  className="group flex items-center gap-2 rounded px-1 py-0.5 text-left transition-colors hover:bg-accent/50"
                >
                  <span className="flex w-[212px] shrink-0 items-center gap-1.5">
                    <Badge
                      variant="outline"
                      className={`px-1 text-[9px] ${CATEGORIA_COR[t.categoria] ?? CATEGORIA_COR.OUTRO}`}
                    >
                      {(CATEGORIA_LABEL[t.categoria] ?? t.categoria).slice(0, 5)}
                    </Badge>
                    <span
                      className={`truncate text-xs ${concluida ? 'text-muted-foreground line-through' : ''}`}
                      title={t.titulo}
                    >
                      {t.titulo}
                    </span>
                  </span>
                  <span className="relative h-4 flex-1">
                    <span
                      className={`absolute top-0.5 h-3 rounded-full ${
                        BARRA_COR[t.categoria] ?? BARRA_COR.OUTRO
                      } ${concluida ? 'opacity-40' : ''} ${
                        t.esta_atrasada ? 'ring-2 ring-red-400' : ''
                      } transition-opacity group-hover:opacity-90`}
                      style={{ left: `${offPct}%`, width: `${durPct}%` }}
                      title={`${ini.toLocaleDateString('pt-BR')} → ${fim.toLocaleDateString('pt-BR')}`}
                    />
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
