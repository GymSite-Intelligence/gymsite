/**
 * useRelatoriosNoMapa — agrega lat/lng dos relatórios pra renderizar pins.
 *
 * Queries Supabase:
 *   1. `useRelatorios` — lista resumo com filtros
 *   2. geocode bairro+cidade (API) — lat/lng do pin no mapa
 *   3. `candidatos` — top 1 (só metadados / fallback coords)
 *   4. `relatorio_outputs.score_concorrencia` — peso do heatmap
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
import type { Veredito, VereditoOceano } from '@/types/domain'
import { normalizeVereditoOceano } from '@/lib/oceano'
import { localidadeKey, viewportFromPins } from '@/lib/map-fly-to'
import { fetchBairroCoordsBatch } from '@/lib/bairro-geocode'

export interface PinRelatorio {
  id: string
  lat: number
  lng: number
  cidade: string
  bairro: string
  veredito: Veredito
  veredito_oceano: VereditoOceano | null
  score_top1: number | null
  score_geoscout: number | null
  modelo_recomendado: string | null
  candidato_nome: string
  candidato_endereco: string
  /** URL Street View Static gerada pelo A1 GeoScout (640x400 c/ key). */
  street_view_url: string | null
  /** A3/A6 — 0–10 (10 = mercado favorável). Prioridade no peso do heatmap. */
  score_concorrencia: number | null
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
  const { data: scoresByRelatorio, isLoading: loadingScores } = useQuery({
    queryKey: ['mapa-scores', user?.id ?? 'anon', ids],
    enabled: !USE_MOCKS && !!user && ids.length > 0,
    meta: { silent: true },
    queryFn: async (): Promise<Map<string, number | null>> => {
      const { data, error } = await supabase
        .from('relatorio_outputs')
        .select('relatorio_id, score_concorrencia')
        .in('relatorio_id', ids)
      if (error) throw new Error(`Supabase: ${error.message}`)
      const map = new Map<string, number | null>()
      for (const row of (data ?? []) as Array<{
        relatorio_id: string
        score_concorrencia: number | string | null
      }>) {
        const sc = row.score_concorrencia
        const n =
          typeof sc === 'string'
            ? parseFloat(sc)
            : typeof sc === 'number'
              ? sc
              : null
        map.set(
          row.relatorio_id,
          n != null && Number.isFinite(n) ? n : null,
        )
      }
      return map
    },
  })


  const { data: bairroCoordsByKey, isLoading: loadingBairroGeo } = useQuery({
    queryKey: [
      'mapa-bairro-geo',
      user?.id ?? 'anon',
      ids,
      (resumos ?? []).map((r) => localidadeKey(r.bairro, r.cidade)).join('|'),
    ],
    enabled: !USE_MOCKS && !!user && (resumos?.length ?? 0) > 0,
    meta: { silent: true },
    staleTime: 1000 * 60 * 60 * 24,
    queryFn: async () => {
      const items = (resumos ?? []).map((r) => ({
        bairro: r.bairro,
        cidade: r.cidade,
        uf: r.uf,
      }))
      return fetchBairroCoordsBatch(items)
    },
  })

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
        const oc = raw.output_consolidado as Record<string, unknown> | undefined
        const rawSc = oc?.score_concorrencia
        const outSc =
          typeof rawSc === 'number' && Number.isFinite(rawSc) ? rawSc : null
        out.push({
          id: resumo.id,
          lat,
          lng,
          cidade: resumo.cidade,
          bairro: resumo.bairro,
          veredito: resumo.veredito ?? 'INVESTIGAR MAIS',
          veredito_oceano: normalizeVereditoOceano(resumo.veredito_posicionamento),
          score_top1: resumo.score_top1_candidato,
          score_geoscout: top?.score_geoscout ?? null,
          modelo_recomendado: resumo.modelo_recomendado,
          candidato_nome: top?.nome ?? '—',
          candidato_endereco: top?.endereco ?? '',
          street_view_url:
            typeof top?.street_view_url === 'string' && top.street_view_url
              ? top.street_view_url
              : null,
          score_concorrencia: outSc,
        })
      }
      return out
    }

    // Modo real: pin = geocode bairro+cidade do relatório (fallback: top1 imóvel)
    const out: PinRelatorio[] = []
    for (const resumo of resumos) {
      const top = topByRelatorio?.get(resumo.id)
      const scoreConc = scoresByRelatorio?.get(resumo.id) ?? null
      const geo = bairroCoordsByKey?.get(localidadeKey(resumo.bairro, resumo.cidade))
      let lat = geo?.lat
      let lng = geo?.lng
      if (lat == null || lng == null) {
        const tLat = typeof top?.lat === 'string' ? parseFloat(top.lat) : top?.lat
        const tLng = typeof top?.lng === 'string' ? parseFloat(top.lng) : top?.lng
        lat = tLat ?? undefined
        lng = tLng ?? undefined
      }
      if (
        lat == null ||
        lng == null ||
        !Number.isFinite(lat) ||
        !Number.isFinite(lng)
      ) {
        continue
      }
      const scoreGeo =
        typeof top?.score_geoscout === 'string'
          ? parseFloat(top?.score_geoscout as string)
          : top?.score_geoscout
      out.push({
        id: resumo.id,
        lat,
        lng,
        cidade: resumo.cidade,
        bairro: resumo.bairro,
        veredito: resumo.veredito ?? 'INVESTIGAR MAIS',
        veredito_oceano: normalizeVereditoOceano(resumo.veredito_posicionamento),
        score_top1: resumo.score_top1_candidato,
        score_geoscout: Number.isFinite(scoreGeo as number)
          ? (scoreGeo as number)
          : null,
        modelo_recomendado: resumo.modelo_recomendado,
        candidato_nome: top?.nome ?? '—',
        candidato_endereco: top?.endereco ?? '',
        street_view_url: top?.street_view_url ?? null,
        score_concorrencia: scoreConc,
      })
    }
    return out
  }, [resumos, topByRelatorio, scoresByRelatorio, bairroCoordsByKey])

  const totalResumos = resumos?.length ?? 0

  return {
    pins,
    /** Bloqueia o mapa só enquanto dados essenciais carregam (não geocode em background). */
    isLoading: loadingResumos || loadingTops || loadingScores,
    /** Geocode bairro+cidade — melhora posição do pin; top1 candidato é fallback imediato. */
    isGeocodingBairros: loadingBairroGeo,
    total: pins.length,
    semCoordenadas: totalResumos - pins.length,
    totalResumos,
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
  oceano_representativo: VereditoOceano | null
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
      existente.oceano_representativo = melhor.veredito_oceano
    } else {
      clusters.push({
        lat: pin.lat,
        lng: pin.lng,
        pins: [pin],
        veredito_representativo: pin.veredito,
        oceano_representativo: pin.veredito_oceano,
      })
    }
  }
  return clusters
}

/** Centro/zoom inicial: enquadra pins em escala cidade/bairro (não Brasil nem rua). */
export function calcularViewportInicial(
  pins: PinRelatorio[],
): { center: [number, number]; zoom: number } {
  return viewportFromPins(pins)
}
