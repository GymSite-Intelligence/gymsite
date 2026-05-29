/**
 * DashboardFilters — filtros para o dashboard (cidade, veredito, status, período).
 */
import { Search, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import type { DashboardFilters } from '@/hooks/useDashboardStats'
import type { Veredito, RelatorioStatus } from '@/types/domain'

const VEREDITOS: { value: Veredito | ''; label: string }[] = [
  { value: '', label: 'Todos' },
  { value: 'APROVADO', label: 'Aprovado' },
  { value: 'APROVADO COM RESSALVAS', label: 'Com Ressalvas' },
  { value: 'INVESTIGAR MAIS', label: 'Investigar' },
  { value: 'REPROVADO', label: 'Reprovado' },
]

const STATUS: { value: RelatorioStatus | ''; label: string }[] = [
  { value: '', label: 'Todos' },
  { value: 'done', label: 'Concluído' },
  { value: 'running', label: 'Em execução' },
  { value: 'queued', label: 'Na fila' },
  { value: 'failed', label: 'Falhou' },
]

const PERIODOS: { value: string; label: string }[] = [
  { value: '', label: 'Todo período' },
  { value: '7', label: 'Últimos 7 dias' },
  { value: '30', label: 'Últimos 30 dias' },
  { value: '90', label: 'Últimos 90 dias' },
]

export interface DashboardFiltersProps {
  filters: DashboardFilters
  onChange: (filters: DashboardFilters) => void
}

export function DashboardFiltersPanel({ filters, onChange }: DashboardFiltersProps) {
  const hasFilters = filters.cidade || filters.veredito || filters.status || filters.since

  function setFilter<K extends keyof DashboardFilters>(key: K, value: DashboardFilters[K]) {
    onChange({ ...filters, [key]: value || undefined })
  }

  function clearFilters() {
    onChange({})
  }

  return (
    <div className="flex flex-wrap items-center gap-2 p-3 rounded-lg border border-border bg-card">
      <div className="relative flex-1 min-w-[180px]">
        <Search size={14} className="absolute left-2.5 top-2.5 text-muted-foreground pointer-events-none" />
        <Input
          placeholder="Filtrar por cidade ou bairro..."
          className="pl-8 h-9"
          value={filters.cidade ?? ''}
          onChange={(e) => setFilter('cidade', e.target.value)}
        />
      </div>

      <select
        value={filters.veredito ?? ''}
        onChange={(e) => setFilter('veredito', (e.target.value as Veredito) || undefined)}
        className="h-9 rounded-md border border-border bg-transparent px-3 text-sm"
      >
        {VEREDITOS.map((v) => (
          <option key={v.value} value={v.value}>
            {v.label}
          </option>
        ))}
      </select>

      <select
        value={filters.status ?? ''}
        onChange={(e) => setFilter('status', (e.target.value as RelatorioStatus) || undefined)}
        className="h-9 rounded-md border border-border bg-transparent px-3 text-sm"
      >
        {STATUS.map((v) => (
          <option key={v.value} value={v.value}>
            {v.label}
          </option>
        ))}
      </select>

      <select
        value={filters.since ? String(Math.round((Date.now() - new Date(filters.since).getTime()) / 86400000)) : ''}
        onChange={(e) => {
          const days = e.target.value
          if (!days) {
            setFilter('since', undefined)
            return
          }
          const d = new Date()
          d.setDate(d.getDate() - Number(days))
          setFilter('since', d.toISOString().slice(0, 10))
        }}
        className="h-9 rounded-md border border-border bg-transparent px-3 text-sm"
      >
        {PERIODOS.map((v) => (
          <option key={v.value} value={v.value}>
            {v.label}
          </option>
        ))}
      </select>

      {hasFilters && (
        <Button variant="ghost" size="sm" onClick={clearFilters} className="h-9 px-2">
          <X size={14} className="mr-1" /> Limpar
        </Button>
      )}
    </div>
  )
}
