/**
 * ProjetoExecucaoPage — Plano de Abertura (/execucao/$playbookId).
 *
 * P-006: filtro de categoria e etapa aberta vivem nos query params —
 * F5 mantém exatamente onde o usuário estava.
 */
import { useMemo, useState } from 'react'
import { useNavigate, useParams, useSearch } from '@tanstack/react-router'
import { AlertTriangle, CalendarDays, Gauge, Plus, Users, Wallet } from 'lucide-react'
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
  useExcluirTarefa,
  useMarcarChecklist,
  type Tarefa,
} from '@/hooks/usePlaybook'
import { EtapaFormDialog } from '@/components/execucao/EtapaFormDialog'
import { PlaybookKanban, CATEGORIA_LABEL, COLUNAS } from '@/components/execucao/PlaybookKanban'
import { PlaybookLista } from '@/components/execucao/PlaybookLista'
import { PlaybookTimeline } from '@/components/execucao/PlaybookTimeline'
import { PlaybookCustos } from '@/components/execucao/PlaybookCustos'
import { TarefaModal } from '@/components/execucao/TarefaModal'
import { PessoasDialog } from '@/components/execucao/PessoasDialog'
import { ObjetivosCard } from '@/components/execucao/ObjetivosCard'
import { useIsMobile } from '@/hooks/use-mobile'

const VIEWS = [
  { id: 'kanban', rotulo: 'Etapas' },
  { id: 'lista', rotulo: 'Lista' },
  { id: 'timeline', rotulo: 'Linha do tempo' },
  { id: 'custos', rotulo: 'Custos' },
] as const
type ViewId = (typeof VIEWS)[number]['id']

