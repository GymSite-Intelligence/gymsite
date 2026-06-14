# SPEC — Execução: KPI por Responsável + Interdependência de Etapas

> **Módulo:** Execução / Plano de Abertura
> **Metodologia:** Spec-Driven Development (SDD)
> **Versão:** 1.0 · **Status:** Draft · **Data:** 2026-06-13
> **Relacionado:** `docs/arquitetura/MODULO_EXECUCAO_E_GESTAO_PROJETO.md`, `docs/produto/PERMISSOES.md`

---

## 1. IDENTIFICAÇÃO

| Campo | Valor |
|-------|-------|
| Feature ID | `exec-responsaveis-interdep-001` |
| Nome | Rota de Responsáveis (KPIs) + Regra de Interdependência de Etapas |
| Prioridade | `P1` |
| Escopo | Frontend (nova rota `/responsaveis`) + Backend (agregação KPI + UI de dependências) |

---

## 2. OBJETIVO DE NEGÓCIO

### 2.1 Problema
O Plano de Abertura tem etapas com responsável (`responsavel_pessoa_id`) e dependências (`tarefa_dependencias`), mas:
1. Não há visão consolidada de **carga e desempenho por responsável** — o dono não sabe quem está sobrecarregado, quem está atrasado, quantas etapas cada um tem em cada situação.
2. A regra de interdependência ("etapa B só começa quando A fecha") existe parcialmente no backend, mas **não há UI para defini-la** nem **SPEC** que a formalize.

### 2.2 Solução
- **Rota `/responsaveis`:** relatório de KPIs por pessoa do projeto.
- **Interdependência:** formalizar a regra (já parcialmente implementada via guardrail) + UI para criar/editar dependências entre etapas.

### 2.3 KPIs de sucesso
| KPI | Target |
|-----|--------|
| Dono identifica responsável sobrecarregado em < 5s | qualitativo |
| 0 etapas iniciáveis com predecessora pendente | gate automático |
| % de etapas com responsável atribuído | > 80% |

---

## 3. PERSONAS
- **Owner / Editor:** quer ver carga da equipe, gargalos, atrasos; define quem faz o quê e a ordem.
- **Org Manager:** acompanha responsáveis across projetos.
- **Executor:** NÃO vê o relatório consolidado de responsáveis (PERMISSOES.md — Executor não vê dashboards/custos totais).

---

## 4. REQUISITOS FUNCIONAIS

### RF-001 — KPIs por Responsável
**Descrição:** agregação das etapas por `responsavel_pessoa_id`, com contagem por situação e atraso.

**Métricas por responsável (1ª entrega):**
- Total de etapas atribuídas
- Contagem por status: **A fazer** (`A_FAZER`), **Em andamento** (`EM_ANDAMENTO`), **Bloqueadas** (`BLOQUEADA`), **Concluídas** (`CONCLUIDA`)
- Atraso: nº de etapas com `esta_atrasada = true` + soma/máx de `dias_atraso`
- % de conclusão (concluídas / total contável, excluindo `CANCELADA`)

**Critérios de aceite:**
- [ ] Etapas sem responsável agrupadas em "Sem responsável"
- [ ] Ordenação default por nº de etapas atrasadas (desc), depois por carga total
- [ ] Cada linha/card linka para o kanban filtrado por aquele responsável
- [ ] Agregação feita no **backend** (`/api/execucao/responsaveis?playbook_id=` ou consolidado por projeto), não no cliente
- [ ] Skeleton em loading; empty state quando não há pessoas

**Regras de negócio:**
- **RN-001:** `CANCELADA` não conta em nenhuma métrica.
- **RN-002:** Executor não acessa a rota (gate de UI; idealmente RLS no backend).
- **RN-003:** Custo por responsável fica FORA da 1ª entrega (decisão de escopo).

### RF-002 — Regra de Interdependência (TERMINA_PARA_COMECAR)
**Descrição:** etapa com predecessora não concluída não pode iniciar/concluir; quando a predecessora fecha, a dependente é liberada.

**Estado atual (já implementado):**
- Tabela `tarefa_dependencias(tarefa_id, depende_de_tarefa_id, tipo)`.
- `_predecessoras_pendentes()` + trava na conclusão.
- Guardrail (kanban): predecessora pendente → `BLOQUEADA`; concluir predecessora → libera dependente para o status do próprio checklist.

