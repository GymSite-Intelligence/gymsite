/** Resolve base(s) do chat isca (`/api/site-agent/*`). Sem misturar A0–A9. */

export function resolveSiteAgentBases(opts: {
  provider?: string;
  viteApiBase?: string;
  viteApiFallback?: string;
  viteApiBases?: string;
  origin?: string;
}): string[] {
  const provider = (opts.provider ?? "").toLowerCase();
  const fallback = (opts.viteApiFallback ?? "").trim().replace(/\/$/, "");

  if (provider === "cloudflare") {
    const primary = (
      (opts.origin ?? "").trim().replace(/\/$/, "") || "https://gymsite.com.br"
    );
    return [primary];
  }

  const lista = (opts.viteApiBases ?? "")
    .split(",")
    .map((s) => s.trim().replace(/\/$/, ""))
    .filter(Boolean);
  if (lista.length) return [...new Set(lista)];

  const primary = (
    (opts.viteApiBase ?? "").trim() || "https://api.getgymsite.com.br"
  ).replace(/\/$/, "");
  return fallback && fallback !== primary ? [primary, fallback] : [primary];
}
