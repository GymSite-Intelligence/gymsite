import { useSearch } from "@tanstack/react-router";
import { EspecialistasChatShell } from "@/components/chat/EspecialistasChatShell";
import { TesteSandboxLocked } from "@/components/site/DegustacaoRouteShell";

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
    <EspecialistasChatShell
      variant="sandbox"
      formulario={abrir === "formulario"}
      devToken={token}
    />
  );
}