**Gaps a implementar:**
- **UI para definir/editar dependências** entre etapas (no `EtapaFormDialog` ou painel da etapa): selecionar "Depende de: [etapas do mesmo playbook]".
- Validação anti-ciclo (A→B→A proibido).
- Indicação visual no card/modal: "Bloqueada por: [etapa X]".

**Critérios de aceite:**
- [ ] Usuário define que etapa B depende de A pela UI
- [ ] Ciclo de dependência é rejeitado com mensagem clara
- [ ] Card bloqueado mostra de qual etapa depende
- [ ] Concluir A move B de Bloqueada → status do checklist (já no guardrail)
- [ ] Não é possível concluir B com A pendente (já implementado)

**Regras de negócio:**
- **RN-004:** Só dependência `TERMINA_PARA_COMECAR` na 1ª entrega.
- **RN-005:** Dependência não pode criar ciclo (DAG).
- **RN-006:** Excluir etapa remove as dependências que a referenciam (cascade).

---

## 5. MODELO DE DADOS

### Existente (reaproveitar)
- `tarefas(id, playbook_id, projeto_id, status, responsavel_pessoa_id, responsavel_nome, esta_atrasada, dias_atraso, ...)`
- `tarefa_dependencias(id, tarefa_id, depende_de_tarefa_id, tipo)`
- `pessoas(id, nome, papel, email, telefone)` (via playbook)

### Novo endpoint (agregação)
```
GET /api/execucao/responsaveis?playbook_id={id}
→ {
    responsaveis: [{
      pessoa_id: string | null,        // null = "Sem responsável"
      nome: string,
      papel: string | null,
      total: number,
      a_fazer: number,
      em_andamento: number,
      bloqueadas: number,
      concluidas: number,
      atrasadas: number,
      dias_atraso_max: number,
      pct_conclusao: number
    }]
  }
```
> Implementar em `playbook_service` (agrega das `tarefas` do playbook do usuário; RLS por user_id como nos demais).

### Novos endpoints (dependências) — se a UI exigir CRUD
```
POST   /api/execucao/tarefas/{id}/dependencias   { depende_de_tarefa_id }
DELETE /api/execucao/dependencias/{dep_id}
```
> Validar DAG (anti-ciclo) no service antes de inserir.

---

## 6. UI

### 6.1 Rota `/responsaveis`
- Registrar em `router.tsx` (rota autenticada) + item no sidebar.
- Seletor de playbook/projeto (ou consolidado).
- **Cards/tabela Geo-Intel** (linguagem do redesign): por responsável, mini-card com nome + papel, contagem por status (chips coloridos com tokens `--chart-*` / `hsl(var(--veredito-*))`), badge de atrasadas (vermelho), barra de % conclusão.
- Click → `/execucao/$playbookId?responsavel=<pessoa_id>` (filtro no kanban — exige novo query param `responsavel`).

### 6.2 Definição de dependência
- No `EtapaFormDialog`: campo "Depende de" (multi-select das outras etapas do playbook).
- No card/modal: linha "Bloqueada por: X" quando aplicável.

---

## 7. PERMISSÕES (PERMISSOES.md)
- Rota `/responsaveis`: Owner, Editor, Viewer, Org Admin/Manager. **Executor não.**
- Definir dependência: Owner, Editor, Org Admin/Manager.

---

## 8. CRITÉRIOS DE ACEITE GERAIS
- [ ] `tsc -b` limpo; lógica de agregação no backend (não no cliente)
- [ ] Linguagem visual consistente com o redesign (mini-cards, tokens OKLCH)
- [ ] Sem custo operacional de IA exposto (não se aplica aqui, mas manter padrão)
- [ ] Anti-ciclo testado nas dependências

---

## 9. WAVES DE IMPLEMENTAÇÃO
1. **Backend agregação** `GET /api/execucao/responsaveis` + (se aprovado) CRUD de dependências com anti-ciclo.
2. **Rota `/responsaveis`** + page KPI (cards/tabela Geo-Intel) + sidebar + router.
3. **Filtro `responsavel` no kanban** (query param) — liga o card do relatório ao kanban filtrado.
4. **UI de dependências** no EtapaFormDialog + "Bloqueada por X" no card/modal.

---

