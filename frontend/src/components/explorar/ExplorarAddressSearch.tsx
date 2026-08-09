import { useEffect, useId, useRef, useState } from 'react'
import { Loader2, Search } from 'lucide-react'
import { useDebounce } from '@/hooks/useDebounce'
import {
  useExplorarEnderecoAutocomplete,
  type ExplorarEnderecoSugestao,
} from '@/hooks/useExplorarEnderecoAutocomplete'
import { cn } from '@/lib/utils'
import { explorarChrome, useExplorarSite } from './explorar-chrome'
import { explorarAutocompleteListKind } from './explorarAutocompleteState'

export function ExplorarAddressSearch({
  query,
  biasLat,
  biasLng,
  onQueryChange,
  onPick,
  onSubmitFree,
  className,
}: {
  query: string
  biasLat?: number
  biasLng?: number
  onQueryChange: (v: string) => void
  onPick: (s: ExplorarEnderecoSugestao) => void
  onSubmitFree: () => void
  className?: string
}) {
  const debounced = useDebounce(query, 450)
  const {
    data: sugestoes = [],
    isFetching,
    isError,
  } = useExplorarEnderecoAutocomplete(debounced, biasLat, biasLng)
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const wrapRef = useRef<HTMLFormElement>(null)
  const chrome = explorarChrome(useExplorarSite())
  const listId = useId()
  const show = open && query.trim().length >= 3
  const listKind = explorarAutocompleteListKind({
    query,
    debounced,
    isFetching,
    suggestionCount: sugestoes.length,
    isError,
  })

  useEffect(() => {
    setActive(0)
  }, [sugestoes.length, debounced])

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  function pick(s: ExplorarEnderecoSugestao) {
    onQueryChange(s.textoCompleto || s.bairro)
    onPick(s)
    setOpen(false)
  }

  return (
    <form
      ref={wrapRef}
      onSubmit={(e) => {
        e.preventDefault()
        if (show && sugestoes[active]) {
          pick(sugestoes[active])
          return
        }
        onSubmitFree()
        setOpen(false)
      }}
      className={cn('pointer-events-auto w-full', className)}
    >
      <div className="flex gap-2">
        <div className="relative min-w-0 flex-1">
          <input
            value={query}
            onChange={(e) => {
              onQueryChange(e.target.value)
              setOpen(true)
            }}
            onFocus={() => setOpen(true)}
            onKeyDown={(e) => {
              if (!show) return
              if (e.key === 'ArrowDown') {
                e.preventDefault()
                setActive((i) => Math.min(i + 1, Math.max(sugestoes.length - 1, 0)))
              } else if (e.key === 'ArrowUp') {
                e.preventDefault()
                setActive((i) => Math.max(i - 1, 0))
              } else if (e.key === 'Escape') {
                setOpen(false)
              }
            }}
            className={cn(
              chrome,
              'h-12.5 w-full rounded-lg border py-3 pl-10 pr-10 text-base font-normal shadow-md outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-primary',
            )}
            placeholder="Digite um endereço..."
            autoComplete="off"
            aria-autocomplete="list"
            aria-expanded={show}
            aria-controls={listId}
          />
          <Search className="pointer-events-none absolute left-3 top-1/2 size-5 -translate-y-1/2 text-muted-foreground" />
          {listKind === 'loading' && (
            <Loader2 className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />
          )}
          {show && (
            <ul
              id={listId}
              role="listbox"
              className={cn(
                chrome,
                'absolute z-50 mt-1 max-h-72 w-full overflow-auto rounded-lg border shadow-lg',
              )}
            >
              {listKind === 'loading' && (
                <li className="px-3 py-2 text-xs text-muted-foreground">Buscando…</li>
              )}
              {listKind === 'error' && (
                <li className="px-3 py-2 text-xs text-muted-foreground">
                  Não deu pra buscar agora — Enter ainda pesquisa o texto
                </li>
              )}
              {listKind === 'empty' && (
                <li className="px-3 py-2 text-xs text-muted-foreground">
                  Sem sugestões — Enter busca o texto digitado
                </li>
              )}
              {sugestoes.map((s, idx) => (
                <li
                  key={s.placeId || s.textoCompleto || `${s.bairro}-${idx}`}
                  role="option"
                  aria-selected={idx === active}
                  onMouseEnter={() => setActive(idx)}
                  onMouseDown={(e) => {
                    e.preventDefault()
                    pick(s)
                  }}
                  className={cn(
                    'cursor-pointer px-3 py-2 text-sm',
                    idx === active ? 'bg-secondary text-foreground' : 'hover:bg-muted',
                  )}
                >
                  <div className="font-medium">{s.bairro || s.textoCompleto}</div>
                  {s.contexto ? (
                    <div className="text-xs text-muted-foreground">{s.contexto}</div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
        <button
          type="submit"
          className={cn(
                chrome,
            'h-12.5 shrink-0 rounded-lg border px-3 text-sm font-semibold shadow-md hover:brightness-110',
          )}
        >
          Ir
        </button>
      </div>
    </form>
  )
}
