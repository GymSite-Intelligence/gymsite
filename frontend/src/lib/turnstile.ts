const SRC = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'

export const TURNSTILE_SITEKEY =
  (import.meta.env.VITE_TURNSTILE_SITEKEY as string) || '0x4AAAAAADouAKkqNK0u3OaG'

let loaded: Promise<void> | null = null

export function loadTurnstileScript(): Promise<void> {
  if (loaded) return loaded
  loaded = new Promise((resolve, reject) => {
    if ((window as Window & { turnstile?: unknown }).turnstile) return resolve()
    const existente = document.querySelector<HTMLScriptElement>(
      'script[src^="https://challenges.cloudflare.com/turnstile/v0/api.js"]',
    )
    if (existente) {
      existente.addEventListener('load', () => resolve())
      return
    }
    const s = document.createElement('script')
    s.src = SRC
    s.async = true
    s.defer = true
    s.setAttribute('data-cfasync', 'false')
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('Falha ao carregar o Turnstile'))
    document.head.appendChild(s)
  })
  return loaded
}