## 10. RISCOS
| Risco | Mitigação |
|-------|-----------|
| Ciclo de dependência trava o plano | Validação DAG no service + teste |
| Backend sem --reload em dev | Restart manual ao editar service (já é o fluxo atual) |
| Gate de Executor só no front | Anotar follow-up de RLS no backend (mesma classe do custo) |

---

> **Próximo:** aprovar esta SPEC → PLAN técnico curto → implementar nas waves acima.

---

# APÊNDICE A — Modelo de Responsabilidade (RACI), Aprovação e Perfis de Setor

> Refina RF-001/RF-002. **Supersede a auto-conclusão** do guardrail atual: checklist 100%
> não conclui sozinho — passa por aprovação do responsável.

## A.1 Papéis na etapa (RACI simplificado)

| Papel | Cardinalidade | Quem é | O que faz |
|-------|---------------|--------|-----------|
| **Responsável (Accountable)** | **1 obrigatório** por etapa | gestor da área / dono da entrega — **não necessariamente quem executa** | acompanha, **aprova a conclusão**, responde pela etapa |
| **Executores (Responsible)** | **0..N**, por **passo** | quem faz o trabalho (pode ser prestador/equipe) | executa os passos do checklist; marca passo como feito |

- **Responsável** vive em `tarefas.responsavel_pessoa_id` (já existe) — equivale ao papel `RESPONDE` (Accountable).
- **Executores** vivem **por passo** em `tarefa_checklist.responsavel_pessoa_id` (já existe!) — variam de passo a passo. Conjunto de executores da etapa = união dos executores dos passos. Equivale ao papel `EXECUTA`.
- **Alinhamento com F2 §7:** o RACI completo usa `tarefa_participantes (papel ∈ RESPONDE|EXECUTA|CONSULTADO|INFORMADO)` — tabela **já especificada no F2, ainda NÃO codada**. Esta SPEC adota essa tabela (não inventa `pode_ser_responsavel` na pessoa). `responsavel_pessoa_id`/checklist seguem como atalho/cache do RESPONDE/EXECUTA principal.
- **Segregação:** executor não aprova o próprio trabalho; quem aprova é o **responsável** (RESPONDE) da etapa.

## A.2 Perfil de Setor da pessoa — REUSAR `areas` (NÃO criar CRUD de setor)

> ⚠️ **Conflito resolvido com F2 §2:** o F2 decide *"CRUD de setores — NÃO criar"* (a categoria é infra do gerador; setor livre quebra o mapa de capex). Logo NÃO criamos `perfis_setor` editável. Em vez disso, classificamos a pessoa pelo **vocabulário fixo `areas`** que o F2 §7 já define (seed, sem CRUD de usuário).

```sql
-- F2 §7 já cria `areas` (slug, rotulo, cor) como seed fixo.
-- A pessoa do projeto aponta pra esse vocabulário (sem inventar setor novo):
ALTER TABLE projeto_pessoas ADD COLUMN area_slug TEXT REFERENCES areas(slug);
-- "pode ser responsável / executor" NÃO vira flag na pessoa: o papel é por
-- tarefa, via tarefa_participantes (A.1). Mesma pessoa pode ser RESPONDE numa
-- etapa e EXECUTA em outra.
```

- Setor da pessoa = um slug de `areas` (Imóvel, Documentação, Obra, Equipamentos, Tecnologia, Equipe, Marketing, Financeiro, Operação, Outros).
- Uso: ao atribuir etapa de categoria `OBRAS`, sugerir pessoas com `area_slug = 'OBRAS'`. Filtro por setor no relatório de Responsáveis.
- **Não há flag fixa de "pode aprovar" na pessoa** — quem aprova é definido por papel na etapa (RESPONDE), não por atributo global.

## A.3 Aprovação como gate de conclusão (dá usabilidade real ao "Bloqueado")

Novo sub-estado entre "Em andamento" e "Concluída":

```
A_FAZER → EM_ANDAMENTO → (checklist 100%) → AGUARDANDO_APROVACAO → (responsável aprova) → CONCLUIDA
                                                  │
                                                  └─ responsável REPROVA → volta EM_ANDAMENTO (reabre passos)
```

