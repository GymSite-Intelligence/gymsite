/**
 * Níveis de zoom — mapa de relatórios (bairro, não rua nem Brasil).
 *
 * ~13 ≈ 3–5 km (bairro) · ~12 ≈ cidade · ~4 ≈ país
 */
import type { PinCluster, PinRelatorio } from '@/hooks/useRelatoriosNoMapa'

export const MAP_ZOOM_BAIRRO = 13
export const MAP_ZOOM_CIDADE = 12
export const MAP_ZOOM_BRASIL = 4

/** Teto ao enquadrar pins (calor ou bairro) — evita zoom 15+ ou vista nacional. */
export const MAP_MAX_ZOOM_FIT = 13
export const MAP_MIN_ZOOM_FIT = 10

const norm = (s: string) => s.trim().toLowerCase()

export function localidadeKey(bairro: string, cidade: string): string {
  return `${norm(bairro)}|${norm(cidade)}`
}

/** Todos os pins visíveis no mesmo bairro+cidade do pin de referência. */
export function pinsDoMesmoBairro(
  allPins: PinRelatorio[],
  ref: PinRelatorio,
): PinRelatorio[] {
  const key = localidadeKey(ref.bairro, ref.cidade)
  return allPins.filter((p) => localidadeKey(p.bairro, p.cidade) === key)
}

export function bairroPinsForCluster(
  cluster: PinCluster,
  allPins: PinRelatorio[],
): PinRelatorio[] {
  const ref = cluster.pins[0]
  if (!ref) return cluster.pins
  const noBairro = cluster.pins.length === 1
  const sameBairro = pinsDoMesmoBairro(allPins, ref)
  return sameBairro.length > 1 || noBairro ? sameBairro : cluster.pins
}

export function focusLabelFromPins(
  pins: PinRelatorio[],
): { bairro: string; cidade: string } | null {
  const ref = pins[0]
  if (!ref) return null
  const bairro = ref.bairro?.trim() || 'Bairro'
  const cidade = ref.cidade?.trim() || 'Cidade'
  return { bairro, cidade }
}

/** Rótulo ao enquadrar vários pins (modo calor / filtros amplos). */
export function focusLabelForViewport(
  pins: PinRelatorio[],
): { bairro: string; cidade: string } | null {
  if (pins.length === 0) return null
  const cidades = new Set(pins.map((p) => norm(p.cidade)))
  const bairros = new Set(pins.map((p) => norm(p.bairro)))
  if (bairros.size === 1 && cidades.size === 1) {
    return focusLabelFromPins(pins)
  }
  if (cidades.size === 1) {
    const cidade = pins[0].cidade?.trim() || 'Cidade'
    const n = bairros.size
    return {
      bairro: n === 1 ? pins[0].bairro?.trim() || 'Bairro' : `${n} bairros`,
      cidade,
    }
  }
  return {
    bairro: `${pins.length} pontos`,
    cidade: 'várias cidades',
  }
}

export interface LatLngBounds {
  minLat: number
  maxLat: number
  minLng: number
  maxLng: number
}

export function boundsFromPins(pins: PinRelatorio[]): LatLngBounds | null {
  if (pins.length === 0) return null
  let minLat = pins[0].lat
  let maxLat = pins[0].lat
  let minLng = pins[0].lng
  let maxLng = pins[0].lng
  for (const p of pins) {
    minLat = Math.min(minLat, p.lat)
    maxLat = Math.max(maxLat, p.lat)
    minLng = Math.min(minLng, p.lng)
    maxLng = Math.max(maxLng, p.lng)
  }
  return { minLat, maxLat, minLng, maxLng }
}

function spreadToZoom(maxSpread: number): number {
  if (maxSpread > 10) return MAP_ZOOM_BRASIL
  if (maxSpread > 1) return MAP_ZOOM_CIDADE
  if (maxSpread > 0.08) return MAP_ZOOM_BAIRRO
  if (maxSpread > 0.02) return MAP_ZOOM_BAIRRO
  return MAP_ZOOM_BAIRRO
}

function clampZoom(zoom: number, maxZoom: number, minZoom: number): number {
  return Math.min(maxZoom, Math.max(minZoom, zoom))
}

/** Centro + zoom para pigeon-maps a partir de um conjunto de pins. */
export function viewportFromPins(
  pins: PinRelatorio[],
  opts?: { maxZoom?: number; minZoom?: number },
): { center: [number, number]; zoom: number } {
  const maxZoom = opts?.maxZoom ?? MAP_MAX_ZOOM_FIT
  const minZoom = opts?.minZoom ?? MAP_MIN_ZOOM_FIT

  if (pins.length === 0) {
    return { center: [-15.7942, -47.8822], zoom: MAP_ZOOM_BRASIL }
  }
  if (pins.length === 1) {
    return {
      center: [pins[0].lat, pins[0].lng],
      zoom: clampZoom(MAP_ZOOM_BAIRRO, maxZoom, minZoom),
    }
  }

  const b = boundsFromPins(pins)
  if (!b) {
    return { center: [pins[0].lat, pins[0].lng], zoom: MAP_ZOOM_BAIRRO }
  }

  const center: [number, number] = [
    (b.minLat + b.maxLat) / 2,
    (b.minLng + b.maxLng) / 2,
  ]
  const spreadLat = b.maxLat - b.minLat
  const spreadLng = b.maxLng - b.minLng
  const maxSpread = Math.max(spreadLat, spreadLng, 0.008)
  const zoom = clampZoom(spreadToZoom(maxSpread), maxZoom, minZoom)
  return { center, zoom }
}

/** @deprecated Use viewportFromPins / fly no Google — mantido só se algo importar. */
export function targetZoomForCluster(
  _pinCount: number,
  currentZoom: number,
): number {
  return Math.max(currentZoom, MAP_ZOOM_BAIRRO)
}

/** Aplica fitBounds no Google Maps e limita zoom ao teto de bairro. */
export function fitGoogleBoundsWithCap(
  map: google.maps.Map,
  pins: PinRelatorio[],
  padding = 56,
  maxZoom = MAP_MAX_ZOOM_FIT,
): number {
  if (pins.length === 0) return map.getZoom() ?? MAP_ZOOM_BAIRRO

  if (pins.length === 1) {
    const p = pins[0]
    map.panTo({ lat: p.lat, lng: p.lng })
    const z = Math.min(maxZoom, MAP_ZOOM_BAIRRO)
    map.setZoom(z)
    return z
  }

  const bounds = new google.maps.LatLngBounds()
  for (const p of pins) {
    bounds.extend({ lat: p.lat, lng: p.lng })
  }
  map.fitBounds(bounds, padding)

  const applyCap = () => {
    const z = map.getZoom()
    if (z != null && z > maxZoom) {
      map.setZoom(maxZoom)
      return maxZoom
    }
    return z ?? MAP_ZOOM_BAIRRO
  }

  const zNow = applyCap()
  if (zNow > maxZoom) return zNow
  google.maps.event.addListenerOnce(map, 'idle', () => {
    applyCap()
  })
  return zNow
}
