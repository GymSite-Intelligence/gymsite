import { useEffect, useRef } from "react";
import { TURNSTILE_SITEKEY, loadTurnstileScript } from "@/lib/turnstile";

/** Widget Turnstile VISÍVEL (managed). Renderiza num <div> sem display:none —
 *  o modo invisível/escondido dá erro 400020. Devolve o token via onToken (só
 *  no sucesso). Em expiração/erro o widget se auto-reseta e pede desafio novo,
 *  então onToken nunca recebe string vazia. Token é single-use. */
export function TurnstileWidget({
  onToken,
  className,
}: {
  onToken: (token: string) => void;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const widgetId = useRef<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    loadTurnstileScript()
      .then(() => {
        const ts = (window as any).turnstile;
        if (cancelado || !ref.current || !ts || widgetId.current) return;
        widgetId.current = ts.render(ref.current, {
          sitekey: TURNSTILE_SITEKEY,
          appearance: "always",
          theme: "dark",
          action: "turnstile-spin-v2",
          callback: (t: string) => onToken(t),
          // Token expirou ou challenge falhou (crashed_retry): pede um desafio
          // novo em vez de morrer. reset() volta o widget pro estado inicial e
          // o usuário não fica travado num challenge morto.
          "expired-callback": () => { try { ts.reset(widgetId.current); } catch { /* noop */ } },
          // Retornar true sinaliza ao Turnstile pra tentar de novo automaticamente.
          "error-callback": () => { try { ts.reset(widgetId.current); } catch { /* noop */ } return true; },
        });
      })
      .catch(() => onToken(""));
    return () => {
      cancelado = true;
      const ts = (window as any).turnstile;
      if (widgetId.current && ts) { try { ts.remove(widgetId.current); } catch { /* noop */ } }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={ref} className={className} />;
}
