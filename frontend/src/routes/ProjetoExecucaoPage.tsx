/**
 * ProjetoExecucaoPage — Plano de Abertura (/execucao/$playbookId).
 *
 * P-006: filtro de categoria e etapa aberta vivem nos query params —
 * F5 mantém exatamente onde o usuário estava.
 */
import { useMemo, useState } from 'react'
import { useNavigate, useParams, useSearch } from '@tanstack/react-router'
import { CalendarDays, Users, Wallet } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { notify } from '@/lib/notify'
import { formatBRL } from '@/lib/format'
import {
  usePlaybook,
  useAtualizarTarefa,
  useMarcarChecklist,
  type Tarefa,
} from '@/hooks/usePlaybook'
import { PlaybookKanban, CATEGORIA_LABEL } from '@/components/execucao/PlaybookKanban'
import { PlaybookLista } from '@/components/execucao/PlaybookLista'
import { PlaybookTimeline } from '@/components/execucao/PlaybookTimeline'
import { TarefaModal } from '@/components/execucao/TarefaModal'
import { PessoasDialog } from '@/components/execucao/PessoasDialog'
import { ObjetivosCard } from '@/components/execucao/ObjetivosCard'
import { useIsMobile } from '@/hooks/use-mobile'

const VIEWS = [
  { id: 'kanban', rotulo: 'Etapas' },
  { id: 'lista', rotulo: 'Lista' },
  { id: 'timeline', rotulo: 'Linha do tempo' },
] as const
type ViewId = (typeof VIEWS)[number]['id']

