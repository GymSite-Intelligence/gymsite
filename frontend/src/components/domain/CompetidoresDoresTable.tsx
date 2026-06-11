/**
 * CompetidoresDoresTable — tabela 1 linha = 1 concorrente, com dores
 * extraídas dos reviews (sem agregação cross-concorrência).
 *
 * Sobrescreve a antiga DoresDominantesTable (que agregava por dor).
 * Aqui cada concorrente mantém suas próprias dores nominais, junto com
 * contato (tel/site/wpp) — mesmo modelo dos Top 3 Candidatos.
 *
 * Os campos telefone/website/whatsapp_link vêm de Places API New (Fase 2).
 * Enquanto não popular, células mostram "—" sem quebrar layout.
 */
import { ExternalLink, MessageCircle, Phone, Globe } from 'lucide-react'
import { CategoriaDorBadge } from './CategoriaDorBadge'
import { SparklinePopularTimes } from './SparklinePopularTimes'
import { cn } from '@/lib/utils'
import { SHOW_WHATSAPP_UI } from '@/lib/feature-flags'
import type {
  CompetidorJSON,
  ReviewJSON,
} from '@/hooks/useRelatorioDetail'
import type { CategoriaDor } from '@/types/domain'

export interface CompetidoresDoresTableProps {
  competidores: CompetidorJSON[] | undefined
  servicosNaoOferecidos?: string[]
  className?: string
}

interface DorAgregada {
  categoria: CategoriaDor
  count: number
  sinal: 'positivo' | 'neutro' | 'negativo'
}

/**
 * Filtro defensive: dores só de reviews com ≤ 1 ano. Backend já filtra,
 * mas mantemos aqui pra dados antigos no DB ou bypass do A3a.
 *
 * Google retorna data_relativa em EN ('3 years ago', 'a year ago',
 * '6 months ago') ou PT-BR ('há 3 anos'). Reviews sem label entram
 * como recentes (defensive).
 */
function reviewRecente1Ano(dataRelativa: string | undefined): boolean {
  if (!dataRelativa) return true
  const s = dataRelativa.trim().toLowerCase()
  if (!s) return true
  return !(s.includes('year') || s.includes('ano'))
}

/** Agrega dores citadas nos reviews recentes (≤ 1 ano) de UM competidor. */
function doresPorCompetidor(c: CompetidorJSON): DorAgregada[] {
  const reviews: ReviewJSON[] = c.reviews ?? c.reviews_traduzidas ?? []
  const recentes = reviews.filter((r) => reviewRecente1Ano(r.data_relativa))
  const baixaNotaRecente = recentes.filter((r) => (r.rating ?? 5) <= 3)
  const baixaNotaQualquer = reviews.filter((r) => (r.rating ?? 5) <= 3)
  const fonte =
    baixaNotaRecente.length > 0
      ? baixaNotaRecente
      : baixaNotaQualquer.length > 0
        ? baixaNotaQualquer
        : recentes
  const map = new Map<string, DorAgregada>()
  for (const r of fonte) {
    const cat = (r.categoria_dor || '').trim() as CategoriaDor
    if (!cat || cat === ('outra' as CategoriaDor)) continue
    const slot = map.get(cat)
    if (slot) {
      slot.count += 1
      // mantém o sinal mais "pessimista" (negativo > neutro > positivo)
      if (r.sinal === 'negativo') slot.sinal = 'negativo'
      else if (r.sinal === 'neutro' && slot.sinal !== 'negativo') slot.sinal = 'neutro'
    } else {
      map.set(cat, { categoria: cat, count: 1, sinal: r.sinal ?? 'neutro' })
    }
  }
  return Array.from(map.values()).sort((a, b) => b.count - a.count)
}

function sinalPredominante(dores: DorAgregada[]): 'positivo' | 'neutro' | 'negativo' {
  if (!dores.length) return 'neutro'
  const totais: Record<string, number> = { positivo: 0, neutro: 0, negativo: 0 }
  for (const d of dores) totais[d.sinal] += d.count
  if (totais.negativo >= totais.neutro && totais.negativo >= totais.positivo) return 'negativo'
  if (totais.positivo > totais.negativo) return 'positivo'
  return 'neutro'
}

const SINAL_BADGE: Record<
  'positivo' | 'neutro' | 'negativo',
  { label: string; classe: string }
> = {
  positivo: { label: '+', classe: 'bg-veredito-aprovado/20 text-veredito-aprovado' },
  neutro: { label: '=', classe: 'bg-muted text-muted-foreground' },
  negativo: { label: '−', classe: 'bg-veredito-reprovado/20 text-veredito-reprovado' },
}

