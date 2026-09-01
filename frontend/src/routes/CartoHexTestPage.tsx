import { useState } from 'react'
import { fetchHexCount, type HexCountOk } from '@/lib/cartoHex'

const DEFAULT_LAT = -3.7455
const DEFAULT_LNG = -38.4855

function parseCoord(raw: string): number {
  return Number(raw.trim().replace(',', '.'))
}

function stampLine(r: HexCountOk): string {
  return `${r.n_academias} academias · ${r.base} · ${r.fonte} · ${r.gerado_em}`
}

export function CartoHexTestPage() {
  const [lat, setLat] = useState(String(DEFAULT_LAT))
  const [lng, setLng] = useState(String(DEFAULT_LNG))
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [resultado, setResultado] = useState<HexCountOk | null>(null)

  const buscar = async () => {
    const latN = parseCoord(lat)
    const lngN = parseCoord(lng)
    if (!Number.isFinite(latN) || !Number.isFinite(lngN)) {
      setErro('Latitude e longitude devem ser números válidos.')
      setResultado(null)
      return
    }
    setCarregando(true)
    setErro(null)
    setResultado(null)
    try {
      const r = await fetchHexCount(latN, lngN)
      setResultado(r)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao buscar hex.')
    } finally {
      setCarregando(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Hex CARTO</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Contagem de academias por hex H3 — ferramenta interna de teste (logado).
        </p>
      </header>

      <div className="mb-6 flex flex-wrap items-end gap-3 rounded-lg border border-border bg-card p-4">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">Latitude</span>
          <input
            type="number"
            step="any"
            value={lat}
            onChange={(e) => setLat(e.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-foreground"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">Longitude</span>
          <input
            type="number"
            step="any"
            value={lng}
            onChange={(e) => setLng(e.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-foreground"
          />
        </label>
        <button
          type="button"
          onClick={buscar}
          disabled={carregando}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {carregando ? 'Buscando…' : 'Buscar hex'}
        </button>
      </div>

      {erro && (
        <p className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {erro}
        </p>
      )}

      {resultado && (
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-3xl font-semibold tabular-nums text-foreground">
            {resultado.n_academias}
          </p>
          <p className="mt-2 text-sm text-muted-foreground">{stampLine(resultado)}</p>
          <p className="mt-3 text-xs text-muted-foreground">
            Hex {resultado.hex} · {resultado.cidade}
          </p>
        </div>
      )}
    </div>
  )
}
