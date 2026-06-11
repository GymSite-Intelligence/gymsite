/**
 * PlaybookKanban — etapas do Plano de Abertura em 4 colunas.
 *
 * Desktop: arrastar entre colunas (dnd-kit). Mobile: mudança de situação pelo
 * painel da etapa (TarefaDrawer) — arrastar não é exigido em tela pequena.
 * Linguagem do domínio: "etapas", "A fazer", nunca jargão técnico.
 */
import { DndContext, PointerSensor, useDraggable, useDroppable, useSensor, useSensors } from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import { AlertTriangle, Calendar, Sparkles, User } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { formatBRL } from '@/lib/format'
import type { Tarefa } from '@/hooks/usePlaybook'

export const COLUNAS: { status: Tarefa['status']; titulo: string }[] = [
  { status: 'A_FAZER', titulo: 'A fazer' },
  { status: 'EM_ANDAMENTO', titulo: 'Em andamento' },
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

const CATEGORIA_COR: Record<string, string> = {
  IMOBILIARIO: 'bg-blue-100 text-blue-800 border-blue-200',
  LEGAL: 'bg-red-100 text-red-800 border-red-200',
  OBRAS: 'bg-orange-100 text-orange-800 border-orange-200',
  EQUIPAMENTOS: 'bg-purple-100 text-purple-800 border-purple-200',
  TECNOLOGIA: 'bg-cyan-100 text-cyan-800 border-cyan-200',
  RH: 'bg-green-100 text-green-800 border-green-200',
  MARKETING: 'bg-pink-100 text-pink-800 border-pink-200',
  FINANCEIRO: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  OPERACIONAL: 'bg-gray-100 text-gray-800 border-gray-200',
  OUTRO: 'bg-gray-100 text-gray-700 border-gray-200',
}

function formatPrazo(iso: string | null): string | null {
  if (!iso) return null
  const d = new Date(`${iso.slice(0, 10)}T12:00:00`)
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
}

function TarefaCardInner({ tarefa }: { tarefa: Tarefa }) {
  const prazo = formatPrazo(tarefa.data_prevista_conclusao)
  const checklistFeitos = tarefa.checklist.filter((c) => c.concluido).length
  return (
    <div className="rounded-lg border bg-card p-3 shadow-sm transition-shadow hover:shadow-md">
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <Badge variant="outline" className={`text-[10px] ${CATEGORIA_COR[tarefa.categoria] ?? CATEGORIA_COR.OUTRO}`}>
          {CATEGORIA_LABEL[tarefa.categoria] ?? tarefa.categoria}
        </Badge>
        {tarefa.sugerida_pela_ia && (
          <Badge variant="outline" className="gap-1 border-violet-200 bg-violet-50 text-[10px] text-violet-700">
            <Sparkles className="h-3 w-3" /> Sugestão
          </Badge>
        )}
        {tarefa.esta_atrasada && (
          <Badge variant="outline" className="gap-1 border-red-200 bg-red-50 text-[10px] text-red-700">
            <AlertTriangle className="h-3 w-3" /> {tarefa.dias_atraso}d atrasada
          </Badge>
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
          <span>
            ☑ {checklistFeitos}/{tarefa.checklist.length}
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
