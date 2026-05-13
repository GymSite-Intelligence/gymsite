/**
 * TextoSecao — wrapper genérico pra renderizar parágrafos de texto
 * gerados pelo A6 (posicionamento_recomendado, resumo_executivo,
 * justificativa_financeira, decisão_recomendada).
 *
 * Usa <p> com quebras de linha preservadas via white-space: pre-line.
 *
 * UI Lote 5: prop `collapsible` envelopa o conteúdo em Collapsible com
 * chevron rotativo no header.
 */
import { useState, type ReactNode } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'

export interface TextoSecaoProps {
  title: string
  emoji?: string
  texto: string | null | undefined
  variant?: 'default' | 'highlight' | 'warning'
  /** Conteúdo extra renderizado abaixo do texto (ex: lista de alertas) */
  children?: ReactNode
  className?: string
  /** Quando true, o conteúdo pode ser colapsado clicando no header. */
  collapsible?: boolean
  /** Estado inicial do collapsible (default: true). */
  defaultOpen?: boolean
}

export function TextoSecao({
  title,
  emoji,
  texto,
  variant = 'default',
  children,
  className,
  collapsible = false,
  defaultOpen = true,
}: TextoSecaoProps) {
  if (!texto && !children) return null

  const containerClass = cn(
    'rounded-lg border p-5 space-y-3',
    variant === 'default' && 'border-border bg-card',
    variant === 'highlight' && 'border-primary/40 bg-primary/5',
    variant === 'warning' && 'border-veredito-reprovado/40 bg-veredito-reprovado/5',
    className,
  )

  const headerClass =
    'text-xs uppercase tracking-wider text-muted-foreground font-mono font-medium flex items-center gap-2'

  const body = (
    <>
      {texto && (
        <p
          className="text-sm leading-relaxed whitespace-pre-line"
          style={{ overflowWrap: 'anywhere' }}
        >
          {texto}
        </p>
      )}
      {children}
    </>
  )

  if (!collapsible) {
    return (
      <div className={containerClass}>
        <h3 className={headerClass}>
          {emoji && <span aria-hidden>{emoji}</span>}
          <span>{title}</span>
        </h3>
        {body}
      </div>
    )
  }

  return (
    <CollapsibleTextoSecao
      containerClass={containerClass}
      headerClass={headerClass}
      title={title}
      emoji={emoji}
      defaultOpen={defaultOpen}
    >
      {body}
    </CollapsibleTextoSecao>
  )
}

function CollapsibleTextoSecao({
  containerClass,
  headerClass,
  title,
  emoji,
  defaultOpen,
  children,
}: {
  containerClass: string
  headerClass: string
  title: string
  emoji?: string
  defaultOpen: boolean
  children: ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <Collapsible open={open} onOpenChange={setOpen} asChild>
      <div className={containerClass}>
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className={cn(
              headerClass,
              'w-full justify-between hover:text-foreground transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm',
            )}
          >
            <span className="flex items-center gap-2">
              {emoji && <span aria-hidden>{emoji}</span>}
              <span>{title}</span>
            </span>
            <ChevronDown
              size={14}
              className={cn(
                'transition-transform',
                open ? 'rotate-180' : 'rotate-0',
              )}
            />
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-3">{children}</CollapsibleContent>
      </div>
    </Collapsible>
  )
}
