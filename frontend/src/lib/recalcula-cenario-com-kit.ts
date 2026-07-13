/**
 * recalcula-cenario-com-kit — refatora cascata financeira do cenário usando
 * o kit de equipamentos detalhado como fonte da verdade pra linha
 * "Equipamentos" do CAPEX.
 *
 * Cascata aplicada (downstream do override de equipamentos):
 *   capex_detalhado.equipamentos       ← kit (estimado real, mediana faixa)
 *   capex_detalhado.contingencia_valor ← (subtotal) × pct
 *   capex_detalhado.total              ← subtotal + contingência
 *   capex_total                        ← total recalculado
 *   custos_detalhados.manutencao       ← 0.5%/mês × capex_total
 *   custos_detalhados.seguro           ← 0.2%/mês × capex_total
 *   custos_fixos_total                 ← recalculado (substitui manut + seguro)
 *   custos_totais                      ← fixos + marketing
 *   lucro_mensal_estimado              ← receita − custos_totais − tributos (Simples)
 *   margem_percentual                  ← lucro / receita × 100
 *   capital_giro                       ← 3 × custos_totais
 *   investimento_total                 ← capex_total + capital_giro
 *   payback_meses                      ← ceil(investimento / lucro_mensal)
 *
 * NÃO MUTA o cenário original — sempre retorna objeto novo. Flag
 * `_ajustado_com_kit` sinaliza pra UI exibir badge.
 */
import type { CenarioJSON } from '@/hooks/useRelatorioDetail'

/** Constantes da cascata (replicam financial_tools.py). */
const MANUTENCAO_PCT_CAPEX_MES = 0.005 // 0.5% /mês do CAPEX
const SEGURO_PCT_CAPEX_MES = 0.002 // 0.2% /mês
const CAPITAL_GIRO_MESES = 3

// Parâmetros do motor fiscal (replicam financial_tools.py e Supabase)
const FATOR_R_CORTE_FOLHA = 0.28
const ALIQUOTA_SIMPLES_ANEXO_III = 0.06
const ALIQUOTA_SIMPLES_ANEXO_V = 0.155

/**
 * Calcula a TIR anual usando o método da bisseção.
 * Réplica da função `_calcular_tir_anual` do backend.
 */
function calcularTirAnual(
  investimento: number,
  lucroMensal: number,
  anos = 5,
): number | null {
  if (lucroMensal <= 0 || investimento <= 0) return null
  const fluxoAnual = lucroMensal * 12

  let low = 0.0
  let high = 2.0 // TIR > 200% é improvável
  let mid = 0.0

  for (let i = 0; i < 50; i++) {
    mid = (low + high) / 2
    let vpl = -investimento
    for (let ano = 1; ano <= anos; ano++) {
      vpl += fluxoAnual / Math.pow(1 + mid, ano)
    }
    if (Math.abs(vpl) < 1.0) return mid
    if (vpl > 0) low = mid
    else high = mid
  }
  return mid
}

/**
 * Estima o custo da água, que escala com o número de visitas.
 * Réplica da função `custo_agua_mensal` do backend.
 */
function calcularCustoAgua(
  area_m2: number,
  agua_por_m2_base: number,
  matriculas: number,
  frequencia_semanal: number,
): number {
  const piso = area_m2 * agua_por_m2_base
  const visitasMes = matriculas * frequencia_semanal * 4.345
  const consumo_m3 = visitasMes * 0.013 // 13 L/visita
  const variavel = consumo_m3 * 15.0 // R$ 15/m³
  return Math.max(piso, variavel)
}

/**
 * Estima o custo do sistema de gestão, que escala com o número de alunos.
 * Réplica da função `custo_sistema_gestao` do backend.
 */
function calcularCustoSistema(
  base_mensal: number,
  matriculas: number,
): number {
  // Contratos de ERP sobem de preço acima de 1500 alunos
  return base_mensal * (matriculas > 1500 ? 1.5 : 1.0)
}

const CUSTO_CAPITAL_ANUAL = 0.12

export interface CenarioAjustado extends CenarioJSON {
  /** Marca pra UI mostrar badge "ajustado via kit". */
  _ajustado_com_kit?: boolean
  /** Total original do CAPEX antes do recálculo — útil pra diff. */
  _capex_total_original?: number
  /** Total original de equipamentos antes do override. */
  _equipamentos_original?: number
}

