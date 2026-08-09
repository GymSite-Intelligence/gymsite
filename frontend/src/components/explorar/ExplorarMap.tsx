import { useEffect, useMemo, useRef, useState } from 'react'
import { GeoJson, Map, Overlay } from 'pigeon-maps'
import { GYMSITE_PALETTE } from '@/config/gymsite-design-system'
import { cn } from '@/lib/utils'
import { explorarChrome } from './explorar-chrome'
import type { Camada, Lente, MapStyle } from './explorarIso'
import type { ExplorarIsoRings } from '@/hooks/useExplorarIsocronas'
import {
  CARTO_ATTRIBUTION,
  ISO_STYLE,
  influenceFeatureCollection,
  tileProvider,
} from './explorarIso'

function CenterPin() {
  return (
    <div
      aria-label="Ponto candidato"
      className="pointer-events-none size-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-white"
      style={{ background: '#22c55e', boxShadow: '0 2px 8px rgba(0,0,0,.5)' }}
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
        background: selected ? '#84cc01' : '#ef4444',
        boxShadow: '0 2px 6px rgba(0,0,0,.4)',
      }}
    />
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

export function ExplorarMap({
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
}: {
  center: [number, number]
  zoom: number
  pin: { lat: number; lng: number } | null
  rivals: ExplorarRival[]
  mapStyle: MapStyle
  camada: Camada
  lente: Lente
  isoRings: ExplorarIsoRings | null
  onClickMap: (lat: number, lng: number) => void
  onZoom: (z: number) => void
}) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ w: 0, h: 0 })
  const [activeRival, setActiveRival] = useState<ExplorarRival | null>(null)
  const iso = Boolean(pin && camada === 'influencia')
  const heat = Boolean(pin && camada === 'calor')
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
    if (!iso && !heat) {
      setLayerOn(false)
      return
    }
    setLayerOn(false)
    const t = window.setTimeout(() => setLayerOn(true), 40)
    return () => window.clearTimeout(t)
  }, [iso, heat, lente, isoRings, pin?.lat, pin?.lng])

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

  return (
    <div ref={wrapRef} className="h-full w-full">
      {size.w > 0 && size.h > 0 && (
        <Map
          width={size.w}
          height={size.h}
          defaultCenter={center}
          center={center}
          zoom={zoom}
          animate
          provider={tileProvider(mapStyle)}
          attribution={<span>{CARTO_ATTRIBUTION}</span>}
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
          {heat && pin && (
            <Overlay anchor={[pin.lat, pin.lng]}>
              <div
                className={cn(
                  'pointer-events-none size-90 -translate-x-1/2 -translate-y-1/2 rounded-full transition-opacity duration-500',
                  layerOn ? 'opacity-70' : 'opacity-0',
                )}
                style={{
                  background: `radial-gradient(circle, rgba(234,88,12,.45) 0%, ${GYMSITE_PALETTE.lime}47 40%, transparent 70%)`,
                }}
              />
            </Overlay>
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
              <div
                className={cn(
                  explorarChrome(),
                  'pointer-events-auto min-w-44 max-w-56 -translate-x-1/2 -translate-y-[calc(100%+10px)] rounded-lg border px-2.5 py-2 text-left shadow-lg',
                )}
                onClick={(e) => e.stopPropagation()}
              >
                <p className="text-xs font-semibold leading-snug text-foreground">{activeRival.nome}</p>
                <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                  {activeRival.endereco?.trim() || 'Endereço não informado no Maps'}
                </p>
              </div>
            </Overlay>
          )}
          {pin && (
            <Overlay anchor={[pin.lat, pin.lng]}>
              <CenterPin />
            </Overlay>
          )}
        </Map>
      )}
    </div>
  )
}
