# Módulo Execução e Gestão de Projeto (Playbook de Abertura) — V1

> **Versão:** 1.0
> **Status:** Refatorado a partir do draft inicial, incorporando referências externas (Apollo Sequences como motor de cadência; Lark "Task Management [AI]" como referência de campos inteligentes e automação reativa).
> **Documento anterior:** draft sem versão (módulo de execução).

---

## Changelog V1 (o que mudou em relação ao draft)

| # | Mudança | Origem da inspiração | Seção afetada |
|---|---------|----------------------|---------------|
| C-01 | Novo campo `resumo_ia` por tarefa e por playbook — resumo vivo em linguagem natural gerado por LLM de forma reativa. | Lark `Task summary` (campo IA) | Modelo de Dados, P4, Endpoints |
| C-02 | Campos derivados `dias_atraso` e `esta_atrasada` calculados em runtime (nunca armazenados). | Lark `Overdue` (campo fórmula) | Modelo de Dados, P2, Regras |
| C-03 | Vínculo tarefa↔OKR migrado de FK única (1:N) para tabela de junção **N:N** com navegação bidirecional. | Lark Two-way Link (Task ↔ OKR) | Modelo de Dados, OkrLinker |
| C-04 | Cadência formalizada: cada tarefa tem regra de início "imediatamente após dependência" **ou** "após N dias", espelhando o motor de sequência. | Apollo "Quando começar esta etapa" | P1, Modelo de Dados |
| C-05 | Separação explícita entre **IA reativa de enriquecimento** (roda sozinha, só texto) e **IA generativa de tarefas** (sempre exige aceite). | Lark automação "record changes → update with AI" + DP-002 | P4 (novo), Regras, DP-002 |
| C-06 | Biblioteca de **prompt templates** nomeados e versionados, em vez de prompts hardcoded. | Lark Prompt Templates (Summary/Enrichment) | Estrutura de Pastas, Regras |
| C-07 | Categoria da tarefa passa a permitir **múltiplos rótulos** (multi-select) além da categoria principal. | Lark `Departments` (multi-select) | Modelo de Dados |

> **Princípio que NÃO mudou:** a UX nunca expõe prompts, API keys ou jargão de IA ao usuário (respeitando o Glossário e a persona A-001). A inteligência do Lark inspira o *backend*, não a interface.

---

## Contexto do Projeto

**Nome:** GymSite Execução — Playbook Inteligente de Abertura de Unidade

**Objetivo:** Uma vez que o empreendedor define o local (cidade, bairro, possivelmente o imóvel) e tem o Relatório de Viabilidade em mãos, ele precisa executar. Este módulo transforma o relatório em um projeto estruturado com tarefas, prazos, responsáveis, custos e acompanhamento de progresso. A IA atua como gestor de projetos: cria tarefas automaticamente a partir dos achados do relatório, mantém resumos vivos de cada tarefa e do projeto, calcula riscos em tempo real e sugere próximos passos baseados em projetos anteriores semelhantes.

**Personas alvo:**
- **A-001 Empreendedor Iniciante:** Nunca abriu academia. Precisa de um "passo a passo" completo. Não sabe o que precisa fazer depois de "escolher o bairro". Acompanha pelo celular.
- **A-002 Franqueado em Expansão:** Sabe o processo, mas quer otimizar prazos e custos. Usa para delegar tarefas à equipe e acompanhar KPIs.
- **A-003 Gestor de Rede:** Acompanha dezenas de projetos de abertura simultâneos. Precisa de dashboard consolidado, resumos por projeto e alertas de atraso.
- **A-004 Consultor/Parceiro:** Acompanha projetos de múltiplos clientes. Precisa de relatórios de progresso e resumos prontos para apresentar.

**Documentos fonte de verdade:**
- `docs/arquitetura/AGENTE_CONSULTOR_CONVERSACIONAL.md` — UserProject como container
- Relatório de Viabilidade (saída A6) — fonte de dados para geração automática de tarefas
- `docs/metodologia/POSITIONING_FRAMEWORK.md` — estratégia de posicionamento vira tarefas de branding/marketing

---

## Stack do Projeto

| Categoria | Tecnologia |
|-----------|------------|
| Frontend | React 19, TypeScript, Tailwind CSS, shadcn/ui |
| Gráficos | Recharts (dashboards), react-big-calendar ou fullcalendar (timeline/Gantt) |
| Kanban | @dnd-kit/core ou @hello-pangea/dnd (drag-and-drop) |
| Estado | Zustand (estado local do projeto), React Query (servidor) |
| Backend | Python 3.12, FastAPI |
| LLM | Gemini 3.6 Flash (geração de tarefas, resumos vivos, sugestões) |
| Banco | Supabase PostgreSQL |
| Notificações | Supabase Realtime (atualizações em tempo real) + push/WhatsApp (futuro) |

---

## Glossário do Domínio

