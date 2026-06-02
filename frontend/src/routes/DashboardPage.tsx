/**
 * DashboardPage — KPIs, série temporal, insights, ranking e relatórios recentes.
 *
 * Interações:
 * - Filtros por cidade, veredito, status e período
 * - Click numa linha da tabela abre drawer lateral (RelatorioQuickView)
 * - Modo comparar na tabela permite selecionar 2 relatórios e ir pra /comparar
 * - Insights automáticos baseados nos dados filtrados
 */
import { useState, useCallback } from 'react'
import { DashboardRelatoriosChart } from '@/components/dashboard/DashboardRelatoriosChart'
import { DashboardRelatoriosTable } from '@/components/dashboard/DashboardRelatoriosTable'
import { DashboardSectionCards } from '@/components/dashboard/DashboardSectionCards'
import { RelatorioQuickView } from '@/components/dashboard/RelatorioQuickView'
import { DashboardFiltersPanel } from '@/components/dashboard/DashboardFilters'
import { VereditoDistributionChart } from '@/components/dashboard/VereditoDistributionChart'
import { DashboardInsights } from '@/components/dashboard/DashboardInsights'
import { BairrosRanking } from '@/components/dashboard/BairrosRanking'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useDashboardStats } from '@/hooks/useDashboardStats'
import type { DashboardFilters } from '@/hooks/useDashboardStats'
import { getDashboardDataSourceLabel } from '@/lib/dashboard/data-source'

export function DashboardPage() {
  const [filters, setFilters] = useState<DashboardFilters>({})
  const [relatorioAtivoId, setRelatorioAtivoId] = useState<string | null>(null)

  const { stats, data, isLoading, isError, error } = useDashboardStats(filters)

  const abrirDrawer = useCallback((id: string) => {
    setRelatorioAtivoId(id)
  }, [])

  const fecharDrawer = useCallback(() => {
    setRelatorioAtivoId(null)
  }, [])

  return (
    <div className="@container/main flex flex-1 flex-col gap-4 md:gap-6">
      {isError && (
        <Alert variant="destructive">
          <AlertDescription>
            Falha ao carregar relatórios:{' '}
            {error instanceof Error ? error.message : 'erro desconhecido'}
          </AlertDescription>
        </Alert>
      )}

      {/* Filtros */}
      <div className="px-4 lg:px-6">
        <DashboardFiltersPanel filters={filters} onChange={setFilters} />
      </div>

      {/* Insights automáticos */}
      <div className="px-4 lg:px-6">
        <DashboardInsights insights={stats?.insights ?? []} loading={isLoading} />
      </div>

      {/* KPIs cards */}
      <DashboardSectionCards stats={stats} loading={isLoading} />

      {/* Gráficos: atividade + distribuição de vereditos */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-4 px-4 lg:px-6">
        <DashboardRelatoriosChart data={stats?.chartData ?? []} loading={isLoading} />
        <VereditoDistributionChart
          data={stats?.vereditoDistribution ?? []}
          loading={isLoading}
        />
      </div>

      {/* Ranking de bairros + Tabela de relatórios */}
      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4 px-4 lg:px-6 items-start">
        <BairrosRanking
          data={stats?.bairrosRanking ?? []}
          loading={isLoading}
          dataSourceLabel={getDashboardDataSourceLabel()}
          relatorioCount={stats?.total}
        />
        <DashboardRelatoriosTable
          rows={data ?? []}
          loading={isLoading}
          onClickRow={abrirDrawer}
        />
      </div>

      <RelatorioQuickView relatorioId={relatorioAtivoId} onClose={fecharDrawer} />
    </div>
  )
}
