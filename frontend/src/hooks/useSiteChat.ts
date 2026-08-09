import { useCallback, useEffect, useRef, useState } from "react";
import {
  conversarSite,
  pollMensagens,
  isApiIndisponivelError,
  MSG_API_INDISPONIVEL,
  type AgenteChat,
  type ToolCallMsg,
} from "../lib/siteAgent";
import { AGENTE_API_ROTEADOR, parseAgenteUiFromSearch } from "../lib/agenteUi";
import { enrichMensagemComLocalizacao } from "../lib/localizacao";

export interface ChatMsg {
  role: "user" | "assistant";
  texto: string;
  sugestoes?: string[];
  agente?: AgenteChat | null;
  tool_calls?: ToolCallMsg[] | null;
}

export interface Prefill {
  cidade?: string;
  bairro?: string;
  uf?: string;
  tipoNegocio?: string;
}

/** Etapas de progresso visíveis ao usuário durante o processamento. */
export type EtapaChat = "idle" | "carregando" | "enviando" | "aguardando" | "processando";

// ─── Persistência da sessão de chat ──────────────────────────────────────────
// O projeto_id fica na URL (?pid=) e no sessionStorage.
// Isso permite:
//   1. Retomar a conversa se o usuário recarregar a página
//   2. Identificar a sessão para debug/suporte (query no backend por ID)
//   3. Compartilhar a URL com o time para investigar problemas

const CHAT_PID_KEY = "gs_chat_pid";
const CHAT_PID_PARAM = "pid";
const CHAT_FUGU_MSGS_KEY = "gs_chat_fugu_msgs";

function lerPidArmazenado(): string | null {
  if (typeof window === "undefined") return null;
  // URL tem prioridade sobre sessionStorage
  const urlPid = new URLSearchParams(window.location.search).get(CHAT_PID_PARAM);
  if (urlPid) return urlPid;
  try {
    return sessionStorage.getItem(CHAT_PID_KEY);
  } catch {
    return null;
  }
}

function salvarPid(pid: string) {
  try {
    sessionStorage.setItem(CHAT_PID_KEY, pid);
  } catch {
    /* storage indisponível */
  }
  // Adiciona ?pid= à URL sem navegação — permite debug/suporte e reload recovery
  try {
    const url = new URL(window.location.href);
    url.searchParams.set(CHAT_PID_PARAM, pid);
    window.history.replaceState(null, "", url.toString());
  } catch {
    /* noop */
  }
}

function limparPid() {
  try {
    sessionStorage.removeItem(CHAT_PID_KEY);
    sessionStorage.removeItem(CHAT_FUGU_MSGS_KEY);
  } catch {
    /* noop */
  }
  try {
    const url = new URL(window.location.href);
    url.searchParams.delete(CHAT_PID_PARAM);
    window.history.replaceState(null, "", url.toString());
  } catch {
    /* noop */
  }
}

function isFuguPid(pid?: string | null) {
  return !!pid && pid.startsWith("fugu-");
}

function lerMsgsFugu(): ChatMsg[] | null {
  try {
    const raw = sessionStorage.getItem(CHAT_FUGU_MSGS_KEY);
    if (!raw) return null;
    const arr = JSON.parse(raw) as ChatMsg[];
    return Array.isArray(arr) ? arr : null;
  } catch {
    return null;
  }
}

