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
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Loader2, AlertTriangle, Clock, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { supabase } from '@/lib/supabase'
import { useDeleteRelatorio } from '@/hooks/useDeleteRelatorio'
import { useRerunPipeline } from '@/hooks/useRerunPipeline'
import { notify } from '@/lib/notify'
import { trackPipeline, untrackPipeline } from '@/lib/pipeline-tracker'
import { pipelineEtaWaitingLine } from '@/lib/pipeline-eta'

interface StatusResponse {
  id: string
  status: 'queued' | 'running' | 'done' | 'failed' | 'cancelled'
  erro_mensagem: string | null
  tempo_execucao_segundos: number | null
  data_execucao: string | null
}

const STATUS_LABEL: Record<StatusResponse['status'], string> = {
  queued: 'Na fila — preparando ambiente do pipeline',
  running: 'Rodando pipeline (A0 → A6) — coletando dados e gerando análise',
  done: 'Pronto — redirecionando para o relatório',
  failed: 'Pipeline falhou',
  cancelled: 'Cancelado',
}

const PIPELINE_STEPS = [
  'A0 ContextBuilder — Deep Research de mercado',
  'A1 GeoScout — Pontos comerciais via Maps',
  'A2/A3/A4 paralelo — Demografia, concorrentes, viabilidade',
  'A5 ContactHunter — Decisor e script',
  'A6 ReportConsolidator — Relatório final',
]

// Regex UUID v4 (formato Postgres). Rejeita "510dafe6..." reticências e similares.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function RelatorioAguardandoPage() {
  const { relatorioId } = useParams({ from: '/relatorios/$relatorioId/aguardando' })
  const navigate = useNavigate()
  const isValidId = UUID_RE.test(relatorioId)

  useEffect(() => {
    if (isValidId) trackPipeline(relatorioId)
  }, [isValidId, relatorioId])

  const [armed, setArmed] = useState(false)
  const armedTimeoutRef = useRef<number | null>(null)
  const deleteMutation = useDeleteRelatorio()
  const rerunMutation = useRerunPipeline()

  useEffect(() => {
    return () => {
      if (armedTimeoutRef.current) window.clearTimeout(armedTimeoutRef.current)
    }
  }, [])

  function handleApagar() {
    if (!armed) {
      setArmed(true)
      armedTimeoutRef.current = window.setTimeout(() => setArmed(false), 3000)
      return
    }
    if (armedTimeoutRef.current) window.clearTimeout(armedTimeoutRef.current)
    setArmed(false)
    deleteMutation.mutate(relatorioId, {
      onSuccess: () => {
        notify.success('Relatório apagado')
        navigate({ to: '/relatorios' })
      },
      onError: (err) => notify.error(err),
    })
  }

  function tentarNovamente() {
    rerunMutation.mutate({ relatorioId })
  }

  const { data, error } = useQuery<StatusResponse>({
    queryKey: ['relatorio-status', relatorioId],
    enabled: isValidId,
    // Polling roda a cada 5s — não queremos toast a cada falha transitória.
    meta: { silent: true },
    queryFn: async () => {
      const { data, error } = await supabase
        .from('relatorios')
        .select('id, status, erro_mensagem, tempo_execucao_segundos, data_execucao')
        .eq('id', relatorioId)
        .single()
      if (error) throw new Error(`Supabase: ${error.message}`)
      return data as unknown as StatusResponse
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
      <header className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">
          Gerando relatório
        </h1>
        <p className="text-sm text-muted-foreground font-mono">
          id: <span className="text-foreground">{relatorioId}</span>
        </p>
      </header>

      {isLoading && (
        <div className="rounded-lg border border-border bg-card p-8 space-y-6">
          <div className="flex items-center justify-center">
            <Loader2 size={40} className="animate-spin text-primary" />
          </div>
          <div className="space-y-1 text-center">
            <p className="text-sm font-medium">{STATUS_LABEL[status]}</p>
            <p className="text-xs text-muted-foreground flex items-center justify-center gap-1.5">
              <Clock size={12} />
              {pipelineEtaWaitingLine()}
            </p>
          </div>
          <ol className="space-y-1.5 text-xs font-mono">
            {PIPELINE_STEPS.map((step, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-muted-foreground"
              >
                <span className="text-foreground/40">{String(i + 1).padStart(2, '0')}</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

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
                onClick={() => navigate({ to: '/relatorios/new' })}
              >
                Começar do zero
              </Button>
              <Button
                variant={armed ? 'destructive' : 'ghost'}
                size="sm"
                onClick={handleApagar}
                disabled={deleteMutation.isPending}
                className={armed ? '' : 'text-veredito-reprovado hover:text-veredito-reprovado hover:bg-veredito-reprovado/10'}
              >
                {deleteMutation.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Trash2 size={14} />
                )}
                {armed ? 'Confirmar exclusão?' : 'Apagar este relatório'}
              </Button>
            </div>
            <p className="text-[10px] text-muted-foreground">
              "Tentar novamente" cria um relatório novo — o falho fica no histórico.
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
