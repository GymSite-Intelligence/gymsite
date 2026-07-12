import { Stamp, Info, ExternalLink } from 'lucide-react'

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

function Parte({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5" role="group" aria-label={label}>
      <dt className="text-[10px] font-semibold uppercase tracking-wide text-primary/80">{label}</dt>
      <dd className="text-xs leading-snug text-foreground">{children}</dd>
    </div>
  )
}

export function CitationStamp({ citacao }: { citacao: CarimboCitacao }) {
  const dados = normalizar(citacao)

  if (!dados) {
    return (
      <div
        role="note"
        className="mt-2 flex items-start gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground"
      >
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        <span>Sem a fonte completa — confirme com um especialista/órgão local antes de usar este número.</span>
      </div>
    )
  }

  return (
    <figure
      aria-label="Fonte da exigência citada"
      className="mt-2 overflow-hidden rounded-lg border border-primary/30 bg-primary/5"
    >
      <figcaption className="flex items-center gap-1.5 border-b border-primary/20 bg-primary/10 px-3 py-1.5 text-[11px] font-semibold text-primary">
        <Stamp className="h-3.5 w-3.5" aria-hidden />
        Carimbo da fonte
      </figcaption>
      <dl className="grid grid-cols-2 gap-3 px-3 py-2.5">
        <Parte label="Valor">{dados.valor}</Parte>
        <Parte label="Base">{dados.base}</Parte>
        <Parte label="Fonte">
          {dados.url ? (
            <a
              href={dados.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-sm font-medium text-primary underline underline-offset-2 outline-none hover:text-primary/80 focus-visible:ring-2 focus-visible:ring-ring"
            >
              {dados.fonte}
              <ExternalLink className="h-3 w-3 shrink-0" aria-hidden />
            </a>
          ) : (
            dados.fonte
          )}
        </Parte>
        <Parte label="Janela">{dados.janela}</Parte>
      </dl>
    </figure>
  )
}
