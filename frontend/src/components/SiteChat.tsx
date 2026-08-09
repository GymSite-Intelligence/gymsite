import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { PanelLeft, PanelRight, ShieldCheck } from "lucide-react";
import { useSiteChat } from "../hooks/useSiteChat";
import { useMediaQuery } from "../hooks/use-media-query";
import { AnaliseGratuitaFlow } from "./site/AnaliseGratuitaFlow";
import { ConcorrentesCard } from "./site/ConcorrentesCard";
import { PlantaLayoutCard } from "./site/PlantaLayoutCard";
import { SiteWelcomePanel } from "./site/SiteWelcomePanel";
import { JornadaContent, SiteJornadaAside } from "./site/SiteJornadaAside";
import { AgentesRail } from "./site/AgentesRail";
import { DegustacaoCapBanner } from "./site/DegustacaoCapBanner";
import { TurnstileWidget } from "./site/TurnstileWidget";
import { AGENTES_LANDING, agentePadrao, crachaDoAgente } from "./site/agentesLanding";
import { isDegustacaoCapTexto } from "@/lib/degustacaoCopy";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "./ui/sheet";
import { CHAT_PRODUCTION_URL, isDeploymentPreviewHost } from "@/lib/chatOrigin";
import { extrairConcorrentes, extrairPlantaLayout, type AgenteChat } from "@/lib/siteAgent";

// O chat renderiza TEXTO, não markdown — sem isto os `**` do modelo aparecem crus.
// Converte **negrito**, marcadores (* / - / •) e quebras de linha. Sem lib, sem HTML cru.
function renderRich(txt: string) {
  return txt.split("\n").map((linha, i) => {
    const bullet = /^\s*[*\-•]\s+/.test(linha);
    const conteudo = bullet ? linha.replace(/^\s*[*\-•]\s+/, "") : linha;
    const partes = conteudo
      .split(/(\*\*[^*]+\*\*)/g)
      .map((p, j) =>
        /^\*\*[^*]+\*\*$/.test(p) ? (
          <strong key={j}>{p.slice(2, -2)}</strong>
        ) : (
          <span key={j}>{p}</span>
        ),
      );
    if (!linha.trim()) return <div key={i} className="h-2" />;
    return bullet ? (
      <div key={i} className="flex gap-1.5">
        <span className="text-lime shrink-0">•</span>
        <span>{partes}</span>
      </div>
    ) : (
      <div key={i}>{partes}</div>
    );
  });
}

