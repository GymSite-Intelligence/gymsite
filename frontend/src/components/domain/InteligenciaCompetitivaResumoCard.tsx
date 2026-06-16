/**
 * Resumo executivo da inteligência competitiva (schema v1.7+).
 * Saturação no raio, referência CNPJ, top 5 independentes, amostra analisada.
 */
import { AlertTriangle, Building2, MapPin, Users } from 'lucide-react'
import { cn } from '@/lib/utils'
import type {
  AcademiaResumoJSON,
  CoberturaRedesA0JSON,
  MarketContextJSON,
  PanoramaCompetitivoJSON,
} from '@/hooks/useRelatorioDetail'

const SATURACAO_STYLE: Record<string, string> = {
  BAIXO: 'text-veredito-aprovado',
  MEDIO: 'text-veredito-ressalvas',
  ALTO: 'text-veredito-investigar',
  SATURADO: 'text-veredito-reprovado',
}

export interface AgregadosCompeticaoPlaces {
  count_total?: number | null
  count_rating_ge_4_2?: number | null
  status?: string
  radius_meters?: number
}

export interface InteligenciaCompetitivaResumoCardProps {
  nivelSaturacao?: string | null
  panorama?: PanoramaCompetitivoJSON | null
  agregadosPlaces?: AgregadosCompeticaoPlaces | null
  totalEncontradosNearby?: number | null
  fonteBuscaCompetidores?: string | null
  marketContext?: MarketContextJSON
  coberturaRedes?: CoberturaRedesA0JSON
  topIndependentes?: AcademiaResumoJSON[]
  academiasAnalisadas?: AcademiaResumoJSON[]
  totalEncontradosRaio?: number | null
  totalAnalisados?: number | null
  bairroAlvo?: string
  className?: string
}

