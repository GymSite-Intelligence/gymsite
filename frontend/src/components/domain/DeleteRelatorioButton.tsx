/**
 * DeleteRelatorioButton — botão de delete com confirmação inline em 2 cliques.
 *
 * UX: 1º clique "arma" (vira vermelho com texto "Confirmar?"); 2º clique
 * dispara a mutation; sem clique em 3s, desarma sozinho.
 */
import { useEffect, useRef, useState } from 'react'
import { Loader2, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useDeleteRelatorio } from '@/hooks/useDeleteRelatorio'
import { notify } from '@/lib/notify'
import { cn } from '@/lib/utils'

const ARMED_TIMEOUT_MS = 3000

export interface DeleteRelatorioButtonProps {
  relatorioId: string
  /** Texto curto pra contexto no toast (ex: "Niterói/Itaipu"). */
  label?: string
  className?: string
  /** Chamado após delete bem-sucedido (ex: redirect). */
  onDeleted?: () => void
}

export function DeleteRelatorioButton({
  relatorioId,
  label,
  className,
  onDeleted,
}: DeleteRelatorioButtonProps) {
  const [armed, setArmed] = useState(false)
  const timeoutRef = useRef<number | null>(null)
  const mutation = useDeleteRelatorio()

  useEffect(() => {
    return () => {
      if (timeoutRef.current) window.clearTimeout(timeoutRef.current)
    }
  }, [])

  function disarm() {
    setArmed(false)
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
  }

  function handleClick(e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()

    if (!armed) {
      setArmed(true)
      timeoutRef.current = window.setTimeout(disarm, ARMED_TIMEOUT_MS)
      return
    }

    disarm()
    mutation.mutate(relatorioId, {
      onSuccess: () => {
        notify.success(
          label ? `Relatório de ${label} apagado` : 'Relatório apagado',
        )
        onDeleted?.()
      },
      onError: (err) => {
        notify.error(err)
      },
    })
  }

  const isLoading = mutation.isPending

  if (isLoading) {
    return (
      <Button
        variant="ghost"
        size="icon"
        disabled
        className={cn('h-8 w-8 text-muted-foreground', className)}
        aria-label="Apagando relatório"
      >
        <Loader2 size={14} className="animate-spin" />
      </Button>
    )
  }

  if (armed) {
    return (
      <Button
        variant="destructive"
        size="sm"
        onClick={handleClick}
        className={cn('h-8 px-2 text-xs', className)}
        aria-label="Confirmar exclusão do relatório"
        autoFocus
      >
        <Trash2 size={12} />
        Confirmar?
      </Button>
    )
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={handleClick}
      className={cn(
        'h-8 w-8 text-muted-foreground hover:text-veredito-reprovado hover:bg-veredito-reprovado/10',
        className,
      )}
      aria-label="Apagar relatório"
      title="Apagar relatório"
    >
      <Trash2 size={14} />
    </Button>
  )
}
