import {
  IconeMercado,
  IconeTecnico,
  IconeRegulatorio,
  IconeArquiteto,
  IconeEngenheiro,
  type Icon,
} from '@/components/icons/gymsite-icons'

export type EspecialistaId = 'mercado' | 'tecnico' | 'regulatorio' | 'arquiteto' | 'engenheiro'

export interface Especialista {
  id: EspecialistaId
  nome: string
  especialidade: string
  Icone: Icon
  saudacao: string
  placeholder: string
}

export const ESPECIALISTAS: Especialista[] = [
  {
    id: 'mercado',
    nome: 'Mercado',
    especialidade: 'Concorrência, demografia e saturação',
    Icone: IconeMercado,
    saudacao:
      'Me diga a cidade e o bairro que você está avaliando e eu pesquiso concorrência, público e saturação em tempo real.',
    placeholder: 'Ex.: quantas academias tem no Cocó, Fortaleza?',
  },
  {
    id: 'tecnico',
    nome: 'Técnico',
    especialidade: 'Equipamentos: mix, specs e fornecedores',
    Icone: IconeTecnico,
    saudacao: 'Me diz o porte (m²) e o foco que eu monto o mix de equipamentos com fornecedor.',
    placeholder: 'Ex.: quero montar 300m² de musculação',
  },
  {
    id: 'regulatorio',
    nome: 'Regulatório',
    especialidade: 'Registro, CREF, licença e Lei 9.696',
    Icone: IconeRegulatorio,
    saudacao: 'Tire dúvidas sobre registro, CREF, licenciamento e a Lei 9.696.',
    placeholder: 'Ex.: preciso de registro no CREF?',
  },
  {
    id: 'arquiteto',
    nome: 'Arquiteto',
    especialidade: 'Projeto do espaço, zonas e acessibilidade',
    Icone: IconeArquiteto,
    saudacao: 'Pergunte sobre layout das zonas, vestiários, quantos banheiros e acessibilidade.',
    placeholder: 'Ex.: quantos banheiros para 200 alunos?',
  },
  {
    id: 'engenheiro',
    nome: 'Engenheiro',
    especialidade: 'Obra, estrutura, instalações e licenças',
    Icone: IconeEngenheiro,
    saudacao: 'Me diz se é reforma ou obra nova que eu vejo estrutura, instalações e licenças.',
    placeholder: 'Ex.: a laje aguenta área de musculação?',
  },
]

export const especialistaPadrao: Especialista = ESPECIALISTAS[0]

const TOOL_TO_ESPECIALISTA: Record<string, EspecialistaId> = {
  consultar_catalogos_equipamentos: 'tecnico',
}

export function especialistaDaMensagem(acoes?: { ferramenta: string }[]): Especialista {
  const alvo = acoes?.map((a) => TOOL_TO_ESPECIALISTA[a.ferramenta]).find(Boolean)
  return ESPECIALISTAS.find((e) => e.id === alvo) ?? especialistaPadrao
}

export function especialistaPorId(id?: EspecialistaId | null): Especialista | undefined {
  return id ? ESPECIALISTAS.find((e) => e.id === id) : undefined
}