export function SiteChat({
  expandido = false,
  fullPage = false,
  forceDevToken,
}: {
  expandido?: boolean;
  /** Rota `/degustacao` — ocupa a área útil abaixo do header. */
  fullPage?: boolean;
  /** Sandbox `/teste` — injeta bypass sem depender só do parse SSR da URL. */
  forceDevToken?: string;
}) {
  const {
    mensagens,
    carregando,
    etapa,
    podeGerar,
    temProjeto,
    prefill,
    agenteUi,
    setAgenteUi,
    enviar,
    temBypass,
    devToken,
  } = useSiteChat({ forceDevToken });
  const [input, setInput] = useState("");
  const [verifyOpen, setVerifyOpen] = useState(false);
  const [pendingMsg, setPendingMsg] = useState("");
  const [mostrarForm, setMostrarForm] = useState(false); // CTA -> abre o formulário inline
  const [agentsSheetOpen, setAgentsSheetOpen] = useState(false);
  const [jornadaSheetOpen, setJornadaSheetOpen] = useState(false);
  const [agentsCollapsed, setAgentsCollapsed] = useState(false);
  const [jornadaCollapsed, setJornadaCollapsed] = useState(false);
  const isLg = useMediaQuery("(min-width: 1024px)");
  const isXl = useMediaQuery("(min-width: 1280px)");
  const scrollRef = useRef<HTMLDivElement>(null);
  // Detecta links de preview do CF Pages: Turnstile não valida hosts de preview
  // (hash.gym-insight-hub.pages.dev) — exibe banner com link para produção.
  const previewDeploy = isDeploymentPreviewHost();

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [mensagens, carregando, podeGerar]);

  const ag = AGENTES_LANDING.find((a) => a.id === agenteUi) ?? agentePadrao;

  // Quem RESPONDEU por último (o bastão) — o rail destaca este; sem resposta ainda → card UI.
  const ultimoResponder = [...mensagens]
    .reverse()
    .find((m) => m.role === "assistant" && m.agente)?.agente;
  const idDestaque = (ultimoResponder && crachaDoAgente(ultimoResponder)?.id) || agenteUi;

  // CTA da análise completa: após ~3 perguntas OU quando cidade/bairro já fecharam
  // (`podeGerar`). O formulário NÃO substitui o input — senão a degustação morre
  // no primeiro "localização OK" (ex.: reabrir ?pid= com Bessa já resolvido).
  const numPerguntas = mensagens.filter((m) => m.role === "user").length;
  const ofertarCta = !mostrarForm && (podeGerar || numPerguntas >= 3);

  // Quem respondeu por último antes da mensagem i (pra detectar a troca de bastão).
  // Na 1ª resposta não há anterior → cai no card escolhido no rail.
  const responderAnterior = (i: number) => {
    for (let j = i - 1; j >= 0; j--) {
      if (mensagens[j].role === "assistant") return crachaDoAgente(mensagens[j].agente);
    }
    return crachaDoAgente(agenteUi);
  };

  const selectAgenteUi = (id: AgenteChat) => {
    setAgenteUi(id);
    setAgentsSheetOpen(false);
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const txt = input.trim();
    if (!txt || carregando) return;
    if (!temProjeto && !temBypass) {
      // 1ª mensagem: abre o pop-up de verificação; envia após resolver o Turnstile.
      // Dono/dev com ?dev_token= na URL pula o Turnstile (backend valida o token).
      setPendingMsg(txt);
      setInput(""); // limpa o campo imediatamente para evitar dupla-submissão
      setVerifyOpen(true);
      return;
    }
    enviar(txt); // seguintes (ou bypass) não precisam de token
    setInput("");
  };

  // Token emitido no pop-up (single-use) → envia a 1ª msg e fecha.
  const onVerified = (token: string) => {
    if (!token) return; // erro/expira → mantém o pop-up aberto pra retry
    setVerifyOpen(false);
    enviar(pendingMsg, token);
    setInput("");
    setPendingMsg("");
  };

  const onUseExample = (text: string) => {
    if (carregando) return;
    if (!temProjeto && !temBypass) {
      setPendingMsg(text);
      setVerifyOpen(true);
      return;
    }
    enviar(text);
  };

  const agentesAtivo = AGENTES_LANDING.find((a) => a.id === idDestaque) ?? ag;

  return (
    <div
      className={`relative flex ${
        fullPage
          ? "h-full min-h-0"
          : expandido
            ? "h-[82vh] max-h-205"
            : "h-[75vh] sm:h-[62vh] max-h-150 min-h-110"
      }`}
    >
      {/* Aviso de preview deploy — Turnstile não valida hosts *.pages.dev */}
      {previewDeploy && !temBypass && (
        <div className="absolute inset-x-0 top-0 z-20 border-b border-amber-500/30 bg-amber-500/10 px-3 py-2 text-center text-[11px] leading-snug text-amber-100">
          Link de preview do deploy não passa no anti-bot (Turnstile). Teste em{" "}
          <a href={CHAT_PRODUCTION_URL} className="font-semibold text-lime underline">
            gymsite.com.br/degustacao
          </a>{" "}
          ou use <code className="font-mono text-[10px]">?dev_token=…</code> na URL.
        </div>
      )}
      {/* Rail de especialistas — desktop; some ou vira drawer no mobile quando expandido */}
      {expandido ? (
        !agentsCollapsed && (
          <aside
            id="sidebar-especialistas"
            className="hidden w-56 shrink-0 flex-col border-r border-border bg-card lg:flex xl:w-60"
          >
            <AgentesRail
              agenteUi={agenteUi}
              idDestaque={idDestaque}
              onSelect={selectAgenteUi}
              expandido
            />
          </aside>
        )
      ) : (
        <div className="flex w-14 shrink-0 flex-col items-center gap-1 border-r border-border bg-card py-3 sm:w-16">
          <AgentesRail
            agenteUi={agenteUi}
            idDestaque={idDestaque}
            onSelect={setAgenteUi}
            expandido={false}
          />
        </div>
      )}

      {/* Coluna do chat */}
      <div className="flex min-w-0 flex-1 flex-col">
        {expandido && (
          <div className="flex shrink-0 items-center gap-2 border-b border-border bg-card/80 px-2 py-1.5 sm:px-3">
            {/* Mobile: abre drawers. Desktop: colapsa/expande o rail permanente. */}
            <button
              type="button"
              onClick={() => {
                if (isLg) setAgentsCollapsed((v) => !v);
                else setAgentsSheetOpen(true);
              }}
              className={`inline-flex h-9 items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium transition ${
                isLg && !agentsCollapsed
                  ? "border-lime/30 bg-lime/10 text-lime"
                  : "border-border bg-background text-foreground hover:bg-accent"
              }`}
              aria-expanded={isLg ? !agentsCollapsed : agentsSheetOpen}
              aria-controls={isLg ? "sidebar-especialistas" : "sidebar-especialistas-sheet"}
              title={
                isLg
                  ? agentsCollapsed
                    ? "Mostrar especialistas"
                    : "Ocultar especialistas"
                  : "Abrir especialistas"
              }
            >
              <PanelLeft className="h-4 w-4 shrink-0 text-lime" aria-hidden />
              <span className="max-w-28 truncate sm:max-w-none">{agentesAtivo.nome}</span>
            </button>

            <span className="min-w-0 flex-1 truncate text-center text-[11px] text-muted-foreground sm:text-xs">
              {agentesAtivo.especialidade}
            </span>

            <button
              type="button"
              onClick={() => {
                if (isXl) setJornadaCollapsed((v) => !v);
                else setJornadaSheetOpen(true);
              }}
              className={`inline-flex h-9 items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium transition ${
                isXl && !jornadaCollapsed
                  ? "border-lime/30 bg-lime/10 text-lime"
                  : "border-border bg-background text-foreground hover:bg-accent"
              }`}
              aria-expanded={isXl ? !jornadaCollapsed : jornadaSheetOpen}
              aria-controls={isXl ? "sidebar-jornada" : "sidebar-jornada-sheet"}
              title={
                isXl ? (jornadaCollapsed ? "Mostrar jornada" : "Ocultar jornada") : "Abrir jornada"
              }
            >
              <span className="hidden sm:inline">Jornada</span>
              <PanelRight className="h-4 w-4 shrink-0 text-lime" aria-hidden />
            </button>
          </div>
        )}

        <div
          ref={scrollRef}
          className="flex-1 space-y-3 overflow-y-auto bg-background px-3 py-3 sm:px-5 sm:py-4"
        >
          {mensagens.length === 0 && !carregando && (
            <SiteWelcomePanel agente={ag} onUseExample={onUseExample} />
          )}
          {mensagens.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className="max-w-[92%] sm:max-w-[85%]">
                {/* Crachá + passagem de bastão. O crachá (mascote) mostra QUEM respondeu.
                    Quando o responder muda vs. a resposta anterior (ou o card escolhido na 1ª),
                    a nota "passou o bastão" torna o handoff explícito — sem isso o rail parado
                    no card faz parecer que o agente errado respondeu. */}
                {m.role === "assistant" &&
                  (() => {
                    const meu = crachaDoAgente(m.agente);
                    if (!meu) return null;
                    const ant = responderAnterior(i);
                    const handoff = ant && ant.id !== meu.id;
                    return (
                      <>
                        {handoff && (
                          <div className="mb-1 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                            <span className="text-lime">↝</span>
                            <span>
                              <span className="font-medium text-foreground">{ant.nome}</span> passou
                              o bastão pro{" "}
                              <span className="font-medium text-foreground">{meu.nome}</span>
                            </span>
                          </div>
                        )}
                        <div className="mb-1 flex items-center gap-1.5 text-xs">
                          <img src={meu.img} alt="" className="h-6 w-6 shrink-0 object-contain" />
                          <span className="font-medium text-foreground">{meu.nome}</span>
                          <span className="truncate text-muted-foreground">
                            · {meu.especialidade}
                          </span>
                        </div>
                      </>
                    );
                  })()}
                {m.role === "assistant" && isDegustacaoCapTexto(m.texto) ? (
                  <DegustacaoCapBanner
                    texto={m.texto}
                    onCta={() => setMostrarForm(true)}
                  />
                ) : (
                  <div
                    className={`inline-block wrap-break-word rounded-2xl px-3 py-2 text-sm leading-relaxed sm:px-4 ${
                      m.role === "user"
                        ? "bg-lime font-medium text-primary-foreground"
                        : "bg-secondary text-foreground"
                    }`}
                  >
                    {m.role === "assistant" ? renderRich(m.texto) : m.texto}
                  </div>
                )}
                {m.role === "assistant" &&
                  (() => {
                    const conc = extrairConcorrentes([{ tool_calls: m.tool_calls }]);
                    return conc ? <ConcorrentesCard data={conc} /> : null;
                  })()}
                {m.role === "assistant" &&
                  (() => {
                    const planta = extrairPlantaLayout([{ tool_calls: m.tool_calls }]);
                    return planta ? <PlantaLayoutCard data={planta} /> : null;
                  })()}
                {m.sugestoes?.length ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {m.sugestoes.map((s, j) => (
                      <button
                        key={j}
                        type="button"
                        onClick={() => temProjeto && enviar(s)}
                        disabled={!temProjeto || carregando}
                        className="rounded-full border border-lime/40 px-3 py-1 text-xs text-foreground hover:bg-lime/10 hover:text-lime disabled:opacity-50"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          ))}
          {(carregando || etapa === "carregando") && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-lg bg-secondary px-3 py-2 text-sm text-muted-foreground">
                <span className="flex gap-1">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-lime" />
                  <span className="h-2 w-2 animate-pulse rounded-full bg-lime [animation-delay:150ms]" />
                  <span className="h-2 w-2 animate-pulse rounded-full bg-lime [animation-delay:300ms]" />
                </span>
                {etapa === "carregando" && "Retomando conversa anterior…"}
                {etapa === "enviando" && "Enviando mensagem…"}
                {etapa === "aguardando" && "Aguardando resposta… (pode levar 1-3 min)"}
                {etapa === "processando" && "Analisando bases públicas… (pode levar 1-3 min)"}
                {etapa === "idle" && "Carregando…"}
              </div>
            </div>
          )}
          {mostrarForm && (
            <div className="space-y-2">
              <AnaliseGratuitaFlow prefill={prefill} devToken={devToken} />
              <button
                type="button"
                onClick={() => setMostrarForm(false)}
                className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
              >
                Continuar conversando na degustação
              </button>
            </div>
          )}
        </div>

        {ofertarCta && (
          <div className="border-t border-border bg-lime/5 p-3 text-center">
            <p className="mb-2 text-xs text-muted-foreground">
              Curtiu a amostra? A{" "}
              <span className="font-medium text-foreground">análise gratuita do seu ponto</span>{" "}
              cruza +27 fontes oficiais — saturação, demanda e viabilidade da sua região.
            </p>
            <button
              type="button"
              onClick={() => setMostrarForm(true)}
              className="rounded-md bg-lime px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-lime-glow"
            >
              Ver minha análise gratuita
            </button>
          </div>
        )}

        <form
          onSubmit={submit}
          className="flex gap-2 border-t border-border bg-card p-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] sm:p-3"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={ag.placeholder}
            disabled={carregando}
            className="min-w-0 flex-1 rounded-md border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={carregando || !input.trim()}
            className="shrink-0 rounded-md bg-lime px-3 py-2 text-sm font-semibold text-primary-foreground hover:bg-lime-glow disabled:opacity-50 sm:px-4"
          >
            Enviar
          </button>
        </form>
      </div>

      {expandido && !jornadaCollapsed && (
        <SiteJornadaAside
          id="sidebar-jornada"
          temAnalise={podeGerar || mostrarForm}
          className="hidden xl:flex"
        />
      )}

      {/* Drawers mobile / tablet — liberam a área do chat */}
      {expandido && (
        <>
          <Sheet open={agentsSheetOpen} onOpenChange={setAgentsSheetOpen}>
            <SheetContent
              id="sidebar-especialistas-sheet"
              side="left"
              className="w-[min(100%,18rem)] border-border bg-card p-0"
            >
              <SheetHeader className="sr-only">
                <SheetTitle>Especialistas</SheetTitle>
                <SheetDescription>
                  Tema sugerido — o especialista certo assume conforme sua pergunta.
                </SheetDescription>
              </SheetHeader>
              <AgentesRail
                agenteUi={agenteUi}
                idDestaque={idDestaque}
                onSelect={selectAgenteUi}
                expandido
                className="pt-2"
              />
            </SheetContent>
          </Sheet>

          <Sheet open={jornadaSheetOpen} onOpenChange={setJornadaSheetOpen}>
            <SheetContent
              id="sidebar-jornada-sheet"
              side="right"
              className="flex w-[min(100%,20rem)] flex-col gap-3 overflow-y-auto border-border bg-muted/20 p-4 pt-12"
            >
              <SheetHeader className="sr-only">
                <SheetTitle>Sua jornada</SheetTitle>
                <SheetDescription>Passos da degustação até a análise completa.</SheetDescription>
              </SheetHeader>
              <JornadaContent temAnalise={podeGerar || mostrarForm} />
            </SheetContent>
          </Sheet>
        </>
      )}

      {/* Pop-up de verificação anti-bot — PORTAL pra document.body. O Turnstile
          NÃO pode ter ancestral com transform/backdrop-filter: o DialogContent
          (shadcn) centraliza com translate-[-50%] → o challenge crashava
          (crashed_retry). Portado pro body, o widget escapa do transform do
          dialog. O blur fica como camada IRMÃ (não ancestral do widget). */}
      {verifyOpen &&
        createPortal(
          <div className="fixed inset-0 z-70 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" aria-hidden />
            <div className="relative max-w-xs space-y-3 rounded-xl border border-border bg-card p-5 text-center shadow-xl">
              <div className="flex items-center justify-center gap-2 text-sm font-medium text-foreground">
                <ShieldCheck className="h-4 w-4 text-lime" /> Confirme que você não é um robô
              </div>
              {previewDeploy && !temBypass ? (
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  Neste link de preview o Turnstile não gera token válido. Abra{" "}
                  <a href={CHAT_PRODUCTION_URL} className="text-lime underline">
                    gymsite.com.br/degustacao
                  </a>{" "}
                  ou adicione <code className="font-mono text-[10px]">?dev_token=…</code>.
                </p>
              ) : (
                <div className="flex justify-center">
                  <TurnstileWidget onToken={onVerified} />
                </div>
              )}
              <button
                type="button"
                onClick={() => setVerifyOpen(false)}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Cancelar
              </button>
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
}
