import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { CheckCircle2, Loader2, Clock, Lock, ShieldCheck, AlertTriangle, Layers, MapPin, Users, Building2, TrendingUp, Contact, FileText, Globe, Target } from "lucide-react";
import type { ComponentType, SVGProps } from "react";
import { criarAnalise, pollAnalise, type MiniRelatorio } from "@/lib/siteAgent";
import { TurnstileWidget } from "./TurnstileWidget";

export interface Prefill {
  cidade?: string; bairro?: string; uf?: string; tipoNegocio?: string;
}

// Crachás dos agentes do pipeline de análise (agents/a0..a9 no backend).
// Passam em marquee vertical enquanto o relatório é gerado.
type LucideIcon = ComponentType<SVGProps<SVGSVGElement>>;
const PIPELINE_AGENTES: { code: string; nome: string; tarefa: string; Icone: LucideIcon }[] = [
  { code: "A0", nome: "Context Builder", tarefa: "Montando o contexto · CNPJ/CNO + deep research", Icone: Layers },
  { code: "A1", nome: "GeoScout", tarefa: "Mapeando a geografia · raio, vias e polos", Icone: MapPin },
  { code: "A2", nome: "Demo Analyst", tarefa: "Analisando demografia · renda e público", Icone: Users },
  { code: "A3", nome: "Competitor Intel", tarefa: "Varrendo concorrência · academias no raio", Icone: Building2 },
  { code: "A4", nome: "Financial Estimator", tarefa: "Estimando potencial de faturamento", Icone: TrendingUp },
  { code: "A5", nome: "Contact Hunter", tarefa: "Levantando contatos do entorno", Icone: Contact },
  { code: "A7", nome: "Market Research", tarefa: "Pesquisando o mercado · fontes oficiais", Icone: Globe },
  { code: "A8", nome: "Validator", tarefa: "Validação cruzada dos dados", Icone: ShieldCheck },
  { code: "A9", nome: "Positioning Strategist", tarefa: "Estratégia de posicionamento · ERRC", Icone: Target },
  { code: "A6", nome: "Report Consolidator", tarefa: "Consolidando o relatório executivo", Icone: FileText },
];

function CrachaAgente({ code, nome, tarefa, Icone }: { code: string; nome: string; tarefa: string; Icone: LucideIcon }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-lime/25 bg-background/60 px-3 py-2.5">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-lime/10 text-lime">
        <Icone className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] tracking-wide text-lime/70">{code}</span>
          <span className="truncate text-sm font-semibold text-foreground">{nome}</span>
        </div>
        <div className="truncate text-xs text-muted-foreground">{tarefa}</div>
      </div>
      <span className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-lime" />
    </div>
  );
}

type Estado =
  | { tipo: "form" }
  | { tipo: "enviando" }
  | { tipo: "processando" }
  | { tipo: "pronto"; dados: MiniRelatorio; upsell: string }
  | { tipo: "quota_used" | "fila" | "erro" | "demorou"; msg: string };

// Persistência da análise em andamento: reload da página NÃO perde o relatório
// nem "queima" a análise gratuita — retoma o polling do mesmo relatorio_id.
const PENDING_KEY = "gs_analise_pending";
const PENDING_MAX_AGE = 30 * 60 * 1000; // 30 min
type Pending = { relatorio_id: string; access_token: string; ts: number };

function lerPending(): Pending | null {
  try {
    const raw = localStorage.getItem(PENDING_KEY);
    if (!raw) return null;
    const p = JSON.parse(raw) as Pending;
    if (!p?.relatorio_id || !p?.access_token) return null;
    if (Date.now() - (p.ts ?? 0) > PENDING_MAX_AGE) return null;
    return p;
  } catch { return null; }
}
function salvarPending(relatorio_id: string, access_token: string) {
  try { localStorage.setItem(PENDING_KEY, JSON.stringify({ relatorio_id, access_token, ts: Date.now() })); } catch { /* storage indisponível */ }
}
function limparPending() {
  try { localStorage.removeItem(PENDING_KEY); } catch { /* noop */ }
}

