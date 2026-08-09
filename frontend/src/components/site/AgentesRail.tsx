import { AGENTES_LANDING } from "./agentesLanding";
import type { AgenteChat } from "@/lib/siteAgent";

interface AgentesRailProps {
  /** Card selecionado na UI (tema sugerido — não fixa quem responde na API). */
  agenteUi: AgenteChat;
  idDestaque: AgenteChat;
  onSelect: (id: AgenteChat) => void;
  /** Lista detalhada (nome + especialidade) vs. só ícones. */
  expandido?: boolean;
  className?: string;
}

export function AgentesRail({
  agenteUi: _unusedAgenteUi,
  idDestaque,
  onSelect,
  expandido = true,
  className = "",
}: AgentesRailProps) {
  if (!expandido) {
    return (
      <div className={`flex flex-col items-center gap-1 ${className}`}>
        {AGENTES_LANDING.map((a) => {
          const destacado = a.id === idDestaque;
          return (
            <button
              key={a.id}
              type="button"
              title={`${a.nome} — ${a.especialidade}`}
              onClick={() => onSelect(a.id)}
              className={`flex w-14 flex-col items-center gap-1 rounded-lg py-2 text-[10px] transition ${
                destacado ? "bg-lime/15 text-lime" : "text-muted-foreground hover:bg-accent"
              }`}
            >
              <img src={a.img} alt="" className="h-8 w-8 object-contain" />
              {a.nome}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className={`flex flex-col ${className}`}>
      <div className="px-3 pb-1 pt-3">
        <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
          Tema sugerido
        </span>
      </div>
      <div className="flex flex-col gap-1 px-2 pb-2">
        {AGENTES_LANDING.map((a) => {
          const destacado = a.id === idDestaque;
          return (
            <button
              key={a.id}
              type="button"
              title={`${a.nome} — ${a.especialidade}`}
              onClick={() => onSelect(a.id)}
              className={`flex w-full items-center gap-2.5 rounded-lg border p-2 text-left transition ${
                destacado
                  ? "border-lime/25 bg-lime/5 text-lime"
                  : "border-transparent text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              }`}
            >
              <img src={a.img} alt="" className="h-9 w-9 shrink-0 object-contain" />
              <div className="min-w-0 flex-1">
                <span className="block truncate text-xs font-semibold">{a.nome}</span>
                <span className="block truncate text-[10px] leading-tight opacity-80">
                  {a.especialidade}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
