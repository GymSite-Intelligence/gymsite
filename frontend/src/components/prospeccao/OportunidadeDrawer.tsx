import { Button } from '@/components/ui/button'
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from '@/components/ui/drawer'
import { useOportunidade, useReenviarWebhook, usePatchStatusOportunidade } from '@/hooks/useProspeccao'
import { StatusBadge } from './StatusBadge'
import { PrioridadeBadge } from './PrioridadeBadge'
import { RefreshCw, ExternalLink, Braces } from 'lucide-react'
import { toast } from 'sonner'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface Props {
  id: string | null
  open: boolean
  onClose: () => void
}

export function OportunidadeDrawer({ id, open, onClose }: Props) {
  const { data, isLoading } = useOportunidade(id ?? undefined)
  const reenviar = useReenviarWebhook()
  const patchStatus = usePatchStatusOportunidade()

  function montarJson() {
    if (!data) return
    const c = (data.contato_cnpj ?? {}) as Record<string, string | null | undefined>
    const payload = {
      id: data.id,
      empresa: data.nome_fantasia || data.razao_social || null,
      razao_social: data.razao_social ?? null,
      nome_fantasia: data.nome_fantasia ?? null,
      cnpj: data.cnpj,
      cno: data.cno ?? null,
      cidade: data.cidade ?? null,
      uf: data.uf ?? null,
      area_total_m2: data.area_total_m2 ?? null,
      status: data.status,
      prioridade: data.prioridade,
      score_match: data.score_match ?? null,
      motivo_match: data.motivo_match ?? null,
      situacao_obra: data.situacao_obra ?? null,
      contato: {
        decision_maker: c.decision_maker ?? null,
        cargo: c.cargo ?? null,
        email: c.email ?? null,
        telefone: c.telefone ?? null,
        whatsapp_link: c.whatsapp_link ?? null,
      },
      webhook: {
        enviado_at: data.webhook_enviado_at ?? null,
        resposta_http: data.webhook_resposta_http ?? null,
        tentativas: data.webhook_tentativas ?? 0,
      },
    }
    const texto = JSON.stringify(payload, null, 2)
    navigator.clipboard.writeText(texto).then(
      () => toast.success('JSON copiado para a área de transferência'),
      () => toast.error('Não foi possível copiar o JSON'),
    )
  }

  return (
    <Drawer open={open} onOpenChange={(v) => !v && onClose()}>
      <DrawerContent className="max-w-xl mx-auto">
        <DrawerHeader>
          <DrawerTitle className="text-lg">
            {isLoading ? 'Carregando…' : data?.nome_fantasia || data?.razao_social || 'Oportunidade'}
          </DrawerTitle>
        </DrawerHeader>

        {data && (
          <div className="px-4 pb-4 space-y-4 text-sm">
            <div className="flex items-center gap-2 flex-wrap">
              <StatusBadge status={data.status} />
              <PrioridadeBadge prioridade={data.prioridade} />
              {data.score_match != null && (
                <span className="text-muted-foreground">Score: {data.score_match.toFixed(2)}</span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-muted-foreground">CNPJ</p>
                <p className="font-mono">{data.cnpj}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">CNO</p>
                <p className="font-mono">{data.cno ?? '—'}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Cidade/UF</p>
                <p>{data.cidade} / {data.uf}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Área obra</p>
                <p>{data.area_total_m2 ? `${data.area_total_m2} m²` : '—'}</p>
              </div>
            </div>

            {data.motivo_match && (
              <div>
                <p className="text-xs text-muted-foreground">Motivo do match</p>
                <p>{data.motivo_match}</p>
              </div>
            )}

            {data.situacao_obra && (
              <div>
                <p className="text-xs text-muted-foreground">Situação da obra</p>
                <p className="capitalize">{data.situacao_obra.replace('_', ' ')}</p>
              </div>
            )}

            {data.contato_cnpj && Object.keys(data.contato_cnpj).length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-1">Contato</p>
                <div className="space-y-1">
                  {(() => {
                    const c = data.contato_cnpj as Record<string, string | null | undefined>
                    return (
                      <>
                        {c.decision_maker && <p>{c.decision_maker} — {c.cargo ?? ''}</p>}
                        {c.email && <p>{c.email}</p>}
                        {c.telefone && <p>{c.telefone}</p>}
                        {c.whatsapp_link && (
                          <a href={c.whatsapp_link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-teal-700 hover:underline">
                            <span>WhatsApp</span> <ExternalLink size={12} />
                          </a>
                        )}
                      </>
                    )
                  })()}
                </div>
              </div>
            )}

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Webhook:</span>
              {data.webhook_enviado_at ? (
                <span className="text-green-600">
                  Enviado ({data.webhook_resposta_http ?? '—'})
                </span>
              ) : (
                <span className="text-amber-600">Pendente</span>
              )}
              {data.webhook_tentativas > 0 && (
                <span>• {data.webhook_tentativas} tentativa(s)</span>
              )}
            </div>

            {/* Pipeline — mudar status */}
            <div className="border-t pt-3 space-y-2">
              <p className="text-xs text-muted-foreground">Pipeline</p>
              <Select
                value={data.status}
                onValueChange={(novo) => {
                  patchStatus.mutate(
                    { id: data.id, status: novo },
                    {
                      onSuccess: () => toast.success(`Status atualizado para "${novo}"`),
                      onError: (err: any) => toast.error(err.message || 'Erro ao atualizar status')
                    }
                  );
                }}
                disabled={patchStatus.isPending}
              >
                <SelectTrigger className="w-full h-8 text-xs">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="novo">Novo</SelectItem>
                  <SelectItem value="qualificado">Qualificado</SelectItem>
                  <SelectItem value="webhook_enviado">Webhook Enviado</SelectItem>
                  <SelectItem value="engajado">Engajado</SelectItem>
                  <SelectItem value="fechado">Fechado</SelectItem>
                  <SelectItem value="descartado">Descartado</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        <DrawerFooter className="flex-row justify-end gap-2">
          {data && (
            <Button variant="outline" size="sm" onClick={montarJson}>
              <Braces size={14} className="mr-1.5" />
              Copiar JSON
            </Button>
          )}
          {data && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                reenviar.mutate(data.id, {
                  onSuccess: () => toast.success('Webhook reenviado com sucesso!'),
                  onError: (err: any) => toast.error(err.message || 'Erro ao reenviar webhook')
                });
              }}
              disabled={reenviar.isPending}
            >
              <RefreshCw size={14} className="mr-1.5" />
              {reenviar.isPending ? 'Reenviando…' : 'Reenviar webhook'}
            </Button>
          )}
          <DrawerClose asChild>
            <Button variant="ghost" size="sm">Fechar</Button>
          </DrawerClose>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  )
}
