/**
 * CoberturaRedesA0Card — confronta redes do Deep Research (A0) vs busca real (A3a).
 *
 * Aparece quando `output_consolidado.cobertura_redes_a0` está populado (schema v1.4).
 * Sinaliza redes que o DR listou mas não têm unidade no raio do bairro alvo —
 * caso clássico de generalização regional virando "concorrência local" inflada.
 *
 * Estados visuais:
 * - tem_redes_fantasma=true → card de aviso (amarelo) com lista de redes não validadas
 * - tem_redes_fantasma=false → card neutro confirmando 100% das redes validadas
 * - redes_solicitadas vazio → componente retorna null (DR não listou nada)
 */
import { CheckCircle2, AlertTriangle, Search } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { CoberturaRedesA0JSON } from '@/hooks/useRelatorioDetail'

export interface CoberturaRedesA0CardProps {
  cobertura: CoberturaRedesA0JSON | undefined
  bairroAlvo?: string
  className?: string
}

export function CoberturaRedesA0Card({
  cobertura,
  bairroAlvo,
  className,
}: CoberturaRedesA0CardProps) {
  if (!cobertura || !cobertura.redes_solicitadas?.length) return null

  const { redes_solicitadas, redes_cobertas, redes_nao_encontradas, tem_redes_fantasma } =
    cobertura
  const totalSolicitadas = redes_solicitadas.length
  const totalCobertas = redes_cobertas.length
  const cobertura_pct = totalSolicitadas
    ? Math.round((totalCobertas / totalSolicitadas) * 100)
    : 0

  return (
    <div
      className={cn(
        'rounded-lg border p-5 space-y-4',
        tem_redes_fantasma
          ? 'border-veredito-ressalvas/40 bg-veredito-ressalvas/5'
          : 'border-border bg-card',
        className,
      )}
    >
      <header className="flex items-center justify-between gap-3">
        <h3 className="text-xs uppercase tracking-wider font-mono font-medium flex items-center gap-2">
          <Search size={14} className="text-muted-foreground" />
          Cobertura Deep Research vs busca real
        </h3>
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          {totalCobertas}/{totalSolicitadas} validadas ({cobertura_pct}%)
        </span>
      </header>

      <p className="text-xs text-muted-foreground leading-snug">
        Confronta as redes que o Deep Research (A0) listou como principais
        concorrentes contra o que a busca georreferenciada (A3a, raio 5 km
        {bairroAlvo ? ` de ${bairroAlvo}` : ' do bairro alvo'}) validou.
      </p>

      {/* Redes confirmadas */}
      {redes_cobertas.length > 0 && (
        <section className="space-y-1.5">
          <h4 className="text-[11px] uppercase tracking-wider font-mono text-muted-foreground flex items-center gap-1.5">
            <CheckCircle2 size={12} className="text-veredito-aprovado" />
            Confirmadas no raio
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {redes_cobertas.map((rede) => (
              <span
                key={rede}
                className="rounded-md border border-veredito-aprovado/30 bg-veredito-aprovado/5 px-2 py-1 text-xs font-medium"
              >
                {rede}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Redes fantasma */}
      {redes_nao_encontradas.length > 0 && (
        <section className="space-y-2">
          <h4 className="text-[11px] uppercase tracking-wider font-mono text-veredito-ressalvas flex items-center gap-1.5">
            <AlertTriangle size={12} />
            Sem unidade local validada
          </h4>
          <ul className="space-y-1.5">
            {redes_nao_encontradas.map((rede) => (
              <li
                key={rede}
                className="text-xs leading-snug flex items-start gap-2"
              >
                <span aria-hidden className="mt-1 shrink-0 text-veredito-ressalvas">
                  ·
                </span>
                <span>
                  <strong>{rede}</strong>{' '}
                  <span className="text-muted-foreground">
                    — citada pelo DR mas sem unidade no raio. Provável
                    generalização regional; não considerar no posicionamento.
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Excluídos por filtro semântico: removido da UI de produção (debug interno,
          desacoplado da informação real). O dado segue em cobertura.concorrentes_excluidos
          pra QA/telemetria, mas não polui o relatório do usuário. */}
    </div>
  )
}
