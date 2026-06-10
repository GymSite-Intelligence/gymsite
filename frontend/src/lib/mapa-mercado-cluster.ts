/** Agrupamento leve de pins no mapa municipal (viewer) — não confundir com /mapa portfolio. */

export interface MercadoCluster<T> {
  lat: number
  lng: number
  items: T[]
}

/** Tolerância ~500m em zoom de cidade (z11). */
export function mercadoClusterTolerance(zoom: number): number {
  if (zoom <= 10) return 0.02
  if (zoom <= 12) return 0.005
  if (zoom <= 14) return 0.001
  return 0.0003
}

export function agruparMercadoPins<T extends { lat: number; lng: number }>(
  pins: T[],
  tolDegrees: number,
): MercadoCluster<T>[] {
  const clusters: MercadoCluster<T>[] = []
  for (const pin of pins) {
    const existente = clusters.find(
      (c) =>
        Math.abs(c.lat - pin.lat) <= tolDegrees &&
        Math.abs(c.lng - pin.lng) <= tolDegrees,
    )
    if (existente) {
      existente.items.push(pin)
    } else {
      clusters.push({ lat: pin.lat, lng: pin.lng, items: [pin] })
    }
  }
  return clusters
}

export const MERCADO_CLUSTER_THRESHOLD = 50
