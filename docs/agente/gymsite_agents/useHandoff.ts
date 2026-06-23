// ============================================================
// hooks/useHandoff.ts — Estado e lógica do Handoff Badge
// GymSite Intelligence v2.1
//
// FIXES aplicados:
//  - tempoMinimoVisivel agora realmente implementado (era declarado mas ignorado)
//  - Tipo 'completo' não trava badge em 100% — pipeline segue normalmente
// ============================================================

import { useState, useCallback, useRef, useEffect } from 'react'
import type { HandoffState, HandoffEvent } from '../types/handoff'

interface UseHandoffOptions {
  duracaoEntrada?: number
  duracaoSaida?: number
  /** Tempo mínimo (ms) que um agente fica visível — evita flash em agentes rápidos */
  tempoMinimoVisivel?: number
}

const DEFAULT_OPTIONS: Required<UseHandoffOptions> = {
  duracaoEntrada: 600,
  duracaoSaida: 300,
  tempoMinimoVisivel: 1200,
}

const ESTADO_INICIAL: HandoffState = {
  agenteAtivoId: null,
  agenteAnteriorId: null,
  agenteEntrandoId: null,
  status: 'idle',
  progresso: 0,
  timestampInicio: null,
  erro: null,
}

export function useHandoff(options: UseHandoffOptions = {}) {
  const opts = { ...DEFAULT_OPTIONS, ...options }
  const [state, setState] = useState<HandoffState>(ESTADO_INICIAL)

  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([])
  // FIX: rastreia o timestamp de quando o agente atual ficou visível
  // para implementar tempoMinimoVisivel
  const visibleSinceRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach(clearTimeout)
    }
  }, [])

  const clearAllTimeouts = useCallback(() => {
    timeoutsRef.current.forEach(clearTimeout)
    timeoutsRef.current = []
  }, [])

  const scheduleTimeout = useCallback((fn: () => void, delay: number) => {
    const t = setTimeout(fn, delay)
    timeoutsRef.current.push(t)
    return t
  }, [])

  const dispatchHandoff = useCallback(
    (event: HandoffEvent) => {
      const { fromAgenteId, toAgenteId, tipo } = event

      if (tipo === 'inicio') {
        clearAllTimeouts()
        visibleSinceRef.current = Date.now()
        setState({
          ...ESTADO_INICIAL,
          agenteAtivoId: toAgenteId,
          timestampInicio: Date.now(),
        })
        return
      }

      if (tipo === 'handoff') {
        clearAllTimeouts()

        // FIX: respeita tempoMinimoVisivel antes de trocar o badge
        const agora = Date.now()
        const tempoDecorrido = visibleSinceRef.current
          ? agora - visibleSinceRef.current
          : opts.tempoMinimoVisivel

        const delay = Math.max(0, opts.tempoMinimoVisivel - tempoDecorrido)

        scheduleTimeout(() => {
          // Fase 1: mostra o novo crachá descendo
          setState((prev) => ({
            ...prev,
            agenteAnteriorId: fromAgenteId,
            agenteEntrandoId: toAgenteId,
            status: 'transicionando',
            progresso: 100,
          }))

          // Fase 2: troca para o novo agente ativo
          scheduleTimeout(() => {
            visibleSinceRef.current = Date.now()
            setState((prev) => ({
              ...prev,
              agenteAtivoId: toAgenteId,
              agenteAnteriorId: fromAgenteId,
              agenteEntrandoId: null,
              status: 'idle',
              progresso: 0,
              timestampInicio: Date.now(),
              erro: null,
            }))
          }, opts.duracaoEntrada)
        }, delay)

        return
      }

      if (tipo === 'completo') {
        // FIX: 'completo' só marca progresso 100% do agente ATUAL.
        // NÃO trava o pipeline — o próximo 'handoff' event avança normalmente.
        // O badge NÃO fica preso em 100%; a troca acontece no próximo handoff.
        setState((prev) => ({
          ...prev,
          progresso: 100,
        }))
        return
      }

      if (tipo === 'erro') {
        clearAllTimeouts()
        setState((prev) => ({
          ...prev,
          erro: (event.payload?.message as string) || 'Erro desconhecido',
          status: 'idle',
        }))
      }
    },
    [clearAllTimeouts, scheduleTimeout, opts.duracaoEntrada, opts.tempoMinimoVisivel]
  )

  const setProgresso = useCallback((progresso: number) => {
    setState((prev) => ({
      ...prev,
      progresso: Math.min(100, Math.max(0, progresso)),
    }))
  }, [])

  const reset = useCallback(() => {
    clearAllTimeouts()
    visibleSinceRef.current = null
    setState(ESTADO_INICIAL)
  }, [clearAllTimeouts])

  return { state, dispatchHandoff, setProgresso, reset }
}
