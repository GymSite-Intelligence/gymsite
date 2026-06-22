# Plano de Correção do Motor Financeiro (A4) + Posicionamento (A9) — V3

> Origem: revisão jun/2026 confrontando o relatório do MVP (Cocó/Fortaleza) com os
> benchmarks do setor (`Benchmark Financeiro de Academias.pdf`, `Zonas de Valor Luiza
> Castanho.pdf`). Auditoria de código por especialistas confirmou que as contradições
> são **estruturais e determinísticas**, não acidente do caso.
> Regra VEC mantida: número vem de tool/cálculo determinístico, nunca da boca do LLM.

## Diagnóstico (confirmado no código)

**A4 — `tools/financial_tools.py`:**
1. Aluguel = `R$/m² (MRLR) × área` direto no OPEX, sem teto de ocupação. O "aluguel >15%" é só `alertas.append(string)` cosmético (`:1159-1160`) → raiz do 34,3% do Cocó.
2. Cegueira fiscal: zero tributos, zero Fator R. `lucro = receita − custos` (`:461`) é pré-imposto disfarçado de líquido (infla margem ~10-14pp).
3. Folha em R$ fixo (`folha_por_modelo`, `:198-202`) → com receita alta vira ~14% vs benchmark mid 35%.
4. OPEX não reconcilia com estrutura-alvo por modelo; alerta setorial (`:846`) só pega margem BAIXA.
5. Payback (`:486`) é artefato de #2+#3.

**A9 — `agents/a9_positioning_strategist.py` / `tools/posicionamento_renda.py`:**
- Cegueira fiscal (sem Fator R/Anexo/CNAE). Ticket só renda+concorrência, nunca cruza aluguel. Veredito de 3 caixas sem KPI operacional. Schema sem `alertas_financeiros_fiscais`.

## Benchmark (ground truth — % do faturamento, operação madura)

| Rubrica | Low-Cost | Mid-Market | Premium |
|---|---|---|---|
| Folha+encargos | 18% | 35% | 28-38% |
| Aluguel+IPTU+ocupação (TETO) | 12,5% | 15% | 15-16% |
| Tributos | 14% | 10% | 12,5% |
| OPEX total | 70% | 83% | 77,5% |
| Margem líquida | 30% | 17% | 22,5% |

Fator R (CNAE 9313-1/00, sem MEI): folha/faturamento ≥ 28% → Anexo III (6%); senão Anexo V (15,5%).
Múltiplos M&A: Low 4,0-6,0× EBITDA; Mid 2,4-3,6×; Premium/Boutique 3,8-6,5× (com retenção >85%/ano, churn <5%/mês).

---

## FASE 1 — A4 (P0). Arquivos: `parametros_metodologia.py`, `financial_tools.py`, novo teste.

### 1.1 Novos params (bloco VIABILIDADE de `parametros_metodologia.py`)
```python
# Folha como % do faturamento (benchmark maduro). Aplicado como max(piso R$, % da receita).
"folha_pct_fat_low":     _p(0.18, "Benchmark Financeiro Academias 2024 (Low-Cost 18%)", "folha_pct", "fração", "benchmark"),
"folha_pct_fat_mid":     _p(0.35, "Benchmark Financeiro Academias 2024 (Mid-Market 35%)", "folha_pct", "fração", "benchmark"),
"folha_pct_fat_premium": _p(0.33, "Benchmark Financeiro Academias 2024 (Premium 28-38%, alvo Fator R)", "folha_pct", "fração", "benchmark"),
# Fator R / Simples Nacional CNAE 9313-1/00
"fator_r_corte_folha":        _p(0.28,  "LC 123/2006 — corte Fator R folha/faturamento", "fator_r", "fração", "regulatorio"),
"aliquota_simples_anexo_iii": _p(0.06,  "LC 123/2006 Anexo III faixa inicial", "tributo", "fração", "regulatorio"),
"aliquota_simples_anexo_v":   _p(0.155, "LC 123/2006 Anexo V faixa inicial", "tributo", "fração", "regulatorio"),
# Teto de ocupação imobiliária (aluguel+condomínio+IPTU / faturamento) por modelo
"ocupacao_teto_low":     _p(0.125, "Benchmark Financeiro Academias 2024 (Low-Cost 12,5%)", "ocupacao_teto", "fração", "benchmark"),
"ocupacao_teto_mid":     _p(0.15,  "Benchmark Financeiro Academias 2024 (Mid-Market 15%)", "ocupacao_teto", "fração", "benchmark"),
"ocupacao_teto_premium": _p(0.15,  "Benchmark Financeiro Academias 2024 (Premium 15-16%)", "ocupacao_teto", "fração", "benchmark"),
```
Constantes derivadas no topo (perto de `CUSTOS_MARKETING_PCT`):
```python
FOLHA_PCT_FATURAMENTO = param_por_modelo("folha_pct_fat")
OCUPACAO_TETO         = param_por_modelo("ocupacao_teto")
```

