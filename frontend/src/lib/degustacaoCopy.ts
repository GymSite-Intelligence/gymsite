/**
 * Degustação pública (landing `/degustacao`).
 *
 * NÃO é cap "1 pergunta por especialista".
 * Modelo: trilha em 3 passos (passosJornada) + roteador ADK na API (ADR-003).
 * O rail/`?agente=` só orientam a UI; POST sempre `agente=degustacao`.
 * CTA da análise completa após ~3 turnos ou quando localização fecha (`podeGerar`).
 *
 * `/agentes` = catálogo deprecado que só linka `/degustacao?agente=<id>`.
 */
export const DEGUSTACAO_COPY = {
  tagline: "DEGUSTAÇÃO · 5 ESPECIALISTAS",
  subtitle: "Trilha em 3 passos · uma região por vez",
  badgesAtritoZero: [
    "uma região por vez — sem comparar bairros",
    "dados com fonte carimbada",
    "trilha: pergunta → bastão → análise completa",
  ],
  miniCardKickers: ["Uma região", "Fonte carimbada", "Trilha 3 passos"] as const,
  metodologia: {
    titulo: "Cada pergunta afina o especialista",
    texto:
      "As dúvidas mais frequentes viram treino dos próprios agentes — a roda de aprendizado. Perguntas são anonimizadas antes de qualquer uso (LGPD); nada que te identifique entra no treino.",
  },
  passosJornada: [
    {
      passo: "01",
      titulo: "Sugira o tema da pergunta",
      texto:
        "Escolha o card que mais combina com sua dúvida (mercado, CREF, obra…). O roteador encaminha ao especialista certo.",
    },
    {
      passo: "02",
      titulo: "Veja quem responde",
      texto:
        "Cada resposta traz o crachá de quem falou. Se a dúvida for de outra área, o especialista certo assume — a passagem de bastão.",
    },
    {
      passo: "03",
      titulo: "Peça a análise completa",
      texto:
        "Gostou da amostra? O relatório de viabilidade da sua região cruza +27 fontes públicas oficiais.",
    },
  ],
  footer:
    "GymSite Intelligence · degustação dos agentes consultores · dados de bases públicas oficiais",
} as const;

export const MERCADO_CONTEXTO_PESQUISAS = [
  "Contexto de mercado",
  "Demografia (IBGE)",
  "Concorrentes",
  "Reviews e dores",
  "Oferta e serviços",
  "Pontos comerciais",
  "Viabilidade financeira",
] as const;

/** 429 cap do chat — backend `site_agent._cap_chat_estourado`. */
const CAP_DEGUSTACAO_MARKERS = [
  "já usou a degustação de hoje",
  "chegou ao limite da degustação",
  "já fez sua pergunta pra esse especialista hoje",
] as const;

export function isDegustacaoCapTexto(texto: string): boolean {
  const t = texto.toLowerCase();
  return CAP_DEGUSTACAO_MARKERS.some((m) => t.includes(m));
}
