# Roadmap Granular — 4 Eixos de Execução

> Este documento decompõe os 4 caminhos possíveis em tarefas pequenas, acionáveis e com critérios de aceite claros. Use como backlog de sprint ou para estimar esforço antes de começar.

---

## EIXO 1: Ajustar Pontos da Arquitetura

**Objetivo:** Refinar o modelo de dados, regras de negócio e fluxos antes de escrever código de produção. Evita retrabalho.

### 1.1 Definir categorias de tarefa definitivas
**Descrição:** Validar se as 8 categorias propostas cobrem todos os cenários de abertura de academia/box/studio.

**Tarefas:**
- [ ] **T1.1.1** — Mapear processo de abertura real de 3 academias (tradicional, box, studio) com donos reais ou desk research.
- [ ] **T1.1.2** — Listar todas as etapas obrigatórias de cada processo (alvará, bombeiros, ANVISA, CREF, etc.).
- [ ] **T1.1.3** — Agrupar etapas nas categorias propostas e identificar gaps.
- [ ] **T1.1.4** — Decidir se precisa de novas categorias (ex: `TECNOLOGIA` separado de `OPERACIONAL`? `COMUNICACAO` separado de `MARKETING`?).
- [ ] **T1.1.5** — Documentar definição de cada categoria com exemplos de tarefas.

**Critério de aceite:** Matriz de etapas × categorias preenchida para os 3 tipos de negócio. Nenhuma etapa sem categoria.

**Depende de:** Nenhuma.
**Estimativa:** 2 dias.

---

### 1.2 Definir regra de geração de playbook (templates vs. IA pura)
**Descrição:** Decidir o balanço entre template estruturado (rápido, previsível) e geração 100% por LLM (flexível, imprevisível).

**Tarefas:**
- [ ] **T1.2.1** — Criar template base de playbook para academia tradicional (lista de tarefas padrão).
- [ ] **T1.2.2** — Criar template base para crossfit box.
- [ ] **T1.2.3** — Criar template base para studio pilates.
- [ ] **T1.2.4** — Criar template base para studio funcional.
- [ ] **T1.2.5** — Testar: dar o mesmo relatório para o LLM 5 vezes. Medir variabilidade nas tarefas geradas.
- [ ] **T1.2.6** — Decidir abordagem: 
  - **Opção A:** Template fixo + IA personaliza título, descrição, prazo e custo.
  - **Opção B:** IA gera tudo, mas valida contra schema rigidamente.
  - **Opção C (recomendada):** Template base + IA adiciona/remover tarefas conforme insights do relatório.
- [ ] **T1.2.7** — Documentar decisão e ajustar `playbook_generator.py` conforme.

**Critério de aceite:** Decisão documentada em `docs/arquitetura/DECISAO_PLAYBOOK_GENERATOR.md`. Teste de variabilidade do LLM salvo.

**Depende de:** T1.1.5.
**Estimativa:** 3 dias.

---

### 1.3 Modelar dependências entre tarefas
**Descrição:** Definir quais dependências são universais (sempre existem) e quais são contextuais.

**Tarefas:**
- [ ] **T1.3.1** — Listar dependências "óbvias" (ex: "Assinar contrato" → "Iniciar obra"; "Obra civil" → "Instalar equipamentos").
- [ ] **T1.3.2** — Definir se dependências são configuráveis pelo usuário ou fixas no template.
- [ ] **T1.3.3** — Decidir como tratar dependências circulares (validação no backend + regra de negócio).
- [ ] **T1.3.4** — Modelar no banco: `tarefa_dependencias` com tipos (`TERMINA_PARA_COMECAR`, `COMECA_JUNTO`, `TERMINA_JUNTO`).
- [ ] **T1.3.5** — Criar diagrama de dependências para playbook padrão de academia.

**Critério de aceite:** Diagrama Mermaid ou Draw.io com dependências do playbook padrão. Schema do banco validado.

