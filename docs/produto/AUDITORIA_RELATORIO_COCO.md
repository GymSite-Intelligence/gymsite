# Auditoria cruzada — Relatório Cocó (4b211a02) · Etapa 1

> 2026-07-05, disparada pela comparação com OndeAbrir. Escopo: demografia, scores,
> viabilidade×resumo, ERRC, preços/banda tarifária, quadro Demanda (matemática + legendas).

## 1. Demografia — número CONFERE, rótulo não

- **60.165 hab no bairro** é internamente consistente: 22.645 domicílios × 2,66
  moradores/dom = 60.236 ≈ 60.165 ✓; 22.645 ÷ 105 setores = 216 dom/setor (faixa IBGE) ✓.
- ⚠️ Inconsistência de RÓTULO na própria seção: card diz "105 setores censitários",
  rodapé do quadro etário diz "183 setores agregados". Um dos dois está errado ou são
  bases diferentes sem explicação. Corrigir + carimbar TODO número: "X hab · base Y ·
  Censo 2022" (mesma régua que cobramos do OndeAbrir).
- Comparação com OndeAbrir é maçã×laranja legítima: nosso 60,1k = BAIRRO REAL (polígono);
  os 27,6k deles = raio de 1 km (3,14 km²). Ambos certos, bases diferentes — rotular sempre.

## 2. Viabilidade "Indeterminado" × Resumo "Mid Market" — contradição de propagação

Causa provável (evidência do run de junho): `score_concorrencia = 0.0` e
`panorama_competitivo = None` → A8 marca viabilidade/oceano INDETERMINADO. Mas o A4 roda
os benchmarks financeiros mesmo assim e recomenda modelo; o Resumo Executivo consome
`modelo_recomendado` sem checar o veredito de viabilidade. **Fix:** quando viabilidade =
INDETERMINADO, o resumo deve dizer "Mid Market sugerido POR BENCHMARK — demanda local não
validada neste run" (propagar o estado, não escondê-lo). Investigar por que
score_concorrencia zerou com 20+ concorrentes coletados (guard do A8?).

## 3. Matriz ERRC — determinística, MAS com base enviesada (bug confirmado)

- **Não é hardcode nem chute de LLM**: `_gaps_reais()` (a9_positioning_strategist.py:315)
  calcula penetração de serviços sobre `concorrentes_detalhados` usando oferta real
  extraída de site+Instagram (`competitor_offer_mapper.py`, keyword matching, sem LLM).
  O LLM é SOBREPOSTO pelo dado ("fonte_gaps: deterministico_oferta_concorrentes").
- **O bug:** a base só contém as academias TRADICIONAIS analisadas — o filtro de
  relevância do A3b (competitor_tools.py:315-393) REMOVE crossfit/lutas/studios de um
  relatório tipo "academia". Resultado: Eikō Artes Marciais, Krav Maga FSAKM e TBOX/box
  estão na praça mas invisíveis pro cálculo → "artes marciais/crossfit: nenhum concorrente
  oferece" com porta especializada na esquina. Além disso, Smart Fit tem site JS-rendered
  (mapper pula, documentado) → oferta dela também não entra.
- **Fix em 2 camadas:** (a) penetração calculada sobre o PARQUE do raio (incluindo
  especializados excluídos do relatório-alvo), com peso "porta especializada existe";
  (b) rotular honestamente: "entre as N academias tradicionais com oferta mapeada".
- **Avaliação física como gap:** legislação federal NÃO obriga avaliação física de entrada
  (CREF exige profissional habilitado; anamnese é recomendação; alguns estados exigem
  atestado médico). Mas academias grandes costumam oferecer — "nenhum oferece" é
  implausível; provável falha de extração (serviço não anunciado em site/IG ≠ não
  oferecido). TODO: validar enunciado com o agente Regulatório e trocar "não oferece"
  por "não anuncia" quando a fonte é site/IG.

## 4. Preços e banda tarifária

