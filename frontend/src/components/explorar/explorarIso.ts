export type MapStyle = 'claro' | 'escuro' | 'satelite'
export type Camada = 'off' | 'calor' | 'influencia'
export type ModoDesloc = 'pe' | 'carro'
export type Lente = '500m' | '1km' | 'bairro'
export type TipoNegocioExplorar =
  | 'academia'
  | 'studio_funcional'
  | 'crossfit_box'
  | 'studio_pilates'

export const EXPLORAR_TIPOS: readonly { id: TipoNegocioExplorar; label: string }[] = [
  { id: 'academia', label: 'Academia' },
  { id: 'studio_funcional', label: 'Studio' },
  { id: 'crossfit_box', label: 'Crossfit' },
  { id: 'studio_pilates', label: 'Pilates' },
] as const

export const LENTE_M: Record<Lente, number> = {
  '500m': 500,
  '1km': 1000,
  bairro: 1400,
}

export type LatLng = [number, number]

export const ISO_STYLE = {
  m15: { stroke: '#ea580c', fill: '#fdba74', fillOpacity: 0.28 },
  m10: { stroke: '#ca8a04', fill: '#facc15', fillOpacity: 0.32 },
  m5: { stroke: '#16a34a', fill: '#4ade80', fillOpacity: 0.38 },
} as const

/** Círculo regular da lente (metros → lat/lng). */
export function circleRing(lat: number, lng: number, meters: number, steps = 64): LatLng[] {
  const mLat = meters / 111320
  const mLng = meters / (111320 * Math.cos((lat * Math.PI) / 180))
  const ring: LatLng[] = []
  for (let i = 0; i < steps; i++) {
    const t = (i / steps) * Math.PI * 2
    ring.push([lat + Math.cos(t) * mLat, lng + Math.sin(t) * mLng])
  }
  return ring
}

function ringToLngLatClosed(ring: LatLng[]): [number, number][] {
  const coords = ring.map(([lat, lng]) => [lng, lat] as [number, number])
  if (coords.length > 0) coords.push(coords[0])
  return coords
}

export function influenceFeatureCollection(
  lat: number,
  lng: number,
  lente: Lente,
  isoRings: { m5?: LatLng[]; m10?: LatLng[]; m15?: LatLng[] } | null,
  opts?: { lenteCircle?: boolean },
) {
  const isoFeatures = (['m15', 'm10', 'm5'] as const)
    .map((key) => {
      const ring = isoRings?.[key]
      if (!ring?.length) return null
      return {
        type: 'Feature' as const,
        properties: { key: key as string },
        geometry: {
          type: 'Polygon' as const,
          coordinates: [ringToLngLatClosed(ring)],
        },
      }
    })
    .filter((f): f is NonNullable<typeof f> => f != null)
  const drawCircle = opts?.lenteCircle ?? lente !== 'bairro'
  const features = [...isoFeatures]
  if (drawCircle) {
    features.push({
      type: 'Feature' as const,
      properties: { key: 'lente' },
      geometry: {
        type: 'Polygon' as const,
        coordinates: [ringToLngLatClosed(circleRing(lat, lng, LENTE_M[lente]))],
      },
    })
  }
  return {
    type: 'FeatureCollection' as const,
    features,
  }
}

/** OSM direto — CARTO raster (`light_all`/`dark_all`) agora exige API key e marca água. */
export const OSM_ATTRIBUTION = '© OpenStreetMap contributors'
export const CARTO_ATTRIBUTION = OSM_ATTRIBUTION

export function tileProvider(style: MapStyle) {
  return (x: number, y: number, z: number, _dpr?: number) => {
    if (style === 'satelite') {
      return `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`
    }
    const host = ['a', 'b', 'c'][Math.abs(x + y) % 3]
    return `https://${host}.tile.openstreetmap.org/${z}/${x}/${y}.png`
  }
}

export function readLs<T extends string>(key: string, fallback: T, allowed: readonly T[]): T {
  try {
    const v = localStorage.getItem(key) as T | null
    if (v && (allowed as readonly string[]).includes(v)) return v
  } catch {
    /* noop */
  }
  return fallback
}

export function writeLs(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* noop */
  }
}
