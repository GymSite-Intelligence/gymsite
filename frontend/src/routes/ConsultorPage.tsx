import { Link } from '@tanstack/react-router'
import { CheckCircle2, Circle, FileText, MapPin } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { ConsultorChat } from '@/components/chat/ConsultorChat'
import { useConsultorChat, type ConsultorPesquisas } from '@/hooks/useConsultorChat'
import { PESQUISA_AGENTE, SETOR_STYLE } from '@/config/agentes'
import { especialistaPadrao } from '@/config/consultor-agentes'

const PESQUISA_LABELS: { key: keyof ConsultorPesquisas; label: string }[] = [
  { key: 'mercado', label: 'Contexto de mercado' },
  { key: 'demografia', label: 'Demografia (IBGE)' },
  { key: 'concorrentes', label: 'Concorrentes' },
  { key: 'reviews', label: 'Reviews e dores' },
  { key: 'oferta_concorrentes', label: 'Oferta e serviços' },
  { key: 'pontos_comerciais', label: 'Pontos comerciais' },
  { key: 'investimento', label: 'Viabilidade financeira' },
]

const STATUS_LABEL: Record<string, string> = {
  EM_CONVERSA: 'Em conversa',
  PESQUISANDO: 'Pesquisando',
  CONSOLIDANDO: 'Gerando relatório',
  RELATORIO_GERADO: 'Relatório pronto',
  ARQUIVADO: 'Arquivado',
}

export function ConsultorPage() {
  const {
    messages,
    projeto,
    sugestoes,
    podeGerarRelatorio,
    isLoading,
    isGeneratingReport,
    error,
    sendMessage,
    gerarRelatorio,
    novaConversa,
  } = useConsultorChat()

  const loc = projeto?.localizacao
  const locLabel = loc?.cidade ? [loc.bairro, loc.cidade, loc.uf].filter(Boolean).join(', ') : null
  const IconeConsultor = especialistaPadrao.Icone

  return (
    <div className="flex h-[calc(100vh-3.5rem)] w-full overflow-hidden">
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center gap-3 border-b px-4 sm:px-6">
          <span className="flex h-7 w-7 items-center justify-center overflow-hidden rounded-full bg-primary/10 p-0.5">
            <IconeConsultor className="h-full w-full object-contain" />
          </span>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold leading-tight">Consultor GymSite</h1>
            <p className="truncate text-[10px] text-muted-foreground">
              {locLabel || 'Análise de viabilidade em tempo real'}
            </p>
          </div>
          <div className="ml-auto">
            <Button variant="ghost" size="sm" className="h-8 gap-1 text-xs" onClick={novaConversa}>
              Nova conversa
            </Button>
          </div>
        </header>

        <ConsultorChat
          messages={messages}
          sugestoes={sugestoes}
          isLoading={isLoading}
          isGeneratingReport={isGeneratingReport}
          podeGerarRelatorio={podeGerarRelatorio}
          temRelatorio={Boolean(projeto?.relatorio_id)}
          error={error}
          onSend={sendMessage}
          onGerarRelatorio={gerarRelatorio}
        />
      </div>

      <aside className="hidden w-72 shrink-0 flex-col gap-4 border-l bg-muted/20 p-4 lg:flex">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Projeto</h2>
          {locLabel ? (
            <div className="mt-1 flex items-center gap-1.5 text-sm font-medium">
              <MapPin className="h-3.5 w-3.5 text-primary" aria-hidden />
              <span className="truncate">{locLabel}</span>
            </div>
          ) : (
            <p className="mt-1 text-sm text-muted-foreground">Informe cidade e bairro para começar.</p>
          )}
          {projeto?.status && (
            <Badge variant="secondary" className="mt-2 text-[10px]">
              {STATUS_LABEL[projeto.status] || projeto.status}
            </Badge>
          )}
        </div>

        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Pesquisas</h3>
          <ul className="space-y-1.5">
            {PESQUISA_LABELS.map(({ key, label }) => {
              const done = Boolean(projeto?.pesquisas_realizadas?.[key])
              const ag = PESQUISA_AGENTE[key]
              const Icone = ag?.icone
              const st = ag ? SETOR_STYLE[ag.setor] : undefined
              return (
                <li key={key} className="flex items-center gap-2 text-xs">
                  {Icone ? (
                    <span
                      className={cn(
                        'flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full transition-all',
                        done ? `ring-2 ${st?.ring} shadow-sm` : 'opacity-70 ring-1 ring-border',
                      )}
                    >
                      <Icone className="h-full w-full object-cover" />
                    </span>
                  ) : done ? (
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-primary" />
                  ) : (
                    <Circle className="h-3.5 w-3.5 shrink-0 text-muted-foreground/40" />
                  )}
                  <span className={cn(done ? 'font-medium text-foreground' : 'text-muted-foreground')}>{label}</span>
                </li>
              )
            })}
          </ul>
        </div>

        <div className="mt-auto space-y-2">
          {typeof projeto?.custo_brl_ate_agora === 'number' && projeto.custo_brl_ate_agora > 0 && (
            <p className="text-[11px] text-muted-foreground">
              Custo de pesquisa:{' '}
              <span className="font-medium text-foreground">R$ {projeto.custo_brl_ate_agora.toFixed(2)}</span>
            </p>
          )}
          {projeto?.relatorio_id && (
            <Button variant="outline" size="sm" className="w-full gap-1 text-xs" asChild>
              <Link to="/relatorios/$relatorioId/aguardando" params={{ relatorioId: projeto.relatorio_id }}>
                <FileText className="h-3.5 w-3.5" />
                Acompanhar relatório
              </Link>
            </Button>
          )}
        </div>
      </aside>
    </div>
  )
}