export function ProjetoExecucaoPage() {
  const { playbookId } = useParams({ strict: false }) as { playbookId: string }
  const search = useSearch({ strict: false }) as { categoria?: string; etapa?: string; view?: string }
  const navigate = useNavigate()
  const isMobile = useIsMobile()

  const { data: playbook, isLoading, error } = usePlaybook(playbookId)
  const atualizar = useAtualizarTarefa(playbookId)
  const marcarChecklist = useMarcarChecklist(playbookId)
  const [pessoasAberto, setPessoasAberto] = useState(false)

  const categoriaFiltro = search.categoria ?? 'todas'
  const tarefaAbertaId = search.etapa ?? null
  const viewPadrao: ViewId = isMobile ? 'lista' : 'kanban'
  const view: ViewId = (VIEWS.some((v) => v.id === search.view) ? search.view : viewPadrao) as ViewId

  const tarefasFiltradas = useMemo(() => {
    const todas = playbook?.tarefas ?? []
    if (categoriaFiltro === 'todas') return todas
    return todas.filter((t) => t.categoria === categoriaFiltro)
  }, [playbook, categoriaFiltro])

  const tarefaAberta = useMemo(
    () => (playbook?.tarefas ?? []).find((t) => t.id === tarefaAbertaId) ?? null,
    [playbook, tarefaAbertaId],
  )

  function setSearch(next: { categoria?: string; etapa?: string | null; view?: string }) {
    const categoria = next.categoria !== undefined ? next.categoria : categoriaFiltro
    const etapa = next.etapa !== undefined ? next.etapa : tarefaAbertaId
    const v = next.view !== undefined ? next.view : search.view
    navigate({
      to: '.',
      search: {
        categoria: categoria && categoria !== 'todas' ? categoria : undefined,
        etapa: etapa || undefined,
        view: v && v !== viewPadrao ? v : undefined,
      },
      replace: true,
    })
  }

  function moverTarefa(tarefaId: string, novoStatus: Tarefa['status'], custoReal: number | null = null) {
    atualizar.mutate(
      { tarefaId, status: novoStatus, custoReal },
      {
        onSuccess: (r) => {
          if (novoStatus === 'CONCLUIDA') {
            const liberadas = r.tarefas_liberadas?.length ?? 0
            notify.success(
              liberadas > 0
                ? `Etapa concluída! ${liberadas} etapa(s) liberada(s) para começar.`
                : 'Etapa concluída!',
            )
          }
          setSearch({ etapa: null })
        },
        onError: (e: Error) => notify.error(e.message),
      },
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-4 p-4 md:p-6">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (error || !playbook) {
    return (
      <div className="p-6">
        <p className="text-sm text-muted-foreground">
          {error instanceof Error ? error.message : 'Plano não encontrado.'}
        </p>
      </div>
    )
  }

  const previsto = playbook.custo_planejado_total ?? 0
  const gasto = playbook.custo_real_total ?? 0
  const conclusao = playbook.data_prevista_conclusao
    ? new Date(`${playbook.data_prevista_conclusao.slice(0, 10)}T12:00:00`).toLocaleDateString('pt-BR')
    : null
  const categorias = Array.from(new Set((playbook.tarefas ?? []).map((t) => t.categoria)))

  return (
    <div className="flex h-full flex-col gap-4 p-4 md:p-6">
      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-semibold">{playbook.nome}</h1>
          {playbook.tarefas_atrasadas > 0 && (
            <Badge variant="outline" className="border-red-200 bg-red-50 text-red-700">
              {playbook.tarefas_atrasadas} etapa(s) atrasada(s)
            </Badge>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="h-2 w-36 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${playbook.percentual_concluido}%` }}
              />
            </div>
            <span className="font-medium text-foreground">
              {playbook.percentual_concluido}% concluído
            </span>
            <span>
              ({playbook.tarefas_concluidas}/{playbook.total_tarefas} etapas)
            </span>
          </div>
          {conclusao && (
            <span className="inline-flex items-center gap-1">
              <CalendarDays className="h-4 w-4" /> Previsão de abertura: {conclusao}
            </span>
          )}
          <span className="inline-flex items-center gap-1">
            <Wallet className="h-4 w-4" />
            Gasto {formatBRL(gasto / 100)} de {formatBRL(previsto / 100)} previstos
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Select
            value={categoriaFiltro}
            onValueChange={(v) => setSearch({ categoria: v })}
          >
            <SelectTrigger className="h-10 w-52">
              <SelectValue placeholder="Todas as áreas" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todas">Todas as áreas</SelectItem>
              {categorias.map((c) => (
                <SelectItem key={c} value={c}>
                  {CATEGORIA_LABEL[c] ?? c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" className="h-10" onClick={() => setPessoasAberto(true)}>
            <Users className="mr-1.5 h-4 w-4" />
            Pessoas
            {(playbook.pessoas ?? []).length > 0 && (
              <span className="ml-1.5 text-muted-foreground">{playbook.pessoas.length}</span>
            )}
          </Button>
          <div className="ml-auto flex rounded-lg border p-0.5">
            {VIEWS.map((v) => (
              <button
                key={v.id}
                type="button"
                onClick={() => setSearch({ view: v.id })}
                className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                  view === v.id
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {v.rotulo}
              </button>
            ))}
          </div>
        </div>
      </header>

      <ObjetivosCard playbookId={playbookId} okrs={playbook.okrs ?? []} />

      {view === 'kanban' && (
        <PlaybookKanban
          tarefas={tarefasFiltradas}
          onMover={(id, status) => moverTarefa(id, status)}
          onAbrir={(id) => setSearch({ etapa: id })}
        />
      )}
      {view === 'lista' && (
        <PlaybookLista tarefas={tarefasFiltradas} onAbrir={(id) => setSearch({ etapa: id })} />
      )}
      {view === 'timeline' && (
        <PlaybookTimeline tarefas={tarefasFiltradas} onAbrir={(id) => setSearch({ etapa: id })} />
      )}

      <TarefaModal
        tarefa={tarefaAberta}
        aberto={Boolean(tarefaAberta)}
        onFechar={() => setSearch({ etapa: null })}
        onMudarStatus={(status, custo) => tarefaAberta && moverTarefa(tarefaAberta.id, status, custo)}
        onMarcarChecklist={(itemId, concluido) =>
          marcarChecklist.mutate(
            { itemId, concluido },
            { onError: (e: Error) => notify.error(e.message) },
          )
        }
        salvando={atualizar.isPending}
        playbookId={playbookId}
        pessoas={playbook.pessoas ?? []}
      />

      <PessoasDialog
        aberto={pessoasAberto}
        onFechar={() => setPessoasAberto(false)}
        pessoas={playbook.pessoas ?? []}
        playbookId={playbookId}
        projetoId={playbook.projeto_id}
      />
    </div>
  )
}