**Depende de:** T1.2.7.
**Estimativa:** 2 dias.

---

### 1.4 Definir política de custos e orçamento
**Descrição:** Como o custo planejado de cada tarefa é calculado e como o sistema lida com desvios.

**Tarefas:**
- [ ] **T1.4.1** — Decidir fonte do custo planejado: vem do relatório (A4) ou de benchmark histórico?
- [ ] **T1.4.2** — Definir threshold de alerta de desvio (ex: > 10% amarelo, > 25% vermelho).
- [ ] **T1.4.3** — Decidir se tarefas de mesmo tipo (ex: 3 tarefas de "Comprar equipamento") compartilham um "orçamento de categoria" ou são independentes.
- [ ] **T1.4.4** — Definir moeda e precisão (centavos? arredondamento?).
- [ ] **T1.4.5** — Documentar regras de cálculo de progresso financeiro (custo real / custo planejado por categoria e total).

**Critério de aceite:** Tabela de regras de custo documentada. Exemplos de cálculo com dados fictícios.

**Depende de:** Nenhuma.
**Estimativa:** 1 dia.

---

### 1.5 Revisar schema de `user_projects` para unificação
**Descrição:** Garantir que `user_projects` tenha todos os campos necessários para alimentar tanto o Consultor quanto o Playbook.

**Tarefas:**
- [ ] **T1.5.1** — Revisar JSONB fields de `user_projects`: faltam campos que o Playbook precisa ler?
- [ ] **T1.5.2** — Decidir se o Playbook lê direto do `relatorio_outputs` ou se o Consultor "copia" dados relevantes para `user_projects`.
- [ ] **T1.5.3** — Validar se `project_messages` consegue armazenar interações do tipo "sugestão aceita/rejeitada" (novo tipo de mensagem).
- [ ] **T1.5.4** — Ajustar schema conforme decisões.

**Critério de aceite:** Schema final revisado e aprovado. Nenhuma query precisa fazer JOIN em mais de 3 tabelas para montar a tela do Playbook.

**Depende de:** T1.3.5, T1.4.5.
**Estimativa:** 1 dia.

---

**Total Eixo 1:** ~9 dias de trabalho (1 pessoa).

---

## EIXO 2: Começar a Implementar (Migrations + Playbook Generator)

**Objetivo:** Código rodando. Schema no banco. Playbook gerando tarefas a partir de um relatório de teste.

### 2.1 Backend — Schema e migrations

**Tarefas:**
- [ ] **T2.1.1** — Criar migration `20250610_add_execucao_schema.sql` com:
  - `playbooks`
  - `tarefas`
  - `tarefa_dependencias`
  - `tarefa_checklist`
  - `okrs`
  - `timeline_eventos`
  - `tarefa_comentarios`
- [ ] **T2.1.2** — Adicionar RLS policies para todas as tabelas.
- [ ] **T2.1.3** — Criar indexes (`playbook_id`, `status`, `categoria`, `projeto_id`).
- [ ] **T2.1.4** — Rodar migration em ambiente de dev (Supabase local ou projeto de staging).
- [ ] **T2.1.5** — Criar seed data: 1 playbook de teste com 10 tarefas.

**Critério de aceite:** `supabase db reset` cria todas as tabelas + seed. SELECTs básicos funcionam.

**Depende de:** T1.5.4.
**Estimativa:** 2 dias.

---

### 2.2 Backend — Templates de playbook

**Tarefas:**
- [ ] **T2.2.1** — Criar `backend/services/execucao/playbook_templates.py`.
- [ ] **T2.2.2** — Implementar `TEMPLATE_ACADEMIA_TRADICIONAL` com lista de tarefas base (título, categoria, ordem, custo_planejado_default).
- [ ] **T2.2.3** — Implementar `TEMPLATE_CROSSFIT_BOX`.
- [ ] **T2.2.4** — Implementar `TEMPLATE_STUDIO_PILATES`.
- [ ] **T2.2.5** — Implementar `TEMPLATE_STUDIO_FUNCIONAL`.
- [ ] **T2.2.6** — Criar teste unitário: instanciar cada template → verificar se tem pelo menos 15 tarefas.
- [ ] **T2.2.7** — Criar função `get_template_por_tipo_negocio(tipo: str) -> list[TarefaTemplate]`.