- **Indicador "R$ 69,99–107,00/mês":** hipótese forte = faixa de mensalidade do segmento
  econômico da cidade vinda do A7/market_context (benchmark), NÃO medição dos concorrentes
  do raio. Confirmar campo de origem e ROTULAR ("benchmark econômico Fortaleza", não
  "preços da concorrência").
- **Posicionamento R$ 185 · banda R$ 100–350:** determinístico do A4 (`parametros_
  metodologia` + renda do bairro): piso = ticket mínimo sustentável do modelo; teto =
  % da renda local + percentil do tier. Documentar as variáveis NA LEGENDA do quadro
  (o leitor não tem como saber).
- **Preços reais da concorrência (coletados à mão pelo Marcelo):** Smart Fit Papicu
  129,90/149,90/159,90/169,90 · VS Club 70,00 · Parque Esportes 319,99. O
  `competitor_offer_mapper` JÁ tenta capturar planos_precos, mas Smart Fit é JS (pulada)
  e cobertura é parcial. **Feature:** seção "Planos e preços da concorrência" no
  relatório com os capturados + banda observada (min 70 – max 319,99 valida a banda
  calculada 100–350 ✓, e mostra que o low-cost real da praça fura o piso).

## 5. Quadro "Demanda — Matrículas vs Capacidade": MATEMÁTICA ✓, LEGENDAS DESALINHADAS

**Auditoria numérica (área de referência 900 m², reproduzida):**
- Matrículas: 1,5/2,2/3,0 ×900 = 1.350/1.980/2.700 (low) ✓ · mid e premium idem ✓
- Capacidade física: 0,55/0,40/0,25 ×900 = 495/360/225 ✓
- Pico realista: matr × freq ÷7 ×25% → low 1.980×2,5/7×0,25 = 176,8 ✓ · mid 90 ✓ · prem 34,7 ✓
- Folga: 1−176/495 = 64,4% ✓ · 75,0% ✓ · 84,9% ✓
- Pico agressivo: 2.700×2,5/7×0,25 = 241≈240 ✓ · 116 ✓ · 52≈51 ✓
- Receita destravável: (teto−realista)×ticket → tickets implícitos R$ 95/178/341
  (coerentes com banda 100–350) ✓
- Colchão 85%: (0,85×capacidade − pico)÷fator pico → +2.741≈2.752 ✓ · +3.024 ✓ · ~2.497 ✓
**Conclusão: o motor calcula certo e é reproduzível.**

**O problema são as LEGENDAS: estão deslocadas (off-by-one) e duplicadas.** Ex.: o texto
sob "Colchão até reclamação" explica a Receita destravável; o de "Share de pico" explica
o Colchão; "m² por pessoa" carrega o texto do Break-even; "Pico no agressivo" repete a
legenda de Frequência. Bug de mapeamento métrica→tooltip no builder do quadro (A6/pdf).

**Legendas corrigidas em linguagem simples (colar no builder, na ordem):**
1. *Matrículas conservador* — "Piso: se a conta fechar já neste cenário pessimista, o risco é baixo."
2. *Matrículas realista* — "Base das projeções de receita (benchmark nacional ACAD/Sebrae; calibração com a demanda do bairro entra na próxima versão)."
3. *Matrículas agressivo* — "Teto que a indústria comprova: a Smart Fit média ~2,5 mil matrículas/clube. Estreante não começa aqui."
4. *Capacidade física simultânea* — "Quantas pessoas treinam AO MESMO TEMPO com conforto. Varia por modelo porque cada um ocupa o espaço de um jeito."
5. *Teto de mercado* — "Máximo de matrículas que o MERCADO sustenta nesta área (≠ teto físico do prédio)."
6. *Pico calculado* — "Pessoas dentro da academia no horário mais cheio: matrículas × idas/semana ÷ 7 × 25% (fatia do pico)."
7. *Folga de capacidade* — "Quanto sobra no horário de pico. Ideal 40–70%: menos = fila e cancelamento; muito mais = aluguel pago por espaço vazio."
8. *Freq. semanal* — "Vezes que o aluno treina por semana (setor: 2,0–2,5x)."
9. *Pico agressivo × capacidade* — "Teste de estresse: mesmo no cenário máximo da indústria, o prédio aguenta? ✓ = sim."
10. *Receita destravável* — "Quanto dá pra faturar A MAIS crescendo do realista até o teto de mercado — marketing, sem obra."
11. *Colchão até reclamação (85%)* — "Matrículas a mais que cabem antes do pico bater 85% da capacidade — o ponto onde nascem as reclamações de lotação (visto nos reviews da praça)."
12. *Break-even ÷ teto* — "Fatia do teto de mercado necessária só pra pagar as contas. Acima de ~60%, o modelo exige execução quase perfeita."
13. *Share de pico medido* — "No SEU bairro, o pico real concentra 17% dos alunos (medido em 3 concorrentes) vs 25% assumido — a premissa está conservadora a seu favor."
14. *m² por pessoa no pico* — "Espaço por aluno no horário cheio (conforto percebido)."