- **Guardrail revisado:** `done == total` **não** vai mais direto pra `CONCLUIDA` — vai pra **`AGUARDANDO_APROVACAO`**.
- Só o **responsável** (ou Owner/Org Admin) aprova. Aprovar → `CONCLUIDA` + libera dependentes (chain). Reprovar → `EM_ANDAMENTO` + nota do motivo.
- **"Bloqueado" ganha sentido real:** uma etapa fica de fato travada quando (a) **predecessora não foi CONCLUÍDA-e-aprovada** (interdependência), ou (b) — opção de UI — aguardando aprovação é destacado como pendência acionável do responsável. A conclusão deixa de ser um clique solto e vira um portão humano auditável.

**Decisão de modelagem (FECHADA):** novo status `AGUARDANDO_APROVACAO` no enum → **5ª coluna "Em aprovação"** no kanban, entre Em andamento e Concluídas. BLOQUEADA permanece com seu significado de dependência. Ordem das colunas: A fazer · Em andamento · **Em aprovação** · Bloqueadas · Concluídas.

## A.4 Interdependência neste modelo

- Dependência continua **no nível da etapa** (`TERMINA_PARA_COMECAR`).
- **"Concluída" passa a significar "aprovada"** → a dependente B só libera quando A foi **aprovada** pelo responsável de A (não basta o executor marcar os passos). Isso fecha a malha: cada nó da cadeia tem gate humano.
- (Futuro) dependência por **setor**: "Marketing só começa quando Obras entrega" — derivável dos `setor_id`, fora do escopo da 1ª entrega.

## A.5 Exibição no card (kanban/lista/modal)

O card deve mostrar **responsável e executores**:
- **Responsável:** avatar/nome com rótulo "Resp." (destaque — é quem aprova).
- **Executores:** chips/avatars compactos (união dos executores dos passos), com contagem se exceder.
- **Bloqueada por:** quando bloqueada por dependência, "Bloqueada por: [etapa]".
- **Aguardando aprovação:** badge quando no sub-estado A.3.

## A.6 Impacto no que já existe

- **Guardrail (`_status_alvo_por_checklist`):** trocar `done==total → CONCLUIDA` por `done==total → AGUARDANDO_APROVACAO`. `CONCLUIDA` passa a ser alcançada **só via aprovação**.
- **`atualizar_status_tarefa`:** ação de aprovar é a transição `AGUARDANDO_APROVACAO → CONCLUIDA` (valida que quem aprova é o responsável/Owner) — e é ela que dispara `tarefas_liberadas`.
- **Frontend:** ação "Aprovar conclusão" no `TarefaModal` (visível ao responsável); card e relatório de Responsáveis exibem o novo estado.

## A.7 Requisitos funcionais adicionais

### RF-003 — Responsável obrigatório
- [ ] Toda etapa exige `responsavel_pessoa_id` (validação no create/edit).
- [ ] Etapas legadas sem responsável: prompt pra atribuir.

### RF-004 — Executores por passo
- [ ] Cada item de checklist pode ter executor (`responsavel_pessoa_id`) — já no schema; expor na UI do passo.
- [ ] Card agrega executores dos passos.

### RF-005 — Aprovação
- [ ] Checklist 100% → `AGUARDANDO_APROVACAO` (não conclui).
- [ ] Responsável aprova → `CONCLUIDA` (+ libera dependentes); reprova → `EM_ANDAMENTO` + nota.
- [ ] Executor não aprova a própria etapa.
- [ ] Evento de aprovação/reprovação auditado (`auditoria_eventos`).

### RF-006 — Setor da pessoa (via `areas`, sem CRUD — F2 §2)
- [ ] `projeto_pessoas.area_slug REFERENCES areas(slug)` (vocabulário fixo do F2 §7).
- [ ] Sugerir responsável/executor por categoria↔`area_slug`.
- [ ] Filtro por setor no relatório de Responsáveis.
- [ ] NÃO criar tabela editável de setor (respeita F2 §2 — capex por categoria).

## A.9 Entrega → Aprovação (formulário do executor → portão do responsável)

Materializa o F2 §5 (formulário externo por token) + o gate de aprovação (A.3).
Caso de uso: etapa "Buscar e avaliar pontos comerciais" — executor entrega
pesquisa/formulário; responsável valida antes de concluir.

