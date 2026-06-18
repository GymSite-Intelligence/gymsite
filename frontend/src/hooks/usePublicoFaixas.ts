/**
 * usePublicoFaixas — segmentos de público-alvo (idade) do catálogo backend.
 *
 * MESMA fonte que o relatório (catalogos_metodologia 'publico_faixa'): form e
 * relatório falam a mesma língua (Jovem/Core/Maduro/Silver). Lista pequena e
 * estável → cache longo. Fallback rotulado se o backend não responder.
 */
import { useQuery } from '@tanstack/react-query'
import { API_BASE } from '@/lib/supabase'

export interface PublicoFaixa {
  faixa: string // ex: "25-39" | "60+"
  nome: string // ex: "Core" | "Silver"
  min: number
  max: number
  ordem: number
}

// Fallback rotulado (espelha o seed do catálogo) — só se o backend cair.
const FALLBACK: PublicoFaixa[] = [
  { faixa: '15-24', nome: 'Jovem', min: 15, max: 24, ordem: 1 },
  { faixa: '25-39', nome: 'Core', min: 25, max: 39, ordem: 2 },
  { faixa: '40-59', nome: 'Maduro', min: 40, max: 59, ordem: 3 },
  { faixa: '60+', nome: 'Silver', min: 60, max: 120, ordem: 4 },
]

function publicoFaixasUrl(): string {
  const devBase = (import.meta.env.VITE_API_BASE as string | undefined)?.trim()
  if (import.meta.env.DEV && !devBase) return '/api/config/publico-faixas'
  const base = (devBase || API_BASE).replace(/\/$/, '')
  return `${base}/api/config/publico-faixas`
}

async function fetchPublicoFaixas(): Promise<PublicoFaixa[]> {
  const res = await fetch(publicoFaixasUrl(), { credentials: 'include' })
  if (!res.ok) return FALLBACK
  const data = (await res.json()) as { faixas?: PublicoFaixa[] }
  const faixas = (data.faixas || []).filter((f) => f.faixa && f.nome)
  return faixas.length ? faixas : FALLBACK
}

export function usePublicoFaixas() {
  return useQuery({
    queryKey: ['publico-faixas'],
    queryFn: fetchPublicoFaixas,
    staleTime: 60 * 60 * 1000, // 1h — catálogo muda raramente
    placeholderData: FALLBACK,
  })
}

/**
 * Range envolvente a partir dos segmentos marcados → string que o pipeline
 * consome (publico_alvo). Ex: [Core, Maduro] → "25-59"; [Silver] → "60+".
 */
export function faixasParaRange(
  selecionadas: string[],
  faixas: PublicoFaixa[],
): string {
  const escolhidas = faixas
    .filter((f) => selecionadas.includes(f.faixa))
    .sort((a, b) => a.ordem - b.ordem)
  if (!escolhidas.length) return ''
  const min = Math.min(...escolhidas.map((f) => f.min))
  const topo = escolhidas[escolhidas.length - 1]
  // Segmento aberto no topo (ex: 60+) → "min+", senão "min-max".
  const aberto = faixas.every((f) => f.ordem <= topo.ordem || !selecionadas.includes(f.faixa))
  if (topo.faixa.includes('+') && aberto) return `${min}+`
  const max = Math.max(...escolhidas.map((f) => f.max))
  return `${min}-${max}`
}

/** Range "25-59" / "60+" → segmentos cobertos (pré-seleção no retry/edição). */
export function rangeParaFaixas(
  range: string,
  faixas: PublicoFaixa[],
): string[] {
  const m = String(range || '').match(/^(\d+)\s*[-+]?\s*(\d+)?/)
  if (!m) return []
  const lo = Number(m[1])
  const hi = m[2] ? Number(m[2]) : 120
  return faixas.filter((f) => f.max >= lo && f.min <= hi).map((f) => f.faixa)
}
