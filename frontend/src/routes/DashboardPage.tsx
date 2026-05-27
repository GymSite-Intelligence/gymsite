/**
 * DashboardPage — KPIs e série temporal (dados reais: v_relatorios_resumo / Supabase).
 */
import { DashboardRelatoriosChart } from '@/components/dashboard/DashboardRelatoriosChart'
import { DashboardRelatoriosTable } from '@/components/dashboard/DashboardRelatoriosTable'
import { DashboardSectionCards } from '@/components/dashboard/DashboardSectionCards'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useDashboardStats } from '@/hooks/useDashboardStats'

export function DashboardPage() {
  const { stats, data, isLoading, isError, error } = useDashboardStats()

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
      <DashboardSectionCards stats={stats} loading={isLoading} />
      <DashboardRelatoriosChart data={stats?.chartData ?? []} loading={isLoading} />
      <DashboardRelatoriosTable rows={data ?? []} loading={isLoading} />
    </div>
  )
}
