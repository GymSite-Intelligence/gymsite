/**
 * MetricaDiff — linha de comparação A vs B com indicador Δ.
 *
 * Usada na tabela do comparador. Para cada métrica:
 * - 1ª coluna: rótulo
 * - 2ª coluna: valor relatório A
 * - 3ª coluna: valor relatório B
 * - 4ª coluna: delta (Δ%) ou texto curto, com cor semântica
 *
 * `delta_melhor` indica se a direção UP é positiva (score, lucro, margem) ou
 * negativa (custo, payback, saturação). Define a cor verde/vermelho.
 */
import { ArrowDown, ArrowUp, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { calcularDelta, formatPct } from '@/hooks/useComparacao'

export type DirecaoMelhor = 'up' | 'down' | 'neutro'

export interface MetricaDiffProps {
  label: string
  /** Sub-label opcional (categoria, contexto). */
  contexto?: string
  /** Valor numérico bruto pra cálculo de Δ. Use `valorAFormatado` se quiser controlar a exibição. */
  valorA: number | null | undefined
  valorB: number | null | undefined
  /** Texto exibido na coluna A (override do número bruto). */
  valorAFormatado?: string
  valorBFormatado?: string
  /** Define cor do Δ. "up" = ↑ é bom (verde). "down" = ↓ é bom (verde). "neutro" = sem cor. */
  direcaoMelhor?: DirecaoMelhor
  /** Quando a métrica é categórica (string), passa só os formatados — não calcula Δ. */
  categorical?: boolean
}

export function MetricaDiff({
  label,
  contexto,
  valorA,
  valorB,
  valorAFormatado,
  valorBFormatado,
  direcaoMelhor = 'up',
  categorical = false,
}: MetricaDiffProps) {
  const delta = categorical ? null : calcularDelta(valorA, valorB)

  // Determina cor do Δ baseado em direcao + direcaoMelhor
  let corDelta = 'text-muted-foreground'
  let Icon = Minus
  if (delta && delta.direcao !== 'eq') {
    Icon = delta.direcao === 'up' ? ArrowUp : ArrowDown
    if (direcaoMelhor === 'neutro') {
      corDelta = 'text-muted-foreground'
    } else {
      const ehMelhor =
        (delta.direcao === 'up' && direcaoMelhor === 'up') ||
        (delta.direcao === 'down' && direcaoMelhor === 'down')
      corDelta = ehMelhor ? 'text-veredito-aprovado' : 'text-veredito-reprovado'
    }
  }

  const exibirA =
    valorAFormatado ??
    (valorA == null
      ? '—'
      : Number.isFinite(valorA)
        ? String(valorA)
        : '—')
  const exibirB =
    valorBFormatado ??
    (valorB == null
      ? '—'
      : Number.isFinite(valorB)
        ? String(valorB)
        : '—')

  // Categorical (texto): mostra "= igual" ou "≠ diferente"
  const textoCategoricoDiff = categorical
    ? exibirA === exibirB
      ? '= igual'
      : '≠ diferente'
    : null

  return (
    <tr className="border-b border-border last:border-b-0">
      <td className="px-3 py-2.5 align-top">
        <div className="text-xs text-muted-foreground">{label}</div>
        {contexto && (
          <div className="text-[10px] text-muted-foreground/70 font-mono mt-0.5">
            {contexto}
          </div>
        )}
      </td>
      <td className="px-3 py-2.5 text-sm font-medium tabular-nums">
        {exibirA}
      </td>
      <td className="px-3 py-2.5 text-sm font-medium tabular-nums">
        {exibirB}
      </td>
      <td className="px-3 py-2.5">
        {delta && delta.direcao !== 'eq' && delta.pct != null && (
          <span
            className={cn(
              'inline-flex items-center gap-1 text-xs font-mono tabular-nums',
              corDelta,
            )}
          >
            <Icon size={11} />
            {formatPct(Math.abs(delta.pct))}
          </span>
        )}
        {delta && delta.direcao === 'eq' && (
          <span className="text-xs text-muted-foreground font-mono">=</span>
        )}
        {textoCategoricoDiff && (
          <span
            className={cn(
              'text-xs font-mono',
              textoCategoricoDiff === '= igual'
                ? 'text-muted-foreground'
                : 'text-veredito-investigar',
            )}
          >
            {textoCategoricoDiff}
          </span>
        )}
      </td>
    </tr>
  )
}