### 1.2 Folha como max(piso, % faturamento) — em `calcular_viabilidade_3_cenarios` (~`:425`)
```python
folha_min = CUSTOS_DETALHADOS_BASE["folha_por_modelo"][faixa_key]
folha = max(folha_min, receita_mensal * FOLHA_PCT_FATURAMENTO[faixa_key])
```
Mantém piso R$ (realismo rampa/pequeno) e % do faturamento (escala). Também habilita o Fator R.

### 1.3 Motor fiscal (Fator R) — depois de `custos_totais`, antes do `lucro_mensal` (~`:458`)
```python
fator_r = (folha / receita_mensal) if receita_mensal > 0 else 0.0
anexo_simples = "III" if fator_r >= param("fator_r_corte_folha") else "V"
aliquota_tributos = param("aliquota_simples_anexo_iii") if anexo_simples == "III" else param("aliquota_simples_anexo_v")
tributos_mensal = round(receita_mensal * aliquota_tributos, 2)
```
Lucro vira **líquido de imposto**:
```python
lucro_mensal = receita_mensal - custos_totais - tributos_mensal
```

### 1.4 Guardrail de ocupação — depois do bloco de custos (~`:458`)
```python
ocupacao_abs = custos["aluguel"] + custos["condominio"] + custos["iptu"]
ocupacao_pct = (ocupacao_abs / receita_mensal) if receita_mensal > 0 else 1.0
teto_ocup = OCUPACAO_TETO[faixa_key]
# ticket mínimo p/ aluguel caber no teto, à mesma matrícula realista
ticket_piso_ocupacao = (
    ocupacao_abs / (teto_ocup * matr_real * (1.0 - inadimplencia))
) if (matr_real > 0 and (1.0 - inadimplencia) > 0) else None
ocupacao_estoura = ocupacao_pct > teto_ocup
```

### 1.5 Penalização do veredito (não só alerta)
`_classificar_viabilidade(...)` ganha param `ocupacao_estoura: bool=False`. Quando True:
- veredito **rebaixa para "INVIAVEL"** (ocupação acima do teto estrangula o caixa estruturalmente), independente do payback.
- `calcular_score_viabilidade` zera o bônus e aplica penalidade (score ≤ limiar de rejeição).

### 1.6 Reconciliação OPEX (alerta bidirecional)
Após margem, comparar `margem_pct` com benchmark do modelo (low 30 / mid 17 / premium 22,5). Se `margem_pct` ficar **acima** de `benchmark + 8pp`, anexar alerta "margem otimista vs benchmark — revisar premissas (folha/tributos/ocupação)". Mantém o alerta de margem baixa existente.

### 1.7 Stress test de ocupação
Adicionar a `STRESS_TESTS` um teste que reprova quando `ocupacao_pct` (base ou +20% aluguel) ultrapassa o teto; `_calcular_sensibilidade` passa a medir e reportar a razão de ocupação, não só lucro/payback.

### 1.8 Campos novos no dict de cada cenário
`tributos_mensal`, `aliquota_tributos`, `fator_r`, `anexo_simples`, `ocupacao_pct`, `teto_ocupacao`, `ticket_piso_ocupacao`, `folha_pct_efetivo` (= folha/receita). Propagar ao snapshot `analise_financeira_pronto` (A4 callback) p/ o A9 consumir.

### 1.9 Teste de regressão (novo — `tools/test_a4_fiscal_ocupacao.py`)
Caso Cocó: area≈1150m², aluguel≈R$79.062, ticket R$149, modelo mid. Asserts:
- `ocupacao_pct` ≈ 0,34 e `ocupacao_estoura == True`;
- veredito do cenário mid == "INVIAVEL";
- `tributos_mensal > 0` e `anexo_simples` definido;
- `ticket_piso_ocupacao` > ticket recomendado (sinaliza necessidade de subir ticket/baixar área);
- caso saudável (aluguel a 12% da receita) NÃO dispara `ocupacao_estoura` e mantém viabilidade.

---

