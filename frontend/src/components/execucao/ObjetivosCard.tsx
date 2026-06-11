/**
 * ObjetivosCard — metas do plano (OKRs) no topo da página de execução.
 *
 * Cada meta vem do cenário recomendado da análise (alunos de equilíbrio,
 * investimento, projeção de matrículas). O dono atualiza o "atual" de cada
 * resultado-chave direto no campo; progresso é barra atual/alvo.
 * KRs financeiros em REAIS (colunas DECIMAL legadas da tabela okrs).
 */
import { useState } from 'react'
import { Pencil, Plus, Target, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { notify } from '@/lib/notify'
import { MetaFormDialog } from '@/components/execucao/MetaFormDialog'
import {
  useAtualizarOkr,
  useExcluirOkr,
  useGerarOkrs,
  type Okr,
} from '@/hooks/usePlaybook'

function KrLinha({
  descricao,
  target,
  atual,
  auto,
  onSalvar,
}: {
  descricao: string
  target: number
  atual: number
  /** Espelho do plano (etapas concluídas, gasto total) — calculado, não digitado. */
  auto?: boolean
  onSalvar: (valor: number) => void
}) {
  const [texto, setTexto] = useState<string | null>(null)
  const pct = Math.min(100, Math.round((atual / target) * 100))
  const maximo = /máximo/i.test(descricao)

  function commit() {
    if (texto == null) return
    const v = Number(texto.replace(/\./g, '').replace(',', '.'))
    setTexto(null)
    if (!Number.isNaN(v) && v >= 0 && v !== atual) onSalvar(v)
  }

  return (
    <div className="flex items-center gap-2">
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <p className="truncate text-xs text-muted-foreground">
            {descricao}
            {auto && <span className="ml-1 text-[10px]">· automático</span>}
          </p>
          <p className="shrink-0 text-xs font-medium">
            {atual.toLocaleString('pt-BR')} / {target.toLocaleString('pt-BR')}
          </p>
        </div>
        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
          <div
            className={`h-full rounded-full transition-all ${maximo ? 'bg-amber-500' : 'bg-primary'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
      {!auto && (
        <Input
          inputMode="decimal"
          className="h-7 w-20 shrink-0 text-right text-xs"
          value={texto ?? String(atual)}
          onChange={(e) => setTexto(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
          aria-label={`Atualizar: ${descricao}`}
        />
      )}
    </div>
  )
}

export function ObjetivosCard({ playbookId, okrs }: { playbookId: string; okrs: Okr[] }) {
  const gerar = useGerarOkrs(playbookId)
  const atualizar = useAtualizarOkr(playbookId)
  const excluir = useExcluirOkr(playbookId)
  const [formAberto, setFormAberto] = useState(false)
  const [okrEditando, setOkrEditando] = useState<Okr | null>(null)

  function abrirForm(okr: Okr | null) {
    setOkrEditando(okr)
    setFormAberto(true)
  }

  const dialog = (
    <MetaFormDialog
      aberto={formAberto}
      onFechar={() => setFormAberto(false)}
      playbookId={playbookId}
      okr={okrEditando}
    />
  )

  if (okrs.length === 0) {
    return (
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          className="h-10 w-fit"
          disabled={gerar.isPending}
          onClick={() =>
            gerar.mutate(undefined, {
              onSuccess: (r) =>
                r.okrs_criados > 0
                  ? notify.success(`${r.okrs_criados} meta(s) criada(s) a partir da sua análise.`)
                  : notify.success('Este plano já tinha metas.'),
              onError: (e: Error) => notify.error(e.message),
            })
          }
        >
          <Target className="mr-1.5 h-4 w-4" />
          {gerar.isPending ? 'Criando metas…' : 'Criar metas da análise'}
        </Button>
        <Button variant="outline" className="h-10 w-fit" onClick={() => abrirForm(null)}>
          <Plus className="mr-1.5 h-4 w-4" /> Nova meta
        </Button>
        {dialog}
      </div>
    )
  }

  function salvar(okrId: string, kr: 1 | 2 | 3, valor: number) {
    atualizar.mutate(
      { okrId, [`kr${kr}_atual`]: valor },
      { onError: (e: Error) => notify.error(e.message) },
    )
  }

  function excluirMeta(okr: Okr) {
    if (!window.confirm(`Excluir a meta "${okr.objetivo}"?`)) return
    excluir.mutate(okr.id, { onError: (e: Error) => notify.error(e.message) })
  }

  return (
    <div>
      <h2 className="mb-2 flex items-center gap-1.5 text-sm font-semibold">
        <Target className="h-4 w-4 text-primary" />
        Metas da abertura
        <span className="font-normal text-muted-foreground">— vindas da sua análise</span>
        <Button
          variant="ghost"
          size="sm"
          className="ml-auto h-7 px-2 text-xs"
          onClick={() => abrirForm(null)}
        >
          <Plus className="mr-1 h-3.5 w-3.5" /> Nova meta
        </Button>
      </h2>
      <div className="grid gap-3 md:grid-cols-3">
        {okrs.map((okr) => (
        <div key={okr.id} className="group rounded-lg border bg-card px-4 py-3">
          <div className="flex items-start gap-1">
            <p className="min-w-0 flex-1 text-sm font-medium">{okr.objetivo}</p>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
              aria-label={`Editar meta ${okr.objetivo}`}
              onClick={() => abrirForm(okr)}
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-red-600 group-hover:opacity-100"
              aria-label={`Excluir meta ${okr.objetivo}`}
              onClick={() => excluirMeta(okr)}
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
          <div className="mt-2.5 flex flex-col gap-2.5">
            {okr.kr1_descricao && okr.kr1_target != null && okr.kr1_target > 0 && (
              <KrLinha
                descricao={okr.kr1_descricao}
                target={okr.kr1_target}
                atual={okr.kr1_atual ?? 0}
                auto={okr.kr1_auto}
                onSalvar={(v) => salvar(okr.id, 1, v)}
              />
            )}
            {okr.kr2_descricao && okr.kr2_target != null && okr.kr2_target > 0 && (
              <KrLinha
                descricao={okr.kr2_descricao}
                target={okr.kr2_target}
                atual={okr.kr2_atual ?? 0}
                auto={okr.kr2_auto}
                onSalvar={(v) => salvar(okr.id, 2, v)}
              />
            )}
            {okr.kr3_descricao && okr.kr3_target != null && okr.kr3_target > 0 && (
              <KrLinha
                descricao={okr.kr3_descricao}
                target={okr.kr3_target}
                atual={okr.kr3_atual ?? 0}
                auto={okr.kr3_auto}
                onSalvar={(v) => salvar(okr.id, 3, v)}
              />
            )}
          </div>
        </div>
        ))}
      </div>
      {dialog}
    </div>
  )
}
