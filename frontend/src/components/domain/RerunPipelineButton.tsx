/**
 * RerunPipelineButton — Re-executa o pipeline sem reabrir o formulário.
 */
import type { MouseEvent } from 'react'
import { Loader2, RefreshCw } from 'lucide-react'
import { USE_MOCKS } from '@/mocks'
import { useRerunPipeline } from '@/hooks/useRerunPipeline'
import { Button } from '@/components/ui/button'
import type { PipelineReportPayload } from '@/lib/submit-pipeline'
import type { RelatorioStatus } from '@/types/domain'
import { cn } from '@/lib/utils'

export interface RerunPipelineButtonProps {
  relatorioId: string
  inputs?: PipelineReportPayload
  status?: RelatorioStatus
  /** Texto do botão. Default: "Gerar novamente" */
  label?: string
  variant?: 'default' | 'outline' | 'secondary' | 'ghost'
  size?: 'default' | 'sm' | 'lg' | 'icon'
  className?: string
  /** Para cards na listagem — não propaga clique pro row pai. */
  stopPropagation?: boolean
}

export function RerunPipelineButton({
  relatorioId,
  inputs,
  status,
  label = 'Gerar novamente',
  variant = 'outline',
  size = 'sm',
  className,
  stopPropagation = false,
}: RerunPipelineButtonProps) {
  const mutation = useRerunPipeline()

  if (USE_MOCKS) return null

  const pipelineAtivo = status === 'queued' || status === 'running'
  const disabled = mutation.isPending || pipelineAtivo

  function handleClick(e: MouseEvent) {
    if (stopPropagation) e.stopPropagation()
    if (disabled) return
    mutation.mutate({ relatorioId, inputs })
  }

  return (
    <Button
      type="button"
      variant={variant}
      size={size}
      className={cn('gap-1.5', className)}
      disabled={disabled}
      title={
        pipelineAtivo
          ? 'Pipeline em andamento — aguarde concluir'
          : 'Rodar pipeline novamente com os mesmos parâmetros'
      }
      onClick={handleClick}
    >
      {mutation.isPending ? (
        <Loader2 size={14} className="animate-spin" />
      ) : (
        <RefreshCw size={14} />
      )}
      {size !== 'icon' && label}
    </Button>
  )
}
