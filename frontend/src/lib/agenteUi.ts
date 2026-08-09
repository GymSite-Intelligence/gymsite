import type { AgenteChat } from "@/lib/siteAgent";

/** Roteador ADK — único `agente` enviado ao POST /conversar (Opção A). */
export const AGENTE_API_ROTEADOR: AgenteChat = "degustacao";

/** Ids aceitos no rail / `?agente=` (só UI; não vão na API). */
export const AGENTES_UI: AgenteChat[] = [
  "degustacao",
  "responsavel_tecnico",
  "regulatorio",
  "arquiteto",
  "engenheiro_obra",
];

/** Normaliza query `?agente=` → card do rail. `mercado` legado vira roteador/Mercado. */
export function parseAgenteUiFromSearch(raw: string | null | undefined): AgenteChat {
  if (!raw) return AGENTE_API_ROTEADOR;
  if (raw === "mercado") return AGENTE_API_ROTEADOR;
  return (AGENTES_UI as string[]).includes(raw) ? (raw as AgenteChat) : AGENTE_API_ROTEADOR;
}
