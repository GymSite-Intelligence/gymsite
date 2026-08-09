import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate, useRouterState } from '@tanstack/react-router'
import { ShieldCheck } from 'lucide-react'
import { TurnstileWidget } from '@/components/landing/TurnstileWidget'
import { ExplorarAddressSearch } from '@/components/explorar/ExplorarAddressSearch'
import { ExplorarBottomBar } from '@/components/explorar/ExplorarBottomBar'
import {
  briefingAreaM2,
  idadesDoBriefing,
  isExplorarTipo,
  type ExplorarBriefing,
} from '@/components/explorar/ExplorarBriefingDialog'
import { ExplorarDadosPanel } from '@/components/explorar/ExplorarDadosPanel'
import {
  EXPLORAR_PAGE,
  ExplorarSiteContext,
  SITE_ORIGIN,
  explorarChrome,
} from '@/components/explorar/explorar-chrome'
import { ExplorarControles } from '@/components/explorar/ExplorarControles'
import { ExplorarMap } from '@/components/explorar/ExplorarMap'
import { ExplorarResultPanel } from '@/components/explorar/ExplorarResultPanel'
import type { ExplorarEnderecoSugestao } from '@/hooks/useExplorarEnderecoAutocomplete'
import { UFS_BRASIL } from '@/data/ufs-brasil'
import { getTamanhoAncora, type TamanhoCodigo } from '@/data/tamanhos-por-modelo'
import { cn } from '@/lib/utils'
import {
  readLs,
  writeLs,
  type Camada,
  type Lente,
  type MapStyle,
  type ModoDesloc,
  type TipoNegocioExplorar,
} from '@/components/explorar/explorarIso'
import { useExplorarAnalise } from '@/hooks/useExplorarAnalise'
import { useExplorarIsocronas } from '@/hooks/useExplorarIsocronas'
import { useAuth } from '@/lib/auth'
import { trackPipeline } from '@/lib/pipeline-tracker'
import {
  pipelineLabelFromPayload,
  submitPipelineReport,
} from '@/lib/submit-pipeline'

const COCO: [number, number] = [-3.7455, -38.4855]

function ufDoTexto(s: string): string | undefined {
  const upper = s.toUpperCase()
  for (const uf of UFS_BRASIL) {
    if (new RegExp(`\\b${uf.sigla}\\b`).test(upper)) return uf.sigla
  }
  return undefined
}

