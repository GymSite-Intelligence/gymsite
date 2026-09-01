/**
 * RelatorioAguardandoPage — tela de espera entre criação e pipeline completo.
 *
 * Fluxo: NovoRelatorioPage faz POST /api/relatorios → backend retorna id em
 * status="queued" → frontend navega aqui passando o id → polling a cada 5s
 * do GET /api/relatorios/{id}/status até status virar "done" (redirect pro
 * viewer) ou "failed" (mostra erro com retry).
 *
 * Estados visuais:
 *   queued/running → spinner + barra de etapas estimadas (sem progresso real
 *                     porque o pipeline não emite percent — uma melhoria
 *                     futura seria SSE com eventos por agente)
 *   done           → redirect automático
 *   failed         → cartão de erro com mensagem do backend + CTA voltar
 */
import { useEffect } from 'react'
import { useNavigate, useParams } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Loader2, AlertTriangle, Clock, CheckCircle2, Circle, Gauge, ListChecks } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { DeleteRelatorioButton } from '@/components/domain/DeleteRelatorioButton'
import { StatusPipelineBadge } from '@/components/domain/StatusPipelineBadge'
import { API_BASE } from '@/lib/supabase'
import { useRerunPipeline } from '@/hooks/useRerunPipeline'
import { trackPipeline, untrackPipeline } from '@/lib/pipeline-tracker'
import { pipelineEtaWaitingLine, pipelineEtaRangeLabel } from '@/lib/pipeline-eta'
import { cn } from '@/lib/utils'

interface EtapaConcluida {
  agente: string
  fim?: string
  duracao_s?: number | null
}

interface StatusResponse {
  id: string
  status: 'queued' | 'running' | 'done' | 'failed' | 'cancelled'
  erro_mensagem: string | null
  tempo_execucao_segundos: number | null
  data_execucao: string | null
  etapa_atual?: string | null
  etapas_concluidas?: EtapaConcluida[] | null
}

const STATUS_LABEL: Record<StatusResponse['status'], string> = {
  queued: 'Na fila — preparando a análise',
  running: 'Coletando dados oficiais e gerando a análise',
  done: 'Pronto — redirecionando para o relatório',
  failed: 'Pipeline falhou',
  cancelled: 'Cancelado',
}

/**
 * Etapas do stepper — copy por FONTE (P-001: o usuário vê de onde vem o
 * dado, não o codinome do agente). Pesos = duração média real de cada
 * fase; a barra de progresso pondera por eles, não por contagem.
 */
const ETAPAS_PIPELINE: {
  agentes: string[]
  peso: number
  titulo: string
  fontes: string
}[] = [
  {
    agentes: ['ContextBuilder'],
    peso: 5,
    titulo: 'Contexto de mercado',
    fontes: 'IBGE · Receita Federal (CNPJ/CNO) · portais de aluguel',
  },
  {
    agentes: ['GeoScout'],
    peso: 15,
    titulo: 'Imóveis e âncoras do bairro',
    fontes: 'Google Maps · OLX / ImovelWeb',
  },
  {
    agentes: [
      'DemoAnalyst',
      'CompetitorSearch',
      'CompetitorAnalysis',
      'CompetitorMapper',
      'FinancialEstimator',
    ],
    peso: 45,
    titulo: 'Demografia, concorrência e viabilidade (em paralelo)',
    fontes: 'Censo/IBGE 2022 · Google Places + reviews reais · 3 cenários financeiros (benchmark ACAD/Sebrae)',
  },
  {
    agentes: ['ContactHunter'],
    peso: 10,
    titulo: 'Contato e abordagem',
    fontes: 'Script de abordagem a partir do candidato #1 (GeoScout)',
  },
  {
    agentes: ['ReportConsolidator'],
    peso: 15,
    titulo: 'Consolidação do relatório',
    fontes: 'síntese auditável de todas as fontes',
  },
  {
    agentes: ['PositioningStrategist'],
    peso: 10,
    titulo: 'Posicionamento estratégico (ERRC)',
    fontes: 'headroom de renda (IBGE 2022) + gaps de serviço × dores dos concorrentes',
  },
]

type EstadoEtapa = 'concluida' | 'ativa' | 'pendente'

