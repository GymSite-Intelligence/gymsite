import { useEffect, useState } from 'react'

/** Retorna `value` defasado em `delay` ms. Útil pra throttle de inputs antes
 * de disparar queries de autocomplete. */
export function useDebounce<T>(value: T, delay: number = 250): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}
