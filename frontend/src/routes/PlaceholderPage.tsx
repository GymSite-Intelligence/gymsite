/**
 * PlaceholderPage — reaproveitável pra rotas ainda não implementadas
 * (Novo Relatório form + Viewer do detalhe). Substituir quando cada
 * tela ganhar implementação real.
 */
import { Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function PlaceholderPage({
  title,
  description,
  next,
}: {
  title: string
  description: string
  next?: string
}) {
  return (
    <div className="space-y-4 max-w-2xl">
      <Button variant="ghost" size="sm" asChild>
        <Link to="/relatorios">
          <ArrowLeft size={14} /> Voltar
        </Link>
      </Button>
      <div className="p-8 border border-dashed border-border rounded-lg space-y-3">
        <h1 className="text-xl font-semibold">{title}</h1>
        <p className="text-sm text-muted-foreground">{description}</p>
        {next && (
          <p className="text-xs font-mono text-muted-foreground pt-3 border-t border-border">
            Próximo: {next}
          </p>
        )}
      </div>
    </div>
  )
}
