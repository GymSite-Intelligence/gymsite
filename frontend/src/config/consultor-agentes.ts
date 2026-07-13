import {
  IconeMercado,
  IconeTecnico,
  IconeRegulatorio,
  IconeArquiteto,
  IconeEngenheiro,
  type Icon,
} from '@/components/icons/gymsite-icons'
import { AGENTES_DEGUSTACAO_META } from '@/config/gymsite-design-system'
import { uiIdFromApi } from '@/config/site-agent-map'

export type EspecialistaId = 'mercado' | 'tecnico' | 'regulatorio' | 'arquiteto' | 'engenheiro'

const COPY_BY_ID = Object.fromEntries(AGENTES_DEGUSTACAO_META.map((a) => [a.id, a])) as Record<
  EspecialistaId,
  (typeof AGENTES_DEGUSTACAO_META)[number]
>

export interface Especialista {
  id: EspecialistaId
  nome: string
  especialidade: string
  exemploPergunta: string
  Icone: Icon
  saudacao: string
  placeholder: string
}

const ICONES: Record<EspecialistaId, Icon> = {
  mercado: IconeMercado,
  tecnico: IconeTecnico,
  regulatorio: IconeRegulatorio,
  arquiteto: IconeArquiteto,
  engenheiro: IconeEngenheiro,
}

const SAUDACOES: Record<EspecialistaId, string> = {
  mercado:
    'Me diga a cidade e o bairro que você está avaliando e eu pesquiso concorrência, público e saturação em tempo real.',
  tecnico: 'Me diz o porte (m²) e o foco que eu monto o mix de equipamentos com fornecedor.',
  regulatorio: 'Tire dúvidas sobre registro, CREF, licenciamento e a Lei 9.696.',
  arquiteto: 'Pergunte sobre layout das zonas, vestiários, quantos banheiros e acessibilidade.',
  engenheiro: 'Me diz se é reforma ou obra nova que eu vejo estrutura, instalações e licenças.',
}

export const ESPECIALISTAS: Especialista[] = AGENTES_DEGUSTACAO_META.map((meta) => ({
  id: meta.id,
  nome: meta.nome,
  especialidade: meta.especialidade,
  exemploPergunta: meta.exemploPergunta,
  Icone: ICONES[meta.id],
  saudacao: SAUDACOES[meta.id],
  placeholder: `Ex.: ${meta.exemploPergunta}`,
}))

export const especialistaPadrao: Especialista = ESPECIALISTAS[0]

const TOOL_TO_ESPECIALISTA: Record<string, EspecialistaId> = {
  consultar_catalogos_equipamentos: 'tecnico',
  consultar_catalogo_equipamentos: 'tecnico',
  dimensionar_cardio_por_pico: 'tecnico',
  dimensionar_musculacao: 'tecnico',
  calcular_equipamentos_por_area: 'tecnico',
  consultar_base_regulatoria: 'regulatorio',
  consultar_engenharia_obra: 'engenheiro',
  calcular_sanitarios_por_lotacao: 'arquiteto',
  buscar_concorrentes: 'mercado',
  analisar_demografia: 'mercado',
  pesquisar_contexto_mercado: 'mercado',
  buscar_pontos_comerciais: 'mercado',
  estimar_investimento: 'mercado',
  consultar_base_mercado: 'mercado',
  pesquisar_concorrentes: 'mercado',
  analisar_reviews_e_dores: 'mercado',
  mapear_oferta_e_servicos: 'mercado',
}

export function especialistaDaMensagem(
  acoes?: { ferramenta: string }[],
  agenteId?: string | null,
): Especialista {
  const fromApi = uiIdFromApi(agenteId)
  if (fromApi) return ESPECIALISTAS.find((e) => e.id === fromApi) ?? especialistaPadrao
  const alvo = acoes?.map((a) => TOOL_TO_ESPECIALISTA[a.ferramenta]).find(Boolean)
  return ESPECIALISTAS.find((e) => e.id === alvo) ?? especialistaPadrao
}

export function especialistaPorId(id?: EspecialistaId | null): Especialista | undefined {
  return id ? ESPECIALISTAS.find((e) => e.id === id) : undefined
}

export function copyDegustacao(id: EspecialistaId) {
  return COPY_BY_ID[id]
}