## 5b. Achados da leitura do PDF real (4b211a02, 05/07 — 8 págs)

**CORREÇÕES à auditoria acima:**
- §4: a seção "Planos e preços da concorrência" **JÁ EXISTE** no PDF (pág. 2: Smart Fit
  129,90/169,90 · VS Club 70 · Parque/Wellhub 319,99, via SearchAPI) + tertis de ticket
  por segmento (pág. 3). O "não está no relatório" valia pro mini/versão anterior.
  O "Ticket médio local R$ 69,99–107,00" provavelmente deriva desses planos coletados
  (faixa do segmento econômico/mediano) — confirmar fórmula na Etapa 2 e ROTULAR.
- §5: as legendas do quadro Demanda estão **corretas no frontend** (verificado em
  CenarioFinanceiroTable.tsx — cada métrica com seu tooltip). O quadro nem existe no PDF.
  O desalinhamento colado na revisão foi artefato da extração manual (tooltips copiados
  em sequência). NÃO-BUG; fica a sugestão de levar o quadro ao PDF um dia.

**BUGS NOVOS (mais graves que os anteriores):**
1. **Parque Estadual do Cocó (26.383 avaliações!) e ARENA COCÓ BEACH listados como
   "concorrentes no bairro"** (pág. 4) — o gate bairro+tipo deixou passar um parque
   público e uma arena de beach tennis como academias. Falso positivo que mina a
   credibilidade da contagem autoritativa (10).
2. **"Analisados a fundo: 1"** (cross-check, pág. 3). A oferta-base do ERRC vem de 1
   concorrente analisado + 3 com planos coletados → serviços entregues mapeados = só
   "Musculação" → TUDO vira "oportunidade de CRIAR". Confirma e agrava o §3: o gap não
   é só o filtro de especializados; é a base de oferta minúscula. Com TBOX (crossfit),
   Krav Maga (artes marciais) e S3 (personal) MAPEADOS na própria página, o ERRC diz
   "nenhum concorrente oferece crossfit/artes marciais/personal".
3. **Célula "População" VAZIA** na tabela Demografia do PDF (pág. 2) — o dado existe
   (60.165 no front) mas não renderiza no PDF.
4. **Selo INVIAVEL sem motivo:** Econômico tem margem 32% e payback 16m e recebe
   INVIAVEL (pág. 4) — o guardrail que reprova (piso de ticket? aluguel?) não é
   explicado ao leitor. Premium idem (10%/172m — esse é óbvio). Exibir o MOTIVO.
5. **Contagens múltiplas sem reconciliação no topo:** Sumário diz "Concorrentes 10";
   Inteligência Competitiva mostra 3; Anéis 3; cross-check 20/10/1/9. O cross-check
   (ótimo!) reconcilia — mas está na pág. 3 e o Sumário da pág. 1 não aponta pra ele.
6. Rótulo "Rating médio 4.5 (recom.)" — "(recom.)" sem explicação.

**Rastreabilidade fonte→fórmula (auditoria de metodologia, não de telas):**