## FASE 2 — A9 (P1 + 6 Zonas). Arquivos: `a9_positioning_strategist.py`, `posicionamento_renda.py`, `pipeline_schemas.py`, `parametros_metodologia.py`.

### 2.1 6 Zonas de Percepção (substitui OCEANO_AZUL/TRANSICAO/VERMELHO)
Mapear veredito nas 6 Zonas de Luiza Castanho (raio-X de posicionamento):
1. Comodidade · 2. Satisfação · 3. Resultado · 4. Superação · 5. Excelência · 6. Culto/Pertença.

**Classificação determinística (`tools/posicionamento_renda.py`, nova `classificar_zona_percepcao`)** a partir dos sinais já calculados — `ratio = ticket_teto_sustentavel / ticket_mercado` (headroom), `tier_modelo_percentil`, densidade competitiva/saturação, e contagem de gaps reais:
- `ratio < 1.0` → **Zona 1 (Comodidade)** — sem headroom, só preço.
- `1.0 ≤ ratio < 1.2` → **Zona 2 (Satisfação)** — conveniência, sem diferenciação.
- `1.2 ≤ ratio < 2.0` → **Zona 3 (Resultado)** — custo-benefício, "teto de vidro".
- `ratio ≥ 2.0` e (há gaps reais OU densidade competitiva baixa) → **Zona 4 (Superação)**.
- `ratio ≥ 2.0` e `tier == Premium` e gaps reais e densidade baixa → **Zona 5 (Excelência)**.
- **Zona 6 (Culto)**: NUNCA atribuída automaticamente — o PDF Zonas de Valor afirma que não existe marca no Brasil na Zona 6. Tratar como alvo aspiracional citado no texto, nunca como classificação calculada.

Manter campo legado `veredito_posicionamento` derivado da zona (Zona 1-2 → VERMELHO, Zona 3 → TRANSICAO, Zona 4-5 → OCEANO_AZUL) p/ compat de quem lê o veredito antigo. Campos novos: `zona_percepcao` (1-6), `zona_nome`, `zona_descricao`.

### 2.2 `alertas_financeiros_fiscais` (campo novo em `A9Output`)
Tipos: `FATOR_R` (gatilho tier Mid/Premium), `OCUPACAO_TICKET` (ticket recomendado < `ticket_piso_ocupacao` do A4), `KPI_BENCHMARK` (metas por tier). Determinístico, plugado em `_errc_deterministica`, consumindo `state["analise_financeira"]` (A4). Sem reabrir LLM.

**Adendo M&A (Valuation readiness) — no `KPI_BENCHMARK`:** para atingir os múltiplos do benchmark (Boutique/Premium **3,8x–6,5x EBITDA**), compradores/investidores institucionais exigem comprovação de eficiência. O alerta deve cravar, para tier Premium/Boutique (e como meta de maturidade p/ Mid):
- **CAC < R$ 180** por aluno;
- **retenção anual > 85%** (churn < ~5%/mês);
- LTV/aluno > R$ 1.500 (Mid) / > R$ 2.800 (Boutique);
- faixa de múltiplo EBITDA do tier (low 4,0-6,0 / mid 2,4-3,6 / premium 3,8-6,5).
Texto-âncora do alerta: estes KPIs atrelam o rigor fiscal/custos do A4 à prontidão de Valuation — blindam o plano contra otimismo e contra furo em due-diligence (teto de ocupação >15% derruba metade do valuation, per benchmark).

### 2.3 Ticket cruzado com ocupação
`recomendacao_ticket` passa a reportar `ticket_piso_ocupacao` do A4 e alertar quando o ticket viável-por-renda for menor que o piso-por-aluguel.

### 2.4 Trava ERRC
Quadrante "Reduzir": se tier ∈ {Mid, Premium}, **proibir** corte de folha/comissão; marcar folha como alavanca a proteger (linka Fator R ≥28% + churn premium).

### 2.5 Params A9 (adicionar)
`ltv_aluno_min_mid=1500`, `ltv_aluno_min_premium=2800`, `multiplo_ebitda_low=[4.0,6.0]`, `multiplo_ebitda_mid=[2.4,3.6]`, `multiplo_ebitda_premium=[3.8,6.5]`, `retencao_ano_min_premium=0.85`, `cac_max_valuation=180.0`, `retencao_ano_min_valuation=0.85`.

---

## Ordem de execução
FASE 1 (A4) primeiro — produz tributos/ocupação/ticket_piso que a FASE 2 (A9) consome.
Cada fase: implementar → teste → validar golden case (Cocó vira INVIÁVEL/penalizado) → revisar diff.
