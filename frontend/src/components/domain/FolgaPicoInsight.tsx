/**
 * FolgaPicoInsight — refina a métrica "Folga capacidade" com a REALIDADE
 * medida do bairro (SearchAPI full, 12/06):
 *
 *   1. Pico dominante observado nos concorrentes (curvas popular_times)
 *   2. Reclamações de lotação nos reviews (categoria_dor=lotacao), com quote
 *   3. Ocupação projetada de cada modelo NESSE mesmo horário
 *
 * Argumento que o card entrega pro dono: "o concorrente opera a 100% às
 * 19h e o aluno reclama de lotação em review público; este dimensionamento
 * opera a X% nesse horário". Zero número inventado — tudo do relatório.
 */
import { Gauge, Users, Quote } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { CenarioJSON, CompetidorJSON } from '@/hooks/useRelatorioDetail'

const DIAS_LABEL: Record<string, string> = {
  segunda: 'segunda', terca: 'terça', quarta: 'quarta', quinta: 'quinta',
  sexta: 'sexta', sabado: 'sábado', domingo: 'domingo',
}

interface PicoObservado {
  diaHora: string
  freq: number
}

/** Moda de (dia, hora) entre os pico_semanal dos concorrentes ("Segunda 19h (100%)"). */
function picoDominante(competidores: CompetidorJSON[]): PicoObservado | null {
  const contagem = new Map<string, number>()
  for (const c of competidores) {
    const m = (c.pico_semanal ?? '').match(/^(\S+)\s+(\d{1,2})h/)
    if (!m) continue
    const dia = m[1].toLowerCase()
    const hora = Number(m[2])
    // agrupa horas vizinhas (18h e 19h = mesma janela de pico)
    const janela = hora >= 17 && hora <= 20 ? '18-20h' : `${hora}h`
    const chave = `${DIAS_LABEL[dia] ?? dia} ${janela}`
    contagem.set(chave, (contagem.get(chave) ?? 0) + 1)
  }
  let melhor: PicoObservado | null = null
  for (const [diaHora, freq] of contagem) {
    if (!melhor || freq > melhor.freq) melhor = { diaHora, freq }
  }
  return melhor
}

interface ReclamacaoLotacao {
  academia: string
  quote: string
  autor?: string
}

function reclamacoesLotacao(competidores: CompetidorJSON[]): {
  total: number
  academias: string[]
  destaque: ReclamacaoLotacao | null
} {
  let total = 0
  const academias = new Set<string>()
  let destaque: ReclamacaoLotacao | null = null
  for (const c of competidores) {
    for (const r of c.reviews ?? []) {
      if (r.categoria_dor !== 'lotacao') continue
      total++
      academias.add(c.nome)
      // Reviews do SearchAPI vêm com <br> e tags HTML cruas no texto
      const quote = (r.quote_curta ?? '')
        .replace(/<br\s*\/?>/gi, ' ')
        .replace(/<[^>]+>/g, '')
        .replace(/\s+/g, ' ')
        .trim()
      if (quote && (!destaque || quote.length > destaque.quote.length)) {
        destaque = { academia: c.nome, quote: quote.slice(0, 180), autor: r.autor }
      }
    }
  }
  return { total, academias: [...academias], destaque }
}

const MODELO_LABEL: Record<string, string> = {
  low: 'Low Cost',
  mid: 'Mid Market',
  premium: 'Premium',
}

export function FolgaPicoInsight({
  cenarios,
  competidores,
  className,
}: {
  cenarios?: Record<string, CenarioJSON> | null
  competidores?: CompetidorJSON[] | null
  className?: string
}) {
  const comps = competidores ?? []
  const pico = picoDominante(comps)
  const lotacao = reclamacoesLotacao(comps)
  const nComCurva = comps.filter(
    (c) => c.horarios_pico && Object.keys(c.horarios_pico).length > 0,
  ).length

  // Sem pico medido E sem reclamação = sem história pra contar (P-004)
  if (!pico && lotacao.total === 0) return null

  const ocupacoes = (['low', 'mid', 'premium'] as const)
    .map((m) => {
      const c = cenarios?.[m]
      const picoCalc = c?.alunos_pico_calculado
      const cap = c?.capacidade_simultanea_pico ?? c?.capacidade_maxima_alunos
      if (picoCalc == null || !cap) return null
      return { modelo: MODELO_LABEL[m], ocupacaoPct: Math.round((picoCalc / cap) * 100) }
    })
    .filter((x): x is { modelo: string; ocupacaoPct: number } => x !== null)

  return (
    <div className={cn('rounded-lg border border-border bg-card overflow-hidden', className)}>
      <header className="px-4 py-2.5 border-b border-border bg-muted/20 flex items-center gap-2">
        <Gauge size={14} className="text-muted-foreground" />
        <div>
          <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-mono font-medium">
            Folga no pico × realidade do bairro
          </h3>
          <p className="text-[10px] text-muted-foreground mt-0.5">
            Curvas de movimento medidas ({nComCurva} concorrentes) + reclamações reais nos reviews
          </p>
        </div>
      </header>

      <div className="px-4 py-3 space-y-3 text-sm">
        {pico && (
          <p>
            <Users size={13} className="inline mr-1.5 text-muted-foreground" />
            O bairro lota na <strong>{pico.diaHora}</strong>:{' '}
            {pico.freq} de {nComCurva || comps.length} concorrentes atingem o pico máximo nessa
            janela (medição Google ao longo das últimas semanas).
          </p>
        )}

        {lotacao.total > 0 && (
          <div>
            <p>
              <strong>{lotacao.total} reclamaç{lotacao.total === 1 ? 'ão' : 'ões'} de lotação</strong>{' '}
              nos reviews de {lotacao.academias.slice(0, 3).join(', ')}
              {lotacao.academias.length > 3 && ` e mais ${lotacao.academias.length - 3}`} —
              o aluno do bairro JÁ sofre com academia cheia.
            </p>
            {lotacao.destaque && (
              <blockquote className="mt-1.5 border-l-2 border-veredito-reprovado/50 pl-3 text-xs italic text-muted-foreground">
                <Quote size={10} className="inline mr-1 opacity-60" />
                “{lotacao.destaque.quote}”
                <span className="not-italic font-mono text-[10px]"> — review da {lotacao.destaque.academia}</span>
              </blockquote>
            )}
          </div>
        )}

        {ocupacoes.length > 0 && (
          <div className="rounded-md bg-muted/30 px-3 py-2.5">
            <p className="text-xs font-medium mb-1.5">
              Ocupação projetada DESTE projeto no mesmo horário de pico:
            </p>
            <div className="flex flex-wrap gap-x-5 gap-y-1">
              {ocupacoes.map((o) => (
                <span key={o.modelo} className="text-xs font-mono">
                  {o.modelo}:{' '}
                  <strong
                    className={cn(
                      o.ocupacaoPct <= 60 ? 'text-emerald-600 dark:text-emerald-400'
                        : o.ocupacaoPct <= 85 ? 'text-amber-600 dark:text-amber-400'
                        : 'text-veredito-reprovado',
                    )}
                  >
                    {o.ocupacaoPct}% da capacidade
                  </strong>
                </span>
              ))}
            </div>
            <p className="mt-1.5 text-[11px] text-muted-foreground">
              Enquanto o concorrente opera no limite{lotacao.total > 0 ? ' e coleciona reclamação pública' : ''},
              este dimensionamento mantém treino sem fila no horário mais disputado —
              promessa de marketing defensável com número.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
