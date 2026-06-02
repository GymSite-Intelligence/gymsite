/**
 * ContextoMercadoCard — exibe o output completo do A0 Deep Research.
 *
 * Schema v1.2+ persiste market_context rico em output_consolidado:
 * ticket, aluguel R$/m², renda, faixa etária, redes, tendência,
 * regulamentação, insights estratégicos.
 * Schema v1.7: novos_cnpj_fitness_90d + serie_aberturas_anual (RFB CNPJ Aberto).
 *
 * Graceful degradation: se o relatório for v1.1 antigo (sem market_context),
 * renderiza só os metadados básicos + métricas derivadas do output.
 */
import {
  CheckCircle,
  Database,
  Lightbulb,
  TrendingDown,
  TrendingUp,
  Minus,
  ScrollText,
  Building2,
} from 'lucide-react'
import { RerunPipelineButton } from '@/components/domain/RerunPipelineButton'
import { cn } from '@/lib/utils'
import { formatComposicaoParque } from '@/lib/segmento-parque'
import { valorDisponivel } from '@/lib/dados-indisponiveis'
import type { CoberturaRedesA0JSON, MarketContextJSON } from '@/hooks/useRelatorioDetail'

export interface ContextoMercadoCardProps {
  /** UUID do relatório — habilita botão "Gerar novamente" no aviso v1.1. */
  relatorioId?: string
  /** Schema v1.2: market_context completo. Em v1.1, undefined → modo legacy. */
  marketContext?: MarketContextJSON
  /** Fallback v1.1 vindo de metadata_execucao */
  fonte?: string
  dataColeta?: string
  cached?: boolean
  redesA0?: string[]
  /** Cobertura A0 — só exibe redes validadas localmente quando DR falhou. */
  coberturaRedes?: CoberturaRedesA0JSON
  /** Métricas derivadas do output_consolidado pra dar substância à seção */
  totalConcorrentesAnalisados?: number
  nivelSaturacao?: string | null
  aluguelMedianaM2?: number | null
  fonteAluguel?: string | null
  className?: string
}

function formatData(iso: string | undefined): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return iso
  }
}

const TENDENCIA_CONFIG: Record<
  string,
  { label: string; Icon: typeof TrendingUp; color: string }
> = {
  crescimento: {
    label: 'Crescimento',
    Icon: TrendingUp,
    color: 'text-veredito-aprovado',
  },
  estavel: { label: 'Estável', Icon: Minus, color: 'text-veredito-ressalvas' },
  retracao: { label: 'Retração', Icon: TrendingDown, color: 'text-veredito-reprovado' },
}