/**
 * Aplica o override de equipamentos e cascateia downstream.
 *
 * @param cenario cenário emitido pelo A4 (pode ser low/mid/premium)
 * @param area_m2 A área do imóvel, que não faz parte do objeto de cenário individual.
 * @param equipamentosTotalReal valor médio da faixa real do kit (com desconto)
 */
export function recalcularCenarioComKit(
  cenario: CenarioJSON | undefined,
  area_m2: number | null | undefined,
  equipamentosTotalReal: number | null | undefined,
): CenarioAjustado | undefined {
  if (!cenario) return undefined
  if (
    equipamentosTotalReal == null ||
    !Number.isFinite(equipamentosTotalReal) ||
    equipamentosTotalReal <= 0
  ) {
    return cenario
  }

  const capexOriginal = cenario.capex_detalhado
  if (!capexOriginal) {
    // Cenário v1 sem capex_detalhado — não recalculamos pra evitar
    // suposições erradas. Retorna original como está.
    return cenario
  }

  // ── 1. CAPEX recalculado ─────────────────────────────────────
  const equipamentosOriginal = capexOriginal.equipamentos ?? 0
  const equipamentosNovo = equipamentosTotalReal
  const obra = capexOriginal.obra_adaptacao ?? 0
  const projeto = capexOriginal.projeto_arquitetonico ?? 0
  const alvara = capexOriginal.alvara_e_taxas ?? 0
  // Schema v1.6: preserva frete se já calculado pelo backend; senão 0.
  // (Recálculo client-side de frete exigiria distância — não temos UF aqui.)
  const frete = capexOriginal.frete_equipamentos ?? 0
  const subtotal = equipamentosNovo + obra + projeto + alvara + frete
  const contingenciaPct = capexOriginal.contingencia_pct ?? 0.1
  const contingenciaNova = subtotal * contingenciaPct
  const capexTotalNovo = subtotal + contingenciaNova

  // ── 2. Custos detalhados que dependem do CAPEX ───────────────
  const custosDetOriginal = cenario.custos_detalhados ?? {
    aluguel: 0,
    condominio: 0,
    iptu: 0,
    energia: 0,
    agua: 0,
    internet: 0,
    folha: 0,
    manutencao: 0,
    contabilidade: 0,
    sistema_gestao: 0,
    seguro: 0,
    outros: 0,
  }
  const manutencaoNova = capexTotalNovo * MANUTENCAO_PCT_CAPEX_MES
  const seguroNovo = capexTotalNovo * SEGURO_PCT_CAPEX_MES

  const matriculasRealista = cenario.matriculas?.realista?.valor ?? 0
  const aguaNova = calcularCustoAgua(
    area_m2 ?? 0,
    custosDetOriginal.agua / (area_m2 || 1), // Extrai a base R$/m²
    matriculasRealista,
    cenario.frequencia_semanal_aluno ?? 2.0,
  )
  const sistemaGestaoNovo = calcularCustoSistema(
    800, // Valor base do parâmetro
    matriculasRealista,
  )

  // ── 3. Custos fixos total recalculado ────────────────────────
  // Mantém todos outros custos, substitui só manutencao + seguro
  const custosFixosTotalNovo =
    custosDetOriginal.aluguel +
    custosDetOriginal.condominio +
    custosDetOriginal.iptu +
    custosDetOriginal.energia + // Energia não muda significativamente com o kit
    aguaNova +
    custosDetOriginal.internet +
    custosDetOriginal.folha +
    manutencaoNova +
    custosDetOriginal.contabilidade +
    sistemaGestaoNovo +
    seguroNovo +
    custosDetOriginal.outros

  // ── 4. Custos totais (fixos + marketing) ─────────────────────
  const marketingMensal = cenario.marketing_mensal ?? 0
  const custosTotaisNovo = custosFixosTotalNovo + marketingMensal

  // ── 5. Resultado (com motor fiscal) ──────────────────────────
  // Recalcula o Fator R e os tributos, pois a folha pode ter mudado
  // implicitamente via custos de manutenção/seguro.
  const receitaMensal = cenario.receita_mensal ?? 0
  const folha = custosDetOriginal.folha ?? 0
  const fatorR = receitaMensal > 0 ? folha / receitaMensal : 0
  const anexoSimples = fatorR >= FATOR_R_CORTE_FOLHA ? 'III' : 'V'
  const aliquotaTributos =
    anexoSimples === 'III'
      ? ALIQUOTA_SIMPLES_ANEXO_III
      : ALIQUOTA_SIMPLES_ANEXO_V

  const tributosMensal = receitaMensal * aliquotaTributos

  // Lucro é LÍQUIDO de impostos
  const lucroMensalNovo =
    receitaMensal - custosTotaisNovo - tributosMensal
  const margemPctNovo =
    cenario.receita_mensal > 0
      ? (lucroMensalNovo / cenario.receita_mensal) * 100
      : 0

  // ── 6. Investimento e payback ────────────────────────────────
  const capitalGiroNovo = custosTotaisNovo * CAPITAL_GIRO_MESES
  const investimentoTotalNovo = capexTotalNovo + capitalGiroNovo
  const paybackMesesNovo =
    lucroMensalNovo > 0
      ? Math.ceil(investimentoTotalNovo / lucroMensalNovo)
      : 999

  // ── 7. TIR e VPL (réplica do backend) ────────────────────────
  const lucroAnual = lucroMensalNovo * 12
  const tirAnual = calcularTirAnual(investimentoTotalNovo, lucroMensalNovo)
  const tirAnualPctNovo = tirAnual !== null ? tirAnual * 100 : null

  // VPL para 5 anos, replicando _calcular_vpl
  // VPL = Σ (lucro_anual / (1+r)^t) - investimento, t=1..5
  let vplNovo = -investimentoTotalNovo
  for (let t = 1; t <= 5; t++) {
    vplNovo += lucroAnual / Math.pow(1 + CUSTO_CAPITAL_ANUAL, t)
  }

  return {
    ...cenario,
    capex_detalhado: {
      ...capexOriginal,
      equipamentos: equipamentosNovo,
      contingencia_valor: contingenciaNova,
      total: capexTotalNovo,
    },
    capex_total: capexTotalNovo,
    custos_detalhados: {
      ...custosDetOriginal,
      manutencao: manutencaoNova,
      seguro: seguroNovo,
      agua: aguaNova,
      sistema_gestao: sistemaGestaoNovo,
    },
    custos_fixos_total: custosFixosTotalNovo,
    custos_totais: custosTotaisNovo,
    // Campos fiscais recalculados
    fator_r: fatorR,
    anexo_simples: anexoSimples,
    aliquota_tributos: aliquotaTributos,
    tributos_mensal: tributosMensal,
    lucro_mensal_estimado: lucroMensalNovo,
    margem_percentual: margemPctNovo,
    capital_giro: capitalGiroNovo,
    investimento_total: investimentoTotalNovo,
    payback_meses: paybackMesesNovo,
    tir_anual_pct: tirAnualPctNovo,
    vpl_5_anos: vplNovo,
    _ajustado_com_kit: true,
    _capex_total_original: capexOriginal.total,
    _equipamentos_original: equipamentosOriginal,
  }
}

