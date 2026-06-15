/**
 * Demanda futura datada (Apêndice B) — obras residenciais no raio → moradores →
 * captura fitness em T+24. Lidera pelo refinado (site/instagram/PDF da construtora).
 */
import { Building2, CalendarClock, ExternalLink, Users } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { DemandaFuturaJSON } from '@/hooks/useRelatorioDetail'

const CONF_STYLE: Record<string, string> = {
  alta: 'text-veredito-aprovado',
  media: 'text-veredito-ressalvas',
  baixa: 'text-muted-foreground',
  nenhuma: 'text-muted-foreground',
}

function Stat({ icon: Icon, label, value }: { icon: typeof Users; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border bg-card px-3 py-2">
      <Icon className="size-4 text-chart-1 shrink-0" />
      <div className="leading-tight">
        <div className="text-sm font-semibold">{value}</div>
        <div className="text-[11px] text-muted-foreground">{label}</div>
      </div>
    </div>
  )
}

export function DemandaFuturaCard({ block }: { block: DemandaFuturaJSON }) {
  if (!block || block.status !== 'ok' || !block.n_obras) {
    return (
      <p className="text-sm text-muted-foreground">
        Sem obras residenciais com entrega futura no raio (ou fonte CNO indisponível).
      </p>
    )
  }
  const jan = block.janela_entrega
  // Só obras com captura estimada real (> 0). Captura ~0 = não-residencial (fora do
  // gate) ou prédio pequeno demais — não entrega ROI, vira ruído na lista.
  const obras = (block.obras ?? [])
    .filter((o) => Math.round(o.captura_est ?? 0) > 0)
    .sort((a, b) => (b.captura_est ?? 0) - (a.captura_est ?? 0))
    .slice(0, 8)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat icon={Building2} label="obras (entrega futura)" value={block.n_obras} />
        <Stat icon={Building2} label="prováveis residenciais" value={block.provavel_residencial_n ?? '—'} />
        <Stat icon={Users} label="captura fitness est. (T+24)" value={`~${Math.round(block.captura_total_est ?? 0)}`} />
        <Stat
          icon={CalendarClock}
          label="janela de entrega"
          value={jan?.de ? `${jan.de} → ${jan.ate}` : '—'}
        />
      </div>

      {obras.length === 0 ? (
        <p className="text-[11px] text-muted-foreground">
          Nenhuma obra futura com captura estimada relevante (&gt; 0) no bairro — sem
          projeção de receita futura material no momento.
        </p>
      ) : (
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left text-[11px] uppercase text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Empreendimento</th>
              <th className="px-3 py-2">Bairro</th>
              <th className="px-3 py-2 text-right">Unidades</th>
              <th className="px-3 py-2">Entrega</th>
              <th className="px-3 py-2 text-right">Captura est.</th>
              <th className="px-3 py-2">Confiança</th>
            </tr>
          </thead>
          <tbody>
            {obras.map((o, i) => (
              <tr key={i} className={cn('border-t', o.provavel_residencial === false && 'opacity-50')}>
                <td className="px-3 py-2">
                  <span className="font-medium">{o.empreendimento || o.construtora || '—'}</span>
                  {o.fonte_url && (
                    <a href={o.fonte_url} target="_blank" rel="noreferrer"
                       className="ml-1 inline-flex text-chart-1" title="fonte auditada">
                      <ExternalLink className="size-3" />
                    </a>
                  )}
                </td>
                <td className="px-3 py-2 text-muted-foreground">{o.bairro || '—'}</td>
                <td className="px-3 py-2 text-right">
                  {Math.round(o.unidades_est ?? 0)}
                  <span className="ml-1 text-[10px] text-muted-foreground">
                    {o.unidades_fonte === 'lancamento_exato' ? '✓exato' : 'proxy'}
                  </span>
                </td>
                <td className="px-3 py-2">{o.entrega || '—'}</td>
                <td className="px-3 py-2 text-right">{o.captura_est != null ? `~${Math.round(o.captura_est)}` : '—'}</td>
                <td className={cn('px-3 py-2 font-medium', CONF_STYLE[o.confianca ?? 'baixa'])}>
                  {o.confianca ?? 'baixa'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      )}

      <p className="text-[11px] text-muted-foreground">
        {block.refinadas ? `${block.refinadas} obras refinadas via site/instagram/PDF da construtora (auditado). ` : ''}
        {block.residencial_por_base
          ? `Residenciais classificados: ${block.residencial_por_base.refino_tipologia ?? 0} por refino auditado, ${block.residencial_por_base.nome_residencial ?? 0} por nome (CNO). Obra sem sinal não conta. `
          : ''}
        Unidades por proxy área÷75 até refino A4. Captura = moradores × penetração × market share (futuros membros captáveis, não leads).
        Fonte registral: CNPJ responsável no CNO. {block.fonte}.
      </p>
    </div>
  )
}
