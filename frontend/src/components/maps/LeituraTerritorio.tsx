/**
 * R2 — Card "Leitura do territorio".
 *
 * Recebe um resumo AGREGADO do recorte visivel do mapa (cidade, contagens por
 * oceano, top bairros, vereditos) e chama POST /api/maps/territorio-read, que
 * devolve uma leitura curta de negocio gerada por IA.
 *
 * Guard-rails de custo/qualidade:
 * - debounce (so dispara apos o usuario parar de mexer no mapa/filtros);
 * - cache em memoria por hash do resumo (evita repagar a mesma vista);
 * - estados de loading/erro; disclaimer fixo de "leitura assistida por IA".
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { API_BASE } from '@/lib/supabase'

export interface ResumoTerritorio {
  cidade: string
  bbox?: { north: number; south: number; east: number; west: number } | null
  counts: Record<string, number>
  top_bairros: string[]
  vereditos: Record<string, number>
}

export interface LeituraTerritorioData {
  titulo: string
  leitura: string
  recomendacao: string
  confianca: 'alta' | 'media' | 'baixa' | string
}

function territorioReadUrl(): string {
  const devBase = (import.meta.env.VITE_API_BASE as string | undefined)?.trim()
  if (import.meta.env.DEV && !devBase) {
    return '/api/maps/territorio-read'
  }
  const base = (devBase || API_BASE).replace(/\/$/, '')
  return `${base}/api/maps/territorio-read`
}

const _cache = new Map<string, LeituraTerritorioData>()

function hashResumo(r: ResumoTerritorio): string {
  // chave estavel (ordena nada complexo; resumo ja e pequeno)
  return JSON.stringify({
    c: r.cidade,
    n: r.counts,
    b: [...r.top_bairros].sort(),
    v: r.vereditos,
  })
}

function vazio(r: ResumoTerritorio): boolean {
  const totalCounts = Object.values(r.counts || {}).reduce((a, b) => a + b, 0)
  return totalCounts === 0 && (r.top_bairros?.length ?? 0) === 0
}

/** Hook: leitura do territorio com debounce + cache. So dispara em interacao. */
export function useTerritorioRead(resumo: ResumoTerritorio | null, enabled = true) {
  const [data, setData] = useState<LeituraTerritorioData | null>(null)
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const chave = useMemo(
    () => (resumo && !vazio(resumo) ? hashResumo(resumo) : null),
    [resumo],
  )

  useEffect(() => {
    if (!enabled || !resumo || !chave) {
      setData(null)
      return
    }
    const cacheado = _cache.get(chave)
    if (cacheado) {
      setData(cacheado)
      setErro(null)
      setLoading(false)
      return
    }
    if (timer.current) clearTimeout(timer.current)
    let cancelado = false
    setLoading(true)
    setErro(null)
    timer.current = setTimeout(async () => {
      try {
        const res = await fetch(territorioReadUrl(), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(resumo),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = (await res.json()) as LeituraTerritorioData
        if (cancelado) return
        _cache.set(chave, json)
        setData(json)
      } catch (e) {
        if (cancelado) return
        setErro('Nao foi possivel gerar a leitura agora.')
        setData(null)
      } finally {
        if (!cancelado) setLoading(false)
      }
    }, 900)
    return () => {
      cancelado = true
      if (timer.current) clearTimeout(timer.current)
    }
  }, [enabled, chave, resumo])

  return { data, loading, erro }
}

const CONFIANCA_LABEL: Record<string, string> = {
  alta: 'Confianca alta',
  media: 'Confianca media',
  baixa: 'Confianca baixa',
}

export function LeituraTerritorio({
  resumo,
  enabled = true,
}: {
  resumo: ResumoTerritorio | null
  enabled?: boolean
}) {
  const { data, loading, erro } = useTerritorioRead(resumo, enabled)

  if (!resumo || (!loading && !data && !erro)) return null

  return (
    <div className="rounded-lg border bg-card p-3 text-sm shadow-sm">
      <div className="mb-1 flex items-center justify-between gap-2">
        <h3 className="font-semibold">Leitura do territorio</h3>
        {data?.confianca && (
          <span className="rounded-full border px-2 py-0.5 text-[10px] uppercase text-muted-foreground">
            {CONFIANCA_LABEL[data.confianca] ?? data.confianca}
          </span>
        )}
      </div>

      {loading && (
        <div className="space-y-2" aria-busy="true">
          <div className="h-3 w-3/4 animate-pulse rounded bg-muted" />
          <div className="h-3 w-full animate-pulse rounded bg-muted" />
          <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
        </div>
      )}

      {!loading && erro && (
        <p className="text-xs text-muted-foreground">{erro}</p>
      )}

      {!loading && data && (
        <div className="space-y-1.5">
          {data.titulo && <p className="font-medium">{data.titulo}</p>}
          <p className="text-xs leading-snug text-muted-foreground">{data.leitura}</p>
          {data.recomendacao && (
            <p className="text-xs leading-snug">
              <span className="font-medium">Recomendacao: </span>
              {data.recomendacao}
            </p>
          )}
        </div>
      )}

      <p className="mt-2 text-[10px] text-muted-foreground">
        Leitura assistida por IA sobre os dados do recorte.
      </p>
    </div>
  )
}
