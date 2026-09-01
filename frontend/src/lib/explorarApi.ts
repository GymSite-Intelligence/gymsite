export const PROD_API_BASE = 'https://api.getgymsite.com.br'

export function isLoopbackApi(base: string): boolean {
  try {
    const host = new URL(base).hostname
    return host === '127.0.0.1' || host === 'localhost'
  } catch {
    return false
  }
}

function primaryApiBase(): string {
  const fromEnv = (import.meta.env.VITE_API_BASE as string | undefined)?.trim()
  return (fromEnv || PROD_API_BASE).replace(/\/$/, '')
}

export async function fetchExplorar(path: string, init?: RequestInit): Promise<Response> {
  const pathNorm = path.startsWith('/') ? path : `/${path}`
  const primary = primaryApiBase()
  try {
    return await fetch(`${primary}${pathNorm}`, init)
  } catch (err) {
    if (!isLoopbackApi(primary)) throw err
    return fetch(`${PROD_API_BASE}${pathNorm}`, init)
  }
}