export function useSiteChat(opts?: { forceDevToken?: string }) {
  const [mensagens, setMensagens] = useState<ChatMsg[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [etapa, setEtapa] = useState<EtapaChat>("idle");
  const [podeGerar, setPodeGerar] = useState(false);

  // Inicializa com PID armazenado (URL ?pid= ou sessionStorage) — retoma sessão existente
  const pidInicial = typeof window !== "undefined" ? lerPidArmazenado() : null;
  const [temProjeto, setTemProjeto] = useState(!!pidInicial);
  const [prefill, setPrefill] = useState<Prefill>({});

  // Card do rail / `?agente=` — só UI (saudação, placeholder). API sempre roteador (ADR-003).
  const [agenteUi, setAgenteUi] = useState<AgenteChat>(() => {
    if (typeof window === "undefined") return AGENTE_API_ROTEADOR;
    return parseAgenteUiFromSearch(new URLSearchParams(window.location.search).get("agente"));
  });
  const projetoId = useRef<string | undefined>(pidInicial ?? undefined);
  // Bypass: prefer forceDevToken (rota /teste, disponível no SSR via search).
  // Fallback URL no client; useEffect cobre hydrate de /degustacao?dev_token=.
  const [devToken, setDevToken] = useState<string | undefined>(() => {
    if (opts?.forceDevToken) return opts.forceDevToken;
    if (typeof window !== "undefined") {
      return new URLSearchParams(window.location.search).get("dev_token") ?? undefined;
    }
    return undefined;
  });

  useEffect(() => {
    if (opts?.forceDevToken) {
      setDevToken(opts.forceDevToken);
      return;
    }
    const fromUrl = new URLSearchParams(window.location.search).get("dev_token") ?? undefined;
    if (fromUrl) setDevToken(fromUrl);
  }, [opts?.forceDevToken]);

  // Ao montar: se há um PID salvo, carrega o histórico completo da sessão anterior.
  useEffect(() => {
    if (!projetoId.current) return;
    const pid = projetoId.current;
    let cancelado = false;
    setEtapa("carregando");

    // Sessão Fugu (fallback): histórico só no sessionStorage — não existe no backend.
    if (isFuguPid(pid)) {
      const local = lerMsgsFugu();
      if (local?.length) setMensagens(local);
      else {
        projetoId.current = undefined;
        limparPid();
        setTemProjeto(false);
      }
      setEtapa("idle");
      return;
    }

    pollMensagens(pid) // sem `desde` → retorna todas as mensagens do projeto
      .then((p) => {
        if (cancelado) return;
        const historico: ChatMsg[] = p.mensagens.map((m) => ({
          role: m.role,
          texto: m.content,
          agente: m.agente,
          tool_calls: m.tool_calls ?? null,
        }));
        if (historico.length > 0) {
          setMensagens(historico);
          setPodeGerar(p.pode_gerar_relatorio);
          setPrefill({
            cidade: p.localizacao?.cidade,
            bairro: p.localizacao?.bairro,
            uf: p.localizacao?.uf,
            tipoNegocio: p.modelo_negocio?.tipo,
          });
        } else {
          // Projeto existe mas sem mensagens (improvável) — limpar para recomeçar
          projetoId.current = undefined;
          limparPid();
          setTemProjeto(false);
        }
      })
      .catch((e) => {
        // Rede/503: manter sessão (?pid=) — o usuário pode tentar de novo sem perder o projeto.
        // Só limpa PID quando a API responde de fato com erro de recurso (404 etc.).
        if (cancelado) return;
        if (isApiIndisponivelError(e)) {
          setMensagens((m) =>
            m.length ? m : [{ role: "assistant", texto: MSG_API_INDISPONIVEL }],
          );
          return;
        }
        projetoId.current = undefined;
        limparPid();
        setTemProjeto(false);
      })
      .finally(() => {
        if (!cancelado) setEtapa("idle");
      });

    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Só na montagem; projetoId.current é um ref, não estado

  // turnstileToken vem do <TurnstileWidget> visível; só exigido na 1ª msg.
  const enviar = useCallback(
    async (texto: string, turnstileToken?: string) => {
      if (!texto.trim() || carregando) return;
      setMensagens((m) => [...m, { role: "user", texto }]);
      setCarregando(true);
      setEtapa("enviando");
      // Timestamp APÓS o envio ser processado pelo backend — usando clock do servidor via
      // Date.now() local. O backend filtra `created_at >= desde`; para evitar que clock
      // skew (servidor alguns ms/s atrasado vs. cliente) exclua a resposta, zeramos
      // os milissegundos e recuamos 3 s como margem.
      const desdeMs = Date.now() - 3_000;
      const desde = new Date(Math.floor(desdeMs / 1000) * 1000).toISOString();
      try {
        const token = projetoId.current ? undefined : turnstileToken;
        // Extrai bairro/cidade/UF (com e sem acento) e anexa hint à mensagem da API —
        // a bolha do usuário continua com o texto original.
        const { mensagem, localizacao } = enrichMensagemComLocalizacao(texto);
        const { projeto_id } = await conversarSite(
          mensagem,
          projetoId.current,
          token,
          AGENTE_API_ROTEADOR,
          devToken,
          localizacao,
        );

        if (!projetoId.current) {
          // Primeira mensagem — persiste o ID para debug e reload recovery
          projetoId.current = projeto_id;
          salvarPid(projeto_id);
        } else {
          projetoId.current = projeto_id;
        }
        setTemProjeto(true); // próximas msgs sem Turnstile
        setEtapa("aguardando");

        // Turno de confirmação dispara a análise pesada (competidores via SearchAPI)
        // que pode passar de 2 min → poll até ~240s.
        // Retry para erros transitórios (5xx / network): até MAX_POLL_ERROS antes de abortar.
        const MAX_POLL_ERROS = 4;
        let errorsConsecutivos = 0;
        let etapaAtualizada = false;
        const t0 = Date.now();

        while (Date.now() - t0 < 240_000) {
          await new Promise((r) => setTimeout(r, 2500));

          // A partir de 15s mostra "processando" (IA ainda trabalhando na análise).
          if (!etapaAtualizada && Date.now() - t0 > 15_000) {
            setEtapa("processando");
            etapaAtualizada = true;
          }

          let p;
          try {
            p = await pollMensagens(projeto_id, desde);
            errorsConsecutivos = 0; // resetar contador em caso de sucesso
          } catch (pollErr: any) {
            errorsConsecutivos += 1;
            if (errorsConsecutivos >= MAX_POLL_ERROS) {
              // Abortar só depois de MAX_POLL_ERROS falhas seguidas (não na primeira)
              throw pollErr;
            }
            // Erro transitório: aguarda mais 2.5s antes de tentar novamente
            continue;
          }

          const ans = p.mensagens.filter((x) => x.role === "assistant");
          if (ans.length) {
            const ultima = ans[ans.length - 1]; // agente = quem respondeu (acende o crachá)
            setMensagens((m) => [
              ...m,
              {
                role: "assistant",
                texto: ultima.content,
                agente: ultima.agente,
                tool_calls: ultima.tool_calls ?? null,
              },
            ]);
            setPodeGerar(p.pode_gerar_relatorio);
            setPrefill({
              cidade: p.localizacao?.cidade ?? localizacao?.cidade,
              bairro: p.localizacao?.bairro ?? localizacao?.bairro,
              uf: p.localizacao?.uf ?? localizacao?.uf,
              tipoNegocio: p.modelo_negocio?.tipo,
            });
            return;
          }
        }
        setMensagens((m) => [
          ...m,
          { role: "assistant", texto: "A análise demorou mais que o esperado. Tente de novo." },
        ]);
      } catch (e: any) {
        setMensagens((m) => [
          ...m,
          {
            role: "assistant",
            texto: isApiIndisponivelError(e)
              ? MSG_API_INDISPONIVEL
              : e?.message || "Erro. Tente de novo.",
          },
        ]);
      } finally {
        setCarregando(false);
        setEtapa("idle");
      }
    },
    [carregando, devToken, mensagens],
  );

  return {
    mensagens,
    carregando,
    etapa,
    podeGerar,
    temProjeto,
    prefill,
    agenteUi,
    setAgenteUi,
    projetoId,
    enviar,
    temBypass: !!devToken,
    devToken,
  };
}
