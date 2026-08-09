import type { HTMLAttributes } from "react";
import { DEGUSTACAO_COPY } from "@/lib/degustacaoCopy";
import { cn } from "@/lib/utils";

interface SiteJornadaAsideProps extends HTMLAttributes<HTMLElement> {
  temAnalise?: boolean;
}

export function JornadaContent({ temAnalise = false }: { temAnalise?: boolean }) {
  return (
    <>
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Sua jornada
      </h2>
      <ol className="space-y-3">
        {DEGUSTACAO_COPY.passosJornada.map((passo, i) => {
          const ativo = i === 0 || (i === 2 && temAnalise);
          return (
            <li
              key={passo.passo}
              className={`rounded-xl border p-3 ${
                ativo ? "border-lime/25 bg-lime/5" : "border-border/60 bg-card/40"
              }`}
            >
              <span className="font-mono text-[10px] font-bold text-lime">{passo.passo}</span>
              <p className="mt-1 text-xs font-semibold text-foreground">{passo.titulo}</p>
              <p className="mt-1 text-[10px] leading-relaxed text-muted-foreground">
                {passo.texto}
              </p>
            </li>
          );
        })}
      </ol>
    </>
  );
}

export function SiteJornadaAside({
  temAnalise = false,
  className,
  ...props
}: SiteJornadaAsideProps) {
  return (
    <aside
      className={cn(
        "flex w-72 shrink-0 flex-col gap-3 overflow-y-auto border-l border-border bg-muted/20 p-4",
        className,
      )}
      {...props}
    >
      <JornadaContent temAnalise={temAnalise} />
    </aside>
  );
}
