# Golden Case: anapolis_anapolis_city_20260529

## Identificação
- **UUID:** `291f1a1f-1303-4da4-b487-bafaa3cc020e`
- **ADK Run ID:** `rpt_1780087287`
- **Data Criação:** 2026-05-29T20:22:42.585483+00:00
- **Pipeline Version:** 1.5
- **Status:** done

## Input
- **Cidade:** Anápolis
- **Bairro:** Anápolis City
- **UF:** GO
- **Área:** 800-1500 m²
- **Público:** 25-40
- **Tipo Negócio:** academia
- **Tamanho Preset:** m
- **Gênero Alvo:** misto

## Output Esperado (ground truth Supabase)
- **Veredito:** APROVADO COM RESSALVAS
- **Score Top1:** 6.65
- **Score Bairro:** 6.65
- **Modelo Recomendado:** Low Cost
- **Saturação:** MEDIO
- **Candidatos (DB):** 0
- **Concorrentes (DB):** 9

## Campos Críticos (devem bater exatamente)
- `veredito`
- `score_top1_candidato`
- `modelo_recomendado`
- `nivel_saturacao`

## Campos com Tolerância
- `score_top1_candidato`: ±50%
- `aluguel_mensal`: ±10%

## Notas do Curador
### Revisão (curadoria)

- **Leitura correta dos "9"**: os `9` deste caso representam **novos CNPJs fitness em 90 dias (CNPJ)** (`market_context.novos_cnpj_fitness_90d`) — **não** o número de concorrentes no raio.
- **Concorrência no raio (georreferenciada)**: no relatório, a amostra aprofundada foi **9 concorrentes** (reviews/dores), enquanto o agregado cita **112 academias no raio 3km** (count bruto/aggregate).
- **Score competitivo baixo é coerente com o algoritmo atual**: `score_concorrencia≈1.96` é explicado por (i) agregado alto no raio e (ii) `rating_medio_concorrentes≈4.54` — penaliza forte mesmo com `nivel_saturacao=MEDIO`.
- **Ponto de atenção (evolução do produto)**: o relatório deveria deixar explícito que **entrantes (CNPJ)** e **concorrência no raio (Maps/Places)** são métricas diferentes, e/ou reconciliar com a lista do Deep Research (cobertura A0 / redes fantasma).
- **Decisão de ground truth**: manter o caso como referência para “mercado viável + competição forte + GeoScout com erro de cidade (alerta)” — mesmo com `candidatos_count=0` no DB.

### Observação técnica

- O texto “±50%” em tolerância veio do template `notes.md`. A intenção para score é **±0,5 ponto absoluto** (ex.: 6,15–7,15) conforme `expected_output.json`.

### Benchmark de mensalidades (Anápolis) — curadoria manual

Referência para validar `ticket_medio` / posicionamento **Low Cost** do relatório vs. mercado real. **5/5 unidades** coletadas em 01/06/2026.

