/**
 * ReviewItem — uma review de aluno com quote, autor, rating e CategoriaDorBadge.
 *
 * Aceita ambos formatos do JSON (reviews_traduzidas e reviews).
 * Se a review tinha original em outro idioma, mostra dica de idioma.
 */
import { Star } from 'lucide-react'
import { CategoriaDorBadge } from './CategoriaDorBadge'
import { cn } from '@/lib/utils'
import type { ReviewJSON } from '@/hooks/useRelatorioDetail'
import type { CategoriaDor, SinalReview } from '@/types/domain'

export interface ReviewItemProps {
  review: ReviewJSON
  className?: string
}

function StarsRating({ rating }: { rating: number }) {
  return (
    <span className="inline-flex items-center gap-0.5" aria-label={`${rating} estrelas`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          size={10}
          className={
            i < rating
              ? 'fill-veredito-ressalvas text-veredito-ressalvas'
              : 'text-muted-foreground/30'
          }
        />
      ))}
    </span>
  )
}

export function ReviewItem({ review, className }: ReviewItemProps) {
  const quote = review.quote_pt_br ?? review.quote_curta ?? review.quote_original ?? ''
  const rating = review.rating ?? 3
  const autor = review.autor ?? 'Anônimo'
  const data = review.data_relativa ?? ''
  const idioma = review.idioma_original
  const isTranslated =
    review.quote_pt_br && review.quote_original && idioma && idioma !== 'português'

  const categoria = (review.categoria_dor ?? 'outra') as CategoriaDor
  const sinal = review.sinal as SinalReview | undefined

  if (!quote.trim()) return null

  return (
    <div className={cn('space-y-1.5', className)}>
      <blockquote className="text-sm italic text-foreground/90 leading-snug">
        &ldquo;{quote}&rdquo;
      </blockquote>
      <div className="flex items-center gap-2 flex-wrap text-[10px] font-mono text-muted-foreground">
        <span>{autor}</span>
        <span aria-hidden>·</span>
        <StarsRating rating={rating} />
        {data && (
          <>
            <span aria-hidden>·</span>
            <span>{data}</span>
          </>
        )}
        {isTranslated && (
          <>
            <span aria-hidden>·</span>
            <span className="opacity-60">[original em {idioma}]</span>
          </>
        )}
        <CategoriaDorBadge categoria={categoria} sinal={sinal} />
      </div>
    </div>
  )
}
