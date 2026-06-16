/**
 * PlaybookKanban — etapas do Plano de Abertura em 4 colunas.
 *
 * Desktop: arrastar entre colunas (dnd-kit). Mobile: mudança de situação pelo
 * painel da etapa (TarefaDrawer) — arrastar não é exigido em tela pequena.
 * Linguagem do domínio: "etapas", "A fazer", nunca jargão técnico.
 */
import { DndContext, PointerSensor, useDraggable, useDroppable, useSensor, useSensors } from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import { AlertTriangle, Calendar, ListChecks, Sparkles, User } from 'lucide-react'
import { formatBRL } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { Tarefa } from '@/hooks/usePlaybook'

export const COLUNAS: { status: Tarefa['status']; titulo: string }[] = [
  { status: 'A_FAZER', titulo: 'A fazer' },
  { status: 'EM_ANDAMENTO', titulo: 'Em andamento' },
  { status: 'AGUARDANDO_APROVACAO', titulo: 'Em aprovação' },
  { status: 'BLOQUEADA', titulo: 'Bloqueadas' },
  { status: 'CONCLUIDA', titulo: 'Concluídas' },
]

export const CATEGORIA_LABEL: Record<string, string> = {
  IMOBILIARIO: 'Imóvel',
  LEGAL: 'Documentação',
  OBRAS: 'Obra',
  EQUIPAMENTOS: 'Equipamentos',
  TECNOLOGIA: 'Tecnologia',
  RH: 'Equipe',
  MARKETING: 'Marketing',
  FINANCEIRO: 'Financeiro',
  OPERACIONAL: 'Operação',
  OUTRO: 'Outros',
}

// Accent por categoria via tokens OKLCH (--chart-*) — theme-aware (funciona no
// dark, ao contrário das antigas bg-*-100 só light). Dot + badge color-mix,
// mesmo padrão dos mini-cards do report.
export const CATEGORIA_ACCENT: Record<string, string> = {
  IMOBILIARIO: 'var(--chart-1)',
  LEGAL: 'var(--chart-4)',
  OBRAS: 'var(--chart-3)',
  EQUIPAMENTOS: 'var(--chart-5)',
  TECNOLOGIA: 'var(--chart-2)',
  RH: 'var(--chart-1)',
  MARKETING: 'var(--chart-5)',
  FINANCEIRO: 'var(--chart-4)',
  OPERACIONAL: 'var(--chart-2)',
  OUTRO: 'var(--muted-foreground)',
}

/** Badge de categoria theme-aware (dot + token) — reusado em Kanban/Lista/Timeline/Custos. */
export function CategoriaBadge({
  categoria,
  compact = false,
  className,
}: {
  categoria: string
  /** compact = trunca o rótulo (espaços apertados, ex.: timeline). */
  compact?: boolean
  className?: string
}) {
  const accent = CATEGORIA_ACCENT[categoria] ?? CATEGORIA_ACCENT.OUTRO
  const label = CATEGORIA_LABEL[categoria] ?? categoria
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium',
        className,
      )}
      style={{
        color: accent,
        borderColor: `color-mix(in oklch, ${accent} 30%, transparent)`,
        background: `color-mix(in oklch, ${accent} 12%, transparent)`,
      }}
    >
      <span className="size-1.5 shrink-0 rounded-full" style={{ background: accent }} />
      {compact ? label.slice(0, 5) : label}
    </span>
  )
}

function formatPrazo(iso: string | null): string | null {
  if (!iso) return null
  const d = new Date(`${iso.slice(0, 10)}T12:00:00`)
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
}

