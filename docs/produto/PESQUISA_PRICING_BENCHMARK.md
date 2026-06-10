# Pesquisa de Pricing — Benchmark Verificado (Alicerce da Decisão de Monetização)

> Deep research executada em 2026-06-10. Metodologia: 5 frentes de busca paralelas, 20 fontes, 89 claims extraídos, 25 verificados adversarialmente (3 votos independentes por claim) → 19 confirmados, 6 refutados. Preços verificados ao vivo nas fontes primárias em 2026-06-10 — pricing pages mudam; revalidar antes de decisão final.

---

## 1. Conclusões Principais

### 1.1. Relatório avulso R$ 49–99: VALIDADO (confiança alta)

- Sebrae MS vende Estudo de Viabilidade Técnica Econômica de **120 horas por R$ 4.680 (promo) / R$ 15.600 (cheio)**. Fonte primária: loja Sebrae MS.
- Relatório GymSite a R$ 49–99 fica **50–300x mais barato** que consultoria tradicional não subsidiada, com margem ~91–95% sobre custo marginal de R$ 4,45.
- ⚠️ **Cuidado no discurso comercial:** existe EVTE subsidiado via Sebraetec por **R$ 126** ao empreendedor (90% subsídio) e plano de negócio MEI por R$ 1.400/20h. O pitch "100x mais barato" quebra se o prospect conhecer o canal Sebrae. Âncora segura: "consultoria de viabilidade custa R$ 5.000–15.000" citando preço cheio.

### 1.2. Pro R$ 99 é BARATO vs. bolso do ICP — existe espaço para tier intermediário

- **Tecnofit** (referência do que dono de academia já paga): parte de **R$ 269/mês + implantação**, preço escala por alunos ativos (50→2000+), média de marketing R$ 3,38–3,98/aluno/mês (real no tier de entrada: ~R$ 5,38/aluno). Fonte primária.
- **ABC Evo (W12)**: assinatura mensal dimensionada por **unidades + alunos**, sem preço público. **Nextfit**: sem preço público, só demo. Padrão do setor: mensalidade variável por porte, cotação gateada.
- **Pacto e Quiver**: nenhum preço confirmado.
- Implicação: GymSite Pro a R$ 99 custa menos que o piso do sistema de gestão que o ICP já assina → fácil vender como add-on do stack. **Gap claro entre R$ 99 e R$ 499** → tier intermediário ~R$ 199–299 para redes 2–10 unidades (inferência, não benchmark citável).
- Enterprise R$ 499 coerente com teto internacional de SaaS fitness (US$ 30–500+/mês: Mindbody $129–500, Glofox $110–200, Zen Planner $99–199) — sanity check de fonte fraca (roundup de concorrente), usar só como teto.

### 1.3. Insumo de dados é centavos — modelo de consumo puro existe no BR

- **BigDataCorp** (único player BR de dados com preço público): consumo puro pós-pago, **R$ 0,02–13,01 por consulta** (Companies API R$ 0,02; People API R$ 0,03; Processos Judiciais R$ 0,07), 500 consultas grátis/mês, boleto mensal. Fonte primária (docs oficiais).
- Confirma: custo marginal ~R$ 4,45/relatório é consistente; qualquer preço acima de R$ 49 tem margem enorme.

### 1.4. Modelo híbrido créditos+assinatura: validado, mas LANÇAR SIMPLES

- Híbrido é padrão de mercado: ~43–61% dos SaaS usam alguma forma (Chargebee/OpenView 2025); modelos de crédito +126% YoY no índice PricingSaaS 500.
- **Best practice convergente (Metronome/Stripe, m3ter, Lago, Flexprice):** começar com **assinatura + franquia de uso inclusa** (ex: Pro inclui N relatórios/mês). Pacote de créditos avulso só DEPOIS de validar a assinatura. Quote: "Start simple. Don't over-engineer. Begin with subscriptions + included usage."
- Dois modelos estruturais de crédito: committed-spend em R$ (estilo Snowflake) vs. crédito como moeda proprietária por SKU (estilo Clearbit). Rollover entre períodos é raro no mercado; Snowflake faz rollover condicional à renovação.
- Praticantes descrevem créditos como "workaround, não resposta de longo prazo" — degrau rumo a usage pricing.

