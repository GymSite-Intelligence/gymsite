/**
 * PlaybookCustos — Real vs Previsto por área do plano.
 *
 * Derivado 100% das etapas (centavos → reais só no display). Diferença
 * verde = abaixo do previsto, vermelha = estourou. Etapas canceladas
 * ficam de fora.
 */
import { useMemo } from 'react'
import { Badge } from '@/components/ui/badge'
import { formatBRL } from '@/lib/format'
import type { Tarefa } from '@/hooks/usePlaybook'
import { CATEGORIA_COR, CATEGORIA_LABEL } from '@/components/execucao/PlaybookKanban'

export function PlaybookCustos({ tarefas }: { tarefas: Tarefa[] }) {
  const linhas = useMemo(() => {
    const porCategoria = new Map<string, { previsto: number; real: number; etapas: number }>()
    for (const t of tarefas) {
      if (t.status === 'CANCELADA') continue
      const atual = porCategoria.get(t.categoria) ?? { previsto: 0, real: 0, etapas: 0 }
      atual.previsto += t.custo_planejado ?? 0
      atual.real += t.custo_real ?? 0
      atual.etapas += 1
      porCategoria.set(t.categoria, atual)
    }
    return Array.from(porCategoria.entries())
      .map(([categoria, v]) => ({ categoria, ...v, diferenca: v.real - v.previsto }))
      .sort((a, b) => b.previsto - a.previsto)
  }, [tarefas])

  const total = useMemo(
    () =>
      linhas.reduce(
        (acc, l) => ({
          previsto: acc.previsto + l.previsto,
          real: acc.real + l.real,
        }),
        { previsto: 0, real: 0 },
      ),
    [linhas],
  )

  if (linhas.length === 0) {
    return <p className="py-10 text-center text-sm text-muted-foreground">Nenhuma etapa para somar.</p>
  }

  return (
    <div className="max-w-3xl pb-6">
      <div className="overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
              <th className="px-4 py-2.5 font-medium">Área</th>
              <th className="px-4 py-2.5 text-right font-medium">Previsto</th>
              <th className="px-4 py-2.5 text-right font-medium">Gasto</th>
              <th className="px-4 py-2.5 text-right font-medium">Diferença</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.categoria} className="border-b last:border-b-0">
                <td className="px-4 py-2.5">
                  <Badge
                    variant="outline"
                    className={`text-[10px] ${CATEGORIA_COR[l.categoria] ?? CATEGORIA_COR.OUTRO}`}
                  >
                    {CATEGORIA_LABEL[l.categoria] ?? l.categoria}
                  </Badge>
                  <span className="ml-2 text-xs text-muted-foreground">{l.etapas} etapa(s)</span>
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums">
                  {l.previsto ? formatBRL(l.previsto / 100) : '—'}
                </td>
                <td className="px-4 py-2.5 text-right font-medium tabular-nums">
                  {l.real ? formatBRL(l.real / 100) : '—'}
                </td>
                <td
                  className={`px-4 py-2.5 text-right tabular-nums ${
                    l.real === 0
                      ? 'text-muted-foreground'
                      : l.diferenca > 0
                        ? 'font-medium text-red-600'
                        : 'font-medium text-emerald-600'
                  }`}
                >
                  {l.real === 0
                    ? '—'
                    : `${l.diferenca > 0 ? '+' : ''}${formatBRL(l.diferenca / 100)}`}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t bg-muted/30 font-medium">
              <td className="px-4 py-2.5">Total</td>
              <td className="px-4 py-2.5 text-right tabular-nums">{formatBRL(total.previsto / 100)}</td>
              <td className="px-4 py-2.5 text-right tabular-nums">{formatBRL(total.real / 100)}</td>
              <td
                className={`px-4 py-2.5 text-right tabular-nums ${
                  total.real - total.previsto > 0 ? 'text-red-600' : 'text-emerald-600'
                }`}
              >
                {total.real === 0
                  ? '—'
                  : `${total.real - total.previsto > 0 ? '+' : ''}${formatBRL((total.real - total.previsto) / 100)}`}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        Gasto entra pelo campo “Gasto até agora” da ficha de cada etapa — em qualquer situação,
        não só na conclusão.
      </p>
    </div>
  )
}