**Critério de aceite:** Testes passam. Cada template retorna lista tipada de tarefas.

**Depende de:** T2.1.5.
**Estimativa:** 2 dias.

---

### 2.3 Backend — Playbook Generator (IA + Template)

**Tarefas:**
- [ ] **T2.3.1** — Criar `backend/services/execucao/playbook_generator.py`.
- [ ] **T2.3.2** — Implementar `carregar_relatorio_para_prompt(relatorio_id) -> str`: busca `relatorio_outputs` e formata em markdown para o LLM.
- [ ] **T2.3.3** — Implementar `carregar_template_base(tipo_negocio) -> list`: pega template de T2.2.7.
- [ ] **T2.3.4** — Criar prompt do LLM: 
  - System: "Você é um gestor de projetos de abertura de academias. Receba um relatório de viabilidade e uma lista de tarefas base. Personalize, adicione, remova ou ajuste tarefas conforme os insights do relatório."
  - User: relatório + template.
  - Output: JSON estruturado com lista de tarefas (título, descrição, categoria, ordem, custo_planejado, data_prevista_conclusao, depende_de).
- [ ] **T2.3.5** — Implementar parser do JSON de resposta do LLM para objetos Python.
- [ ] **T2.3.6** — Implementar validação: todas as tarefas têm título, categoria válida, ordem >= 0.
- [ ] **T2.3.7** — Implementar fallback: se LLM falhar (timeout, JSON inválido), usar template base sem personalização + log de alerta.
- [ ] **T2.3.8** — Criar teste de integração: mock de relatório → gerar playbook → verificar se tarefas foram criadas no banco.

**Critério de aceite:** Teste de integração passa. Geração de playbook completa em < 30s. Fallback funciona.

**Depende de:** T2.2.7.
**Estimativa:** 4 dias.

---

### 2.4 Backend — CRUD de Playbook e Tarefas

**Tarefas:**
- [ ] **T2.4.1** — Criar `backend/services/execucao/playbook_service.py`.
- [ ] **T2.4.2** — `criar_playbook(projeto_id, relatorio_id, nome) -> playbook_id`.
- [ ] **T2.4.3** — `listar_playbooks(user_id, filtros) -> list`.
- [ ] **T2.4.4** — `obter_playbook_completo(playbook_id) -> dict` (com tarefas, OKRs, timeline).
- [ ] **T2.4.5** — Criar `backend/services/execucao/tarefa_service.py`.
- [ ] **T2.4.6** — `criar_tarefa(...)`, `atualizar_tarefa(...)`, `concluir_tarefa(tarefa_id, custo_real)`, `excluir_tarefa` (soft delete).
- [ ] **T2.4.7** — `validar_dependencias(tarefa_id, novo_status) -> bool` (não pode concluir se predecessoras pendentes).
- [ ] **T2.4.8** — `recalcular_progresso(playbook_id)` (atualiza percentual_concluido, custo_real_total).
- [ ] **T2.4.9** — Criar endpoints FastAPI:
  - `POST /api/execucao/playbooks`
  - `GET /api/execucao/playbooks`
  - `GET /api/execucao/playbooks/{id}`
  - `POST /api/execucao/playbooks/{id}/gerar`
  - `PATCH /api/execucao/tarefas/{id}`
  - `POST /api/execucao/tarefas/{id}/concluir`

**Critério de aceite:** Todos os endpoints respondem 200 com dados corretos. Testes de API (pytest ou manual com curl/Postman).

