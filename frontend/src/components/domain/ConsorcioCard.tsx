/**
 * ConsorcioCard — alternativa estratégica para preservar caixa.
 * UI only (GYM-23): sem probabilidade de sorteio no client.
 */
import * as React from 'react'
import { Landmark, MessageCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { SHOW_WHATSAPP_UI } from '@/lib/feature-flags'
import {
  CONSORCIO_TAXA_ADMIN_PCT,
  CONSORCIO_TAXA_FUNDO_RESERVA_PCT,
  estimarConsorcio,
  estimarParcelaConsorcio,
  estimarPosLance,
  getLanceBenchmarkPack,
  VECTRA_CONTATO_URL,
  type ConsorcioEstimativa,
} from '@/lib/consorcio-config'

function formatBRL(v: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  }).format(v)
}

export interface ConsorcioCardProps {
  capexMid: number | null
  /** Horizonte do investidor (copy) — default 18. */
  horizonteMeses?: 12 | 18 | 24
  className?: string
}

function ConsorcioCardEmpty({ className }: { className?: string }) {
  return (
    <article
      className={cn(
        'rounded-lg border border-primary/30 bg-primary/5 p-5 space-y-4',
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <div className="rounded-md bg-primary/15 p-2 shrink-0">
          <Landmark size={18} className="text-primary" aria-hidden />
        </div>
        <div className="space-y-1 min-w-0">
          <h3 className="font-semibold text-foreground">
            Consórcio (alternativa estratégica)
          </h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Mesmo em investimentos menores, o consórcio pode ser uma alternativa para{' '}
            <span className="font-medium text-foreground">preservar caixa</span> e planejar a execução em{' '}
            <span className="font-medium text-foreground">12–24 meses</span>.
          </p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Para preencher a estimativa, este relatório precisa trazer os cenários financeiros (CAPEX do cenário mid).
          </p>
        </div>
      </div>

      {SHOW_WHATSAPP_UI && (
        <Button asChild className="gap-2 w-full sm:w-auto">
          <a href={VECTRA_CONTATO_URL} target="_blank" rel="noopener noreferrer">
            <MessageCircle size={14} aria-hidden />
            Falar com Vectra Cargo
          </a>
        </Button>
      )}
    </article>
  )
}

export function ConsorcioCard({
  capexMid,
  horizonteMeses = 18,
  className,
}: ConsorcioCardProps) {
  if (capexMid == null) {
    return <ConsorcioCardEmpty className={className} />
  }

  return (
    <ConsorcioCardWithCapex
      capexMid={capexMid}
      horizonteMeses={horizonteMeses}
      className={className}
    />
  )
}

function ConsorcioCardWithCapex({
  capexMid,
  horizonteMeses,
  className,
}: {
  capexMid: number
  horizonteMeses: 12 | 18 | 24
  className?: string
}) {
  const est: ConsorcioEstimativa = estimarConsorcio(capexMid)

  const [considerarLance, setConsiderarLance] = React.useState(true)
  const [prazoLance, setPrazoLance] = React.useState<number>(est.prazoMeses)
  const pack = React.useMemo(
    () => getLanceBenchmarkPack({ valorCarta: est.valorCarta, prazoMeses: prazoLance }),
    [est.valorCarta, prazoLance],
  )
  const [preset, setPreset] = React.useState<'baixo' | 'médio' | 'alto'>(pack.defaultPreset)

  React.useEffect(() => {
    setPreset(pack.defaultPreset)
  }, [pack.defaultPreset])

  const lancePct =
    preset === 'baixo' ? pack.low.pct : preset === 'alto' ? pack.high.pct : pack.avg.pct

  const parcelaBasePrazo = React.useMemo(() => {
    return estimarParcelaConsorcio({
      valorCarta: est.valorCarta,
      prazoMeses: pack.prazoMeses,
      taxaAdminPct: CONSORCIO_TAXA_ADMIN_PCT,
      taxaFundoReservaPct: CONSORCIO_TAXA_FUNDO_RESERVA_PCT,
    })
  }, [est.valorCarta, pack.prazoMeses])

  const posLance = React.useMemo(() => {
    return estimarPosLance({
      valorCarta: est.valorCarta,
      prazoMeses: pack.prazoMeses,
      lancePct,
      taxaAdminPct: CONSORCIO_TAXA_ADMIN_PCT,
      taxaFundoReservaPct: CONSORCIO_TAXA_FUNDO_RESERVA_PCT,
    })
  }, [est.valorCarta, pack.prazoMeses, lancePct])

  return (
    <article
      className={cn(
        'rounded-lg border border-primary/30 bg-primary/5 p-5 space-y-4',
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <div className="rounded-md bg-primary/15 p-2 shrink-0">
          <Landmark size={18} className="text-primary" aria-hidden />
        </div>
        <div className="space-y-1 min-w-0">
          <h3 className="font-semibold text-foreground">
            Consórcio (alternativa estratégica)
          </h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            O consórcio pode diluir o investimento inicial com custo abaixo de financiamento tradicional,
            preservando caixa no horizonte de{' '}
            <span className="font-medium text-foreground">{horizonteMeses} meses</span> — com planejamento típico de{' '}
            <span className="font-medium text-foreground">12–24 meses</span>.
          </p>
        </div>
      </div>

      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <Metric label="Carta sugerida" value={formatBRL(est.valorCarta)} highlight />
        <Metric
          label={`Parcela (${est.prazoMeses}×)`}
          value={formatBRL(est.parcelaConsorcio)}
        />
        <Metric label="Prazo" value={`${est.prazoMeses} meses`} />
        <Metric
          label="Economia vs. banco"
          value={formatBRL(est.economiaTotal)}
          hint={`~${est.economiaPct.toFixed(0)}% vs. ${formatBRL(est.parcelaFinanciamentoRef)}/mês ref.`}
          highlight
        />
      </dl>

      <section className="rounded-lg border border-border/60 bg-card p-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1 min-w-0">
            <h4 className="text-sm font-semibold text-foreground">Estratégia de lance (estimativa)</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Benchmarks de “média de lance por cota” são <span className="font-medium">assunções configuráveis</span>{' '}
              (variando por administradora/grupo). Use para entender viabilidade e ordem de grandeza do aporte.
            </p>
          </div>
          <label className="flex items-center gap-2 text-xs text-muted-foreground shrink-0 select-none">
            <Checkbox
              checked={considerarLance}
              onCheckedChange={(v) => setConsiderarLance(Boolean(v))}
              aria-label="Considerar lance"
            />
            considerar lance
          </label>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="space-y-1">
            <div className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
              prazo (para benchmark)
            </div>
            <Select value={String(pack.prazoMeses)} onValueChange={(v) => setPrazoLance(Number(v))}>
              <SelectTrigger className="h-9">
                <SelectValue placeholder="Prazo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="84">84 meses</SelectItem>
                <SelectItem value="120">120 meses</SelectItem>
                <SelectItem value="180">180 meses</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <div className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
              benchmark de lance
            </div>
            <Select value={preset} onValueChange={(v) => setPreset(v as 'baixo' | 'médio' | 'alto')}>
              <SelectTrigger className="h-9">
                <SelectValue placeholder="Preset" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="baixo">
                  baixo ({Math.round(pack.low.pct * 100)}%)
                </SelectItem>
                <SelectItem value="médio">
                  médio ({Math.round(pack.avg.pct * 100)}%)
                </SelectItem>
                <SelectItem value="alto">
                  alto ({Math.round(pack.high.pct * 100)}%)
                </SelectItem>
              </SelectContent>
            </Select>
            <div className="text-[10px] text-muted-foreground font-mono">
              Faixa: {pack.bracketLabel}
            </div>
          </div>

          <div className="space-y-1">
            <div className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
              horizonte
            </div>
            <div className="rounded-md border border-border/60 bg-card/60 px-3 py-2 text-xs text-muted-foreground leading-relaxed">
              Planeje o caixa para <span className="font-medium text-foreground">{horizonteMeses} meses</span> de
              parcelas e, se optar pelo lance, um aporte pontual para antecipar a contemplação.
            </div>
          </div>
        </div>

        <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <Metric
            label="Lance (R$)"
            value={considerarLance ? formatBRL(posLance.lanceValor) : '—'}
            hint={considerarLance ? `${Math.round(lancePct * 100)}% da carta` : 'desativado'}
            highlight={considerarLance}
          />
          <Metric
            label="Parcela base (ref.)"
            value={formatBRL(parcelaBasePrazo)}
            hint={`${pack.prazoMeses}× · taxas ref.`}
          />
          <Metric
            label="Parcela pós-lance (est.)"
            value={considerarLance ? formatBRL(posLance.parcelaPosLance) : '—'}
            hint={considerarLance ? 'assume amortização do principal' : 'desativado'}
            highlight={considerarLance}
          />
          <Metric
            label="Saldo principal"
            value={considerarLance ? formatBRL(posLance.saldoPrincipalRestante) : '—'}
            hint={considerarLance ? 'após amortização (ref.)' : 'desativado'}
          />
        </dl>

        <p className="text-[11px] text-muted-foreground font-mono leading-relaxed">
          Assunções: lance como aporte próprio que amortiza o principal; taxas (admin/fundo) mantidas sobre a carta cheia
          para estimativa conservadora. Não modela contemplação, sorteio ou regras específicas (embutido/fixo/livre).
        </p>
      </section>

      <p className="text-[11px] text-muted-foreground font-mono leading-relaxed">
        Estimativa ilustrativa (taxa admin. {Math.round(CONSORCIO_TAXA_ADMIN_PCT * 100)}% · fundo{' '}
        {Math.round(CONSORCIO_TAXA_FUNDO_RESERVA_PCT * 100)}% · ref. financiamento {60}× a 1,2% a.m.). Não inclui
        probabilidade de contemplação por sorteio.
      </p>

      {SHOW_WHATSAPP_UI && (
        <Button asChild className="gap-2 w-full sm:w-auto">
          <a href={VECTRA_CONTATO_URL} target="_blank" rel="noopener noreferrer">
            <MessageCircle size={14} aria-hidden />
            Falar com Vectra Cargo
          </a>
        </Button>
      )}
    </article>
  )
}

function Metric({
  label,
  value,
  hint,
  highlight,
}: {
  label: string
  value: string
  hint?: string
  highlight?: boolean
}) {
  return (
    <div className="rounded-md border border-border/60 bg-card/60 px-3 py-2">
      <dt className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
        {label}
      </dt>
      <dd
        className={cn(
          'mt-0.5 font-semibold tabular-nums',
          highlight ? 'text-primary' : 'text-foreground',
        )}
      >
        {value}
      </dd>
      {hint && (
        <dd className="text-[10px] text-muted-foreground mt-0.5">{hint}</dd>
      )}
    </div>
  )
}