### Fluxo
```
Executor preenche "Pacote de Entrega" (no app OU link externo /acesso?code=token):
   ├─ "O que foi entregue" (resumo da execução)        ← campo obrigatório
   ├─ anexos (formulário, página de consulta, planilha, link, comprovante)
   └─ marca passos do checklist (executor por passo)
        │  [Enviar para aprovação]
        ▼
   Etapa → AGUARDANDO_APROVACAO  (grava ENTREGA: resumo + anexos + autor + evento)
        │  notifica responsável (badge no card + rota /responsaveis + e-mail F3)
        ▼
   Responsável abre a etapa → Página de Entrega (read-only consolidada)
        ├─ [Aprovar]  → CONCLUÍDA + libera dependentes (A.4)
        └─ [Reprovar] → EM_ANDAMENTO + motivo (executor refaz)
```

### Página de Entrega — estrutura da info que chega no responsável
| Bloco | Origem (reuso) |
|-------|----------------|
| Cabeçalho: etapa · categoria · Responsável · Executores | `tarefas` + `tarefa_participantes` |
| **Entregável** — "o que foi entregue" | nota tipada `ENTREGA` em `tarefa_notas` + campo `resumo_entrega` |
| Checklist: passos + quem executou + quando | `tarefa_checklist.responsavel_pessoa_id` (já existe) |
| Anexos (formulário, consulta, comprovante) | sistema de anexos (já existe) |
| Histórico de notas de progresso | `tarefa_notas` (já existe) |
| Ações: Aprovar / Reprovar (com motivo) | nova transição `AGUARDANDO_APROVACAO → CONCLUÍDA/EM_ANDAMENTO` |

### Reuso máximo (não reinventar)
- **Entregável + anexos** = `tarefa_notas` (tipo `ENTREGA`) + anexos existentes — sem tabela nova de conteúdo.
- **Link externo por token** = padrão `/acesso?code=` (LeadAccessPage) — já pronto, F2 §5 aponta.
- **Papéis** = `tarefa_participantes` (F2 §7).
- **Novo de fato:** estado `AGUARDANDO_APROVACAO`, ação aprovar/reprovar (backend, valida que é o RESPONDE/Owner), `resumo_entrega`, e a view "Página de Entrega".

### RF-007 — Entrega e aprovação
- [ ] Executor envia Pacote de Entrega (resumo obrigatório + anexos) → etapa vai a `AGUARDANDO_APROVACAO`.
- [ ] Página de Entrega consolida resumo + checklist (com executores) + anexos + notas.
- [ ] Responsável (RESPONDE) ou Owner/Admin aprova/reprova; executor não aprova a própria entrega.
- [ ] Aprovar concretiza CONCLUÍDA (dispara liberação de dependentes); reprovar volta a EM_ANDAMENTO com motivo.
- [ ] Toda entrega/aprovação/reprovação auditada (`auditoria_eventos`).
- [ ] (F3) link externo por token permite executor sem login entregar.

## A.8 Decisões abertas (fechar antes de implementar)
| Código | Decisão | Recomendação |
|--------|---------|--------------|
| AD-001 | `AGUARDANDO_APROVACAO`: status novo (5ª coluna) ou flag? | ✅ **DECIDIDO: status novo — 5ª coluna "Em aprovação"** (entre Em andamento e Concluídas). Mantém BLOQUEADA = dependência. |
| AD-002 | Quem aprova além do responsável? | ✅ **DECIDIDO: Responsável (RESPONDE) + Owner/Org Admin** (override). Executor nunca aprova a própria. |
| AD-003 | Etapa sem checklist precisa de aprovação? | Sim — aprovação manual do responsável (botão concluir = aprovar) |
| AD-004 | Reprovar reabre quais passos? | Todos voltam a "pendente" ou nota indica quais — definir |

> **Impacto nas waves:** Wave 0 = "Migração de schema do pacote pós-F2 (F2 §7: `areas`, `tarefa_participantes`, `tarefa_okrs`) + estado/flag `AGUARDANDO_APROVACAO` + `tarefa_notas.tipo`/`resumo_entrega` + `projeto_pessoas.area_slug`". Roda antes das demais. Reaproveita o pacote de metadados que o F2 §7 já planejou — não duplica.

---

# APÊNDICE B — Metodologia oficial: SIPOC (lean) + PDCA + 5W2H

