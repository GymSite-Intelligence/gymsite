/**
 * MarketAtlasPage — visão estratégica: ondas vermelho → transição → azul + A9.
 */
import { useMemo } from 'react'
import { Link } from '@tanstack/react-router'
import { OceanoBadge } from '@/components/domain/OceanoBadge'
import { VeredictoBadge } from '@/components/domain/VeredictoBadge'
import { OceanoDistributionChart } from '@/components/dashboard/OceanoDistributionChart'
import { DashboardOceanoCards } from '@/components/dashboard/DashboardOceanoCards'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useDashboardStats } from '@/hooks/useDashboardStats'
import { useRelatorios } from '@/hooks/useRelatorios'
import {
  MARKET_WAVES_CATALOG,
  WAVE_LABELS,
} from '@/lib/market-waves-catalog'
import { normalizeVereditoOceano } from '@/lib/oceano'
import type { MarketWave, RelatorioResumo } from '@/types/domain'

const WAVE_BADGE: Record<MarketWave, string> = {
  red: 'bg-red-600 text-white',
  transition: 'bg-amber-500 text-black',
  blue: 'bg-blue-600 text-white',
}

function matchScenario(
  r: RelatorioResumo,
  cidade: string,
  bairro: string,
): boolean {
  const c = r.cidade.toLowerCase()
  const b = r.bairro.toLowerCase()
  return (
    c.includes(cidade.toLowerCase()) &&
    (b.includes(bairro.toLowerCase()) || bairro.toLowerCase().includes(b))
  )
}

export function MarketAtlasPage() {
  const { stats, isLoading, isError, error } = useDashboardStats()
  const { data: relatorios } = useRelatorios()

  const waveProgress = useMemo(() => {
    const done = (relatorios ?? []).filter((r) => r.status === 'done')
    return MARKET_WAVES_CATALOG.map((scenario) => {
      const match =
        done.find(
          (r) =>
            r.market_wave === scenario.wave &&
            matchScenario(r, scenario.cidade, scenario.bairro),
        ) ??
        done.find((r) => matchScenario(r, scenario.cidade, scenario.bairro))
      return { scenario, relatorio: match ?? null }
    })
  }, [relatorios])

  const byWave = useMemo(() => {
    const groups: Record<MarketWave, typeof waveProgress> = {
      red: [],
      transition: [],
      blue: [],
    }
    for (const item of waveProgress) {
      groups[item.scenario.wave].push(item)
    }
    return groups
  }, [waveProgress])

  return (
    <div className="@container/main flex flex-1 flex-col gap-6 pb-8">
      <div className="px-4 lg:px-6 space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Market Atlas</h1>
        <p className="text-sm text-muted-foreground max-w-2xl">
          Catálogo de ondas para mapear mercados saturados, transição (capital → RM) e
          oceano azul. Cada cenário referencia um golden case quando disponível.
        </p>
      </div>

      {isError && (
        <Alert variant="destructive" className="mx-4 lg:mx-6">
          <AlertDescription>
            {error instanceof Error ? error.message : 'Erro ao carregar dados'}
          </AlertDescription>
        </Alert>
      )}

      <DashboardOceanoCards stats={stats} loading={isLoading} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 px-4 lg:px-6">
        <OceanoDistributionChart
          data={stats?.oceanoDistribution ?? []}
          loading={isLoading}
        />
        <Card>
          <CardHeader>
            <CardTitle>Ondas planejadas</CardTitle>
            <CardDescription>
              {MARKET_WAVES_CATALOG.length} cenários em{' '}
              <code className="text-xs">data/market_waves.csv</code>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {(['red', 'transition', 'blue'] as MarketWave[]).map((wave) => (
              <div key={wave} className="flex justify-between items-center">
                <Badge className={WAVE_BADGE[wave]}>{WAVE_LABELS[wave]}</Badge>
                <span className="text-muted-foreground tabular-nums">
                  {byWave[wave].length} cenários ·{' '}
                  {byWave[wave].filter((w) => w.relatorio).length} com relatório
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="px-4 lg:px-6 space-y-4">
        <h2 className="text-lg font-semibold">Catálogo de ondas</h2>
        <div className="rounded-xl border overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Onda</TableHead>
                <TableHead>Local</TableHead>
                <TableHead>Hipótese</TableHead>
                <TableHead>Golden</TableHead>
                <TableHead>Relatório</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {waveProgress.map(({ scenario, relatorio }) => (
                <TableRow key={scenario.id}>
                  <TableCell>
                    <Badge className={WAVE_BADGE[scenario.wave]}>
                      {WAVE_LABELS[scenario.wave]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="font-medium">{scenario.bairro}</span>
                    <span className="text-muted-foreground">
                      {' '}
                      · {scenario.cidade}/{scenario.uf}
                    </span>
                  </TableCell>
                  <TableCell className="max-w-xs text-muted-foreground text-sm">
                    {scenario.hypothesis}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {scenario.golden_anchor ?? '—'}
                  </TableCell>
                  <TableCell>
                    {relatorio ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          to="/relatorios/$relatorioId"
                          params={{ relatorioId: relatorio.id }}
                          className="text-sm font-medium text-primary hover:underline"
                        >
                          Abrir
                        </Link>
                        {relatorio.veredito && (
                          <VeredictoBadge veredito={relatorio.veredito} />
                        )}
                        <OceanoBadge
                          veredito={normalizeVereditoOceano(
                            relatorio.veredito_posicionamento,
                          )}
                        />
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-sm">Planejado</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  )
}
