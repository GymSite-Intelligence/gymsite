/**
 * PlanosListPage — /execucao: todos os planos de abertura do usuário.
 *
 * Entrada de primeira classe do módulo de execução no sidebar. O plano em si
 * nasce do relatório (botão "Gerar plano de abertura"); aqui é o retorno do
 * dia a dia: progresso, gasto e atrasos de cada abertura em andamento.
 */
import { Link } from '@tanstack/react-router'
import { CalendarDays, ClipboardList, Wallet } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { formatBRL } from '@/lib/format'
import { usePlaybooks } from '@/hooks/usePlaybook'

function formatData(iso: string | null): string | null {
  if (!iso) return null
  return new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString('pt-BR')
}

export function PlanosListPage() {
  const { data: planos, isLoading, error } = usePlaybooks()

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <p className="text-sm text-muted-foreground">
        {error instanceof Error ? error.message : 'Não foi possível carregar seus planos.'}
      </p>
    )
  }

  if (!planos || planos.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <ClipboardList className="h-10 w-10 text-muted-foreground" />
        <div>
          <p className="font-medium">Você ainda não tem um plano de abertura.</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Abra um relatório concluído e clique em “Gerar plano de abertura”.
          </p>
        </div>
        <Button asChild variant="outline" className="mt-2 h-10">
          <Link to="/relatorios">Ver meus relatórios</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div>
        <h1 className="text-xl font-semibold">Planos de abertura</h1>
        <p className="text-sm text-muted-foreground">
          {planos.length} plano(s) — acompanhe etapas, gasto e previsão de inauguração.
        </p>
      </div>

      {planos.map((p) => {
        const pct = Math.round(p.percentual_concluido ?? 0)
        const previsto = p.custo_planejado_total ?? 0
        const gasto = p.custo_real_total ?? 0
        const conclusao = formatData(p.data_prevista_conclusao)
        return (
          <Link
            key={p.id}
            to="/execucao/$playbookId"
            params={{ playbookId: p.id }}
            className="rounded-lg border bg-card px-4 py-3 transition-colors hover:border-primary/40 hover:bg-accent/40"
          >
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-medium">{p.projeto_nome || p.nome}</p>
              {p.status !== 'ATIVO' && (
                <Badge variant="secondary" className="rounded-full px-2.5 font-normal">
                  {p.status === 'ARQUIVADO' ? 'Arquivado' : p.status}
                </Badge>
              )}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
              <span className="flex items-center gap-2">
                <span className="h-2 w-28 overflow-hidden rounded-full bg-muted">
                  <span
                    className="block h-full rounded-full bg-primary transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </span>
                <span className="font-medium text-foreground">{pct}%</span>
                <span>
                  ({p.tarefas_concluidas}/{p.total_tarefas} etapas)
                </span>
              </span>
              {conclusao && (
                <span className="inline-flex items-center gap-1">
                  <CalendarDays className="h-4 w-4" /> Abertura: {conclusao}
                </span>
              )}
              <span className="inline-flex items-center gap-1">
                <Wallet className="h-4 w-4" />
                {formatBRL(gasto / 100)} de {formatBRL(previsto / 100)}
              </span>
            </div>
          </Link>
        )
      })}
    </div>
  )
}
