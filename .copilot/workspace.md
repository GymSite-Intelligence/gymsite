# Copilot Workspace: GymSite Antigravity

## Pasta Principal Selecionada
`gymsite_intelligence/agents/`

Esta pasta centraliza os "skills" (agentes fundamentais) usados no pipeline de avaliação comercial para academias. Serve como núcleo de automação para qualquer agente do Copilot operar o ecossistema GymSite.

---

## Skills Fundamentais do Agente
### 1. ContextBuilder (A0)
- **Arquivo:** agents/a0_context_builder.py
- Função: Pesquisa qualitativa (deep research), benchmarks, contexto de mercado com dados oficiais e insights via Gemini.
- Entrada: cidade, bairro, tipo de negócio, público alvo.
- Saída: contexto_mercado, insights, benchmarks.

### 2. GeoScout (A1)
- **Arquivo:** agents/a1_geoscout.py
- Função: Análise e ranqueamento de pontos comerciais. Busca no Google Maps, OLX, ImovelWeb, geolocalização e score.
- Entrada: localização, contexto do A0.
- Saída: top 3 imóveis, score, polos geradores.

### 3. DemoAnalyst (A2)
- **Arquivo:** agents/a2_demo_analyst.py
- Função: Enriquecimento demográfico, score, renda e faixa etária usando IBGE e benchmarks.
- Entrada: cidade, bairro.
- Saída: análise demográfica}

### 4. CompetitorSearch (A3a)
- **Arquivo:** agents/a3a_competitor_search.py
- Função: Mapeamento de concorrentes, reviews e enriquecimento por painéis públicos.
- Entrada: bairro, tipo_negocio.
- Saída: concorrentes_brutos.

### 5. CompetitorAnalysis (A3b)
- **Arquivo:** agents/a3b_competitor_analysis.py
- Função: Determina gaps, dores e oportunidades em concorrentes do A3a; calcula score de saturação.
- Entrada: concorrentes do A3a.
- Saída: inteligencia competitiva, scores, recomendações.

### 6. FinancialEstimator (A4)
- **Arquivo:** agents/a4_financial_estimator.py
- Função: Projeta cenários financeiros (aluguel, CAPEX, payback), renda e viabilidade.
- Entrada: candidatos, demografia, contexto.
- Saída: cenários financeiros, viabilidade.

### 7. ContactHunter (A5)
- **Arquivo:** agents/a5_contact_hunter.py
- Função: Busca decisor do imóvel, identifica tipo de ponto, script abordagem, contato.
- Entrada: top candidato, contexto negócio.
- Saída: contato_decisor, script.

### 8. ReportConsolidator (A6)
- **Arquivo:** agents/a6_report_consolidator.py
- Função: Consolida outputs dos agentes anteriores, define veredito, bairros alternativos e alertas.
- Entrada: outputs A0-A5.
- Saída: relatório executivo, veredito.

### 9. MarketResearch (A7)
- **Arquivo:** agents/a7_market_research.py
- Função: Pesquisa ad hoc de tendências de mercado. Chamada apenas sob demanda.
- Entrada: pergunta macro.
- Saída: resposta baseada em fontes dinâmicas.

---

## Prompt de Uso para Agente Copilot

> Você é o agente principal do GymSite Intelligence. Utilize cada skill-fundamental como uma macro-tool, executando sempre via script da pasta `agents/`, seguindo o fluxo sequencial `A0 → A6`. Só execute o `A7` caso solicitado para pesquisa de tendências ou falha de fontes.
>
> - Não duplique processamento nem rode etapas em paralelo antes do A2/A3/A4, cuja paralelização é garantida pela orquestração (ParallelAgent).
> - Garanta entrada e saída JSON em todas as etapas (use dicionários validados).
> - Sempre registre o progresso e evidências em `state_diagnostics.jsonl` via macro-tool dedicada.
> - Ao receber inputs do usuário (cidade, bairro, etc), normalize usando padrões do frontend antes de rodar qualquer agente.
> - Dúvidas de negócio/score? Consulte os scripts em `/tools/`, especialmente para cálculo financeiro, benchmarks e KPIs.
> - Foque em gerar outputs interpretáveis, markdown e células de score claras para consumo dos dashboards e relatórios.

---

## Boas Práticas
- Nunca trafegue credenciais ou API keys em código/git (usar `.env` e variáveis de ambiente).
- Persistência de dados sensíveis por Supabase, nunca localmente.
- Use sempre as macro-tools consolidadas. Não invoque funções antigas de steps atomizados.
- Use logging detalhado no pipeline para diagnosticar erros LLM, custos e token usage.
- Mantenha compatibilidade com orquestração do ADK (Google ADK >=1.3.0), testando sempre no ambiente de staging.
- Outputs dos skills devem ser validados por schema antes de consolidar resultado final.
- Scripts de contato: personalize e valide se os dados do decisor estão completos.
- Para qualquer etapa nova, documente o skill e att README de `agents/`.

---