**Depende de:** T2.3.8, T2.1.5.
**Estimativa:** 4 dias.

---

### 2.5 Frontend — Kanban Base

**Tarefas:**
- [ ] **T2.5.1** — Criar `frontend/src/hooks/usePlaybook.ts` (React Query: fetch playbook + tarefas).
- [ ] **T2.5.2** — Criar `frontend/src/hooks/useTarefas.ts` (mutations: atualizar status, concluir).
- [ ] **T2.5.3** — Criar `frontend/src/routes/ProjetoExecucaoPage.tsx`.
- [ ] **T2.5.4** — Criar `frontend/src/components/execucao/PlaybookKanban.tsx`.
- [ ] **T2.5.5** — Implementar colunas: A_FAZER, EM_ANDAMENTO, CONCLUIDA, BLOQUEADA.
- [ ] **T2.5.6** — Implementar `TarefaCard.tsx` com título, categoria (badge colorido), prazo, responsável, custo planejado.
- [ ] **T2.5.7** — Implementar drag-and-drop básico entre colunas (atualiza status via mutation).
- [ ] **T2.5.8** — Criar `TarefaDrawer.tsx` — ao clicar no card, abre drawer com descrição, checklist (mock), custo, comentários (mock).
- [ ] **T2.5.9** — Criar botão "Gerar Playbook" na tela do Relatório (redireciona para execução).

**Critério de aceite:** Usuário consegue ver playbook, mover tarefas entre colunas, abrir drawer. Dados persistem no backend.

**Depende de:** T2.4.9.
**Estimativa:** 4 dias.

---

### 2.6 Integração end-to-end (teste completo)

**Tarefas:**
- [ ] **T2.6.1** — Criar relatório de teste mockado no banco.
- [ ] **T2.6.2** — Clicar "Gerar Playbook" no frontend → verificar se tarefas aparecem no Kanban.
- [ ] **T2.6.3** — Mover tarefa para CONCLUIDA → verificar se progresso % atualiza.
- [ ] **T2.6.4** — Testar fluxo em mobile (375px).
- [ ] **T2.6.5** — Documentar bugs e criar issues.

**Critério de aceite:** Vídeo ou screenshot do fluxo completo funcionando. Nenhum bug crítico.

**Depende de:** T2.5.9.
**Estimativa:** 1 dia.

---

**Total Eixo 2:** ~17 dias de trabalho (1 pessoa full-stack ou 1 backend + 1 frontend).

---

## EIXO 3: Unificar Consultor + Playbook em Arquitetura Única

**Objetivo:** Garantir que `UserProject` seja a fonte única de verdade. Eliminar duplicidade de dados. Documentar o fluxo end-to-end.

### 3.1 Revisar e consolidar o modelo de `UserProject`

**Tarefas:**
- [ ] **T3.1.1** — Listar todos os dados que o Consultor precisa (localização, modelo_negocio, dados de pesquisa).
- [ ] **T3.1.2** — Listar todos os dados que o Playbook precisa (relatorio_id, tarefas, OKRs, custos).
- [ ] **T3.1.3** — Identificar sobreposições e gaps entre as duas listas.
- [ ] **T3.1.4** — Redesenhar `user_projects` JSONB fields para serem consumidos por ambos os módulos.
- [ ] **T3.1.5** — Criar diagrama ER unificado: `user_projects` no centro, com relacionamentos para `relatorios`, `playbooks`, `project_messages`, `chat_sessions` (legado).

**Critério de aceite:** Diagrama ER unificado salvo em `docs/arquitetura/DIAGRAMA_ER_UNIFICADO.md`. Schema revisado.

**Depende de:** T1.5.4.
**Estimativa:** 2 dias.

---

### 3.2 Criar documento de fluxo unificado