### Termos que o usuário USA (use na UI)
- **Playbook / Plano de Ação:** o conjunto de tarefas gerado para abrir a unidade.
- **Tarefa / Etapa:** cada coisa que precisa ser feita. "Regularizar no Corpo de Bombeiros."
- **Prazo / Data Limite:** quando a tarefa precisa estar pronta.
- **Responsável:** quem vai fazer a tarefa (o próprio empreendedor, um sócio, um prestador).
- **Marco / Checkpoint:** datas importantes do projeto. "Dia da inauguração", "Entrega da obra civil."
- **Custo Planejado vs. Real:** quanto se esperava gastar vs. quanto se gastou de fato.
- **Progresso:** "Você completou 35% do playbook."
- **Risco / Atenção:** tarefas atrasadas, com custo estourado ou com dependências bloqueadas.
- **Resumo da IA:** *(novo)* "Tarefa iniciada em 12/06, atrasada 5 dias, aguardando entrega do projeto de obra." — texto curto e atualizado automaticamente.
- **Sugestão da IA:** "Com base em projetos similares em Recife, sugiro adicionar uma tarefa de..."

### Termos PROIBIDOS na UI
`stub`, `pipeline`, `queue`, `worker`, `entity`, `record`, `transaction`, `async`, `commit`, `deploy`, `schema`, `trigger`, `cron`, **`prompt`**, **`API key`**, **`LLM`**, **`token`**.

> *(V1 adiciona prompt/API key/LLM/token à lista — a mecânica de IA nunca é exposta na interface, ao contrário de ferramentas horizontais.)*

---

## Padrões Arquiteturais

### P0 — Playbook com Contexto do Relatório
O playbook é gerado automaticamente a partir do Relatório de Viabilidade. Ele não é uma lista genérica — é contextualizado:
- Se o relatório identificou falta de estacionamento → tarefa "Negociar convênio de estacionamento com edifício vizinho".
- Se o relatório indicou investimento de R$ 1,2M em cenário premium → tarefa "Levantar financiamento" com custo estimado vinculado.
- Se A3c mapeou que concorrentes não oferecem pilates → tarefa "Contratar instrutora de pilates" vinculada à estratégia de diferenciação.

### P1 — Cadência: Tarefas com Dependências e Início Relativo *(refatorado — C-04)*
Inspirado no motor de sequência (Apollo), cada tarefa tem uma **regra de início** que combina dependência + offset temporal:
- **Início imediato após dependência:** "Iniciar obra civil" começa assim que "Assinar contrato do imóvel" é concluída (equivalente ao `TERMINA_PARA_COMECAR`).
- **Início após N dias:** "Inspeção do Corpo de Bombeiros" começa 15 dias após a conclusão da obra.

A diferença em relação a uma sequência linear de vendas é que o Playbook é um **grafo** de dependências (uma tarefa pode depender de várias e liberar várias). A conclusão de uma tarefa dispara a liberação de dependentes; atrasos propagam em cascata e são refletidos no campo derivado `dias_atraso`.

### P2 — Custos e Atraso Calculados em Runtime (sem denormalização) *(refatorado — C-02)*
Cada tarefa pode ter custos; o empreendedor registra o valor real gasto. O sistema calcula o desvio em tempo real. **Não há "saldo armazenado"** — custo consolidado e atraso são *derivados*:
- `custo_real_total` = soma dos `custo_real` das tarefas com lançamento.
- `dias_atraso` = `GREATEST(0, hoje − data_prevista_conclusao)` para tarefas não concluídas (espelha o campo fórmula `Overdue` do Lark).
- `esta_atrasada` = `dias_atraso > 0`.

### P3 — Dashboards de Acompanhamento
Visões analíticas: progresso geral, custo acumulado vs. orçamento, tarefas atrasadas, riscos, comparação com projetos similares. Atualizados em runtime a cada mudança de status.

### P4 — Camada de IA: Reativa vs. Generativa *(novo — C-01, C-05)*
O módulo separa explicitamente dois tipos de inteligência, com regras de autonomia diferentes:

| Tipo | O que faz | Autonomia | Exemplo |
|------|-----------|-----------|---------|
| **IA Reativa (enriquecimento)** | Resume e descreve o estado atual. Só produz **texto descritivo**, nunca cria/altera estrutura. | **Roda sozinha** ao mudar um registro. | `resumo_ia` de uma tarefa: "Atrasada 5 dias, aguardando projeto de obra." |
| **IA Generativa (estrutura)** | Cria tarefas, sugere novos passos, gera OKRs. | **Sempre exige aceite** do usuário (DP-002). | "Sua análise indicou falta de pilates. Adicionar tarefa de contratação?" |

A IA Reativa é inspirada na automação do Lark *"quando um registro muda → atualizar campo de IA"*: ao alterar status, custo ou comentário de uma tarefa, o `resumo_ia` é regenerado. Como é apenas texto descritivo e não modifica a estrutura do projeto, pode rodar sem aceite. Já qualquer ação que **crie ou altere tarefas/OKRs** passa obrigatoriamente pelo fluxo de sugestão com aceite.

---

## Estrutura de Pastas e Arquivos (Proposta)