/**
 * Combobox — input com dropdown de sugestões.
 *
 * Custom em vez de cmdk + radix-popover (-2 deps). Suporta:
 * - Filtro client-side via prop `options` controlado pelo caller (não filtra
 *   sozinho — caller decide quais opções mostrar pra dado `value`).
 * - Keyboard nav: ↑/↓ navega, Enter seleciona, Esc fecha.
 * - Loading state via `isLoading` (não bloqueia input — só mostra placeholder
 *   "Buscando...").
 * - Vazio: callout opcional via `emptyMessage` (default oculto).
 * - Bind via `onSelect(option)` — caller decide o que fazer com a seleção.
 *
 * Não pretende ser shadcn Combobox completo. Atende ao caso do Form Novo
 * Relatório (município, bairro). Se algo mais complexo aparecer, migrar pra cmdk.
 */
import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { ChevronDown, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Input } from '@/components/ui/input'

export interface ComboboxOption<T = unknown> {
  /** Texto exibido na linha principal. */
  label: string
  /** Texto auxiliar opcional (cinza, embaixo ou ao lado). */
  description?: string
  /** Identifica unicamente a opção pra keys do React e onSelect. */
  value: string
  /** Payload arbitrário que volta no onSelect — útil pra passar IBGE id, place_id, etc. */
  payload?: T
}

export interface ComboboxProps<T = unknown> {
  /** Texto digitado pelo usuário (controlado). */
  inputValue: string
  /** Callback de mudança de input — caller dispara filtro/query. */
  onInputChange: (v: string) => void
  /** Lista de opções já filtrada pelo caller. */
  options: ComboboxOption<T>[]
  /** Acionado quando o usuário escolhe uma opção (click ou Enter). */
  onSelect: (option: ComboboxOption<T>) => void
  /** Placeholder do input. */
  placeholder?: string
  /** Mostra spinner; não desabilita o input. */
  isLoading?: boolean
  /** Mensagem opcional quando options está vazio mas input >= minChars. */
  emptyMessage?: ReactNode
  /** Mínimo de caracteres pra abrir dropdown (default 2). */
  minChars?: number
  /** Desabilita interação (form readonly, etc). */
  disabled?: boolean
  /** Forwarded para input — útil pra aria-invalid. */
  ariaInvalid?: boolean
  className?: string
}

export function Combobox<T = unknown>({
  inputValue,
  onInputChange,
  options,
  onSelect,
  placeholder,
  isLoading,
  emptyMessage,
  minChars = 2,
  disabled,
  ariaInvalid,
  className,
}: ComboboxProps<T>) {
  const [open, setOpen] = useState(false)
  const [activeIdx, setActiveIdx] = useState(0)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listId = useId()

  // Abre quando: foco aberto + não desabilitado + (input >= minChars OU há opções pré-carregadas).
  // O segundo termo permite mostrar lista inicial mesmo com input vazio
  // (útil pra Município logo após UF selecionada — lista alfabética dos primeiros 20).
  const shouldShow =
    open &&
    !disabled &&
    (inputValue.trim().length >= minChars || options.length > 0)

  useEffect(() => {
    setActiveIdx(0)
  }, [options.length, inputValue])

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setActiveIdx((i) => Math.min(i + 1, options.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIdx((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      if (shouldShow && options[activeIdx]) {
        e.preventDefault()
        onSelect(options[activeIdx])
        setOpen(false)
      }
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div ref={wrapperRef} className={cn('relative', className)}>
      <div className="relative">
        <Input
          ref={inputRef}
          value={inputValue}
          onChange={(e) => {
            onInputChange(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKey}
          placeholder={placeholder}
          disabled={disabled}
          aria-autocomplete="list"
          aria-expanded={shouldShow}
          aria-controls={listId}
          aria-invalid={ariaInvalid || undefined}
          className="pr-9"
        />
        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground">
          {isLoading ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <ChevronDown size={14} />
          )}
        </span>
      </div>

      {shouldShow && (
        <ul
          id={listId}
          role="listbox"
          className={cn(
            'absolute z-50 mt-1 max-h-72 w-full overflow-auto rounded-md border border-border bg-card text-card-foreground shadow-lg',
          )}
        >
          {options.length === 0 && !isLoading && (
            <li className="px-3 py-2 text-xs text-muted-foreground">
              {emptyMessage ?? 'Sem resultados'}
            </li>
          )}
          {options.length === 0 && isLoading && (
            <li className="px-3 py-2 text-xs text-muted-foreground flex items-center gap-2">
              <Loader2 size={12} className="animate-spin" /> Buscando…
            </li>
          )}
          {options.map((opt, idx) => (
            <li
              key={opt.value}
              role="option"
              aria-selected={idx === activeIdx}
              onMouseEnter={() => setActiveIdx(idx)}
              onMouseDown={(e) => {
                // mousedown (não click) pra preceder o blur do input
                e.preventDefault()
                onSelect(opt)
                setOpen(false)
              }}
              className={cn(
                'cursor-pointer px-3 py-2 text-sm transition-colors',
                idx === activeIdx
                  ? 'bg-muted text-foreground'
                  : 'hover:bg-muted/50',
              )}
            >
              <div className="font-medium">{opt.label}</div>
              {opt.description && (
                <div className="text-xs text-muted-foreground">
                  {opt.description}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