**Tarefas:**
- [ ] **T3.2.1** — Desenhar fluxo: "Usuário inicia conversa no Consultor" → pesquisas → relatório → "Gerar Playbook" → execução → consultor acompanha.
- [ ] **T3.2.2** — Definir pontos de transição entre módulos (quando o Consultor chama o Playbook e vice-versa).
- [ ] **T3.2.3** — Definir contrato de dados: o que o Consultor grava no `UserProject` que o Playbook lê.
- [ ] **T3.2.4** — Definir eventos que disparam notificação cruzada (ex: tarefa atrasada → Consultor pergunta se precisa de ajuda).
- [ ] **T3.2.5** — Documentar em `docs/arquitetura/FLUXO_CONSULTOR_PLAYBOOK_UNIFICADO.md`.

**Critério de aceite:** Documento com diagrama de sequência Mermaid mostrando 3 cenários: (a) pesquisa → relatório → playbook, (b) playbook → consultor pergunta, (c) novo concorrente detectado → sugestão no playbook.

**Depende de:** T3.1.5.
**Estimativa:** 2 dias.

---

### 3.3 Refatorar `consultor_engine.py` para gravar no `UserProject`

**Tarefas:**
- [ ] **T3.3.1** — Garantir que toda pesquisa do Consultor (A0, A3a, etc.) persista em `user_projects` (não apenas em memória ou mensagens).
- [ ] **T3.3.2** — Criar função `sincronizar_projeto_com_relatório(projeto_id, relatorio_id)` que copia dados estruturados do relatório para o projeto.
- [ ] **T3.3.3** — Refatorar `POST /api/consultor/conversar` para retornar não só mensagem, mas também `dados_atualizados` (o que mudou no projeto).
- [ ] **T3.3.4** — Testar: fazer 3 perguntas no chat → verificar se `user_projects` tem os dados acumulados.

**Critério de aceite:** `SELECT * FROM user_projects WHERE id = X` retorna todos os dados pesquisados na conversa.

**Depende de:** T3.2.5.
**Estimativa:** 3 dias.

---

### 3.4 Integrar Playbook ao `UserProject`

**Tarefas:**
- [ ] **T3.4.1** — Garantir que `playbooks.projeto_id` seja NOT NULL (cada playbook vive dentro de um projeto).
- [ ] **T3.4.2** — Criar função `obter_projeto_completo(projeto_id)` que retorna: projeto + último relatório + playbook ativo + tarefas pendentes.
- [ ] **T3.4.3** — Adaptar `ProjetoExecucaoPage.tsx` para ler do endpoint unificado.
- [ ] **T3.4.4** — Criar navegação unificada: sidebar mostra "Projeto: Cabo Branco" com abas: Conversa | Pesquisas | Playbook | Dashboard | Relatório.

**Critério de aceite:** Usuário navega entre abas sem perder contexto. Dados são consistentes entre abas.

**Depende de:** T3.3.4.
**Estimativa:** 3 dias.

---

### 3.5 Depreciar `chat_sessions` legado

**Tarefas:**
- [ ] **T3.5.1** — Criar migration que migra dados de `chat_sessions` para `user_projects` + `project_messages`.
- [ ] **T3.5.2** — Atualizar `services/chat_state.py` para ler/escrever em `user_projects`.
- [ ] **T3.5.3** — Marcar `chat_sessions` como deprecated nos comentários.
- [ ] **T3.5.4** — Testar se conversas antigas ainda aparecem corretamente.

**Critério de aceite:** Nenhuma query nova usa `chat_sessions`. Dados migrados sem perda.

**Depende de:** T3.4.4.
**Estimativa:** 2 dias.

---

**Total Eixo 3:** ~12 dias de trabalho.

---

## EIXO 4: Focar em Decisões Pendentes (Modelo de Negócio / Freemium)

**Objetivo:** Definir limites, preços e regras de acesso antes de codar restrições. Evita refactoring de permissões depois.

### 4.1 Definir modelo de negócio do módulo