function useAnaliseGratuita(devToken?: string) {
  const [estado, setEstado] = useState<Estado>({ tipo: "form" });
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (pollTimer.current) clearInterval(pollTimer.current); }, []);

  function iniciarPolling(id: string, token: string) {
    salvarPending(id, token);
    setEstado({ tipo: "processando" });
    const t0 = Date.now();
    pollTimer.current = setInterval(async () => {
      if (Date.now() - t0 > 12 * 60 * 1000) {
        // Timeout do CLIENTE ≠ erro: o pipeline pode enfileirar e o relatório
        // chega por e-mail. Estado "demorou" (tranquilizador), não "erro".
        // Mantém o pending: um reload posterior ainda retoma o polling.
        clearInterval(pollTimer.current!);
        setEstado({ tipo: "demorou", msg: "Sua análise continua sendo gerada — assim que ficar pronta enviamos por e-mail. Pode fechar esta janela." });
        return;
      }
      try {
        const s = await pollAnalise(id, token);
        if (s.status === "pronto") {
          clearInterval(pollTimer.current!);
          limparPending();
          setEstado({ tipo: "pronto", dados: s.mini_relatorio, upsell: s.upsell });
        } else if (s.status === "erro") {
          clearInterval(pollTimer.current!);
          limparPending();
          setEstado({ tipo: "erro", msg: s.mensagem });
        }
      } catch { /* transitório: mantém polling */ }
    }, 10_000);
  }

  // Retoma um relatório em andamento após reload (sem re-submeter → não queima o e-mail).
  useEffect(() => {
    const p = lerPending();
    if (p) iniciarPolling(p.relatorio_id, p.access_token);
    else limparPending();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function enviar(dados: {
    nome: string; email: string; cidade: string; bairro: string;
    uf?: string; telefone?: string; tipo_negocio?: string;
  }, turnstile_token?: string) {
    setEstado({ tipo: "enviando" });
    try {
      const r = await criarAnalise({
        ...dados,
        turnstile_token: turnstile_token || undefined,
        dev_token: devToken || undefined,
      });
      if (r.status === "quota_used") return setEstado({ tipo: "quota_used", msg: r.mensagem });
      if (r.status === "fila") return setEstado({ tipo: "fila", msg: r.mensagem });
      iniciarPolling(r.relatorio_id!, r.access_token!);
    } catch (e) {
      setEstado({ tipo: "erro", msg: (e as Error).message });
    }
  }

  function reset() {
    if (pollTimer.current) clearInterval(pollTimer.current);
    limparPending();
    setEstado({ tipo: "form" });
  }

  return { estado, enviar, reset };
}

/** Form Tier 2 (gera o mini-relatório). Prefill vem do /conversar (localizacao+modelo).
 *  `devToken` = bypass dono (?dev_token= / rota /teste): sem Turnstile; backend valida. */
export function AnaliseGratuitaFlow({ prefill, devToken }: { prefill?: Prefill; devToken?: string }) {
  const { estado, enviar, reset } = useAnaliseGratuita(devToken);
  const [consent, setConsent] = useState(false);
  const [verifyOpen, setVerifyOpen] = useState(false);
  const [verifyKey, setVerifyKey] = useState(0);
  const [form, setForm] = useState({
    nome: "", email: "", whats: "",
    cidade: prefill?.cidade ?? "", bairro: prefill?.bairro ?? "", uf: prefill?.uf ?? "",
  });

  function doEnviar(token?: string) {
    enviar({
      nome: form.nome,
      email: form.email,
      telefone: form.whats || undefined,
      cidade: form.cidade.trim(),
      bairro: form.bairro.trim() || form.cidade.trim(),
      uf: form.uf.trim() || undefined,
      tipo_negocio: prefill?.tipoNegocio || "academia",
    }, token);
  }

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!consent) return;
    // Dono/dev: pula Turnstile (token vai no body; backend valida contra o secret).
    if (devToken) { doEnviar(); return; }
    // Sempre pede Turnstile fresco — token é single-use (reutilizar = 403).
    setVerifyKey((k) => k + 1);
    setVerifyOpen(true);
  };

  if (estado.tipo === "processando") {
    return (
      <div className="mt-3 rounded-lg border border-lime/40 bg-lime/10 p-5 space-y-4">
        <style>{`
          @keyframes gsPipeScroll { from { transform: translateY(0); } to { transform: translateY(-50%); } }
          .gs-pipe-track { animation: gsPipeScroll 20s linear infinite; }
          .gs-pipe-mask {
            -webkit-mask-image: linear-gradient(180deg, transparent, #000 12%, #000 88%, transparent);
            mask-image: linear-gradient(180deg, transparent, #000 12%, #000 88%, transparent);
          }
          @media (prefers-reduced-motion: reduce) { .gs-pipe-track { animation: none; } }
        `}</style>

        <div className="text-center space-y-2">
          <Loader2 className="h-8 w-8 text-lime mx-auto animate-spin" />
          <p className="text-foreground font-semibold">Gerando sua análise…</p>
          <p className="text-xs font-mono uppercase tracking-wider text-lime/70">
            Pipeline GymSite · 10 agentes trabalhando
          </p>
        </div>

        <div className="gs-pipe-mask relative h-57 overflow-hidden">
          <div className="gs-pipe-track space-y-2">
            {[...PIPELINE_AGENTES, ...PIPELINE_AGENTES].map((a, i) => (
              <CrachaAgente key={`${a.code}-${i}`} {...a} />
            ))}
          </div>
        </div>

        <p className="text-center text-sm text-muted-foreground">
          Cruzando bases públicas oficiais com nossa modelagem. Leva de 3 a 5 minutos —
          deixa esta janela aberta que o resultado aparece aqui.
        </p>
      </div>
    );
  }

  if (estado.tipo === "pronto") {
    const d = estado.dados;
    const demo = d.demografia;
    const ctx = d.contexto_mercado;
    const fmtR$ = (n: number | null | undefined) =>
      n == null ? "—" : n.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
    const fmtN = (n: number | null | undefined) =>
      n == null ? "—" : n.toLocaleString("pt-BR");

    return (
      <div className="mt-3 rounded-lg border border-lime/40 bg-lime/6 p-5 space-y-4">
        <div className="flex items-center gap-2 text-lime font-semibold">
          <CheckCircle2 className="h-5 w-5" /> Sua análise preliminar
          {d.bairro_analisado ? (
            <span className="font-normal text-xs text-muted-foreground">
              · {d.bairro_analisado}
            </span>
          ) : null}
        </div>

        <section className="space-y-2">
          <h3 className="text-xs font-bold uppercase tracking-wide text-foreground">
            Demografia do bairro
          </h3>
          <div className="grid grid-cols-1 gap-1.5 text-xs sm:grid-cols-2">
            <Stat
              label="Renda per capita"
              value={fmtR$(demo?.renda_per_capita)}
              hint={demo?.renda_per_capita_rotulo}
            />
            <Stat label="População (bairro)" value={fmtN(demo?.populacao_bairro)} />
            <Stat label="Moradores/domicílio" value={fmtN(demo?.moradores_domicilio)} />
            <Stat
              label="Público idade × sexo"
              value={demo?.publico_idade_sexo ?? "—"}
            />
          </div>
          {demo?.fonte ? (
            <p className="text-[10px] text-muted-foreground">Fonte: {demo.fonte}</p>
          ) : null}
        </section>

        <section className="space-y-2 border-t border-border/40 pt-3">
          <h3 className="text-xs font-bold uppercase tracking-wide text-foreground">
            Contexto de Mercado
          </h3>
          <div className="grid grid-cols-1 gap-1.5 text-xs sm:grid-cols-2">
            <Stat label="Renda média bairro" value={fmtR$(ctx?.renda_media_bairro)} />
            <Stat label="Gênero alvo" value={ctx?.genero_alvo ?? "—"} />
            <Stat label="Saturação" value={ctx?.saturacao ?? d.nivel_saturacao ?? "—"} />
            <Stat
              label="Concorrentes analisados"
              value={fmtN(ctx?.concorrentes_analisados ?? d.total_concorrentes)}
            />
          </div>
          {ctx?.fonte_concorrencia ? (
            <p className="text-[10px] text-muted-foreground">{ctx.fonte_concorrencia}</p>
          ) : null}
        </section>

        {estado.upsell && (
          <div className="flex items-start gap-2 rounded-md border border-lime/30 bg-background/50 p-3 text-xs text-muted-foreground">
            <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-lime" />
            <span>{estado.upsell}</span>
          </div>
        )}
      </div>
    );
  }

  if (estado.tipo === "quota_used" || estado.tipo === "fila" || estado.tipo === "demorou" || estado.tipo === "erro") {
    const icone =
      estado.tipo === "erro" ? <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto" />
      : estado.tipo === "quota_used" ? <CheckCircle2 className="h-8 w-8 text-lime mx-auto" />
      : <Clock className="h-8 w-8 text-lime mx-auto" />;
    const titulo =
      estado.tipo === "quota_used" ? "Você já usou sua análise gratuita"
      : estado.tipo === "fila" ? "Alta demanda agora"
      : estado.tipo === "demorou" ? "Sua análise está sendo gerada"
      : "Algo deu errado";
    return (
      <div className="mt-3 rounded-lg border border-border bg-card p-5 text-center space-y-3">
        {icone}
        <p className="text-foreground font-semibold">{titulo}</p>
        <p className="text-sm text-muted-foreground">{estado.msg}</p>
        {estado.tipo === "erro" && (
          <Button onClick={reset} className="bg-lime text-primary-foreground hover:bg-lime-glow font-semibold">
            Tentar novamente
          </Button>
        )}
      </div>
    );
  }

  const enviando = estado.tipo === "enviando";
  return (
    <>
    <form onSubmit={onSubmit} className="mt-3 rounded-lg border border-border bg-card p-4 space-y-3">
      <div className="flex items-center gap-2 text-xs text-lime font-medium">
        <ShieldCheck className="h-4 w-4" />
        {devToken
          ? "Sandbox dono — sem Turnstile (backend valida o token)"
          : "Última etapa — Dados protegidos pela LGPD"}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Input required placeholder="Cidade" value={form.cidade} onChange={(e) => setForm({ ...form, cidade: e.target.value })} className="bg-background" />
        <Input placeholder="Bairro" value={form.bairro} onChange={(e) => setForm({ ...form, bairro: e.target.value })} className="bg-background" />
      </div>
      <Input required placeholder="Nome completo" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} className="bg-background" />
      <Input required type="email" placeholder="E-mail corporativo" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="bg-background" />
      <Input required placeholder="WhatsApp com DDD" value={form.whats} onChange={(e) => setForm({ ...form, whats: e.target.value })} className="bg-background" />
      <label className="flex gap-2 text-xs text-muted-foreground leading-snug">
        <Checkbox checked={consent} onCheckedChange={(v) => setConsent(Boolean(v))} className="mt-0.5" />
        <span>Autorizo a GymSite Intelligence a tratar meus dados para envio do diagnóstico e contato comercial, conforme a Lei Geral de Proteção de Dados (LGPD). Posso revogar a qualquer momento.</span>
      </label>
      <Button type="submit" disabled={!consent || enviando} className="w-full bg-lime text-primary-foreground hover:bg-lime-glow font-semibold">
        {enviando ? "Enviando…" : "Gerar minha análise gratuita"}
      </Button>
    </form>

    {/* Turnstile num popup PORTADO pro body — escapa do transform do DialogContent. */}
    {verifyOpen && createPortal(
      <div className="fixed inset-0 z-70 flex items-center justify-center p-4">
        <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" aria-hidden />
        <div className="relative rounded-xl border border-border bg-card p-5 shadow-xl text-center space-y-3 max-w-xs">
          <div className="flex items-center justify-center gap-2 text-sm font-medium text-foreground">
            <ShieldCheck className="h-4 w-4 text-lime" /> Confirme que você não é um robô
          </div>
          <div className="flex justify-center">
            <TurnstileWidget
              key={verifyKey}
              onToken={(t) => {
                if (!t) return;
                setVerifyOpen(false);
                doEnviar(t);
              }}
            />
          </div>
          <button type="button" onClick={() => setVerifyOpen(false)}
            className="text-xs text-muted-foreground hover:text-foreground">
            Cancelar
          </button>
        </div>
      </div>,
      document.body,
    )}
    </>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string | null }) {
  return (
    <div className="rounded-md border border-border bg-background px-2 py-1.5">
      <div className="text-muted-foreground">{label}</div>
      <div className="text-foreground font-semibold">{value}</div>
      {hint ? <div className="text-[10px] leading-snug text-muted-foreground/90">{hint}</div> : null}
    </div>
  );
}
