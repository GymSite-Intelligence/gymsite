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

export const OSM_ATTRIBUTION = '© OpenStreetMap contributors'
export const ESRI_ATTRIBUTION = '© Esri'

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

const MAPLIBRE_GLYPHS = 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf'

const OSM_TILES = [
  'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
  'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
  'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
] as const

const ESRI_IMAGERY =
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'

function rasterStyle(sourceId: string, tiles: readonly string[], attribution: string) {
  return {
    version: 8 as const,
    glyphs: MAPLIBRE_GLYPHS,
    sources: {
      [sourceId]: {
        type: 'raster' as const,
        tiles: [...tiles],
        tileSize: 256,
        attribution,
      },
    },
    layers: [
      { id: sourceId, type: 'raster' as const, source: sourceId },
      {
        id: 'gs-overlay-anchor',
        type: 'background' as const,
        paint: { 'background-color': '#000000', 'background-opacity': 0 },
      },
    ],
  }
}

const MAPLIBRE_STYLES = {
  claro: rasterStyle('osm', OSM_TILES, OSM_ATTRIBUTION),
  escuro: rasterStyle('osm-dark', OSM_TILES, OSM_ATTRIBUTION),
  satelite: rasterStyle('esri', [ESRI_IMAGERY], ESRI_ATTRIBUTION),
} as const

export function mapLibreStyle(style: MapStyle) {
  return MAPLIBRE_STYLES[style]
}

export function tileProvider(style: MapStyle) {
  if (style === 'satelite') {
    return (x: number, y: number, z: number) =>
      `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`
  }
  return (x: number, y: number, z: number) => {
    const host = ['a', 'b', 'c'][Math.abs(x + y) % 3]
    return `https://${host}.tile.openstreetmap.org/${z}/${x}/${y}.png`
  }
}

export function topViasToFeatureCollection(
  vias: { nome_via?: string; fluxo_score?: number; coords?: [number, number][] }[],
) {
  return {
    type: 'FeatureCollection' as const,
    features: vias
      .filter((v) => Array.isArray(v.coords) && v.coords.length >= 2)
      .map((v, i) => ({
        type: 'Feature' as const,
        properties: {
          nome: v.nome_via ?? '',
          fluxo: v.fluxo_score ?? 0,
          rank: i,
        },
        geometry: { type: 'LineString' as const, coordinates: v.coords! },
      })),
  }
}

export function recorteWkt(lat: number, lng: number, lente: Lente, steps = 24): string {
  const ring = ringToLngLatClosed(circleRing(lat, lng, LENTE_M[lente], steps))
  const body = ring.map(([x, y]) => `${x} ${y}`).join(', ')
  return `POLYGON((${body}))`
}

export function cartoBuscaEmbedUrl(
  base: string,
  opts: {
    lat?: number
    lng?: number
    lente: Lente
    search?: string
  },
): string {
  const root = base.trim()
  if (!root) return ''
  const lat = opts.lat
  const lng = opts.lng
  if (lat == null || lng == null || !Number.isFinite(lat) || !Number.isFinite(lng)) {
    return root
  }
  const params = new URLSearchParams()
  params.set('lat', String(lat))
  params.set('lng', String(lng))
  params.set('zoom', opts.lente === 'bairro' ? '13' : '14')
  params.set('layers', '0,1')
  params.set('mask', recorteWkt(lat, lng, opts.lente))
  const q = (opts.search || '').trim()
  if (q) params.set('search', q)
  const join = root.includes('?') ? '&' : '?'
  return `${root}${join}${params.toString()}`
}
