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
            sub={`ref. ${block.renda_data_referencia ?? '—'} (Censo/IDH)`}
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
            sub={block.censo_n_setores ? `${block.censo_n_setores} setores censitários` : undefined}
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
      <p className="text-[11px] text-muted-foreground">
        Renda: {block.renda_fonte ?? 'CKAN municipal (IDH-Renda → Atlas)'}. População/ocupação:{' '}
        {block.populacao_fonte ?? 'IBGE Censo 2022 por setor'}. Cada dimensão com fonte real do
        bairro (não herdada do município).
      </p>
    </div>
  )
}
