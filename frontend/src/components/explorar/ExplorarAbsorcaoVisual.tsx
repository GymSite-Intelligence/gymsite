import type { AbsorcaoCarimboJSON, AbsorcaoMargemFrescaJSON } from '@/hooks/useRelatorioDetail'
import { cn } from '@/lib/utils'
import { explorarBarPercents, explorarIntPt } from './explorarAbsorcaoBars'

const ROTULO: Record<string, { label: string; cls: string }> = {
  fresco: { label: 'Aluno novo disponível', cls: 'explorar-badge-fresco' },
  misto: { label: 'Crescimento misto', cls: 'explorar-badge-misto' },
  roubo: { label: 'Disputa com o parque', cls: 'explorar-badge-roubo' },
}

function carimboText(raw: unknown): string {
  if (raw == null) return ''
  if (typeof raw === 'string') return raw
  if (typeof raw === 'object') {
    const o = raw as AbsorcaoCarimboJSON
    return [o.valor, o.base, o.fonte, o.janela]
      .filter((x) => x != null && x !== '')
      .map(String)
      .join(' · ')
  }
  return String(raw)
}

function BlocoBarra({
  n,
  titulo,
  valor,
  pct,
  fill,
  carimbo,
}: {
  n: number
  titulo: string
  valor: string
  pct: number
  fill: 'lime' | 'muted' | 'amber' | 'good' | 'bad'
  carimbo?: string
}) {
  return (
    <div className="min-w-0 rounded-lg border border-border bg-secondary/40 p-2.5">
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <p className="min-w-0 text-[11px] font-semibold leading-snug text-foreground">
          {n}. {titulo}
        </p>
        <p className="shrink-0 text-sm font-semibold tabular-nums text-primary">{valor}</p>
      </div>
      <div className="explorar-bar-track">
        <div
          className={cn('explorar-bar-fill', `explorar-bar-${fill}`)}
          style={{ width: `${pct}%`, minWidth: pct > 0 ? 6 : 0 }}
        />
      </div>
      {carimbo ? (
        <p className="mt-1 text-[10px] leading-snug text-muted-foreground">{carimbo}</p>
      ) : null}
    </div>
  )
}

export function ExplorarAbsorcaoVisual({ absorcao }: { absorcao: AbsorcaoMargemFrescaJSON }) {
  const rotulo = String(absorcao.rotulo || '')
  const badge = ROTULO[rotulo] ?? { label: rotulo || 'Leitura', cls: 'explorar-badge-misto' }
  const teto = Number(absorcao.teto_unidade) || 0
  const parque = Number(absorcao.capacidade_parque_estimada) || 0
  const pool = Number(absorcao.pool_primario ?? absorcao.pool_demografico) || 0
  const secundario = Number(absorcao.pool_secundario) || 0
  const margem = absorcao.margem_fresca
  const [pTeto, pParque, pPool, pSec] = explorarBarPercents([teto, parque, pool, secundario])
  const pMargem =
    margem == null || teto <= 0
      ? 0
      : Math.min(100, Math.round((Math.abs(Number(margem)) / Math.max(teto, 1)) * 100))
  const folga = margem != null && Number(margem) >= 0
  const car = absorcao.carimbos ?? {}

  return (
    <div className="min-w-0 space-y-2">
      <span className={cn('explorar-badge', badge.cls)}>{badge.label}</span>
      <BlocoBarra
        n={1}
        titulo="Capacidade da sua unidade"
        valor={`${explorarIntPt(teto)} alunos`}
        pct={pTeto}
        fill="lime"
        carimbo={carimboText(car.teto_unidade)}
      />
      <BlocoBarra
        n={2}
        titulo="Capacidade das academias no recorte"
        valor={`${explorarIntPt(parque)} alunos`}
        pct={pParque}
        fill="muted"
        carimbo={carimboText(car.capacidade_parque_estimada)}
      />
      <BlocoBarra
        n={3}
        titulo="Potencial no público escolhido"
        valor={`${explorarIntPt(pool)} alunos`}
        pct={pPool}
        fill="amber"
        carimbo={carimboText(car.pool_demografico)}
      />
      <BlocoBarra
        n={4}
        titulo="Potencial nas outras idades"
        valor={`${explorarIntPt(secundario)} alunos`}
        pct={pSec}
        fill="muted"
      />
      <div className="min-w-0 rounded-lg border border-border bg-secondary/40 p-2.5">
        <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[11px] font-semibold text-foreground">5. Conclusão</p>
          <span className={cn('explorar-badge', badge.cls)}>{badge.label}</span>
        </div>
        {margem != null && (
          <>
            <div className="mb-1 flex items-baseline justify-between gap-2">
              <p className="text-[11px] text-muted-foreground">
                {folga ? 'Folga para aluno novo' : 'Déficit — disputa com o parque'}
              </p>
              <p className="shrink-0 text-sm font-semibold tabular-nums text-primary">
                {explorarIntPt(Math.abs(Number(margem)))} alunos
              </p>
            </div>
            <div className="explorar-bar-track">
              <div
                className={cn('explorar-bar-fill', folga ? 'explorar-bar-good' : 'explorar-bar-bad')}
                style={{ width: `${pMargem}%`, minWidth: pMargem > 0 ? 6 : 0 }}
              />
            </div>
            {carimboText(car.margem_fresca) ? (
              <p className="mt-1 text-[10px] leading-snug text-muted-foreground">
                {carimboText(car.margem_fresca)}
              </p>
            ) : null}
          </>
        )}
      </div>
    </div>
  )
}
