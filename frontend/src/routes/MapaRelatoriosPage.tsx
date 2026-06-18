/**
 * MapaRelatoriosPage — visualização geográfica dos relatórios.
 *
 * Cada pin representa o bairro analisado no relatório (geocode bairro+cidade).
 * Mapa: Google Maps JS + deck.gl heatmap (oceano) quando a chave está no backend;
 * fallback pigeon-maps (OSM) se VITE_MAP_PROVIDER=pigeon ou chave indisponível.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { Map, Marker } from 'pigeon-maps'
import {
  GoogleMapOceano,
  type MapaCamada,
} from '@/components/maps/GoogleMapOceano'
import {
  LeituraTerritorio,
  type ResumoTerritorio,
} from '@/components/maps/LeituraTerritorio'
import { useMapsJsConfig } from '@/hooks/useMapsJsConfig'
import { OCEANO_FILL } from '@/lib/oceano'
import {
  ChevronRight,
  ExternalLink,
  GitCompare,
  Image as ImageIcon,
  Search,
  X,
} from 'lucide-react'
import {
  useRelatoriosNoMapa,
  calcularViewportInicial,
  agruparPinsCoLocalizados,
  tolerancePorZoom,
  type PinRelatorio,
} from '@/hooks/useRelatoriosNoMapa'
import { cn } from '@/lib/utils'
import {
  bairroPinsForCluster,
  focusLabelForViewport,
  focusLabelFromPins,
  viewportFromPins,
} from '@/lib/map-fly-to'
import { PinVeredito } from '@/components/domain/PinVeredito'
import { PinOceano } from '@/components/domain/PinOceano'
import { VeredictoBadge } from '@/components/domain/VeredictoBadge'
import { OceanoBadge } from '@/components/domain/OceanoBadge'
import { OCEANO_LEGEND_ITEMS } from '@/lib/oceano'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import type { Veredito } from '@/types/domain'

const VEREDITOS: { value: Veredito | ''; label: string }[] = [
  { value: '', label: 'Todos' },
  { value: 'APROVADO', label: 'Aprovado' },
  { value: 'APROVADO COM RESSALVAS', label: 'Com Ressalvas' },
  { value: 'INVESTIGAR MAIS', label: 'Investigar' },
  { value: 'REPROVADO', label: 'Reprovado' },
]

interface MapaSearch {
  cidade?: string
  veredito?: Veredito
}

type MapaLente = 'viabilidade' | 'mercado'

const MAP_PROVIDER =
  (import.meta.env.VITE_MAP_PROVIDER as string | undefined)?.trim() || 'google'

export function MapaRelatoriosPage() {
  const navigate = useNavigate()
  const search = useSearch({ strict: false }) as MapaSearch
  const [lente, setLente] = useState<MapaLente>('viabilidade')
  const { pins, isLoading, isGeocodingBairros, total, semCoordenadas, totalResumos } =
    useRelatoriosNoMapa({
    cidade: search.cidade,
    veredito: search.veredito,
  })

  // R2 — resumo AGREGADO do recorte visivel (sem dados crus/PII) p/ a leitura IA.
  const resumoTerritorio = useMemo<ResumoTerritorio | null>(() => {
    if (!pins || pins.length === 0) return null
    const counts: Record<string, number> = {}
    const vereditos: Record<string, number> = {}
    const bairros: string[] = []
    for (const p of pins) {
      const oc = (p as { veredito_oceano?: string }).veredito_oceano
      if (oc) counts[oc] = (counts[oc] ?? 0) + 1
      const vd = (p as { veredito?: string }).veredito
      if (vd) vereditos[vd] = (vereditos[vd] ?? 0) + 1
      const ba = (p as { bairro?: string }).bairro
      if (ba && !bairros.includes(ba)) bairros.push(ba)
    }
    return {
      cidade: search.cidade ?? '',
      bbox: null,
      counts,
      top_bairros: bairros.slice(0, 12),
      vereditos,
    }
  }, [pins, search.cidade])
  const { data: mapsJs, isLoading: loadingMapsJs, isError: mapsJsError } =
    useMapsJsConfig()
  const [googleMapFailed, setGoogleMapFailed] = useState(false)
  const useGoogleMap =
    MAP_PROVIDER !== 'pigeon' &&
    !loadingMapsJs &&
    !mapsJsError &&
    !googleMapFailed &&
    Boolean(mapsJs?.configured && mapsJs.key)
  const [camada, setCamada] = useState<MapaCamada>('both')
  const [clusterAtivoIdx, setClusterAtivoIdx] = useState<number | null>(null)
  const [mapFocus, setMapFocus] = useState<{
    bairro: string
    cidade: string
  } | null>(null)
  const camadaAnteriorRef = useRef<MapaCamada>('both')
  // Modo seleção pra comparação — ativado pelo botão "Comparar"
  const [modoComparar, setModoComparar] = useState(false)
  const [selecionados, setSelecionados] = useState<string[]>([])

  // Viewport recalcula quando pins mudam (filtros aplicados)
  const viewport = useMemo(() => calcularViewportInicial(pins), [pins])

  // Zoom dinâmico (Map emite onBoundsChanged com center+zoom atuais).
  // Usamos pra ajustar a tolerância de agrupamento: zoom out junta mais
  // pins num cluster, zoom in desagrupa.
  const [zoomAtual, setZoomAtual] = useState<number>(viewport.zoom)
  const [pigeonCenter, setPigeonCenter] = useState<[number, number]>(
    viewport.center,
  )
  const [pigeonZoom, setPigeonZoom] = useState<number>(viewport.zoom)
  // Sincroniza quando filtros mudam (viewport recalcula → reseta zoom)
  useEffect(() => {
    setZoomAtual(viewport.zoom)
    setPigeonCenter(viewport.center)
    setPigeonZoom(viewport.zoom)
  }, [viewport.center, viewport.zoom])

  const heatmapDisponivel =
    useGoogleMap && Boolean(mapsJs?.key) && !googleMapFailed

  useEffect(() => {
    if (lente === 'viabilidade' && camada !== 'pins') {
      setCamada('pins')
    }
  }, [lente, camada])

  useEffect(() => {
    if (!heatmapDisponivel && (camada === 'heat' || camada === 'both')) {
      setCamada('pins')
    }
  }, [heatmapDisponivel, camada])

  useEffect(() => {
    setMapFocus(null)
    setClusterAtivoIdx(null)
  }, [viewport.center, viewport.zoom, pins.length])

  useEffect(() => {
    const nowHeat = camada === 'heat' || camada === 'both'
    const wasHeat =
      camadaAnteriorRef.current === 'heat' ||
      camadaAnteriorRef.current === 'both'
    camadaAnteriorRef.current = camada
    if (nowHeat && !wasHeat && pins.length > 0) {
      setMapFocus(focusLabelForViewport(pins))
    }
  }, [camada, pins])

  // Agrupa pins co-localizados pelo nível de zoom atual
  const clusters = useMemo(
    () => agruparPinsCoLocalizados(pins, tolerancePorZoom(zoomAtual)),
    [pins, zoomAtual],
  )
  const clusterAtivo = useMemo(
    () =>
      clusterAtivoIdx != null ? clusters[clusterAtivoIdx] ?? null : null,
    [clusters, clusterAtivoIdx],
  )

  function handleClusterClick(idx: number) {
    const c = clusters[idx]
    if (!c) return

    const bairroPins = bairroPinsForCluster(c, pins)
    setMapFocus(focusLabelFromPins(bairroPins))

    if (modoComparar && c.pins.length === 1) {
      toggleSelecao(c.pins[0].id)
      setClusterAtivoIdx(idx)
      return
    }
    setClusterAtivoIdx(idx)
  }

  function handlePigeonClusterClick(idx: number) {
    const c = clusters[idx]
    if (!c) return
    const bairroPins = bairroPinsForCluster(c, pins)
    const { center, zoom } = viewportFromPins(bairroPins)
    setPigeonCenter(center)
    setPigeonZoom(zoom)
    setZoomAtual(zoom)
    handleClusterClick(idx)
  }

  function fecharCluster() {
    setClusterAtivoIdx(null)
    setMapFocus(null)
  }

  function toggleSelecao(pinId: string) {
    setSelecionados((prev) => {
      if (prev.includes(pinId)) return prev.filter((x) => x !== pinId)
      if (prev.length >= 2) return [prev[1], pinId] // FIFO mantém só 2
      return [...prev, pinId]
    })
  }

  function irParaComparador() {
    if (selecionados.length !== 2) return
    navigate({
      to: '/comparar',
      search: { a: selecionados[0], b: selecionados[1] },
    })
  }

  function updateSearch(patch: Partial<MapaSearch>) {
    navigate({
      to: '/mapa',
      // biome-ignore lint/suspicious/noExplicitAny: TanStack search merge
      search: ((prev: any) => ({ ...prev, ...patch })) as any,
    })
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Mapa de Relatórios
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {isLoading ? (
              'Carregando relatórios…'
            ) : totalResumos === 0 ? (
              'Nenhum relatório encontrado'
            ) : total === 0 ? (
              <>
                {totalResumos} relatório{totalResumos === 1 ? '' : 's'} — nenhum
                com coordenadas para o mapa
              </>
            ) : (
              <>
                {total} pin{total === 1 ? '' : 's'} ({clusters.length} marcador
                {clusters.length === 1 ? '' : 'es'} após agrupamento)
                {totalResumos > total && (
                  <span className="ml-1 text-veredito-ressalvas">
                    · {semCoordenadas} sem coordenadas (de {totalResumos})
                  </span>
                )}
              </>
            )}
            {isGeocodingBairros && !isLoading && total > 0 && (
              <span className="ml-2 text-muted-foreground/80">
                · refinando posições por bairro…
              </span>
            )}
          </p>
          {mapFocus && pins.length > 0 && (
            <p className="text-xs text-foreground/80 mt-1 font-medium">
              Visualizando:{' '}
              <span className="text-foreground">
                {mapFocus.bairro} · {mapFocus.cidade}
              </span>
            </p>
          )}
        </div>
        <Button
          variant={modoComparar ? 'default' : 'outline'}
          size="sm"
          onClick={() => {
            setModoComparar((v) => !v)
            setSelecionados([])
            fecharCluster()
          }}
        >
          <GitCompare size={14} />
          {modoComparar ? 'Cancelar comparação' : 'Comparar 2 relatórios'}
        </Button>
      </div>

      {/* Filtros */}
      <div className="flex items-center gap-2 flex-wrap p-3 rounded-lg border border-border bg-card">
        <div className="flex rounded-md border border-border overflow-hidden shrink-0">
          <button
            type="button"
            className={cn(
              'px-3 py-1.5 text-xs font-medium transition-colors',
              lente === 'viabilidade'
                ? 'bg-primary text-primary-foreground'
                : 'bg-transparent text-muted-foreground hover:bg-muted',
            )}
            onClick={() => setLente('viabilidade')}
          >
            Viabilidade (A6)
          </button>
          <button
            type="button"
            className={cn(
              'px-3 py-1.5 text-xs font-medium transition-colors',
              lente === 'mercado'
                ? 'bg-primary text-primary-foreground'
                : 'bg-transparent text-muted-foreground hover:bg-muted',
            )}
            onClick={() => setLente('mercado')}
          >
            Mercado (A9)
          </button>
        </div>
        <div className="relative flex-1 min-w-[200px]">
          <Search
            size={14}
            className="absolute left-2.5 top-2.5 text-muted-foreground pointer-events-none"
          />
          <Input
            placeholder="Filtrar por cidade ou bairro..."
            className="pl-8"
            value={search.cidade ?? ''}
            onChange={(e) => updateSearch({ cidade: e.target.value || undefined })}
          />
        </div>
        <select
          value={search.veredito ?? ''}
          onChange={(e) =>
            updateSearch({
              veredito: (e.target.value as Veredito) || undefined,
            })
          }
          className="h-9 rounded-md border border-border bg-transparent px-3 text-sm"
        >
          {VEREDITOS.map((v) => (
            <option key={v.value} value={v.value} className="bg-background">
              {v.label}
            </option>
          ))}
        </select>
        {lente === 'mercado' && (
          <div
            className="flex rounded-md border border-border overflow-hidden shrink-0"
            title={
              heatmapDisponivel
                ? undefined
                : 'Calor e Ambos exigem Google Maps (deck.gl). Configure GOOGLE_MAPS_API_KEY no backend.'
            }
          >
            {(
              [
                { id: 'pins' as const, label: 'Pins' },
                { id: 'heat' as const, label: 'Calor' },
                { id: 'both' as const, label: 'Ambos' },
              ] as const
            ).map((opt) => {
              const desabilitado =
                !heatmapDisponivel && (opt.id === 'heat' || opt.id === 'both')
              return (
                <button
                  key={opt.id}
                  type="button"
                  disabled={desabilitado}
                  className={cn(
                    'px-3 py-1.5 text-xs font-medium transition-colors',
                    camada === opt.id
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-transparent text-muted-foreground hover:bg-muted',
                    desabilitado && 'opacity-40 cursor-not-allowed hover:bg-transparent',
                  )}
                  onClick={() => {
                    if (!desabilitado) setCamada(opt.id)
                  }}
                >
                  {opt.label}
                </button>
              )
            })}
          </div>
        )}
        {(search.cidade || search.veredito) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate({ to: '/mapa', search: {} })}
          >
            <X size={14} /> Limpar
          </Button>
        )}
      </div>

      {/* Mapa + popover lateral */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
        {/* Mapa */}
        <div className="relative h-[600px] min-h-[320px] rounded-lg border border-border overflow-hidden bg-muted/20">
          {mapFocus && pins.length > 0 && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
              <div className="rounded-full border border-border bg-card/95 backdrop-blur px-3 py-1 text-[11px] font-medium shadow-sm">
                {mapFocus.bairro} · {mapFocus.cidade}
              </div>
            </div>
          )}
          {isLoading || loadingMapsJs ? (
            <Skeleton className="h-full w-full min-h-[320px]" />
          ) : pins.length === 0 ? (
            <MapaVazio totalResumos={totalResumos} />
          ) : useGoogleMap && mapsJs?.key ? (
            <GoogleMapOceano
              apiKey={mapsJs.key}
              mapId={mapsJs.mapId}
              viewportCenter={{
                lat: viewport.center[0],
                lng: viewport.center[1],
              }}
              viewportZoom={viewport.zoom}
              mapZoom={zoomAtual}
              clusters={clusters}
              heatmapPins={pins}
              lente={lente}
              camada={lente === 'mercado' ? camada : 'pins'}
              clusterAtivoIdx={clusterAtivoIdx}
              selecionados={selecionados}
              onZoomChange={setZoomAtual}
              onClusterClick={handleClusterClick}
              onLoadError={() => setGoogleMapFailed(true)}
              className="h-full"
            />
          ) : (
            <Map
              center={pigeonCenter}
              zoom={pigeonZoom}
              attribution={false}
              onBoundsChanged={({ center, zoom }) => {
                setPigeonCenter(center)
                setPigeonZoom(zoom)
                setZoomAtual(zoom)
              }}
            >
              {clusters.map((c, idx) => {
                const algumSelecionado = c.pins.some((p) =>
                  selecionados.includes(p.id),
                )
                return (
                  <Marker
                    key={`${c.lat}-${c.lng}-${idx}`}
                    anchor={[c.lat, c.lng]}
                    onClick={() => handlePigeonClusterClick(idx)}
                  >
                    {lente === 'mercado' ? (
                      <PinOceano
                        veredito={c.oceano_representativo}
                        ativo={clusterAtivoIdx === idx && !algumSelecionado}
                        selecionado={algumSelecionado}
                        count={c.pins.length}
                      />
                    ) : (
                      <PinVeredito
                        veredito={c.veredito_representativo}
                        ativo={clusterAtivoIdx === idx && !algumSelecionado}
                        selecionado={algumSelecionado}
                        count={c.pins.length}
                      />
                    )}
                  </Marker>
                )
              })}
            </Map>
          )}

          {googleMapFailed && pins.length > 0 && (
            <div className="absolute top-3 right-3 z-10 max-w-[240px] rounded-md border border-border bg-card/95 px-2 py-1.5 text-[10px] text-muted-foreground shadow-sm">
              Google Maps indisponível — exibindo mapa OpenStreetMap (pigeon).
            </div>
          )}

          {pins.length > 0 &&
            (lente === 'mercado' ? (
              <>
                <LegendaOceano />
                {heatmapDisponivel &&
                  (camada === 'heat' || camada === 'both') && (
                  <LegendaHeatmap />
                )}
              </>
            ) : (
              <LegendaVereditos />
            ))}

          {/* R2 — Leitura do territorio (IA) sobre o recorte do heatmap (vista de mercado) */}
          {lente === 'mercado' && resumoTerritorio && pins.length > 0 && (
            <div className="absolute bottom-3 left-3 z-10 w-[260px] max-w-[80%]">
              <LeituraTerritorio resumo={resumoTerritorio} enabled={!isLoading} />
            </div>
          )}
        </div>

        {/* Painel lateral — pin selecionado ou cluster */}
        <aside className="rounded-lg border border-border bg-card p-4 h-fit lg:sticky lg:top-4">
          {clusterAtivo ? (
            clusterAtivo.pins.length === 1 ? (
              // Pin único — mostra detalhes
              <DetalhePinSelecionado
                pin={clusterAtivo.pins[0]}
                modoComparar={modoComparar}
                selecionado={selecionados.includes(clusterAtivo.pins[0].id)}
                onToggleSelecao={() =>
                  toggleSelecao(clusterAtivo.pins[0].id)
                }
                onAbrir={() =>
                  navigate({
                    to: '/relatorios/$relatorioId',
                    params: { relatorioId: clusterAtivo.pins[0].id },
                  })
                }
                onFechar={fecharCluster}
              />
            ) : (
              // Cluster com N>1 — mostra lista
              <ClusterLista
                pins={clusterAtivo.pins}
                modoComparar={modoComparar}
                selecionados={selecionados}
                onToggleSelecao={toggleSelecao}
                onAbrirRelatorio={(id) =>
                  navigate({
                    to: '/relatorios/$relatorioId',
                    params: { relatorioId: id },
                  })
                }
                onFechar={fecharCluster}
              />
            )
          ) : (
            <div className="text-sm text-muted-foreground py-8 text-center space-y-2">
              <p>
                {modoComparar
                  ? 'Clique nos pins pra selecionar 2 relatórios pra comparar'
                  : 'Clique num pin pra ver detalhes'}
              </p>
              <p className="text-[10px] font-mono">
                Cores: verde=aprovado · amarelo=ressalvas · azul=investigar ·
                vermelho=reprovado
              </p>
              <p className="text-[10px] font-mono text-muted-foreground/70">
                Pins com número agrupam relatórios próximos. Dê zoom in (scroll
                ou botão +) pra separar.
              </p>
            </div>
          )}
        </aside>
      </div>

      {/* Barra flutuante de comparação */}
      {modoComparar && (
        <div
          className={cn(
            'fixed bottom-6 left-1/2 -translate-x-1/2 z-40 transition-all',
            selecionados.length === 0
              ? 'pointer-events-none opacity-0 translate-y-2'
              : 'opacity-100',
          )}
        >
          <div className="flex items-center gap-3 rounded-lg border border-border bg-card shadow-lg px-4 py-2.5">
            <span className="text-xs font-mono text-muted-foreground">
              {selecionados.length}/2 selecionados
            </span>
            <Button
              size="sm"
              disabled={selecionados.length !== 2}
              onClick={irParaComparador}
            >
              <GitCompare size={14} /> Comparar
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Subcomponentes ────────────────────────────────────────────────────

function DetalhePinSelecionado({
  pin,
  modoComparar,
  selecionado,
  onToggleSelecao,
  onAbrir,
  onFechar,
}: {
  pin: PinRelatorio
  modoComparar: boolean
  selecionado: boolean
  onToggleSelecao: () => void
  onAbrir: () => void
  onFechar: () => void
}) {
  // URL pra abrir Street View interativo no Google Maps com pano (não Static).
  // Formato `?cbll=lat,lng&layer=c` ativa o modo Street View na própria URL.
  const streetViewInterativoUrl = `https://www.google.com/maps?q=&layer=c&cbll=${pin.lat},${pin.lng}`

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm truncate">{pin.bairro}</h3>
          <p className="text-xs text-muted-foreground">{pin.cidade}</p>
        </div>
        <button
          onClick={onFechar}
          className="text-muted-foreground hover:text-foreground"
          aria-label="Fechar"
        >
          <X size={14} />
        </button>
      </div>

      <VeredictoBadge veredito={pin.veredito} />
      <OceanoBadge veredito={pin.veredito_oceano} />

      {/* Street View Static do A1 GeoScout */}
      <StreetViewPreview
        url={pin.street_view_url}
        interativoUrl={streetViewInterativoUrl}
        nomeCandidato={pin.candidato_nome}
      />

      <dl className="space-y-1.5 text-xs">
        <div className="flex justify-between">
          <dt className="text-muted-foreground">Score Top 1</dt>
          <dd className="font-mono tabular-nums">
            {pin.score_top1 != null ? pin.score_top1.toFixed(1) : '—'}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted-foreground">Score GeoScout</dt>
          <dd className="font-mono tabular-nums">
            {pin.score_geoscout != null ? pin.score_geoscout.toFixed(1) : '—'}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted-foreground">Modelo</dt>
          <dd className="font-mono truncate max-w-[150px]">
            {pin.modelo_recomendado ?? '—'}
          </dd>
        </div>
      </dl>

      <div className="pt-2 border-t border-border space-y-1">
        <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
          Candidato Top 1
        </p>
        <p className="text-xs leading-snug">{pin.candidato_nome}</p>
        {pin.candidato_endereco && (
          <p className="text-[10px] text-muted-foreground leading-snug">
            {pin.candidato_endereco}
          </p>
        )}
      </div>

      {modoComparar ? (
        <Button
          onClick={onToggleSelecao}
          className="w-full"
          size="sm"
          variant={selecionado ? 'default' : 'outline'}
        >
          {selecionado ? '✓ Selecionado pra comparar' : 'Selecionar pra comparar'}
        </Button>
      ) : (
        <Button onClick={onAbrir} className="w-full" size="sm">
          Abrir relatório completo <ChevronRight size={12} />
        </Button>
      )}
    </div>
  )
}

/**
 * ClusterLista — quando 2+ pins co-localizados, mostra lista compacta
 * com mini-card pra cada relatório. Acelera UX quando mesmo bairro tem
 * múltiplas análises (raro mas possível).
 */
function ClusterLista({
  pins,
  modoComparar,
  selecionados,
  onToggleSelecao,
  onAbrirRelatorio,
  onFechar,
}: {
  pins: PinRelatorio[]
  modoComparar: boolean
  selecionados: string[]
  onToggleSelecao: (id: string) => void
  onAbrirRelatorio: (id: string) => void
  onFechar: () => void
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-sm">
            {pins.length} relatórios neste ponto
          </h3>
          <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
            {pins[0].bairro} · {pins[0].cidade}
          </p>
        </div>
        <button
          onClick={onFechar}
          className="text-muted-foreground hover:text-foreground"
          aria-label="Fechar"
        >
          <X size={14} />
        </button>
      </div>

      {modoComparar && (
        <p className="text-[10px] font-mono text-muted-foreground bg-muted/30 rounded px-2 py-1">
          Clique pra selecionar (máx 2)
        </p>
      )}

      <ul className="space-y-1.5 max-h-96 overflow-auto">
        {pins.map((p) => {
          const selecionado = selecionados.includes(p.id)
          return (
            <li key={p.id}>
              <button
                onClick={() =>
                  modoComparar
                    ? onToggleSelecao(p.id)
                    : onAbrirRelatorio(p.id)
                }
                className={cn(
                  'w-full text-left rounded-md border p-2 transition-colors',
                  selecionado
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/40 hover:bg-muted/40',
                )}
              >
                <div className="flex items-center justify-between gap-2 mb-1 flex-wrap">
                  <div className="flex flex-wrap gap-1">
                    <VeredictoBadge veredito={p.veredito} />
                    <OceanoBadge veredito={p.veredito_oceano} compact />
                  </div>
                  {modoComparar && (
                    <input
                      type="checkbox"
                      checked={selecionado}
                      readOnly
                      className="h-3.5 w-3.5 accent-primary pointer-events-none"
                    />
                  )}
                </div>
                <p className="text-xs font-medium leading-tight">
                  {p.candidato_nome}
                </p>
                <div className="flex items-center gap-3 mt-1 text-[10px] text-muted-foreground font-mono">
                  <span>Score {p.score_top1?.toFixed(1) ?? '—'}</span>
                  <span>{p.modelo_recomendado ?? '—'}</span>
                </div>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

/**
 * Preview Street View estático com fallback gracioso quando URL inválida
 * ou imagem 404 (Google retorna placeholder cinza nesses casos — sinalizamos
 * via state `imagemFalhou` pra render UI alternativa em vez do placeholder).
 */
function StreetViewPreview({
  url,
  interativoUrl,
  nomeCandidato,
}: {
  url: string | null
  interativoUrl: string
  nomeCandidato: string
}) {
  const [imagemFalhou, setImagemFalhou] = useState(false)

  if (!url || imagemFalhou) {
    return (
      <div className="rounded-md border border-border bg-muted/30 p-3 flex items-center gap-2 text-xs text-muted-foreground">
        <ImageIcon size={14} />
        <span>Street View indisponível pra esse ponto</span>
      </div>
    )
  }

  return (
    <div className="rounded-md border border-border overflow-hidden bg-muted/20">
      <a
        href={interativoUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="block relative group"
        title={`Street View interativo de ${nomeCandidato}`}
      >
        <img
          src={url}
          alt={`Street View de ${nomeCandidato}`}
          loading="lazy"
          className="w-full h-32 object-cover"
          onError={() => setImagemFalhou(true)}
        />
        {/* Overlay com CTA on hover */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
          <span className="text-white text-xs font-medium inline-flex items-center gap-1">
            <ExternalLink size={12} /> Abrir Street View
          </span>
        </div>
      </a>
      <div className="px-2 py-1.5 text-[10px] font-mono text-muted-foreground bg-muted/40 border-t border-border">
        Google Street View Static · fov 90°
      </div>
    </div>
  )
}

function LegendaHeatmap() {
  const stops = [
    { color: OCEANO_FILL.OCEANO_AZUL, label: 'Favorável' },
    { color: OCEANO_FILL.TRANSICAO, label: 'Transição' },
    { color: OCEANO_FILL.VERMELHO, label: 'Pressão' },
  ]
  return (
    <div className="absolute bottom-3 right-3 rounded-md border border-border bg-card/95 backdrop-blur px-3 py-2 shadow-lg max-w-[200px]">
      <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground mb-1.5">
        Calor (concorrência)
      </p>
      <div
        className="h-2 rounded-full mb-1.5"
        style={{
          background: `linear-gradient(90deg, ${OCEANO_FILL.OCEANO_AZUL}, ${OCEANO_FILL.TRANSICAO}, ${OCEANO_FILL.VERMELHO})`,
        }}
      />
      <div className="flex justify-between text-[10px] text-muted-foreground">
        {stops.map((s) => (
          <span key={s.label}>{s.label}</span>
        ))}
      </div>
    </div>
  )
}

function LegendaOceano() {
  const items = OCEANO_LEGEND_ITEMS
  return (
    <div className="absolute bottom-3 left-3 rounded-md border border-border bg-card/95 backdrop-blur px-3 py-2 shadow-lg">
      <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground mb-1.5">
        Posicionamento (A9)
      </p>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {items.map((i) => (
          <div key={i.label} className="flex items-center gap-1.5 text-[10px]">
            <span
              aria-hidden
              className="w-2.5 h-2.5 rounded-full"
              style={{ background: i.color }}
            />
            {i.label}
          </div>
        ))}
      </div>
    </div>
  )
}

function LegendaVereditos() {
  const items = [
    { color: 'hsl(142 70% 45%)', label: 'Aprovado' },
    { color: 'hsl(45 95% 55%)', label: 'Ressalvas' },
    { color: 'hsl(210 80% 55%)', label: 'Investigar' },
    { color: 'hsl(0 70% 50%)', label: 'Reprovado' },
  ]
  return (
    <div className="absolute bottom-3 left-3 rounded-md border border-border bg-card/95 backdrop-blur px-3 py-2 shadow-lg">
      <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground mb-1.5">
        Veredito
      </p>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {items.map((i) => (
          <div key={i.label} className="flex items-center gap-1.5 text-[10px]">
            <span
              aria-hidden
              className="w-2.5 h-2.5 rounded-full"
              style={{ background: i.color }}
            />
            {i.label}
          </div>
        ))}
      </div>
    </div>
  )
}

function MapaVazio({ totalResumos = 0 }: { totalResumos?: number }) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[320px] text-center space-y-2 text-muted-foreground">
      <span className="text-4xl"></span>
      <p className="text-sm">
        {totalResumos > 0
          ? `${totalResumos} relatório${totalResumos === 1 ? '' : 's'} sem coordenadas para mapear`
          : 'Nenhum relatório com coordenadas pra mapear'}
      </p>
      <p className="text-xs">
        Os pins vêm do bairro+cidade do relatório (geocode). Metadados do Top 1 aparecem no card. Rode
        novos relatórios pra popular o mapa.
      </p>
    </div>
  )
}
