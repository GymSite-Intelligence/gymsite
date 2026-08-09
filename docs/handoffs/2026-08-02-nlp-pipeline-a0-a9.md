# Handoff — NLP Intelligence Pipeline → GymSite (A0–A9 + consultor)

**Data:** 2026-08-02  
**Origem:** sessão Cursor em `vectra-hub` (exploração NIM + diagramas NLP capstone)  
**Destino:** agente / sessão no repo `C:\Users\marce\gymsite`  
**Escopo:** encaixe de pipeline NLP clássico (intent + sentiment + retrieve/rerank) no GymSite.  
**Fora de escopo:** endurecer preset CIOT / TMS no Vectra Hub — **não vale a pena** para este trabalho.

---

## 1. Decisão do humano

- Diagramas “NLP Intelligence API / Capstone Days 176–180” têm **mais sinergia com GymSite** do que com Vectra Hub / CIOT.
- Não tratar o diagrama como substituto do pipeline A0–A9 (Gemini + tools + Redis).
- Tratar como **camada barata** (classificação / sentimento / retrieve) **ao redor** do pipeline caro.

---

## 2. O que o diagrama é (definição fechada)

Arquitetura do capstone (duas figuras equivalentes: API flow + component architecture):

```
User Input Text
    → Preprocessor (normalize · tokenize · truncate)
    → Parallel Inference
         ├─ Intent Classifier  — DistilBERT + linear head · 6 intent classes
         └─ Sentiment Scorer   — LSTM / lexicon hybrid · score −1…+1
    → Response Selector (retrieve · rerank · return)
    → JSON Response
```

| Bloco | Tipo | Não confundir com |
|---|---|---|
| DistilBERT intent | **Fine-tune** classificador | LLM chat (Nemotron / Gemini) |
| LSTM + lexicon | Modelo + regras de sentimento | Heurística `rating >= 4` |
| Retrieve + rerank | IR / mini-RAG de **respostas prontas** | RAG Discovery + LLM gerando prosa |
| Pipeline NLP | Ponta a ponta classificação→resposta | Pipeline A0–A9 de relatório |

**Veredito:** é um **pipeline NLP** com pedaço fine-tuned + pedaço retrieve/rerank. Não é “só RAG” nem “só fine-tune”. Não é o stack NIM `integrate.api.nvidia.com`.

---

## 3. Como o GymSite faz NLP **hoje** (scripts)

### 3.1 Intent (consultor / conversacional)

| Item | Onde |
|---|---|
| Função | `classificar_intencao()` em `services/conversational_engine.py` |
| Método | **LLM** (Gemini) → JSON `{"intencao","confianca"}` — **não** DistilBERT |
| Consumidor | `api.py` (rotas conversacionais / disparo de relatório) |
| Classes atuais (8, não 6) | `novo_relatorio`, `pergunta_simples`, `status_relatorio`, `ajuda`, `clarificacao`, `encerrar`, `fora_de_escopo`, `indefinido` |

Prompt canônico: `_PROMPT_CLASSIFICACAO` no mesmo arquivo (~L110–130). Regra de ouro já no código: na dúvida entre consulta de dado e criar análise → `pergunta_simples` (criar relatório custa dinheiro).

### 3.2 Sentiment / dores (reviews concorrentes)

| Item | Onde |
|---|---|
| Sentimento grosso | `tools/competitor_tools.py` — `rating >= 4` → positivo, `<= 2` → negativo |
| Dores | `classificar_dores_reviews_deterministico` + opcional `classificar_dores_reviews_batch_gemini` (`CLASSIFICAR_DORES_GEMINI=1`) |
| Tool site | `agents_site/tools.py` — reviews + classificação determinística |

### 3.3 Retrieve / RAG (já existe, outro stack)

| Item | Onde |
|---|---|
| SPEC | `agents_site/specs/SPEC_RAG_AGENTES_SITE.md` |
| Engines | Discovery (market / equip / regulatorio / obra) |
| Papel | grounding dos 5 agentes de degustação — **não** Response Selector do diagram |

### 3.4 Pipeline A0–A9 (relatório)

Referência: `docs/arquitetura/PIPELINE_AGENTES.md`.

```
A0 ContextBuilder (LLM + override nums)
→ A1 GeoScout (det.)
→ Parallel: A2 Demo · A3a Search → A3b Analysis · A4 Financial
→ A6 ReportConsolidator (LLM)
→ A9 Positioning (det. + narrador)
```

Fora do hot-path principal: A5, A7, A8.  
Regra VEC: **LLM veste, não inventa número**. Intent/sentiment do diagram **não** geram `market_context` / financeiro.

---

## 4. Mapa: diagram → slots GymSite

