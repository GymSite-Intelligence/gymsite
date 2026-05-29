/**
 * CandidatoCard — card de um dos Top 3 candidatos a imóvel.
 *
 * Renderiza street view image, endereço, área estimada, scores GeoScout e
 * Ancoragem, polos geradores e próximo passo recomendado.
 *
 * O `street_view_url` vem pronto do JSON canônico do pipeline (Google Street
 * View Static API com lat/lng do candidato). Se falhar (404 / quota), fallback
 * pra placeholder visual sem quebrar layout.
 */
import { useState } from 'react'
import { MapPin, Eye, AlertCircle, Phone, Globe, Clock, MessageCircle, ExternalLink } from 'lucide-react'
import { ScoreGauge } from './ScoreGauge'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { SHOW_WHATSAPP_UI } from '@/lib/feature-flags'
import type { CandidatoJSON } from '@/hooks/useRelatorioDetail'

function formatTelefoneBR(tel: string): string {
  const digits = tel.replace(/\D/g, '').replace(/^55/, '')
  if (digits.length === 11) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`
  }
  if (digits.length === 10) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`
  }
  return tel  // formato desconhecido — devolve cru
}

function whatsappLink(tel: string): string {
  const digits = tel.replace(/\D/g, '')
  const num = digits.startsWith('55') ? digits : `55${digits}`
  return `https://wa.me/${num}`
}

export interface CandidatoCardProps {
  candidato: CandidatoJSON
  posicao: number
  /** Score Geral combinado (4 dim) — calculado no caller pra todos receberem mesma base */
  scoreGeral?: number | null
  className?: string
}

export function CandidatoCard({
  candidato,
  posicao,
  scoreGeral = null,
  className,
}: CandidatoCardProps) {
  const [imgError, setImgError] = useState(false)

  const visibilidade = candidato.estimativa_visibilidade ?? 'desconhecida'
  const tipoLabel = (candidato.tipos?.[0] ?? '').replace(/_/g, ' ')
  const isListing =
    candidato.qualidade_sinal === 'direto-listing' ||
    candidato.fonte === 'listing' ||
    !!candidato.listing_url
  const anuncioUrl = candidato.listing_url || candidato.website
  const portalLabel =
    candidato.listing_source === 'olx'
      ? 'OLX'
      : candidato.listing_source === 'imovelweb'
        ? 'ImovelWeb'
        : 'Anúncio'

  return (
    <article
      className={cn(
        'rounded-lg border border-border bg-card overflow-hidden flex flex-col',
        className,
      )}
    >
      {/* Header com street view */}
      <div className="relative aspect-[16/10] bg-muted">
        {candidato.street_view_url && !imgError ? (
          <img
            src={candidato.street_view_url}
            alt={`Street view de ${candidato.nome}`}
            onError={() => setImgError(true)}
            loading="lazy"
            className="absolute inset-0 w-full h-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
            <Eye size={32} className="opacity-40 mb-1" />
            <span className="text-xs font-mono">street view indisponível</span>
          </div>
        )}
        {/* Badge posição (canto esquerdo) */}
        <Badge
          mono
          className="absolute top-2 left-2 bg-background/85 backdrop-blur text-foreground border-transparent font-semibold"
        >
          #{posicao}
        </Badge>
        {isListing && (
          <Badge
            variant="default"
            className="absolute top-2 left-14 bg-primary/90 text-primary-foreground backdrop-blur"
          >
            {portalLabel}
          </Badge>
        )}
        {/* Badge visibilidade (canto direito) — tonalidade por nível */}
        <Badge
          variant={
            visibilidade === 'alta'
              ? 'success'
              : visibilidade === 'média' || visibilidade === 'media'
                ? 'warning'
                : 'secondary'
          }
          mono
          className="absolute top-2 right-2 uppercase backdrop-blur"
        >
          vis. {visibilidade}
        </Badge>
      </div>

      {/* Corpo */}
      <div className="p-4 space-y-3 flex-1 flex flex-col">
        <div>
          <h3 className="font-semibold text-sm leading-tight">{candidato.nome}</h3>
          {candidato.price_raw && isListing && (
            <p className="text-sm font-mono font-semibold text-primary mt-0.5">
              {candidato.price_raw}
            </p>
          )}
          {tipoLabel && (
            <p className="text-[10px] font-mono uppercase text-muted-foreground mt-0.5">
              {tipoLabel}
              {candidato.area_estimada_m2 && (
                <>
                  {' · '}
                  <span>~{candidato.area_estimada_m2} m²</span>
                </>
              )}
            </p>
          )}
        </div>

        {candidato.endereco && (
          <p className="text-xs text-muted-foreground flex items-start gap-1.5">
            <MapPin size={12} className="mt-0.5 shrink-0" />
            <span>{candidato.endereco}</span>
          </p>
        )}

        {/* Contact Data — Button primitives padronizados (UI Lote 2) */}
        {(candidato.telefone || anuncioUrl || candidato.tem_24h) && (
          <div className="flex items-center gap-2 flex-wrap">
            {candidato.telefone && (
              <>
                <Button variant="outline" size="sm" className="h-7 text-xs" asChild>
                  <a href={`tel:${candidato.telefone}`} title="Ligar">
                    <Phone size={12} />
                    <span className="font-mono">
                      {formatTelefoneBR(candidato.telefone)}
                    </span>
                  </a>
                </Button>
                {SHOW_WHATSAPP_UI && (
                  <Button variant="success" size="sm" className="h-7 text-xs" asChild>
                    <a
                      href={whatsappLink(candidato.telefone)}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="WhatsApp"
                    >
                      <MessageCircle size={12} />
                      WhatsApp
                    </a>
                  </Button>
                )}
              </>
            )}
            {anuncioUrl && (
              <Button variant="outline" size="sm" className="h-7 text-xs" asChild>
                <a
                  href={anuncioUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={isListing ? `Ver anúncio ${portalLabel}` : 'Site'}
                >
                  {isListing ? (
                    <ExternalLink data-icon="inline-start" />
                  ) : (
                    <Globe data-icon="inline-start" />
                  )}
                  {isListing ? 'Ver anúncio' : 'Site'}
                </a>
              </Button>
            )}
            {candidato.tem_24h && (
              <Badge variant="success" className="gap-1 h-7 px-2.5">
                <Clock size={11} />
                24h
              </Badge>
            )}
          </div>
        )}

        {/* Scores */}
        <div className="space-y-2 py-2 border-y border-border">
          <ScoreGauge value={candidato.score_geoscout} label="GeoScout" />
          <ScoreGauge value={candidato.score_ancoragem} label="Ancoragem" />
          {scoreGeral != null && (
            <ScoreGauge value={scoreGeral} label="Score Geral (4 dim)" />
          )}
        </div>

        {/* Polos geradores */}
        {candidato.polos_geradores && candidato.polos_geradores.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono mb-1.5">
              Polos próximos
            </p>
            <ul className="space-y-0.5">
              {candidato.polos_geradores.slice(0, 3).map((polo, i) => (
                <li key={i} className="text-xs flex items-baseline gap-1.5">
                  <span aria-hidden className="text-muted-foreground">·</span>
                  <span className="text-muted-foreground">{polo}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Motivo / aviso */}
        {candidato.motivo && (
          <p className="text-xs italic text-muted-foreground bg-muted/40 rounded p-2 flex items-start gap-1.5 mt-auto">
            <AlertCircle size={12} className="mt-0.5 shrink-0" />
            <span>{candidato.motivo}</span>
          </p>
        )}
      </div>
    </article>
  )
}
