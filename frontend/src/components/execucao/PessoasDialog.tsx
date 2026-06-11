/**
 * PessoasDialog — equipe do projeto (contador, arquiteto, sócio…).
 *
 * Pessoas são externas à plataforma (sem login). Cadastro leve: nome, papel
 * e contato. É a base do vínculo responsável por etapa/passo e, na F3, o
 * destinatário dos formulários por papel.
 */
import { useState } from 'react'
import { Trash2, UserPlus } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { notify } from '@/lib/notify'
import {
  useCriarPessoa,
  useRemoverPessoa,
  type Pessoa,
} from '@/hooks/usePlaybook'

export function PessoasDialog({
  aberto,
  onFechar,
  pessoas,
  playbookId,
  projetoId,
}: {
  aberto: boolean
  onFechar: () => void
  pessoas: Pessoa[]
  playbookId: string
  projetoId: string | undefined
}) {
  const [nome, setNome] = useState('')
  const [papel, setPapel] = useState('')
  const [telefone, setTelefone] = useState('')

  const criar = useCriarPessoa(playbookId, projetoId)
  const remover = useRemoverPessoa(playbookId)

  function adicionar() {
    if (!nome.trim()) return
    criar.mutate(
      { nome: nome.trim(), papel: papel.trim() || undefined, telefone: telefone.trim() || undefined },
      {
        onSuccess: () => {
          setNome('')
          setPapel('')
          setTelefone('')
        },
        onError: (e: Error) => notify.error(e.message),
      },
    )
  }

  return (
    <Dialog open={aberto} onOpenChange={(v) => !v && onFechar()}>
      <DialogContent className="gap-0 p-0 sm:max-w-md">
        <DialogHeader className="px-6 pt-6 text-center sm:text-center">
          <DialogTitle className="text-lg">Pessoas do projeto</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 px-6 py-5">
          {pessoas.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Cadastre quem trabalha com você na abertura — contador, arquiteto,
              sócio. Depois é só apontar quem cuida de cada etapa.
            </p>
          )}

          {pessoas.length > 0 && (
            <div className="flex flex-col gap-2">
              {pessoas.map((p) => (
                <div key={p.id} className="flex items-center gap-2 rounded-md border px-3 py-2">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{p.nome}</p>
                    {p.telefone && (
                      <p className="truncate text-xs text-muted-foreground">{p.telefone}</p>
                    )}
                  </div>
                  {p.papel && (
                    <Badge variant="secondary" className="rounded-full px-2.5 font-normal">
                      {p.papel}
                    </Badge>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 shrink-0 text-muted-foreground hover:text-red-600"
                    aria-label={`Remover ${p.nome}`}
                    onClick={() =>
                      remover.mutate(p.id, { onError: (e: Error) => notify.error(e.message) })
                    }
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          <div className="space-y-2 border-t pt-4">
            <Input
              placeholder="Nome"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              className="h-10"
            />
            <div className="flex gap-2">
              <Input
                placeholder="Papel (ex.: Contador)"
                value={papel}
                onChange={(e) => setPapel(e.target.value)}
                className="h-10"
              />
              <Input
                placeholder="WhatsApp"
                value={telefone}
                onChange={(e) => setTelefone(e.target.value)}
                className="h-10"
              />
            </div>
            <Button
              className="h-10 w-full"
              disabled={!nome.trim() || criar.isPending}
              onClick={adicionar}
            >
              <UserPlus className="mr-1.5 h-4 w-4" />
              {criar.isPending ? 'Adicionando…' : 'Adicionar pessoa'}
            </Button>
          </div>
        </div>

        <DialogFooter className="border-t px-6 py-4 sm:justify-end">
          <Button variant="outline" onClick={onFechar} className="h-10">
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