| Slot | Encaixa? | Ação proposta | Não fazer |
|---|---|---|---|
| **Antes do A0** (consultor chat) | **Sim — melhor ROI** | Substituir ou gatear `classificar_intencao` com DistilBERT (6–8 classes alinhadas às atuais) | Não disparar A0–A9 sem intent `novo_relatorio` explícito |
| **A3a / A3b reviews** | **Sim** | Sentiment Scorer (−1…+1) no texto da review; alimentar card de dores | Não substituir A3a SearchAPI por NLP |
| **agents_site Response Selector** | **Parcial** | Retrieve+rerank para FAQ / recusas / CTAs curtos | Não substituir Discovery RAG + LLM dos especialistas |
| **A0 ContextBuilder** | Não | — | Classificador de intent não consolida mercado |
| **A1 / A2 / A4** | Não | — | Determinísticos / dados estruturados |
| **A6 / A9** | Quase zero | — | Precisam **gerar** narrativa, não puxar template |
| **A5 / A7 / A8** | Baixo | — | Fora do escopo deste handoff |

Fluxo alvo (conceitual):

```
Lead mensagem
  → Preprocessor
  → [Intent Classifier || Sentiment Scorer]
  → se intent=novo_relatorio (+ slots ok) → fila Redis A0–A9 (inalterada)
  → se FAQ / ajuda / fora_escopo → Response Selector → JSON
  → reviews A3a → Sentiment Scorer → state inteligencia_competitiva
```

---

## 5. Sinergia vs outros stacks (sessão de origem)

| Stack | Repo / uso | Relação com este handoff |
|---|---|---|
| NVIDIA NIM (`nim-chat.py`, Nemotron) | `vectra-hub/scripts/` + key `NVIDIA_API_KEY` | LLM OpenAI-compat; útil se GymSite quiser **provedor alternativo** em A6/narrador — **não** é o DistilBERT do diagram |
| NeMo Skills | research SDG/eval | Sem overlap operacional GymSite |
| Diagram DistilBERT/LSTM | Capstone | **Este handoff** |

Preset TMS/CIOT no `nim-chat.py` do Hub: **não endurecer** só por CIOT — irrelevante para GymSite.

---

## 6. Trabalho sugerido (próxima sessão no gymsite)

Ordem sugerida — multi-step:

1. **Inventário de intents reais**  
   Extrair do `_PROMPT_CLASSIFICACAO` + logs/`chat_interacoes` a distribuição das 8 classes. Decidir se DistilBERT usa 6 (colapsar) ou 8 (1:1 com código).

2. **Spike intent barato**  
   Dataset mínimo (mensagens rotuladas) → DistilBERT fine-tune ou baseline sklearn → comparar custo/latência vs `classificar_intencao` LLM. Gate: se confianca DistilBERT &lt; limiar → fallback LLM atual.

3. **Spike sentiment reviews**  
   Rodar scorer −1…+1 em sample de reviews A3a; comparar com heurística de estrela; métrica = acordo com dores nominadas.

4. **Não abrir PR no pipeline A0–A9** até spikes 2–3 terem número. A0–A9 permanece fonte da verdade do relatório.

5. **Docs a atualizar se spike for embora**  
   - `docs/arquitetura/AGENTE_CONSULTOR_CONVERSACIONAL.md`  
   - `docs/arquitetura/PIPELINE_AGENTES.md` (nota “camada NLP pré-pipeline”)  
   - Este handoff → marcar spike done/fail

---

## 7. Arquivos âncora (ler antes de codar)

| Arquivo | Por quê |
|---|---|
| `services/conversational_engine.py` | intent + slots + guardrails fora_de_escopo |
| `api.py` (rotas que chamam `classificar_intencao`) | wiring HTTP → fila relatório |
| `tools/competitor_tools.py` | sentimento + dores reviews |
| `agents_site/specs/SPEC_RAG_AGENTES_SITE.md` | RAG degustação (não misturar com Response Selector do diagram) |
| `docs/arquitetura/PIPELINE_AGENTES.md` | árvore A0–A9 |

---

## 8. Critérios de sucesso

- [ ] Intent local (ou híbrido) classifica `novo_relatorio` vs `pergunta_simples` com menos tokens LLM e sem regressão de “disparo caro indevido”.
- [ ] Sentiment de review não depende só de estrela quando o texto contradiz a nota.
- [ ] Zero mudança no contrato de saída de A0–A9 (`market_context`, `inteligencia_competitiva`, etc.) sem SPEC atualizada.
- [ ] Nenhum DistilBERT “no meio” do SequentialAgent A0→A9 sem ADR.

---

## 9. Mensagem curta pro agente que pegar isto

> Diagram NLP = Preprocessor → DistilBERT intent (6–8 classes) + LSTM sentiment → retrieve/rerank → JSON.  
> GymSite já faz intent via LLM em `conversational_engine.classificar_intencao` e sentimento via rating/keywords em `competitor_tools`.  
> Encaixe certo: **consultor pré-A0** + **reviews A3a/A3b**.  
> **Não** reescrever A0–A9 com DistilBERT.  
> Spikes primeiro; números; depois PR.  
> CIOT/Vectra Hub NIM fora do escopo.

---

*Handoff gerado 2026-08-02 · sessão vectra-hub → destino gymsite.*