> **Decisão (2026-06-13):** a rota do Plano de Abertura adota **SIPOC lean + PDCA + 5W2H + critério de aceite** como metodologia oficial. Fontes: blog Sults (plano-de-ação, 5w2h, pdca, checklist, sipoc, gestão/padronização de processos, kaizen) + Air Academy (SIPOC/DMAIC). SIPOC é incorporado como **espinha conceitual** (não 5 campos por etapa — o próprio material trata SIPOC como workshop de 1-2h, não formulário por tarefa).

## B.1 Cada etapa = um processo SIPOC, executado via PDCA

| SIPOC | Significado | Materialização na etapa | Já existe? |
|-------|-------------|-------------------------|-----------|
| **Suppliers** | quem fornece o insumo | etapa **predecessora** (`tarefa_dependencias` TERMINA_PARA_COMECAR) ou parte externa | ✅ |
| **Inputs** | o que entra pra começar | entregável da predecessora / docs (derivável; sem campo novo) | ✅ derivado |
| **Process** | a execução | checklist (atividades) · dono = **Responsável** (RESPONDE) · faz = **Executores** (EXECUTA, por passo) | ✅ |
| **Outputs** | o que sai | **entrega** = nota tipo `ENTREGA` + anexos ("o que foi entregue") | ✅ schema |
| **Customers** | quem recebe e **aceita** | próxima etapa (dependente) e/ou o Responsável; aceite por **critério de verificação** | ⚠️ falta `criterio_verificacao` |

**Fronteira da etapa (airacad):** definida por *quem fornece o input* (Supplier=predecessora) e *quem recebe o output* (Customer=dependente/responsável). É exatamente a malha de dependências + entrega.

## B.2 Ciclo de vida PDCA = colunas do kanban

| PDCA | Coluna | O que acontece |
|------|--------|----------------|
| **Plan** | A fazer | etapa definida (5W2H) + **critério de aceite** semeado pelo gerador |
| **Do** | Em andamento | executores fazem; marcam **checklist verificável** (+evidência/anexo); registram notas |
| **Check** | Em aprovação | "Enviar para aprovação" → Responsável **verifica o Output contra o critério de aceite** → Aprova/Reprova |
| **Act** | Concluídas | aprovado → conclui + libera dependentes (handoff) + (padroniza: registro fica como POP/histórico) |
| — | Bloqueadas | ortogonal: predecessora (Supplier) ainda não entregou |

## B.3 5W2H = campos da etapa (mapeados no schema atual)
What=`titulo`/`descricao` · Why=`origem_relatorio_*` · Who=`tarefa_participantes` (RESPONDE/EXECUTA) · Where=projeto/bairro · When=`data_inicio`/`data_prevista_conclusao` · How=checklist · HowMuch=`custo_planejado`/`custo_real`.

## B.4 Critério de aceite (o gate do Check) — RF-008

> Único campo novo que a metodologia exige além do que já temos.

- **`tarefas.criterio_verificacao TEXT`** — "o que comprova que a etapa foi concluída com eficácia" (ex.: *"3 imóveis avaliados com foto e parecer; visita à prefeitura registrada"*).
- Redigido como **afirmação verificável** (checklist guideline da Sults).
- Gerador semeia sugestão por categoria; editável pelo dono (P-003: nada auto-associado sem edição).
- Exibido na **Página de Entrega** — o Responsável aprova/reprova **contra ele** (não "tá feito?", e sim "atingiu o critério?").
- [ ] Migração `20260613_criterio_verificacao.sql` (1 coluna).
- [ ] Backend retorna no payload + aceita no create/edit.
- [ ] Frontend: exibe na etapa + na Página de Entrega.

## B.5 Fluxo Do→Check (fecha o gap do teste real)
1. Executor trabalha (checklist/notas) → clica **"Enviar para aprovação"** com **resumo da entrega** (Output).
2. Etapa → `AGUARDANDO_APROVACAO`; cria nota tipo `ENTREGA`.
3. Responsável abre **Página de Entrega**: critério de aceite + resumo + checklist (com executores) + anexos + notas.
4. **Aprova** (atingiu o critério) → `CONCLUIDA` + libera dependentes · **Reprova** → `EM_ANDAMENTO` + motivo (volta pro Do — Kaizen/PDCA).

> Coexistência: quem trabalha por checkbox usa a auto-transição (checklist 100% → Em aprovação); quem trabalha por entrega usa o "Enviar para aprovação". Os dois caem no mesmo Check.