**Tarefas:**
- [ ] **T4.1.1** — Analisar custo de infra por projeto: tokens de LLM (geração de playbook, sugestões IA), storage de anexos, chamadas de API externas (Places, CNPJ).
- [ ] **T4.1.2** — Definir 3 opções de modelo:
  - **Opção A (Grátis):** Tudo gratuito, limitado a X projetos por mês. Monetização via parcerias (fornecedores de equipamento, financiamento).
  - **Opção B (Freemium):** Consultor gratuito. Playbook pago (ou limitado a 5 tarefas no gratuito). Relatório formal pago.
  - **Opção C (SaaS):** Assinatura mensal por usuário. Tiers: Starter (1 projeto ativo), Pro (ilimitado), Enterprise (múltiplos usuários, dashboards avançados).
- [ ] **T4.1.3** — Pesquisar preços de concorrentes (SEbrae, Franq.io, outras ferramentas de viabilidade).
- [ ] **T4.1.4** — Calcular unit economics: CAC, LTV, margem por tier.
- [ ] **T4.1.5** — Decidir modelo e documentar.

**Critério de aceite:** Documento `docs/produto/MODELO_NEGOCIO.md` com decisão, preços, limites por tier e justificativa.

**Depende de:** Nenhuma.
**Estimativa:** 2 dias.

---

### 4.2 Definir limites técnicos por tier

**Tarefas:**
- [ ] **T4.2.1** — Definir limites se freemium/SaaS:
  - Máximo de projetos ativos
  - Máximo de tarefas por playbook
  - Máximo de sugestões IA por mês
  - Máximo de anexos por projeto
  - Acesso a dashboards avançados (sim/não)
  - Compartilhamento com equipe (sim/não)
- [ ] **T4.2.2** — Mapear cada limite para campo no banco (ex: `orgs.plano`, `user_projects_contagem`).
- [ ] **T4.2.3** — Criar middleware de rate-limit/plano nos endpoints.
- [ ] **T4.2.4** — Criar tela de "Upgrade" no frontend quando usuário atinge limite.

**Critério de aceite:** Tabela de limites por tier. Middleware funcional com testes.

**Depende de:** T4.1.5.
**Estimativa:** 2 dias.

---

### 4.3 Definir notificações e canais

**Tarefas:**
- [ ] **T4.3.1** — Decidir canais de notificação:
  - In-app (badge, toast)
  - Email (SendGrid / Resend / Cloudflare Email)
  - WhatsApp (evolution-api / WPPConnect)
  - Push notification (web push)
- [ ] **T4.3.2** — Definir quais eventos geram notificação:
  - Tarefa atrasada
  - Sugestão da IA
  - Marco se aproximando
  - Novo concorrente detectado
  - Relatório pronto
- [ ] **T4.3.3** — Definir preferências do usuário (quais canais, quais eventos, horário de silêncio).
- [ ] **T4.3.4** — Documentar e criar tabela `notificacao_preferencias`.

**Critério de aceite:** Tabela criada. Documento `docs/produto/NOTIFICACOES.md` com matriz evento × canal.

**Depende de:** Nenhuma.
**Estimativa:** 1 dia.

---

### 4.4 Definir compartilhamento e permissões

**Tarefas:**
- [ ] **T4.4.1** — Decidir se projeto/playbook pode ser compartilhado:
  - Com sócios (editar)
  - Com prestadores (ver apenas tarefas atribuídas)
  - Com consultores externos (ver tudo, não editar)
  - Público (link de acompanhamento, read-only)
- [ ] **T4.4.2** — Definir schema de permissões (RBAC simples: owner, editor, viewer).
- [ ] **T4.4.3** — Decidir se usamos convite por email ou link mágico.
- [ ] **T4.4.4** — Documentar e ajustar RLS policies.

**Critério de aceite:** Documento `docs/produto/PERMISSOES.md` com diagrama de papéis.

**Depende de:** T4.1.5.
**Estimativa:** 1 dia.

---

### 4.5 Definir integrações externas (futuro)

