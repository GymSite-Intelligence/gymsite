import { useEffect, useMemo, useRef, useState } from 'react'
import { GeoJson, Map as PigeonMap, Overlay } from 'pigeon-maps'
import * as maplibregl from 'maplibre-gl'
import MapLibreMap, {
  AttributionControl,
  Layer,
  Marker,
  Popup,
  Source,
} from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import { GYMSITE_PALETTE } from '@/config/gymsite-design-system'
import { cn } from '@/lib/utils'
import { explorarChrome } from './explorar-chrome'
import type { Camada, Lente, MapStyle } from './explorarIso'
import type { ExplorarIsoRings } from '@/hooks/useExplorarIsocronas'
import {
  OSM_ATTRIBUTION,
  ESRI_ATTRIBUTION,
  ISO_STYLE,
  influenceFeatureCollection,
  mapLibreStyle,
  tileProvider,
} from './explorarIso'

function mapLibreSupported(): boolean {
  const supported = (maplibregl as { supported?: () => boolean }).supported
  if (typeof supported === 'function') return supported()
  try {
    const canvas = document.createElement('canvas')
    return Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'))
  } catch {
    return false
  }
}

const glOk = typeof window !== 'undefined' && mapLibreSupported()

const ISO_KEYS = ['m15', 'm10', 'm5'] as const

function CenterPin({ lime = false }: { lime?: boolean }) {
  return (
    <div
      aria-label="Ponto candidato"
      className="pointer-events-none size-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-white"
      style={{
        background: lime ? GYMSITE_PALETTE.lime : '#22c55e',
        boxShadow: '0 2px 8px rgba(0,0,0,.5)',
      }}
    />
  )
}

function RivalPin({ selected, onClick }: { selected: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-label="Academia no recorte"
      onClick={(e) => {
        e.stopPropagation()
        onClick()
      }}
      className={cn(
        'size-3.5 -translate-x-1/2 -translate-y-1/2 cursor-pointer rounded-full border-2 border-white',
        selected && 'scale-125',
      )}
      style={{
        background: selected ? GYMSITE_PALETTE.lime : '#ef4444',
        boxShadow: '0 2px 6px rgba(0,0,0,.4)',
      }}
    />
  )
}

function RivalPopupBody({ rival }: { rival: ExplorarRival }) {
  return (
    <div
      className={cn(
        explorarChrome(),
        'min-w-44 max-w-56 rounded-lg border px-2.5 py-2 text-left shadow-lg',
      )}
      onClick={(e) => e.stopPropagation()}
    >
      <p className="text-xs font-semibold leading-snug text-foreground">{rival.nome}</p>
      <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
        {rival.endereco?.trim() || 'Endereço não informado no Maps'}
      </p>
      {(rival.rating != null || rival.reviews != null) && (
        <p className="mt-1 text-[11px] text-muted-foreground">
          {rival.rating != null ? `★ ${rival.rating}` : '—'}
          {rival.reviews != null ? ` · ${rival.reviews} avaliações` : ''}
        </p>
      )}
    </div>
  )
}

export type ExplorarReclamacao = {
  texto: string
  rating: number
  autor?: string
}

export type ExplorarRival = {
  nome: string
  lat: number
  lng: number
  dist_m?: number
  rating?: number | null
  reviews?: number
  endereco?: string
  place_id?: string
  reclamacoes?: ExplorarReclamacao[]
}

type ViasFeatureCollection = ReturnType<typeof import('./explorarIso').topViasToFeatureCollection>

type ExplorarMapProps = {
  center: [number, number]
  zoom: number
  pin: { lat: number; lng: number } | null
  rivals: ExplorarRival[]
  mapStyle: MapStyle
  camada: Camada
  lente: Lente
  isoRings: ExplorarIsoRings | null
  viasFc: ViasFeatureCollection
  viasOn: boolean
  onClickMap: (lat: number, lng: number) => void
  onZoom: (z: number) => void
}

function useMapSize() {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ w: 0, h: 0 })

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const apply = () => {
      const r = el.getBoundingClientRect()
      const w = Math.round(r.width)
      const h = Math.round(r.height)
      if (w < 1 || h < 1) return
      setSize((prev) => (prev.w === w && prev.h === h ? prev : { w, h }))
    }
    apply()
    const ro = new ResizeObserver(apply)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  return { wrapRef, size }
}