### 1.5. Armadilhas documentadas do modelo de créditos

1. **Burn rate confuso:** definir claro quanto custa cada ação ("1 crédito = 1 relatório" simples; evitar tabela de pesos opaca).
2. **Pool de time:** power user drena saldo do time → disputas. Exigir caps por usuário se houver pool.
3. **Overage pós-pago:** expõe a risco de inadimplência (conta surpresa).
4. **Expiração/breakage:** best practice ~12 meses de validade + lembretes automáticos. Anti-exemplo documentado: **Apollo.io** (US$ 49–119/usuário/mês, franquia de créditos por tier) expira créditos no fim de cada ciclo, sem rollover nem reembolso — fricção conhecida e principal reclamação do modelo.

### 1.6. Risco jurídico não avaliado

Nenhuma fonte cobre CDC/legislação brasileira sobre expiração de créditos pré-pagos (analogia: créditos de celular pré-pago já foram limitados por Anatel/Justiça). **Validar com jurídico antes de fixar política de expiração.**

---

## 2. Lacunas — o que a pesquisa NÃO encontrou (segue aberto)

| Lacuna | Por quê | Como fechar |
|---|---|---|
| Pricing Geofusion/OnMaps, Cortex, Maplink, Serasa geomarketing | Pricing 100% fechado/negociado, nada público sobreviveu à verificação | Licitações públicas (PNCP), propostas comerciais, mystery shopping, ex-clientes |
| Willingness-to-pay por ICP (consultor fitness, single-unit, rede, franqueadora) | Zero evidência verificada | **Entrevistas da Fase 0** (5–10 por ICP) |
| Custo por lead qualificado para fornecedores de equipamentos | Zero benchmark sobreviveu | Conversar direto com fornecedores (Movement, Life Fitness BR, TechnoGym BR) |
| Split real de receita créditos vs. assinatura em SaaS maduros | Benchmarks encontrados foram refutados | Sem fonte pública confiável |

---

## 3. Números REFUTADOS na verificação — NÃO usar

- ~~Margem de breakage intencional de 30–50%~~ (0-3)
- ~~Cap típico de rollover de 20%~~ (0-3)
- ~~Churn de 20% por falta de visibilidade de saldo~~ (0-3)
- ~~Apollo top-up a US$ 0,20/crédito com mínimos 250/2.500~~ (1-2)
- ~~Airtable/Monday/Copilot usam créditos+top-up~~ (0-3)

---

## 4. Recomendação Derivada (síntese, não benchmark — validar na Fase 0)

| Oferta | Preço sugerido | Ancoragem |
|---|---|---|
| Relatório avulso | R$ 49–99 | 50–300x abaixo de consultoria não subsidiada; margem 91–95% |
| Pro | R$ 99/mês **com 2–3 relatórios inclusos** | "Subscription + included usage" (best practice); abaixo do piso Tecnofit R$ 269 |
| Tier intermediário (novo) | ~R$ 199–299/mês | Gap entre Pro e Enterprise; redes 2–10 unidades; espelha eixo unidades+alunos do setor |
| Enterprise | R$ 499/mês com eixo de escala (unidades analisadas ou seats) | Coerente com teto internacional |
| Pacote de créditos | Fase 2, após validar assinatura | 1 crédito = 1 relatório; validade 12 meses + lembretes; sem expiração mensal estilo Apollo |
| Lead gen fornecedores | Sem benchmark — negociar caso a caso | Fechar lacuna com entrevistas |

---

## 5. Fontes Primárias Verificadas

- https://docs.bigdatacorp.com.br/plataforma/docs/tabela-de-pre%C3%A7os
- https://www.tecnofit.com.br/precos/
- https://www.tecnofit.com.br/precos_/grandes-redes/
- https://w12.com.br/sistema-para-academia/
- https://ms.loja.sebrae.com.br/estudo-de-viabilidade-tecnica-economica-77197
- https://www.apollo.io/pricing/about-credits

Secundárias (guidance de billing, viés de vendor reconhecido): Metronome/Stripe, m3ter, Lago, Flexprice, Schematic, Cognism.
