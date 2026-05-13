/**
 * KitEquipamentosTable — exibe o kit de equipamentos detalhado por modelo+tamanho.
 *
 * Substitui a linha genérica "Equipamentos: R$ X" do CenarioFinanceiroTable
 * por um detalhamento item-por-item (esteiras, flexora, extensora, crossover,
 * etc) com fornecedor de referência e preço de catálogo.
 *
 * Visual:
 * - Header com modelo de operação + área de referência
 * - Resumo: total bruto + faixa de custo real estimado (após desconto volume)
 * - Tabela agrupada por categoria (cardio, musc_superior, musc_inferior, etc)
 * - Footer com fontes
 */
import { useMemo, useState } from 'react'
import { ChevronRight, Package } from 'lucide-react'
import {
  type KitEquipamentos,
  type CategoriaEquipamento,
  CATEGORIA_LABEL,
  totalKit,
  totaisPorCategoria,
  faixaCustoReal,
} from '@/data/kits/types'
import { cn } from '@/lib/utils'

export interface KitEquipamentosTableProps {
  kit: KitEquipamentos
  className?: string
}

function formatBRL(v: number): string {
  return v.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  })
}

const ORDEM_CATEGORIAS: CategoriaEquipamento[] = [
  'cardio',
  'spinning',
  'musc_superior',
  'musc_inferior',
  'gluteo',
  'core',
  'livre',
  'pesos',
  'funcional',
  'pilates',
  'crossfit',
  'acessorios',
  'estetica',
]

