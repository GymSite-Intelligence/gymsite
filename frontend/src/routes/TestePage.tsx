import { useSearch } from "@tanstack/react-router";
import {
  DegustacaoRouteShell,
  TesteSandboxLocked,
} from "@/components/site/DegustacaoRouteShell";

/**
 * Sandbox dono/dev — mesmo shell que `/degustacao`, bypass Turnstile/caps
 * quando `?dev_token=` bate com `SITE_CHAT_BYPASS_TOKEN` no backend.
 */
export function TestePage() {
  const { dev_token, abrir } = useSearch({ from: "/teste" });
  const token = dev_token?.trim();

  if (!token) {
    return <TesteSandboxLocked />;
  }

  return (
    <DegustacaoRouteShell
      variant="sandbox"
      formulario={abrir === "formulario"}
      devToken={token}
    />
  );
}
