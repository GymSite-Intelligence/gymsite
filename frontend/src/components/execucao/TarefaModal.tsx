/**
 * TarefaModal — ficha da etapa em modal centralizado.
 *
 * Mesmo padrão visual da ficha de oportunidade da Prospecção: título no topo,
 * badges, grid de campos com rótulos discretos, seções divididas, seletor de
 * situação e ações no rodapé. Substitui o painel lateral (decisão 12/06).
 * Concluir etapa de valor alto (> R$ 10.000 previstos) pede o gasto real
 * (CST-003); nas demais o campo é opcional.
 */
import { useEffect, useState } from 'react'
import { AlertTriangle, Sparkles } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { formatBRL } from '@/lib/format'
import { CATEGORIA_LABEL } from '@/components/execucao/PlaybookKanban'
import type { Tarefa } from '@/hooks/usePlaybook'

const STATUS_LABEL: Record<Tarefa['status'], string> = {
  A_FAZER: 'A fazer',
  EM_ANDAMENTO: 'Em andamento',
  BLOQUEADA: 'Bloqueada',
  CONCLUIDA: 'Concluída',
  CANCELADA: 'Cancelada',
}

const CUSTO_OBRIGATORIO_ACIMA_CENTAVOS = 1_000_000 // R$ 10.000 (CST-003)

function formatData(iso: string | null): string {
  if (!iso) return '—'
  return new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString('pt-BR')
}

function Campo({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="mb-0.5 text-xs text-muted-foreground">{rotulo}</p>
      <div className="text-sm font-medium">{children}</div>
    </div>
  )
}

