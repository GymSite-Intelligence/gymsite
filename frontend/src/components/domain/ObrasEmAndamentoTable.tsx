/**
 * Obras fitness em andamento — Cadastro Nacional de Obras (RFB).
 */
import { HardHat } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ObrasCnoEmCursoJSON } from '@/hooks/useRelatorioDetail'

export interface ObrasEmAndamentoTableProps {
  block?: ObrasCnoEmCursoJSON | null
  className?: string
}

function formatData(iso: string | undefined | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return iso
  }
}

function formatArea(m2: number | undefined): string {
  if (m2 == null || Number.isNaN(m2)) return '—'
  return `${Math.round(m2).toLocaleString('pt-BR')} m²`
}

export function ObrasEmAndamentoTable({ block, className }: ObrasEmAndamentoTableProps) {
  if (!block || block.status === 'nao_configurado' || block.status === 'indisponivel') {
    return (
      <p className="text-xs text-muted-foreground">
        {block?.status === 'nao_configurado'
          ? 'Cadastro CNO não configurado no servidor (CNO_DATA_DIR).'
          : 'Obras em andamento indisponíveis para esta cidade.'}
      </p>
    )
  }
  if (block.status === 'erro') {
    return (
      <p className="text-xs text-veredito-reprovado">
        Erro ao carregar obras CNO: {block.motivo ?? 'desconhecido'}
      </p>
    )
  }

  const bench = block.benchmark_tempo_obra
  const filtroBairro = block.filtro_bairro
  const lista = block.obras ?? []
  if (lista.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        Nenhuma obra fitness em andamento encontrada no CNO para{' '}
        {block.cidade ?? 'o município'}.
      </p>
    )
  }

  return (
    <div className={cn('space-y-3', className)}>
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground flex items-center gap-1.5">
          <HardHat size={12} />
          Obras em andamento
        </h4>
        <span className="text-xs font-mono text-muted-foreground tabular-nums">
          {lista.length} listada(s)
          {filtroBairro?.bairro_filtro
            ? ` · filtro: ${filtroBairro.bairro_filtro}`
            : ` · ${block.total_obras_em_curso_municipio ?? block.total_obras_em_curso ?? lista.length} no município`}
          {block.cidade ? ` · ${block.cidade}` : ''}
          {block.uf ? ` (${block.uf})` : ''}
        </span>
      </header>

      {filtroBairro?.bairro_filtro && filtroBairro.total_apos_filtro_bairro === 0 && (
        <p className="text-[11px] text-muted-foreground">
          Nenhuma obra CNO em andamento no bairro{' '}
          <strong className="text-foreground">{filtroBairro.bairro_filtro}</strong>
          {filtroBairro.total_antes_filtro != null && filtroBairro.total_antes_filtro > 0
            ? ` (${filtroBairro.total_antes_filtro} no município).`
            : '.'}
        </p>
      )}

      {bench?.status === 'ok' && bench.metricas?.dias_por_m2_mediana != null && (
        <p className="text-[11px] text-muted-foreground leading-snug">
          Tempo de obra (CNO encerradas, {bench.amostra_valida ?? 0} amostras): mediana{' '}
          <span className="font-mono tabular-nums">
            {bench.metricas.dias_por_m2_mediana.toLocaleString('pt-BR')}
          </span>{' '}
          dias/m²
          {bench.metricas.duracao_dias_mediana != null && (
            <>
              {' '}
              · duração mediana{' '}
              <span className="font-mono tabular-nums">
                {bench.metricas.duracao_dias_mediana}
              </span>{' '}
              dias
            </>
          )}
        </p>
      )}

      <div className="rounded-md border border-border overflow-x-auto">
        <table className="w-full text-xs min-w-[640px]">
          <thead>
            <tr className="border-b border-border bg-muted/40 text-left">
              <th className="px-3 py-2 font-mono text-[10px]">Academia / obra</th>
              <th className="px-3 py-2 font-mono text-[10px]">Área</th>
              <th className="px-3 py-2 font-mono text-[10px]">Bairro</th>
              <th className="px-3 py-2 font-mono text-[10px]">Início</th>
              <th className="px-3 py-2 font-mono text-[10px]">Previsão encerr. (est.)</th>
            </tr>
          </thead>
          <tbody>
            {lista.map((obra) => (
              <tr
                key={obra.cno ?? `${obra.nome_obra}-${obra.bairro}`}
                className="border-b border-border last:border-0 hover:bg-muted/30"
              >
                <td className="px-3 py-2 font-medium max-w-[280px]">
                  {obra.nome_obra?.trim() || '—'}
                </td>
                <td className="px-3 py-2 whitespace-nowrap tabular-nums font-semibold">
                  {formatArea(obra.area_m2)}
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-muted-foreground">
                  {obra.bairro?.trim() || '—'}
                </td>
                <td className="px-3 py-2 whitespace-nowrap tabular-nums">
                  {formatData(obra.data_inicio ?? undefined)}
                </td>
                <td className="px-3 py-2 whitespace-nowrap tabular-nums text-muted-foreground">
                  {obra.previsao_encerramento_estimada
                    ? formatData(obra.previsao_encerramento_estimada)
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {block.fonte && (
        <p className="text-[10px] font-mono text-muted-foreground">Fonte: {block.fonte}</p>
      )}
      {block.nota_metodologica && (
        <p className="text-[10px] text-muted-foreground leading-snug">{block.nota_metodologica}</p>
      )}
    </div>
  )
}
