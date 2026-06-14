/**
 * EtapaFormDialog — criar ou editar etapa do plano.
 *
 * O gerador sugere o plano inicial; aqui o dono assume: etapa nova do zero
 * ou ajuste do que a análise propôs. Custo digitado em reais, gravado em
 * centavos (regra de dinheiro).
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { notify } from '@/lib/notify'
import { CATEGORIA_LABEL } from '@/components/execucao/PlaybookKanban'
import {
  useCriarTarefa,
  useEditarTarefa,
  type NovaTarefa,
  type Pessoa,
  type Tarefa,
} from '@/hooks/usePlaybook'

function reaisParaCentavos(txt: string): number | null {
  const limpo = txt.replace(/\./g, '').replace(',', '.').trim()
  if (!limpo) return null
  const v = Number(limpo)
  if (Number.isNaN(v) || v < 0) return null
  return Math.round(v * 100)
}

export function EtapaFormDialog({
  aberto,
  onFechar,
  playbookId,
  tarefa,
  pessoas,
}: {
  aberto: boolean
  onFechar: () => void
  playbookId: string
  /** null = criar nova; preenchida = editar existente */
  tarefa: Tarefa | null
  pessoas: Pessoa[]
}) {
  const [titulo, setTitulo] = useState('')
  const [categoria, setCategoria] = useState('OUTRO')
  const [prazo, setPrazo] = useState('')
  const [custoReais, setCustoReais] = useState('')
  const [responsavel, setResponsavel] = useState('')
  const [pessoaId, setPessoaId] = useState<string>('')
  const [descricao, setDescricao] = useState('')
  const [criterio, setCriterio] = useState('')

  const criar = useCriarTarefa(playbookId)
  const editar = useEditarTarefa(playbookId)
  const salvando = criar.isPending || editar.isPending

  useEffect(() => {
    if (!aberto) return
    setTitulo(tarefa?.titulo ?? '')
    setCategoria(tarefa?.categoria ?? 'OUTRO')
    setPrazo(tarefa?.data_prevista_conclusao?.slice(0, 10) ?? '')
    setCustoReais(
      tarefa?.custo_planejado != null ? String(tarefa.custo_planejado / 100).replace('.', ',') : '',
    )
    setResponsavel(tarefa?.responsavel_nome ?? '')
    setPessoaId(tarefa?.responsavel_pessoa_id ?? '')
    setDescricao(tarefa?.descricao ?? '')
    setCriterio(tarefa?.criterio_verificacao ?? '')
  }, [aberto, tarefa?.id])

  function salvar() {
    if (!titulo.trim()) return
    const campos: NovaTarefa = {
      titulo: titulo.trim(),
      categoria,
      descricao: descricao.trim() || undefined,
      criterio_verificacao: criterio.trim() || undefined,
      custo_planejado: reaisParaCentavos(custoReais),
      data_prevista_conclusao: prazo || undefined,
      responsavel_pessoa_id: pessoaId || null,
      responsavel_nome: pessoaId ? undefined : responsavel.trim() || undefined,
    }
    const opts = {
      onSuccess: () => {
        notify.success(tarefa ? 'Etapa atualizada.' : 'Etapa criada no plano.')
        onFechar()
      },
      onError: (e: Error) => notify.error(e.message),
    }
    if (tarefa) {
      editar.mutate({ tarefaId: tarefa.id, ...campos }, opts)
    } else {
      criar.mutate(campos, opts)
    }
  }

  return (
    <Dialog open={aberto} onOpenChange={(v) => !v && onFechar()}>
      <DialogContent className="gap-0 p-0 sm:max-w-md">
        <DialogHeader className="px-6 pt-6 text-center sm:text-center">
          <DialogTitle className="text-lg">
            {tarefa ? 'Editar etapa' : 'Nova etapa'}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3 px-6 py-5">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Nome da etapa</Label>
            <Input
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              placeholder="Ex.: Negociar fiador do contrato"
              className="h-10"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Área</Label>
              <Select value={categoria} onValueChange={setCategoria}>
                <SelectTrigger className="h-10 w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(CATEGORIA_LABEL).map(([valor, rotulo]) => (
                    <SelectItem key={valor} value={valor}>
                      {rotulo}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Prazo</Label>
              <Input
                type="date"
                value={prazo}
                onChange={(e) => setPrazo(e.target.value)}
                className="h-10"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Custo previsto (R$)</Label>
              <Input
                inputMode="decimal"
                value={custoReais}
                onChange={(e) => setCustoReais(e.target.value)}
                placeholder="0,00"
                className="h-10"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Responsável</Label>
              {pessoas.length > 0 ? (
                <Select value={pessoaId || 'ninguem'} onValueChange={(v) => setPessoaId(v === 'ninguem' ? '' : v)}>
                  <SelectTrigger className="h-10 w-full">
                    <SelectValue placeholder="Quem cuida?" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ninguem">— sem pessoa —</SelectItem>
                    {pessoas.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.nome}
                        {p.papel ? ` (${p.papel})` : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  value={responsavel}
                  onChange={(e) => setResponsavel(e.target.value)}
                  placeholder="Ex.: Empreendedor"
                  className="h-10"
                />
              )}
            </div>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">O que fazer</Label>
            <Input
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              placeholder="Detalhe o que precisa acontecer"
              className="h-10"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">
              Critério de aceite — o que comprova a conclusão
            </Label>
            <Input
              value={criterio}
              onChange={(e) => setCriterio(e.target.value)}
              placeholder="Ex.: 3 imóveis avaliados com foto e parecer; visita à prefeitura registrada"
              className="h-10"
            />
          </div>
        </div>

        <DialogFooter className="gap-2 border-t px-6 py-4 sm:justify-end">
          <Button variant="outline" onClick={onFechar} className="h-10">
            Cancelar
          </Button>
          <Button className="h-10" disabled={!titulo.trim() || salvando} onClick={salvar}>
            {salvando ? 'Salvando…' : tarefa ? 'Salvar mudanças' : 'Criar etapa'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
