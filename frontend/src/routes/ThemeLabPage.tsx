/**
 * ThemeLabPage — vitrine de redesign (/theme-lab).
 *
 * Visualização local das 3 direções candidatas de UI. Cada direção é um
 * conjunto de tokens OKLCH em `html[data-theme='dir-a|dir-b|dir-c']`
 * (ver src/index.css). O switcher troca `data-theme` ao vivo.
 *
 * Rota pública (sem auth) — só para decisão visual. Não é parte do produto.
 * Depois de escolher 1 direção, promover os tokens dela ao :root/.dark base
 * e remover esta página + os blocos dir-* das outras.
 */
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

type Dir = 'geo' | 'atual'

const DIRECTIONS: { id: Dir; name: string; blurb: string }[] = [
  {
    id: 'geo',
    name: 'Geo-Intel',
    blurb:
      'Geomarketing-nativo (ref. Cortex Geofusion): base ink-navy, gráficos como heatmap de intensidade, score territorial, números em mono.',
  },
  { id: 'atual', name: 'Atual', blurb: 'Look atual (cinza shadcn default) — para comparar o antes/depois.' },
]

const HEAT = [
  { label: 'Baixo', v: 'var(--chart-1)' },
  { label: '', v: 'var(--chart-2)' },
  { label: 'Médio', v: 'var(--chart-3)' },
  { label: '', v: 'var(--chart-4)' },
  { label: 'Alto', v: 'var(--chart-5)' },
]

const KPIS = [
  { label: 'Academias mapeadas', value: '1.284', delta: '+12%' },
  { label: 'Relatórios gerados', value: '347', delta: '+8%' },
  { label: 'Custo médio / relatório', value: 'R$ 4,45', delta: '-15%' },
  { label: 'Taxa de aprovação', value: '63%', delta: '+5%' },
]

const ROWS = [
  { cidade: 'Curitiba', bairro: 'Batel', score: 87, veredito: 'Aprovado' as const },
  { cidade: 'Joinville', bairro: 'Centro', score: 64, veredito: 'Ressalvas' as const },
  { cidade: 'Florianópolis', bairro: 'Trindade', score: 41, veredito: 'Investigar' as const },
  { cidade: 'Blumenau', bairro: 'Velha', score: 23, veredito: 'Reprovado' as const },
]

const VEREDITO_VAR: Record<string, string> = {
  Aprovado: 'var(--color-veredito-aprovado)',
  Ressalvas: 'var(--color-veredito-ressalvas)',
  Investigar: 'var(--color-veredito-investigar)',
  Reprovado: 'var(--color-veredito-reprovado)',
}

const CHART = [62, 78, 45, 90, 71, 84, 58]

export function ThemeLabPage() {
  const [dir, setDir] = useState<Dir>('geo')

  // Tema escopado neste wrapper (data-theme + dark). NÃO mexe no <html> —
  // imune ao theme-provider (next-themes) do app, que sobrescreveria o html.
  // 'atual' = sem data-theme → cai no .dark base (cinza shadcn default).
  return (
    <div
      data-theme={dir === 'atual' ? undefined : dir}
      className="dark min-h-screen bg-background text-foreground"
    >
      {/* Top bar / switcher */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">GymSite · Theme Lab</h1>
            <p className="text-sm text-muted-foreground">
              Compare 3 direções de UI ao vivo. Escolha uma para promover ao base.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {DIRECTIONS.map((d) => (
              <Button
                key={d.id}
                size="sm"
                variant={dir === d.id ? 'default' : 'outline'}
                onClick={() => setDir(d.id)}
              >
                {d.name}
              </Button>
            ))}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">
            {DIRECTIONS.find((d) => d.id === dir)?.name}
          </span>{' '}
          — {DIRECTIONS.find((d) => d.id === dir)?.blurb}
        </p>

        {/* KPIs */}
        <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {KPIS.map((k) => (
            <Card key={k.label}>
              <CardHeader className="pb-2">
                <CardDescription>{k.label}</CardDescription>
                <CardTitle className="text-2xl">{k.value}</CardTitle>
              </CardHeader>
              <CardContent>
                <span className="text-xs font-medium text-primary">{k.delta}</span>{' '}
                <span className="text-xs text-muted-foreground">vs. mês anterior</span>
              </CardContent>
            </Card>
          ))}
        </section>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Chart */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Densidade de potencial por praça</CardTitle>
              <CardDescription>
                Barras = intensidade (rampa heatmap --chart-1..5: frio→quente = baixo→alto)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex h-44 items-end gap-3">
                {CHART.map((v, i) => (
                  <div key={i} className="flex flex-1 flex-col items-center gap-2">
                    <div
                      className="w-full rounded-md transition-all"
                      style={{
                        height: `${v}%`,
                        // mapeia altura → bin de intensidade (heatmap)
                        background: `var(--chart-${Math.min(5, Math.max(1, Math.ceil(v / 20)))})`,
                      }}
                    />
                    <span className="text-[10px] font-mono text-muted-foreground">S{i + 1}</span>
                  </div>
                ))}
              </div>
              {/* Legenda heatmap — assinatura geomarketing */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground">Intensidade</span>
                <div className="flex flex-1 overflow-hidden rounded-full">
                  {HEAT.map((h, i) => (
                    <div key={i} className="h-2 flex-1" style={{ background: h.v }} />
                  ))}
                </div>
                <div className="flex gap-3 text-[10px] text-muted-foreground">
                  <span>Baixo</span>
                  <span>Alto</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Form / controls */}
          <Card>
            <CardHeader>
              <CardTitle>Novo relatório</CardTitle>
              <CardDescription>Inputs, botões e badges</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input placeholder="Cidade (ex: Curitiba)" />
              <Input placeholder="Bairro (ex: Batel)" />
              <div className="flex flex-wrap gap-2 pt-1">
                <Badge>Pré-abertura</Badge>
                <Badge variant="secondary">Premium</Badge>
                <Badge variant="outline">Raio 3km</Badge>
                <Badge variant="destructive">Saturado</Badge>
              </div>
              <Separator />
              <div className="flex gap-2">
                <Button className="flex-1">Gerar</Button>
                <Button variant="outline">Cancelar</Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Table com veredito */}
        <Card>
          <CardHeader>
            <CardTitle>Viabilidade por praça</CardTitle>
            <CardDescription>Tabela + badges de status semântico</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Cidade</TableHead>
                  <TableHead>Bairro</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead>Veredito</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ROWS.map((r) => (
                  <TableRow key={`${r.cidade}-${r.bairro}`}>
                    <TableCell className="font-medium">{r.cidade}</TableCell>
                    <TableCell className="text-muted-foreground">{r.bairro}</TableCell>
                    <TableCell className="text-right font-mono">{r.score}</TableCell>
                    <TableCell>
                      <span
                        className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
                        style={{
                          color: VEREDITO_VAR[r.veredito],
                          background: `color-mix(in oklch, ${VEREDITO_VAR[r.veredito]} 14%, transparent)`,
                        }}
                      >
                        <span
                          className="size-1.5 rounded-full"
                          style={{ background: VEREDITO_VAR[r.veredito] }}
                        />
                        {r.veredito}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <p className="pb-8 text-center text-xs text-muted-foreground">
          Tokens em <code className="font-mono">src/index.css</code> ·{' '}
          <code className="font-mono">html[data-theme='{dir}']</code>
        </p>
      </main>
    </div>
  )
}
