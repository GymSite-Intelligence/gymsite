/**
 * Tamanhos benchmark por modelo de negócio fitness.
 *
 * Fontes:
 * - Smart Fit (comunicação institucional pública)
 * - ACAD Brasil / SECA — relatórios setoriais 2024
 * - ABFPilates — guia de implantação
 * - F45, Velocity Performance — material institucional
 * - Sebrae 2024 — pesquisa de mercado fitness BR
 *
 * Estrutura PP/P/M/G/GG segue padrão Smart Fit (mais reconhecido no setor).
 * "M" é geralmente o tamanho-âncora — modelo viável que paga conta e tem
 * melhor relação ROI/CAPEX. Pra default no form, sempre apontamos pra M.
 */

export type TamanhoCodigo = 'pp' | 'p' | 'm' | 'g' | 'gg'

export interface FaixaTamanho {
  codigo: TamanhoCodigo
  /** Label curto: "PP", "P", "M", "G", "GG" */
  label: string
  /** Descrição curta do que esse tamanho representa */
  descricao: string
  /** m² mínimo da faixa */
  min: number
  /** m² máximo da faixa */
  max: number
  /** Exemplo de operação real nesse tamanho (referência de mercado) */
  exemploRede?: string
}

export type ModeloNegocio =
  | 'academia'
  | 'crossfit_box'
  | 'studio_pilates'
  | 'studio_funcional'
  | 'outro'

/**
 * Faixas oficiais por modelo. "M" é sempre o tamanho-âncora (default no form).
 *
 * Critério de inclusão: PP só existe quando o modelo tem operação real abaixo
 * de 250 m² (Pilates sim, Academia não — Smart Fit Express já é PP em 400 m²).
 */
export const TAMANHOS_POR_MODELO: Record<ModeloNegocio, FaixaTamanho[]> = {
  academia: [
    {
      codigo: 'pp',
      label: 'PP',
      descricao: 'Mini studio / Express',
      min: 250,
      max: 400,
      exemploRede: 'Smart Fit Express',
    },
    {
      codigo: 'p',
      label: 'P',
      descricao: 'Studio compacto',
      min: 400,
      max: 800,
      exemploRede: 'Selfit P, Just Fit',
    },
    {
      codigo: 'm',
      label: 'M',
      descricao: 'Padrão de mercado (mais comum)',
      min: 800,
      max: 1500,
      exemploRede: 'Smart Fit Standard, Bluefit',
    },
    {
      codigo: 'g',
      label: 'G',
      descricao: 'Grande porte / Premium',
      min: 1500,
      max: 2500,
      exemploRede: 'Bodytech, Cia Athletica',
    },
    {
      codigo: 'gg',
      label: 'GG',
      descricao: 'Mega centro fitness',
      min: 2500,
      max: 5000,
      exemploRede: 'Companhia Athletica flagship',
    },
  ],
  crossfit_box: [
    {
      codigo: 'pp',
      label: 'PP',
      descricao: 'Box garagem / micro',
      min: 150,
      max: 250,
    },
    {
      codigo: 'p',
      label: 'P',
      descricao: 'Box pequeno',
      min: 250,
      max: 500,
      exemploRede: 'CrossFit afiliados pequenos',
    },
    {
      codigo: 'm',
      label: 'M',
      descricao: 'Box padrão (mais comum)',
      min: 500,
      max: 800,
      exemploRede: 'CrossFit médio brasileiro',
    },
    {
      codigo: 'g',
      label: 'G',
      descricao: 'Box performance',
      min: 800,
      max: 1500,
      exemploRede: 'CrossFit Recife, Performance Centers',
    },
    {
      codigo: 'gg',
      label: 'GG',
      descricao: 'CT multimodalidade',
      min: 1500,
      max: 3000,
    },
  ],
  studio_pilates: [
    {
      codigo: 'pp',
      label: 'PP',
      descricao: 'Studio único (1 sala)',
      min: 50,
      max: 80,
      exemploRede: 'Pilates Solo PP',
    },
    {
      codigo: 'p',
      label: 'P',
      descricao: 'Studio compacto',
      min: 80,
      max: 150,
      exemploRede: 'Studios independentes P',
    },
    {
      codigo: 'm',
      label: 'M',
      descricao: 'Studio + sala funcional (mais comum)',
      min: 150,
      max: 280,
      exemploRede: 'Pilates Pró, Body Pilates',
    },
    {
      codigo: 'g',
      label: 'G',
      descricao: 'Multi-equipamentos premium',
      min: 280,
      max: 500,
      exemploRede: 'STOTT Pilates, Polestar',
    },
    {
      codigo: 'gg',
      label: 'GG',
      descricao: 'Reabilitação + Pilates',
      min: 500,
      max: 1000,
    },
  ],
  studio_funcional: [
    {
      codigo: 'pp',
      label: 'PP',
      descricao: 'Studio boutique micro',
      min: 100,
      max: 200,
    },
    {
      codigo: 'p',
      label: 'P',
      descricao: 'Studio compacto',
      min: 200,
      max: 350,
      exemploRede: 'F45 P, Velocity Performance P',
    },
    {
      codigo: 'm',
      label: 'M',
      descricao: 'Padrão F45 / boutique (mais comum)',
      min: 350,
      max: 600,
      exemploRede: 'F45 Training padrão',
    },
    {
      codigo: 'g',
      label: 'G',
      descricao: 'Funcional grande / multi-aula',
      min: 600,
      max: 1000,
    },
    {
      codigo: 'gg',
      label: 'GG',
      descricao: 'Centro funcional + cardio',
      min: 1000,
      max: 2000,
    },
  ],
  outro: [
    {
      codigo: 'pp',
      label: 'PP',
      descricao: 'Pequeno porte',
      min: 100,
      max: 300,
    },
    {
      codigo: 'p',
      label: 'P',
      descricao: 'Médio-pequeno',
      min: 300,
      max: 600,
    },
    {
      codigo: 'm',
      label: 'M',
      descricao: 'Médio (mais comum)',
      min: 600,
      max: 1200,
    },
    {
      codigo: 'g',
      label: 'G',
      descricao: 'Grande',
      min: 1200,
      max: 2000,
    },
    {
      codigo: 'gg',
      label: 'GG',
      descricao: 'Mega centro',
      min: 2000,
      max: 5000,
    },
  ],
}

/**
 * Retorna a faixa âncora ("M") do modelo — usada como default ao trocar tipo.
 */
export function getTamanhoAncora(modelo: ModeloNegocio): FaixaTamanho {
  const faixas = TAMANHOS_POR_MODELO[modelo]
  return faixas.find((f) => f.codigo === 'm') ?? faixas[2] ?? faixas[0]
}

/**
 * Dado um par (min, max) em m², descobre em qual faixa do modelo se encaixa.
 * Útil pra UI mostrar "Você selecionou tamanho M" quando user mexe nos inputs.
 */
export function inferirTamanho(
  modelo: ModeloNegocio,
  min: number,
  max: number,
): TamanhoCodigo | null {
  const meio = (min + max) / 2
  const faixas = TAMANHOS_POR_MODELO[modelo]
  // Procura faixa cujo intervalo contém o meio
  const exata = faixas.find((f) => meio >= f.min && meio <= f.max)
  if (exata) return exata.codigo
  // Fallback: a mais próxima por distância do meio
  let melhor: FaixaTamanho | null = null
  let menorDist = Infinity
  for (const f of faixas) {
    const centro = (f.min + f.max) / 2
    const dist = Math.abs(centro - meio)
    if (dist < menorDist) {
      menorDist = dist
      melhor = f
    }
  }
  return melhor?.codigo ?? null
}