function estadosEtapas(
  etapaAtual: string | null | undefined,
  concluidas: EtapaConcluida[] | null | undefined,
): { estados: EstadoEtapa[]; progressoPct: number } {
  const done = new Set((concluidas ?? []).map((e) => e.agente))
  const estados: EstadoEtapa[] = ETAPAS_PIPELINE.map((etapa) => {
    if (etapa.agentes.every((a) => done.has(a))) return 'concluida'
    if (
      (etapaAtual && etapa.agentes.includes(etapaAtual)) ||
      etapa.agentes.some((a) => done.has(a))
    )
      return 'ativa'
    return 'pendente'
  })
  let pct = 0
  ETAPAS_PIPELINE.forEach((etapa, i) => {
    if (estados[i] === 'concluida') pct += etapa.peso
    else if (estados[i] === 'ativa') {
      // fração da etapa ativa = agentes do grupo já concluídos + meia-vida do atual
      const feitos = etapa.agentes.filter((a) => done.has(a)).length
      pct += etapa.peso * Math.min(0.9, (feitos + 0.5) / etapa.agentes.length)
    }
  })
  return { estados, progressoPct: Math.min(99, Math.round(pct)) }
}

// Regex UUID v4 (formato Postgres). Rejeita "510dafe6..." reticências e similares.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/**
 * Stat — chip de resumo (mesmo padrão do DemandaFuturaCard/viewer): ícone
 * accent + valor + label, dentro de um cartão `bg-card`.
 */
function Stat({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Gauge
  label: string
  value: React.ReactNode
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg border bg-card px-3 py-2">
      <Icon className="size-4 text-chart-1 shrink-0" />
      <div className="min-w-0 leading-tight">
        <div className="truncate text-sm font-semibold">{value}</div>
        <div className="text-[11px] text-muted-foreground">{label}</div>
      </div>
    </div>
  )
}

