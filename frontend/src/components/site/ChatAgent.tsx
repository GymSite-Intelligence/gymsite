import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Bot, Maximize2, Minimize2 } from "lucide-react";
import { SiteChat } from "@/components/SiteChat";
import { AnaliseGratuitaFlow } from "@/components/site/AnaliseGratuitaFlow";

// Wrapper do diálogo aberto pelos CTAs da landing. O conteúdo é o <SiteChat />,
// que conversa EXCLUSIVAMENTE com o backend real (api.getgymsite.com.br
// /api/site-agent/conversar). Não há mais funil scriptado nem chamada ao Agent
// Builder/Vertex — nenhuma resposta é gerada sem passar pelo /conversar.
export function ChatAgent({ open, onOpenChange, modo = "chat" }: { open: boolean; onOpenChange: (v: boolean) => void; modo?: "chat" | "formulario" }) {
  const [expandido, setExpandido] = useState(false);
  const formulario = modo === "formulario";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={`${expandido ? "max-w-5xl" : "max-w-2xl"} w-[calc(100vw-2rem)] p-0 gap-0 overflow-hidden border-border bg-card transition-[max-width] duration-200`}
      >
        <DialogHeader className="px-5 py-4 border-b border-border bg-petroleum-deep/60">
          <DialogTitle className="flex items-center gap-2 text-foreground font-display">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-lime/15 text-lime">
              <Bot className="h-4 w-4" />
            </span>
            {formulario ? "Análise gratuita do seu ponto" : "Diagnóstico GymSite"}
          </DialogTitle>
          <DialogDescription className="text-muted-foreground text-xs">
            {formulario
              ? "Preencha e receba o retrato da sua região · bases públicas oficiais"
              : "Inteligência de mercado em tempo real · bases públicas oficiais"}
          </DialogDescription>
          {/* Ajuste de tamanho (expandir/recolher). Fica à esquerda do X de fechar. */}
          <button
            type="button"
            onClick={() => setExpandido((v) => !v)}
            aria-label={expandido ? "Recolher" : "Expandir"}
            title={expandido ? "Recolher" : "Expandir"}
            className="absolute right-12 top-4 text-muted-foreground hover:text-foreground transition"
          >
            {expandido ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
        </DialogHeader>
        {formulario ? (
          <div className="max-h-[75vh] overflow-y-auto px-5 py-4">
            <AnaliseGratuitaFlow />
          </div>
        ) : (
          <SiteChat expandido={expandido} />
        )}
      </DialogContent>
    </Dialog>
  );
}
