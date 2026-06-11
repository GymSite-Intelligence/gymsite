/**
 * ObjetivosCard — metas do plano (OKRs) no topo da página de execução.
 *
 * Cada meta vem do cenário recomendado da análise (alunos de equilíbrio,
 * investimento, projeção de matrículas). O dono atualiza o "atual" de cada
 * resultado-chave direto no campo; progresso é barra atual/alvo.
 * KRs financeiros em REAIS (colunas DECIMAL legadas da tabela okrs).
 */
import { useState } from 'react'
import { Target } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { notify } from '@/lib/notify'
import { useAtualizarOkr, useGerarOkrs, type Okr } from '@/hooks/usePlaybook'

function KrLinha({
  descricao,
  target,
  atual,
  onSalvar,
}: {
  descricao: string
  target: number
  atual: number
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
          <p className="truncate text-xs text-muted-foreground">{descricao}</p>
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
      <Input
        inputMode="decimal"
        className="h-7 w-20 shrink-0 text-right text-xs"
        value={texto ?? String(atual)}
        onChange={(e) => setTexto(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
        aria-label={`Atualizar: ${descricao}`}
      />
    </div>
  )
}

export function ObjetivosCard({ playbookId, okrs }: { playbookId: string; okrs: Okr[] }) {
  const gerar = useGerarOkrs(playbookId)
  const atualizar = useAtualizarOkr(playbookId)

  if (okrs.length === 0) {
    return (
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
    )
  }

  function salvar(okrId: string, kr: 1 | 2 | 3, valor: number) {
    atualizar.mutate(
      { okrId, [`kr${kr}_atual`]: valor },
      { onError: (e: Error) => notify.error(e.message) },
    )
  }

  return (
    <div className="grid gap-3 md:grid-cols-3">
      {okrs.map((okr) => (
        <div key={okr.id} className="rounded-lg border bg-card px-4 py-3">
          <p className="flex items-center gap-1.5 text-sm font-medium">
            <Target className="h-4 w-4 shrink-0 text-primary" />
            {okr.objetivo}
          </p>
          <div className="mt-2.5 flex flex-col gap-2.5">
            {okr.kr1_descricao && okr.kr1_target != null && okr.kr1_target > 0 && (
              <KrLinha
                descricao={okr.kr1_descricao}
                target={okr.kr1_target}
                atual={okr.kr1_atual ?? 0}
                onSalvar={(v) => salvar(okr.id, 1, v)}
              />
            )}
            {okr.kr2_descricao && okr.kr2_target != null && okr.kr2_target > 0 && (
              <KrLinha
                descricao={okr.kr2_descricao}
                target={okr.kr2_target}
                atual={okr.kr2_atual ?? 0}
                onSalvar={(v) => salvar(okr.id, 2, v)}
              />
            )}
            {okr.kr3_descricao && okr.kr3_target != null && okr.kr3_target > 0 && (
              <KrLinha
                descricao={okr.kr3_descricao}
                target={okr.kr3_target}
                atual={okr.kr3_atual ?? 0}
                onSalvar={(v) => salvar(okr.id, 3, v)}
              />
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
