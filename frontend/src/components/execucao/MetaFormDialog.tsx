/**
 * MetaFormDialog — criar ou editar meta (OKR) do plano.
 *
 * Objetivo + até 3 resultados-chave (descrição + alvo numérico).
 * Valores financeiros em REAIS (colunas DECIMAL legadas da tabela okrs).
 */
import { useEffect, useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { notify } from '@/lib/notify'
import {
  useAtualizarOkr,
  useCriarOkr,
  type Okr,
} from '@/hooks/usePlaybook'

function numeroOuUndefined(txt: string): number | undefined {
  const limpo = txt.replace(/\./g, '').replace(',', '.').trim()
  if (!limpo) return undefined
  const v = Number(limpo)
  return Number.isNaN(v) || v < 0 ? undefined : v
}

export function MetaFormDialog({
  aberto,
  onFechar,
  playbookId,
  okr,
}: {
  aberto: boolean
  onFechar: () => void
  playbookId: string
  /** null = criar nova; preenchida = editar existente */
  okr: Okr | null
}) {
  const [objetivo, setObjetivo] = useState('')
  const [krs, setKrs] = useState<{ descricao: string; target: string }[]>([
    { descricao: '', target: '' },
    { descricao: '', target: '' },
    { descricao: '', target: '' },
  ])

  const criar = useCriarOkr(playbookId)
  const atualizar = useAtualizarOkr(playbookId)
  const salvando = criar.isPending || atualizar.isPending

  useEffect(() => {
    if (!aberto) return
    setObjetivo(okr?.objetivo ?? '')
    setKrs([
      {
        descricao: okr?.kr1_descricao ?? '',
        target: okr?.kr1_target != null ? String(okr.kr1_target).replace('.', ',') : '',
      },
      {
        descricao: okr?.kr2_descricao ?? '',
        target: okr?.kr2_target != null ? String(okr.kr2_target).replace('.', ',') : '',
      },
      {
        descricao: okr?.kr3_descricao ?? '',
        target: okr?.kr3_target != null ? String(okr.kr3_target).replace('.', ',') : '',
      },
    ])
  }, [aberto, okr?.id])

  function setKr(i: number, campo: 'descricao' | 'target', valor: string) {
    setKrs((prev) => prev.map((kr, j) => (j === i ? { ...kr, [campo]: valor } : kr)))
  }

  function salvar() {
    if (!objetivo.trim()) return
    const campos: Record<string, unknown> = { objetivo: objetivo.trim() }
    krs.forEach((kr, i) => {
      const n = i + 1
      const desc = kr.descricao.trim()
      const target = numeroOuUndefined(kr.target)
      if (desc && target != null) {
        campos[`kr${n}_descricao`] = desc
        campos[`kr${n}_target`] = target
      } else if (okr) {
        campos[`kr${n}_descricao`] = desc || null
        campos[`kr${n}_target`] = target ?? null
      }
    })
    const opts = {
      onSuccess: () => {
        notify.success(okr ? 'Meta atualizada.' : 'Meta criada.')
        onFechar()
      },
      onError: (e: Error) => notify.error(e.message),
    }
    if (okr) {
      atualizar.mutate({ okrId: okr.id, ...campos }, opts)
    } else {
      criar.mutate(campos as never, opts)
    }
  }

  return (
    <Dialog open={aberto} onOpenChange={(v) => !v && onFechar()}>
      <DialogContent className="gap-0 p-0 sm:max-w-md">
        <DialogHeader className="px-6 pt-6 text-center sm:text-center">
          <DialogTitle className="text-lg">{okr ? 'Editar meta' : 'Nova meta'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-3 px-6 py-5">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Objetivo</Label>
            <Input
              value={objetivo}
              onChange={(e) => setObjetivo(e.target.value)}
              placeholder="Ex.: Fechar o primeiro trimestre no azul"
              className="h-10"
            />
          </div>
          {krs.map((kr, i) => (
            <div key={i} className="grid grid-cols-[1fr_110px] gap-2">
              <div className="space-y-1.5">
                {i === 0 && (
                  <Label className="text-xs text-muted-foreground">Resultados-chave</Label>
                )}
                <Input
                  value={kr.descricao}
                  onChange={(e) => setKr(i, 'descricao', e.target.value)}
                  placeholder={`Resultado ${i + 1} (ex.: Alunos matriculados)`}
                  className="h-10"
                />
              </div>
              <div className="space-y-1.5">
                {i === 0 && <Label className="text-xs text-muted-foreground">Alvo</Label>}
                <Input
                  inputMode="decimal"
                  value={kr.target}
                  onChange={(e) => setKr(i, 'target', e.target.value)}
                  placeholder="0"
                  className="h-10"
                />
              </div>
            </div>
          ))}
        </div>

        <DialogFooter className="gap-2 border-t px-6 py-4 sm:justify-end">
          <Button variant="outline" onClick={onFechar} className="h-10">
            Cancelar
          </Button>
          <Button className="h-10" disabled={!objetivo.trim() || salvando} onClick={salvar}>
            {salvando ? 'Salvando…' : okr ? 'Salvar mudanças' : 'Criar meta'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
