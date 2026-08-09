import { resolveSiteAgentBases } from "@/lib/siteAgentBases"

/**
 * Bases da API site-agent (chat isca).
 * `VITE_DEGUSTACAO_PROVIDER=cloudflare` → same-origin Worker (ignora `VITE_API_BASE`).
 * Sem provider → `VITE_API_BASE` / api.getgymsite.com.br (A0–A9).
 */

export function isCfDegustacaoProvider(): boolean {
  return String(import.meta.env.VITE_DEGUSTACAO_PROVIDER ?? "").toLowerCase() === "cloudflare";
}

function parseApiBases(): string[] {
  const env = import.meta.env;
  return resolveSiteAgentBases({
    provider: String(env.VITE_DEGUSTACAO_PROVIDER ?? ""),
    viteApiBase: String(env.VITE_API_BASE ?? ""),
    viteApiFallback: String(env.VITE_API_FALLBACK_BASE ?? ""),
    viteApiBases: String(env.VITE_API_BASES ?? ""),
    origin: typeof window !== "undefined" ? window.location.origin : "https://www.gymsite.com.br",
  });
}

const API_BASES = parseApiBases();
/** Índice sticky da base que está respondendo nesta sessão. */
let apiBaseIdx = 0;

export function getApiBase(): string {
  return API_BASES[apiBaseIdx] ?? API_BASES[0];
}

/** @deprecated use getApiBase() — mantido p/ imports legados / debug */
export const API_BASE = API_BASES[0];

/** Mensagem amigável quando a API está fora (503) ou o browser engole o fetch
 *  ("Load failed" no Safari / "Failed to fetch" no Chrome — tipicamente CORS
 *  ausente na página de erro do gateway). */
export const MSG_API_INDISPONIVEL =
  "Serviço temporariamente indisponível. Aguarde alguns segundos e tente de novo.";

/** Erro de rede/indisponibilidade — o front NÃO deve apagar a sessão (?pid=). */
export class ApiIndisponivelError extends Error {
  readonly name = "ApiIndisponivelError";
  constructor(message = MSG_API_INDISPONIVEL) {
    super(message);
  }
}

