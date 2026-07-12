---
name: google-adk-agents
description: Gestão, debug e manutenção da esteira de agentes do Google ADK (A0 até A9). Use ao alterar pipelines sequenciais, paralelos ou lógicas de retry de LLMs.
---

# 🤖 Orquestração Google ADK

Você está manipulando a espinha dorsal de inteligência do GymSite em `gymsite_intelligence/agent.py`.

## 🧠 Mapa de Fluxo do Pipeline
* **Sequencial:** A0 (Contexto via Deep Research) ➔ A1 (GeoScout) ➔ Análise Paralela.
* **Paralelo:** Executa simultaneamente A2 (Demografia), o subprocesso competitivo (A3a ➔ A3b), e A4 (Financeiro via MRLR determinístico).
* **Consolidação:** A6 junta os dados ➔ A8 valida invariantes cruzadas (A4 × A9) ➔ A9 define o Posicionamento Estratégico.

## 🛠️ Regras de Escrita de Código do ADK
* Novas ferramentas/agentes devem ser criados através da fábrica canônica em `tools/agent_factory.py`.
* **Obrigatório:** Garantir telemetria de tokens e o mecanismo de retry nativo do modelo em erros 429/503.
* **Cache Semântico:** Implementar `langcache` nas chamadas pesadas (como o estrategista A9 com `gemini-2.5-pro`) para economizar custos.