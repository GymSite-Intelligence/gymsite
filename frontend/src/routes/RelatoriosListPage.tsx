/**
 * RelatoriosListPage — Tela 2: "Meus Relatórios".
 *
 * Lê filtros tipados da URL via TanStack Router search params.
 * Lista RelatorioCard agrupados, com loading skeleton + empty state.
 */
import { useState } from 'react'
import { Link, useNavigate, useSearch } from '@tanstack/react-router'
import { GitCompare, Plus, RefreshCw, Search, X } from 'lucide-react'
import { useMembership } from '@/hooks/useMembership'
import { useRelatorios } from '@/hooks/useRelatorios'
import { RelatorioCard } from '@/components/domain/RelatorioCard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import type { Veredito } from '@/types/domain'

const VEREDITOS: { value: Veredito | ''; label: string }[] = [
  { value: '', label: 'Todos' },
  { value: 'APROVADO', label: 'Aprovado' },
  { value: 'APROVADO COM RESSALVAS', label: 'Com Ressalvas' },
  { value: 'INVESTIGAR MAIS', label: 'Investigar' },
  { value: 'REPROVADO', label: 'Reprovado' },
]

export function RelatoriosListPage() {
  const navigate = useNavigate()
  const search = useSearch({ from: '/relatorios' })

  const { orgId, loading: membershipLoading } = useMembership()
  const { data, isLoading, isFetching, refetch, error } = useRelatorios({
    cidade: search.cidade || undefined,
    veredito: search.veredito || undefined,
    since: search.since || undefined,
  })

  const hasFiltros = !!(search.cidade || search.veredito || search.since)

  // Seleção pra comparar (modo opcional, ativa quando user clica "Comparar")
  const [modoComparar, setModoComparar] = useState(false)
  const [selecionados, setSelecionados] = useState<string[]>([])
  const podeComparar = selecionados.length === 2

  function toggleSelecao(id: string) {
    setSelecionados((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      if (prev.length >= 2) return [prev[1], id] // FIFO — mantém só 2
      return [...prev, id]
    })
  }

  function irParaComparador() {
    if (!podeComparar) return
    navigate({
      to: '/comparar',
      search: { a: selecionados[0], b: selecionados[1] },
    })
  }

  function updateSearch(patch: Partial<typeof search>) {
    navigate({
      to: '/relatorios',
      search: (prev) => ({ ...prev, ...patch }),
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Meus Relatórios</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {data ? `${data.length} relatório${data.length === 1 ? '' : 's'}` : '...'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={modoComparar ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              setModoComparar((v) => !v)
              setSelecionados([])
            }}
          >
            <GitCompare size={14} />
            {modoComparar ? 'Cancelar comparação' : 'Comparar 2 relatórios'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={isFetching ? 'animate-spin' : ''} size={14} />
          </Button>
          <Button asChild>
            <Link to="/relatorios/new">
              <Plus size={16} /> Novo Relatório
            </Link>
          </Button>
        </div>
      </div>

      {/* Filtros */}
      <div className="flex items-center gap-2 flex-wrap p-3 rounded-lg border border-border bg-card">
        <div className="relative flex-1 min-w-[200px]">
          <Search
            size={14}
            className="absolute left-2.5 top-2.5 text-muted-foreground pointer-events-none"
          />
          <Input
            placeholder="Filtrar por cidade ou bairro..."
            className="pl-8"
            value={search.cidade ?? ''}
            onChange={(e) => updateSearch({ cidade: e.target.value || undefined })}
          />
        </div>

        <select
          value={search.veredito ?? ''}
          onChange={(e) =>
            updateSearch({
              veredito: (e.target.value as Veredito) || undefined,
            })
          }
          className="h-9 rounded-md border border-border bg-transparent px-3 text-sm"
        >
          {VEREDITOS.map((v) => (
            <option key={v.value} value={v.value} className="bg-background">
              {v.label}
            </option>
          ))}
        </select>

        {hasFiltros && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              navigate({ to: '/relatorios', search: {} })
            }
          >
            <X size={14} /> Limpar
          </Button>
        )}
      </div>

      {/* Lista / loading / empty */}
      {isLoading || membershipLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          Erro ao carregar relatórios: {error.message}
        </div>
      ) : !orgId ? (
        <EmptyState hasFiltros={false} semOrg />
      ) : !data || data.length === 0 ? (
        <EmptyState hasFiltros={hasFiltros} />
      ) : (
        <div className="space-y-2">
          {data.map((r) => {
            const selecionado = selecionados.includes(r.id)
            return (
              <div
                key={r.id}
                className={cn(
                  'flex items-start gap-3 rounded-lg transition-colors',
                  modoComparar && 'cursor-pointer p-1 -m-1',
                  modoComparar &&
                    selecionado &&
                    'bg-primary/5 ring-2 ring-primary/40',
                )}
                onClick={modoComparar ? () => toggleSelecao(r.id) : undefined}
              >
                {modoComparar && (
                  <div className="pt-4 pl-2">
                    <input
                      type="checkbox"
                      checked={selecionado}
                      onChange={() => toggleSelecao(r.id)}
                      className="h-4 w-4 accent-primary"
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <RelatorioCard relatorio={r} />
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Barra flutuante quando 2 selecionados */}
      {modoComparar && (
        <div
          className={cn(
            'fixed bottom-6 left-1/2 -translate-x-1/2 z-40 transition-all',
            selecionados.length === 0
              ? 'pointer-events-none opacity-0 translate-y-2'
              : 'opacity-100',
          )}
        >
          <div className="flex items-center gap-3 rounded-lg border border-border bg-card shadow-lg px-4 py-2.5">
            <span className="text-xs font-mono text-muted-foreground">
              {selecionados.length}/2 selecionados
            </span>
            <Button
              size="sm"
              disabled={!podeComparar}
              onClick={irParaComparador}
            >
              <GitCompare size={14} /> Comparar
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function EmptyState({
  hasFiltros,
  semOrg = false,
}: {
  hasFiltros: boolean
  semOrg?: boolean
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 border-2 border-dashed border-border rounded-lg text-center">
      <span aria-hidden className="text-4xl mb-3">📊</span>
      {semOrg ? (
        <>
          <h3 className="font-semibold mb-1">Sem acesso à organização</h3>
          <p className="text-sm text-muted-foreground max-w-md">
            Sua conta ainda não está vinculada a uma organização. Peça ao
            administrador para convidar você — depois disso os relatórios
            aparecem aqui.
          </p>
        </>
      ) : hasFiltros ? (
        <>
          <h3 className="font-semibold mb-1">Nenhum relatório bate com os filtros</h3>
          <p className="text-sm text-muted-foreground">
            Ajuste os filtros acima ou limpe pra ver todos.
          </p>
        </>
      ) : (
        <>
          <h3 className="font-semibold mb-1">Nenhum relatório ainda</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Crie seu primeiro relatório de viabilidade comercial.
          </p>
          <Button asChild>
            <Link to="/relatorios/new">
              <Plus size={16} /> Novo Relatório
            </Link>
          </Button>
        </>
      )}
    </div>
  )
}
