import type { ComponentType, SVGProps } from "react";
import { IconeDados, IconeContabilidade, IconeTecnico, IconeConhecimento, IconeFinanceiro } from "./gymsite-icons";
import type { AgenteChat } from "@/lib/siteAgent";

// Ícones robôs line-art custom (gymsite-icons.tsx). Textos trocam no chat
// conforme o agente selecionado.
type IconeComp = ComponentType<SVGProps<SVGSVGElement> & { className?: string }>;

export interface AgenteLanding {
  id: AgenteChat;
  nome: string;
  especialidade: string;
  Icone: IconeComp;
  img: string;            // mascote da marca (public/agentes) — usado no rail e no crachá
  saudacao: string;
  placeholder: string;
  exemplo: string;
}

export const AGENTES_LANDING: AgenteLanding[] = [
  {
    id: "degustacao",
    nome: "Mercado",
    especialidade: "Concorrência, demografia e saturação",
    Icone: IconeDados,
    img: "/agentes/mercado.png",
    saudacao: "Pergunte sobre concorrência, perfil de moradores ou saturação do bairro onde quer abrir.",
    placeholder: "Ex.: quantas academias tem no Cocó, Fortaleza, CE?",
    exemplo: "quantas academias tem no Cocó, Fortaleza, CE?",
  },
  {
    id: "responsavel_tecnico",
    nome: "Técnico",
    especialidade: "Equipamentos: mix, specs e fornecedores",
    Icone: IconeTecnico,
    img: "/agentes/tecnico.png",
    saudacao: "Me diz o porte (m²) e o foco que eu monto o mix de equipamentos com fornecedor.",
    placeholder: "Ex.: quero montar 300m² de musculação",
    exemplo: "quero montar 300m² de musculação",
  },
  {
    id: "regulatorio",
    nome: "Regulatório",
    especialidade: "Registro, CREF, licença e Lei 9.696",
    Icone: IconeContabilidade,
    img: "/agentes/regulatorio.png",
    saudacao: "Tire dúvidas sobre registro, CREF, licenciamento e a Lei 9.696.",
    placeholder: "Ex.: preciso de registro no CREF?",
    exemplo: "preciso de registro no CREF?",
  },
  {
    id: "arquiteto",
    nome: "Arquiteto",
    especialidade: "Projeto do espaço, zonas e acessibilidade",
    Icone: IconeConhecimento,
    img: "/agentes/arquiteto.png",
    saudacao: "Pergunte sobre layout das zonas, vestiários, quantos banheiros e acessibilidade.",
    placeholder: "Ex.: quantos banheiros para 200 alunos?",
    exemplo: "quantos banheiros para 200 alunos?",
  },
  {
    id: "engenheiro_obra",
    nome: "Engenheiro",
    especialidade: "Obra, estrutura, instalações e licenças",
    Icone: IconeFinanceiro,
    img: "/agentes/engenheiro.png",
    saudacao: "Me diz se é reforma ou obra nova que eu vejo estrutura, instalações e licenças.",
    placeholder: "Ex.: a laje aguenta área de musculação?",
    exemplo: "a laje aguenta área de musculação?",
  },
];

export const agentePadrao = AGENTES_LANDING[0];

/** Id do AUTOR da resposta (vindo do polling) → visual do crachá.
 *  - `mercado` = o ESPECIALISTA de Mercado respondeu → card Mercado (que tem id `degustacao`).
 *  - `degustacao` = o ROTEADOR (GymSiteSite) respondeu ele mesmo (ex.: pergunta de desambiguação
 *    antes de rotear). NÃO é o especialista Mercado — não mostra crachá de especialista (evita
 *    rotular "documentação de obra" como Mercado). */
export function crachaDoAgente(id?: string | null): AgenteLanding | undefined {
  if (!id || id === "degustacao") return undefined;
  const alvo = id === "mercado" ? "degustacao" : id;
  return AGENTES_LANDING.find((a) => a.id === alvo);
}
