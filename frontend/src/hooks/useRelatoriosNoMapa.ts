/**
 * useRelatoriosNoMapa — agrega lat/lng dos relatórios pra renderizar pins.
 *
 * Faz 2 queries Supabase:
 *   1. `useRelatorios` — lista resumo com filtros
 *   2. `candidatos` — top 1 (posicao=1) de cada relatório, com lat/lng
 *
 * Quando USE_MOCKS=true, cai no fallback antigo que lia RAW_MOCKS[i].top_3_candidatos[0].
 */
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useRelatorios, type RelatoriosFilters } from './useRelatorios'
import { useAuth } from '@/lib/auth'
import { filterRelatorioUuids } from '@/lib/relatorio-id'
import { supabase } from '@/lib/supabase'
import { RAW_MOCKS, USE_MOCKS } from '@/mocks'
import type { Veredito } from '@/types/domain'

export interface PinRelatorio {
  id: string
  lat: number
  lng: number
  cidade: string
  bairro: string
  veredito: Veredito
  score_top1: number | null
  score_geoscout: number | null
  modelo_recomendado: string | null
  candidato_nome: string
  candidato_endereco: string
  /** URL Street View Static gerada pelo A1 GeoScout (640x400 c/ key). */
  street_view_url: string | null
}

interface TopCandidatoRow {
  relatorio_id: string
  nome: string | null
  endereco: string | null
  lat: number | string | null
  lng: number | string | null
  score_geoscout: number | string | null
  street_view_url: string | null
}

export function useRelatoriosNoMapa(filters: RelatoriosFilters = {}) {
  const { user } = useAuth()
  const { data: resumos, isLoading: loadingResumos } = useRelatorios(filters)
  const ids = useMemo(() => filterRelatorioUuids((resumos ?? []).map((r) => r.id)), [resumos])

  // Top 1 candidato (posicao=1) de cada relatório visível — só os com lat/lng.
  // Query rola só quando temos IDs e estamos logados (RLS filtra por org).
  const { data: topByRelatorio, isLoading: loadingTops } = useQuery({
    queryKey: ['mapa-top1', user?.id ?? 'anon', ids],
    enabled: !USE_MOCKS && !!user && ids.length > 0,
    meta: { silent: true },
    queryFn: async (): Promise<Map<string, TopCandidatoRow>> => {
      const { data, error } = await supabase
        .from('candidatos')
        .select(
          'relatorio_id, nome, endereco, lat, lng, score_geoscout, street_view_url',
        )
        .in('relatorio_id', ids)
        .eq('posicao', 1)
        .not('lat', 'is', null)
      if (error) throw new Error(`Supabase: ${error.message}`)
      const map = new Map<string, TopCandidatoRow>()
      for (const row of (data ?? []) as TopCandidatoRow[]) {
        map.set(row.relatorio_id, row)
      }
      return map
    },
  })

  const pins = useMemo<PinRelatorio[]>(() => {
    if (!resumos) return []

    // Fallback mocks dev (USE_MOCKS=true)
    if (USE_MOCKS) {
      const rawById = new Map(RAW_MOCKS.map((r) => [r.id, r]))
      const out: PinRelatorio[] = []
      for (const resumo of resumos) {
        const raw = rawById.get(resumo.id)
        if (!raw) continue
        // biome-ignore lint/suspicious/noExplicitAny: top_3_candidatos não tipado no RawRelatorioJSON
        const top = ((raw.output_consolidado as any)?.top_3_candidatos ?? [])[0]
        const lat = top?.lat
        const lng = top?.lng
        if (
          typeof lat !== 'number' ||
          typeof lng !== 'number' ||
          !Number.isFinite(lat) ||
          !Number.isFinite(lng)
        ) {
          continue
        }
        out.push({
          id: resumo.id,
          lat,
          lng,
          cidade: resumo.cidade,
          bairro: resumo.bairro,
          veredito: resumo.veredito ?? 'INVESTIGAR MAIS',
          score_top1: resumo.score_top1_candidato,
          score_geoscout: top?.score_geoscout ?? null,
          modelo_recomendado: resumo.modelo_recomendado,
          candidato_nome: top?.nome ?? '—',
          candidato_endereco: top?.endereco ?? '',
          street_view_url:
            typeof top?.street_view_url === 'string' && top.street_view_url
              ? top.street_view_url
              : null,
        })
      }
      return out
    }

    // Modo real: usa o map de top1 candidato do Supabase
    if (!topByRelatorio) return []
    const out: PinRelatorio[] = []
    for (const resumo of resumos) {
      const top = topByRelatorio.get(resumo.id)
      if (!top) continue
      const lat = typeof top.lat === 'string' ? parseFloat(top.lat) : top.lat
      const lng = typeof top.lng === 'string' ? parseFloat(top.lng) : top.lng
      if (
        lat == null ||
        lng == null ||
        !Number.isFinite(lat) ||
        !Number.isFinite(lng)
      ) {
        continue
      }
      const scoreGeo =
        typeof top.score_geoscout === 'string'
          ? parseFloat(top.score_geoscout)
          : top.score_geoscout
      out.push({
        id: resumo.id,
        lat,
        lng,
        cidade: resumo.cidade,
        bairro: resumo.bairro,
        veredito: resumo.veredito ?? 'INVESTIGAR MAIS',
        score_top1: resumo.score_top1_candidato,
        score_geoscout: Number.isFinite(scoreGeo as number)
          ? (scoreGeo as number)
          : null,
        modelo_recomendado: resumo.modelo_recomendado,
        candidato_nome: top.nome ?? '—',
        candidato_endereco: top.endereco ?? '',
        street_view_url: top.street_view_url ?? null,
      })
    }
    return out
  }, [resumos, topByRelatorio])

  return {
    pins,
    isLoading: loadingResumos || loadingTops,
    total: pins.length,
    semCoordenadas: (resumos?.length ?? 0) - pins.length,
  }
}