- **Renda "per capita" R$ 4.953 — fórmula encontrada e reproduzida** (`renda_bairro_loader.py`):
  `renda_pc = V06004 (rendimento médio do RESPONSÁVEL, Censo 2022 agregados por bairro)
  ÷ moradores_por_domicílio` → 13.175 ÷ 2,66 = 4.953 ✓ reproduz.
  **Dois achados:** (1) isso é uma PROXY de per capita (dilui a renda do responsável pelos
  moradores; ignora a renda dos demais) — não a renda domiciliar per capita oficial;
  (2) o rótulo do front "ref. 2022 (Censo/IDH)" está errado no "IDH": o caminho IDH-Renda
  (CKAN, inversão Atlas) NÃO pode ter gerado esse valor — a fórmula Atlas tem teto
  matemático de R$ 4.034 (`_ATLAS_RENDA_MAX`) e 4.953 o excede. Fonte real: IBGE 2022.
  **Fix de rótulo:** "Renda per capita (proxy: rendimento do responsável ÷ moradores/dom.)
  · IBGE Censo 2022". O viés (subestima domicílios com 2 rendas) entra na metodologia.
- **Novos CNPJ 90d = 31:** fórmula em api.py (bloco entrantes_cnpj_90d) sobre espelho RFB,
  janela 90d, CNAE fitness, cidade. Reproduzir contagem na Etapa 2 (exige acesso ao espelho).
- **Score 6.0 (bairro):** fórmula/pesos ainda NÃO auditados — item nº 1 da Etapa 2
  (reproduzir o 5.97→6.0 a partir de `parametros_metodologia` + componentes 10.0/1.9/6.0).
- Zoneamento: fonte CKAN/LUOS 236/2017 declarada no código e no PDF ✓ (metodologia visível).

## 5c. Confronto com a auditoria externa (Gemini Deep Research, 05/07)

Terceiro auditor independente sobre o MESMO PDF. Balanço:

**Confirmou nossos achados (com fontes):** Parque Estadual como concorrente (fix feito ✓);
ERRC com falsos gaps (fix feito ✓); rótulo da renda (fix feito ✓ — e a renda do responsável
que ele traz do Ipece, R$ 13.372, BATE com nossa base: 13.175 ✓ nosso espelho está certo,
só exibíamos a métrica sem rótulo adequado).

**O que ele achou e nós NÃO (vira trabalho):**
1. **CT Greenlife é o concorrente mais perigoso da praça e nosso relatório o tratou como
   "mapeado 3.9"**: 3.000 m², crossfit, recovery/crioterapia, nutricionista, nutrólogo,
   fisio, kids, lutas (fontes: site oficial + Wellhub). Nosso offer_mapper só minera os
   ANALISADOS — o fix da praça inteira (por nome) não alcança serviço que não está no nome.
   → Camada 2 pendente: rodar offer_mapper (site+IG) em TODOS os concorrentes do bairro.
2. **Preços multi-fonte:** VS Club R$ 173–247 no Gurupass vs R$ 70 no nosso (capturamos o
   menor plano público sem rotular). Agregadores (Wellhub/Gurupass/TotalPass) são fonte
   rica de planos que não usamos — com ressalva: preço de agregador tem markup/condições
   próprias, rotular fonte em cada preço.
3. **Aderência por empreendimento** na Janela de Entrada: BS Rubi/Casa Monã (ultra-premium
   com academia no condomínio) = baixa aderência ao Mid Market; Sensia/Mood/Like
   (50–80 m²) = alvo primário. Classificável deterministicamente por m²/ticket.
4. **Like Residencial: 88 unidades, não 129** — nosso proxy superestimou. Validar fonte.
5. GTM acionável: pré-venda "Founder's Club" nos estandes das construtoras.

**Onde ELE erra (nossa vantagem estrutural):**
- **Contradição interna no aluguel:** afirma mercado a R$ 39,10/m² "consideravelmente
  abaixo do nosso piso de 60" (fonte que mistura residencial+comercial) e, páginas depois,
  que o aluguel real "supera com folga os R$ 60–75". As duas coisas ao mesmo tempo.
