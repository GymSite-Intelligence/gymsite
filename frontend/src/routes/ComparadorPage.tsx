/**
 * ComparadorPage — comparador side-by-side de 2 relatórios.
 *
 * Acessada via /comparar?a=rpt_X&b=rpt_Y. IDs vêm dos search params
 * (não state interno) pra permitir bookmark/share do link.
 *
 * Estratégia visual:
 * - Header: identificação A vs B com badges de veredito
 * - 5 seções de métricas (Veredito, Scores, Top Candidato, Financeiro,
 *   Competitivo) em tabelas com diff Δ
 * - Footer: link de volta + CTA pra trocar relatórios
 */
import { useNavigate, useSearch } from '@tanstack/react-router'
import { ArrowLeft, ChevronRight } from 'lucide-react'
import { useComparacao, formatBRL } from '@/hooks/useComparacao'
import { VeredictoBadge } from '@/components/domain/VeredictoBadge'
import { MetricaDiff } from '@/components/domain/MetricaDiff'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

export function ComparadorPage() {
  const navigate = useNavigate()
  const { a, b } = useSearch({ strict: false }) as { a?: string; b?: string }
  const { relatorioA, relatorioB, isLoading, error, invalido, motivoInvalido } =
    useComparacao(a, b)

  // Estado vazio: sem IDs
  if (invalido) {
    return (
      <div className="container max-w-3xl py-12">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold tracking-tight">
            Comparador de Relatórios
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Compare 2 análises de viabilidade lado a lado: scores, custos,
            payback, vereditos e dores dominantes.
          </p>
        </header>
        <div className="rounded-lg border border-dashed border-border p-8 text-center space-y-3">
          <p className="text-sm">{motivoInvalido}</p>
          <Button
            variant="outline"
            onClick={() =>
              navigate({
                to: '/relatorios',
                search: {
                  cidade: undefined,
                  veredito: undefined,
                  since: undefined,
                },
              })
            }
          >
            Ir pra listagem
          </Button>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="container max-w-5xl py-8 space-y-6">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="container max-w-3xl py-12">
        <p className="text-veredito-reprovado">
          Erro ao carregar relatórios: {error.message}
        </p>
      </div>
    )
  }

  if (!relatorioA || !relatorioB) {
    return (
      <div className="container max-w-3xl py-12">
        <p className="text-muted-foreground">Relatórios não encontrados.</p>
      </div>
    )
  }

  const outA = relatorioA.output_consolidado
  const outB = relatorioB.output_consolidado
  const inpA = relatorioA.input_canonico
  const inpB = relatorioB.input_canonico

  // Extrai cenário do modelo recomendado (pra comparar financeiro coerente).
  // Quando os 2 relatórios recomendam modelos diferentes, mostra ambos.
  const cenarioA = pegaCenarioRecomendado(outA)
  const cenarioB = pegaCenarioRecomendado(outB)

  const dorTopA = outA.dores_dominantes?.[0]?.dor ?? '—'
  const dorTopB = outB.dores_dominantes?.[0]?.dor ?? '—'

  const bairroAltA = outA.bairros_alternativos?.[0]?.bairro ?? '—'
  const bairroAltB = outB.bairros_alternativos?.[0]?.bairro ?? '—'

  return (
    <div className="container max-w-5xl py-8 space-y-6">
      {/* Header */}
      <header className="space-y-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <button
            onClick={() => window.history.back()}
            className="inline-flex items-center gap-1 hover:text-foreground"
          >
            <ArrowLeft size={12} /> voltar
          </button>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Comparador de Relatórios
        </h1>
        <p className="text-sm text-muted-foreground">
          Decisão entre 2 candidatos — analise diferenças críticas antes de
          escolher o ponto comercial.
        </p>
      </header>

      {/* Identificação dos relatórios */}
      <div className="grid grid-cols-2 gap-4">
        <CartaoIdentificacao
          rotulo="Relatório A"
          cidade={inpA.cidade}
          bairro={inpA.bairro}
          veredito={outA.veredito}
          data={relatorioA.data_execucao}
          id={relatorioA.id}
          onAbrir={() =>
            navigate({
              to: '/relatorios/$relatorioId',
              params: { relatorioId: relatorioA.id },
            })
          }
        />
        <CartaoIdentificacao
          rotulo="Relatório B"
          cidade={inpB.cidade}
          bairro={inpB.bairro}
          veredito={outB.veredito}
          data={relatorioB.data_execucao}
          id={relatorioB.id}
          onAbrir={() =>
            navigate({
              to: '/relatorios/$relatorioId',
              params: { relatorioId: relatorioB.id },
            })
          }
        />
      </div>

      {/* Bloco 1: Scores */}
      <SecaoComparativa titulo="Scores Regionais (0-10)">
        <MetricaDiff
          label="Score Bairro (3 dim regionais)"
          valorA={outA.score_bairro}
          valorB={outB.score_bairro}
          direcaoMelhor="up"
        />
        <MetricaDiff
          label="Score Top 1 Candidato (4 dim)"
          contexto="Base do veredito"
          valorA={outA.score_top1_candidato}
          valorB={outB.score_top1_candidato}
          direcaoMelhor="up"
        />
        <MetricaDiff
          label="Demográfico"
          valorA={outA.scores_regionais?.demografico}
          valorB={outB.scores_regionais?.demografico}
          direcaoMelhor="up"
        />
        <MetricaDiff
          label="Competitivo"
          contexto="Maior = menos saturação"
          valorA={
            outA.scores_regionais?.competitivo ??
            outA.scores_regionais?.concorrencia
          }
          valorB={
            outB.scores_regionais?.competitivo ??
            outB.scores_regionais?.concorrencia
          }
          direcaoMelhor="up"
        />
        <MetricaDiff
          label="Viabilidade financeira"
          valorA={outA.scores_regionais?.viabilidade}
          valorB={outB.scores_regionais?.viabilidade}
          direcaoMelhor="up"
        />
      </SecaoComparativa>

      {/* Bloco 2: Top 1 Candidato */}
      <SecaoComparativa titulo="Top 1 Candidato">
        <MetricaDiff
          label="Nome"
          valorA={null}
          valorB={null}
          valorAFormatado={outA.top_3_candidatos?.[0]?.nome ?? '—'}
          valorBFormatado={outB.top_3_candidatos?.[0]?.nome ?? '—'}
          categorical
        />
        <MetricaDiff
          label="Score GeoScout"
          valorA={outA.top_3_candidatos?.[0]?.score_geoscout}
          valorB={outB.top_3_candidatos?.[0]?.score_geoscout}
          direcaoMelhor="up"
        />
        <MetricaDiff
          label="Score Ancoragem"
          valorA={outA.top_3_candidatos?.[0]?.score_ancoragem}
          valorB={outB.top_3_candidatos?.[0]?.score_ancoragem}
          direcaoMelhor="up"
        />
        <MetricaDiff
          label="Área estimada"
          valorA={outA.top_3_candidatos?.[0]?.area_estimada_m2}
          valorB={outB.top_3_candidatos?.[0]?.area_estimada_m2}
          valorAFormatado={
            outA.top_3_candidatos?.[0]?.area_estimada_m2
              ? `${outA.top_3_candidatos[0].area_estimada_m2} m²`
              : '—'
          }
          valorBFormatado={
            outB.top_3_candidatos?.[0]?.area_estimada_m2
              ? `${outB.top_3_candidatos[0].area_estimada_m2} m²`
              : '—'
          }
          direcaoMelhor="neutro"
        />
      </SecaoComparativa>

      {/* Bloco 3: Financeiro (modelo recomendado de cada um) */}
      <SecaoComparativa
        titulo="Viabilidade Financeira (modelo recomendado de cada)"
        descricao={
          outA.modelo_recomendado !== outB.modelo_recomendado
            ? `⚠ Modelos recomendados diferentes — A=${outA.modelo_recomendado}, B=${outB.modelo_recomendado}`
            : undefined
        }
      >
        <MetricaDiff
          label="Modelo recomendado"
          valorA={null}
          valorB={null}
          valorAFormatado={outA.modelo_recomendado ?? '—'}
          valorBFormatado={outB.modelo_recomendado ?? '—'}
          categorical
        />
        <MetricaDiff
          label="Receita mensal"
          valorA={cenarioA?.receita_mensal}
          valorB={cenarioB?.receita_mensal}
          valorAFormatado={formatBRL(cenarioA?.receita_mensal)}
          valorBFormatado={formatBRL(cenarioB?.receita_mensal)}
          direcaoMelhor="up"
        />
        <MetricaDiff
          label="Aluguel mensal"
          valorA={outA.aluguel_mensal}
          valorB={outB.aluguel_mensal}
          valorAFormatado={formatBRL(outA.aluguel_mensal)}
          valorBFormatado={formatBRL(outB.aluguel_mensal)}
          direcaoMelhor="down"
        />
        <MetricaDiff
          label="Aluguel R$/m² (mediana)"
          contexto="Pesquisa Search Grounding"
          valorA={outA.aluguel_mediana_m2_observado}
          valorB={outB.aluguel_mediana_m2_observado}
          valorAFormatado={
            outA.aluguel_mediana_m2_observado != null
              ? `R$ ${outA.aluguel_mediana_m2_observado.toFixed(2)}/m²`
              : '—'
          }
          valorBFormatado={
            outB.aluguel_mediana_m2_observado != null
              ? `R$ ${outB.aluguel_mediana_m2_observado.toFixed(2)}/m²`
              : '—'
          }
          direcaoMelhor="down"
        />
        <MetricaDiff
          label="Lucro mensal estimado"
          valorA={cenarioA?.lucro_mensal_estimado}
          valorB={cenarioB?.lucro_mensal_estimado}
          valorAFormatado={formatBRL(cenarioA?.lucro_mensal_estimado)}
          valorBFormatado={formatBRL(cenarioB?.lucro_mensal_estimado)}
          direcaoMelhor="up"
        />
        <MetricaDiff
          label="Margem"
          valorA={cenarioA?.margem_percentual}
          valorB={cenarioB?.margem_percentual}
          valorAFormatado={
            cenarioA?.margem_percentual != null
              ? `${cenarioA.margem_percentual.toFixed(1)}%`
              : '—'
          }
          valorBFormatado={
            cenarioB?.margem_percentual != null
              ? `${cenarioB.margem_percentual.toFixed(1)}%`
              : '—'
          }
          direcaoMelhor="up"
        />
        <MetricaDiff
          label="Payback (meses)"
          valorA={cenarioA?.payback_meses}
          valorB={cenarioB?.payback_meses}
          direcaoMelhor="down"
        />
        <MetricaDiff
          label="Investimento total"
          valorA={cenarioA?.investimento_total ?? cenarioA?.capex_estimado}
          valorB={cenarioB?.investimento_total ?? cenarioB?.capex_estimado}
          valorAFormatado={formatBRL(
            cenarioA?.investimento_total ?? cenarioA?.capex_estimado,
          )}
          valorBFormatado={formatBRL(
            cenarioB?.investimento_total ?? cenarioB?.capex_estimado,
          )}
          direcaoMelhor="down"
        />
        <MetricaDiff
          label="TIR anual"
          valorA={cenarioA?.tir_anual_pct}
          valorB={cenarioB?.tir_anual_pct}
          valorAFormatado={
            cenarioA?.tir_anual_pct != null
              ? `${cenarioA.tir_anual_pct.toFixed(1)}%`
              : '—'
          }
          valorBFormatado={
            cenarioB?.tir_anual_pct != null
              ? `${cenarioB.tir_anual_pct.toFixed(1)}%`
              : '—'
          }
          direcaoMelhor="up"
        />
        <MetricaDiff
          label="VPL 5 anos"
          valorA={cenarioA?.vpl_5_anos}
          valorB={cenarioB?.vpl_5_anos}
          valorAFormatado={formatBRL(cenarioA?.vpl_5_anos)}
          valorBFormatado={formatBRL(cenarioB?.vpl_5_anos)}
          direcaoMelhor="up"
        />
      </SecaoComparativa>

      {/* Bloco 4: Competitivo */}
      <SecaoComparativa titulo="Competitivo">
        <MetricaDiff
          label="Concorrentes analisados"
          valorA={outA.total_concorrentes_analisados}
          valorB={outB.total_concorrentes_analisados}
          direcaoMelhor="down"
        />
        <MetricaDiff
          label="Nível de saturação"
          valorA={null}
          valorB={null}
          valorAFormatado={outA.nivel_saturacao ?? '—'}
          valorBFormatado={outB.nivel_saturacao ?? '—'}
          categorical
        />
        <MetricaDiff
          label="Rating médio concorrentes"
          valorA={outA.rating_medio_concorrentes}
          valorB={outB.rating_medio_concorrentes}
          valorAFormatado={
            outA.rating_medio_concorrentes != null
              ? `★ ${outA.rating_medio_concorrentes.toFixed(1)}`
              : '—'
          }
          valorBFormatado={
            outB.rating_medio_concorrentes != null
              ? `★ ${outB.rating_medio_concorrentes.toFixed(1)}`
              : '—'
          }
          direcaoMelhor="neutro"
        />
        <MetricaDiff
          label="Dor dominante #1"
          valorA={null}
          valorB={null}
          valorAFormatado={dorTopA}
          valorBFormatado={dorTopB}
          categorical
        />
      </SecaoComparativa>

      {/* Bloco 5: Bairros Alternativos */}
      <SecaoComparativa titulo="Bairros Alternativos sugeridos">
        <MetricaDiff
          label="Top alternativo #1"
          valorA={null}
          valorB={null}
          valorAFormatado={bairroAltA}
          valorBFormatado={bairroAltB}
          categorical
        />
        <MetricaDiff
          label="Total de alternativas"
          valorA={outA.bairros_alternativos?.length ?? 0}
          valorB={outB.bairros_alternativos?.length ?? 0}
          direcaoMelhor="neutro"
        />
      </SecaoComparativa>

      <footer className="flex items-center justify-between pt-4 border-t border-border">
        <Button
          variant="outline"
          onClick={() =>
            navigate({
              to: '/relatorios',
              search: {
                cidade: undefined,
                veredito: undefined,
                since: undefined,
              },
            })
          }
        >
          Escolher outros relatórios
        </Button>
        <p className="text-xs text-muted-foreground font-mono">
          {relatorioA.id} ↔ {relatorioB.id}
        </p>
      </footer>
    </div>
  )
}

