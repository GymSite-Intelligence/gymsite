/**
 * GerarPlanoButton — "Gerar plano de abertura" na tela do relatório.
 *
 * Transforma o Relatório de Viabilidade em plano com etapas, prazos e custos.
 * Se o plano já existe, leva direto pra ele.
 */
import { ClipboardList } from 'lucide-react'
import { useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { notify } from '@/lib/notify'
import { useGerarPlano } from '@/hooks/usePlaybook'

export function GerarPlanoButton({
  relatorioId,
  className,
}: {
  relatorioId: string
  className?: string
}) {
  const navigate = useNavigate()
  const gerar = useGerarPlano()

  function onClick() {
    gerar.mutate(
      { relatorioId },
      {
        onSuccess: (r) => {
          if (r.ja_existia) {
            notify.success('Você já tem um plano para esta análise — abrindo.')
          } else {
            notify.success(`Plano de abertura criado com ${r.tarefas_geradas ?? ''} etapas!`)
          }
          navigate({ to: '/execucao/$playbookId', params: { playbookId: r.playbook_id } })
        },
        onError: (e: Error) => notify.error(e.message),
      },
    )
  }

  return (
    <Button onClick={onClick} disabled={gerar.isPending} className={className}>
      <ClipboardList className="mr-1.5 h-4 w-4" />
      {gerar.isPending ? 'Montando seu plano…' : 'Gerar plano de abertura'}
    </Button>
  )
}
