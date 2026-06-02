# Golden Case: fortaleza_parangaba_20260528

## Identificação
- **UUID:** `8845b104-4536-444e-98d6-03b7319cbf08`
- **ADK Run ID:** `rpt_1780008001`
- **Data Criação:** 2026-05-28T22:09:37.481338+00:00
- **Pipeline Version:** 1.5
- **Status:** done

## Input
- **Cidade:** Fortaleza
- **Bairro:** Parangaba
- **UF:** CE
- **Área:** 800-1500 m²
- **Público:** 25-40
- **Tipo Negócio:** academia
- **Tamanho Preset:** m
- **Gênero Alvo:** misto

## Output Esperado (ground truth Supabase)
- **Veredito:** APROVADO COM RESSALVAS
- **Score Top1:** 6.99
- **Score Bairro:** 6.48
- **Modelo Recomendado:** Mid Market
- **Saturação:** MEDIO
- **Candidatos (DB):** 3
- **Concorrentes (DB):** 10 *(amostra no raio 3 km com reviews — não confundir com entrantes CNPJ)*
- **Entrantes CNPJ 90d (Fortaleza):** 48

## Campos Críticos (devem bater exatamente)
- `veredito`
- `score_top1_candidato`
- `modelo_recomendado`
- `nivel_saturacao`

## Campos com Tolerância
- `score_top1_candidato`: ±0,5 ponto absoluto (ver `expected_output.json`)
- `aluguel_mensal`: ±10%

## Notas do Curador

### Revisão (curadoria)

- **Dois universos de “concorrência” (não misturar)**:
  - **CNPJ / Deep Research (município)**: `novos_cnpj_fitness_90d = 48` (entrantes em Fortaleza nos últimos 90 dias); `parque_comercial_total ≈ 1733` unidades fitness na cidade.
  - **Maps / raio 3 km (bairro)**: `total_concorrentes_analisados = 10` — amostra georreferenciada com reviews/dores (Smart Fit, Selfit, Max Forma, etc. em bairros adjacentes a Parangaba).
- **Os “10” do Supabase são concorrentes no raio**, não entrantes CNPJ (diferente do caso Anápolis, onde o “9” no resumo confundia métricas).

- **Scores regionais (bate com o output)**:
  - Demográfico **8.0**, Viabilidade **9.5**, Competitivo **1.94** → Score Bairro **6.48** \((8.0 + 1.94 + 9.5) / 3\).
  - Score Top1 **6.99** > Score Bairro porque inclui **score_geoscout do candidato #1** (4 dimensões); coerente com ressalvas e âncoras GeoScout (não imóvel vago confirmado).

- **Score competitivo baixo vs. `nivel_saturacao = MEDIO`**:
  - `score_concorrencia ≈ 1.94` com `rating_medio_concorrentes ≈ 4.4` e agregado alto no raio (fórmula em `competitor_tools.calcular_score_concorrencia` penaliza quantidade + rating).
  - Saturação “MÉDIO” no label e score quase mínimo é tensão conhecida do modelo atual — documentar no eval, não reprovar o caso só por isso.

- **GeoScout / candidatos**:
  - `candidatos_count = 3` no DB (âncoras com investigação); relatório lista 14 avaliados no markdown — conferir persistência tabela `candidatos` vs. narrativa A6.
  - DR cita Smart Fit; busca local valida redes no raio — alinhado para `cobertura_redes_a0` quando existir.

- **Decisão de ground truth**:
  - Caso **mais completo** que Anápolis: tem candidatos + concorrentes mapeados.
  - Manter como referência de **Parangaba / Mid Market / APROVADO COM RESSALVAS** com competição local relevante e score regional na faixa 6–7.

### Observação técnica

- O texto “±50%” no template antigo era enganoso; para score use **±0,5 ponto absoluto** conforme `expected_output.json`.
- Incluir em curadoria futura: `entrantes_cnpj_90d` (48) separado de `competidores_raio` (10) no metadata do golden case, para o eval não confundir métricas.

### Benchmark de mensalidades (Fortaleza / Parangaba) — curadoria manual

Referência para validar `ticket_medio` / posicionamento **Mid Market** do relatório vs. mercado real. **5/5 unidades** coletadas em 01/06/2026.

**Regras de benchmark (eval):**

