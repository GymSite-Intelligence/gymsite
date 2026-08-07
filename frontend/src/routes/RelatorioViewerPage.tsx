/**
 * RelatorioViewerPage — Tela 3 do GymSite (completa).
 *
 * Renderiza 12 seções a partir do JSON canônico v1.1:
 *  1. Header (cidade, bairro, tipo, área, veredito)
 *  2. Scores Regionais (3 dim + 2 cards Score Bairro / Top 1)
 *  3. Contexto de Mercado (metadados Deep Research A0)
 *  4. Resumo Executivo
 *  5. Top 3 Candidatos (CandidatoCard com street view)
 *  6. Viabilidade Financeira 3 Cenários (low/mid/premium)
 *  7. Posicionamento Recomendado
 *  8. Inteligência Competitiva (CompetidorGroup + Dores Dominantes)
 *  9. Distribuição Geográfica dos Concorrentes
 * 10. Bairros Alternativos
 * 11. Script de Abordagem (com botão copiar)
 * 12. Alertas Globais + Decisão
 */
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearch } from '@tanstack/react-router'
import { AlertTriangle, ArrowLeft, ChevronDown, ListTree, MapPin } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Separator } from '@/components/ui/separator'
import { useRelatorioDetail } from '@/hooks/useRelatorioDetail'
import { VeredictoBadge } from '@/components/domain/VeredictoBadge'
import { DualVereditoStrip } from '@/components/domain/DualVereditoStrip'
import { normalizeVereditoOceano } from '@/lib/oceano'
import { ScoresViz } from '@/components/domain/ScoresViz'
import { ContextoMercadoViz } from '@/components/domain/ContextoMercadoViz'
import { CandidatoCard } from '@/components/domain/CandidatoCard'
import { CenarioFinanceiroTable } from '@/components/domain/CenarioFinanceiroTable'
import { CenariosViz } from '@/components/domain/CenariosViz'
import { CapexBreakdownChart } from '@/components/domain/CapexBreakdownChart'
import { ConsorcioCard } from '@/components/domain/ConsorcioCard'
import { FinanceiroKpiStrip } from '@/components/domain/FinanceiroKpiStrip'
import { KitEquipamentosTable } from '@/components/domain/KitEquipamentosTable'
import {
  getKit,
  getKitParaModeloFinanceiro,
  getTamanhoParaModeloFinanceiro,
  faixaCustoReal,
} from '@/data/kits'
import type { ModeloNegocio, TamanhoCodigo } from '@/data/tamanhos-por-modelo'
import { recalcularCenariosComKit } from '@/lib/recalcula-cenario-com-kit'
import { DoresPorCategoria } from '@/components/domain/DoresPorCategoria'
import { PicoLotacaoViz } from '@/components/domain/PicoLotacaoViz'
import { InteligenciaCompetitivaResumoCard } from '@/components/domain/InteligenciaCompetitivaResumoCard'
import { NovasUnidadesCard } from '@/components/domain/NovasUnidadesCard'
import { DemografiaBairroCard } from '@/components/domain/DemografiaBairroCard'
import { AbsorcaoMargemFrescaCard } from '@/components/domain/AbsorcaoMargemFrescaCard'
import { FluxoPedestreCard } from '@/components/domain/FluxoPedestreCard'
import { MapaMunicipioMercado } from '@/components/maps/MapaMunicipioMercado'
import { ObrasEmAndamentoTable } from '@/components/domain/ObrasEmAndamentoTable'
import { DemandaFuturaCard } from '@/components/domain/DemandaFuturaCard'
import { AneisCompetitivosCard } from '@/components/domain/AneisCompetitivosCard'
import { CoberturaRedesA0Card } from '@/components/domain/CoberturaRedesA0Card'
import { DoresHeatmap } from '@/components/domain/DoresHeatmap'
import { PlanosConcorrenciaTable } from '@/components/domain/PlanosConcorrenciaTable'
import { FolgaPicoInsight } from '@/components/domain/FolgaPicoInsight'
import { AluguelFonteAuditavel } from '@/components/domain/AluguelFonteAuditavel'
import { DistribuicaoViz } from '@/components/domain/DistribuicaoViz'
import { BairrosAlternativosViz } from '@/components/domain/BairrosAlternativosViz'
import { TextoSecao } from '@/components/domain/TextoSecao'
import { PosicionamentoCard } from '@/components/domain/PosicionamentoCard'
import { AlertasViz } from '@/components/domain/AlertasViz'
import { RerunPipelineButton } from '@/components/domain/RerunPipelineButton'
import { RebuscarCandidatosButton } from '@/components/domain/RebuscarCandidatosButton'
import { GerarPlanoButton } from '@/components/execucao/GerarPlanoButton'
import { DeleteRelatorioButton } from '@/components/domain/DeleteRelatorioButton'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { SectionHeader } from '@/components/ui/section-header'
import { RouteErrorBoundary } from '@/components/RouteErrorBoundary'
import {
  relatorioViewerErrorMessage,
  shouldRedirectToAguardando,
  shouldShowRerunInViewer,
} from '@/lib/relatorio-completeness'

