/**
 * SectionHeader — padroniza headers de seção no viewer.
 *
 * Antes: cada seção usava emoji + tracking-wider inline, escala inconsistente
 * entre views. Agora: 1 componente com prop `icon` (Lucide) e tipografia
 * fixa (`text-sm font-semibold uppercase tracking-wider text-muted-foreground`).
 *
 * Suporta `suffix` (ex: pílula de fonte/data ao lado direito) e `description`
 * (linha auxiliar abaixo do título).
 */
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Separator } from '@/components/ui/separator'

export interface SectionHeaderProps {
  /** Título da seção (será uppercased via CSS). */
  title: string
  /** Ícone Lucide à esquerda do título. */
  icon?: LucideIcon
  /** Descrição auxiliar abaixo do título (1 linha). */
  description?: ReactNode
  /** Conteúdo flutuante à direita (chips, badges, link "ver tudo"). */
  suffix?: ReactNode
  /** Mostra Separator embaixo (default true). */
  withSeparator?: boolean
  className?: string
}

export function SectionHeader({
  title,
  icon: Icon,
  description,
  suffix,
  withSeparator = true,
  className,
}: SectionHeaderProps) {
  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          {Icon && <Icon size={14} aria-hidden />}
          <span>{title}</span>
        </h2>
        {suffix && <div className="flex items-center gap-2">{suffix}</div>}
      </div>
      {description && (
        <p className="text-xs text-muted-foreground/80">{description}</p>
      )}
      {withSeparator && <Separator className="mt-3" />}
    </div>
  )
}
