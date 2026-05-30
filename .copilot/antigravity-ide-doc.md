# Guia de Sequência Antigravity IDE para GymSite

Este documento adapta a sequência das principais seções da documentação do Antigravity IDE para contextos de agentes, automação e orquestração aplicados ao projeto GymSite Intelligence. Use como referência de boas práticas, arquitetura de automação e integração futura de agentes com o ecossistema IDE.

---

## 1. IDE Rules (`ide-rules`)
Regras fundamentais que regem o comportamento dos skills (agentes) do GymSite. Incluem restrições de segurança (ex: nunca persistir credenciais fora do Supabase), lógicas de fallback e encadeamento, e validação dos dados trafegados entre os steps A0–A6.

- Sempre valide entradas/saídas conforme schema.
- Utilize orquestração ADK/SequentialAgent para garantir execução sequencial e paralelização segura dos agentes.
- Log detalhado obrigatório para cada etapa do pipeline.

## 2. IDE Workflows (`ide-workflows`)
Representa o fluxo dos agentes (pipeline) e sua execução. Cada agente é um macro-tool no contexto GymSite;
eu:
- O fluxo padrão deve sempre ser: ContextBuilder (A0) → GeoScout (A1) → DemoAnalyst (A2) → (paralelo: CompetitorSearch, CompetitorAnalysis, Mapper) → FinancialEstimator (A4) → ContactHunter (A5) → ReportConsolidator (A6).
- A etapa MarketResearch (A7) apenas sob demanda ou fallback.
- O estado e progresso devem ser persistidos em `state_diagnostics.jsonl`.

## 3. IDE Plugins (`ide-plugins`)
Plugins/skills para automação ou extensões do pipeline GymSite:
- Integrações externas: Google Maps API, OLX, ImovelWeb, IBGE, Search Grounding.
- Ferramentas do diretório `tools/` devem ser tratadas e documentadas como plugins reutilizáveis e versionáveis para qualquer agente.
- Sempre respeite versionamento semântico nos plugins.

## 4. IDE Hooks (`ide-hooks`)
Hooks de automação para execução de tarefas pré/pós-execução dos skills:
- Exemplo: hook de pré-processamento para normalizar entradas do usuário.
- Hook pós-execução para validação/normalização das saídas antes de enviar para o frontend ou persistir no banco.
- Hooks de erro para registrar falhas e evidências no Supabase e/ou dashboards de telemetria.

## 5. IDE Settings (`ide-settings`)
Configurações globais para orquestração e execução do pipeline GymSite:
- .env centraliza variáveis sensíveis, endpoints e chaves de API.
- Settings de fronteira: múltiplos tenants via Supabase, limites de paralelismo dos agentes em produção, regras para timeout/retry do pipeline.
- Recomenda-se isolar settings sensíveis do código-fonte, usando apenas variáveis de ambiente.

---

## 6. Próximos Passos e Customizações
- Consulte sempre a documentação original do Antigravity para novos recursos, integração de modelos ou melhorias no workflow IDE.
- Para extensões personalizadas (ex: novos agentes, integração com novos provedores de dados), siga a convenção de hooks e plugins já estruturados neste repositório.
- Documente todo skill customizado nesta estrutura para garantir rastreabilidade e onboardings rápidos.

---

Este guia serve de referência viva. Atualize conforme evoluírem os pipelines do GymSite.