export function TarefaModal({
  tarefa,
  aberto,
  onFechar,
  onMudarStatus,
  onMarcarChecklist,
  salvando,
}: {
  tarefa: Tarefa | null
  aberto: boolean
  onFechar: () => void
  onMudarStatus: (status: Tarefa['status'], custoRealCentavos: number | null) => void
  onMarcarChecklist: (itemId: string, concluido: boolean) => void
  salvando: boolean
}) {
  const [novoStatus, setNovoStatus] = useState<Tarefa['status'] | ''>('')
  const [gastoReais, setGastoReais] = useState('')

  useEffect(() => {
    setNovoStatus('')
    setGastoReais('')
  }, [tarefa?.id])

  if (!tarefa) return null

  const statusEfetivo = (novoStatus || tarefa.status) as Tarefa['status']
  const concluindo = statusEfetivo === 'CONCLUIDA' && tarefa.status !== 'CONCLUIDA'
  const custoAlto = (tarefa.custo_planejado ?? 0) > CUSTO_OBRIGATORIO_ACIMA_CENTAVOS
  const precisaGasto = concluindo && custoAlto && !gastoReais.trim()
  const mudou = Boolean(novoStatus) && novoStatus !== tarefa.status

  function salvar() {
    if (!mudou) return
    let centavos: number | null = null
    const txt = gastoReais.replace(/\./g, '').replace(',', '.').trim()
    if (txt) {
      const v = Number(txt)
      if (!Number.isNaN(v) && v >= 0) centavos = Math.round(v * 100)
    }
    onMudarStatus(novoStatus as Tarefa['status'], centavos)
  }

  return (
    <Dialog open={aberto} onOpenChange={(v) => !v && onFechar()}>
      <DialogContent className="max-h-[88vh] gap-0 overflow-y-auto p-0 sm:max-w-xl">
        <DialogHeader className="space-y-3 px-6 pt-6 text-center sm:text-center">
          <DialogTitle className="text-lg leading-snug">{tarefa.titulo}</DialogTitle>
          <div className="flex flex-wrap items-center justify-center gap-1.5">
            <Badge variant="secondary" className="rounded-full px-3 font-normal">
              {CATEGORIA_LABEL[tarefa.categoria] ?? tarefa.categoria}
            </Badge>
            <Badge variant="secondary" className="rounded-full bg-blue-50 px-3 font-normal text-blue-700">
              {STATUS_LABEL[tarefa.status]}
            </Badge>
            {tarefa.sugerida_pela_ia && (
              <Badge variant="secondary" className="gap-1 rounded-full bg-violet-50 px-3 font-normal text-violet-700">
                <Sparkles className="h-3 w-3" /> Sugestão da análise
              </Badge>
            )}
            {tarefa.esta_atrasada && (
              <Badge variant="secondary" className="gap-1 rounded-full bg-red-50 px-3 font-normal text-red-700">
                <AlertTriangle className="h-3 w-3" /> {tarefa.dias_atraso} dia(s) de atraso
              </Badge>
            )}
          </div>
        </DialogHeader>

        <div className="space-y-5 px-6 py-5">
          <div className="grid grid-cols-2 gap-x-6 gap-y-4">
            <Campo rotulo="Prazo">{formatData(tarefa.data_prevista_conclusao)}</Campo>
            <Campo rotulo="Responsável">{tarefa.responsavel_nome ?? '—'}</Campo>
            <Campo rotulo="Previsto">
              {tarefa.custo_planejado != null ? formatBRL(tarefa.custo_planejado / 100) : '—'}
            </Campo>
            <Campo rotulo="Gasto até agora">
              {tarefa.custo_real != null ? formatBRL(tarefa.custo_real / 100) : '—'}
            </Campo>
          </div>

          {tarefa.descricao && (
            <div className="border-t pt-4">
              <p className="mb-0.5 text-xs text-muted-foreground">O que fazer</p>
              <p className="whitespace-pre-line text-sm leading-relaxed">{tarefa.descricao}</p>
            </div>
          )}

          {tarefa.origem_relatorio_insight && (
            <div className="border-t pt-4">
              <p className="mb-0.5 text-xs text-muted-foreground">Da sua análise</p>
              <p className="text-sm leading-relaxed text-blue-900">{tarefa.origem_relatorio_insight}</p>
            </div>
          )}

          {tarefa.checklist.length > 0 && (
            <div className="border-t pt-4">
              <p className="mb-2 text-xs text-muted-foreground">Passo a passo</p>
              <div className="flex flex-col gap-2">
                {tarefa.checklist.map((item) => (
                  <label key={item.id} className="flex cursor-pointer items-start gap-2 text-sm">
                    <Checkbox
                      checked={item.concluido}
                      onCheckedChange={(v) => onMarcarChecklist(item.id, v === true)}
                      className="mt-0.5"
                    />
                    <span className={item.concluido ? 'text-muted-foreground line-through' : ''}>
                      {item.descricao}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-3 border-t pt-4">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Situação</Label>
              <Select value={statusEfetivo} onValueChange={(v) => setNovoStatus(v as Tarefa['status'])}>
                <SelectTrigger className="h-11 w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(STATUS_LABEL) as Tarefa['status'][]).map((s) => (
                    <SelectItem key={s} value={s}>
                      {STATUS_LABEL[s]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {concluindo && (
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">
                  Quanto você gastou de fato? {custoAlto ? '' : '(se souber)'}
                </Label>
                <Input
                  inputMode="decimal"
                  placeholder="R$ 0,00"
                  value={gastoReais}
                  onChange={(e) => setGastoReais(e.target.value)}
                  className="h-11"
                />
                {precisaGasto && (
                  <p className="text-xs text-amber-700">
                    Esta etapa tem valor alto — informe o gasto real para manter seu orçamento confiável.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        <DialogFooter className="gap-2 border-t px-6 py-4 sm:justify-end">
          <Button variant="outline" onClick={onFechar} className="h-10">
            Fechar
          </Button>
          <Button
            className="h-10"
            disabled={!mudou || precisaGasto || salvando}
            onClick={salvar}
          >
            {salvando ? 'Salvando…' : 'Salvar mudança'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
