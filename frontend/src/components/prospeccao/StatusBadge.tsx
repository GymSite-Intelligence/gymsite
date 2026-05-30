import { Badge } from '@/components/ui/badge'

const STATUS_CONFIG: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' }> = {
  novo: { label: 'Novo', variant: 'default' },
  qualificado: { label: 'Qualificado', variant: 'secondary' },
  webhook_enviado: { label: 'Webhook Enviado', variant: 'success' as any },
  engajado: { label: 'Engajado', variant: 'outline' },
  fechado: { label: 'Fechado', variant: 'success' as any },
  descartado: { label: 'Descartado', variant: 'destructive' },
}

export function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || { label: status, variant: 'default' as const }
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>
}
