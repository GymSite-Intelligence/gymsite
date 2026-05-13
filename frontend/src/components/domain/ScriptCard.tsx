/**
 * ScriptCard — card destacado com o script de abordagem do A5.
 *
 * Mostra:
 *   - Canal recomendado (badge colorida por tipo)
 *   - Melhor horário
 *   - Nível de confiança do contato
 *   - Script formatado em <pre> monospace
 *   - Botão "Copiar" usando navigator.clipboard
 *   - Próximos passos (lista)
 */
import { useState } from 'react'
import { Check, Copy, MessageCircle, Phone, Mail, Linkedin } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface ContatoDecisorShape {
  tipo_ponto?: string
  decisor_identificado?: string
  empresa?: string
  telefone?: string
  email?: string
  whatsapp_link?: string
  canal_recomendado?: 'WHATSAPP' | 'LIGACAO' | 'EMAIL' | 'LINKEDIN' | string
  observacao_canal?: string
  melhor_horario?: string
  script_abordagem?: string
  nivel_confianca_contato?: 'ALTO' | 'MEDIO' | 'BAIXO' | string
  proximos_passos?: string[]
}

export interface ScriptCardProps {
  contato: ContatoDecisorShape | null | undefined
  className?: string
}

const CANAL_CONFIG: Record<
  string,
  { label: string; Icon: typeof MessageCircle; bg: string }
> = {
  WHATSAPP: { label: 'WhatsApp', Icon: MessageCircle, bg: 'bg-veredito-aprovado' },
  LIGACAO: { label: 'Ligação', Icon: Phone, bg: 'bg-veredito-investigar' },
  EMAIL: { label: 'E-mail', Icon: Mail, bg: 'bg-muted-foreground' },
  LINKEDIN: { label: 'LinkedIn', Icon: Linkedin, bg: 'bg-veredito-investigar' },
}

const CONFIANCA_COLOR: Record<string, string> = {
  ALTO: 'text-veredito-aprovado',
  MEDIO: 'text-veredito-ressalvas',
  BAIXO: 'text-veredito-reprovado',
}

export function ScriptCard({ contato, className }: ScriptCardProps) {
  const [copied, setCopied] = useState(false)

  if (!contato || (!contato.script_abordagem && !contato.canal_recomendado)) {
    return null
  }

  // `??` aqui fallha pra string vazia (`""` é falsy mas não nullish — vira `""` em vez de WHATSAPP).
  // Por isso checa explicitamente com ternário antes de aplicar fallback.
  const canalKey = contato.canal_recomendado || 'WHATSAPP'
  const canalCfg = CANAL_CONFIG[canalKey] ?? CANAL_CONFIG.WHATSAPP
  const CanalIcon = canalCfg.Icon

  const handleCopy = async () => {
    if (!contato.script_abordagem) return
    try {
      await navigator.clipboard.writeText(contato.script_abordagem)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // navegador antigo sem Clipboard API — silent fallback
    }
  }

  return (
    <div
      className={cn(
        'rounded-lg border border-primary/30 bg-primary/5 overflow-hidden',
        className,
      )}
    >
      {/* Header com canal + confiança */}
      <header className="px-5 py-3 border-b border-border bg-background/40 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3 flex-wrap">
          <span
            className={cn(
              'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-semibold text-white',
              canalCfg.bg,
            )}
          >
            <CanalIcon size={12} />
            {canalCfg.label}
          </span>
          {contato.melhor_horario && (
            <span className="text-xs text-muted-foreground">
              {contato.melhor_horario}
            </span>
          )}
        </div>
        {contato.nivel_confianca_contato && (
          <span className="text-[10px] font-mono uppercase">
            <span className="text-muted-foreground">Confiança: </span>
            <span
              className={cn(
                'font-semibold',
                CONFIANCA_COLOR[contato.nivel_confianca_contato] ?? 'text-foreground',
              )}
            >
              {contato.nivel_confianca_contato}
            </span>
          </span>
        )}
      </header>

      <div className="p-5 space-y-4">
        {/* Identificação alvo */}
        {(contato.decisor_identificado || contato.empresa) && (
          <div className="text-xs space-y-1">
            {contato.decisor_identificado && (
              <div>
                <span className="text-muted-foreground">Decisor: </span>
                <span className="font-medium">{contato.decisor_identificado}</span>
              </div>
            )}
            {contato.empresa && contato.empresa !== 'N/A' && (
              <div>
                <span className="text-muted-foreground">Empresa: </span>
                <span className="font-medium">{contato.empresa}</span>
              </div>
            )}
            {contato.telefone && contato.telefone !== 'N/A' && (
              <div>
                <span className="text-muted-foreground">Telefone: </span>
                <span className="font-mono">{contato.telefone}</span>
              </div>
            )}
          </div>
        )}

        {/* Script */}
        {contato.script_abordagem && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono">
                Script de abordagem
              </h4>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopy}
                aria-label="Copiar script para a área de transferência"
              >
                {copied ? (
                  <>
                    <Check size={12} /> Copiado!
                  </>
                ) : (
                  <>
                    <Copy size={12} /> Copiar
                  </>
                )}
              </Button>
            </div>
            <pre className="text-xs font-mono leading-relaxed bg-background/50 border border-border rounded-md p-4 overflow-x-auto whitespace-pre-wrap">
              {contato.script_abordagem}
            </pre>
          </div>
        )}

        {/* Próximos passos */}
        {contato.proximos_passos && contato.proximos_passos.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono">
              Próximos passos
            </h4>
            <ol className="space-y-1.5 list-decimal list-inside text-sm">
              {contato.proximos_passos.map((p, i) => (
                <li key={i} className="text-foreground/90 leading-snug pl-1">
                  <span className="ml-1">{p}</span>
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </div>
  )
}