export function KitEquipamentosTable({ kit, className }: KitEquipamentosTableProps) {
  const total = useMemo(() => totalKit(kit), [kit])
  const [faixaMin, faixaMax] = useMemo(() => faixaCustoReal(kit), [kit])
  const totaisCat = useMemo(() => totaisPorCategoria(kit), [kit])

  const totaisCatOrdenados = useMemo(() => {
    return [...totaisCat].sort(
      (a, b) =>
        ORDEM_CATEGORIAS.indexOf(a.categoria) -
        ORDEM_CATEGORIAS.indexOf(b.categoria),
    )
  }, [totaisCat])

  // Todas as categorias começam fechadas — user clica pra abrir o que interessa.
  const [abertas, setAbertas] = useState<Set<CategoriaEquipamento>>(
    () => new Set(),
  )

  function toggle(cat: CategoriaEquipamento) {
    setAbertas((prev) => {
      const next = new Set(prev)
      if (next.has(cat)) next.delete(cat)
      else next.add(cat)
      return next
    })
  }

  return (
    <div className={cn('rounded-lg border border-border overflow-hidden bg-card', className)}>
      <header className="px-5 py-3 border-b border-border bg-muted/20 flex items-start justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Package size={16} className="text-muted-foreground" />
          <div>
            <h3 className="text-sm font-semibold">Kit de Equipamentos detalhado</h3>
            <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
              {kit.modelo_operacao} · referência {kit.area_referencia_m2.toLocaleString('pt-BR')} m²
            </p>
          </div>
        </div>
      </header>

      {/* Resumo */}
      <div className="px-5 py-3 border-b border-border bg-card grid grid-cols-2 lg:grid-cols-3 gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
            Total catálogo (lista)
          </p>
          <p className="text-lg font-semibold tabular-nums">{formatBRL(total)}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
            Estimado real (com desconto)
          </p>
          <p className="text-lg font-semibold tabular-nums text-status-good">
            {formatBRL(faixaMin)} – {formatBRL(faixaMax)}
          </p>
          <p className="text-[10px] text-muted-foreground font-mono">
            Desconto de volume{' '}
            {Math.round((kit.desconto_volume_pct?.[0] ?? 0.15) * 100)}–
            {Math.round((kit.desconto_volume_pct?.[1] ?? 0.35) * 100)}%
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
            Itens
          </p>
          <p className="text-lg font-semibold tabular-nums">
            {kit.itens.length}{' '}
            <span className="text-xs font-mono text-muted-foreground">
              modelos
            </span>
          </p>
          <p className="text-[10px] text-muted-foreground font-mono">
            {kit.itens.reduce((a, b) => a + b.qtd, 0)} unidades totais
          </p>
        </div>
      </div>

      {/* Accordion por categoria (UI Lote 2) */}
      <div className="divide-y divide-border">
        {totaisCatOrdenados.map((cat) => {
          const aberta = abertas.has(cat.categoria)
          const itensCat = kit.itens.filter((i) => i.cat === cat.categoria)
          const pctTotal = total > 0 ? (cat.total / total) * 100 : 0
          return (
            <section key={cat.categoria}>
              <button
                onClick={() => toggle(cat.categoria)}
                aria-expanded={aberta}
                className="w-full px-5 py-3 flex items-center justify-between gap-3 hover:bg-muted/30 transition-colors group"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <ChevronRight
                    size={14}
                    className={cn(
                      'text-muted-foreground shrink-0 transition-transform duration-200',
                      aberta && 'rotate-90',
                    )}
                  />
                  <span className="text-sm font-medium truncate">
                    {CATEGORIA_LABEL[cat.categoria]}
                  </span>
                  <span className="text-[10px] text-muted-foreground font-mono shrink-0">
                    {cat.modelos_count} modelo{cat.modelos_count === 1 ? '' : 's'}{' '}
                    · {cat.itens_count} un.
                  </span>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {/* Mini progress bar — % deste cat no total */}
                  <div className="hidden sm:flex items-center gap-1.5">
                    <div className="w-20 h-1.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-primary/60 transition-all"
                        style={{ width: `${Math.min(100, pctTotal)}%` }}
                      />
                    </div>
                    <span className="text-[10px] font-mono text-muted-foreground tabular-nums w-9 text-right">
                      {pctTotal.toFixed(0)}%
                    </span>
                  </div>
                  <span className="text-sm font-semibold tabular-nums">
                    {formatBRL(cat.total)}
                  </span>
                </div>
              </button>
              {aberta && (
                <table className="w-full bg-muted/10">
                  <thead className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
                    <tr className="border-y border-border">
                      <th className="px-5 py-1.5 text-left">Equipamento</th>
                      <th className="px-3 py-1.5 text-left w-32">Referência</th>
                      <th className="px-3 py-1.5 text-left w-24">Fornecedor</th>
                      <th className="px-3 py-1.5 text-right w-14">Qtd</th>
                      <th className="px-3 py-1.5 text-right w-28">Un.</th>
                      <th className="px-3 py-1.5 text-right w-28">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {itensCat.map((item, idx) => (
                      <tr
                        key={`${item.cat}-${idx}`}
                        className="border-b border-border/50 last:border-b-0"
                      >
                        <td className="px-5 py-2 text-sm">
                          {item.nome}
                          {item.nota && (
                            <div className="text-[10px] text-muted-foreground italic">
                              {item.nota}
                            </div>
                          )}
                        </td>
                        <td className="px-3 py-2 text-[11px] text-muted-foreground font-mono">
                          {item.ref ?? '—'}
                        </td>
                        <td className="px-3 py-2 text-[11px] font-mono">
                          {item.fornecedor ?? '—'}
                        </td>
                        <td className="px-3 py-2 text-sm text-right tabular-nums">
                          {item.qtd}
                        </td>
                        <td className="px-3 py-2 text-sm text-right tabular-nums">
                          {formatBRL(item.preco_un)}
                        </td>
                        <td className="px-3 py-2 text-sm text-right tabular-nums font-medium">
                          {formatBRL(item.qtd * item.preco_un)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          )
        })}
      </div>

      {/* Footer */}
      <footer className="px-5 py-2.5 bg-muted/20 border-t border-border text-[10px] font-mono text-muted-foreground">
        Fontes: {kit.fontes.join(' · ')} · Preços de lista 2024 — descontos de
        volume não aplicados nos subtotais.
      </footer>
    </div>
  )
}
