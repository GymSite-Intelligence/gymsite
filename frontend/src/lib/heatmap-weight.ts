/**
 * Pesos e paleta do heatmap (deck.gl, oceano vermelho → azul).
 *
 * Verificação manual: /mapa → lente Mercado (A9) → modo Calor ou Ambos.
 * score_concorrencia 10 = pouca pressão (azul); 0 = saturado (vermelho).
 */

/** RGBA 0–255 para `colorRange` do deck.gl HeatmapLayer. */
export type DeckColor = [number, number, number, number]
import type { PinRelatorio } from '@/hooks/useRelatoriosNoMapa'
import { OCEANO_FILL } from '@/lib/oceano'
import type { VereditoOceano } from '@/types/domain'

/** Intensidade por categoria A9 quando score_concorrencia ausente. */
export function oceanoHeatmapWeight(
  veredito: VereditoOceano | null,
): number {
  switch (veredito) {
    case 'OCEANO_AZUL':
      return 0.5
    case 'TRANSICAO':
      return 2
    case 'VERMELHO':
      return 4
    default:
      return 1
  }
}

/** Peso do ponto: prioriza score_concorrencia (0–10), senão oceano A9. */
export function pinHeatmapWeight(pin: PinRelatorio): number {
  const sc = pin.score_concorrencia
  if (sc != null && Number.isFinite(sc)) {
    return Math.max(0.5, 11 - sc)
  }
  return oceanoHeatmapWeight(pin.veredito_oceano)
}

/** HSL do design system → rgba para gradient do Google Maps. */
function hslToRgba(hsl: string, alpha = 1): string {
  const m = hsl.match(
    /hsl\(\s*([\d.]+)\s+([\d.]+)%\s+([\d.]+)%\s*\)/i,
  )
  if (!m) return `rgba(128,128,128,${alpha})`
  const h = Number(m[1]) / 360
  const s = Number(m[2]) / 100
  const l = Number(m[3]) / 100
  const hue2rgb = (p: number, q: number, t: number) => {
    let tt = t
    if (tt < 0) tt += 1
    if (tt > 1) tt -= 1
    if (tt < 1 / 6) return p + (q - p) * 6 * tt
    if (tt < 1 / 2) return q
    if (tt < 2 / 3) return p + (q - p) * (2 / 3 - tt) * 6
    return p
  }
  let r: number
  let g: number
  let b: number
  if (s === 0) {
    r = g = b = l
  } else {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s
    const p = 2 * l - q
    r = hue2rgb(p, q, h + 1 / 3)
    g = hue2rgb(p, q, h)
    b = hue2rgb(p, q, h - 1 / 3)
  }
  return `rgba(${Math.round(r * 255)},${Math.round(g * 255)},${Math.round(b * 255)},${alpha})`
}

function rgbaStringToDeck(rgba: string): DeckColor {
  const m = rgba.match(
    /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)/i,
  )
  if (!m) return [128, 128, 128, 255]
  const a =
    m[4] != null ? Math.round(Number(m[4]) * 255) : (255 as number)
  return [Number(m[1]), Number(m[2]), Number(m[3]), a]
}

/** Paleta deck.gl: baixo peso = azul (favorável), alto = vermelho. */
export function oceanoDeckColorRange(): DeckColor[] {
  return [
    rgbaStringToDeck(hslToRgba(OCEANO_FILL.OCEANO_AZUL)),
    rgbaStringToDeck(hslToRgba(OCEANO_FILL.TRANSICAO)),
    rgbaStringToDeck(hslToRgba(OCEANO_FILL.VERMELHO)),
  ]
}

/** Domínio estável de pesos (pinHeatmapWeight ~0.5–11). */
export function oceanoHeatmapColorDomain(): [number, number] {
  return [0.5, 11]
}

/**
 * Raio em pixels do HeatmapLayer — otimizado para z12–14 (escala bairro).
 * Em zoom país o raio é alto só pra não sumir; o mapa deve iniciar em z12–13.
 */
export function heatmapRadiusPixels(zoom: number): number {
  if (zoom <= 5) return 100
  if (zoom <= 7) return 72
  if (zoom <= 9) return 52
  if (zoom <= 11) return 42
  if (zoom <= 12) return 48
  if (zoom <= 13) return 56
  if (zoom <= 14) return 52
  if (zoom <= 15) return 40
  return 32
}

/** Peso por recência de abertura CNPJ (mapa municipal — entrantes 90d). */
export function entranteHeatmapWeight(peso?: number | null): number {
  if (peso != null && Number.isFinite(peso)) {
    return Math.max(0.35, Math.min(1.0, peso)) * 4
  }
  return 2
}

/** Intensidade: mais suave em z13–14 (blob de bairro legível). */
export function heatmapIntensity(zoom: number): number {
  if (zoom <= 6) return 2.8
  if (zoom <= 9) return 2
  if (zoom <= 11) return 1.6
  if (zoom <= 13) return 1.25
  if (zoom <= 14) return 1.1
  return 1
}