const TIPO_NEGOCIO_LABEL: Record<string, string> = {
  academia: 'Academia',
  crossfit_box: 'Box CrossFit',
  studio_pilates: 'Studio Pilates',
  studio_funcional: 'Studio Funcional',
  outro: 'Outro',
}

interface MetadataExecucaoShape {
  fonte_market_context?: string
  data_coleta_market_context?: string
  cached_market_context?: boolean
  redes_a0_solicitadas?: string[]
  schema_version?: string
}

/** Slug estável a partir do título (remove emoji/acentos) para âncora de seção. */
function slugify(title: string): string {
  return title
    .replace(/[^a-zA-Z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase()
}

/**
 * ReportNavMenu — atalhos de seção como DROPDOWN no header (ao lado das ações).
 * Substitui a antiga sidebar TOC (que dava aparência de 2 sidebars) — o relatório
 * passa a ocupar a largura total. Varre [data-section-title] no mount (robusto a
 * seções condicionais), scroll-spy via IntersectionObserver reflete a seção atual
 * no valor do select, e onChange dá scroll suave até a seção.
 */
function ReportNavMenu({ className }: { className?: string }) {
  const [items, setItems] = useState<{ id: string; title: string }[]>([])
  const [active, setActive] = useState<string>('')

  useEffect(() => {
    const els = Array.from(
      document.querySelectorAll<HTMLElement>('[data-section-title]'),
    )
    setItems(els.map((el) => ({ id: el.id, title: el.dataset.sectionTitle ?? '' })))
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) setActive((e.target as HTMLElement).id)
        })
      },
      { rootMargin: '-15% 0px -75% 0px' },
    )
    els.forEach((el) => obs.observe(el))
    return () => obs.disconnect()
  }, [])

  if (items.length === 0) return null

  return (
    <div className={cn('relative inline-flex', className)}>
      <ListTree
        size={14}
        className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground"
      />
      <ChevronDown
        size={14}
        className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground"
      />
      <select
        value={active}
        onChange={(e) => {
          const id = e.target.value
          if (id) {
            document
              .getElementById(id)
              ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
          }
        }}
        className="h-9 max-w-[200px] appearance-none truncate rounded-md border border-border bg-card pl-8 pr-7 text-sm text-foreground shadow-sm outline-none transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="Ir para seção do relatório"
      >
        <option value="" disabled>
          Ir para seção…
        </option>
        {items.map((it) => (
          <option key={it.id} value={it.id}>
            {it.title}
          </option>
        ))}
      </select>
    </div>
  )
}

export function RelatorioViewerPage() {
  const { relatorioId } = useParams({ from: '/relatorios/$relatorioId' })
  const search = useSearch({ from: '/relatorios/$relatorioId' }) as { print?: string }
  const navigate = useNavigate()
  const { data, isLoading, error } = useRelatorioDetail(relatorioId)

  useEffect(() => {
    if (isLoading || !data) return
    if (shouldRedirectToAguardando(data.pipeline_status)) {
      navigate({
        to: '/relatorios/$relatorioId/aguardando',
        params: { relatorioId },
      })
    }
  }, [isLoading, data, relatorioId, navigate])

  // Hooks sempre antes de early return (React #310).
  useEffect(() => {
    if (search?.print !== '1') return
    if (isLoading || error || !data) return
    const t = window.setTimeout(() => {
      try {
        window.print()
      } catch {
        // noop
      }
    }, 600)
    return () => window.clearTimeout(t)
  }, [search?.print, relatorioId, isLoading, error, data])

  if (isLoading) return <ViewerSkeleton />
  if (error || !data) return <ViewerError message={error?.message} />

  const viewerErr = relatorioViewerErrorMessage(data)
  if (viewerErr) {
    return (
      <ViewerError
        message={viewerErr}
        relatorioId={relatorioId}
        showRerun={shouldShowRerunInViewer(data)}
      />
    )
  }

  return (
    <RouteErrorBoundary title="Erro ao exibir o relatório">
      <RelatorioViewerContent relatorioId={relatorioId} data={data} />
    </RouteErrorBoundary>
  )
}

