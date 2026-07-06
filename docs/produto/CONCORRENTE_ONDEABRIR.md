# Concorrente: OndeAbrir (ondeabrir.com)

> Análise 2026-07-05, feita com conta real do Marcelo (pacote 5 análises / R$ 99; 3 usadas,
> nenhuma gasta nesta análise — usei o histórico). Fontes: relatório Cocó/Fortaleza deles
> (score 7.7, 21/06), blog `/blog/como-abrir/academia` e página programática `/academia/fortaleza`.
> Confronto: nosso rpt_1781804284 (mesmo bairro Cocó, 18/06).

## 1. O que eles são

Geomarketing HORIZONTAL (23+ tipos de negócio, academia é um deles) por ponto/endereço,
raio 1 km, self-service, R$ 99/5 análises. Fontes declaradas: IBGE, Receita Federal,
Google Maps, OpenStreetMap. Nós: VERTICAL fitness, análise por bairro com motor de
viabilidade financeira por modelo de operação.

## 2. Confronto no MESMO bairro (Cocó, Fortaleza)

| Dimensão | OndeAbrir (7.7 "Muito Boa") | GymSite (5.97 "INVESTIGAR MAIS", SATURADO) |
|---|---|---|
| Concorrentes | ~20 no raio 1 km ("baixa concorrência"!) | 37 no raio 1 km / 211 em 3 km (auditado) |
| Veredito | Otimista — nota 9.0 pra concorrência | Conservador — saturação ALTA |
| Renda | R$ 15.786 (500m) / 10.431 (1km) / 8.847 (2km) — por raio, IBGE Censo 2022 | renda do bairro no market_context (menos granular na exibição) |
| Aluguel | "estimado R$ 50–100/m²" (heurística) | MRLR determinístico + benchmark (R$ 30–94/m², mediana ~69) — MELHOR |
| Financeiro | Faturamento estimado R$ 105–195k/mês + potencial de consumo POF (R$ 9,3 mi/mês região) | 3 cenários por modelo (low/mid/premium) com payback — MELHOR em profundidade |
| Reviews | Resumo LLM de 50 reviews/10 estabelecimentos: percepção, perfil público, reclamações, oportunidades | dores_dominantes rankeadas + servicos_nao_oferecidos — mesmo insumo, exibição pior |
| Zoneamento | "consulte a prefeitura" (link REDESIM) | CKAN oficial com mapa SVG e compatibilidade CNAE — MUITO MELHOR |
| Tendência CNPJ | Série 2015–2024 (378 aberturas/242 fechamentos, por ano, MEI×formal, capital social típico R$ 52,5k, porte) | entrantes_cnpj_90d (mais FRESCO, menos histórico) |
| Ponto físico | Fluxo estimado 80/100, conversão do ponto 6.7 (pesos: via/estacionamento/âncoras), 21 estacionamentos, âncoras com distância, Street View | análise por bairro (avisamos que independe do imóvel) + top_3_candidatos de imóveis |

**INCONSISTÊNCIA DELES (munição):** o próprio blog prega "máx. 1 academia por 3–5 mil hab
no raio de 1 km". Com 27,6 mil hab/1 km no Cocó, o teto ideal deles seria 6–9 academias —
eles acharam 20 e ainda chamaram de "baixa concorrência / oportunidade clara", nota 9.0.
O score deles é inflacionado pra converter (todo lugar é "bom"); o nosso é honesto.
Nos posts P3: "dois relatórios, mesmo bairro: um diz 'oportunidade clara', outro mostra
211 espaços fitness no raio. Qual protege seu dinheiro?" (sem citar marca).

**Divergência a INVESTIGAR (pode ser bug nosso ou deles):** contagem de concorrentes
1 km — eles ~20, nós 37 (Places Aggregate auditado). Tipos incluídos diferem
(eles Google Maps textual, nós gym+fitness_center). Vale reproduzir com os mesmos tipos.

## 3. O que vale APROVEITAR (priorizado)

1. **Exibição de renda por raio (500m/1km/2km) + perfil etário + % público-alvo 18-45**
   — dado que JÁ TEMOS (censo/setores censitários) mal exibido. É o número que o dono entende.
2. **Percepção da região narrada** — nossos dores_dominantes viram 3 blocos: "perfil do
   público / reclamações frequentes / oportunidades". Mesmo insumo, storytelling melhor.
3. **Score decomposto com nota por dimensão** (concorrência 9.0, renda 9.0…) — nosso mini
   mostra só 5.97; decompor gera confiança e conversa.
4. **Série histórica CNPJ 2015-2024 + capital social típico do setor** — temos RFB nos
   espelhos BQ; combinar com nosso entrantes_90d (fresco) = melhor dos dois mundos.
5. **Fatores operacionais do ponto** (tipo de via, estacionamentos, âncoras c/ distância)
   — usar nos top_3_candidatos de imóveis; POIs via OSM/Places que já consumimos.
