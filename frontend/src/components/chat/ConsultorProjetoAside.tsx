import { Link } from '@tanstack/react-router'
import { CheckCircle2, Circle, FileText, MapPin } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { AgentAvatar } from '@/components/chat/AgentAvatar'
import { cn } from '@/lib/utils'
import { PESQUISA_AGENTE } from '@/config/agentes'
import type { ConsultorPesquisas, ConsultorProjeto } from '@/hooks/useConsultorChat'

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

interface ConsultorProjetoAsideProps {
  projeto: ConsultorProjeto | null
  className?: string
}

export function ConsultorProjetoContent({ projeto }: { projeto: ConsultorProjeto | null }) {
  const loc = projeto?.localizacao
  const locLabel = loc?.cidade ? [loc.bairro, loc.cidade, loc.uf].filter(Boolean).join(', ') : null

  return (
    <aside className="hidden w-80 shrink-0 flex-col gap-4 overflow-y-auto border-l border-border bg-card p-4 lg:flex">
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Projeto</h2>
        <div className="mt-2 rounded-xl border border-border bg-card p-3">
          {locLabel ? (
            <div className="flex items-center gap-1.5 text-sm font-medium">
              <MapPin className="h-3.5 w-3.5 text-lime" aria-hidden />
              <span className="truncate">{locLabel}</span>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Informe cidade e bairro para começar.</p>
          )}
          {projeto?.status && (
            <Badge variant="secondary" className="mt-2 text-[10px]">
              {STATUS_LABEL[projeto.status] || projeto.status}
            </Badge>
          )}
          {typeof projeto?.total_concorrentes === 'number' && (
            <p className="mt-2 text-[10px] text-muted-foreground">
              Concorrentes mapeados:{' '}
              <span className="font-medium text-foreground">{projeto.total_concorrentes}</span>
            </p>
          )}
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Pesquisas</h3>
        <ul className="grid grid-cols-1 gap-1.5">
          {PESQUISA_LABELS.map(({ key, label }) => {
            const done = Boolean(projeto?.pesquisas_realizadas?.[key])
            const ag = PESQUISA_AGENTE[key]
            const Icone = ag?.icone
            return (
              <li
                key={key}
                className={cn(
                  'flex items-center gap-2 rounded-lg border px-2.5 py-2 text-xs',
                  done ? 'border-primary bg-elevated' : 'border-border/60 bg-card',
                )}
              >
                {Icone ? (
                  <AgentAvatar
                    Icone={Icone}
                    imgSrc={ag?.img}
                    size="sm"
                    active={done}
                    className={cn(!done && 'opacity-70 ring-1 ring-border')}
                  />
                ) : done ? (
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-lime" />
                ) : (
                  <Circle className="h-3.5 w-3.5 shrink-0 text-muted-foreground/40" />
                )}
                <span className={cn('flex-1', done ? 'font-medium text-foreground' : 'text-muted-foreground')}>
                  {label}
                </span>
                <span
                  className={cn(
                    'font-mono text-[9px] uppercase',
                    done ? 'text-lime' : 'text-muted-foreground/60',
                  )}
                >
                  {done ? 'ok' : '—'}
                </span>
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
    </>
  )
}

/** Conteúdo do painel projeto — usado em drawer (paridade com jornada na degustação). */
export function ConsultorProjetoAside({ projeto, className }: ConsultorProjetoAsideProps) {
  return (
    <div className={cn('flex flex-col gap-4', className)}>
      <ConsultorProjetoContent projeto={projeto} />
    </div>
  )
}
