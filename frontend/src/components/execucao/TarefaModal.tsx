/**
 * TarefaModal — ficha da etapa em modal centralizado.
 *
 * Mesmo padrão visual da ficha de oportunidade da Prospecção: título no topo,
 * badges, grid de campos com rótulos discretos, seções divididas, seletor de
 * situação e ações no rodapé. Substitui o painel lateral (decisão 12/06).
 * Concluir etapa de valor alto (> R$ 10.000 previstos) pede o gasto real
 * (CST-003); nas demais o campo é opcional.
 */
import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, FileText, Paperclip, Send, Sparkles, X } from 'lucide-react'
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
import { notify } from '@/lib/notify'
import { formatBRL } from '@/lib/format'
import { CATEGORIA_LABEL } from '@/components/execucao/PlaybookKanban'
import {
  abrirAnexo,
  useAdicionarNota,
  useAnexosTarefa,
  useAtribuirResponsavelChecklist,
  useAtribuirResponsavelTarefa,
  useEnviarAnexo,
  useExcluirAnexo,
  useNotasTarefa,
  useRegistrarGasto,
  type Pessoa,
  type Tarefa,
} from '@/hooks/usePlaybook'

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
  playbookId,
  pessoas,
}: {
  tarefa: Tarefa | null
  aberto: boolean
  onFechar: () => void
  onMudarStatus: (status: Tarefa['status'], custoRealCentavos: number | null) => void
  onMarcarChecklist: (itemId: string, concluido: boolean) => void
  salvando: boolean
  playbookId: string
  pessoas: Pessoa[]
}) {
  const [novoStatus, setNovoStatus] = useState<Tarefa['status'] | ''>('')
  const [gastoReais, setGastoReais] = useState('')
  const [novaNota, setNovaNota] = useState('')
  const arquivoRef = useRef<HTMLInputElement>(null)

  const { data: notas } = useNotasTarefa(tarefa?.id ?? null)
  const adicionarNota = useAdicionarNota(tarefa?.id ?? null)
  const { data: anexos } = useAnexosTarefa(tarefa?.id ?? null)
  const enviarAnexo = useEnviarAnexo(tarefa?.id ?? null)
  const excluirAnexo = useExcluirAnexo(tarefa?.id ?? null)
  const atribuirTarefa = useAtribuirResponsavelTarefa(playbookId)
  const atribuirPasso = useAtribuirResponsavelChecklist(playbookId)
  const registrarGasto = useRegistrarGasto(playbookId)
  const [gastoEdit, setGastoEdit] = useState<string | null>(null)

  useEffect(() => {
    setNovoStatus('')
    setGastoReais('')
    setNovaNota('')
    setGastoEdit(null)
  }, [tarefa?.id])

  if (!tarefa) return null

  const statusEfetivo = (novoStatus || tarefa.status) as Tarefa['status']
  const concluindo = statusEfetivo === 'CONCLUIDA' && tarefa.status !== 'CONCLUIDA'
  const custoAlto = (tarefa.custo_planejado ?? 0) > CUSTO_OBRIGATORIO_ACIMA_CENTAVOS
  const precisaGasto = concluindo && custoAlto && !gastoReais.trim()
  const mudou = Boolean(novoStatus) && novoStatus !== tarefa.status

  const variacao = tarefa.variacao_conclusao_dias

  function salvarGasto() {
    if (gastoEdit == null || !tarefa) return
    const txt = gastoEdit.replace(/\./g, '').replace(',', '.').trim()
    setGastoEdit(null)
    if (!txt) return
    const v = Number(txt)
    if (Number.isNaN(v) || v < 0) return
    const centavos = Math.round(v * 100)
    if (centavos === (tarefa.custo_real ?? 0)) return
    registrarGasto.mutate(
      { tarefaId: tarefa.id, custoRealCentavos: centavos },
      { onError: (e: Error) => notify.error(e.message) },
    )
  }

  function aoEscolherArquivo(e: React.ChangeEvent<HTMLInputElement>) {
    const arquivo = e.target.files?.[0]
    e.target.value = ''
    if (!arquivo) return
    enviarAnexo.mutate(
      { arquivo },
      { onError: (err: Error) => notify.error(err.message) },
    )
  }

  function enviarNota() {
    const texto = novaNota.trim()
    if (!texto) return
    adicionarNota.mutate(texto, {
      onSuccess: () => setNovaNota(''),
      onError: (e: Error) => notify.error(e.message),
    })
  }

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
            {variacao != null && variacao > 0 && (
              <Badge variant="secondary" className="rounded-full bg-amber-50 px-3 font-normal text-amber-700">
                Concluída {variacao} dia(s) depois do previsto
              </Badge>
            )}
            {variacao != null && variacao < 0 && (
              <Badge variant="secondary" className="rounded-full bg-emerald-50 px-3 font-normal text-emerald-700">
                Concluída {Math.abs(variacao)} dia(s) antes do previsto
              </Badge>
            )}
          </div>
        </DialogHeader>

        <div className="space-y-5 px-6 py-5">
          <div className="grid grid-cols-2 gap-x-6 gap-y-4">
            <Campo rotulo="Prazo">{formatData(tarefa.data_prevista_conclusao)}</Campo>
            <Campo rotulo="Responsável">
              {pessoas.length > 0 ? (
                <Select
                  value={tarefa.responsavel_pessoa_id ?? 'sugestao'}
                  onValueChange={(v) =>
                    atribuirTarefa.mutate(
                      { tarefaId: tarefa.id, pessoaId: v === 'sugestao' ? null : v },
                      { onError: (e: Error) => notify.error(e.message) },
                    )
                  }
                >
                  <SelectTrigger className="h-8 w-full text-sm font-medium">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sugestao">{tarefa.responsavel_nome ?? '—'}</SelectItem>
                    {pessoas.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.nome}
                        {p.papel ? ` (${p.papel})` : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                (tarefa.responsavel_nome ?? '—')
              )}
            </Campo>
            <Campo rotulo="Previsto">
              {tarefa.custo_planejado != null ? formatBRL(tarefa.custo_planejado / 100) : '—'}
            </Campo>
            <Campo rotulo="Gasto até agora">
              <Input
                inputMode="decimal"
                placeholder="R$ 0,00"
                className="h-8 w-full text-sm font-medium"
                value={
                  gastoEdit ??
                  (tarefa.custo_real != null ? String(tarefa.custo_real / 100).replace('.', ',') : '')
                }
                onChange={(e) => setGastoEdit(e.target.value)}
                onBlur={salvarGasto}
                onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
                aria-label="Gasto até agora"
              />
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
                  <div key={item.id} className="flex items-start gap-2 text-sm">
                    <label className="flex min-w-0 flex-1 cursor-pointer items-start gap-2">
                      <Checkbox
                        checked={item.concluido}
                        onCheckedChange={(v) => onMarcarChecklist(item.id, v === true)}
                        className="mt-0.5"
                      />
                      <span className={item.concluido ? 'text-muted-foreground line-through' : ''}>
                        {item.descricao}
                      </span>
                    </label>
                    {pessoas.length > 0 && (
                      <Select
                        value={item.responsavel_pessoa_id ?? 'ninguem'}
                        onValueChange={(v) =>
                          atribuirPasso.mutate(
                            { itemId: item.id, pessoaId: v === 'ninguem' ? null : v },
                            { onError: (e: Error) => notify.error(e.message) },
                          )
                        }
                      >
                        <SelectTrigger className="h-7 w-28 shrink-0 border-dashed text-xs text-muted-foreground">
                          <SelectValue placeholder="quem faz?" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="ninguem">quem faz?</SelectItem>
                          {pessoas.map((p) => (
                            <SelectItem key={p.id} value={p.id}>
                              {p.nome}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="border-t pt-4">
            <p className="mb-2 text-xs text-muted-foreground">Andamento</p>
            <div className="flex gap-2">
              <Input
                placeholder="O que aconteceu nesta etapa?"
                value={novaNota}
                onChange={(e) => setNovaNota(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && enviarNota()}
                className="h-10"
              />
              <Button
                variant="outline"
                size="icon"
                className="h-10 w-10 shrink-0"
                disabled={!novaNota.trim() || adicionarNota.isPending}
                onClick={enviarNota}
                aria-label="Salvar anotação"
              >
                <Send className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-10 w-10 shrink-0"
                disabled={enviarAnexo.isPending}
                onClick={() => arquivoRef.current?.click()}
                aria-label="Anexar arquivo"
              >
                <Paperclip className="h-4 w-4" />
              </Button>
              <input
                ref={arquivoRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp,.heic,.doc,.docx,.xls,.xlsx"
                className="hidden"
                onChange={aoEscolherArquivo}
              />
            </div>
            {enviarAnexo.isPending && (
              <p className="mt-2 text-xs text-muted-foreground">Enviando arquivo…</p>
            )}
            {(anexos ?? []).length > 0 && (
              <div className="mt-3 flex flex-col gap-1.5">
                {(anexos ?? []).map((a) => (
                  <div key={a.id} className="flex items-center gap-2 rounded-md border px-3 py-1.5">
                    <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <button
                      type="button"
                      className="min-w-0 flex-1 truncate text-left text-sm hover:underline"
                      onClick={() => abrirAnexo(a.id).catch((e: Error) => notify.error(e.message))}
                    >
                      {a.nome_arquivo}
                    </button>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {a.tamanho_bytes != null ? `${Math.max(1, Math.round(a.tamanho_bytes / 1024))} KB` : ''}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 shrink-0 text-muted-foreground hover:text-red-600"
                      aria-label={`Excluir ${a.nome_arquivo}`}
                      onClick={() =>
                        excluirAnexo.mutate(a.id, { onError: (e: Error) => notify.error(e.message) })
                      }
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
            {(notas ?? []).length > 0 && (
              <div className="mt-3 flex max-h-48 flex-col gap-2 overflow-y-auto">
                {(notas ?? []).map((n) => (
                  <div key={n.id} className="rounded-md bg-muted/50 px-3 py-2">
                    <p className="text-sm leading-relaxed">{n.texto}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {n.autor_nome} · {new Date(n.criado_em).toLocaleDateString('pt-BR')}{' '}
                      {new Date(n.criado_em).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                      {n.origem === 'IA' ? ' · IA' : n.origem === 'EXTERNO' ? ' · externo' : ''}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

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