export function isApiIndisponivelError(e: unknown): boolean {
  if (e instanceof ApiIndisponivelError) return true;
  const msg = String((e as Error)?.message ?? e ?? "").toLowerCase();
  return (
    msg.includes("load failed") ||
    msg.includes("failed to fetch") ||
    msg.includes("networkerror") ||
    msg.includes("network request failed") ||
    msg.includes("indisponível") ||
    msg.includes("indisponivel")
  );
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function isGatewayDown(status: number) {
  return [502, 503, 504].includes(status);
}

/**
 * fetch na API com:
 * 1) retry curto na base atual (cold start)
 * 2) failover para a próxima base (mirror site-agent) se a primária continuar 503/rede
 * 3) rejeita 2xx "fantasma" (HTML / texto "I'm alive") — stub de health
 */
async function fetchApi(
  path: string,
  init?: RequestInit,
  opts?: { tentativasPorBase?: number; baseDelayMs?: number },
): Promise<Response> {
  const tentativasPorBase = opts?.tentativasPorBase ?? 2;
  const baseDelayMs = opts?.baseDelayMs ?? 1200;
  const ordem = [
    ...API_BASES.slice(apiBaseIdx),
    ...API_BASES.slice(0, apiBaseIdx),
  ];
  let ultimoErro: unknown;
  let ultimoStatus: number | undefined;

  for (let b = 0; b < ordem.length; b++) {
    const base = ordem[b];
    for (let i = 0; i < tentativasPorBase; i++) {
      try {
        const r = await fetch(`${base}${path}`, init);
        if (isGatewayDown(r.status)) {
          ultimoStatus = r.status;
          if (i < tentativasPorBase - 1) {
            await sleep(baseDelayMs * 2 ** i);
            continue;
          }
          break; // próxima base
        }

        const ct = r.headers.get("content-type") ?? "";
        const pareceApi =
          ct.includes("application/json") ||
          ct.includes("+json") ||
          r.status === 403 ||
          r.status === 401;
        // Pages sem secrets devolve 500 text/plain — tenta mirror Worker.
        if (r.status >= 500 && !pareceApi) {
          ultimoStatus = r.status;
          break;
        }

        // Stub Render / página HTML: 2xx sem JSON → não sticky, tenta fallback
        if (r.ok && !pareceApi) {
          // Lê um sniffer do body sem consumir: clone
          const sniff = (await r.clone().text()).trim().slice(0, 80).toLowerCase();
          if (
            sniff === "i'm alive" ||
            sniff.startsWith("<!") ||
            sniff.startsWith("<html") ||
            (!sniff.startsWith("{") && !sniff.startsWith("["))
          ) {
            ultimoStatus = r.status;
            break; // próxima base
          }
        }

        // API de verdade (JSON ou 401/403 de negócio): sticky
        apiBaseIdx = API_BASES.indexOf(base);
        if (apiBaseIdx < 0) apiBaseIdx = 0;
        return r;
      } catch (e) {
        ultimoErro = e;
        if (i < tentativasPorBase - 1) {
          await sleep(baseDelayMs * 2 ** i);
          continue;
        }
      }
    }
  }

  if (ultimoStatus && isGatewayDown(ultimoStatus)) throw new ApiIndisponivelError();
  if (isApiIndisponivelError(ultimoErro) || ultimoErro instanceof TypeError) {
    throw new ApiIndisponivelError();
  }
  throw ultimoErro instanceof Error ? ultimoErro : new ApiIndisponivelError();
}

// ─── Tier 1: chat de degustação (ASSÍNCRONO) ─────────────────────────────────
// O engine leva 30-90s; rodar inline estourava o fetch/proxy ("Failed to fetch").
// Agora /conversar ENFILEIRA e responde na hora com projeto_id; a resposta vem
// por polling em /conversar/{id}/mensagens.

export interface ConversarLoc {
  cidade?: string;
  bairro?: string;
  uf?: string;
}

export interface ConcorrenteItem {
  nome: string;
  endereco?: string | null;
  distancia_m?: number | null;
  rating?: number | null;
  avaliacoes?: number | null;
  place_id?: string;
}

export interface BuscarConcorrentesResult {
  ferramenta?: string;
  query?: string;
  tipo_negocio?: string;
  total_concorrentes: number;
  nivel_saturacao?: string;
  exclude_aplicado?: string[];
  maps_smoke_url?: string;
  truncado?: boolean;
  concorrentes: ConcorrenteItem[];
  erro?: string;
}

export interface ToolCallMsg {
  ferramenta: string;
  status?: string;
  resumo?: string;
  resultado?: BuscarConcorrentesResult | Record<string, unknown>;
}

/** Fonte recuperada pelo RAG Eros (`consultar_eros_*` → polling `sources`). */
export interface ErosSource {
  chunk_id: string;
  score: number;
  nome_academia?: string | null;
  modalidade?: string | null;
  source_ref?: string | null;
  municipios?: string[] | null;
}

export interface PollMsg {
  role: "user" | "assistant";
  content: string;
  created_at: string;
  agente?: AgenteChat | null;
  tool_calls?: ToolCallMsg[] | null;
  sources?: ErosSource[] | null;
}

export interface PollResp {
  // `agente` = quem PRODUZIU a resposta (id do backend). Com roteador, só se sabe após o turno.
  mensagens: PollMsg[];
  status: string;
  pode_gerar_relatorio: boolean;
  localizacao: ConversarLoc;
  modelo_negocio: { tipo?: string };
}

/** Último `buscar_concorrentes` ok nas msgs (fail-closed se sem resultado). */
export function extrairConcorrentes(
  mensagens: { tool_calls?: ToolCallMsg[] | null }[],
): BuscarConcorrentesResult | null {
  for (let i = mensagens.length - 1; i >= 0; i--) {
    const calls = mensagens[i].tool_calls;
    if (!calls?.length) continue;
    for (let j = calls.length - 1; j >= 0; j--) {
      const c = calls[j];
      if (c.ferramenta !== "buscar_concorrentes" || c.status === "erro") continue;
      const r = c.resultado;
      if (!r || typeof r !== "object") continue;
      if (!("total_concorrentes" in r) || !("concorrentes" in r)) continue;
      return r as BuscarConcorrentesResult;
    }
  }
  return null;
}

export interface PlantaZona {
  nome: string;
  area_m2?: number;
  bbox_m?: Record<string, number>;
}

export interface PlantaLayoutResult {
  tipo?: string;
  preset?: string;
  dimensoes_m?: {
    comprimento: number;
    largura: number;
    area_informada_m2?: number;
    area_desenhada_m2?: number;
  };
  fluxo?: string;
  zonas?: PlantaZona[];
  svg?: string;
  aviso?: string;
  erro?: string;
  fonte?: string;
}

/** Último `gerar_planta_layout_zonas` ok na mensagem. */
export function extrairPlantaLayout(
  mensagens: { tool_calls?: ToolCallMsg[] | null }[],
): PlantaLayoutResult | null {
  for (let i = mensagens.length - 1; i >= 0; i--) {
    const calls = mensagens[i].tool_calls;
    if (!calls?.length) continue;
    for (let j = calls.length - 1; j >= 0; j--) {
      const c = calls[j];
      if (c.ferramenta !== "gerar_planta_layout_zonas" || c.status === "erro") continue;
      const r = c.resultado;
      if (!r || typeof r !== "object") continue;
      if (!("zonas" in r) && !("svg" in r) && !("erro" in r)) continue;
      return r as PlantaLayoutResult;
    }
  }
  return null;
}

// Agentes de chat selecionáveis na landing → id no backend.
// `mercado` não é selecionável na lateral (o card Mercado manda `degustacao` = roteador),
// mas VOLTA no polling como autor quando o roteador entrega ao especialista de Mercado.
export type AgenteChat =
  | "degustacao"
  | "mercado"
  | "responsavel_tecnico"
  | "regulatorio"
  | "arquiteto"
  | "engenheiro_obra";

/** Extrai a mensagem real de um erro do backend (JSON {detail|message|error} ou
 *  texto cru), em vez de descartar o corpo e mostrar só o status. */
async function erroDaResposta(r: Response, fallback: string): Promise<string> {
  if ([502, 503, 504].includes(r.status)) return MSG_API_INDISPONIVEL;
  try {
    const ct = r.headers.get("content-type") ?? "";
    if (ct.includes("application/json")) {
      const j = await r.json();
      const msg = j?.detail ?? j?.message ?? j?.error;
      if (msg) return typeof msg === "string" ? msg : JSON.stringify(msg);
    } else {
      const t = (await r.text()).trim();
      // Páginas HTML de gateway (503 Cloud Run / CF) — não vazar markup pro chat
      if (t && !t.startsWith("<") && !t.toLowerCase().includes("<!doctype")) {
        return t.slice(0, 300);
      }
    }
  } catch {
    /* corpo vazio/ilegível → usa fallback */
  }
  return fallback;
}

/** Enfileira a mensagem. turnstile_token só na 1ª (sem projeto_id).
 *  Na degustação pública o front envia sempre `agente=degustacao` (roteador); ver ADR-003.
 *  `devToken` = bypass anti-bot do dono/dev (validado no backend contra o secret). */
export async function conversarSite(
  mensagem: string,
  projetoId?: string,
  turnstileToken?: string,
  agente: AgenteChat = "degustacao",
  devToken?: string,
  localizacao?: ConversarLoc,
): Promise<{ projeto_id: string; status: string }> {
  let r: Response;
  try {
    r = await fetchApi("/api/site-agent/conversar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mensagem,
        projeto_id: projetoId,
        turnstile_token: turnstileToken,
        agente,
        dev_token: devToken,
        // Hint opcional: o backend ignora se ainda não consumir o campo.
        ...(localizacao && (localizacao.bairro || localizacao.cidade || localizacao.uf)
          ? { localizacao }
          : {}),
      }),
    });
  } catch (e) {
    if (isApiIndisponivelError(e) || e instanceof TypeError) throw new ApiIndisponivelError();
    throw e;
  }
  if (r.status === 403) throw new Error("Verificação anti-bot falhou. Recarregue a página.");
  if (isGatewayDown(r.status)) throw new ApiIndisponivelError();
  if (!r.ok) throw new Error(await erroDaResposta(r, `Erro ${r.status} ao enviar.`));
  return r.json();
}