/**
 * Aplica recalculo nos 3 cenários (low/mid/premium) usando kits DIFERENTES
 * por modelo financeiro — Low usa kit econômico (1 tamanho abaixo), Mid
 * usa o tamanho selecionado, Premium usa kit robusto (1 tamanho acima).
 *
 * Diferencia o CAPEX entre cenários e reflete a escolha de equipamentos:
 * Low Cost = mais barato, Premium = mais caro. Sem isso, os 3 cenários
 * mostravam o mesmo valor de equipamentos, escondendo a variação real
 * de investimento por modelo de negócio.
 */
export function recalcularCenariosComKit(
  cenarios: Record<string, CenarioJSON> | undefined,
  area_m2: number | null | undefined,
  /** Map { 'low': X, 'mid': Y, 'premium': Z } com totais por modelo. */
  equipamentosPorModelo: Record<string, number | null | undefined> | null | undefined,
): Record<string, CenarioAjustado> | undefined {
  if (!cenarios) return undefined
  if (!equipamentosPorModelo) return undefined
  if (!area_m2) return cenarios

  const out: Record<string, CenarioAjustado> = {}
  for (const [key, cenario] of Object.entries(cenarios)) {
    const valor = equipamentosPorModelo[key]
    const recalc = recalcularCenarioComKit(cenario, area_m2, valor)
    if (recalc) out[key] = recalc
  }
  return out
}