function TarefaCardInner({ tarefa }: { tarefa: Tarefa }) {
  const prazo = formatPrazo(tarefa.data_prevista_conclusao)
  const checklistFeitos = tarefa.checklist.filter((c) => c.concluido).length
  const catAccent = CATEGORIA_ACCENT[tarefa.categoria] ?? CATEGORIA_ACCENT.OUTRO
  // Left-accent por urgência (sinal acionável > cor arbitrária de categoria).
  const accent = tarefa.esta_atrasada
    ? 'hsl(var(--veredito-reprovado))'
    : tarefa.status === 'CONCLUIDA'
      ? 'hsl(var(--veredito-aprovado))'
      : tarefa.status === 'AGUARDANDO_APROVACAO'
        ? 'hsl(var(--veredito-ressalvas))'
        : catAccent
  return (
    <div
      className="rounded-lg border border-border bg-card p-3 shadow-sm transition-shadow hover:shadow-md"
      style={{ borderLeft: `3px solid ${accent}` }}
    >
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <CategoriaBadge categoria={tarefa.categoria} />
        {tarefa.sugerida_pela_ia && (
          <span
            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium"
            style={{
              color: 'var(--accent-foreground)',
              background: 'var(--accent)',
            }}
          >
            <Sparkles className="h-3 w-3" /> Sugestão
          </span>
        )}
        {tarefa.esta_atrasada && (
          <span
            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium"
            style={{
              color: 'hsl(var(--veredito-reprovado))',
              background: 'color-mix(in oklch, hsl(var(--veredito-reprovado)) 14%, transparent)',
            }}
          >
            <AlertTriangle className="h-3 w-3" /> {tarefa.dias_atraso}d atrasada
          </span>
        )}
      </div>
      <p className="text-sm font-medium leading-snug">{tarefa.titulo}</p>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        {prazo && (
          <span className="inline-flex items-center gap-1">
            <Calendar className="h-3 w-3" /> {prazo}
          </span>
        )}
        {tarefa.custo_planejado != null && (
          <span>{formatBRL(tarefa.custo_planejado / 100)}</span>
        )}
        {tarefa.responsavel_nome && (
          <span className="inline-flex items-center gap-1 truncate">
            <User className="h-3 w-3" /> {tarefa.responsavel_nome.split('/')[0].trim()}
          </span>
        )}
        {tarefa.checklist.length > 0 && (
          <span className="inline-flex items-center gap-1">
            <ListChecks className="h-3 w-3" /> {checklistFeitos}/{tarefa.checklist.length}
          </span>
        )}
      </div>
    </div>
  )
}

function DraggableTarefa({ tarefa, onAbrir }: { tarefa: Tarefa; onAbrir: (id: string) => void }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: tarefa.id })
  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      onClick={() => onAbrir(tarefa.id)}
      style={transform ? { transform: `translate(${transform.x}px, ${transform.y}px)`, zIndex: 50 } : undefined}
      className={`cursor-pointer touch-manipulation ${isDragging ? 'opacity-80' : ''}`}
    >
      <TarefaCardInner tarefa={tarefa} />
    </div>
  )
}

function Coluna({
  status,
  titulo,
  tarefas,
  onAbrir,
}: {
  status: Tarefa['status']
  titulo: string
  tarefas: Tarefa[]
  onAbrir: (id: string) => void
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status })
  return (
    <div
      ref={setNodeRef}
      className={`flex min-w-[260px] flex-1 flex-col gap-2 rounded-xl border bg-muted/40 p-3 ${
        isOver ? 'ring-2 ring-primary/40' : ''
      }`}
    >
      <div className="flex items-center justify-between px-1">
        <span className="text-sm font-semibold">{titulo}</span>
        <span className="text-xs text-muted-foreground">{tarefas.length}</span>
      </div>
      <div className="flex flex-col gap-2">
        {tarefas.map((t) => (
          <DraggableTarefa key={t.id} tarefa={t} onAbrir={onAbrir} />
        ))}
        {tarefas.length === 0 && (
          <p className="px-1 py-4 text-center text-xs text-muted-foreground">Nenhuma etapa aqui.</p>
        )}
      </div>
    </div>
  )
}

export function PlaybookKanban({
  tarefas,
  onMover,
  onAbrir,
}: {
  tarefas: Tarefa[]
  onMover: (tarefaId: string, novoStatus: Tarefa['status']) => void
  onAbrir: (tarefaId: string) => void
}) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))

  function handleDragEnd(event: DragEndEvent) {
    const tarefaId = String(event.active.id)
    const destino = event.over?.id ? (String(event.over.id) as Tarefa['status']) : null
    if (!destino) return
    const atual = tarefas.find((t) => t.id === tarefaId)
    if (!atual || atual.status === destino) return
    onMover(tarefaId, destino)
  }

  const visiveis = tarefas.filter((t) => t.status !== 'CANCELADA')
  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {COLUNAS.map((c) => (
          <Coluna
            key={c.status}
            status={c.status}
            titulo={c.titulo}
            tarefas={visiveis.filter((t) => t.status === c.status)}
            onAbrir={onAbrir}
          />
        ))}
      </div>
    </DndContext>
  )
}
