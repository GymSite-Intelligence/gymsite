import { Badge } from '@/components/ui/badge'

const PRIORIDADE_CONFIG: Record<string, { label: string; className: string }> = {
  baixa: { label: 'Baixa', className: 'bg-gray-100 text-gray-700 hover:bg-gray-100' },
  media: { label: 'Média', className: 'bg-blue-100 text-blue-700 hover:bg-blue-100' },
  alta: { label: 'Alta', className: 'bg-orange-100 text-orange-700 hover:bg-orange-100' },
  critica: { label: 'Crítica', className: 'bg-red-100 text-red-700 hover:bg-red-100' },
}

export function PrioridadeBadge({ prioridade }: { prioridade: string }) {
  const cfg = PRIORIDADE_CONFIG[prioridade] || { label: prioridade, className: '' }
  return <Badge className={cfg.className}>{cfg.label}</Badge>
}
