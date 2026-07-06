/**
 * DemografiaBairroCard — demografia do bairro em mini-cards (fontes reais por dimensão).
 *
 * Renda: CKAN municipal (IDH-Renda → renda per capita Atlas). População/ocupação: IBGE
 * Censo 2022 por setor censitário. Bairro deixa de herdar o município — cada número tem
 * fonte. (Censo 2022 não tem renda por setor → renda só do CKAN.)
 */
import { Banknote, Home, TrendingUp, Users, UsersRound } from 'lucide-react'

import type { DemografiaBairroJSON } from '@/hooks/useRelatorioDetail'

function MiniCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: typeof Users
  label: string
  value: string
  sub?: string
}) {
  return (
    <div className="rounded-lg border bg-muted/40 px-3 py-2">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
        <Icon size={12} /> {label}
      </div>
      <div className="mt-0.5 text-lg font-semibold">{value}</div>
      {sub && <div className="text-[11px] text-muted-foreground leading-tight">{sub}</div>}
    </div>
  )
}

const _brl = (n: number) =>
  n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
const _int = (n: number) => n.toLocaleString('pt-BR')

export function DemografiaBairroCard({ block }: { block: DemografiaBairroJSON }) {
  if (!block) return null
  const temRenda = block.renda_media != null
  const temPop = block.populacao != null
  if (!temRenda && !temPop) {
    return (
      <p className="text-sm text-muted-foreground">
        Sem demografia de bairro disponível (CKAN/Censo não cobriram este bairro) — análise
        usa o nível município.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {temRenda && (
          <MiniCard
            icon={Banknote}
            label="renda per capita"
            value={_brl(block.renda_media as number)}
            sub={
              block.idh_renda != null
                ? `ref. ${block.renda_data_referencia ?? '—'} · IDH-Renda (Atlas/CKAN)`
                : `proxy: rend. do responsável ÷ moradores/dom. · IBGE Censo ${block.renda_data_referencia ?? '2022'}`
            }
          />
        )}
        {block.idh_renda != null && (
          <MiniCard
            icon={TrendingUp}
            label="IDH-Renda"
            value={(block.idh_renda as number).toFixed(3)}
            sub={block.ranking_idh ? `ranking ${block.ranking_idh}` : undefined}
          />
        )}
        {temPop && (
          <MiniCard
            icon={Users}
            label="população (bairro)"
            value={_int(block.populacao as number)}
            sub={block.censo_n_setores ? `${block.censo_n_setores} setores · raio do centróide · IBGE 2022` : undefined}
          />
        )}
        {block.media_moradores != null && (
          <MiniCard
            icon={Home}
            label="moradores/domicílio"
            value={(block.media_moradores as number).toFixed(2)}
            sub={block.domicilios != null ? `${_int(block.domicilios as number)} domicílios` : undefined}
          />
        )}
        {block.perfil_sexo_publico?.total != null &&
          block.perfil_sexo_publico.pct_mulheres != null &&
          block.perfil_sexo_publico.pct_homens != null && (
            <MiniCard
              icon={UsersRound}
              label={`público ${block.perfil_sexo_publico.faixa_idade ?? '25-40'} (sexo)`}
              value={`${Math.round(block.perfil_sexo_publico.pct_mulheres)}% ♀ / ${Math.round(block.perfil_sexo_publico.pct_homens)}% ♂`}
              sub={`gancho mkt · ${block.perfil_sexo_publico.granularidade === 'municipio' ? 'município' : 'bairro'} · Censo 2022`}
            />
          )}
      </div>
      {(() => {
        const segs = block.perfil_idade_sexo_bairro?.segmentos
        if (!segs) return null
        const labels = ['15-24', '25-39', '40-59', '60+'] as const
        const nomes: Record<string, string> = {
          '15-24': 'Jovem', '25-39': 'Core', '40-59': 'Maduro', '60+': 'Silver',
        }
        const rows = labels
          .map((l) => ({ l, s: segs[l] }))
          .filter((r) => r.s?.total != null && (r.s.total as number) > 0)
        if (rows.length === 0) return null
        const maxTotal = Math.max(...rows.map((r) => r.s!.total as number))
        const dominante = rows.reduce((a, b) => ((b.s!.total as number) > (a.s!.total as number) ? b : a))
        const pctM = dominante.s!.pct_mulheres ?? 50
        const tendencia = pctM >= 55 ? 'majoritariamente feminino' : pctM <= 45 ? 'majoritariamente masculino' : 'equilibrado'
        return (
          <div className="rounded-lg border bg-muted/40 px-3 py-2">
            <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
              <UsersRound size={12} /> público por idade × sexo (bairro real)
            </div>
            <div className="mt-1.5 space-y-1">
              {rows.map(({ l, s }) => {
                const total = s!.total as number
                const pm = Math.round(s!.pct_mulheres ?? 0)
                const ph = Math.round(s!.pct_homens ?? 0)
                return (
                  <div key={l} className="flex items-center gap-2 text-xs">
                    <span className="w-24 shrink-0 font-mono text-muted-foreground">
                      {l} <span className="text-[10px]">{nomes[l]}</span>
                    </span>
                    <div className="relative h-3.5 flex-1 overflow-hidden rounded bg-muted">
                      <div className="h-full bg-primary/25" style={{ width: `${(total / maxTotal) * 100}%` }} />
                    </div>
                    <span className="w-16 shrink-0 text-right font-semibold tabular-nums">{_int(total)}</span>
                    <span className="w-16 shrink-0 text-right text-muted-foreground tabular-nums">
                      {pm}♀/{ph}♂
                    </span>
                  </div>
                )
              })}
            </div>
            <div className="mt-1.5 text-[11px]">
              Público predominante: <span className="font-semibold">{dominante.l} ({nomes[dominante.l]})</span> ·
              perfil <span className="font-semibold">{tendencia}</span>.
            </div>
            <div className="mt-0.5 text-[10px] text-muted-foreground leading-tight">
              IBGE Censo 2022 por setor ({block.perfil_idade_sexo_bairro?.n_setores ?? '—'} setores agregados em torno
              do centróide até cobrir a população do bairro — base distinta do card de população) — idade real do
              bairro, não herdada do município.
            </div>
          </div>
        )
      })()}
      <p className="text-[11px] text-muted-foreground">
        Renda: {block.renda_fonte ?? 'CKAN municipal (IDH-Renda → Atlas)'}. População/ocupação:{' '}
        {block.populacao_fonte ?? 'IBGE Censo 2022 por setor'}. Cada dimensão com fonte real do
        bairro (não herdada do município).
      </p>
    </div>
  )
}
