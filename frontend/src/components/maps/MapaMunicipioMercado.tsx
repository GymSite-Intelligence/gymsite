/**
 * Mapa municipal no viewer — concorrentes + heat entrantes (90d).
 * Escopo: município do relatório (nunca fit Brasil).
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { Loader } from '@googlemaps/js-api-loader'
import { GoogleMapsOverlay } from '@deck.gl/google-maps'
import { HeatmapLayer } from '@deck.gl/aggregation-layers'
import { useMapsJsConfig } from '@/hooks/useMapsJsConfig'
import {
  useMapaMercado,
  type MapaMercadoBounds,
  type MapaMercadoEntrante,
} from '@/hooks/useMapaMercado'
import {
  agruparMercadoPins,
  MERCADO_CLUSTER_THRESHOLD,
  mercadoClusterTolerance,
} from '@/lib/mapa-mercado-cluster'
import {
  entranteHeatmapWeight,
  heatmapIntensity,
  heatmapRadiusPixels,
  oceanoDeckColorRange,
  oceanoHeatmapColorDomain,
} from '@/lib/heatmap-weight'
import { MAP_ZOOM_CIDADE } from '@/lib/map-fly-to'
import { cn } from '@/lib/utils'

const MAP_MIN_ZOOM = 10
const MAP_MAX_ZOOM = 14

interface LatLngPin {
  lat: number
  lng: number
}

interface HeatmapDatum {
  position: [number, number]
  weight: number
}

function fitMunicipioBounds(
  map: google.maps.Map,
  pins: LatLngPin[],
  municipioCentro: LatLngPin | null,
  boundsMunicipio: MapaMercadoBounds | null | undefined,
  padding = 48,
): void {
  const bounds = new google.maps.LatLngBounds()
  let hasBounds = false
  if (boundsMunicipio?.ne && boundsMunicipio?.sw) {
    bounds.extend(boundsMunicipio.sw)
    bounds.extend(boundsMunicipio.ne)
    hasBounds = true
  } else if (municipioCentro) {
    bounds.extend(municipioCentro)
    hasBounds = true
  }
  for (const p of pins) {
    bounds.extend(p)
    hasBounds = true
  }
  if (!hasBounds) {
    if (municipioCentro) {
      map.setCenter(municipioCentro)
      map.setZoom(MAP_ZOOM_CIDADE)
    }
    return
  }
  map.fitBounds(bounds, padding)
  const cap = () => {
    const z = map.getZoom()
    if (z != null && z > MAP_MAX_ZOOM) map.setZoom(MAP_MAX_ZOOM)
    if (z != null && z < MAP_MIN_ZOOM) map.setZoom(MAP_MIN_ZOOM)
  }
  cap()
  google.maps.event.addListenerOnce(map, 'idle', cap)
}

function ratingPinColor(rating: number | null | undefined): string {
  if (rating == null || !Number.isFinite(rating)) return '#94a3b8'
  if (rating >= 4.2) return '#ea580c'
  if (rating >= 3.5) return '#f59e0b'
  return '#dc2626'
}

function MapLegend() {
  return (
    <div className="absolute bottom-2 left-2 z-10 flex flex-wrap gap-3 rounded-md border bg-background/90 px-3 py-2 text-xs shadow-sm">
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#ea580c]" />
        Concorrentes
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-2.5 rotate-45 bg-sky-500" />
        Entrantes (90d)
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-2.5 rounded-full border-2 border-violet-600 bg-violet-200" />
        Site (bairro)
      </span>
    </div>
  )
}

export interface MapaMunicipioMercadoProps {
  relatorioId: string
  cidade: string
  uf?: string | null
  bairro?: string | null
  className?: string
}

export function MapaMunicipioMercado({
  relatorioId,
  cidade,
  uf,
  bairro,
  className,
}: MapaMunicipioMercadoProps) {
  const { data: mapsCfg, isLoading: cfgLoading } = useMapsJsConfig()
  const { data: mapa, isLoading: mapaLoading, error: mapaError } = useMapaMercado(
    relatorioId,
  )
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<google.maps.Map | null>(null)
  const deckRef = useRef<GoogleMapsOverlay | null>(null)
  const markersRef = useRef<google.maps.Marker[]>([])
  const [mapReady, setMapReady] = useState(false)
  const [mapZoom, setMapZoom] = useState(MAP_ZOOM_CIDADE)
  const [loadError, setLoadError] = useState<string | null>(null)

  const boundsMunicipio = useMemo((): MapaMercadoBounds | null => {
    return mapa?.bounds_municipio ?? mapa?.municipio?.bounds ?? null
  }, [mapa])

  const concorrenteClusters = useMemo(() => {
    const list = (mapa?.concorrentes ?? []).filter(
      (c): c is typeof c & { lat: number; lng: number } =>
        typeof c.lat === 'number' && typeof c.lng === 'number',
    )
    if (list.length <= MERCADO_CLUSTER_THRESHOLD) {
      return list.map((c) => ({ lat: c.lat, lng: c.lng, items: [c] }))
    }
    return agruparMercadoPins(list, mercadoClusterTolerance(mapZoom))
  }, [mapa?.concorrentes, mapZoom])

  const municipioCentro = useMemo((): LatLngPin | null => {
    const c = mapa?.municipio?.centro
    if (typeof c?.lat === 'number' && typeof c?.lng === 'number') {
      return { lat: c.lat, lng: c.lng }
    }
    return null
  }, [mapa])

  const allPins = useMemo((): LatLngPin[] => {
    if (!mapa) return []
    const pins: LatLngPin[] = []
    for (const c of mapa.concorrentes ?? []) {
      if (typeof c.lat === 'number' && typeof c.lng === 'number') {
        pins.push({ lat: c.lat, lng: c.lng })
      }
    }
    for (const e of mapa.entrantes ?? []) {
      if (typeof e.lat === 'number' && typeof e.lng === 'number') {
        pins.push({ lat: e.lat, lng: e.lng })
      }
    }
    if (mapa.site) {
      pins.push({ lat: mapa.site.lat, lng: mapa.site.lng })
    }
    return pins
  }, [mapa])

  const heatData = useMemo((): HeatmapDatum[] => {
    if (!mapa?.entrantes?.length) return []
    return mapa.entrantes.map((e: MapaMercadoEntrante) => ({
      position: [e.lng, e.lat] as [number, number],
      weight: entranteHeatmapWeight(e.peso_heatmap),
    }))
  }, [mapa])

  const deckLayers = useMemo(() => {
    if (heatData.length === 0) return []
    return [
      new HeatmapLayer<HeatmapDatum>({
        id: 'entrantes-heatmap',
        data: heatData,
        aggregation: 'SUM',
        getPosition: (d) => d.position,
        getWeight: (d) => d.weight,
        radiusPixels: heatmapRadiusPixels(mapZoom),
        intensity: heatmapIntensity(mapZoom),
        threshold: 0.04,
        colorRange: oceanoDeckColorRange(),
        colorDomain: oceanoHeatmapColorDomain(),
      }),
    ]
  }, [heatData, mapZoom])

  useEffect(() => {
    let cancelled = false
    const el = containerRef.current
    const apiKey = mapsCfg?.key
    if (!el || !apiKey || cfgLoading) return

    const loader = new Loader({
      apiKey,
      version: 'weekly',
      libraries: ['marker'],
      language: 'pt-BR',
      region: 'BR',
    })

    ;(async () => {
      try {
        await loader.importLibrary('maps')
        if (cancelled) return
        const center = municipioCentro ?? { lat: -15.7942, lng: -47.8822 }
        const opts: google.maps.MapOptions = {
          center,
          zoom: MAP_ZOOM_CIDADE,
          minZoom: MAP_MIN_ZOOM,
          maxZoom: MAP_MAX_ZOOM,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: true,
          gestureHandling: 'greedy',
        }
        if (mapsCfg?.mapId) {
          opts.mapId = mapsCfg.mapId
        }
        const map = new google.maps.Map(el, opts)
        mapRef.current = map
        const deckOverlay = new GoogleMapsOverlay({
          interleaved: !mapsCfg?.mapId,
          layers: [],
        })
        deckOverlay.setMap(map)
        deckRef.current = deckOverlay
        map.addListener('zoom_changed', () => {
          const z = map.getZoom()
          if (z != null) setMapZoom(z)
        })
        map.setOptions({
          restriction: undefined,
        })
        setMapReady(true)
        setLoadError(null)
      } catch (e) {
        setLoadError(e instanceof Error ? e.message : String(e))
      }
    })()

    return () => {
      cancelled = true
      for (const m of markersRef.current) {
        m.setMap(null)
      }
      markersRef.current = []
      deckRef.current?.setMap(null)
      deckRef.current = null
      mapRef.current = null
      setMapReady(false)
    }
  }, [mapsCfg?.key, mapsCfg?.mapId, cfgLoading, municipioCentro?.lat, municipioCentro?.lng])

  useEffect(() => {
    if (!mapReady || !mapRef.current || !mapa) return
    const map = mapRef.current
    fitMunicipioBounds(map, allPins, municipioCentro, boundsMunicipio)
    const z = map.getZoom()
    if (z != null) setMapZoom(z)
  }, [mapReady, mapa, allPins, municipioCentro, boundsMunicipio])

  useEffect(() => {
    if (!mapReady || !deckRef.current) return
    deckRef.current.setProps({ layers: deckLayers })
  }, [deckLayers, mapReady])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady || !mapa) return
    for (const m of markersRef.current) {
      m.setMap(null)
    }
    markersRef.current = []

    for (const cluster of concorrenteClusters) {
      const isMulti = cluster.items.length > 1
      const rep = cluster.items[0]
      const marker = new google.maps.Marker({
        map,
        position: { lat: cluster.lat, lng: cluster.lng },
        title: isMulti
          ? `${cluster.items.length} concorrentes`
          : rep.nome ?? 'Concorrente',
        label: isMulti
          ? {
              text: String(cluster.items.length),
              color: '#fff',
              fontSize: '11px',
              fontWeight: '700',
            }
          : undefined,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: isMulti ? 12 : 8,
          fillColor: isMulti ? '#64748b' : ratingPinColor(rep.rating),
          fillOpacity: 0.95,
          strokeColor: '#fff',
          strokeWeight: 1.5,
        },
      })
      if (isMulti) {
        marker.addListener('click', () => {
          map.setCenter({ lat: cluster.lat, lng: cluster.lng })
          const z = map.getZoom() ?? MAP_ZOOM_CIDADE
          map.setZoom(Math.min(MAP_MAX_ZOOM, z + 2))
        })
      }
      markersRef.current.push(marker)
    }

    for (const e of mapa.entrantes as MapaMercadoEntrante[]) {
      const marker = new google.maps.Marker({
        map,
        position: { lat: e.lat, lng: e.lng },
        title: e.nome_exibicao ?? 'Novo entrante',
        zIndex: 500,
        icon: {
          path: 'M 0,-6 L 6,0 L 0,6 L -6,0 Z',
          scale: 1.1,
          fillColor: '#0ea5e9',
          fillOpacity: 0.92,
          strokeColor: '#fff',
          strokeWeight: 1.5,
        },
      })
      markersRef.current.push(marker)
    }

    if (mapa.site) {
      const siteMarker = new google.maps.Marker({
        map,
        position: { lat: mapa.site.lat, lng: mapa.site.lng },
        title: mapa.site.label ?? 'Site de estudo',
        zIndex: 1000,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 11,
          fillColor: '#8b5cf6',
          fillOpacity: 1,
          strokeColor: '#4c1d95',
          strokeWeight: 2,
        },
      })
      markersRef.current.push(siteMarker)
    }
  }, [mapReady, mapa, concorrenteClusters])

  const ufLabel = (uf || mapa?.uf || '').trim()
  const title = `Mapa do município — ${cidade}${ufLabel ? `/${ufLabel}` : ''}`

  if (!mapsCfg?.configured && !cfgLoading) {
    return (
      <p className="text-sm text-muted-foreground">
        Mapa indisponível: configure a chave Google Maps no servidor.
      </p>
    )
  }

  if (mapaLoading || cfgLoading) {
    return (
      <div className={cn('flex h-[320px] items-center justify-center rounded-lg border bg-muted/30', className)}>
        <span className="text-sm text-muted-foreground">Carregando mapa…</span>
      </div>
    )
  }

  if (mapaError) {
    return (
      <p className="text-sm text-destructive">
        Não foi possível carregar o mapa: {mapaError.message}
      </p>
    )
  }

  const temDados =
    (mapa?.concorrentes?.length ?? 0) > 0 ||
    (mapa?.entrantes?.length ?? 0) > 0 ||
    !!mapa?.site

  return (
    <div className={cn('space-y-2', className)}>
      <h4 className="text-sm font-medium">{title}</h4>
      {bairro && (
        <p className="text-xs text-muted-foreground">
          Bairro de estudo: <strong>{bairro}</strong>
          {(mapa?.entrantes_com_coord ?? 0) > 0 && (
            <>
              {' '}
              · {mapa?.entrantes_com_coord} entrante(s) no mapa
            </>
          )}
        </p>
      )}
      {!temDados && (
        <p className="text-xs text-muted-foreground">
          Sem coordenadas de concorrentes ou entrantes para este relatório. Reexecute o
          pipeline após aplicar a migration de geo nos competidores.
        </p>
      )}
      <div className="relative h-[360px] w-full overflow-hidden rounded-lg border">
        <div ref={containerRef} className="h-full w-full" aria-label={title} />
        <MapLegend />
        {loadError && (
          <div className="absolute inset-0 flex items-center justify-center bg-muted/80 p-4 text-center text-sm text-destructive">
            {loadError}
          </div>
        )}
      </div>
    </div>
  )
}
