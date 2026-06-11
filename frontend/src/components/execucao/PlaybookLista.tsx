/**
 * PlaybookLista — etapas agrupadas por situação, em linhas compactas.
 *
 * View default no mobile (P-002): kanban de 4 colunas exige scroll
 * horizontal; lista agrupada não. Mesmo onAbrir do kanban — tudo
 * converge na ficha da etapa.
 */
import { AlertTriangle, Calendar, Sparkles, User } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { formatBRL } from '@/lib/format'
import type { Tarefa } from '@/hooks/usePlaybook'
import { CATEGORIA_COR, CATEGORIA_LABEL, COLUNAS } from '@/components/execucao/PlaybookKanban'

function formatPrazo(iso: string | null): string | null {
  if (!iso) return null
  return new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'short',
  })
}

export function PlaybookLista({
  tarefas,
  onAbrir,
}: {
  tarefas: Tarefa[]
  onAbrir: (tarefaId: string) => void
}) {
  return (
    <div className="flex flex-col gap-5 pb-6">
      {COLUNAS.map((col) => {
        const grupo = tarefas.filter((t) => t.status === col.status)
        if (grupo.length === 0) return null
        return (
          <section key={col.status}>
            <h2 className="mb-2 flex items-baseline gap-2 text-sm font-semibold">
              {col.titulo}
              <span className="text-xs font-normal text-muted-foreground">{grupo.length}</span>
            </h2>
            <div className="flex flex-col gap-1.5">
              {grupo.map((t) => {
                const prazo = formatPrazo(t.data_prevista_conclusao)
                const feitos = t.checklist.filter((c) => c.concluido).length
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => onAbrir(t.id)}
                    className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border bg-card px-3 py-2 text-left transition-colors hover:border-primary/40 hover:bg-accent/40"
                  >
                    <Badge
                      variant="outline"
                      className={`text-[10px] ${CATEGORIA_COR[t.categoria] ?? CATEGORIA_COR.OUTRO}`}
                    >
                      {CATEGORIA_LABEL[t.categoria] ?? t.categoria}
                    </Badge>
                    <span
                      className={`min-w-0 flex-1 truncate text-sm font-medium ${
                        t.status === 'CONCLUIDA' ? 'text-muted-foreground line-through' : ''
                      }`}
                    >
                      {t.titulo}
                    </span>
                    {t.sugerida_pela_ia && <Sparkles className="h-3.5 w-3.5 shrink-0 text-violet-500" />}
                    {t.esta_atrasada && (
                      <span className="inline-flex shrink-0 items-center gap-1 text-xs text-red-600">
                        <AlertTriangle className="h-3.5 w-3.5" /> {t.dias_atraso}d
                      </span>
                    )}
                    <span className="hidden shrink-0 items-center gap-3 text-xs text-muted-foreground sm:inline-flex">
                      {prazo && (
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="h-3.5 w-3.5" /> {prazo}
                        </span>
                      )}
                      {t.custo_planejado != null && <span>{formatBRL(t.custo_planejado / 100)}</span>}
                      {t.responsavel_nome && (
                        <span className="inline-flex max-w-32 items-center gap-1 truncate">
                          <User className="h-3.5 w-3.5" /> {t.responsavel_nome}
                        </span>
                      )}
                      {t.checklist.length > 0 && (
                        <span>
                          ☑ {feitos}/{t.checklist.length}
                        </span>
                      )}
                    </span>
                  </button>
                )
              })}
            </div>
          </section>
        )
      })}
    </div>
  )
}
