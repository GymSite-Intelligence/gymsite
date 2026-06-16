/**
 * PicoLotacaoViz — janela de lotação (pico) por academia, para posicionamento.
 *
 * Lê horarios_pico (7 dias × 24h, % movimento) + pico_semanal. Cada academia
 * vira mini-card: pico (dia/hora/%) + barras semanais (forma da semana). No topo,
 * insight da janela de pico DOMINANTE do mercado — onde há mais concorrência por
 * espaço; fora dela = oportunidade de horário pro consultor.
 */
import type { CompetidorJSON } from '@/hooks/useRelatorioDetail'
import { Flame } from 'lucide-react'
import { cn } from '@/lib/utils'

const ORDEM = ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo']
const ABREV: Record<string, string> = {
  segunda: 'Seg', terca: 'Ter', quarta: 'Qua', quinta: 'Qui',
  sexta: 'Sex', sabado: 'Sáb', domingo: 'Dom',
}

const norm = (s: string) =>
  s
    .toLowerCase()
    .replace(/ç/g, 'c')
    .replace(/[áàâã]/g, 'a')
    .replace(/[éê]/g, 'e')
    .replace(/í/g, 'i')
    .replace(/[óôõ]/g, 'o')
    .replace(/ú/g, 'u')
    .slice(0, 7)

interface Dia {
  key: string
  abrev: string
  maxPct: number
  horaPico: string
}

interface AcadPico {
  nome: string
  picoDia: string
  picoHora: string
  picoPct: number
  semana: Dia[]
}

function extrair(c: CompetidorJSON): AcadPico | null {
  const hp = c.horarios_pico
  if (!hp || typeof hp !== 'object' || Object.keys(hp).length === 0) return null

  const diasMap = new Map<string, Dia>()
  let gMaxPct = -1
  let gDia = ''
  let gHora = ''
  for (const [diaRaw, horas] of Object.entries(hp)) {
    if (!horas || typeof horas !== 'object') continue
    const nk = norm(diaRaw)
    let maxPct = 0
    let horaPico = ''
    for (const [h, pct] of Object.entries(horas as Record<string, number>)) {
      const v = Number(pct) || 0
      if (v > maxPct) {
        maxPct = v
        horaPico = h
      }
    }
    diasMap.set(nk, { key: nk, abrev: ABREV[nk] ?? diaRaw.slice(0, 3), maxPct, horaPico })
    if (maxPct > gMaxPct) {
      gMaxPct = maxPct
      gDia = nk
      gHora = horaPico
    }
  }
  if (diasMap.size === 0) return null

  const semana = ORDEM.filter((d) => diasMap.has(d)).map((d) => diasMap.get(d)!)
  // dias fora da ordem conhecida (spelling diferente) entram no fim
  for (const [k, v] of diasMap) if (!ORDEM.includes(k)) semana.push(v)

  return {
    nome: c.nome,
    picoDia: ABREV[gDia] ?? gDia,
    picoHora: gHora,
    picoPct: Math.max(0, gMaxPct),
    semana,
  }
}

function chartVar(pct: number): string {
  const bin = Math.min(5, Math.max(1, Math.ceil((pct / 100) * 5)))
  return `var(--chart-${bin})`
}

export interface PicoLotacaoVizProps {
  competidores: CompetidorJSON[] | undefined
  className?: string
}

export function PicoLotacaoViz({ competidores, className }: PicoLotacaoVizProps) {
  if (!competidores || competidores.length === 0) return null
  const acads = competidores.map(extrair).filter((a): a is AcadPico => a != null)
  if (acads.length === 0) return null

  // Janela de pico dominante do mercado (moda de dia+hora).
  const janela = new Map<string, number>()
  for (const a of acads) {
    const k = `${a.picoDia} ${a.picoHora}h`
    janela.set(k, (janela.get(k) ?? 0) + 1)
  }
  const [janelaTop, janelaCount] = Array.from(janela.entries()).sort((a, b) => b[1] - a[1])[0] ?? [
    '',
    0,
  ]

  return (
    <div className={cn('space-y-3', className)}>
      {janelaTop && (
        <div className="flex items-start gap-2.5 rounded-xl border border-accent/40 bg-accent/5 p-4">
          <Flame size={16} className="mt-0.5 shrink-0 text-accent" />
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-accent">
              Janela de pico do mercado
            </p>
            <p className="text-sm leading-relaxed text-foreground/90">
              <strong>{janelaTop}</strong> concentra a lotação em {janelaCount} de {acads.length}{' '}
              academias. Horários fora dessa janela têm menor disputa por espaço — oportunidade de
              posicionamento.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {acads.map((a, i) => (
          <div key={`${a.nome}-${i}`} className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
            <div className="flex items-start justify-between gap-2">
              <p className="line-clamp-2 text-sm font-semibold leading-tight" title={a.nome}>
                {a.nome}
              </p>
              <span
                className="inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 font-mono text-xs font-semibold"
                style={{
                  color: chartVar(a.picoPct),
                  background: `color-mix(in oklch, ${chartVar(a.picoPct)} 16%, transparent)`,
                }}
              >
                <Flame size={11} /> {a.picoDia} {a.picoHora}h
              </span>
            </div>

            {/* Barras semanais — forma de movimento da semana */}
            <div className="flex items-end gap-1.5">
              {a.semana.map((d) => (
                <div key={d.key} className="flex flex-1 flex-col items-center gap-1">
                  <div
                    className="w-full rounded-sm"
                    style={{
                      height: `${Math.max(6, (d.maxPct / 100) * 40)}px`,
                      background: chartVar(d.maxPct),
                    }}
                    title={`${d.abrev}: ${d.maxPct}% às ${d.horaPico}h`}
                  />
                  <span className="text-[9px] text-muted-foreground">{d.abrev}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
