import { DEGUSTACAO_COPY } from '@/config/gymsite-design-system'

interface DegustacaoJornadaAsideProps {
  temAnalise?: boolean
}

export function DegustacaoJornadaAside({ temAnalise = false }: DegustacaoJornadaAsideProps) {
  return (
    <aside className="hidden w-72 shrink-0 flex-col gap-3 overflow-y-auto border-l border-border bg-muted/20 p-4 xl:flex">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Sua jornada</h2>
      <ol className="space-y-3">
        {DEGUSTACAO_COPY.passosJornada.map((passo, i) => {
          const ativo = i === 0 || (i === 2 && temAnalise)
          return (
            <li
              key={passo.passo}
              className={`rounded-xl border p-3 ${ativo ? 'border-primary/25 bg-primary/5' : 'border-border/60 bg-card/40'}`}
            >
              <span className="font-mono text-[10px] font-bold text-primary">{passo.passo}</span>
              <p className="mt-1 text-xs font-semibold text-foreground">{passo.titulo}</p>
              <p className="mt-1 text-[10px] leading-relaxed text-muted-foreground">{passo.texto}</p>
            </li>
          )
        })}
      </ol>
    </aside>
  )
}
