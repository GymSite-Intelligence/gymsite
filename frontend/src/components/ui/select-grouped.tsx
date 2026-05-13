/**
 * SelectGrouped — dropdown de seleção fechada com suporte a grupos.
 *
 * Por que existe (e não usamos <select> nativo):
 *   Chrome Windows ignora estilos em <option> e <optgroup> em muitos casos —
 *   nem `color-scheme: dark` no html resolve. O popup nativo herda cor do
 *   sistema (branco) e nossas opções viram cinza claro sobre branco ilegível.
 *
 *   Este componente reusa DropdownMenu (Radix) já instalado, dá controle
 *   total via CSS do tema dark e mantém UX equivalente ao select nativo
 *   (clique abre, seta seleciona, click fora fecha, keyboard nav).
 *
 * Não pretende ser shadcn Select completo. Atende ao caso do NovoRelatorioPage
 * (estado, tipo_negocio, faixa_etaria, genero_alvo).
 */
import { useMemo } from 'react'
import { Check, ChevronDown } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'

export interface SelectOption {
  value: string
  label: string
  /** Texto opcional secundário (cinza, ao lado). */
  description?: string
  disabled?: boolean
}

export interface SelectGroup {
  /** Header textual do grupo (opcional — se omitido, renderiza ungrouped). */
  label?: string
  options: SelectOption[]
}

export interface SelectGroupedProps {
  value: string | undefined
  onChange: (value: string) => void
  /** Lista flat (sem grupos) OU agrupada. Se passar `groups`, usa estes. */
  options?: SelectOption[]
  groups?: SelectGroup[]
  placeholder?: string
  disabled?: boolean
  ariaInvalid?: boolean
  className?: string
  /** Altura máxima do popup antes de scrollar. Default 320px. */
  maxHeight?: number | string
}

export function SelectGrouped({
  value,
  onChange,
  options,
  groups,
  placeholder = 'Selecione…',
  disabled,
  ariaInvalid,
  className,
  maxHeight = 320,
}: SelectGroupedProps) {
  const finalGroups: SelectGroup[] = useMemo(() => {
    if (groups && groups.length > 0) return groups
    if (options && options.length > 0) return [{ options }]
    return []
  }, [groups, options])

  const labelDoSelecionado = useMemo(() => {
    for (const g of finalGroups) {
      const found = g.options.find((o) => o.value === value)
      if (found) return found.label
    }
    return undefined
  }, [finalGroups, value])

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        disabled={disabled}
        aria-invalid={ariaInvalid || undefined}
        className={cn(
          'h-9 w-full rounded-md border border-border bg-transparent px-3 text-sm',
          'flex items-center justify-between gap-2',
          'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'data-[state=open]:ring-1 data-[state=open]:ring-primary',
          'aria-invalid:border-destructive',
          className,
        )}
      >
        <span
          className={cn(
            'truncate text-left',
            !labelDoSelecionado && 'text-muted-foreground',
          )}
        >
          {labelDoSelecionado ?? placeholder}
        </span>
        <ChevronDown size={14} className="text-muted-foreground flex-shrink-0" />
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="start"
        sideOffset={4}
        className="w-[var(--radix-dropdown-menu-trigger-width)] min-w-[200px]"
        style={{ maxHeight, overflowY: 'auto' }}
      >
        {finalGroups.map((g, gi) => (
          <div key={g.label ?? `g-${gi}`}>
            {g.label && (
              <>
                {gi > 0 && <DropdownMenuSeparator />}
                <DropdownMenuLabel className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground py-1.5">
                  {g.label}
                </DropdownMenuLabel>
              </>
            )}
            {g.options.map((o) => {
              const selecionado = o.value === value
              return (
                <DropdownMenuItem
                  key={o.value}
                  disabled={o.disabled}
                  onSelect={() => onChange(o.value)}
                  className={cn(
                    'flex items-center justify-between gap-2',
                    selecionado && 'bg-muted/50',
                  )}
                >
                  <div className="flex flex-col leading-tight min-w-0">
                    <span className="truncate">{o.label}</span>
                    {o.description && (
                      <span className="text-[10px] text-muted-foreground font-mono truncate">
                        {o.description}
                      </span>
                    )}
                  </div>
                  {selecionado && (
                    <Check size={12} className="text-primary flex-shrink-0" />
                  )}
                </DropdownMenuItem>
              )
            })}
          </div>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
