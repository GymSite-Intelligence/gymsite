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
 * TIR e VPL ficam como aproximação simplificada — recálculo exato exigiria
 * fluxo de caixa de 60 meses; mantemos a fórmula linear `lucro × 12 / capex`.
 *
 * NÃO MUTA o cenário original — sempre retorna objeto novo. Flag
 * `_ajustado_com_kit` sinaliza pra UI exibir badge.
 */
import type { CenarioJSON } from '@/hooks/useRelatorioDetail'

/** Constantes da cascata (replicam financial_tools.py). */
const MANUTENCAO_PCT_CAPEX_MES = 0.005 // 0.5% /mês do CAPEX
const SEGURO_PCT_CAPEX_MES = 0.002 // 0.2% /mês
const CAPITAL_GIRO_MESES = 3
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
 * @param equipamentosTotalReal valor médio da faixa real do kit (com desconto)
 */
export function recalcularCenarioComKit(
  cenario: CenarioJSON | undefined,
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

  // ── 3. Custos fixos total recalculado ────────────────────────
  // Mantém todos outros custos, substitui só manutencao + seguro
  const custosFixosTotalNovo =
    custosDetOriginal.aluguel +
    custosDetOriginal.condominio +
    custosDetOriginal.iptu +
    custosDetOriginal.energia +
    custosDetOriginal.agua +
    custosDetOriginal.internet +
    custosDetOriginal.folha +
    manutencaoNova +
    custosDetOriginal.contabilidade +
    custosDetOriginal.sistema_gestao +
    seguroNovo +
    custosDetOriginal.outros

  // ── 4. Custos totais (fixos + marketing) ─────────────────────
  const marketingMensal = cenario.marketing_mensal ?? 0
  const custosTotaisNovo = custosFixosTotalNovo + marketingMensal

  // ── 5. Resultado ─────────────────────────────────────────────
  // Motor fiscal v1.3: lucro é LÍQUIDO do Simples. Tributos = receita ×
  // alíquota (a receita não muda no recálculo do kit, então o valor do motor
  // vale). Runs antigos sem o campo continuam pré-imposto (?? 0).
  const tributosMensal = cenario.tributos_mensal ?? 0
  const lucroMensalNovo =
    cenario.receita_mensal - custosTotaisNovo - tributosMensal
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

  // ── 7. TIR aproximada (fluxo linear simplificado) ────────────
  // Pra TIR exata precisaria do fluxo mensal de 60 meses; aqui
  // aproximamos por (lucro_anual / investimento) − custo_capital
  const lucroAnual = lucroMensalNovo * 12
  const tirAnualPctNovo =
    investimentoTotalNovo > 0
      ? ((lucroAnual / investimentoTotalNovo) * 100) - CUSTO_CAPITAL_ANUAL * 100
      : null

  // ── 8. VPL aproximado (5 anos a 12% a.a.) ────────────────────
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
    },
    custos_fixos_total: custosFixosTotalNovo,
    custos_totais: custosTotaisNovo,
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
  /** Map { 'low': X, 'mid': Y, 'premium': Z } com totais por modelo. */
  equipamentosPorModelo: Record<string, number | null | undefined> | null | undefined,
): Record<string, CenarioAjustado> | undefined {
  if (!cenarios) return undefined
  if (!equipamentosPorModelo) return undefined

  const out: Record<string, CenarioAjustado> = {}
  for (const [key, cenario] of Object.entries(cenarios)) {
    const valor = equipamentosPorModelo[key]
    const recalc = recalcularCenarioComKit(cenario, valor)
    if (recalc) out[key] = recalc
  }
  return out
}