/**
 * Cluster de pins co-localizados (mesma lat/lng dentro de uma tolerância).
 * Quando 2+ relatórios analisaram o mesmo Top 1 candidato (mesmo imóvel
 * ou imóvel muito próximo), os marcadores sobrepostos viram 1 com badge.
 */
export interface PinCluster {
  /** lat/lng representativo (do primeiro pin do cluster). */
  lat: number
  lng: number
  /** Lista dos pins agrupados — sempre tem pelo menos 1. */
  pins: PinRelatorio[]
  /** Veredito "dominante" do cluster (do pin de maior score) pra cor do pin. */
  veredito_representativo: Veredito
}

/**
 * Tolerância de agrupamento por nível de zoom.
 *
 * Em zoom baixo (Brasil inteiro, ~z5) pins a 10km de distância parecem
 * sobrepostos. Em zoom alto (rua, ~z16) só sobrepõem se estiverem no
 * mesmo prédio. Heurística:
 *
 *   z5  → 0.5°    ~55km (Brasil)
 *   z8  → 0.05°   ~5km  (cidades vizinhas viram 1 cluster)
 *   z11 → 0.005°  ~500m (bairros viram 1 cluster)
 *   z14 → 0.0005° ~50m  (mesma quadra)
 *   z16+→ 0.0001° ~10m  (mesmo endereço)
 */
export function tolerancePorZoom(zoom: number): number {
  if (zoom <= 5) return 0.5
  if (zoom <= 8) return 0.05
  if (zoom <= 11) return 0.005
  if (zoom <= 14) return 0.0005
  return 0.0001
}

/** Agrupa pins que estão a ≤ `tolDegrees` de distância (default ~10m em lat). */
export function agruparPinsCoLocalizados(
  pins: PinRelatorio[],
  tolDegrees = 0.0001,
): PinCluster[] {
  const clusters: PinCluster[] = []
  for (const pin of pins) {
    const existente = clusters.find(
      (c) =>
        Math.abs(c.lat - pin.lat) <= tolDegrees &&
        Math.abs(c.lng - pin.lng) <= tolDegrees,
    )
    if (existente) {
      existente.pins.push(pin)
      // Recalcula veredito dominante: usa o de maior score_top1
      const melhor = [...existente.pins].sort(
        (a, b) => (b.score_top1 ?? 0) - (a.score_top1 ?? 0),
      )[0]
      existente.veredito_representativo = melhor.veredito
    } else {
      clusters.push({
        lat: pin.lat,
        lng: pin.lng,
        pins: [pin],
        veredito_representativo: pin.veredito,
      })
    }
  }
  return clusters
}

/** Centro/zoom inicial: se há pins, usa centroide; senão Brasil (Brasília). */
export function calcularViewportInicial(
  pins: PinRelatorio[],
): { center: [number, number]; zoom: number } {
  if (pins.length === 0) {
    return { center: [-15.7942, -47.8822], zoom: 4 } // Brasília + Brasil
  }
  if (pins.length === 1) {
    return { center: [pins[0].lat, pins[0].lng], zoom: 13 }
  }
  // Centroide simples (média) + zoom proporcional ao spread
  const lats = pins.map((p) => p.lat)
  const lngs = pins.map((p) => p.lng)
  const center: [number, number] = [
    lats.reduce((a, b) => a + b, 0) / pins.length,
    lngs.reduce((a, b) => a + b, 0) / pins.length,
  ]
  const spreadLat = Math.max(...lats) - Math.min(...lats)
  const spreadLng = Math.max(...lngs) - Math.min(...lngs)
  const maxSpread = Math.max(spreadLat, spreadLng)
  // Zoom heurístico: spread em graus → zoom level
  // 0.01° ≈ z14, 0.1° ≈ z11, 1° ≈ z8, 10° ≈ z5
  let zoom = 13
  if (maxSpread > 10) zoom = 5
  else if (maxSpread > 1) zoom = 8
  else if (maxSpread > 0.1) zoom = 11
  else if (maxSpread > 0.01) zoom = 13
  else zoom = 15
  return { center, zoom }
}
