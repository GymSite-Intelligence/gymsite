/**
 * Google Maps + deck.gl HeatmapLayer (oceano vermelho → azul).
 *
 * Verificação manual (dev):
 *   1. GOOGLE_MAPS_API_KEY no .env + Maps JavaScript API ativa
 *   2. uvicorn api:app --port 8000  e  npm run dev (frontend)
 *   3. /mapa → Mercado (A9) → Calor / Ambos; filtros cidade/veredito
 */
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { Loader } from '@googlemaps/js-api-loader'
import { GoogleMapsOverlay } from '@deck.gl/google-maps'
import { HeatmapLayer } from '@deck.gl/aggregation-layers'
import type { PinCluster, PinRelatorio } from '@/hooks/useRelatoriosNoMapa'
import { PinOceano } from '@/components/domain/PinOceano'
import { PinVeredito } from '@/components/domain/PinVeredito'
import {
  heatmapIntensity,
  heatmapRadiusPixels,
  oceanoDeckColorRange,
  oceanoHeatmapColorDomain,
  pinHeatmapWeight,
} from '@/lib/heatmap-weight'
import {
  MAP_MAX_ZOOM_FIT,
  bairroPinsForCluster,
  fitGoogleBoundsWithCap,
} from '@/lib/map-fly-to'
import { cn } from '@/lib/utils'
import type { Veredito } from '@/types/domain'

declare global {
  interface Window {
    gm_authFailure?: () => void
  }
}

export type MapaCamada = 'pins' | 'heat' | 'both'

export interface GoogleMapOceanoProps {
  apiKey: string
  mapId?: string
  /** Centro/zoom iniciais — reaplicados só quando filtros mudam (viewport). */
  viewportCenter: { lat: number; lng: number }
  viewportZoom: number
  /** Zoom atual do mapa (heatmap + agrupamento). */
  mapZoom: number
  clusters: PinCluster[]
  /** Todos os pins com coords — heatmap usa isto, não só centróides de cluster. */
  heatmapPins: PinRelatorio[]
  lente: 'viabilidade' | 'mercado'
  camada: MapaCamada
  clusterAtivoIdx: number | null
  selecionados: string[]
  onClusterClick: (idx: number) => void
  onZoomChange: (zoom: number) => void
  /** Falha de auth/tiles — permite fallback pigeon no pai. */
  onLoadError?: (message: string) => void
  className?: string
}

type GMap = google.maps.Map
type GOverlay = google.maps.OverlayView

interface HeatmapDatum {
  position: [number, number]
  weight: number
}

function PinOverlay({
  map,
  lat,
  lng,
  onClick,
  children,
}: {
  map: GMap
  lat: number
  lng: number
  onClick: () => void
  children: ReactNode
}) {
  const rootRef = useRef<Root | null>(null)
  const overlayRef = useRef<GOverlay | null>(null)

  useEffect(() => {
    const div = document.createElement('div')
    div.style.position = 'absolute'
    div.style.transform = 'translate(-50%, -100%)'
    div.style.cursor = 'pointer'
    div.onclick = onClick
    rootRef.current = createRoot(div)

    class HtmlOverlay extends google.maps.OverlayView {
      onAdd() {
        this.getPanes()?.overlayMouseTarget.appendChild(div)
      }
      draw() {
        const projection = this.getProjection()
        const point = projection?.fromLatLngToDivPixel(
          new google.maps.LatLng(lat, lng),
        )
        if (point) {
          div.style.left = `${point.x}px`
          div.style.top = `${point.y}px`
        }
      }
      onRemove() {
        div.remove()
      }
    }

    const overlay = new HtmlOverlay()
    overlay.setMap(map)
    overlayRef.current = overlay
    rootRef.current.render(children)

    const idle = map.addListener('idle', () => overlay.draw())
    return () => {
      google.maps.event.removeListener(idle)
      overlay.setMap(null)
      rootRef.current?.unmount()
      rootRef.current = null
    }
  }, [map, lat, lng, onClick])

  useEffect(() => {
    rootRef.current?.render(children)
    overlayRef.current?.draw()
  }, [children])

  return null
}