| # | Rede / unidade | Status | Plano entrada | Outros planos | Fonte |
|---|----------------|--------|---------------|---------------|-------|
| 1 | **Bluefit Anápolis** | Pré-inauguração (“Avise-me na inauguração”) | **BLUE** R$ **149,90**/mês (unidade escolhida; matrícula R$ 60; anuidade R$ 99,90; sem fidelidade) | **PREMIUM** R$ 194,90 (todas unidades; sem taxas); **PREMIUM PLUS** R$ 214,90 (+ bio 1×/mês) | [bluefit.com.br/unidade/anapolis](https://www.bluefit.com.br/unidade/anapolis) |
| 2 | **Skyfit JK Nova Capital** | Em operação (Av. Paraguai, 135 — JK Nova Capital) | **SKY Recorrente** R$ **139,90**/mês (de R$ 229,90; rede Skyfit) | **ÁGUIA Anual** R$ 119,90 (só unidade; de R$ 199,90); **PRIME Mensal** R$ 159,90 (rede; de R$ 239,90) | [skyfitacademia.com — JK Nova Capital](https://skyfitacademia.com/unidade/anapolis-jk-nova-capital-go/) |
| 3 | **Smart Fit Anápolis** | Em operação (Av. Brasil Norte, 1080 — Cidade Jardim) | **Fit** R$ **119,90**/mês (promo 1º mês R$ 99; 12 meses fidelidade; adesão grátis) | **Smart** R$ 139,90 (sem fidelidade; 1º mês R$ 99); **Black** R$ 159,90 (+2.000 unidades; 12 meses fidelidade; 1º mês R$ 99) | [smartfit.com.br — Anápolis](https://www.smartfit.com.br/academias/anapolis/) |
| 4 | **Academia (portal Next Fit)** | Vendas online — *confirmar nome/endereço da unidade* | **12 meses** R$ **79,90**/mês (total R$ 958,80; 12×; adesão grátis) | **Recorrente** R$ 99,90/mês (total R$ 1.198,80); **Especial 026** R$ 110,00×10 (total R$ 1.100; “2M GRÁTIS”; 12 meses) | [venda.nextfit.com.br — contratos](https://venda.nextfit.com.br/09f330f8-acc4-45af-8cac-22448ddb2e2c/contratos) |
| 5 | **Panobianco Jaiara** | Em operação (Av. Fernando Costa, 772 — Vila Jaiara) | **Gold** R$ **99,90**/mês (site; 12m fidelidade; adesão R$ 59,90) | **Silver** R$ 39,90 (horário limitado; só unidade); **Platinum** R$ 109,90; **Platinum+** R$ 139,90 (sem fidelidade no site); **EVO:** Platinum Recorrente **R$ 139,90** (sem adesão/fidelidade; promo Orange 1º mês R$ 0,99 de 119,90) | [panobianco — Jaiara](https://www.panobiancoacademia.com.br/academias/jaiara) · [EVO matrícula online](https://evo-totem.w12app.com.br/panobiancos/191/site/oportunidade) |

**Caso 1 — detalhe (Bluefit)**

- Unidade ainda **não inaugurada** no site (CTA de aviso + tour virtual); preços são **tabela divulgada pré-abertura**, sujeitos a alteração (disclaimer no site).
- **Faixa útil para o golden case:** plano mais barato **R$ 149,90** alinha com faixa Low Cost / high-value do DR; Premium **R$ 194,90–214,90** puxa para mid market se comparar só o topo da grade.
- Taxas BLUE (matrícula + anuidade) elevam **TCO** vs. Premium sem taxas — relevante se o eval comparar “preço de vitrine” vs. custo real no 1º ano.

**Caso 2 — detalhe (Skyfit JK Nova Capital)**

- Unidade **ativa**; horário amplo (seg–sex 05h–00h; sáb/dom reduzido).
- **Menor vitrine recorrente com rede:** SKY **R$ 139,90** — **R$ 10 abaixo** do Bluefit BLUE (149,90), com acesso à rede Skyfit (condições no site).
- **Menor valor nominal da grade:** ÁGUIA **R$ 119,90**, porém **plano anual** e **sem** treino em toda a rede (benefício riscado no site).
- **PRIME R$ 159,90** mensal com rede — entre SKY e faixa Premium Bluefit.
- Para benchmark Low Cost do relatório: usar **SKY 139,90** ou **ÁGUIA 119,90** conforme regra (recorrente vs. menor preço absoluto com compromisso anual).

**Caso 3 — detalhe (Smart Fit Anápolis)**

- Unidade **ativa** (Cidade Jardim); horário seg–sex 5h–23h.
- **Fit R$ 119,90** empata o piso recorrente com fidelidade da Skyfit ÁGUIA (119,90) — referência forte para **Low Cost** do relatório.
- Promo **R$ 99 no 1º mês** em Fit, Smart e Black (não usar como mensalidade estrutural no eval).
- **Smart R$ 139,90** sem fidelidade — comparável ao SKY Skyfit (139,90) e abaixo do Bluefit BLUE (149,90).
- **Black R$ 159,90** com rede América Latina — alinhado ao PRIME Skyfit (159,90).
- Add-ons opcionais no site: **Smart Fit Body** +R$ 19,90/mês; **Combo Coach + Body** +R$ 29,90/mês (12 meses).
- CNPJ na página: Anapolis Fit Academia ltda `28.784.413/0001-23`.

**Caso 4 — detalhe (portal Next Fit / venda online)**

- **Next Fit aqui é software de gestão + site de vendas**, não a rede “Next Fit” corporativa ([nextfit.com.br](https://nextfit.com.br/) = SaaS). UUID da unidade: `09f330f8-acc4-45af-8cac-22448ddb2e2c` — **pendente** cruzar com nome no Maps/relatório (candidato: academia independente em **Anápolis City**, ex. New Fit na Av. Perimetral).
- **Menor mensalidade estrutural da amostra:** **R$ 79,90/mês** (plano 12 meses, total R$ 958,80) — **abaixo** de Smart Fit Fit e Skyfit ÁGUIA (119,90).
- **Recorrente R$ 99,90/mês** (total R$ 1.198,80) — comparável à promo 1º mês das grandes redes, porém com **12 meses** de duração no contrato.
- **026 Plano Especial — 2M GRÁTIS:** parcelas R$ 110,00 (até 10×), total R$ 1.100,00; adesão grátis — tratar como **campanha** (custo efetivo ~R$ 91,67/mês se 12 meses de acesso por 10 parcelas).
- **Regra para eval:** preferir **79,90** como piso “contrato fechado”; não misturar com vitrine R$ 99 promocional de redes sem anualizar TCO.

**Caso 5 — detalhe (Panobianco Jaiara)**

- Unidade **ativa** (Vila Jaiara); seg–sex 05h–23h; sáb/dom 08h–14h. ERP **EVO** — contrato disponível para matrícula online ([totem EVO](https://evo-totem.w12app.com.br/panobiancos/191/site/oportunidade)).
- **Site institucional** ([jaiara](https://www.panobiancoacademia.com.br/academias/jaiara)): **Silver R$ 39,90** (horário limitado na semana; só unidade escolhida) é vitrine agressiva mas **não comparável** 1:1 com musculação 24h das redes; **Gold R$ 99,90** (fins de semana em todas unidades*) é piso “academia completa” no site; **Platinum R$ 109,90** (rede ilimitada*); **Platinum+ R$ 139,90** sem fidelidade/adesão no site.
- **Venda online (EVO) — Platinum Mensal Recorrente R$ 139,90/mês** (sem permanência mínima no contrato; adesão zero na promo):
  - Musculação, área de cardio, aulas coletivas
  - **Sem taxa de adesão** · **Sem fidelidade**
  - **4 acessos/mês** em unidades **Panobianco CT**
  - **Acesso ilimitado** em unidades **Panobianco tradicionais**
  - **5 convidados/mês** · **Avaliação física gratuita**
- **Orange Anual Recorrente:** 1º mês **R$ 0,99** (de R$ 119,90) — promo; valor estrutural após promo conforme contrato.
- **Comparável ao mercado:** Platinum online **139,90** = Smart **Smart** / Sky **SKY**; Gold site **99,90** compete com Smart **Fit** (119,90) e portal Next Fit recorrente (99,90) se ignorar restrições do Silver.

### Síntese do benchmark (5 unidades — Anápolis, 01/06/2026)

| Faixa | Mensalidade estrutural | Quem |
|-------|------------------------|------|
| **Piso absoluto (restrições)** | R$ 39,90 | Panobianco Silver (horário/unidade) |
| **Piso contrato 12m fechado** | R$ 79,90 | Portal Next Fit (unidade a confirmar) |
| **Piso rede / musculação ampla** | R$ 99,90 – R$ 119,90 | Panobianco Gold · Smart Fit Fit · Skyfit ÁGUIA (anual) |
| **Recorrente sem fidelidade (rede)** | R$ 139,90 – R$ 149,90 | Sky SKY · Smart Smart · Panobianco Platinum (EVO/site+) · Bluefit BLUE |
| **Premium / rede ampliada** | R$ 159,90 – R$ 214,90 | Smart Black · Sky PRIME · Bluefit Premium(+) |

**Leitura vs. relatório golden (Low Cost):** mercado real em Anápolis concentra **R$ 99,90–149,90** para planos comparáveis; **R$ 79,90** (independente) e **R$ 39,90** (Panobianco restrito) são outliers — o DR/ticket do relatório deve explicitar se usa piso **com ou sem** restrição de horário/rede.


## Aprovação
- [x] Veredito correto
- [x] Score dentro da faixa esperada
- [x] Modelo recomendado faz sentido
- [x] Campos críticos validados
- [x] Notas do curador preenchidas

*Aprovado em 01/06/2026 — benchmark 5/5 + scores conferidos; pendências de produto (CNPJ vs raio, candidatos DB) permanecem nas notas.*
