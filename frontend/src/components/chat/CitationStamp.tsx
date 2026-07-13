import { AlertCircle, ExternalLink, FileText, Stamp } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export interface CarimboCitacao {
  valor?: string | null
  base?: string | null
  fonte?: string | null
  janela?: string | null
  url?: string | null
}

interface CarimboCompleto {
  valor: string
  base: string
  fonte: string
  janela: string
  url?: string
}

function normalizar(c: CarimboCitacao): CarimboCompleto | null {
  const valor = c.valor?.trim()
  const base = c.base?.trim()
  const fonte = c.fonte?.trim()
  const janela = c.janela?.trim()
  if (!valor || !base || !fonte || !janela) return null
  const url = c.url?.trim()
  const linkavel = url && /^https?:\/\//i.test(url) ? url : undefined
  return { valor, base, fonte, janela, url: linkavel }
}

export function CitationStamp({ citacao }: { citacao: CarimboCitacao }) {
  const dados = normalizar(citacao)

  if (!dados) {
    return (
      <Card
        role="note"
        size="sm"
        className="mt-2 border-l-4 border-l-muted-foreground/40 bg-muted/30 py-0 ring-border/60"
      >
        <CardContent className="flex items-start gap-2 py-3 text-xs text-muted-foreground">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          <span>
            Sem a fonte completa — confirme com um especialista ou órgão local antes de usar este
            número.
          </span>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card
      aria-label="Fonte da exigência citada"
      size="sm"
      className={cn(
        'mt-2 border-l-4 border-l-primary bg-primary/5 py-0 shadow-sm ring-primary/20',
      )}
    >
      <CardContent className="space-y-3 py-3">
        <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-primary">
          <Stamp className="h-3.5 w-3.5" aria-hidden />
          Carimbo da fonte
        </div>

        <div>
          <p className="text-lg font-bold tracking-tight text-foreground">{dados.valor}</p>
          <p className="text-sm text-muted-foreground">{dados.base}</p>
        </div>

        <div className="flex flex-wrap gap-2">
          {dados.url ? (
            <a
              href={dados.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-4xl"
            >
              <Badge variant="default" className="gap-1">
                <ExternalLink className="h-3 w-3" aria-hidden />
                {dados.fonte}
              </Badge>
            </a>
          ) : (
            <Badge variant="secondary" className="gap-1">
              <FileText className="h-3 w-3" aria-hidden />
              {dados.fonte}
            </Badge>
          )}
          <Badge variant="outline">{dados.janela}</Badge>
        </div>

        <div className="flex items-start gap-2 border-t border-border/60 pt-2 text-[11px] italic text-muted-foreground">
          <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
          <p>Confirme com um especialista local antes de iniciar o projeto.</p>
        </div>
      </CardContent>
    </Card>
  )
}
