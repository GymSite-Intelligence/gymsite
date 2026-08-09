import { Link } from "@tanstack/react-router";
import { Lock, ShieldCheck } from "lucide-react";
import { SiteChat } from "@/components/SiteChat";
import { AnaliseGratuitaFlow } from "@/components/site/AnaliseGratuitaFlow";
import { explorarHref } from "@/lib/degustacaoUrls";

/**
 * Layout canônico de `/degustacao` e `/teste` (desbloqueado).
 * Alterações de header/main/chat vão aqui — não duplicar nas rotas.
 *
 * @see src/routes/DegustacaoPage.tsx
 * @see src/routes/TestePage.tsx
 * @see src/lib/degustacaoUrls.ts — validateSearch compartilhado
 */

export type DegustacaoRouteVariant = "public" | "sandbox";

const COPY: Record<
  DegustacaoRouteVariant,
  { formTitle: string; formSubtitle: string }
> = {
  public: {
    formTitle: "Análise gratuita do seu ponto",
    formSubtitle:
      "Preencha e receba o retrato da sua região · bases públicas oficiais",
  },
  sandbox: {
    formTitle: "Análise (sandbox)",
    formSubtitle: "Bypass ativo — pipeline real, sem gates de lead.",
  },
};

const HEADER_CLASS =
  "flex h-14 shrink-0 items-center border-b border-border px-3 sm:h-[78px] sm:px-6";

const CHAT_VIEWPORT_CLASS =
  "flex h-[calc(100dvh-3.5rem)] min-h-0 flex-1 flex-col sm:h-[calc(100dvh-78px)]";

function DegustacaoLogoLink() {
  return (
    <a href="/" className="flex items-center gap-3">
      <img
        src="/gymsite-logo-white.png"
        alt="GymSite Intelligence"
        className="h-10 w-auto sm:h-14"
      />
    </a>
  );
}

function SandboxBadge() {
  return (
    <div className="ml-2 flex items-center gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[10px] font-medium text-amber-200 sm:ml-3 sm:px-2.5 sm:text-xs">
      <ShieldCheck className="h-3 w-3 shrink-0 sm:h-3.5 sm:w-3.5" />
      <span className="hidden sm:inline">Sandbox · sem Turnstile · sem caps</span>
      <span className="sm:hidden">Sandbox</span>
    </div>
  );
}

function DegustacaoRouteNav({ variant }: { variant: DegustacaoRouteVariant }) {
  return (
    <div className="ml-auto flex items-center gap-3 text-sm text-muted-foreground sm:gap-4">
      <Link to="/agentes" className="hover:text-foreground">
        Especialistas
      </Link>
      <a href={explorarHref()} className="hover:text-foreground">
        Explorar
      </a>
      {variant === "sandbox" ? (
        <Link to="/degustacao" className="hover:text-foreground">
          Degustação
        </Link>
      ) : null}
      <a href="/" className="hover:text-foreground">
        Início
      </a>
    </div>
  );
}

export type DegustacaoRouteShellProps = {
  variant: DegustacaoRouteVariant;
  formulario: boolean;
  /** Sandbox: bypass Turnstile/caps no chat e formulário. */
  devToken?: string;
};

export function DegustacaoRouteShell({
  variant,
  formulario,
  devToken,
}: DegustacaoRouteShellProps) {
  const copy = COPY[variant];

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className={HEADER_CLASS}>
        <DegustacaoLogoLink />
        {variant === "sandbox" ? <SandboxBadge /> : null}
        <DegustacaoRouteNav variant={variant} />
      </header>

      <main className="flex min-h-0 flex-1 flex-col">
        {formulario ? (
          <div className="mx-auto w-full max-w-2xl flex-1 overflow-y-auto px-4 py-6 sm:px-5 sm:py-8">
            <h1 className="mb-1 font-display text-xl font-semibold">
              {copy.formTitle}
            </h1>
            <p className="mb-6 text-sm text-muted-foreground">
              {copy.formSubtitle}
            </p>
            <AnaliseGratuitaFlow devToken={devToken} />
          </div>
        ) : (
          <div className={CHAT_VIEWPORT_CLASS}>
            <SiteChat
              expandido
              fullPage
              forceDevToken={devToken}
            />
          </div>
        )}
      </main>
    </div>
  );
}

/** Gate `/teste` sem `?dev_token=` — header mínimo alinhado ao shell. */
export function TesteSandboxLocked() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className={HEADER_CLASS}>
        <DegustacaoLogoLink />
      </header>
      <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center gap-4 px-5 text-center">
        <Lock className="h-10 w-10 text-lime" />
        <h1 className="font-display text-xl font-semibold">Sandbox trancado</h1>
        <p className="text-sm text-muted-foreground">
          Esta rota é só pra teste interno. Abra com{" "}
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground">
            /teste?dev_token=…
          </code>{" "}
          (mesmo valor de{" "}
          <code className="font-mono text-xs">SITE_CHAT_BYPASS_TOKEN</code> no
          backend).
        </p>
        <Link to="/degustacao" className="text-sm text-lime hover:underline">
          Ir pra degustação pública →
        </Link>
      </main>
    </div>
  );
}
