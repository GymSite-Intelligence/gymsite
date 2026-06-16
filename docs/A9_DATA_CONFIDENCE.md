# A9 — Confiabilidade dos Dados no Relatório PDF

> Diretrizes de design para aumentar a **confiabilidade percebida** dos dados apresentados no relatório PDF gerado pelo agente A9, **sem citar nomes de fontes reais**. A confiabilidade vem da transparência metodológica (mostrar *como* o dado foi obtido) e não da autoridade de um provedor nomeado.

## Princípio central

O leitor confia mais em quem mostra o método e admite incerteza do que em quem apresenta números absolutos sem contexto. Toda a estrategia abaixo aproveita a arquitetura multi-agente existente (A1 geoscout, A2 demo_analyst, A3 competitor intel, A4 financial_estimator, A7 market_research, A8 validator) como lastro metodológico, sem revelar provedores externos.

## Opções de design

### 1. Selos de confiança por dado
Atribuir a cada métrica um badge de qualidade usando a paleta do projeto:
- **TEAL (#0D9488)** — "Dado medido" (alta confiança)
- **ORANGE (#E8751A)** — "Estimativa calculada"
- **SLATE (#64748B)** — "Inferência / projeção modelada"

Comunica honestamente o grau de certeza sem nomear ninguem.

### 2. Intervalos em vez de números absolutos
Apresentar faixas ("entre X e Y, base Z") transmite rigor estatístico. Combina diretamente com os 3 cenários financeiros (conservador / base / otimista) já previstos no design.

### 3. Box metodológico genérico
Seção "Como chegamos a estes números" em linguagem neutra: estimativas derivadas de cruzamento de dados geográficos públicos, modelagem de densidade populacional e benchmarks do setor. Descreve o processo real (A1/A4/A7) sem nomear provedores.

### 4. Datação e versionamento
Carimbar "Dados coletados em [data]", número de versão do relatório e janela de validade ("válido por X meses"). Dado com prazo de validade explícito parece auditável.

### 5. Amostragem e cobertura declarada
Indicar o escopo: "N concorrentes mapeados num raio de X km", "M pontos de interesse considerados". Dá lastro sem revelar a origem.

### 6. Margem de erro / nível de confiança
Para projeções financeiras, exibir "margem de ±X%" ou um mini gráfico de sensibilidade. Reforça visualmente que houve modelagem, não chute.

### 7. Triangulação visível
Mostrar que um número foi confirmado por mais de uma abordagem: "estimativa convergente entre análise de demanda (A2) e análise de oferta (A3)". Vários métodos chegando ao mesmo resultado = robustez.

### 8. Notas de rodapé por número
Superscritos ao lado de métricas-chave, remetendo a notas que explicam a derivação ("calculado a partir da densidade comercial da região"). Padrão de consultoria.

### 9. Distinção visual fato vs. interpretação
Usar tipografia/cor para separar dado bruto de recomendação do consultor. O leitor confia mais quando vê onde termina o dado e começa a opinião.

### 10. Critérios objetivos do veredito
Explicitar os critérios de cada classificação usando as VEREDITO_COLORS:
- **APROVADO (#16A34A)** = score >= X em demanda E margem positiva no cenário base
- **RESSALVAS (#CA8A04)** = condições parcialmente atendidas
- **INVESTIGAR (#EA580C)** = dados insuficientes para conclusão
- **REPROVADO (#DC2626)** = critérios mínimos não atingidos

Transforma um selo subjetivo em algo auditável.

## Prioridade recomendada

Se for implementar poucas, começar por:
1. **Selos de confiança por dado** (opção 1)
2. **Intervalos com 3 cenários** (opção 2)
3. **Box metodológico** (opção 3)

Esses três sozinhos já elevam muito a percepção de seriedade e encaixam na paleta/layout documentados em `docs/A9_REPORT_DESIGN.md`.

## Mapeamento por seção do PDF

| Seção do relatório | Técnicas de confiabilidade aplicáveis |
|---|---|
| Resumo executivo | Datação/versionamento (4), critérios de veredito (10) |
| Mercado / localização | Amostragem (5), box metodológico (3), notas (8) |
| Concorrência | Triangulação (7), amostragem (5) |
| Financeiro | Intervalos/3 cenários (2), margem de erro (6), selos (1) |
| Posicionamento | Distinção fato vs. interpretação (9) |
| Recomendações | Critérios de veredito (10), notas (8) |

---

*Documento de diretrizes — complementa `docs/A9_REPORT_DESIGN.md`. Nenhuma fonte real é citada; toda a confiabilidade é construída via transparência metodológica.*
