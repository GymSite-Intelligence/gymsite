export const GYMSITE_PALETTE = {
  bg: '#13161b',
  card: '#181c22',
  card2: '#1c212a',
  lime: '#84cc01',
  fg: '#eef1f4',
  muted: '#9aa4b0',
  border: '#2b323d',
} as const

/** Copy do consultor logado (app). Regras de cap/monetização vêm depois do MVP — ver MODELO_NEGOCIO.md */
export const CONSULTOR_COPY = {
  tagline: 'CONSULTOR · ANÁLISE EM TEMPO REAL',
  miniCards: [
    { kicker: 'Projeto salvo', detail: 'Conversa vinculada ao bairro que você está avaliando' },
    { kicker: 'Fonte carimbada', detail: 'Valor · base · fonte · janela em cada dado citado' },
    { kicker: 'Relatório formal', detail: 'Gere o dossiê quando os dados do projeto fecharem' },
  ],
} as const

export const DEGUSTACAO_COPY = {
  tagline: 'DEGUSTAÇÃO · 5 ESPECIALISTAS',
  h1: 'Escolha o especialista. Faça sua pergunta.',
  p: 'Cinco agentes, cada um com sua especialidade. Pergunte direto pra quem entende do assunto — concorrência, equipamentos, obra, projeto ou regulatório — e receba uma amostra da inteligência que alimenta o relatório completo.',
  badgesAtritoZero: [
    '1 pergunta grátis por especialista',
    'dados com fonte carimbada',
    'sem cadastro pra começar',
  ],
  metodologia: {
    titulo: 'Cada pergunta afina o especialista',
    texto:
      'As dúvidas mais frequentes viram treino dos próprios agentes — a roda de aprendizado. Perguntas são anonimizadas antes de qualquer uso (LGPD); nada que te identifique entra no treino.',
  },
  passosJornada: [
    {
      passo: '01',
      titulo: 'Pergunte ao especialista',
      texto: 'Escolha o agente pela especialidade e mande sua dúvida real sobre abrir/operar a academia.',
    },
    {
      passo: '02',
      titulo: 'Veja quem responde',
      texto:
        'Cada resposta traz o crachá de quem falou. Se a dúvida for de outra área, o especialista certo assume — a passagem de bastão.',
    },
    {
      passo: '03',
      titulo: 'Peça a análise completa',
      texto: 'Gostou da amostra? O relatório de viabilidade da sua região cruza +27 fontes oficiais.',
    },
  ],
  footer: 'GymSite Intelligence · degustação dos agentes consultores · dados de bases públicas oficiais',
} as const

export const HANDOFF_COPY = {
  prefixo: 'Assunto alterado.',
  template: (anterior: string, novo: string) =>
    `${anterior} passou a palavra para ${novo}.`,
} as const

export const AGENTES_DEGUSTACAO_META = [
  {
    id: 'mercado' as const,
    nome: 'Mercado',
    especialidade: 'Concorrência, demografia e saturação do bairro',
    exemploPergunta: 'quantas academias tem no Cocó, Fortaleza?',
    contextoPesquisas: [
      'Contexto de mercado',
      'Demografia (IBGE)',
      'Concorrentes',
      'Reviews e dores',
      'Oferta e serviços',
      'Pontos comerciais',
      'Viabilidade financeira',
    ],
  },
  {
    id: 'tecnico' as const,
    nome: 'Técnico',
    especialidade: 'Equipamentos: mix, specs e fornecedores',
    exemploPergunta: 'que mix pra 300 m² de musculação?',
  },
  {
    id: 'regulatorio' as const,
    nome: 'Regulatório',
    especialidade: 'CREF, registro, licença e Lei 9.696',
    exemploPergunta: 'preciso de registro no CREF?',
  },
  {
    id: 'arquiteto' as const,
    nome: 'Arquiteto',
    especialidade: 'Projeto do espaço, zonas e acessibilidade',
    exemploPergunta: 'quantos banheiros pra 200 alunos?',
  },
  {
    id: 'engenheiro' as const,
    nome: 'Engenheiro',
    especialidade: 'Obra, estrutura, instalações e licenças',
    exemploPergunta: 'a laje aguenta peso livre?',
  },
] as const