/** Polling das mensagens do projeto. desde = ISO do envio (só mensagens novas). */
export async function pollMensagens(projetoId: string, desde?: string): Promise<PollResp> {
  const path =
    `/api/site-agent/conversar/${projetoId}/mensagens` +
    (desde ? `?desde=${encodeURIComponent(desde)}` : "");
  let r: Response;
  try {
    r = await fetchApi(path, undefined, { tentativasPorBase: 2, baseDelayMs: 1000 });
  } catch (e) {
    if (isApiIndisponivelError(e) || e instanceof TypeError) throw new ApiIndisponivelError();
    throw e;
  }
  if (isGatewayDown(r.status)) throw new ApiIndisponivelError();
  if (!r.ok) throw new Error(await erroDaResposta(r, `Erro ${r.status} no polling.`));
  return r.json();
}

// ─── Tier 2: geração do mini-relatório ────────────────────────────────────────

export interface AnaliseResp {
  status: "processando" | "quota_used" | "fila";
  relatorio_id?: string;
  access_token?: string;
  eta_min?: number;
  mensagem: string;
}

export interface ExtrasTeaser {
  bairro_analisado: string | null;
  dor_top: { dor: string | null; mencoes: number | null } | null;
  dores_total: number | null;
  brechas_amostra: string[] | null;
  brechas_total: number | null;
  entrantes_90d_total: number | null;
  aluguel_m2: { min: number | null; max: number | null; mediana: number | null } | null;
  bairro_alternativo_motivo: string | null;
  payback_mid_meses: number | null;
}

