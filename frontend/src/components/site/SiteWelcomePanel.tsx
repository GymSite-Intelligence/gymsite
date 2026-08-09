import { ArrowRight, ShieldAlert } from "lucide-react";
import { DEGUSTACAO_COPY, MERCADO_CONTEXTO_PESQUISAS } from "@/lib/degustacaoCopy";
import type { AgenteLanding } from "./agentesLanding";

function MiniCard({ kicker, detail }: { kicker: string; detail: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-card/50 p-3 text-left">
      <span className="mb-0.5 block text-xs font-bold text-lime">{kicker}</span>
      <span className="block text-[10px] leading-snug text-muted-foreground">{detail}</span>
    </div>
  );
}

interface SiteWelcomePanelProps {
  agente: AgenteLanding;
  onUseExample: (text: string) => void;
}

export function SiteWelcomePanel({ agente, onUseExample }: SiteWelcomePanelProps) {
  const contextoPesquisas = agente.id === "degustacao" ? MERCADO_CONTEXTO_PESQUISAS : undefined;
  // Garante que o exemplo do Mercado inclua UF (ex.: "Fortaleza, CE") para o backend
  // parsear a localização corretamente sem reperguntar.
  const example =
    agente.id === "degustacao" &&
    /fortaleza/i.test(agente.exemplo) &&
    !/(^|[,\s])CE([,\s]|$)/i.test(agente.exemplo)
      ? `${agente.exemplo.replace(/\s+$/, "")}, CE`
      : agente.exemplo;

  return (
    <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center px-1 py-4 text-center sm:px-2 sm:py-8">
      <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl border border-border bg-card shadow-inner sm:mb-4 sm:h-16 sm:w-16">
        <img src={agente.img} alt="" className="h-10 w-10 object-contain sm:h-12 sm:w-12" />
      </div>

      <span className="text-[10px] font-bold uppercase tracking-widest text-lime">
        {DEGUSTACAO_COPY.tagline}
      </span>
      <h2 className="mt-1.5 text-lg font-bold text-foreground sm:text-xl">Tema: {agente.nome}</h2>
      <p className="mt-1 text-[11px] text-muted-foreground">
        O especialista certo assume conforme sua pergunta — passagem de bastão automática.
      </p>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
        {agente.saudacao}
      </p>

      <div className="mt-4 w-full rounded-2xl border border-border bg-card p-3 text-left sm:mt-5 sm:p-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-lime">
            Sugestão técnica
          </span>
          <span className="font-mono text-[9px] text-muted-foreground">
            exemplo por especialidade
          </span>
        </div>
        <p className="rounded-lg border border-border/80 bg-background p-3 text-xs italic leading-relaxed text-foreground">
          &ldquo;{example}&rdquo;
        </p>
        <button
          type="button"
          onClick={() => onUseExample(example)}
          className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-lime outline-none transition-colors hover:underline focus-visible:ring-2 focus-visible:ring-lime/50"
        >
          Usar pergunta exemplo
          <ArrowRight className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>

      {contextoPesquisas?.length ? (
        <div className="mt-4 w-full text-left">
          <span className="mb-2 block text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            O que este consultor cruza
          </span>
          <div className="flex flex-wrap gap-1.5">
            {contextoPesquisas.map((item) => (
              <span
                key={item}
                className="rounded-md border border-border/70 bg-muted/30 px-2 py-0.5 text-[10px] text-muted-foreground"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-5 grid w-full grid-cols-1 gap-2.5 sm:grid-cols-3">
        {DEGUSTACAO_COPY.badgesAtritoZero.map((detail, i) => (
          <MiniCard
            key={DEGUSTACAO_COPY.miniCardKickers[i]}
            kicker={DEGUSTACAO_COPY.miniCardKickers[i]}
            detail={detail}
          />
        ))}
      </div>

      <div className="mt-4 w-full rounded-xl border border-lime/20 bg-lime/5 p-3.5 text-left">
        <div className="mb-1 flex items-center gap-1.5 text-xs font-bold text-lime">
          <ShieldAlert className="h-3.5 w-3.5 shrink-0" aria-hidden />
          {DEGUSTACAO_COPY.metodologia.titulo}
        </div>
        <p className="text-[10px] leading-relaxed text-muted-foreground">
          {DEGUSTACAO_COPY.metodologia.texto}
        </p>
      </div>
    </div>
  );
}