function useIsoData(
  pin: ExplorarMapProps['pin'],
  camada: Camada,
  lente: Lente,
  isoRings: ExplorarIsoRings | null,
) {
  const iso = Boolean(pin && camada === 'influencia')
  const [layerOn, setLayerOn] = useState(false)
  const isoData = useMemo(
    () =>
      pin && iso
        ? influenceFeatureCollection(pin.lat, pin.lng, lente, isoRings, {
            lenteCircle: lente !== 'bairro',
          })
        : null,
    [pin, iso, lente, isoRings],
  )

  useEffect(() => {
    setLayerOn(iso)
  }, [iso, lente, isoRings, pin?.lat, pin?.lng])

  return { iso, isoData, layerOn }
}

function ExplorarMapPigeon({
  center,
  zoom,
  pin,
  rivals,
  mapStyle,
  camada,
  lente,
  isoRings,
  onClickMap,
  onZoom,
}: ExplorarMapProps) {
  const { wrapRef, size } = useMapSize()
  const [activeRival, setActiveRival] = useState<ExplorarRival | null>(null)
  const { isoData, layerOn } = useIsoData(pin, camada, lente, isoRings)

  return (
    <div ref={wrapRef} className="relative h-full w-full">
      <p className="pointer-events-none absolute bottom-2 left-2 z-10 text-[11px] text-muted-foreground/80">
        Mapa simplificado neste aparelho.
      </p>
      {size.w > 0 && size.h > 0 && (
        <PigeonMap
          width={size.w}
          height={size.h}
          defaultCenter={center}
          center={center}
          zoom={zoom}
          animate
          provider={tileProvider(mapStyle)}
          attribution={<span>{mapStyle === 'satelite' ? ESRI_ATTRIBUTION : OSM_ATTRIBUTION}</span>}
          attributionPrefix={false}
          onClick={({ latLng }) => {
            setActiveRival(null)
            onClickMap(latLng[0], latLng[1])
          }}
          onBoundsChanged={({ zoom: z }) => {
            if (typeof z === 'number' && z !== zoom) onZoom(z)
          }}
        >
          {isoData && (
            <GeoJson
              data={isoData}
              style={{ pointerEvents: 'none', opacity: layerOn ? 1 : 0, transition: 'opacity 0.45s ease' }}
              styleCallback={(feature: { properties?: { key?: string } }) => {
                const key = feature.properties?.key
                const fade = layerOn ? 1 : 0
                if (key === 'lente') {
                  return {
                    fill: 'none',
                    stroke: '#2563eb',
                    strokeWidth: 2,
                    strokeOpacity: fade,
                    pointerEvents: 'none',
                  }
                }
                const st = key === 'm5' || key === 'm10' || key === 'm15' ? ISO_STYLE[key] : null
                if (!st) return { fill: 'none', pointerEvents: 'none' }
                return {
                  fill: st.fill,
                  fillOpacity: st.fillOpacity * fade,
                  stroke: st.stroke,
                  strokeWidth: 2,
                  strokeDasharray: '6 5',
                  strokeOpacity: fade,
                  pointerEvents: 'none',
                }
              }}
            />
          )}
          {rivals.map((r) => (
            <Overlay key={`${r.lat},${r.lng},${r.nome}`} anchor={[r.lat, r.lng]}>
              <RivalPin
                selected={
                  activeRival?.lat === r.lat &&
                  activeRival?.lng === r.lng &&
                  activeRival?.nome === r.nome
                }
                onClick={() => setActiveRival(r)}
              />
            </Overlay>
          ))}
          {activeRival && (
            <Overlay anchor={[activeRival.lat, activeRival.lng]}>
              <div className="pointer-events-auto -translate-x-1/2 -translate-y-[calc(100%+10px)]">
                <RivalPopupBody rival={activeRival} />
              </div>
            </Overlay>
          )}
          {pin && (
            <Overlay anchor={[pin.lat, pin.lng]}>
              <CenterPin lime />
            </Overlay>
          )}
        </PigeonMap>
      )}
    </div>
  )
}