export function GoogleMapOceano({
  apiKey,
  mapId,
  viewportCenter,
  viewportZoom,
  mapZoom,
  clusters,
  heatmapPins,
  lente,
  camada,
  clusterAtivoIdx,
  selecionados,
  onClusterClick,
  onZoomChange,
  onLoadError,
  className,
}: GoogleMapOceanoProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<GMap | null>(null)
  const deckRef = useRef<GoogleMapsOverlay | null>(null)
  const [mapReady, setMapReady] = useState(false)
  const [tilesReady, setTilesReady] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const reportError = (message: string) => {
    setLoadError(message)
    onLoadError?.(message)
  }

  const heatData = useMemo((): HeatmapDatum[] => {
    return heatmapPins.map((p) => ({
      position: [p.lng, p.lat] as [number, number],
      weight: pinHeatmapWeight(p),
    }))
  }, [heatmapPins])

  const deckLayers = useMemo(() => {
    const showHeat = camada === 'heat' || camada === 'both'
    if (!showHeat || heatData.length === 0) return []
    return [
      new HeatmapLayer<HeatmapDatum>({
        id: 'oceano-heatmap',
        data: heatData,
        aggregation: 'SUM',
        getPosition: (d) => d.position,
        getWeight: (d) => d.weight,
        radiusPixels: heatmapRadiusPixels(mapZoom),
        intensity: heatmapIntensity(mapZoom),
        threshold: 0.03,
        colorRange: oceanoDeckColorRange(),
        colorDomain: oceanoHeatmapColorDomain(),
      }),
    ]
  }, [camada, heatData, mapZoom])

  useEffect(() => {
    let cancelled = false
    const el = containerRef.current
    if (!el || !apiKey) return

    const prevAuthFailure = window.gm_authFailure
    window.gm_authFailure = () => {
      if (!cancelled) {
        reportError(
          'Chave Google Maps rejeitada (RefererNotAllowed ou billing). Confira restrições no Cloud Console.',
        )
      }
    }

    const loader = new Loader({
      apiKey,
      version: 'weekly',
      libraries: ['marker'],
      language: 'pt-BR',
      region: 'BR',
      ...(mapId ? { mapIds: [mapId] } : {}),
    })

    ;(async () => {
      try {
        await loader.importLibrary('maps')
        if (cancelled) return

        const opts: google.maps.MapOptions = {
          center: viewportCenter,
          zoom: viewportZoom,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: true,
          gestureHandling: 'greedy',
          backgroundColor: '#e5e3df',
        }
        if (mapId) {
          opts.mapId = mapId
        }

        const map = new google.maps.Map(el, opts)
        mapRef.current = map

        let tilesLoaded = false
        const tileTimer = window.setTimeout(() => {
          if (!cancelled && !tilesLoaded) {
            reportError(
              'Tiles do Google Maps não carregaram (timeout). Verifique Maps JavaScript API e billing.',
            )
          }
        }, 12_000)

        map.addListener('tilesloaded', () => {
          if (!cancelled) {
            tilesLoaded = true
            setTilesReady(true)
            window.clearTimeout(tileTimer)
          }
        })

        // interleaved:true em mapas raster (sem mapId) — canvas deck opaco não cobre tiles
        const deckOverlay = new GoogleMapsOverlay({
          interleaved: !mapId,
          layers: [],
        })
        deckOverlay.setMap(map)
        deckRef.current = deckOverlay

        map.addListener('zoom_changed', () => {
          const z = map.getZoom()
          if (z != null) onZoomChange(z)
        })
        setMapReady(true)
        setLoadError(null)
      } catch (e) {
        reportError(e instanceof Error ? e.message : String(e))
      }
    })()

    return () => {
      cancelled = true
      window.gm_authFailure = prevAuthFailure
      deckRef.current?.setMap(null)
      deckRef.current = null
      mapRef.current = null
      setMapReady(false)
      setTilesReady(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- init once per key/mapId
  }, [apiKey, mapId])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady) return
    map.setCenter(viewportCenter)
    map.setZoom(viewportZoom)
  }, [viewportCenter.lat, viewportCenter.lng, viewportZoom, mapReady])

  useEffect(() => {
    if (!mapReady) return
    deckRef.current?.setProps({ layers: deckLayers })
  }, [deckLayers, mapReady])

  const camadaRef = useRef(camada)
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady || heatData.length === 0) return
    const prev = camadaRef.current
    camadaRef.current = camada
    const wasHeat = prev === 'heat' || prev === 'both'
    const nowHeat = camada === 'heat' || camada === 'both'
    if (!nowHeat || wasHeat) return
    const pinsForFit = heatmapPins
    const z = fitGoogleBoundsWithCap(map, pinsForFit, 48, MAP_MAX_ZOOM_FIT)
    onZoomChange(z)
  }, [camada, heatData, heatmapPins, mapReady, onZoomChange])

  const showPins = camada === 'pins' || camada === 'both'
  const map = mapRef.current

  return (
    <div className={cn('relative h-full min-h-[320px] w-full', className)}>
      <div
        ref={containerRef}
        className="h-full min-h-[320px] w-full bg-[#e5e3df]"
        aria-label="Mapa Google"
      />
      {!loadError && mapReady && !tilesReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#e5e3df]/90 text-sm text-muted-foreground">
          Carregando mapa…
        </div>
      )}
      {loadError && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted/80 text-sm text-destructive p-4 text-center">
          Falha ao carregar Google Maps: {loadError}
        </div>
      )}
      {mapReady &&
        map &&
        showPins &&
        clusters.map((c, idx) => {
          const algumSelecionado = c.pins.some((p) =>
            selecionados.includes(p.id),
          )
          const pinNode =
            lente === 'mercado' ? (
              <PinOceano
                veredito={c.oceano_representativo}
                ativo={clusterAtivoIdx === idx && !algumSelecionado}
                selecionado={algumSelecionado}
                count={c.pins.length}
              />
            ) : (
              <PinVeredito
                veredito={c.veredito_representativo as Veredito}
                ativo={clusterAtivoIdx === idx && !algumSelecionado}
                selecionado={algumSelecionado}
                count={c.pins.length}
              />
            )
          return (
            <PinOverlay
              key={`${c.lat}-${c.lng}-${idx}`}
              map={map}
              lat={c.lat}
              lng={c.lng}
              onClick={() => {
                const bairroPins = bairroPinsForCluster(c, heatmapPins)
                const z = fitGoogleBoundsWithCap(
                  map,
                  bairroPins,
                  56,
                  MAP_MAX_ZOOM_FIT,
                )
                onZoomChange(z)
                onClusterClick(idx)
              }}
            >
              {pinNode}
            </PinOverlay>
          )
        })}
    </div>
  )
}