function RelatorioViewerContent({
  relatorioId,
  data,
}: {
  relatorioId: string
  data: NonNullable<ReturnType<typeof useRelatorioDetail>['data']>
}) {
  const inp = data.input_canonico
  const out = data.output_consolidado
  const meta = (data.metadata_execucao ?? {}) as MetadataExecucaoShape

  // Schema v1.5: kit detalhado vira fonte da verdade pra "Equipamentos".
  // Kit DIFERE por modelo financeiro: Low usa tamanho-1 (econômico),
  // Mid usa tamanho selecionado, Premium usa tamanho+1 (robusto).
  // Cascateia recalculo nos 3 cenários (capex → manutenção → seguro →
  // contingência → capital giro → investimento → payback → margem → TIR/VPL).
  const tipoNegocio = (data.input_canonico.tipo_negocio || 'academia') as ModeloNegocio
  const tamanhoPreset = (data.input_canonico.tamanho_preset || 'm') as TamanhoCodigo

  // Helper: mediana da faixa real de um kit
  const medianaKit = (k: ReturnType<typeof getKit>) =>
    k ? (faixaCustoReal(k)[0] + faixaCustoReal(k)[1]) / 2 : null

  // Map de equipamentos por modelo financeiro
  const equipamentosPorModelo: Record<string, number | null> = {
    low: medianaKit(getKitParaModeloFinanceiro(tipoNegocio, tamanhoPreset, 'low')),
    mid: medianaKit(getKitParaModeloFinanceiro(tipoNegocio, tamanhoPreset, 'mid')),
    premium: medianaKit(getKitParaModeloFinanceiro(tipoNegocio, tamanhoPreset, 'premium')),
  }

  const areaM2Kit =
    data.input_canonico.area_m2_max ?? data.input_canonico.area_m2_min ?? null
  const cenariosRecalc = recalcularCenariosComKit(
    out.viabilidade_3_cenarios,
    areaM2Kit,
    equipamentosPorModelo,
  )

  // Tamanhos usados por cenário (pra exibir hint na UI)
  const tamanhosPorModelo = {
    low: getTamanhoParaModeloFinanceiro(tamanhoPreset, 'low'),
    mid: getTamanhoParaModeloFinanceiro(tamanhoPreset, 'mid'),
    premium: getTamanhoParaModeloFinanceiro(tamanhoPreset, 'premium'),
  }

  // Score Geral por candidato (4 dim) = (geoscout + 3 regionais) / 4
  const scoreRegional = (() => {
    const dim = out.scores_regionais
    const valores = [
      dim?.demografico,
      dim?.competitivo ?? dim?.concorrencia,
      dim?.viabilidade,
    ].filter((v): v is number => typeof v === 'number')
    if (valores.length === 0) return null
    return valores.reduce((a, b) => a + b, 0) / valores.length
  })()

  const semCandidatos = (out.top_3_candidatos?.length ?? 0) === 0
  const semConcorrentes = (out.competitors_set?.length ?? 0) === 0
  const modoCidadeInteira = inp.bairro === '(cidade inteira)'
  const coleta = out.coleta_geografica
  const avisoGeoScout = [coleta?.aviso, coleta?.erro].filter(Boolean).join(' ')
  const geocodeDenied =
    /REQUEST_DENIED/i.test(avisoGeoScout) ||
    /geocod/i.test(avisoGeoScout) && /falhou|denied|ausente/i.test(avisoGeoScout)
  const totalCandidatosPipeline =
    typeof coleta?.total_candidatos === 'number'
      ? coleta.total_candidatos
      : null

  return (
    <div className="space-y-6">
      {(semCandidatos || semConcorrentes) && (
        <div className="rounded-lg border border-veredito-ressalvas/50 bg-veredito-ressalvas/5 p-4 space-y-2">
          <div className="flex items-start gap-2">
            <AlertTriangle
              size={16}
              className="text-veredito-ressalvas shrink-0 mt-0.5"
            />
            <div className="space-y-1 text-sm">
              <p className="font-semibold text-veredito-ressalvas">
                Coleta geográfica incompleta — candidatos, listings e concorrentes
                não foram encontrados
              </p>
              <ul className="list-disc pl-4 text-foreground/90 space-y-1">
                {modoCidadeInteira && (
                  <li>
                    Relatório foi gerado em modo <strong>cidade inteira</strong> (não
                    suportado no MVP). Gere novamente escolhendo um <strong>bairro
                    específico</strong> — o GeoScout e o Deep Research (A0) dependem
                    disso.
                  </li>
                )}
                {geocodeDenied && (
                  <li>
                    Geocoding Google retornou{' '}
                    <code className="text-xs">REQUEST_DENIED</code> (ou falhou) — habilite
                    a <strong>Geocoding API</strong> no projeto da chave{' '}
                    <code className="text-xs">GOOGLE_MAPS_API_KEY</code> e confira billing.
                    {avisoGeoScout && (
                      <span className="block mt-1 text-muted-foreground font-normal">
                        GeoScout: {avisoGeoScout}
                      </span>
                    )}
                  </li>
                )}
                {!geocodeDenied && semCandidatos && totalCandidatosPipeline === 0 && (
                  <li>
                    GeoScout não retornou candidatos no raio (Places pode ter sido
                    chamado — veja custos de <code className="text-xs">places_*</code>).
                    {avisoGeoScout ? (
                      <span className="block mt-1 text-muted-foreground font-normal">
                        {avisoGeoScout}
                      </span>
                    ) : null}
                  </li>
                )}
                {!geocodeDenied &&
                  semConcorrentes &&
                  (out.total_concorrentes_analisados ?? 0) === 0 && (
                    <li>
                      Busca de concorrentes no raio não encontrou academias (A3a/A3c).
                    </li>
                  )}
                {semCandidatos && (
                  <li>
                    Cenários financeiros abaixo usam premissas genéricas (sem imóvel
                    validado no GeoScout).
                  </li>
                )}
              </ul>
            </div>
          </div>
        </div>
      )}
      {/* 1. Header — hero card (breadcrumb + título + veredito + ações) */}
      <header className="space-y-3 rounded-xl border border-border bg-card/40 p-5 sm:p-6">
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link to="/relatorios">Relatórios</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link
                  to="/relatorios"
                  search={{
                    cidade: inp.cidade,
                    veredito: undefined,
                    since: undefined,
                  }}
                >
                  {inp.cidade}
                </Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>{inp.bairro}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>

        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3 flex-wrap">
            <span>{inp.bairro}</span>
            <span className="text-muted-foreground font-normal">·</span>
            <span className="text-muted-foreground font-normal text-2xl">
              {inp.cidade}
            </span>
            {/* Veredito INLINE ao título (não flutuando isolado no canto) */}
            <VeredictoBadge veredito={out.veredito} />
          </h1>
          <DualVereditoStrip
            vereditoViabilidade={out.veredito}
            vereditoOceano={
              normalizeVereditoOceano(
                out.posicionamento_estrategico?.veredito_posicionamento,
              ) ?? undefined
            }
          />
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <MapPin size={12} className="shrink-0" />
            <span>
              {TIPO_NEGOCIO_LABEL[inp.tipo_negocio ?? 'academia'] ?? inp.tipo_negocio}
              {' · '}
              <span className="font-mono">
                {inp.area_m2_min}-{inp.area_m2_max} m²
              </span>
              {' · '}
              público {inp.publico_alvo ?? '25-40'}
            </span>
            <span className="ml-auto flex items-center gap-2">
              <ReportNavMenu />
              <GerarPlanoButton relatorioId={relatorioId} />
              <RebuscarCandidatosButton relatorioId={relatorioId} />
              <RerunPipelineButton relatorioId={relatorioId} />
            </span>
          </div>
        </div>
      </header>

      {/* BODY — coluna única full-width (TOC virou dropdown no header) */}
      <div className="min-w-0 space-y-8">
      {/* Alertas e Ressalvas — POSICIONADO NO TOPO: o usuário deve ver os riscos
          antes de mergulhar nos detalhes (decisão informada). */}
      {out.alertas_financeiros && out.alertas_financeiros.length > 0 && (
        <Section
          title={
            out.veredito === 'REPROVADO'
              ? `Alertas Críticos (${out.alertas_financeiros.length})`
              : `Alertas e Ressalvas (${out.alertas_financeiros.length})`
          }
        >
          <AlertasViz alertas={out.alertas_financeiros} veredito={out.veredito} />
        </Section>
      )}
      {/* 2. Scores Regionais */}
      <Section title="Scores Regionais">
        <ScoresViz
          scoreBairro={out.score_bairro}
          scoreTop1={out.score_top1_candidato}
          scoresRegionais={out.scores_regionais}
        />
      </Section>

      {/* 2.5 Demografia do bairro — renda (CKAN) + população/ocupação (Censo 2022),
          fontes reais por dimensão (bairro não herda o município). */}
      {out.demografia_bairro &&
        (out.demografia_bairro.renda_media != null || out.demografia_bairro.populacao != null) && (
        <Section title="Demografia do bairro">
          <DemografiaBairroCard block={out.demografia_bairro} />
        </Section>
      )}

      {out.posicionamento_estrategico?.absorcao_margem_fresca?.rotulo && (
        <Section title="Quem ainda pode matricular">
          <AbsorcaoMargemFrescaCard
            block={out.posicionamento_estrategico.absorcao_margem_fresca}
          />
        </Section>
      )}

      {out.fluxo_pedestre && (
        <Section title="Fluxo pedestre — sintaxe espacial">
          <FluxoPedestreCard block={out.fluxo_pedestre} />
        </Section>
      )}

      {/* 3. Contexto de Mercado (schema v1.2 → market_context completo; v1.1 → fallback) */}
      {(out.market_context || meta.fonte_market_context) && (
        <Section title="Contexto de Mercado">
          <ContextoMercadoViz
            marketContext={out.market_context}
            nivelSaturacao={out.nivel_saturacao}
            aluguelMedianaM2={out.aluguel_mediana_m2_observado}
            totalConcorrentes={out.total_concorrentes_analisados}
          />
        </Section>
      )}

      {/* 4. Resumo Executivo */}
      {out.resumo_executivo && (
        <TextoSecao
          title="Resumo Executivo"
          texto={out.resumo_executivo}
          variant="highlight"
        />
      )}

      {/* 5. Candidatos (imóveis anunciados) × Âncoras e polos — blocos separados.
          Sem guard de length: com 0 candidatos o empty state com CTA de
          re-busca PRECISA aparecer (run sem listing é cenário real). */}
      {(() => {
        const todosCandidatos = out.top_3_candidatos ?? []
        const anunciados = todosCandidatos.filter((c) => Boolean(c.listing_url))
        const ancoras = todosCandidatos.filter((c) => !c.listing_url)
        return (
          <>
            {anunciados.length > 0 && (() => {
              const _norm = (s: string) =>
                (s ?? '').normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase()
              const alvo = _norm(inp.bairro ?? '')
              const marcados = anunciados.slice(0, 3).map((cand) => ({
                cand,
                foraDoBairro: Boolean(alvo) && !_norm(cand.endereco ?? '').includes(alvo),
              }))
              const algumFora = marcados.some((m) => m.foraDoBairro)
              return (
              <Section title="Top Candidatos — imóveis anunciados">
                {algumFora && inp.bairro && (
                  <p className="mb-3 rounded-lg border border-veredito-ressalvas/40 bg-veredito-ressalvas/5 px-3 py-2 text-xs text-muted-foreground">
                    ⚠ Alguns imóveis estão em <strong>bairro vizinho</strong> (o GeoScout não
                    achou vago em {inp.bairro}). O referencial de viabilidade — demografia,
                    concorrência e aluguel de referência — é do bairro <strong>{inp.bairro}</strong> e
                    independe do imóvel específico abaixo; trate-os como ponto de partida físico,
                    não como o veredito do bairro.
                  </p>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {marcados.map(({ cand, foraDoBairro }, i) => {
                    const scoreGeral =
                      cand.score_geoscout != null && scoreRegional != null
                        ? (cand.score_geoscout + scoreRegional * 3) / 4
                        : null
                    return (
                      <CandidatoCard
                        key={cand.place_id ?? `${cand.nome}-${i}`}
                        candidato={cand}
                        posicao={i + 1}
                        scoreGeral={scoreGeral}
                        foraDoBairro={foraDoBairro}
                      />
                    )
                  })}
                </div>
              </Section>
              )
            })()}
            {anunciados.length === 0 && (
              <Section title="Top Candidatos — imóveis anunciados">
                <p className="text-sm text-muted-foreground">
                  Nenhum imóvel anunciado na faixa de área passou no filtro de qualidade.
                  Use “Re-buscar pontos” no topo para uma nova varredura do mercado.
                </p>
              </Section>
            )}
            {ancoras.length > 0 && (
              <Section title="Âncoras e polos de referência">
                <p className="mb-3 text-xs text-muted-foreground">
                  Referências de fluxo e localização do bairro — não estão à locação.
                  Imóvel próximo a estas âncoras herda o movimento delas.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {ancoras.slice(0, 3).map((cand, i) => {
                    const scoreGeral =
                      cand.score_geoscout != null && scoreRegional != null
                        ? (cand.score_geoscout + scoreRegional * 3) / 4
                        : null
                    return (
                      <CandidatoCard
                        key={cand.place_id ?? `${cand.nome}-${i}`}
                        candidato={cand}
                        posicao={i + 1}
                        scoreGeral={scoreGeral}
                      />
                    )
                  })}
                </div>
              </Section>
            )}
          </>
        )
      })()}

      {/* 6. Viabilidade Financeira (collapsible) */}
      <Section
        title="Viabilidade Financeira — 3 Cenários"
        collapsible
        suffix={
          <AluguelFonteAuditavel
            fonte={out.fonte_aluguel}
            medianaM2={out.aluguel_mediana_m2_observado}
            amostras={out.aluguel_amostras}
            meta={out.aluguel_fonte_meta}
          />
        }
      >
        {(() => {
          const cenariosAtivos = cenariosRecalc ?? out.viabilidade_3_cenarios

          // Reconciliação aluguel de referência × candidato anunciado.
          // Cenários usam a mediana de mercado da faixa de área (conservador);
          // quando o candidato real anuncia preço >25% distante, o leitor
          // precisa da ponte — senão os dois números parecem contradição.
          const aluguelRef = Number(out.aluguel_mensal) || null
          const candidatoComPreco = (out.top_3_candidatos ?? [])
            .filter((c) => c.listing_url && c.price_raw)
            .map((c) => {
              const digits = (c.price_raw ?? '').replace(/[^\d]/g, '')
              return { nome: c.nome, preco: digits ? Number(digits) : 0 }
            })
            .find((c) => c.preco >= 2000 && c.preco < 1_000_000)
          const ticketRealizado = cenariosAtivos?.mid?.ticket_realizado_estimado
            ?? cenariosAtivos?.mid?.ticket_medio
          const mostraReconciliacao =
            aluguelRef != null &&
            candidatoComPreco != null &&
            Math.abs(aluguelRef - candidatoComPreco.preco) / aluguelRef > 0.25

          return (
            <>
              <FinanceiroKpiStrip
                areaM2Min={inp.area_m2_min}
                areaM2Max={inp.area_m2_max}
                aluguelMensal={out.aluguel_mensal}
                cenarioMid={cenariosAtivos?.mid}
              />
              {/* Viz radical dos 3 cenários (drill-down detalhado na tabela abaixo) */}
              <CenariosViz
                cenarios={cenariosAtivos}
                modeloRecomendado={out.modelo_recomendado ?? undefined}
                className="mt-4"
              />
              {mostraReconciliacao && (
                <div className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5 px-4 py-3 text-sm">
                  <p className="font-medium text-emerald-700 dark:text-emerald-400">
                    Os cenários acima usam o aluguel de referência de mercado
                    ({Number(aluguelRef).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}/mês
                    para a faixa de área) — premissa conservadora.
                  </p>
                  <p className="mt-1 text-muted-foreground">
                    O imóvel anunciado custa{' '}
                    <strong>{candidatoComPreco.preco.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}/mês</strong>
                    {candidatoComPreco.preco < aluguelRef ? (
                      <>
                        {' '}({Math.round((1 - candidatoComPreco.preco / aluguelRef) * 100)}% abaixo da referência).
                        {ticketRealizado ? (
                          <>
                            {' '}Com esse aluguel, o break-even cai
                            ~{Math.round((aluguelRef - candidatoComPreco.preco) / Number(ticketRealizado))} alunos
                            — todos os cenários melhoram a partir daqui.
                          </>
                        ) : (
                          <> — todos os cenários melhoram a partir daqui.</>
                        )}
                      </>
                    ) : (
                      <>
                        {' '}({Math.round((candidatoComPreco.preco / aluguelRef - 1) * 100)}% acima da referência)
                        — negocie ou avalie os bairros alternativos.
                      </>
                    )}
                  </p>
                </div>
              )}
              <CapexBreakdownChart
                cenarios={cenariosAtivos}
                className="mt-4"
              />
              <CenarioFinanceiroTable
                cenarios={cenariosAtivos}
                modeloRecomendado={out.modelo_recomendado}
                areaM2={data.input_canonico.area_m2_max ?? data.input_canonico.area_m2_min}
                competidores={out.competitors_set}
              />
              <FolgaPicoInsight
                cenarios={cenariosAtivos}
                competidores={out.competitors_set}
                className="mt-4"
              />
              <ConsorcioCard key={cenariosAtivos?.mid?.capex_total ?? cenariosAtivos?.mid?.capex_estimado ?? 'sem-capex'} capexMid={cenariosAtivos?.mid?.capex_total ?? cenariosAtivos?.mid?.capex_estimado ?? null} className="mt-4" />
            </>
          )
        })()}
        {cenariosRecalc && (
          <p className="mt-2 text-[10px] text-muted-foreground font-mono">
            Valores recalculados via kit detalhado v1.5. Equipamentos
            diferentes por modelo: Low usa kit{' '}
            <strong>{tamanhosPorModelo.low.toUpperCase()}</strong> (econômico),
            Mid usa <strong>{tamanhosPorModelo.mid.toUpperCase()}</strong>{' '}
            (selecionado), Premium usa{' '}
            <strong>{tamanhosPorModelo.premium.toUpperCase()}</strong>{' '}
            (robusto). Cascata aplicada em manutenção (0,5%/mês CAPEX), seguro
            (0,2%/mês), contingência (10%), capital de giro (3 meses) e
            investimento total.
          </p>
        )}
      </Section>

      {/* 6.5 Kit Equipamentos Detalhado (schema v1.5)
         Só renderiza quando o pipeline gerou veredito + cenários financeiros.
         Sem essa guarda, em relatórios `failed` a tabela de equipamentos
         (hardcoded em frontend/src/data/kits/) seria exibida e revelaria que
         o kit não vem da análise — só esconder pra preservar a percepção
         de que tudo é gerado pelo pipeline. */}
      {(() => {
        const cenariosOk =
          !!out.viabilidade_3_cenarios?.low ||
          !!out.viabilidade_3_cenarios?.mid ||
          !!out.viabilidade_3_cenarios?.premium
        if (!out.veredito || !cenariosOk) return null
        const tipo = (data.input_canonico.tipo_negocio || 'academia') as ModeloNegocio
        const tamanho = (data.input_canonico.tamanho_preset || 'm') as TamanhoCodigo
        const kit = getKit(tipo, tamanho)
        if (!kit) return null
        return (
          <Section title="Kit de Equipamentos" collapsible>
            <KitEquipamentosTable kit={kit} />
          </Section>
        )
      })()}

      {/* 7. Posicionamento Recomendado (collapsible) */}
      {out.posicionamento_recomendado && (
        <TextoSecao
          title="Posicionamento Recomendado"
          texto={out.posicionamento_recomendado}
          collapsible
        />
      )}

      {/* 7.1 Posicionamento Estratégico A9 (ERRC) */}
      {out.posicionamento_estrategico && (
        <Section title="Posicionamento Estratégico (ERRC)" collapsible>
          <PosicionamentoCard data={out.posicionamento_estrategico} />
        </Section>
      )}

      {/* 7.4 Novas unidades (90d) — panorama em mini-cards. A lista nominal de
          entrantes (com QSA/contato) migrou pra rota de PROSPECÇÃO; aqui fica só o
          agregado (total/segmento/bairro) com o bairro pesquisado destacado. */}
      {out.entrantes_cnpj_90d && (out.entrantes_cnpj_90d.total ?? 0) > 0 && (
        <Section title="Novas unidades (90 dias)" collapsible>
          <NovasUnidadesCard block={out.entrantes_cnpj_90d} bairroAlvo={inp.bairro} />
        </Section>
      )}

      {/* 7.45 Obras fitness em andamento (CNO) */}
      {out.obras_cno_em_curso && (
        <Section title="Obras em andamento (CNO)" collapsible>
          <ObrasEmAndamentoTable block={out.obras_cno_em_curso} />
        </Section>
      )}

      {/* 7.46 Demanda futura datada (Apêndice B) */}
      {out.demanda_futura && out.demanda_futura.status === 'ok' && (
        <Section title="Demanda futura (obras no raio)" collapsible>
          <DemandaFuturaCard block={out.demanda_futura} />
        </Section>
      )}

      {/* 7.47 Anéis competitivos (Apêndice D) — score ponderado */}
      {out.aneis_competitivos && (out.aneis_competitivos.total_concorrentes ?? 0) > 0 && (
        <Section title="Anéis competitivos" collapsible>
          <AneisCompetitivosCard block={out.aneis_competitivos} />
        </Section>
      )}

      {/* 7.5 Cobertura Deep Research (schema v1.4) */}
      {out.cobertura_redes_a0 && out.cobertura_redes_a0.redes_solicitadas?.length > 0 && (
        <Section title="Cobertura Deep Research" collapsible>
          <CoberturaRedesA0Card
            cobertura={out.cobertura_redes_a0}
            bairroAlvo={data.input_canonico?.bairro || data.input_canonico?.cidade}
          />
        </Section>
      )}

      {/* 8. Inteligência Competitiva — tabela por concorrente substituindo Dores Dominantes */}
      {out.competitors_set && out.competitors_set.length > 0 && (
        <Section title="Inteligência Competitiva" collapsible>
          {(out.entrantes_cnpj_90d?.entrantes?.length ?? 0) === 0 && (
            <MapaMunicipioMercado
              className="mb-4"
              relatorioId={relatorioId}
              cidade={inp.cidade}
              uf={inp.uf ?? out.market_context?.uf}
              bairro={inp.bairro}
            />
          )}
          <InteligenciaCompetitivaResumoCard
            className="mb-4"
            nivelSaturacao={out.nivel_saturacao}
            panorama={out.panorama_competitivo}
            agregadosPlaces={out.agregados_competicao_places ?? null}
            totalEncontradosNearby={out.total_encontrados_raio_nearby ?? null}
            fonteBuscaCompetidores={out.fonte_busca_competidores ?? null}
            marketContext={out.market_context}
            coberturaRedes={out.cobertura_redes_a0}
            topIndependentes={out.top_independentes}
            academiasAnalisadas={out.academias_analisadas}
            totalEncontradosRaio={out.total_encontrados_raio}
            totalAnalisados={out.total_concorrentes_analisados}
            bairroAlvo={inp.bairro}
          />
          {/* Heatmap de dores dominantes (totais por categoria) */}
          <DoresHeatmap competidores={out.competitors_set} className="mb-4" />
          {/* Dores segmentadas por categoria — link pro review no Maps, sem texto */}
          <DoresPorCategoria competidores={out.competitors_set} />
          {/* Pico/lotação por academia — janela de demanda pro posicionamento */}
          <PicoLotacaoViz competidores={out.competitors_set} className="mt-4" />
          {/* "Concorrentes — dores citadas nos reviews" REMOVIDO: redundante com
              DoresHeatmap + DoresPorCategoria acima. O dado servicos_nao_oferecidos
              segue no output (A9/posicionamento consome). */}
          <div className="mt-4">
            <PlanosConcorrenciaTable competidores={out.competitors_set} />
          </div>
        </Section>
      )}

      {/* 9. Distribuição Geográfica */}
      {out.distribuicao_geografica && out.distribuicao_geografica.length > 0 && (
        <Section title="Distribuição Geográfica dos Concorrentes" collapsible>
          <DistribuicaoViz
            distribuicao={out.distribuicao_geografica}
            bairroAlvo={inp.bairro}
          />
        </Section>
      )}

      {/* 10. Bairros Alternativos (com aviso geográfico v1.5) */}
      {out.bairros_alternativos && out.bairros_alternativos.length > 0 && (
        <Section title="Bairros Alternativos Recomendados" collapsible>
          {out.aviso_geografico && (
            <div className="mb-4 rounded-md border-l-2 border-veredito-ressalvas bg-veredito-ressalvas/5 p-3 text-xs leading-relaxed">
              <strong className="text-veredito-ressalvas">
                Correção geográfica detectada
              </strong>
              <p className="mt-1 text-foreground/90">{out.aviso_geografico}</p>
              {out.cidade_efetiva && (
                <p className="mt-1 text-muted-foreground font-mono text-[10px]">
                  Município efetivo usado pra derivar bairros alternativos:{' '}
                  <span className="text-foreground font-semibold">
                    {out.cidade_efetiva}
                  </span>
                </p>
              )}
            </div>
          )}
          <BairrosAlternativosViz bairros={out.bairros_alternativos} />
        </Section>
      )}

      {/* 11. Script de Abordagem — só renderiza se A5 conseguiu extrair algo útil.
          Quando A5 falha, contato_decisor vem como {} e a section ficaria vazia. */}
      {(() => {
        // Ocultado até segunda ordem
        void out.contato_decisor
        return null
      })()}

      </div>
    </div>
  )
}

/**
 * Section — wrapper que usa SectionHeader por baixo pra consistência visual.
 *
 * UI Lote 1: Separator embaixo do título + escala tipográfica uniforme.
 * UI Lote 5: prop `collapsible` habilita colapsar/expandir clicando no header
 * (chevron rotativo 180°). Mantém a API antiga estática quando omitido.
 */
function Section({
  title,
  suffix,
  children,
  collapsible = false,
  defaultOpen = true,
}: {
  title: string
  suffix?: React.ReactNode
  children: React.ReactNode
  collapsible?: boolean
  defaultOpen?: boolean
}) {
  if (collapsible) {
    return (
      <CollapsibleSection title={title} suffix={suffix} defaultOpen={defaultOpen}>
        {children}
      </CollapsibleSection>
    )
  }
  return (
    <section
      id={slugify(title)}
      data-section-title={title}
      className="scroll-mt-24 space-y-4"
    >
      <SectionHeader title={title} suffix={suffix} />
      {children}
    </section>
  )
}

/**
 * CollapsibleSection — variante colapsável do Section.
 *
 * Substitui o SectionHeader por um header custom com o título dentro de um
 * <button> (CollapsibleTrigger) + chevron rotativo, mantendo o Separator
 * embaixo pra preservar o ritmo visual. O suffix (ex: fonte aluguel) é
 * renderizado fora do botão pra evitar HTML inválido (p dentro de button).
 */
function CollapsibleSection({
  title,
  suffix,
  defaultOpen,
  children,
}: {
  title: string
  suffix?: React.ReactNode
  defaultOpen: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <Collapsible open={open} onOpenChange={setOpen} asChild>
      <section
        id={slugify(title)}
        data-section-title={title}
        className="scroll-mt-24 space-y-4"
      >
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
                aria-expanded={open}
              >
                <span>{title}</span>
                <ChevronDown
                  size={14}
                  aria-hidden
                  className={cn(
                    'transition-transform',
                    open ? 'rotate-180' : 'rotate-0',
                  )}
                />
              </button>
            </CollapsibleTrigger>
            {suffix && <div className="flex items-center gap-2">{suffix}</div>}
          </div>
          <Separator className="mt-3" />
        </div>
        <CollapsibleContent className="space-y-4 data-[state=closed]:hidden">
          {children}
        </CollapsibleContent>
      </section>
    </Collapsible>
  )
}

function ViewerSkeleton() {
  return (
    <div className="space-y-8">
      <Skeleton className="h-12 w-2/3" />
      <Skeleton className="h-48 w-full" />
      <div className="grid grid-cols-3 gap-4">
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </div>
      <Skeleton className="h-96 w-full" />
    </div>
  )
}

function ViewerError({
  message,
  relatorioId,
  showRerun,
}: {
  message?: string
  relatorioId?: string
  showRerun?: boolean
}) {
  const navigate = useNavigate()

  return (
    <div className="space-y-4">
      <Button variant="ghost" size="sm" asChild>
        <Link to="/relatorios">
          <ArrowLeft size={14} /> Voltar
        </Link>
      </Button>
      <div className="rounded-lg border border-veredito-reprovado/40 bg-veredito-reprovado/5 p-6 space-y-4">
        <div>
          <h2 className="font-semibold text-veredito-reprovado mb-1">
            Não foi possível exibir o relatório
          </h2>
          <p className="text-sm text-muted-foreground">
            {message ?? 'Erro desconhecido'}
          </p>
        </div>
        {showRerun && relatorioId ? (
          <RerunPipelineButton relatorioId={relatorioId} />
        ) : null}
        {relatorioId ? (
          <DeleteRelatorioButton
            relatorioId={relatorioId}
            onDeleted={() => navigate({ to: '/relatorios' })}
          />
        ) : null}
      </div>
    </div>
  )
}
