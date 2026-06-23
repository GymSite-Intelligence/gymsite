# 🏋️ AGENTS_GYMSITE.md — Guia Oficial dos Agentes GymSite Intelligence

> Guia mestre para **projetar, construir, configurar, avaliar e implantar** o time
> multiagente do GymSite Intelligence.
> Bases: documentação oficial ADK (Agents, Multi-agent, Tools, Code Execution,
> Callbacks, Planner/Gemini Thinking, Agent Config, Runtime, Deploy) + LiteLLM.
> **Norte de toda decisão: maior ROI, menor custo, menor latência.**
> Status (ADK code-first, `agents_site/`): **Técnico 🟢 montado/em teste** ·
> **Regulatório 🟢 montado/em teste** · **Mercado 🟢 montado/em teste (FunctionTool, não MCP)**

---

## Índice
1. [Princípios](#1-princípios)
2. [Melhores Práticas ADK](#2-melhores-práticas-adk)
3. [Regra de Ouro de Criação dos Agentes](#3-regra-de-ouro-de-criação-dos-agentes)
4. [Framework de Times de Agentes (ADK + LiteLLM)](#4-framework-de-times-de-agentes-adk--litellm)
5. [Agent Config & Deploy](#5-agent-config--deploy)
6. [Matriz dos Agentes GymSite](#6-matriz-dos-agentes-gymsite)
7. [Checklist Definition-of-Done](#7-checklist-definition-of-done)
8. [Operação & Pendências Manuais](#8-operação--pendências-manuais)
9. [Referências](#9-referências)

---

## 1. Princípios

Todo agente é **software code-first e não-determinístico**. O modelo decide
dinamicamente — projete, instrua e **avalie** assumindo isso. **Especialização +
hierarquia** vence o agente monolítico. Construa em camadas: 1 agente → multi-modelo
→ delegação → estado → guardrails → avaliação → deploy.

---

## 2. Melhores Práticas ADK

- **Code-first e modular:** lógica, tools e orquestração em código (Python/Go/Java) →
  modularidade, testabilidade, versionamento.
- **Arquitetura multiagente:** agentes especializados em hierarquia; o raiz delega por
  papel → mais confiável e escalável.
- **Orquestração certa por caso:** workflow agents (sequencial, paralelo, loop) para
  fluxos previsíveis; roteamento dinâmico via LLM para casos complexos.
- **Ecossistema de tools:** pré-construídas (Google Search, Code Execution), APIs
  custom, libs de terceiros, e **agentes como tools**. Dê só o necessário.
- **Dev experience:** CLI + Dev UI para rodar/testar/debugar localmente.
- **Avaliação integrada:** mede **resposta final + trajetória de execução**.
- **Ecossistema aberto:** vários LLMs (interface base), interoperabilidade, **MCP** e
  **A2A** para comunicação padronizada.
- **Deploy desde o início:** containerizado — Agent Engine (gerenciado), Cloud Run
  (serverless) ou GKE (controle máximo).

---

## 3. Regra de Ouro de Criação dos Agentes
*(todos os itens são obrigatórios, não opcionais)*

**3.1 Identidade** — `name` descritivo e único; **`description` afiada** (é o que o
raiz usa para rotear); `model` explícito.

**3.2 Instruções** — Markdown estruturado (`## PAPEL`, `## COMO AGIR`, `## REGRA DE
OURO`, `## ESCOPO`); few-shot quando o formato importa; guie o uso da tool (quando e
por quê); **anti-alucinação explícito**; escopo fechado; `global_instruction` no raiz.

**3.3 Estado/contexto** — `{var}`/`{var?}` nas instruções; **`output_key`** para passar
resultado entre agentes; **`include_contents='none'`** em tarefas stateless (menos
tokens).

**3.4 Saída estruturada** — `output_schema` (Pydantic) quando alimenta sistema/UI.
⚠️ `output_schema` + `tools` na mesma chamada tem suporte limitado → separe em
sub-agentes.

**3.5 Ferramentas** — docstrings claras (o LLM escolhe pelo nome+description+schema);
retorno padronizado (`{"status":...}`); **mínima superfície**.

**3.6 Planner / Thinking** — `BuiltInPlanner` com **`thinking_budget` calibrado**
(256–1024); `include_thoughts=OFF` em produção; `PlanReActPlanner` p/ modelos sem
thinking nativo.

**3.7 Code Execution / cálculo determinístico** — para QUALQUER número derivado
(ex.: nº de esteiras por pico), use cálculo determinístico em vez de "calcular de
cabeça". ⚠️ `BuiltInCodeExecutor` (e tools nativas como `google_search`) **NÃO coexiste
com outras tools no mesmo agente Gemini** → no GymSite o cálculo de dimensionamento é
uma **FunctionTool** (`dimensionar_cardio_por_pico`), que convive com o RAG do catálogo.

**3.8 Modelo & geração** — **Flash padrão**, Pro só sob demanda; **Vertex AI**
(`USE_VERTEXAI=true`) p/ fugir do free-tier/429; `temperature~0.2` em tarefas factuais;
`max_output_tokens` com teto. *(GymSite: Técnico/Regulatório temp 0.2; Mercado 0.3;
roteador 0.1; teto 512–1536.)*

**3.9 Callbacks** — `before_model` (guardrail/cache de entrada), `before_tool`
(validar argumentos), `after_*` (normalizar/logar custo).

**3.10 Avaliação** — cenários predefinidos = as **5 perguntas de cada doc**; valida
resposta **e** trajetória; rode no Dev UI com ADC ativo antes de promover.

---

## 4. Framework de Times de Agentes (ADK + LiteLLM)

**4.1 Anatomia do membro:** `name`, `description` (delegação), `instruction`, `model`,
`tools` mínimas.

**4.2 Padrões de orquestração** (escolha o de menor latência que resolve):

| Padrão | Uso no GymSite | Custo/latência |
|---|---|---|
| **Coordinator/Delegation** | Padrão: raiz → Técnico/Regulatório/Mercado | 1 hop, baixo overhead |
| **Sequential** | Coletar → diagnosticar → formatar | Determinístico |
| **Parallel** | RAG + concorrentes simultâneos | **Reduz latência** |
| **Loop** | Refinar mix vs. pico/porte | Limitar iterações |
| **Graph/Dynamic** (ADK 2.0+) | Branching + nós determinísticos | Controle máx. |
| **Agent Routing** (exp.) | Fallback / A/B / auto-routing | Resiliência |

**4.3 Delegação automática:** descrições afiadas dos sub-agentes + instrução do raiz
citando-os por nome e condição; controle com `disallow_transfer_to_*`.

**4.4 Multi-modelo via LiteLLM:** interface única p/ 100+ LLMs (formato OpenAI); envolva
o modelo em `LiteLlm`; **roteie modelo por role** (constantes `MODEL_TECNICO`…);
**Claude Agent SDK + LiteLLM** roda o mesmo código com qualquer provider via Proxy.

**4.5 LiteLLM Proxy/Gateway (produção):** Router (retry/**fallback**/load-balancing),
**virtual keys + budgets** (teto de custo), **cost tracking** por key/team/model,
guardrails centralizados (PII/safety), **caching**, e **MCP Gateway**. *(Se um dia o
`buscar_concorrentes` precisar ser MCP — ex.: consumido por outro runtime ou para
cost-tracking central — é aqui que ele se registra. Hoje é FunctionTool ADK nativo.)*

**4.6 Memória/estado:** `output_key`, `ToolContext`, `include_contents='none'`.

**4.7 Guardrails em camadas:** `before_model` + `before_tool` (ADK) + PII/safety (Proxy).

**4.8 Observabilidade:** `success_callback` (Langfuse/MLflow/Helicone) + custo por
resposta; traces no Dev UI.

---

## 5. Agent Config & Deploy

> No GymSite os agentes são **code-first** (`agents_site/agent.py`), não YAML — dá
> controle de tools, grounding e generate_config. O bloco YAML abaixo fica como
> referência do caminho declarativo (experimental, só Gemini).

**5.1 Agent Config (YAML, declarativo, experimental — só Gemini):**
```yaml
name: assistant_agent
model: gemini-flash-latest
description: A helper agent that can answer users' questions.
instruction: You are an agent to help answer users' various questions.
```

**5.2 Instalação:**
```bash
pip install google-adk
adk --version
```

**5.3 Credenciais (.env / ambiente):**
```env
# Produção (Vertex AI) — recomendado
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=gen-lang-client-0106729343
GOOGLE_CLOUD_LOCATION=global   # RAG (Discovery Engine) é global; rodou em prod assim
```
*(Dev via AI Studio: `USE_VERTEXAI=0` + `GOOGLE_API_KEY` — sujeito ao free-tier 20/dia.)*

**5.4 Rodar local (Dev UI):**
```powershell
$env:GOOGLE_GENAI_USE_VERTEXAI = "true"
$env:GOOGLE_CLOUD_PROJECT = "gen-lang-client-0106729343"
$env:GOOGLE_CLOUD_LOCATION = "global"
adk web        # http://localhost:8000 → escolher "agents_site"
# adk run agents_site   (terminal)   ·   adk api_server   (REST p/ o site)
```

**5.5 Deploy (Cloud Run):**
```bash
export GOOGLE_CLOUD_PROJECT=gen-lang-client-0106729343
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=True

adk deploy cloud_run \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$GOOGLE_CLOUD_LOCATION \
  --service_name=gymsite-agents \
  --app_name=agents_site \
  --with_ui \
  ./agents_site
```
Opções: **Agent Runtime / Vertex AI Agent Engine** (gerenciado, prod) · **Cloud Run**
(serverless) · **GKE** (controle máximo). Em prod, **LiteLLM Proxy** à frente dos modelos.

---

## 6. Matriz dos Agentes GymSite (as-built — `agents_site/`)

| Agente | RAG (data store) | Tools (FunctionTool ADK) | Google/URL | temp | Status |
|---|---|---|---|---|---|
| **Técnico** | `gymsite-equip-docs` | `dimensionar_cardio_por_pico`, `calcular_equipamentos_por_area` | OFF | 0.2 | 🟢 montado/em teste |
| **Arquiteto** | `gymsite-obra-docs` (engine `gymsite-obra-app`) | `calcular_sanitarios_por_lotacao` | OFF | 0.2 | 🟡 montado — store a criar/ingerir |
| **Engenheiro de Obra** | `gymsite-obra-docs` (engine `gymsite-obra-app`) | — | OFF | 0.2 | 🟡 montado — store a criar/ingerir |
| **Regulatório** | `gymsite-market-docs_1782013477930` | — | OFF | 0.2 | 🟢 montado/em teste |
| **Mercado** | `gymsite-market-docs_1782013477930` | `buscar_concorrentes` (Google Maps ao vivo) | ON | 0.3 | 🟢 montado/em teste |
| **Roteador** (`GymSiteSite`) | — | — | — | 0.1 | 🟢 |

- **Store nova `gymsite-obra-docs`** (Arquiteto + Engenheiro): ingerir `engenharia_obra_academia_ref.txt`
  + `engenharia_layout_academia_ref.txt` (em `docs/agente/agentes_site/rag/`). Engine de busca `gymsite-obra-app`.

- **RAG via FunctionTool**, não `VertexAiSearchTool` nativo: reusa `tools/discovery_engine_tools.py`
  (`buscar_catalogos_equipamentos` / `buscar_conhecimento`) — código validado retornando dado real
  (ex.: Leg Press 45° Life Fitness 270×144×147 cm, 720 kg, código `SPLIP`). Garante grounding +
  mesmo auth (ADC) que já roda em prod + controle de formato.
- **Grounding na arquitetura:** cada agente só tem a sua tool; o prompt manda chamar a tool ANTES
  de citar modelo/valor/contagem. Mata a alucinação de código (`SS-LP`/`MG-A45LP` inventados).
- Engines Discovery: `gymsite-equip-app` (equip) · `gymsite-market-app_1782013373452` (mercado).

---

## 7. Checklist Definition-of-Done

- [x] `name` + `description` afiada (roteamento correto comprovado no smoke import)
- [x] `instruction` em Markdown, escopo fechado, anti-alucinação (grounding obrigatório)
- [x] Ferramentas mínimas (1 RAG por agente; Google/URL OFF onde não se aplica)
- [x] `temperature`/`max_output_tokens` definidos (0.1–0.3 / 512–1536)
- [ ] `thinking_budget` calibrado (`include_thoughts=OFF` em prod) — *avaliar p/ Técnico*
- [ ] `output_key`/`include_contents` ajustados ao fluxo — *site é single-turn por agente*
- [ ] Callbacks `before_model` + `before_tool` (+ PII/safety no Proxy) — *pendente*
- [x] Cálculo determinístico onde há número derivado (`dimensionar_cardio_por_pico`)
- [ ] LiteLLM: modelo por role; Proxy com fallback, budgets, cache, cost tracking — *fase 2*
- [ ] (Mercado) avaliar MCP no Gateway com access control — *só se necessário*
- [ ] Passou nas 5 perguntas de avaliação no Dev UI (ADC ativo) — **rodar `adk web`**
- [x] Modelo Flash padrão; Vertex AI habilitado (env)
- [ ] Deploy definido (Agent Engine / Cloud Run / GKE)

---

## 8. Operação & Pendências Manuais
*(etapas que exigem o ambiente Cloud Shell / permissões — fora do alcance do assistente)*

- **ADC:** `gcloud auth application-default login` (autentica RAG + Maps + Gemini-via-Vertex).
- **`adk web`** com as 5 perguntas de cada doc no Dev UI (validar roteamento + grounding +
  cálculo de pico). Conferir que o Técnico parou de inventar código de modelo.
- **Git:** commit dos arquivos (`agents_site/`, docs) na branch `feat/site-agent-async-chat`.
- **IAM (só se migrar p/ `VertexAiSearchTool` nativo ou deploy gerenciado):** conceder à
  service account `roles/discoveryengine.viewer` + `roles/secretmanager.secretAccessor`.
  *(Com FunctionTool + ADC, a SA do Cloud Run que já roda RAG em prod resolve.)*
- **Decisão Regulatório:** sub-agente novo (feito, `Regulatorio`) vs. reaproveitar "Sr. Regra".

---

## 9. Referências
- ADK — Simple agents, Multi-agents/Workflows, Tools, Code Execution, Callbacks,
  Planner/Gemini Thinking, Agent Config, Installation, Runtime, ADK CLI, Cloud Run,
  Deploy to Agent Runtime.
- ADK samples (`adk-python`) — `tool_builtin_config`, `multi_agent_llm_config`.
- LiteLLM — Getting Started, Learn, Integrations, Providers, Cost Tracking,
  Claude Agent SDK with LiteLLM.
- Google Cloud — AI Studio API Keys; Resource Manager (criar/gerenciar projetos).
- Gemini Enterprise Agent Platform — Visão geral (set up tools).

---
*Documento vivo. Atualize a Matriz (§6) e o status conforme cada agente avança.*
*Arquivos: [agents_site/agent.py](../../../agents_site/agent.py) · [agents_site/tools.py](../../../agents_site/tools.py) · docs [01](01_responsavel_tecnico.md) · [02](02_regulatorio.md) · [03](03_mercado.md).*
