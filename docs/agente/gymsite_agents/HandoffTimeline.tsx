// ============================================================
// components/handoff/HandoffTimeline.tsx
// Timeline visual do pipeline completo (sidebar)
// GymSite Intelligence v2.1
//
// FIX: barra de progresso usava corTexto (text-*) que não gera background.
//      Adicionado corBarraProgresso derivado do corBg com saturação maior.
// ============================================================

'use client'

import { motion } from 'framer-motion'
import { Check, Loader2, Circle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { HandoffTimelineProps } from '@/types/handoff'

// Mapeia corBg (bg-blue-100) → cor sólida da barra (bg-blue-500)
// Mantém consistência visual sem precisar de nova prop no SetorConfig
function getCorBarra(corBg: string): string {
  return corBg
    .replace('bg-', 'bg-')
    .replace('-100', '-500')
}

export function HandoffTimeline({ agentes, setores, state, className }: HandoffTimelineProps) {

  const getAgenteStatus = (agenteId: string) => {
    if (state.agenteAtivoId === agenteId) return 'ativo'
    if (state.agenteEntrandoId === agenteId) return 'entrando'
    const agente = agentes.find((a) => a.id === agenteId)
    const ativo = agentes.find((a) => a.id === state.agenteAtivoId)
    if (agente && ativo && agente.ordemPipeline < ativo.ordemPipeline) return 'completo'
    if (state.agenteAnteriorId === agenteId) return 'completo'
    return 'pendente'
  }

  return (
    <div className={cn('w-full', className)}>
      {/* Badges de setor no topo */}
      <div className="mb-4 flex flex-wrap items-center gap-1.5 px-1">
        {Object.values(setores).map((setor) => {
          const Icone = setor.icone
          return (
            <div
              key={setor.id}
              className={cn(
                'flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-medium',
                setor.corBg,
                setor.corTexto
              )}
            >
              <Icone className="h-3 w-3" />
              <span className="hidden sm:inline">{setor.nomeCurto}</span>
            </div>
          )
        })}
      </div>

      {/* Timeline vertical */}
      <div className="relative space-y-0">
        <div className="absolute bottom-2 left-[15px] top-2 w-px bg-border" />

        {agentes.map((agente, idx) => {
          const setor = setores[agente.setor]
          const status = getAgenteStatus(agente.id)
          // FIX: usa bg-*-500 em vez de text-*-700 para a barra de progresso
          const corBarra = getCorBarra(setor.corBg)

          return (
            <motion.div
              key={agente.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.03 }}
              className={cn(
                'group relative flex items-start gap-3 py-2 pl-1 pr-2',
                status === 'ativo' && 'rounded-lg bg-muted/50',
                status === 'entrando' && 'rounded-lg bg-primary/5'
              )}
            >
              {/* Indicador de status */}
              <div className="relative z-10 flex h-[30px] w-[30px] shrink-0 items-center justify-center">
                {status === 'completo' && (
                  <div className={cn('flex h-5 w-5 items-center justify-center rounded-full border', setor.corBg, setor.corBorda)}>
                    <Check className={cn('h-3 w-3', setor.corTexto)} />
                  </div>
                )}
                {status === 'ativo' && (
                  <div className={cn('flex h-6 w-6 items-center justify-center rounded-full border-2', setor.corBg, setor.corBorda, setor.corTexto)}>
                    <Loader2 className="h-3 w-3 animate-spin" />
                  </div>
                )}
                {status === 'entrando' && (
                  <motion.div
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ repeat: Infinity, duration: 1 }}
                    className={cn('flex h-5 w-5 items-center justify-center rounded-full border', setor.corBg, setor.corBorda)}
                  >
                    <div className={cn('h-2 w-2 rounded-full', setor.corTexto)} />
                  </motion.div>
                )}
                {status === 'pendente' && (
                  <Circle className="h-4 w-4 text-muted-foreground/30" />
                )}
              </div>

              {/* Conteúdo */}
              <div className="min-w-0 flex-1 pt-0.5">
                <div className="flex items-center gap-2">
                  <span className={cn(
                    'truncate text-xs font-medium',
                    status === 'ativo' && setor.corTexto,
                    status === 'pendente' && 'text-muted-foreground/50',
                    status === 'completo' && 'text-foreground/70'
                  )}>
                    {agente.nome}
                  </span>
                  <span className={cn('rounded px-1 py-px text-[9px] font-medium uppercase tracking-wider', setor.corBg, setor.corTexto)}>
                    {setor.nomeCurto}
                  </span>
                </div>
                <p className={cn('mt-0.5 text-[10px] leading-tight', status === 'ativo' ? 'text-muted-foreground' : 'text-muted-foreground/40')}>
                  {agente.descricao}
                </p>

                {/* FIX: barra de progresso com bg-*-500 em vez de text-*-700 */}
                {status === 'ativo' && state.progresso > 0 && (
                  <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-muted">
                    <motion.div
                      className={cn('h-full rounded-full', corBarra)}
                      initial={{ width: 0 }}
                      animate={{ width: `${state.progresso}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                )}
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
