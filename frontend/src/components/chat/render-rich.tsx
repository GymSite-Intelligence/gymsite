import { Fragment } from 'react'

function renderInline(texto: string) {
  return texto.split(/(\*\*[^*]+\*\*)/g).map((parte, i) =>
    /^\*\*[^*]+\*\*$/.test(parte) ? (
      <strong key={i} className="font-semibold text-foreground">
        {parte.slice(2, -2)}
      </strong>
    ) : (
      <Fragment key={i}>{parte}</Fragment>
    ),
  )
}

export function renderRich(texto: string) {
  return texto.split('\n').map((linha, i) => {
    if (!linha.trim()) return <div key={i} className="h-2" />
    const bullet = /^\s*[*\-•]\s+/.test(linha)
    const conteudo = bullet ? linha.replace(/^\s*[*\-•]\s+/, '') : linha
    return bullet ? (
      <div key={i} className="flex gap-1.5">
        <span className="shrink-0 text-lime" aria-hidden>
          •
        </span>
        <span>{renderInline(conteudo)}</span>
      </div>
    ) : (
      <div key={i}>{renderInline(conteudo)}</div>
    )
  })
}