export function ProjetoExecucaoPage() {
  const { playbookId } = useParams({ strict: false }) as { playbookId: string }
  const search = useSearch({ strict: false }) as {
    categoria?: string
    etapa?: string
    view?: string
    situacao?: string
  }
  const navigate = useNavigate()
  const isMobile = useIsMobile()

  const { data: playbook, isLoading, error } = usePlaybook(playbookId)
  const atualizar = useAtualizarTarefa(playbookId)
  const marcarChecklist = useMarcarChecklist(playbookId)
  const excluirTarefa = useExcluirTarefa(playbookId)
  const [pessoasAberto, setPessoasAberto] = useState(false)
  const [etapaFormAberto, setEtapaFormAberto] = useState(false)
  const [etapaEditando, setEtapaEditando] = useState<Tarefa | null>(null)

  const categoriaFiltro = search.categoria ?? 'todas'
  const situacaoFiltro = search.situacao ?? 'todas'
  const tarefaAbertaId = search.etapa ?? null
  const viewPadrao: ViewId = isMobile ? 'lista' : 'kanban'
  const view: ViewId = (VIEWS.some((v) => v.id === search.view) ? search.view : viewPadrao) as ViewId

  const tarefasFiltradas = useMemo(() => {
    let todas = playbook?.tarefas ?? []
    if (categoriaFiltro !== 'todas') todas = todas.filter((t) => t.categoria === categoriaFiltro)
    if (situacaoFiltro !== 'todas') todas = todas.filter((t) => t.status === situacaoFiltro)
    return todas
  }, [playbook, categoriaFiltro, situacaoFiltro])

  const tarefaAberta = useMemo(
    () => (playbook?.tarefas ?? []).find((t) => t.id === tarefaAbertaId) ?? null,
    [playbook, tarefaAbertaId],
  )

  function setSearch(next: {
    categoria?: string
    etapa?: string | null
    view?: string
    situacao?: string
  }) {
    const categoria = next.categoria !== undefined ? next.categoria : categoriaFiltro
    const etapa = next.etapa !== undefined ? next.etapa : tarefaAbertaId
    const v = next.view !== undefined ? next.view : search.view
    const situacao = next.situacao !== undefined ? next.situacao : situacaoFiltro
    navigate({
      to: '.',
      search: {
        categoria: categoria && categoria !== 'todas' ? categoria : undefined,
        etapa: etapa || undefined,
        view: v && v !== viewPadrao ? v : undefined,
        situacao: situacao && situacao !== 'todas' ? situacao : undefined,
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
        <h1 className="text-xl font-semibold">{playbook.nome}</h1>

        {/* KPI strip Geo-Intel — progresso, prazo, orçamento, atrasadas */}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {/* Progresso */}
          <div
            className="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-xs"
            style={{ borderLeft: '3px solid var(--chart-1)' }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Progresso
              </span>
              <Gauge size={15} style={{ color: 'var(--chart-1)' }} />
            </div>
            <span className="text-2xl font-semibold leading-none tabular-nums">
              {playbook.percentual_concluido}%
            </span>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${playbook.percentual_concluido}%`, background: 'var(--chart-1)' }}
              />
            </div>
            <span className="text-xs text-muted-foreground">
              {playbook.tarefas_concluidas}/{playbook.total_tarefas} etapas
            </span>
          </div>

          {/* Previsão de abertura */}
          <div
            className="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-xs"
            style={{ borderLeft: '3px solid var(--chart-2)' }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Previsão de abertura
              </span>
              <CalendarDays size={15} style={{ color: 'var(--chart-2)' }} />
            </div>
            <span className="text-2xl font-semibold leading-none tabular-nums">
              {conclusao ?? '—'}
            </span>
            <span className="text-xs text-muted-foreground">data prevista de conclusão</span>
          </div>

          {/* Orçamento */}
          <div
            className="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-xs"
            style={{
              borderLeft: `3px solid ${
                gasto > previsto && previsto > 0
                  ? 'hsl(var(--veredito-reprovado))'
                  : 'hsl(var(--veredito-aprovado))'
              }`,
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Orçamento
              </span>
              <Wallet size={15} className="text-muted-foreground" />
            </div>
            <span className="text-2xl font-semibold leading-none tabular-nums">
              {formatBRL(gasto / 100)}
            </span>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${previsto > 0 ? Math.min(100, (gasto / previsto) * 100) : 0}%`,
                  background:
                    gasto > previsto && previsto > 0
                      ? 'hsl(var(--veredito-reprovado))'
                      : 'hsl(var(--veredito-aprovado))',
                }}
              />
            </div>
            <span className="text-xs text-muted-foreground">
              de {formatBRL(previsto / 100)} previstos
            </span>
          </div>

          {/* Etapas atrasadas */}
          <div
            className="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-xs"
            style={{
              borderLeft: `3px solid ${
                playbook.tarefas_atrasadas > 0
                  ? 'hsl(var(--veredito-reprovado))'
                  : 'var(--muted-foreground)'
              }`,
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Etapas atrasadas
              </span>
              <AlertTriangle
                size={15}
                style={{
                  color:
                    playbook.tarefas_atrasadas > 0
                      ? 'hsl(var(--veredito-reprovado))'
                      : 'var(--muted-foreground)',
                }}
              />
            </div>
            <span
              className="text-2xl font-semibold leading-none tabular-nums"
              style={
                playbook.tarefas_atrasadas > 0
                  ? { color: 'hsl(var(--veredito-reprovado))' }
                  : undefined
              }
            >
              {playbook.tarefas_atrasadas}
            </span>
            <span className="text-xs text-muted-foreground">
              {playbook.tarefas_atrasadas > 0 ? 'precisam de atenção' : 'tudo no prazo'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Select
            value={categoriaFiltro}
            onValueChange={(v) => setSearch({ categoria: v })}
          >
            <SelectTrigger className="h-10 w-44">
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
          <Select value={situacaoFiltro} onValueChange={(v) => setSearch({ situacao: v })}>
            <SelectTrigger className="h-10 w-44">
              <SelectValue placeholder="Todas as situações" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todas">Todas as situações</SelectItem>
              {COLUNAS.map((c) => (
                <SelectItem key={c.status} value={c.status}>
                  {c.titulo}
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
          <Button
            className="h-10"
            onClick={() => {
              setEtapaEditando(null)
              setEtapaFormAberto(true)
            }}
          >
            <Plus className="mr-1.5 h-4 w-4" /> Nova etapa
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
      {view === 'custos' && <PlaybookCustos tarefas={tarefasFiltradas} />}

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
        onEditar={() => {
          setEtapaEditando(tarefaAberta)
          setEtapaFormAberto(true)
        }}
        onExcluir={() => {
          if (!tarefaAberta) return
          if (!window.confirm(`Excluir a etapa "${tarefaAberta.titulo}" do plano?`)) return
          excluirTarefa.mutate(tarefaAberta.id, {
            onSuccess: () => {
              notify.success('Etapa excluída do plano.')
              setSearch({ etapa: null })
            },
            onError: (e: Error) => notify.error(e.message),
          })
        }}
      />

      <EtapaFormDialog
        aberto={etapaFormAberto}
        onFechar={() => setEtapaFormAberto(false)}
        playbookId={playbookId}
        tarefa={etapaEditando}
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
