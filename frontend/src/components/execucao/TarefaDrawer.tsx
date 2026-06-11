/**
 * TarefaDrawer — painel lateral com o detalhe de uma etapa do plano.
 *
 * É também o caminho MOBILE para mudar a situação da etapa (sem arrastar).
 * Concluir etapa de valor alto (> R$ 10.000 previstos) pede o gasto real —
 * regra CST-003 da política de custos; etapas menores o campo é opcional.
 */
import { useEffect, useState } from 'react'
import { AlertTriangle, Calendar, Sparkles, User } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
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

export function TarefaDrawer({
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

  function salvar() {
    if (!novoStatus || novoStatus === tarefa!.status) return
    let centavos: number | null = null
    const txt = gastoReais.replace(/\./g, '').replace(',', '.').trim()
    if (txt) {
      const v = Number(txt)
      if (!Number.isNaN(v) && v >= 0) centavos = Math.round(v * 100)
    }
    onMudarStatus(novoStatus as Tarefa['status'], centavos)
  }

  return (
    <Sheet open={aberto} onOpenChange={(v) => !v && onFechar()}>
      <SheetContent className="flex w-full flex-col gap-0 overflow-y-auto sm:max-w-md">
        <SheetHeader className="space-y-2 pb-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="outline" className="text-[10px]">
              {CATEGORIA_LABEL[tarefa.categoria] ?? tarefa.categoria}
            </Badge>
            {tarefa.sugerida_pela_ia && (
              <Badge variant="outline" className="gap-1 border-violet-200 bg-violet-50 text-[10px] text-violet-700">
                <Sparkles className="h-3 w-3" /> Sugestão da análise
              </Badge>
            )}
            {tarefa.esta_atrasada && (
              <Badge variant="outline" className="gap-1 border-red-200 bg-red-50 text-[10px] text-red-700">
                <AlertTriangle className="h-3 w-3" /> {tarefa.dias_atraso} dia(s) de atraso
              </Badge>
            )}
          </div>
          <SheetTitle className="text-left text-base leading-snug">{tarefa.titulo}</SheetTitle>
          {tarefa.descricao && (
            <SheetDescription className="text-left whitespace-pre-line">
              {tarefa.descricao}
            </SheetDescription>
          )}
        </SheetHeader>

        <div className="grid grid-cols-2 gap-3 border-y py-3 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Prazo</p>
            <p className="inline-flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" /> {formatData(tarefa.data_prevista_conclusao)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Responsável</p>
            <p className="inline-flex items-center gap-1 truncate">
              <User className="h-3.5 w-3.5" /> {tarefa.responsavel_nome ?? '—'}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Previsto</p>
            <p>{tarefa.custo_planejado != null ? formatBRL(tarefa.custo_planejado / 100) : '—'}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Gasto até agora</p>
            <p>{tarefa.custo_real != null ? formatBRL(tarefa.custo_real / 100) : '—'}</p>
          </div>
        </div>

        {tarefa.origem_relatorio_insight && (
          <div className="mt-3 rounded-lg border border-blue-100 bg-blue-50 p-3 text-xs text-blue-900">
            <span className="font-medium">Da sua análise: </span>
            {tarefa.origem_relatorio_insight}
          </div>
        )}

        {tarefa.checklist.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-sm font-medium">Passo a passo</p>
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

        <div className="mt-auto space-y-3 border-t pt-4">
          <div className="space-y-1.5">
            <Label>Situação</Label>
            <Select value={statusEfetivo} onValueChange={(v) => setNovoStatus(v as Tarefa['status'])}>
              <SelectTrigger className="h-12">
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
              <Label>
                Quanto você gastou de fato? {custoAlto ? '' : '(se souber)'}
              </Label>
              <Input
                inputMode="decimal"
                placeholder="R$ 0,00"
                value={gastoReais}
                onChange={(e) => setGastoReais(e.target.value)}
                className="h-12"
              />
              {precisaGasto && (
                <p className="text-xs text-amber-700">
                  Esta etapa tem valor alto — informe o gasto real para manter seu orçamento confiável.
                </p>
              )}
            </div>
          )}

          <Button
            className="h-12 w-full"
            disabled={!novoStatus || novoStatus === tarefa.status || precisaGasto || salvando}
            onClick={salvar}
          >
            {salvando ? 'Salvando…' : 'Salvar mudança'}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