6. **Potencial de consumo POF** (gasto médio domicílio × domicílios no raio) — 1 conta
   com dados IBGE POF que já dá número de faturamento defensável.
7. **Próximos passos com links oficiais** (REDESIM, SEBRAE, Portal Empreendedor) — barato,
   e nosso Playbook de Abertura já faz melhor; expor 2 passos grátis como teaser do playbook.
8. **PDF de download no free** — eles dão; nós gateamos. Avaliar PDF resumido com marca.
9. **SEO programático** (`/academia/{cidade}`, `/mercado/academia/{cidade}`, `/franquia/
   {rede}/{cidade}`, guia "como abrir academia") — máquina de aquisição deles. Nosso motor
   gera conteúdo MELHOR por cidade (viabilidade real). Roadmap de marketing.
10. **Página "vs" comparativa** (eles têm vs consultoria/Google Maps/análise manual) —
    fazer as nossas, incluindo "análise por ponto vs análise de viabilidade".

## 4. Dados de renda do blog deles (pra cruzar/calibrar)

- Fortaleza: renda média per capita R$ 1.399 (IBGE, página da cidade).
- Cocó por raio (relatório): 500 m R$ 15.786 · 1 km R$ 10.431 · 2 km R$ 8.847
  (renda do responsável do domicílio, Censo 2022, 44 setores censitários no raio de 2 km).
- Benchmark do guia: investimento R$ 100–500k · faturamento R$ 20–100k/mês · margem 15–30%
  · payback 18–30 meses · mensalidade média R$ 80–250 · retenção 50–60%/ano
  · capacidade 200 m² ≈ 150–200 alunos · ponto de equilíbrio 100–150 alunos.
  ⚠️ Números DELES — usar só como referência de calibração, nunca publicar como nossos.

## 4b. Análise do PDF deles (9 páginas, Cocó — emitido 05/07)

**Pesos do score revelados (p.2):** Concorrência 20% · Renda 20% · CNPJ 15% · Fluxo 15% ·
População 10% · Acessibilidade 10% · Infraestrutura 10%. Score "calculado sobre raio de
2 km para estabilidade estatística" — mas as seções misturam raios 1/2/5 km.

**Inconsistências internas (mesmo relatório, números diferentes por superfície):**

| Métrica | Dashboard | PDF | Problema |
|---|---|---|---|
| Faturamento estimado | R$ 105–195k/mês | R$ 34–63k/mês | **3× de diferença** (raio 2km vs 1km, sem avisar a mudança de base) |
| Potencial de consumo | R$ 9,3 mi (2,4%/dom) | R$ 3,5 mi (2,8%/dom) | base E percentual POF mudam entre telas |
| Multiplicador de renda | 4,2× nacional | 5,0× nacional / 5,3× e 6,2× municipal | 4 multiplicadores diferentes pro mesmo lugar |
| Transporte público | "6 pontos trazem fluxo constante" (ponto positivo) | componente transporte = **0/100** | contam bicicletário como transporte |
| Contexto de mercado | — | "aberturas superou fechamentos em 56%, indicando mercado em **declínio**" | frase se contradiz sozinha |

Lição pra nós: número que muda conforme a tela destrói confiança — o motor V3 ser fonte
única (mesmo JSON pro site, PDF e e-mail) é vantagem estrutural; nunca gerar número na
camada de apresentação.

**O que copiar do PDF deles (pro nosso A9/pdf-report):**
1. Rodapé com fontes em TODA página + "dados atualizados MM/AAAA" + "emitido em".
2. Score decomposto com pesos explícitos na página 2 (transparência que gera confiança).
3. Etiqueta de raio por seção ("dados desta seção referem-se ao raio de 1 km") — nós
   devemos fazer igual com bairro/raio.
4. Checklist de validação presencial (seção 6) — genérico neles; o nosso pode ser gerado
   do relatório (ex.: "confirme o aluguel pedido vs teto de R$ X/m² do seu modelo").
5. Tabela de concorrentes com distância em metros + nº de avaliações.
6. Disclaimer final sóbrio ("orientativo, não substitui consultoria").

**Gap deles que confirmamos:** ticket médio = "sem dados de preço suficientes" — nosso
A3b/A4 com ticket por modelo preenche exatamente o buraco que eles admitem ter.

## 5. Onde ganhamos hoje (defender no posicionamento)

Vertical fitness (modelo de operação, dimensionamento, equipamentos), viabilidade
financeira real (3 cenários + payback + guardrail de aluguel 12–15%), zoneamento oficial
com mapa, aluguel determinístico vs estimativa, imóveis candidatos reais, honestidade do
veredito (INVESTIGAR MAIS vs 7.7 pro mesmo bairro), playbook de execução pós-aprovação,
consultor conversacional. Eles ganham em: UX do relatório, granularidade por raio,
ponto físico, preço público claro (R$ 99/5), PDF e máquina de SEO.