export function ExplorarPage() {
  const novoSearch = useRouterState({
    select: (s) => {
      const q = s.location.search as { novo?: boolean | string }
      return q.novo === true || q.novo === '1' || q.novo === 'true'
    },
  })
  const navigate = useNavigate()
  const { user } = useAuth()
  const degustacao = !user
  const loggedIn = Boolean(user)

  const [mapStyle, setMapStyle] = useState<MapStyle>(() =>
    readLs('explorar-map-style', 'claro', ['claro', 'escuro', 'satelite']),
  )
  const [camada, setCamada] = useState<Camada>(() =>
    readLs('explorar-camada-v2', 'off', ['off', 'calor', 'influencia']),
  )
  const [modo, setModo] = useState<ModoDesloc>(() =>
    readLs('explorar-modo-desloc', 'pe', ['pe', 'carro']),
  )
  const [lente, setLente] = useState<Lente>('1km')
  const [tipoNegocio, setTipoNegocio] = useState<TipoNegocioExplorar>(() =>
    readLs('explorar-tipo-negocio', 'academia', [
      'academia',
      'studio_funcional',
      'crossfit_box',
      'studio_pilates',
    ]),
  )
  const [pin, setPin] = useState<{ lat: number; lng: number } | null>(null)
  const [lugar, setLugar] = useState<{ bairro?: string; cidade?: string; uf?: string }>({})
  const [resultOpen, setResultOpen] = useState(false)
  const [zoom, setZoom] = useState(14)
  const zoomLock = useRef(false)
  const [query, setQuery] = useState('')
  const [controlesOpen, setControlesOpen] = useState(true)
  const [toast, setToast] = useState<string | null>(null)
  const [email, setEmail] = useState('')
  const [turnstile, setTurnstile] = useState<string | null>(null)
  const [verifyOpen, setVerifyOpen] = useState(false)
  const [verifyKey, setVerifyKey] = useState(0)
  const pendingAnalise = useRef<{
    p: { lat: number; lng: number }
    b: ExplorarBriefing
  } | null>(null)
  const [dadosOpen, setDadosOpen] = useState(false)
  const [tamanho, setTamanho] = useState<TamanhoCodigo>('m')
  const [areaMin, setAreaMin] = useState(800)
  const [areaMax, setAreaMax] = useState(1500)
  const [publicoFaixas, setPublicoFaixas] = useState<string[]>(['25-39'])
  const [publicoAlvo, setPublicoAlvo] = useState('25-39')
  const [generoAlvo, setGeneroAlvo] = useState<ExplorarBriefing['generoAlvo']>('misto')
  const [pdfLoading, setPdfLoading] = useState(false)
  const [explorarUsed, setExplorarUsed] = useState(false)

  const { loading, error, result, analisar, geocode } = useExplorarAnalise()
  const {
    data: isoRings,
    isError: isoError,
    isFetching: isoLoading,
  } = useExplorarIsocronas(pin, modo, camada === 'influencia')

  const center = useMemo<[number, number]>(
    () => (pin ? [pin.lat, pin.lng] : COCO),
    [pin],
  )
  const rivals =
    result && result.status === 'ok' ? result.concorrentes : []
  const absorcao = result && result.status === 'ok' ? result.absorcao_margem_fresca : null
  const dadosOk = Boolean(lugar.uf && lugar.cidade && lugar.bairro)

  function flash(msg: string) {
    setToast(msg)
    window.setTimeout(() => setToast(null), 2800)
  }

  useEffect(() => {
    if (isoError) flash('Não deu para desenhar o tempo de rua neste ponto.')
  }, [isoError])

  useEffect(() => {
    if (novoSearch) setDadosOpen(true)
  }, [novoSearch])

  function closeDados() {
    setDadosOpen(false)
    if (novoSearch) {
      void navigate({
        to: '/explorar',
        search: {},
        replace: true,
      })
    }
  }

  function montarBriefing(): ExplorarBriefing | null {
    const uf = (lugar.uf || ufDoTexto(query) || '').toUpperCase()
    const municipio = (lugar.cidade || '').trim()
    const bairro = (lugar.bairro || '').trim()
    if (uf.length !== 2 || municipio.length < 2 || bairro.length < 2) return null
    return {
      uf,
      municipio,
      bairro,
      areaMin,
      areaMax,
      publicoAlvo,
      publicoFaixas,
      generoAlvo,
      tipoNegocio,
      tamanho,
    }
  }

  function changeStyle(s: MapStyle) {
    setMapStyle(s)
    writeLs('explorar-map-style', s)
  }
  function changeCamada(c: Camada) {
    setCamada(c)
    writeLs('explorar-camada-v2', c)
    if (c === 'off') return
    flash(
      c === 'calor'
        ? 'Mapa de calor: ainda sem dados IBGE neste recorte.'
        : 'Área de influência: tempo real a pé ou de carro nas ruas.',
    )
  }
  function lockZoom(z: number) {
    zoomLock.current = true
    setZoom(z)
    window.setTimeout(() => {
      zoomLock.current = false
    }, 800)
  }

  function changeModo(m: ModoDesloc) {
    setModo(m)
    writeLs('explorar-modo-desloc', m)
    lockZoom(m === 'carro' ? 13 : 14)
  }

  async function goToAddress(endereco: string) {
    const texto = endereco.trim()
    if (!texto) return
    try {
      const g = await geocode(texto)
      setPin({ lat: g.lat, lng: g.lng })
      setLugar({
        bairro: g.bairro,
        cidade: g.cidade,
        uf: g.uf || ufDoTexto(texto),
      })
      lockZoom(14)
    } catch (err) {
      flash(err instanceof Error ? err.message : 'Endereço não encontrado')
    }
  }

  function onPickSugestao(s: ExplorarEnderecoSugestao) {
    const texto = [s.bairro, s.contexto].filter(Boolean).join(', ') || s.textoCompleto
    setLugar({
      bairro: s.bairro || undefined,
      uf: ufDoTexto(s.contexto || s.textoCompleto),
    })
    void goToAddress(texto)
  }

  function changeTipo(t: TipoNegocioExplorar) {
    setTipoNegocio(t)
    writeLs('explorar-tipo-negocio', t)
    const ancora = getTamanhoAncora(t)
    setTamanho(ancora.codigo)
    setAreaMin(ancora.min)
    setAreaMax(ancora.max)
  }

  async function runAnalise(
    p: { lat: number; lng: number },
    b: ExplorarBriefing,
    lugarOverride?: { bairro?: string; cidade?: string; uf?: string },
    token?: string,
  ) {
    const ts = token ?? turnstile
    if (!loggedIn && (!email || !ts)) {
      flash('Informe o e-mail para analisar.')
      return
    }
    const tipo = isExplorarTipo(b.tipoNegocio) ? b.tipoNegocio : tipoNegocio
    const loc = {
      bairro: lugarOverride?.bairro || lugar.bairro || b.bairro,
      cidade: lugarOverride?.cidade || lugar.cidade || b.municipio,
      uf: lugarOverride?.uf || lugar.uf || b.uf,
    }
    const out = await analisar({
      lat: p.lat,
      lng: p.lng,
      lente,
      tipo_negocio: tipo,
      cidade: loc.cidade,
      bairro: loc.bairro,
      uf: loc.uf,
      endereco: `${b.bairro}, ${b.municipio}, ${b.uf}`,
      publico_alvo: b.publicoAlvo,
      area_m2: briefingAreaM2(b),
      ...idadesDoBriefing(b.publicoAlvo),
      email: loggedIn ? undefined : email,
      turnstile_token: loggedIn ? undefined : ts ?? undefined,
    })
    if (out.status === 'quota_used' || out.status === 'fila') {
      setExplorarUsed(true)
      flash(out.mensagem)
      return
    }
    setResultOpen(true)
    setControlesOpen(false)
    if (degustacao) setExplorarUsed(true)
  }

  async function startPipelineFromBriefing(b: ExplorarBriefing) {
    if (!loggedIn) return
    setPdfLoading(true)
    try {
      const payload = {
        cidade: b.municipio,
        uf: b.uf,
        bairro: b.bairro,
        area_m2_min: b.areaMin,
        area_m2_max: b.areaMax,
        tamanho_preset: b.tamanho,
        publico_alvo: b.publicoAlvo,
        genero_alvo: b.generoAlvo,
        tipo_negocio: b.tipoNegocio,
        estacionamento_obrigatorio: true,
        a0_research_provider: 'auto' as const,
      }
      const { id } = await submitPipelineReport(payload)
      trackPipeline(id, pipelineLabelFromPayload(payload))
      await navigate({
        to: '/relatorios/$relatorioId/aguardando',
        params: { relatorioId: id },
      })
    } catch (err) {
      flash(err instanceof Error ? err.message : 'Não deu para gerar o relatório PDF')
    } finally {
      setPdfLoading(false)
    }
  }

  function onBaixarPdf() {
    const b = montarBriefing()
    if (!b) {
      setResultOpen(false)
      setDadosOpen(true)
      flash('Busque o endereço em cima e confira os dados do projeto.')
      return
    }
    void startPipelineFromBriefing(b)
  }

  async function onAnalisar() {
    const b = montarBriefing()
    if (!b) {
      flash('Busque um endereço em cima. Tamanho e público ficam em Dados do projeto.')
      return
    }
    if (!loggedIn && (!email.trim() || !email.includes('@'))) {
      flash('Informe o e-mail para analisar.')
      return
    }
    let p = pin
    if (!p) {
      try {
        const g = await geocode(`${b.bairro}, ${b.municipio}, ${b.uf}`)
        p = { lat: g.lat, lng: g.lng }
        setPin(p)
        setLugar({
          bairro: g.bairro || b.bairro,
          cidade: g.cidade || b.municipio,
          uf: g.uf || b.uf,
        })
        lockZoom(14)
      } catch (err) {
        flash(err instanceof Error ? err.message : 'Endereço não encontrado')
        return
      }
    }
    if (!loggedIn && !turnstile) {
      pendingAnalise.current = { p, b }
      setVerifyKey((k) => k + 1)
      setVerifyOpen(true)
      return
    }
    try {
      await runAnalise(p, b)
    } catch (err) {
      flash(err instanceof Error ? err.message : 'Falha ao analisar')
      setTurnstile(null)
    }
  }

  const onVerifiedRef = useRef<(token: string) => void>(() => {})
  onVerifiedRef.current = (token: string) => {
    if (!token) return
    setTurnstile(token)
    setVerifyOpen(false)
    const pending = pendingAnalise.current
    if (!pending) {
      flash('Busque um endereço em cima. Tamanho e público ficam em Dados do projeto.')
      return
    }
    pendingAnalise.current = null
    void runAnalise(pending.p, pending.b, undefined, token).catch((err) => {
      flash(err instanceof Error ? err.message : 'Falha ao analisar')
      setTurnstile(null)
    })
  }
  const onVerified = useCallback((token: string) => {
    onVerifiedRef.current(token)
  }, [])

  const chrome = explorarChrome(degustacao)

  return (
    <ExplorarSiteContext.Provider value={degustacao}>
    <div
      className={cn(
        EXPLORAR_PAGE,
        degustacao
          ? 'explorar-page--site flex h-dvh flex-col overflow-hidden'
          : 'relative min-h-0 w-full flex-1 overflow-hidden',
      )}
    >
      {degustacao && (
        <header className="explorar-site-header">
          <a href={`${SITE_ORIGIN}/`} aria-label="GymSite Intelligence">
            <img src="/gymsite-logo-white.png" alt="GymSite Intelligence" />
          </a>
          <nav>
            <a href={`${SITE_ORIGIN}/agentes`}>Especialistas</a>
            <a href={`${SITE_ORIGIN}/degustacao`}>Degustação</a>
            <span className="is-current">Explorar</span>
            <a href={`${SITE_ORIGIN}/`}>Início</a>
          </nav>
        </header>
      )}
      <div
        className={cn(
          'relative overflow-hidden',
          degustacao ? 'min-h-0 flex-1' : 'h-full min-h-0',
        )}
      >
      <div className="absolute inset-0 z-0">
      <ExplorarMap
        center={center}
        zoom={zoom}
        pin={pin}
        rivals={rivals}
        mapStyle={mapStyle}
        camada={camada}
        lente={lente}
        isoRings={isoRings ?? null}
        onClickMap={(lat, lng) => setPin({ lat, lng })}
        onZoom={(z) => {
          if (zoomLock.current) return
          setZoom(z)
        }}
      />
      </div>

      <div
        className={cn(
          'pointer-events-none absolute top-3.5 z-50 flex flex-col items-stretch gap-2',
          resultOpen ? 'left-3.5 right-94' : 'left-3.5 right-3.5',
        )}
      >
        <ExplorarAddressSearch
          query={query}
          biasLat={pin?.lat}
          biasLng={pin?.lng}
          onQueryChange={setQuery}
          onPick={onPickSugestao}
          onSubmitFree={() => void goToAddress(query)}
        />
        {controlesOpen && (
          <div className="pointer-events-auto self-start">
            <ExplorarControles
              mapStyle={mapStyle}
              camada={camada}
              modo={modo}
              nMaps={rivals.length}
              onStyle={changeStyle}
              onCamada={changeCamada}
              onModo={changeModo}
              onClose={() => setControlesOpen(false)}
            />
          </div>
        )}
      </div>

      {absorcao && result?.status === 'ok' && (
        <ExplorarResultPanel
          open={resultOpen}
          onOpenChange={setResultOpen}
          absorcao={absorcao}
          rivals={rivals}
          baseLabel={result.base_espacial_label}
          loggedIn={loggedIn}
          pdfLoading={pdfLoading}
          onBaixarPdf={onBaixarPdf}
          emailCapturado={explorarUsed}
        />
      )}
      {absorcao && result?.status === 'ok' && !resultOpen && (
        <button
          type="button"
          className={cn(
            chrome,
            'absolute right-3.5 top-20 z-50 rounded-lg border px-3 py-2 text-sm font-semibold shadow-md',
          )}
          onClick={() => setResultOpen(true)}
        >
          Ver análise · {rivals.length} academias
        </button>
      )}

      {camada === 'influencia' && pin && (
        <div className={cn(chrome, 'pointer-events-none absolute bottom-21.5 left-3.5 z-50 rounded-xl border px-3 py-2.5 shadow-md')}>
          <p className="mb-1.5 text-[10px] font-medium tracking-[0.5px] text-muted-foreground">
            TEMPO{isoLoading ? ' · calculando…' : ''}
          </p>
          <div className="space-y-1 text-xs font-normal text-foreground">
            <div className="flex items-center gap-2">
              <span className="size-3 rounded-sm border border-dashed border-green-600 bg-green-400/50" />
              5 min
            </div>
            <div className="flex items-center gap-2">
              <span className="size-3 rounded-sm border border-dashed border-yellow-600 bg-yellow-400/50" />
              10 min
            </div>
            <div className="flex items-center gap-2">
              <span className="size-3 rounded-sm border border-dashed border-orange-600 bg-orange-400/50" />
              15 min
            </div>
          </div>
        </div>
      )}

      {!loggedIn && !explorarUsed && (
        <form
          className={cn(chrome, 'pointer-events-auto absolute bottom-21.5 right-3.5 z-50 w-72 rounded-xl border p-3 shadow-lg')}
          onSubmit={(e) => {
            e.preventDefault()
            void onAnalisar()
          }}
        >
          <p className="mb-2 text-xs font-semibold text-foreground">1 pesquisa grátis · degustação</p>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="seu e-mail"
            required
            autoComplete="email"
            className="h-9 w-full rounded-md border border-border bg-secondary px-2 text-sm text-foreground"
          />
          <button
            type="submit"
            disabled={loading || !email.includes('@')}
            className="explorar-cta mt-2 h-9 w-full text-sm"
          >
            {loading ? 'Analisando…' : 'Continuar'}
          </button>
        </form>
      )}

      {verifyOpen &&
        createPortal(
          <div
            className="fixed inset-0 z-70 flex items-center justify-center p-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="explorar-verify-title"
          >
            <div
              className="absolute inset-0 bg-background/80 backdrop-blur-sm"
              aria-hidden
              onClick={() => setVerifyOpen(false)}
            />
            <div className="relative max-w-xs space-y-3 rounded-xl border border-border bg-card p-5 text-center shadow-xl">
              <div className="flex items-center justify-center gap-2 text-sm font-medium text-foreground">
                <ShieldCheck className="h-4 w-4 text-primary" />
                <h3 id="explorar-verify-title">Confirme que você não é um robô</h3>
              </div>
              <div className="flex justify-center">
                <TurnstileWidget key={verifyKey} onToken={onVerified} />
              </div>
              <button
                type="button"
                className="text-xs text-muted-foreground hover:text-foreground"
                onClick={() => setVerifyOpen(false)}
              >
                Cancelar
              </button>
            </div>
          </div>,
          document.body,
        )}

      {toast && (
        <div className={cn(chrome, 'absolute bottom-21.5 left-1/2 z-60 -translate-x-1/2 rounded-lg border px-3.5 py-2 text-xs shadow-md')}>
          {toast}
        </div>
      )}
      {error && !toast && (
        <div className={cn(chrome, 'absolute bottom-21.5 left-1/2 z-60 -translate-x-1/2 rounded-lg border border-destructive/40 px-3.5 py-2 text-xs text-destructive shadow-md')}>
          {error}
        </div>
      )}

      <div className="absolute inset-x-3.5 bottom-3.5 z-50 flex flex-col gap-2">
        {dadosOpen && (
          <ExplorarDadosPanel
            lugar={lugar}
            tipoNegocio={tipoNegocio}
            tamanho={tamanho}
            areaMin={areaMin}
            areaMax={areaMax}
            publicoFaixas={publicoFaixas}
            generoAlvo={generoAlvo}
            onTamanho={(cod, min, max) => {
              setTamanho(cod)
              setAreaMin(min)
              setAreaMax(max)
            }}
            onArea={(min, max) => {
              setAreaMin(min)
              setAreaMax(max)
            }}
            onPublicoFaixas={(faixas, alvo) => {
              setPublicoFaixas(faixas)
              setPublicoAlvo(alvo)
            }}
            onGenero={setGeneroAlvo}
            onClose={closeDados}
          />
        )}
        <ExplorarBottomBar
          tipoNegocio={tipoNegocio}
          lente={lente}
          canAnalyze={!degustacao || !explorarUsed}
          loading={loading}
          dadosOpen={dadosOpen}
          dadosOk={dadosOk}
          controlesOpen={controlesOpen}
          onTipo={changeTipo}
          onLente={setLente}
          onControles={() => setControlesOpen((v) => !v)}
          onDados={() => (dadosOpen ? closeDados() : setDadosOpen(true))}
          onAnalisar={onAnalisar}
        />
      </div>
      </div>
    </div>
    </ExplorarSiteContext.Provider>
  )
}
