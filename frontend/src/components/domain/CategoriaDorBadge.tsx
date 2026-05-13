/**
 * CategoriaDorBadge — exibe a categoria semântica de dor classificada pelo
 * Gemini Flash em batch (A3a, taxonomia DORES_TAXONOMIA, 14 categorias).
 *
 * Cada categoria tem cor distinta + label PT-BR humanizado.
 * Aceita prop `sinal` opcional pra modular intensidade (negativo = mais saturado).
 */
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { CategoriaDor, SinalReview } from '@/types/domain'

const DOR_CONFIG: Record<
  CategoriaDor,
  { label: string; bg: string; emoji?: string }
> = {
  lotacao: { label: 'Lotação', bg: 'bg-dor-lotacao', emoji: '👥' },
  equipamento_problema: { label: 'Equipamento', bg: 'bg-dor-equipamento', emoji: '🔧' },
  climatizacao: { label: 'Climatização', bg: 'bg-dor-climatizacao', emoji: '❄️' },
  limpeza_higiene: { label: 'Limpeza', bg: 'bg-dor-limpeza', emoji: '🧹' },
  atendimento_ruim: { label: 'Atendimento', bg: 'bg-dor-atendimento', emoji: '🗣️' },
  preco_alto: { label: 'Preço alto', bg: 'bg-dor-preco', emoji: '💰' },
  contrato_abusivo: { label: 'Contrato abusivo', bg: 'bg-dor-contrato', emoji: '📋' },
  estacionamento: { label: 'Estacionamento', bg: 'bg-dor-estacionamento', emoji: '🅿️' },
  estrutura_envelhecida: { label: 'Estrutura velha', bg: 'bg-dor-estrutura', emoji: '🏚️' },
  ruido_alto: { label: 'Ruído', bg: 'bg-dor-ruido', emoji: '🔊' },
  horarios_limitados: { label: 'Horários', bg: 'bg-dor-horarios', emoji: '🕐' },
  ausencia_servico: { label: 'Falta serviço', bg: 'bg-dor-servico', emoji: '➖' },
  seguranca: { label: 'Segurança', bg: 'bg-dor-seguranca', emoji: '🚨' },
  outra: { label: 'Outra', bg: 'bg-dor-outra' },
}

export interface CategoriaDorBadgeProps {
  categoria: CategoriaDor
  sinal?: SinalReview
  showEmoji?: boolean
  className?: string
}

export function CategoriaDorBadge({
  categoria,
  sinal,
  showEmoji = true,
  className,
}: CategoriaDorBadgeProps) {
  const cfg = DOR_CONFIG[categoria] ?? DOR_CONFIG.outra

  // Modula opacidade pela intensidade do sinal (reviews positivas têm cor mais suave)
  const opacityClass =
    sinal === 'positivo'
      ? 'opacity-50'
      : sinal === 'neutro'
        ? 'opacity-75'
        : 'opacity-100'

  return (
    <Badge
      className={cn(
        'border-transparent text-white gap-1 text-[10px] px-1.5 py-0',
        cfg.bg,
        opacityClass,
        className,
      )}
      aria-label={`Categoria: ${cfg.label}`}
    >
      {showEmoji && cfg.emoji && <span aria-hidden>{cfg.emoji}</span>}
      <span>{cfg.label}</span>
    </Badge>
  )
}