- **Conclusão dupla:** elogia nosso INDETERMINADO como cautela correta E decreta
  "VIABILIDADE COMPROVADA E ALTAMENTE RECOMENDADA" no mesmo capítulo.
- Casa Monã com duas datas de entrega (2026 e fev/2028) em trechos diferentes.
- Zero memória de cálculo: nenhum número reproduzível; prosa adjetivada no lugar de conta.
- Trata preço de agregador como "preço de balcão auditado" sem ressalva.

**Lições de FORMATO a adotar:** tabela de confronto por concorrente (estimado × auditado ×
serviços comprovados × risco); referências numeradas com URL + data de acesso; fio
narrativo demografia→elasticidade→posicionamento entre os blocos; coluna de aderência na
tabela de empreendimentos. Diferencial nosso a preservar: reproduzibilidade das contas
(que ele não tem) + consistência interna.

## 7. Etapa 2 EXECUTADA — memória de cálculo dos scores (07/07)

**Reprodução completa do 5.97/6.0 do Cocó, componente a componente:**

- **Demográfico 10.0 ✓**: pop_faixa ≥ 50.000 (+4) + renda 4.953 ≥ R$ 2.500 (+4) +
  base 2.0 = 10.0 (`calcular_score_demografico`, cortes em parametros_metodologia).
- **Competitivo 1.9 ✓ — e aqui morava um BUG**: a fórmula
  `bonus(saturação) + (10 − min(n×0,4, 4)×2)/10 − rating/5×2` com n=10 e rating 4,5
  dá 1.9 SOMENTE com saturação MEDIO (bônus 3,5). Com o rótulo EXIBIDO no relatório
  (SATURADO, bônus 0) dá **0.0**. Causa: o score era calculado com
  `classificar_saturacao(n, raio 3km)` — densidade que DILUI (10÷28,3 km² = MEDIO) —
  e depois o cross-check trocava o rótulo pra SATURADO (contagem no bairro ≥10)
  **sem recalcular o score**. Mesma família do bug do INDETERMINADO×resumo.
  **FIX aplicado no A6**: após o gate, recalcula score_concorrencia + score_bairro +
  score_top1 (antes/depois gravados no cross_check pra auditoria).
- **Viabilidade 6.0 ✓** (plausível): payback 26m na banda regular (+2) + ocupação no
  break-even na banda boa (+2) + base 2.0 = 6.0 (`calcular_score_viabilidade`).
- **score_bairro = MÉDIA SIMPLES das 3 dimensões**: (10 + 1,9 + 6)/3 = **5,97** ✓
  (o PDF exibe 6.0 arredondado). **Pós-fix, o Cocó recalcula pra (10 + 0 + 6)/3 =
  5,33** — mais conservador e coerente com o rótulo SATURADO.
- Sobre o run de junho (score_concorrencia = 0.0): consistente com a mesma fórmula
  recebendo SATURADO — os dois runs divergiam porque o INSUMO saturação vinha de
  réguas diferentes (densidade × contagem), não por mudança de fórmula.
- Regressão da memória de cálculo: `tools/test_score_metodologia.py` — se fórmula ou
  parâmetro mudar, os números mudam e o teste acusa.
- PENDÊNCIA menor registrada: o veredito heurístico do top1 é calculado ANTES do
  cross-check — com o score recalculado depois, pode ficar um degrau mais otimista
  que o score final (só afeta borda; revisar quando mexer no A8/veredito).

## 6. Fila da Etapa 2

- Metodologia dos NOSSOS scores: auditar como o motor calcula score_bairro,
  score_demografico, score_concorrencia e score_viabilidade — fórmulas, pesos e parâmetros
  (`parametros_metodologia`), reproduzindo a conta do 5.97 do Cocó passo a passo.
- Origem exata do indicador R$ 69,99–107 e das variáveis da banda (ler A4/A7 + params).
- Por que score_concorrencia=0 no run (guard A8).
- Contexto e Panorama de Mercado (coerência com market_context).
- Perguntar ao agente Regulatório sobre avaliação física/CREF (enunciado jurídico correto).