function ExplorarMapLibre({
  center,
  zoom,
  pin,
  rivals,
  mapStyle,
  camada,
  lente,
  isoRings,
  viasFc,
  viasOn,
  onClickMap,
  onZoom,
}: ExplorarMapProps) {
  const { wrapRef } = useMapSize()
  const [activeRival, setActiveRival] = useState<ExplorarRival | null>(null)
  const { iso, isoData } = useIsoData(pin, camada, lente, isoRings)
  const overlayFc = isoData ?? { type: 'FeatureCollection' as const, features: [] }
  const fade = iso ? 1 : 0
  const viasVisible = camada === 'influencia' && viasOn
  const overlayBefore = 'gs-overlay-anchor'
  const basemapCredit = mapStyle === 'satelite' ? ESRI_ATTRIBUTION : OSM_ATTRIBUTION

  return (
    <div ref={wrapRef} className="h-full w-full">
      <MapLibreMap
        key={mapStyle}
        mapLib={maplibregl}
        style={{ width: '100%', height: '100%' }}
        mapStyle={mapLibreStyle(mapStyle)}
        longitude={center[1]}
        latitude={center[0]}
        zoom={zoom}
        attributionControl={false}
        onMoveEnd={(e) => onZoom(e.viewState.zoom)}
        onClick={(e) => {
          const el = e.originalEvent.target
          if (el instanceof Element && el.closest('button')) return
          setActiveRival(null)
          onClickMap(e.lngLat.lat, e.lngLat.lng)
        }}
      >
        <AttributionControl compact customAttribution={basemapCredit} />

        <Source id="iso" type="geojson" data={overlayFc}>
            {ISO_KEYS.map((key) => {
              const st = ISO_STYLE[key]
              return (
                <Layer
                  key={`${key}-fill`}
                  id={`iso-${key}-fill`}
                  type="fill"
                  beforeId={overlayBefore}
                  filter={['==', ['get', 'key'], key]}
                  paint={{
                    'fill-color': st.fill,
                    'fill-opacity': st.fillOpacity * fade,
                  }}
                />
              )
            })}
            {ISO_KEYS.map((key) => {
              const st = ISO_STYLE[key]
              return (
                <Layer
                  key={`${key}-line`}
                  id={`iso-${key}-line`}
                  type="line"
                  beforeId={overlayBefore}
                  filter={['==', ['get', 'key'], key]}
                  paint={{
                    'line-color': st.stroke,
                    'line-width': 2,
                    'line-opacity': fade,
                    'line-dasharray': [6, 5],
                  }}
                />
              )
            })}
            <Layer
              id="iso-lente-line"
              type="line"
              beforeId={overlayBefore}
              filter={['==', ['get', 'key'], 'lente']}
              paint={{
                'line-color': '#2563eb',
                'line-width': 2,
                'line-opacity': fade,
              }}
            />
          </Source>

        {rivals.map((r) => (
          <Marker key={`${r.lat},${r.lng},${r.nome}`} longitude={r.lng} latitude={r.lat} anchor="center">
            <RivalPin
              selected={
                activeRival?.lat === r.lat &&
                activeRival?.lng === r.lng &&
                activeRival?.nome === r.nome
              }
              onClick={() => setActiveRival(r)}
            />
          </Marker>
        ))}

        {activeRival && (
          <Popup
            longitude={activeRival.lng}
            latitude={activeRival.lat}
            closeButton={false}
            closeOnClick={false}
            anchor="bottom"
            offset={12}
            onClose={() => setActiveRival(null)}
          >
            <RivalPopupBody rival={activeRival} />
          </Popup>
        )}

        {pin && (
          <Marker longitude={pin.lng} latitude={pin.lat} anchor="center">
            <CenterPin lime />
          </Marker>
        )}

        <Source id="explorar-vias" type="geojson" data={viasFc}>
          <Layer
            id="explorar-vias-line"
            type="line"
            beforeId={overlayBefore}
            layout={{
              visibility: viasVisible ? 'visible' : 'none',
            }}
            paint={{
              'line-color': [
                'interpolate',
                ['linear'],
                ['get', 'rank'],
                0,
                '#ea580c',
                1,
                '#f97316',
                2,
                '#fb923c',
              ],
              'line-width': [
                'interpolate',
                ['linear'],
                ['get', 'rank'],
                0,
                5,
                2,
                3,
              ],
              'line-opacity': 0.88,
            }}
          />
        </Source>
      </MapLibreMap>
    </div>
  )
}

export function ExplorarMap(props: ExplorarMapProps) {
  if (glOk) return <ExplorarMapLibre {...props} />
  return <ExplorarMapPigeon {...props} />
}