export function CompetidoresDoresTable({
  competidores,
  servicosNaoOferecidos,
  className,
}: CompetidoresDoresTableProps) {
  if (!competidores || competidores.length === 0) {
    return (
      <div
        className={cn(
          'rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground',
          className,
        )}
      >
        Nenhum concorrente analisado neste relatório.
      </div>
    )
  }

  const algumPico = competidores.some(
    (c) => (c.horarios_pico && Object.keys(c.horarios_pico).length > 0) || c.pico_semanal,
  )

  return (
    <div className={cn('space-y-4', className)}>
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <header className="px-4 py-2.5 border-b border-border bg-muted/20 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-mono font-medium">
              Concorrentes — dores citadas nos reviews
            </h3>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              Place ID alimenta horários de pico (SearchAPI → cache 7d por ficha).
            </p>
          </div>
          <span className="text-[10px] font-mono text-muted-foreground">
            {competidores.length} academia{competidores.length === 1 ? '' : 's'}
          </span>
        </header>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono border-b border-border">
                <th className="text-left p-3 font-medium">Concorrente</th>
                <th className="text-left p-3 font-medium w-[148px]">Place ID</th>
                <th className="text-left p-3 font-medium">Contato</th>
                <th className="text-center p-3 font-medium w-20">Rating</th>
                {algumPico && (
                  <th className="text-left p-3 font-medium w-[140px]">Pico (24h)</th>
                )}
                <th className="text-left p-3 font-medium">Dores citadas</th>
                <th className="text-center p-3 font-medium w-16">Sinal</th>
              </tr>
            </thead>
            <tbody>
              {competidores.map((c, i) => {
                const dores = doresPorCompetidor(c)
                const sinal = sinalPredominante(dores)
                const sinalCfg = SINAL_BADGE[sinal]
                const rating = c.rating_oficial ?? c.rating_geral
                const pid = c.place_id?.trim()
                const mapsPlaceUrl = pid
                  ? `https://www.google.com/maps/place/?q=place_id:${encodeURIComponent(pid)}`
                  : null
                return (
                  <tr
                    key={pid ?? `${c.nome}-${i}`}
                    className="border-b border-border last:border-b-0 hover:bg-muted/30 align-top"
                  >
                    <td className="p-3">
                      <div className="font-medium text-sm">{c.nome}</div>
                      {(c.bairro_concorrente || c.endereco) && (
                        <div className="text-[10px] text-muted-foreground font-mono mt-0.5">
                          {c.bairro_concorrente || c.endereco}
                        </div>
                      )}
                      {c.tem_24h && (
                        <span className="inline-block mt-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-veredito-aprovado/15 text-veredito-aprovado">
                          24h
                        </span>
                      )}
                    </td>
                    <td className="p-3 align-top">
                      {pid ? (
                        <a
                          href={mapsPlaceUrl!}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[10px] font-mono text-muted-foreground hover:text-foreground"
                          title={pid}
                        >
                          <span className="truncate max-w-[120px]">{pid}</span>
                          <ExternalLink size={9} className="shrink-0" />
                        </a>
                      ) : (
                        <span
                          className="text-[10px] italic text-veredito-investigar"
                          title="Sem Place ID — horários de pico (SearchAPI) não rodam para esta linha"
                        >
                          ausente
                        </span>
                      )}
                    </td>
                    <td className="p-3">
                      <ContatoCell
                        telefone={c.telefone}
                        website={c.website}
                        whatsapp={SHOW_WHATSAPP_UI ? c.whatsapp_link : undefined}
                      />
                    </td>
                    <td className="p-3 text-center font-mono text-sm tabular-nums">
                      {rating != null ? rating.toFixed(1) : '—'}
                      {c.num_avaliacoes != null && (
                        <div className="text-[10px] text-muted-foreground">
                          {c.num_avaliacoes} aval.
                        </div>
                      )}
                    </td>
                    {algumPico && (
                      <td className="p-3">
                        <SparklinePopularTimes
                          horariosPico={c.horarios_pico}
                          picoSemanal={c.pico_semanal}
                        />
                      </td>
                    )}
                    <td className="p-3">
                      {dores.length === 0 ? (
                        <span className="text-xs italic text-muted-foreground">
                          Sem dores classificadas
                        </span>
                      ) : (
                        <ul className="flex flex-wrap gap-1.5">
                          {dores.map((d) => (
                            <li key={d.categoria} className="flex items-center gap-1">
                              <CategoriaDorBadge
                                categoria={d.categoria}
                                sinal={d.sinal}
                              />
                              <span className="font-mono text-[10px] text-muted-foreground">
                                ×{d.count}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                    <td className="p-3 text-center">
                      <span
                        className={cn(
                          'inline-flex items-center justify-center w-7 h-7 rounded-full font-semibold text-sm',
                          sinalCfg.classe,
                        )}
                        title={sinal}
                        aria-label={sinal}
                      >
                        {sinalCfg.label}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {servicosNaoOferecidos && servicosNaoOferecidos.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-mono font-medium mb-2">
            Gaps de mercado (NINGUÉM oferece)
          </h3>
          <ul className="flex flex-wrap gap-1.5">
            {servicosNaoOferecidos.map((s) => (
              <li
                key={s}
                className="px-2 py-0.5 rounded-md bg-veredito-investigar/20 text-veredito-investigar text-xs font-mono"
              >
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function ContatoCell({
  telefone,
  website,
  whatsapp,
}: {
  telefone?: string | null
  website?: string | null
  whatsapp?: string | null
}) {
  const temAlgo = telefone || website || whatsapp
  if (!temAlgo) {
    return <span className="text-[10px] italic text-muted-foreground">—</span>
  }
  return (
    <div className="flex flex-col gap-1 text-xs">
      {telefone && (
        <a
          href={`tel:${telefone.replace(/[^0-9+]/g, '')}`}
          className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
        >
          <Phone size={11} /> <span className="font-mono">{telefone}</span>
        </a>
      )}
      {whatsapp && (
        <a
          href={whatsapp}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-veredito-aprovado hover:underline"
        >
          <MessageCircle size={11} /> WhatsApp
          <ExternalLink size={9} />
        </a>
      )}
      {website && (
        <a
          href={website}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
        >
          <Globe size={11} />
          <span className="font-mono truncate max-w-[140px]">
            {website.replace(/^https?:\/\//, '')}
          </span>
          <ExternalLink size={9} />
        </a>
      )}
    </div>
  )
}