export function InteligenciaCompetitivaResumoCard({
  nivelSaturacao,
  panorama,
  agregadosPlaces,
  totalEncontradosNearby,
  fonteBuscaCompetidores,
  marketContext,
  coberturaRedes,
  topIndependentes = [],
  academiasAnalisadas = [],
  totalEncontradosRaio,
  totalAnalisados,
  bairroAlvo,
  className,
}: InteligenciaCompetitivaResumoCardProps) {
  const sat =
    panorama?.nivel_saturacao || nivelSaturacao || '—'
  const satClass = SATURACAO_STYLE[sat.toUpperCase()] ?? 'text-foreground'
  const raio = panorama?.total_encontrados_raio ?? totalEncontradosRaio
  const aggTotal = agregadosPlaces?.count_total
  const nearby = totalEncontradosNearby
  const analisados = panorama?.total_concorrentes_analisados ?? totalAnalisados
  const parqueAtivo =
    panorama?.cnpj_parque_ativo_cidade ??
    panorama?.cnpj_academias_ativas_cidade ??
    marketContext?.parque_ativo_total ??
    marketContext?.academias_ativas_cidade_cnpj
  const novos90 = marketContext?.novos_cnpj_fitness_90d
  const redesDr = marketContext?.principais_redes_concorrentes ?? []
  const redesCobertas = coberturaRedes?.redes_cobertas ?? []
  const redesFantasma = coberturaRedes?.redes_nao_encontradas ?? []

  const temConteudo =
    sat !== '—' ||
    raio != null ||
    analisados != null ||
    parqueAtivo != null ||
    topIndependentes.length > 0 ||
    redesDr.length > 0

  if (!temConteudo) return null

  return (
    <div
      className={cn(
        'rounded-lg border border-border bg-muted/20 p-4 space-y-4',
        className,
      )}
    >
      <header>
        <h4 className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground flex items-center gap-1.5">
          <Users size={12} />
          Panorama competitivo
          {bairroAlvo ? ` — ${bairroAlvo}` : ''}
        </h4>
        {panorama?.metodologia && (
          <p className="mt-1 text-[11px] text-muted-foreground leading-snug">
            {panorama.metodologia}
          </p>
        )}
      </header>

      {fonteBuscaCompetidores === 'google_places' && (
        <p className="text-[11px] text-muted-foreground font-mono">
          Fonte: Google Places (New) + Area Insights
          {aggTotal != null && nearby != null
            ? ` — ${aggTotal} no raio; ${nearby} na amostra detalhada`
            : ''}
        </p>
      )}

      <dl className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Metric
          label="Saturação (bairro)"
          value={sat}
          valueClassName={satClass}
        />
        {analisados != null && (
          <Metric label="Concorrentes no bairro" value={String(analisados)} />
        )}
        {raio != null && (
          <Metric label="Densidade 3km (contexto regional)" value={String(raio)} />
        )}
        {parqueAtivo != null && (
          <Metric label="Parque município (contexto)" value={String(parqueAtivo)} />
        )}
        {typeof novos90 === 'number' && (
          <Metric label="Novas unidades 90d (contexto)" value={String(novos90)} />
        )}
      </dl>

      {(redesDr.length > 0 || redesCobertas.length > 0) && (
        <section className="space-y-2">
          <h5 className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
            Redes (Deep Research vs validadas no bairro)
          </h5>
          <div className="flex flex-wrap gap-1.5">
            {redesDr.map((r) => (
              <span
                key={`dr-${r}`}
                className="rounded-md bg-muted px-2 py-0.5 text-xs font-mono"
              >
                {r}
              </span>
            ))}
          </div>
          {redesCobertas.length > 0 && (
            <p className="text-[11px] text-muted-foreground">
              Validadas: {redesCobertas.join(' · ')}
            </p>
          )}
          {redesFantasma.length > 0 && (
            <p className="text-[11px] text-veredito-ressalvas flex items-start gap-1.5">
              <AlertTriangle size={12} className="shrink-0 mt-0.5" />
              DR listou sem unidade no raio: {redesFantasma.join(', ')}
            </p>
          )}
        </section>
      )}

      {topIndependentes.length > 0 && (
        <section className="space-y-2">
          <h5 className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground flex items-center gap-1.5">
            <Building2 size={11} />
            Top {topIndependentes.length} academias independentes (por avaliações)
          </h5>
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-left">
                  <th className="px-2 py-1.5 font-mono text-[10px]">Nome</th>
                  <th className="px-2 py-1.5 font-mono text-[10px]">Rating</th>
                  <th className="px-2 py-1.5 font-mono text-[10px]">Reviews</th>
                  <th className="px-2 py-1.5 font-mono text-[10px]">Bairro</th>
                </tr>
              </thead>
              <tbody>
                {topIndependentes.map((a) => (
                  <tr key={a.place_id ?? a.nome} className="border-b border-border last:border-0">
                    <td className="px-2 py-1.5 font-medium">{a.nome}</td>
                    <td className="px-2 py-1.5 tabular-nums">{a.rating ?? '—'}</td>
                    <td className="px-2 py-1.5 tabular-nums">{a.num_avaliacoes ?? '—'}</td>
                    <td className="px-2 py-1.5 text-muted-foreground">{a.bairro ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {academiasAnalisadas.length > 0 && (
        <section className="space-y-1.5">
          <h5 className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground flex items-center gap-1.5">
            <MapPin size={11} />
            Unidades na amostra aprofundada (reviews + dores)
          </h5>
          <ul className="text-xs space-y-1">
            {academiasAnalisadas.map((a) => (
              <li key={a.place_id ?? a.nome} className="flex flex-wrap gap-x-2">
                <span className="font-medium">{a.nome}</span>
                {a.rede_vinculada ? (
                  <span className="text-muted-foreground font-mono">({a.rede_vinculada})</span>
                ) : (
                  <span className="text-veredito-investigar font-mono text-[10px]">
                    independente
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

function Metric({
  label,
  value,
  valueClassName,
}: {
  label: string
  value: string
  valueClassName?: string
}) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono">
        {label}
      </dt>
      <dd className={cn('font-semibold text-sm tabular-nums', valueClassName)}>{value}</dd>
    </div>
  )
}