**Tarefas:**
- [ ] **T4.5.1** — Calendário: Google Calendar / Outlook para prazos e marcos?
- [ ] **T4.5.2** — Financeiro: integração com contabilidade (ContaAzul, Omie)?
- [ ] **T4.5.3** — Comunicação: Slack / Discord para notificações de equipe?
- [ ] **T4.5.4** — CRM: integração com módulo de prospecção existente?
- [ ] **T4.5.5** — Priorizar e documentar roadmap de integrações (Fase 2, 3, 4).

**Critério de aceite:** Documento `docs/produto/INTEGRACOES_FUTURAS.md` com priorização MoSCoW.

**Depende de:** Nenhuma.
**Estimativa:** 1 dia.

---

**Total Eixo 4:** ~7 dias de trabalho (envolve pesquisa de mercado, não só código).

---

## Matriz de Dependências Cruzadas

```
EIXO 1 (Ajustar Arquitetura)
  ├── T1.1.5 (categorias) ──► T1.2.7 (templates)
  ├── T1.2.7 ──► T1.3.5 (dependências)
  ├── T1.3.5 + T1.4.5 ──► T1.5.4 (schema revisado)
  │
  └── T1.5.4 ──► EIXO 2 (T2.1.1 migration)
               └─► EIXO 3 (T3.1.3 gaps)

EIXO 2 (Implementar)
  ├── T2.1.5 (schema) ──► T2.2.1 (templates)
  ├── T2.2.7 ──► T2.3.8 (generator)
  ├── T2.3.8 + T2.1.5 ──► T2.4.9 (endpoints)
  ├── T2.4.9 ──► T2.5.9 (frontend)
  └── T2.5.9 ──► T2.6.5 (E2E)

EIXO 3 (Unificar)
  ├── T3.1.5 ──► T3.2.5 (fluxo)
  ├── T3.2.5 ──► T3.3.4 (consultor grava projeto)
  ├── T3.3.4 ──► T3.4.4 (playbook lê projeto)
  └── T3.4.4 ──► T3.5.4 (deprecar chat_sessions)

EIXO 4 (Decisões)
  ├── T4.1.5 ──► T4.2.3 (limites)
  ├── T4.1.5 ──► T4.4.4 (permissões)
  └── T4.x.x são independentes entre si (exceto T4.1.5)
```

---

## Recomendação de Ordem de Execução

Se você tem **1 pessoa full-stack** e quer entregar valor rápido:

1. **Sprint 0 (3-4 dias):** EIXO 4 primeiro — define limites e regras de negócio. Sem isso, você pode codar restrições erradas.
2. **Sprint 1 (5-7 dias):** EIXO 1 — ajusta schema e templates. Evita refactoring.
3. **Sprint 2-3 (14 dias):** EIXO 2 — implementa migrations, generator, endpoints e Kanban base.
4. **Sprint 4 (7-10 dias):** EIXO 3 — unifica consultor + playbook, cria navegação por abas.

**Total estimado:** ~30-35 dias úteis (1 pessoa full-stack).

Se você tem **2 pessoas** (1 backend + 1 frontend):
- Backend faz EIXO 1 + EIXO 2 backend em paralelo com frontend fazendo EIXO 2 frontend.
- EIXO 3 é feito em conjunto no final.
- **Total estimado:** ~20-25 dias úteis.

---

## Checklist Go/No-Go (antes de começar a codar)

- [ ] Decisão de modelo de negócio tomada (EIXO 4)
- [ ] Schema de banco revisado e aprovado (EIXO 1)
- [ ] Templates de playbook definidos para pelo menos 2 tipos de negócio (EIXO 1)
- [ ] Decisão sobre notificações (EIXO 4)
- [ ] Decisão sobre compartilhamento (EIXO 4)
- [ ] Ambiente de dev/staging disponível para testes
- [ ] Seed de relatório mockado disponível para testar geração