1. **Preço estrutural** = mensalidade após promo de 1º mês (ignorar R$ 9,99 / R$ 99 vitrine).
2. **Plano entrada** = menor preço **recorrente** com musculação + cardio na **mesma unidade** (anotar se plano for só unidade vs. rede).
3. **Mid Market** do relatório (~**R$ 139,90–149,90**) compara com planos **rede + modalidades** (Smart Smart, MaxForma Saúde Livre, Selfit Plus, Top Up TOP+).
4. Unidade **fora de Parangaba** (Panobianco) entra só como **referência municipal**, não como concorrente georreferenciado do raio.

| # | Rede / unidade | Status | Plano entrada | Outros planos | Fonte |
|---|----------------|--------|---------------|---------------|-------|
| 1 | **Smart Fit Parangaba** | Em operação (Av. Dr. Silas Munguba, 643 — Parangaba) | **Fit** R$ **119,90**/mês (promo 1º mês R$ 99; **rede/convidados/cadeira fora do plano**) | **Smart** R$ 139,90 (sem fidelidade; rede/convidados/cadeira fora); **Black** R$ 159,90 (rede + 5 convidados + cadeira; 12m fidelidade) | [smartfit.com.br — Parangaba](https://www.smartfit.com.br/academias/parangaba) |
| 2 | **Selfit Shopping Parangaba** | Em operação (Rua Germano Franck, 300 — Parangaba) | **Light** R$ **89,90**/mês (só unidade de matrícula; sem fidelidade/anuidade) | **Infinity** 119,90 (estado CE); **Plus** 149,90 (Brasil + Weburn); **Mega Plus** 159,90 (Brasil + 10 acompanhantes) | [selfitacademias.com.br](https://www.selfitacademias.com.br/) |
| 3 | **MaxForma Parangaba** | Em operação (Rua Germano Franck, 767 — Parangaba; seg–sex 05h–00h) | **Vitalidade** R$ **99,99**/mês (1ª mens. promo R$ 9,99; só unidade; todas as atividades) | **Saúde Livre** / **Premium** R$ 139,99 (rede; 7 acompanhantes/mês; bio 1×/mês) | [maxformaacademias.com — Parangaba](https://maxformaacademias.com/unidades/parangaba) |
| 4 | **Panobianco Fortaleza** *(ref. municipal — José de Alencar)* | Em operação (Av. Washington Soares, 7.263 — ~8 km de Parangaba) | **Silver** R$ **39,90**/mês (horário limitado; 12m; adesão R$ 59,90) | **Gold** 99,90; **Platinum** 109,90; **Platinum+** 139,90 (sem fidelidade/adesão) | [panobianco — Fortaleza](https://www.panobiancoacademia.com.br/academias/fortaleza) |
| 5 | **Top Up Parangaba** | Em operação (Av. Augusto dos Anjos, 1140 — Parangaba) | **TOP Recorrente** R$ **99,90**/mês (musculação + ergometria; permanência mín. 3 meses) | **TOP+ Recorrente** R$ 129,90 (+ modalidades; rede; 4 convidados/mês) | [topupacademia.com.br](https://www.topupacademia.com.br/) · [CT Parangaba](https://www.topupacademia.com.br/ct) |

**Caso 1 — detalhe (Smart Fit Parangaba)**

- Unidade no **epicentro** do caso (Av. Silas Munguba); seg–sex 5h–23h.
- **Fit R$ 119,90**: plano econômico com **12 meses fidelidade**; benefícios de rede Black (acesso +2.000 unidades, convidados, cadeira) **não** incluídos no Fit/Smart — só musculação, aeróbicos e app.
- **Smart R$ 139,90**: sem fidelidade; mesmo escopo de serviços que Fit (sem rede/convidados/cadeira no site).
- **Black R$ 159,90**: único com rede América Latina + 5 convidados + cadeira.
- Promo **R$ 99 no 1º mês** (todos os planos) — não usar no eval.
- Add-ons: Body +R$ 19,90; Combo Coach + Body +R$ 29,90/mês.

**Caso 2 — detalhe (Selfit Shopping Parangaba)**

- Grade **oficial** (site institucional), não a página promocional `promo.selfit` (valores de campanha podem diferir).
- **Light R$ 89,90**: menor preço da grade; **restrito à unidade de matrícula** (Shopping Parangaba) — comparável ao escopo reduzido do Smart Fit Fit (sem rede/convidados).
- **Infinity R$ 119,90**: qualquer unidade **no estado (CE)**; modalidades* + 5 acompanhantes/mês; sem fidelidade/anuidade.
- **Plus R$ 149,90**: rede **Brasil** + App Weburn — **bate com o teto Mid Market** do relatório (~149,90).
- **Mega Plus R$ 159,90**: igual Plus com 10 acompanhantes/mês — faixa premium local (próximo Smart Fit Black 159,90).
- Promo “Você no ritmo do hexa” (01–10/06/2026) pode alterar vitrine; usar tabela acima como estrutural.

**Caso 3 — detalhe (MaxForma Parangaba)**

- Concorrente citado no relatório (reviews/dores); mesma rua da Selfit (Germano Franck 767 vs 300).
- **Vitalidade R$ 99,99**: unidade de origem + horário livre + todas as atividades + app + estacionamento + bio 1 crédito/mês; **1ª mensalidade R$ 9,99** é promo (não usar como estrutural).
- **Saúde Livre / Premium R$ 139,99**: recorrente mensal; rede (Livre *exceto Santos Dumont*; Premium todas); **7 acompanhantes/mês** (exc. planos ativos/agregadores Wellhub/TotalPass).
- **139,99** alinha com **Smart Smart 139,90** e **Top Up TOP+ 129,90** — reforça **Mid Market** do golden case.
- Horário amplo (até meia-noite seg–sex) — diferencial vs. redes low-cost padrão.

**Caso 4 — detalhe (Panobianco Fortaleza — referência municipal)**

- Unidade em **José de Alencar** (Washington Soares) — **fora do raio Parangaba**; usar só para contexto de preços em Fortaleza.
- **Silver R$ 39,90**: horário limitado na semana; outlier (não comparar 1:1 com musculação 24h).
- **Gold R$ 99,90** / **Platinum R$ 109,90** / **Platinum+ R$ 139,90**: Platinum+ sem fidelidade e sem adesão — **139,90** alinha com faixa Mid local.

**Caso 5 — detalhe (Top Up Parangaba)**

- Rede local (**8+ unidades** em Fortaleza); unidade Parangaba: Av. Augusto dos Anjos, 1140.
- **TOP R$ 99,90**: musculação + ergometria; permanência mín. **3 meses**; sem taxas adesão/manutenção no site.
- **TOP+ R$ 129,90**: + modalidades; qualquer unidade; 4 convidados/mês; mesmos valores na página [CT](https://www.topupacademia.com.br/ct) (Av. Godofredo Maciel, 88 — CT 24h, unidade distinta).
- TOP+ fica **abaixo** do ticket Mid do relatório (139,90+) mas **acima** do piso low-cost com rede parcial.

### Síntese do benchmark (5 unidades — Parangaba/Fortaleza, 01/06/2026)

| Faixa | Mensalidade estrutural | Quem (Parangaba ou ref. CE) |
|-------|------------------------|-----------------------------|
| **Piso absoluto (restrições)** | R$ 39,90 | Panobianco Silver *(fora Parangaba; horário limitado)* |
| **Piso só unidade (completo)** | R$ 89,90 – R$ 99,99 | Selfit Light · Top Up TOP · MaxForma Vitalidade |
| **Piso rede estadual / musculação ampla** | R$ 119,90 | Smart Fit Fit · Selfit Infinity |
| **Mid Market (rede + modalidades)** | R$ 129,90 – R$ 149,90 | Top Up TOP+ · Smart Smart · MaxForma Saúde Livre 139,99 · Selfit Plus |
| **Premium local** | R$ 159,90 | Smart Fit Black · Selfit Mega Plus |

**Leitura vs. relatório golden (Mid Market):**

- Mercado em **Parangaba** concentra planos comparáveis em **R$ 119,90–149,90**; entradas promocionais (9,99 / 99) e Light 89,90 são vitrine ou escopo reduzido.
- Ticket recomendado pelo relatório (**~R$ 139,90–149,90**) é **defensável**: Smart Smart, MaxForma Saúde Livre e Selfit Plus cobrem a faixa; TOP+ (129,90) fica ligeiramente abaixo mas com rede + modalidades.
- **Concorrência forte + rating alto** (`score_concorrencia ≈ 1.94`) não contradiz Mid Market — indica pressão de preço na vitrine, não impossibilidade de ticket 140+.
- **3 candidatos no DB** + **10 concorrentes no raio** — caso mais rico que Anápolis para validar posicionamento e pricing side-by-side.

## Aprovação
- [x] Veredito correto
- [x] Score dentro da faixa esperada
- [x] Modelo recomendado faz sentido
- [x] Campos críticos validados
- [x] Notas do curador preenchidas

*Aprovado em 01/06/2026 — benchmark 5/5 + scores conferidos; pendências de produto (candidatos DB vs markdown, CNPJ vs raio) permanecem nas notas.*