export interface DemografiaSecao {
  renda_per_capita: number | null;
  renda_per_capita_rotulo: string | null;
  populacao_bairro: number | null;
  moradores_domicilio: number | null;
  publico_idade_sexo: string | null;
  fonte: string | null;
}

export interface ContextoMercadoSecao {
  renda_media_bairro: number | null;
  genero_alvo: string | null;
  saturacao: string | null;
  concorrentes_analisados: number | null;
  fonte_concorrencia: string | null;
}

export interface MiniRelatorio {
  demografia?: DemografiaSecao | null;
  contexto_mercado?: ContextoMercadoSecao | null;
  bairro_analisado?: string | null;
  veredito: string | null;
  resumo_executivo: string | null;
  nivel_saturacao: string | null;
  score_bairro: number | null;
  total_concorrentes: number | null;
  rating_medio_concorrentes: number | null;
  modelo_recomendado: string | null;
  top_concorrentes: { nome: string; bairro_concorrente: string; rating_oficial: number }[];
  extras?: ExtrasTeaser | null;
}

export type StatusAnalise =
  | { status: "processando"; eta_min?: number }
  | { status: "pronto"; mini_relatorio: MiniRelatorio; upsell: string }
  | { status: "erro"; mensagem: string };

/** Release Tier 2 (form) → gera o relatório (entitlement 1/email).
 *  `dev_token` = bypass anti-bot/caps do dono (validado no backend; opcional). */
export async function criarAnalise(payload: {
  nome: string;
  email: string;
  telefone?: string;
  cidade: string;
  bairro: string;
  uf?: string;
  tipo_negocio?: string;
  turnstile_token?: string;
  dev_token?: string;
  utm_source?: string;
}): Promise<AnaliseResp> {
  let r: Response;
  try {
    r = await fetchApi("/api/site-agent/analise", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    if (isApiIndisponivelError(e) || e instanceof TypeError) throw new ApiIndisponivelError();
    throw e;
  }
  if (isGatewayDown(r.status)) throw new ApiIndisponivelError();
  if (!r.ok && r.status !== 200) throw new Error(`Erro ${r.status} ao gerar análise.`);
  return r.json();
}

/** Polling do mini-relatório. Tipado (StatusAnalise) p/ o consumer ter upsell. */
export async function pollAnalise(relatorioId: string, token: string): Promise<StatusAnalise> {
  let r: Response;
  try {
    r = await fetchApi(
      `/api/site-agent/analise/${relatorioId}?token=${encodeURIComponent(token)}`,
      undefined,
      { tentativasPorBase: 2, baseDelayMs: 1000 },
    );
  } catch (e) {
    if (isApiIndisponivelError(e) || e instanceof TypeError) throw new ApiIndisponivelError();
    throw e;
  }
  if (isGatewayDown(r.status)) throw new ApiIndisponivelError();
  if (!r.ok) throw new Error(`Erro ${r.status} no polling.`);
  return r.json();
}