export function ContextoMercadoCard({
  relatorioId,
  marketContext,
  fonte,
  dataColeta,
  cached,
  redesA0,
  coberturaRedes,
  totalConcorrentesAnalisados,
  nivelSaturacao,
  aluguelMedianaM2,
  fonteAluguel,
  className,
}: ContextoMercadoCardProps) {
  // Prefere market_context (v1.2); fallback graceful pros campos avulsos (v1.1)
  const mc = marketContext ?? {}
  const fonteEff = mc.fonte ?? fonte ?? 'Desconhecida'
  const dataColetaEff = mc.data_coleta ?? dataColeta ?? ''
  const cachedEff = mc.cached ?? cached ?? false
  const redesDr = mc.principais_redes_concorrentes ?? redesA0 ?? []
  const redesValidadas =
    coberturaRedes?.redes_locais_validadas ??
    coberturaRedes?.redes_cobertas ??
    (coberturaRedes?.tem_redes_fantasma ? [] : redesDr)
  const redesDrNaoValidadas =
    mc.redes_dr_nao_validadas ?? coberturaRedes?.redes_nao_encontradas ?? []

  const tendCfg = mc.tendencia_mercado
    ? TENDENCIA_CONFIG[mc.tendencia_mercado.toLowerCase()] ?? null
    : null

  // Schema v1.4: gênero alvo só aparece se ≠ misto (default).
  // Labels legíveis pra usuário (não o slug snake_case que vem do A0).
  const GENERO_LABELS: Record<string, string> = {
    misto: 'Misto (50/50)',
    predominantemente_feminino: 'Predominantemente feminino',
    predominantemente_masculino: 'Predominantemente masculino',
    exclusivamente_feminino: 'Exclusivamente feminino',
    exclusivamente_masculino: 'Exclusivamente masculino',
  }
  const generoLabel =
    mc.genero_alvo && mc.genero_alvo !== 'misto'
      ? GENERO_LABELS[mc.genero_alvo] ?? mc.genero_alvo
      : null

  // Schema v1.5: tipo de negócio + tamanho preset (Smart Fit-style).
  // Mostra sempre quando presente — útil pra cliente confirmar inputs.
  const TIPO_LABELS: Record<string, string> = {
    academia: 'Academia tradicional',
    crossfit_box: 'CrossFit / Box',
    studio_pilates: 'Estúdio Pilates',
    studio_funcional: 'Studio Funcional',
    outro: 'Outro',
  }
  const TAMANHO_LABELS: Record<string, string> = {
    pp: 'PP (micro)',
    p: 'P (pequeno)',
    m: 'M (padrão de mercado ★)',
    g: 'G (grande porte)',
    gg: 'GG (mega centro)',
  }
  const tipoLabel = mc.tipo_negocio ? TIPO_LABELS[mc.tipo_negocio] ?? mc.tipo_negocio : null
  const tamanhoLabel = mc.tamanho_preset
    ? TAMANHO_LABELS[mc.tamanho_preset] ?? mc.tamanho_preset.toUpperCase()
    : null

  const novosCnpj90d =
    typeof mc.novos_cnpj_fitness_90d === 'number' && mc.novos_cnpj_fitness_90d >= 0
      ? mc.novos_cnpj_fitness_90d
      : null

  const serieAberturas = mc.serie_aberturas_anual
    ? Object.entries(mc.serie_aberturas_anual)
        .filter(([, n]) => typeof n === 'number')
        .sort(([a], [b]) => a.localeCompare(b))
    : []

  const serieAberturasLabel =
    serieAberturas.length > 0
      ? serieAberturas.map(([ano, n]) => `${ano}: ${n}`).join(' · ')
      : null

  const fonteEntrantes =
    mc.fonte_entrantes && mc.fonte_entrantes !== 'dados_nao_disponiveis'
      ? mc.fonte_entrantes
      : null

  const parqueAtivo =
    typeof mc.parque_ativo_total === 'number'
      ? mc.parque_ativo_total
      : typeof mc.academias_ativas_cidade_cnpj === 'number'
        ? mc.academias_ativas_cidade_cnpj
        : null

  const composicaoParqueLabel = formatComposicaoParque(mc.composicao_parque)

  const temDadosCnpj =
    novosCnpj90d != null ||
    parqueAtivo != null ||
    !!composicaoParqueLabel ||
    !!serieAberturasLabel

  // Calculado DEPOIS das labels pra ordem de declaração (TypeScript strict).
  const temMarketContextRico = !!(
    valorDisponivel(mc.ticket_medio_mercado) ||
    valorDisponivel(mc.aluguel_medio_m2) ||
    valorDisponivel(mc.renda_media_bairro) ||
    valorDisponivel(mc.faixa_etaria_predominante) ||
    generoLabel ||
    tipoLabel ||
    tamanhoLabel ||
    mc.tendencia_mercado ||
    mc.regulamentacao_resumo ||
    temDadosCnpj ||
    (mc.insights_estrategicos && mc.insights_estrategicos.length > 0)
  )

  return (
    <div
      className={cn(
        'rounded-lg border border-border bg-card overflow-hidden',
        className,
      )}
    >
      {/* Header — fonte */}
      <div className="px-5 py-3 border-b border-border flex items-center justify-between flex-wrap gap-2 bg-muted/20">
        <div className="flex items-center gap-2 text-sm">
          <Database size={14} className="text-muted-foreground" />
          <span className="text-muted-foreground">Fonte:</span>
          <span className="font-mono">{fonteEff}</span>
        </div>
        <div className="flex items-center gap-3 text-[10px] font-mono text-muted-foreground">
          {dataColetaEff && <span>coletado em {formatData(dataColetaEff)}</span>}
          {cachedEff && (
            <span className="flex items-center gap-1 text-veredito-investigar">
              <CheckCircle size={10} /> cache
            </span>
          )}
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* Tabela de indicadores ricos (v1.2) */}
        {temMarketContextRico && (
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full">
              <tbody>
                {valorDisponivel(mc.ticket_medio_mercado) && (
                  <IndicatorRow
                    label="Ticket médio local"
                    value={String(valorDisponivel(mc.ticket_medio_mercado))}
                  />
                )}
                {valorDisponivel(mc.aluguel_medio_m2) && (
                  <IndicatorRow
                    label="Aluguel médio comercial"
                    value={String(valorDisponivel(mc.aluguel_medio_m2))}
                  />
                )}
                {valorDisponivel(mc.renda_media_bairro) && (
                  <IndicatorRow
                    label="Renda média do bairro"
                    value={String(valorDisponivel(mc.renda_media_bairro))}
                  />
                )}
                {valorDisponivel(mc.faixa_etaria_predominante) && (
                  <IndicatorRow
                    label="Faixa etária predominante"
                    value={String(valorDisponivel(mc.faixa_etaria_predominante))}
                  />
                )}
                {generoLabel && (
                  <IndicatorRow
                    label="Gênero alvo"
                    value={
                      <span className="inline-flex items-center gap-1.5">
                        <span className="font-semibold">{generoLabel}</span>
                        <span className="text-[10px] text-muted-foreground font-mono">
                          calibra A4
                        </span>
                      </span>
                    }
                  />
                )}
                {tipoLabel && (
                  <IndicatorRow label="Tipo de negócio" value={tipoLabel} />
                )}
                {tamanhoLabel && (
                  <IndicatorRow
                    label="Tamanho"
                    value={
                      <span className="inline-flex items-center gap-1.5">
                        <span className="font-semibold">{tamanhoLabel}</span>
                        <span className="text-[10px] text-muted-foreground font-mono">
                          Smart Fit-style
                        </span>
                      </span>
                    }
                  />
                )}
                {tendCfg && (
                  <IndicatorRow
                    label="Tendência do mercado"
                    value={
                      <span className={cn('inline-flex items-center gap-1.5', tendCfg.color)}>
                        <tendCfg.Icon size={12} />
                        <span className="font-semibold">{tendCfg.label}</span>
                      </span>
                    }
                  />
                )}
                {parqueAtivo != null && (
                  <IndicatorRow
                    label="Parque ativo (município)"
                    value={
                      <span className="font-semibold tabular-nums">{parqueAtivo}</span>
                    }
                  />
                )}
                {composicaoParqueLabel && (
                  <IndicatorRow
                    label="Composição do parque"
                    value={
                      <span className="text-xs leading-snug">{composicaoParqueLabel}</span>
                    }
                  />
                )}
                {novosCnpj90d != null && (
                  <IndicatorRow
                    label="Novas unidades (90 dias)"
                    value={
                      <span className="inline-flex items-center gap-1.5">
                        <Building2 size={12} className="text-veredito-investigar shrink-0" />
                        <span className="font-semibold tabular-nums">{novosCnpj90d}</span>
                        <span className="text-[10px] text-muted-foreground font-normal">
                          {mc.cidade ? `em ${mc.cidade}` : 'na cidade'}
                          {mc.uf ? ` (${mc.uf})` : ''}
                        </span>
                      </span>
                    }
                  />
                )}
                {serieAberturasLabel && (
                  <IndicatorRow
                    label="Aberturas por ano (CNPJ)"
                    value={
                      <span className="font-mono text-xs">{serieAberturasLabel}</span>
                    }
                  />
                )}
              </tbody>
            </table>
          </div>
        )}

        {temDadosCnpj && fonteEntrantes && (
          <p className="text-[10px] font-mono text-muted-foreground -mt-3">
            Entrantes: {fonteEntrantes}
          </p>
        )}

        {(mc.fatos_parque_cnpj?.lacunas?.length ?? 0) > 0 && (
          <section className="rounded-md border border-border bg-muted/15 p-4 space-y-2">
            <h4 className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
              Fatos parque CNPJ (A0)
            </h4>
            <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-1">
              {mc.fatos_parque_cnpj!.lacunas!.map((l, i) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          </section>
        )}

        {/* Métricas derivadas (sempre presentes — vêm do output, não do A0) */}
        <dl className="grid grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-3">
          {totalConcorrentesAnalisados != null && (
            <Metric
              label="Concorrentes analisados"
              value={String(totalConcorrentesAnalisados)}
            />
          )}
          {nivelSaturacao && <Metric label="Nível de saturação" value={nivelSaturacao} />}
          {aluguelMedianaM2 != null && (
            <Metric
              label="Aluguel mediana R$/m² (pipeline)"
              value={`R$ ${aluguelMedianaM2.toFixed(2)}`}
              hint={fonteAluguel ?? undefined}
            />
          )}
        </dl>

        {/* Redes — só as validadas no raio (OSM/Places); não lista DR “fantasma”. */}
        {redesValidadas.length > 0 && (
          <div>
            <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono mb-2">
              Redes com unidade no raio (validadas)
            </h4>
            <ul className="flex flex-wrap gap-1.5">
              {redesValidadas.map((rede) => (
                <li
                  key={rede}
                  className="px-2 py-0.5 rounded-md bg-muted text-xs font-mono"
                >
                  {rede}
                </li>
              ))}
            </ul>
          </div>
        )}
        {redesDrNaoValidadas.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Redes citadas pelo Deep Research sem unidade confirmada no raio:{' '}
            <span className="font-mono">{redesDrNaoValidadas.join(', ')}</span>
          </p>
        )}
        {redesValidadas.length === 0 &&
          redesDr.length > 0 &&
          (coberturaRedes?.tem_redes_fantasma || totalConcorrentesAnalisados === 0) && (
            <p className="text-xs text-veredito-investigar">
              Nenhuma rede foi confirmada por busca local (geocode/Places/OSM). A lista do
              Deep Research não é exibida como concorrência verificada.
            </p>
          )}

        {/* Insights estratégicos */}
        {mc.insights_estrategicos && mc.insights_estrategicos.length > 0 && (
          <div className="rounded-md border-l-2 border-veredito-investigar bg-veredito-investigar/5 p-3 space-y-2">
            <h4 className="text-[10px] uppercase tracking-wider text-veredito-investigar font-mono font-semibold flex items-center gap-1.5">
              <Lightbulb size={11} />
              Insights estratégicos
            </h4>
            <ul className="space-y-1.5 text-sm">
              {mc.insights_estrategicos.map((insight, i) => (
                <li key={i} className="flex items-start gap-2 leading-snug">
                  <span aria-hidden className="text-veredito-investigar mt-0.5 shrink-0">›</span>
                  <span>{insight}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Regulamentação */}
        {valorDisponivel(mc.regulamentacao_resumo) && (
          <div className="rounded-md bg-muted/30 p-3 flex items-start gap-2">
            <ScrollText size={14} className="text-muted-foreground mt-0.5 shrink-0" />
            <div>
              <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono font-semibold mb-1">
                Regulamentação
              </h4>
              <p className="text-xs leading-relaxed">
                {String(valorDisponivel(mc.regulamentacao_resumo))}
              </p>
            </div>
          </div>
        )}

        {/* Aviso quando schema v1.1 (sem dados ricos) */}
        {!temMarketContextRico && (
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-t border-border pt-3">
            <p className="text-[10px] font-mono text-muted-foreground/60">
              ⚠ Este relatório foi gerado com schema v1.1. Indicadores ricos (ticket, renda,
              tendência, regulamentação, insights) só aparecem em relatórios v1.2+.
            </p>
            {relatorioId && (
              <RerunPipelineButton
                relatorioId={relatorioId}
                label="Atualizar relatório"
                variant="secondary"
                size="sm"
                className="shrink-0"
              />
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function IndicatorRow({
  label,
  value,
}: {
  label: string
  value: React.ReactNode
}) {
  return (
    <tr className="border-b border-border last:border-b-0">
      <td className="px-3 py-2 text-xs text-muted-foreground w-1/2">{label}</td>
      <td className="px-3 py-2 text-sm font-medium">{value}</td>
    </tr>
  )
}

function Metric({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint?: string
}) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono">
        {label}
      </dt>
      <dd className="font-semibold text-sm">{value}</dd>
      {hint && (
        <dd className="text-[10px] font-mono text-muted-foreground">{hint}</dd>
      )}
    </div>
  )
}