export function RelatorioAguardandoPage() {
  const { relatorioId } = useParams({ from: '/relatorios/$relatorioId/aguardando' })
  const navigate = useNavigate()
  const isValidId = UUID_RE.test(relatorioId)

  useEffect(() => {
    if (isValidId) trackPipeline(relatorioId)
  }, [isValidId, relatorioId])

  const rerunMutation = useRerunPipeline()

  function tentarNovamente() {
    rerunMutation.mutate({ relatorioId })
  }

  const { data, error } = useQuery<StatusResponse>({
    queryKey: ['relatorio-status', relatorioId],
    enabled: isValidId,
    // Polling roda a cada 5s — não queremos toast a cada falha transitória.
    meta: { silent: true },
    queryFn: async () => {
      const res = await fetch(
        `${API_BASE.replace(/\/$/, '')}/api/relatorios/${relatorioId}/status`,
      )
      if (!res.ok) {
        const detail = await res.text().catch(() => '')
        throw new Error(
          detail || `API status ${res.status} — verifique se o backend está no ar`,
        )
      }
      return (await res.json()) as StatusResponse
    },
    refetchInterval: (q) => {
      const s = q.state.data?.status
      // Para de pollar quando terminou
      return s === 'done' || s === 'failed' || s === 'cancelled' ? false : 5000
    },
    refetchIntervalInBackground: true,
  })

  // Redirect automático quando completar
  useEffect(() => {
    if (data?.status === 'done') {
      untrackPipeline(relatorioId)
      const t = setTimeout(() => {
        navigate({ to: '/relatorios/$relatorioId', params: { relatorioId } })
      }, 800)
      return () => clearTimeout(t)
    }
    if (data?.status === 'failed' || data?.status === 'cancelled') {
      untrackPipeline(relatorioId)
    }
  }, [data?.status, relatorioId, navigate])

  // Early return amigável quando o ID na URL não é UUID válido.
  // Evita query Supabase que retornaria 22P02 (invalid uuid syntax).
  if (!isValidId) {
    return (
      <div className="container max-w-2xl py-12 space-y-4">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>ID de relatório inválido</AlertTitle>
          <AlertDescription className="space-y-3">
            <p>
              A URL contém um identificador que não é um UUID válido. Talvez
              o link foi truncado ou copiado errado.
            </p>
            <Button size="sm" onClick={() => navigate({ to: '/relatorios' })}>
              Voltar para a lista
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  const status = data?.status ?? 'queued'
  const isFailed = status === 'failed'
  const isLoading = status === 'queued' || status === 'running'

  return (
    <div className="container max-w-2xl py-12 space-y-6">
      <header className="space-y-3 rounded-xl border border-border bg-card p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-bold tracking-tight">Gerando relatório</h1>
          <StatusPipelineBadge status={status} />
        </div>
        <p className="text-xs text-muted-foreground font-mono">
          id: <span className="text-foreground">{relatorioId}</span>
        </p>
      </header>

      {isLoading && (() => {
        const { estados, progressoPct } = estadosEtapas(
          data?.etapa_atual,
          data?.etapas_concluidas,
        )
        const duracoes = new Map(
          (data?.etapas_concluidas ?? []).map((e) => [e.agente, e.duracao_s]),
        )
        const nConcluidas = estados.filter((e) => e === 'concluida').length
        const idxAtiva = estados.findIndex((e) => e === 'ativa')
        const etapaAtivaTitulo =
          idxAtiva >= 0 ? ETAPAS_PIPELINE[idxAtiva]!.titulo : '—'
        return (
          <div className="rounded-xl border border-border bg-card p-6 sm:p-8 space-y-6">
            <div className="space-y-1">
              <p className="text-sm font-medium">{STATUS_LABEL[status]}</p>
              <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                <Clock size={12} />
                {pipelineEtaWaitingLine()}
              </p>
            </div>

            {/* Resumo em chips — mesmo padrão Stat do viewer/DemandaFuturaCard */}
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat icon={Gauge} label="progresso" value={`${progressoPct}%`} />
              <Stat
                icon={Loader2}
                label="etapa atual"
                value={<span className="text-chart-1">{etapaAtivaTitulo}</span>}
              />
              <Stat
                icon={ListChecks}
                label="etapas concluídas"
                value={`${nConcluidas}/${ETAPAS_PIPELINE.length}`}
              />
              <Stat icon={Clock} label="tempo estimado" value={pipelineEtaRangeLabel()} />
            </div>

            {/* Barra ponderada por duração média de cada fase */}
            <div className="space-y-1">
              <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-700"
                  style={{ width: `${Math.max(3, progressoPct)}%` }}
                />
              </div>
              <p className="text-right text-[10px] font-mono text-muted-foreground">
                {progressoPct}%
              </p>
            </div>

            <ol className="space-y-2.5">
              {ETAPAS_PIPELINE.map((etapa, i) => {
                const estado = estados[i]
                const durTotal = etapa.agentes
                  .map((a) => duracoes.get(a))
                  .filter((d): d is number => typeof d === 'number')
                  .reduce((s, d) => s + d, 0)
                return (
                  <li key={i} className="flex items-start gap-2.5">
                    <span className="mt-0.5 shrink-0">
                      {estado === 'concluida' ? (
                        <CheckCircle2 size={15} className="text-veredito-aprovado" />
                      ) : estado === 'ativa' ? (
                        <Loader2 size={15} className="animate-spin text-chart-1" />
                      ) : (
                        <Circle size={15} className="text-muted-foreground/30" />
                      )}
                    </span>
                    <div className="min-w-0">
                      <p
                        className={cn(
                          'text-xs font-medium leading-tight',
                          estado === 'pendente' && 'text-muted-foreground/60',
                          estado === 'ativa' && 'text-chart-1',
                        )}
                      >
                        {etapa.titulo}
                        {estado === 'concluida' && durTotal > 0 && (
                          <span className="ml-1.5 font-mono text-[10px] text-muted-foreground">
                            {Math.round(durTotal)}s
                          </span>
                        )}
                      </p>
                      <p
                        className={cn(
                          'text-[10px] text-muted-foreground leading-tight',
                          estado === 'pendente' && 'opacity-50',
                        )}
                      >
                        {etapa.fontes}
                      </p>
                    </div>
                  </li>
                )
              })}
            </ol>

            <div className="flex justify-center pt-2 border-t border-border">
              <DeleteRelatorioButton
                relatorioId={relatorioId}
                onDeleted={() => navigate({ to: '/relatorios' })}
              />
            </div>
          </div>
        )
      })()}

      {status === 'done' && (
        <Alert variant="success">
          <AlertTitle>Relatório pronto</AlertTitle>
          <AlertDescription>
            Redirecionando para o viewer…
            {data?.tempo_execucao_segundos != null && (
              <> Executado em {data.tempo_execucao_segundos}s.</>
            )}
          </AlertDescription>
        </Alert>
      )}

      {isFailed && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Pipeline falhou</AlertTitle>
          <AlertDescription className="space-y-3">
            <p className="font-mono text-xs whitespace-pre-wrap">
              {data?.erro_mensagem ?? 'Erro desconhecido — verifique logs do backend.'}
            </p>
            <div className="flex gap-2 flex-wrap">
              <Button
                size="sm"
                onClick={() => tentarNovamente()}
                disabled={rerunMutation.isPending}
              >
                {rerunMutation.isPending ? (
                  <>Iniciando pipeline…</>
                ) : (
                  <>Tentar novamente com mesmos parâmetros</>
                )}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate({ to: '/explorar', search: { novo: true } })}
              >
                Começar do zero
              </Button>
              <DeleteRelatorioButton
                relatorioId={relatorioId}
                onDeleted={() => navigate({ to: '/relatorios' })}
              />
            </div>
            <p className="text-[10px] text-muted-foreground">
              "Tentar novamente" cria um relatório novo — o anterior fica no histórico.
              {' '}"Apagar" remove permanentemente da base.
            </p>
          </AlertDescription>
        </Alert>
      )}

      {error && status !== 'failed' && (
        <Alert variant="warning">
          <AlertTitle>Erro ao consultar status</AlertTitle>
          <AlertDescription className="font-mono text-xs">
            {(error as Error).message}
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
