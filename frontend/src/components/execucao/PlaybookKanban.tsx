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

/** Dot de categoria — cor só no indicador; badge sólido. */
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

/** Badge de categoria (dot + secondary sólido) — Kanban/Lista/Timeline/Custos. */
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
        'inline-flex items-center gap-1.5 rounded-md border border-border bg-secondary px-2 py-0.5 text-[10px] font-medium text-muted-foreground',
        className,
      )}
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
  // Barra 2px só para status acionável (atraso / concluída / aprovação).
  const statusBar = tarefa.esta_atrasada
    ? 'bg-destructive'
    : tarefa.status === 'CONCLUIDA'
      ? 'bg-primary'
      : tarefa.status === 'AGUARDANDO_APROVACAO'
        ? 'bg-[hsl(var(--veredito-ressalvas))]'
        : null
  return (
    <div className="relative overflow-hidden rounded-lg border border-border bg-card p-3">
      {statusBar && <span className={`absolute inset-y-0 left-0 w-0.5 ${statusBar}`} aria-hidden />}
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <CategoriaBadge categoria={tarefa.categoria} />
        {tarefa.sugerida_pela_ia && (
          <span className="inline-flex items-center gap-1 rounded-md border border-border bg-secondary px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
            <Sparkles className="h-3 w-3" /> Sugestão
          </span>
        )}
        {tarefa.esta_atrasada && (
          <span className="inline-flex items-center gap-1 rounded-md border border-border bg-secondary px-2 py-0.5 text-[10px] font-medium text-destructive">
            <AlertTriangle className="h-3 w-3" /> {tarefa.dias_atraso}d atrasada
          </span>
        )}
      </div>
      <p className="text-sm font-medium leading-snug">{tarefa.titulo}</p>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs text-muted-foreground">
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
      className={`flex min-w-[260px] flex-1 flex-col gap-2 rounded-xl border border-border bg-secondary p-3 ${
        isOver ? 'outline outline-2 outline-primary' : ''
      }`}
    >
      <div className="flex items-center justify-between px-1">
        <span className="text-sm font-semibold">{titulo}</span>
        <span className="font-mono text-xs text-muted-foreground">{tarefas.length}</span>
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
