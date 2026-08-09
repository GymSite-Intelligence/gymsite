import { useEffect, useRef } from 'react'
import { TURNSTILE_SITEKEY, loadTurnstileScript } from '@/lib/turnstile'

export function TurnstileWidget({
  onToken,
  className,
}: {
  onToken: (token: string) => void
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const widgetId = useRef<string | null>(null)

  useEffect(() => {
    let cancelado = false
    loadTurnstileScript()
      .then(() => {
        const ts = (window as Window & { turnstile?: { render: Function; reset: Function; remove: Function } })
          .turnstile
        if (cancelado || !ref.current || !ts || widgetId.current) return
        widgetId.current = ts.render(ref.current, {
          sitekey: TURNSTILE_SITEKEY,
          appearance: 'always',
          theme: 'dark',
          action: 'turnstile-spin-v2',
          callback: (t: string) => onToken(t),
          'expired-callback': () => {
            try {
              ts.reset(widgetId.current)
            } catch {
              /* noop */
            }
          },
          'error-callback': () => {
            try {
              ts.reset(widgetId.current)
            } catch {
              /* noop */
            }
            return true
          },
        })
      })
      .catch(() => onToken(''))
    return () => {
      cancelado = true
      const ts = (window as Window & { turnstile?: { remove: Function } }).turnstile
      if (widgetId.current && ts) {
        try {
          ts.remove(widgetId.current)
        } catch {
          /* noop */
        }
      }
    }
  }, [onToken])

  return <div ref={ref} className={className} />
}