// ── Subcomponentes ────────────────────────────────────────────────────

function CartaoIdentificacao({
  rotulo,
  cidade,
  bairro,
  veredito,
  data,
  id,
  onAbrir,
}: {
  rotulo: string
  cidade: string
  bairro: string
  veredito: 'APROVADO' | 'APROVADO COM RESSALVAS' | 'INVESTIGAR MAIS' | 'REPROVADO'
  data: string
  id: string
  onAbrir: () => void
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
          {rotulo}
        </span>
        <VeredictoBadge veredito={veredito} />
      </div>
      <h2 className="font-semibold text-sm">
        {bairro} <span className="text-muted-foreground">·</span> {cidade}
      </h2>
      <p className="text-[10px] text-muted-foreground font-mono">
        {new Date(data).toLocaleDateString('pt-BR')} · {id}
      </p>
      <button
        onClick={onAbrir}
        className="flex items-center gap-1 text-xs text-primary hover:underline"
      >
        Abrir relatório completo <ChevronRight size={12} />
      </button>
    </div>
  )
}

function SecaoComparativa({
  titulo,
  descricao,
  children,
}: {
  titulo: string
  descricao?: string
  children: React.ReactNode
}) {
  return (
    <section className="rounded-lg border border-border overflow-hidden">
      <header className="px-4 py-2.5 bg-muted/30 border-b border-border">
        <h3 className="text-sm font-semibold">{titulo}</h3>
        {descricao && (
          <p className="text-xs text-muted-foreground mt-0.5">{descricao}</p>
        )}
      </header>
      <table className="w-full">
        <thead className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
          <tr className="border-b border-border">
            <th className="px-3 py-2 text-left w-2/5">Métrica</th>
            <th className="px-3 py-2 text-left">A</th>
            <th className="px-3 py-2 text-left">B</th>
            <th className="px-3 py-2 text-left w-20">Δ</th>
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </section>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────

/**
 * Pega o cenário correspondente ao `modelo_recomendado` do relatório.
 * Se modelo é "Low Cost" → cenários.low. Se "Mid Market" → cenários.mid, etc.
 *
 * Quando o modelo é null ou cenário não existe, devolve undefined — a UI
 * mostra "—" nas células.
 */
function pegaCenarioRecomendado(out: {
  modelo_recomendado: string | null
  viabilidade_3_cenarios?: Record<string, unknown>
}) {
  const modelo = (out.modelo_recomendado ?? '').toLowerCase()
  const cenarios = out.viabilidade_3_cenarios ?? {}
  if (modelo.includes('low')) return cenarios.low as Record<string, number> | undefined
  if (modelo.includes('mid')) return cenarios.mid as Record<string, number> | undefined
  if (modelo.includes('premium')) return cenarios.premium as Record<string, number> | undefined
  // Fallback: pega o primeiro disponível
  const primeiroKey = Object.keys(cenarios)[0]
  return primeiroKey
    ? (cenarios[primeiroKey] as Record<string, number> | undefined)
    : undefined
}
