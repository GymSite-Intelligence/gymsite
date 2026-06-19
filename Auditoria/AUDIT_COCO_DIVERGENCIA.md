# Auditoria de Divergência — Relatórios de Cocó (Fortaleza)

> Data: 2026-06-19 · 32 relatórios (23 done) · mesma praça, resultados muito diferentes.

## Divergência observada (mesma praça)

| Campo | Faixa observada | Swing |
|---|---|---|
| Aluguel mensal | R$ 17.000 → R$ 88.550 | **5×** |
| Renda média bairro | (ausente) → 2.095 → 4.952 | **2,4×** |
| nº concorrentes (nC) | 3 → 10 | **3×** |
| Saturação | BAIXO / MEDIO / SATURADO / ALTO | todos os níveis |
| Score viabilidade | 0 → 10 | tudo |
| Modelo / Veredito | Low Cost / Mid / Premium · APROVADO / INVESTIGAR | varia |

## Causa-raiz (4) — separadas por tipo

### 1. Aluguel — NÃO-DETERMINÍSTICO (o cerne) 🔴
Dois problemas somados:
- **(a) Fonte alterna**: "Portais municipais (ZAP/Viva)" vs "Search Grounding (LLM, mediana)". Métodos diferentes → 88.550 (Grounding) vs 17–49k (Portais).
- **(b) Amostragem não-cacheada**: dentro de Portais, cada run **raspa listings diferentes** → mediana muda toda vez (17.000 / 18.573 / 19.640 / 21.516 / 30.314 / 49.082 / 79.062...). **Mesma praça, mesmo método, valor diferente.** É EXATAMENTE o problema: rodar a mesma praça e achar dado diferente.

### 2. Renda — MUDANÇA DE CÓDIGO/FONTE 🟡
Ausente → 2.095 (06-15) → 4.952 (06-17 em diante). A nacionalização `renda_bairro` / censo v-codes trocou a fonte no meio de junho. 2.095 vs 4.952 = 2,4× → muda ticket/viabilidade/modelo. **Evolução de código, não ruído** — mas relatórios de antes/depois não são comparáveis.

### 3. nº concorrentes — NÃO-DETERMINÍSTICO + gate novo 🔴/🟡
- Places/SearchAPI retorna lista variável run-a-run (não cacheada).
- Gate de status (CLOSED_*) + filtro bairro adicionados 18/06 mudaram a contagem.
- nC=3 (06-18 02:27) = run onde a busca voltou pouca.

### 4. Saturação — RECALIBRAÇÃO DE THRESHOLD 🟡
Params `saturacao_bairro_{medio,alto,saturado}_min` (3/6/10) adicionados 18/06. **Antes nC=7 → BAIXO; depois nC=7 (≥6) → ALTO.** Mesma contagem, classificação diferente = mudança de regra.

## Veredito

| Causa | Tipo | Fix |
|---|---|---|
| Aluguel (fonte alterna + amostragem) | **não-determinístico** | **cachear em DB por praça** (1 coleta, reusa) + fonte única |
| nC concorrentes (lista varia) | **não-determinístico** | **cachear lista de concorrente por praça** |
| Renda (2095→4952) | código (evolução) | já estabilizou em `renda_bairro` nacional |
| Saturação (threshold) | código (recalibração) | já fixado em `parametros_metodologia` |

**2 causas são DADO não-determinístico** (aluguel + concorrente) — re-coleta a mesma praça e acha valor diferente. **2 são evolução de código** (renda + threshold), já estabilizadas.

## Direção (= o mapa de determinização)

Os dados que geram insight devem ser **coletados 1× por praça, cacheados em DB, reusados** — não re-raspados a cada run. Igual já foi feito com renda (`renda_bairro`), censo (`censo_setor`), geocode (`cache_geocode` hoje). Falta: **aluguel** e **lista de concorrente**.
