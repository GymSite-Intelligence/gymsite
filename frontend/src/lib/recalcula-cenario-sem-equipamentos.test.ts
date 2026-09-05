import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  recalcularCenarioSemEquipamentos,
} from './recalcula-cenario-com-kit.ts'

const baseCenario = {
  capex_detalhado: {
    equipamentos: 100_000,
    obra_adaptacao: 50_000,
    projeto_arquitetonico: 10_000,
    alvara_e_taxas: 5_000,
    frete_equipamentos: 8_000,
    contingencia_pct: 0.1,
    contingencia_valor: 0,
    total: 0,
  },
  capex_total: 999,
  custos_detalhados: {
    aluguel: 1,
    condominio: 0,
    iptu: 0,
    energia: 0,
    agua: 100,
    internet: 0,
    folha: 0,
    manutencao: 0,
    contabilidade: 0,
    sistema_gestao: 0,
    seguro: 0,
    outros: 0,
  },
  matriculas: { realista: { valor: 100 } },
  frequencia_semanal_aluno: 2,
  receita_mensal_estimada: 50_000,
  receita_mensal: 50_000,
} as never

test('strips equipamentos and frete from capex total', () => {
  const out = recalcularCenarioSemEquipamentos(baseCenario, 400)
  assert.ok(out)
  assert.equal(out!.capex_detalhado!.equipamentos, 0)
  assert.equal(out!.capex_detalhado!.frete_equipamentos, 0)
  const sub = 0 + 50_000 + 10_000 + 5_000 + 0
  const expected = sub + sub * 0.1
  assert.equal(out!.capex_detalhado!.total, expected)
  assert.equal(out!.capex_total, expected)
  assert.equal(out!._equipamentos_ocultos, true)
})

test('returns cenario unchanged when no capex_detalhado', () => {
  const cenario = { capex_total: 123 } as never
  const out = recalcularCenarioSemEquipamentos(cenario, 400)
  assert.equal(out, cenario)
})

test('null equipment treated as zero without NaN', () => {
  const cenario = {
    ...baseCenario,
    capex_detalhado: {
      ...baseCenario.capex_detalhado,
      equipamentos: null,
      frete_equipamentos: null,
    },
  } as never
  const out = recalcularCenarioSemEquipamentos(cenario, 400)
  assert.ok(out)
  assert.equal(out!.capex_detalhado!.equipamentos, 0)
  assert.equal(out!.capex_detalhado!.frete_equipamentos, 0)
  assert.equal(Number.isNaN(out!.capex_total), false)
})
