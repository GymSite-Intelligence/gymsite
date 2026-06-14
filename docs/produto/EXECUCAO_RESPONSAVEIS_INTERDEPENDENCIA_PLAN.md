# PLAN Técnico — Execução: Responsáveis + Interdependência + Aprovação

> **Para:** análise e aprovação antes de tocar schema/código.
> **SPEC:** `docs/produto/EXECUCAO_RESPONSAVEIS_INTERDEPENDENCIA.md` (+ Apêndice A).
> **Status:** Draft · **Data:** 2026-06-13
> **Princípio:** migração idempotente, com rollback por passo, aplicada em branch/staging do Supabase antes de produção.

---

## 0. Premissas e estado as-built (verificado no código)

| Objeto | Estado hoje | Fonte |
|--------|-------------|-------|
| `tarefas.status` CHECK | `A_FAZER, EM_ANDAMENTO, CONCLUIDA, BLOQUEADA, CANCELADA` | `db/migrations/20250610_add_execucao_schema.sql:126` |
| `tarefas.categoria` CHECK | 10 valores (IMOBILIARIO…OUTRO) | idem |
| `tarefas.responsavel_pessoa_id` | existe (FK `projeto_pessoas`) | `playbook_service` / F2 §3 |
| `tarefas.okr_id` | existe, **morto** (sem N:N) | schema |
| `tarefa_checklist.responsavel_pessoa_id` | existe (executor por passo) | `20260611_pessoas_anexos.sql` |
| `tarefa_notas` | `origem ∈ (DONO,EXTERNO,IA)`, `texto`, RLS por tarefa→user | `20260611_tarefa_notas.sql` |
| `tarefa_dependencias` | `(tarefa_id, depende_de_tarefa_id, tipo)`; guardrail auto-block/unblock | `playbook_service` |
| `projeto_pessoas` | nome/papel/email/telefone, soft delete, RLS | `20260611_pessoas_anexos.sql` |
| `areas`, `tarefa_participantes`, `tarefa_okrs` | **planejados no F2 §7, NÃO codados** | F2 |

> ⚠️ Nome do constraint de status: inline sem nome → Postgres gera `tarefas_status_check`. Confirmar com `\d tarefas` antes de aplicar (o DROP abaixo assume esse nome).

---

## WAVE 0 — Migração de schema (Supabase)

> Arquivo: `db/migrations/20260613_execucao_raci_aprovacao.sql`. Tudo `IF NOT EXISTS`/guardado. Aplicar em **branch** primeiro (`mcp supabase create_branch`), validar, depois merge.

### 0.1 Novo status `AGUARDANDO_APROVACAO`
```sql
ALTER TABLE tarefas DROP CONSTRAINT IF EXISTS tarefas_status_check;
ALTER TABLE tarefas ADD CONSTRAINT tarefas_status_check
  CHECK (status IN ('A_FAZER','EM_ANDAMENTO','AGUARDANDO_APROVACAO','CONCLUIDA','BLOQUEADA','CANCELADA'));
```
**Rollback:** recriar o CHECK sem `AGUARDANDO_APROVACAO` (exige nenhuma linha nesse estado — UPDATE para EM_ANDAMENTO antes).

### 0.2 `areas` (vocabulário fixo — F2 §7/§2; sem CRUD de usuário)
```sql
CREATE TABLE IF NOT EXISTS areas (
  slug TEXT PRIMARY KEY,
  rotulo TEXT NOT NULL,
  cor TEXT NOT NULL,                 -- token: 'var(--chart-1)' etc.
  ordem INT NOT NULL DEFAULT 0,
  tipo_negocio TEXT NOT NULL DEFAULT 'academia'
);
INSERT INTO areas (slug, rotulo, cor, ordem) VALUES
  ('IMOBILIARIO','Imóvel','var(--chart-1)',1),
  ('LEGAL','Documentação','var(--chart-4)',2),
  ('OBRAS','Obra','var(--chart-3)',3),
  ('EQUIPAMENTOS','Equipamentos','var(--chart-5)',4),
  ('TECNOLOGIA','Tecnologia','var(--chart-2)',5),
  ('RH','Equipe','var(--chart-1)',6),
  ('MARKETING','Marketing','var(--chart-5)',7),
  ('FINANCEIRO','Financeiro','var(--chart-4)',8),
  ('OPERACIONAL','Operação','var(--chart-2)',9),
  ('OUTRO','Outros','var(--muted-foreground)',10)
ON CONFLICT (slug) DO NOTHING;
-- FK opcional nesta wave: manter o CHECK de categoria por ora (menor risco).
-- Trocar CHECK→FK só após o payload entregar `areas` (evita quebrar inserts do gerador).
```
**Rollback:** `DROP TABLE areas;` (só se nada referenciar).

### 0.3 `tarefa_participantes` (RACI N:N — F2 §7)
```sql
CREATE TABLE IF NOT EXISTS tarefa_participantes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
  pessoa_id UUID NOT NULL REFERENCES projeto_pessoas(id) ON DELETE CASCADE,
  papel TEXT NOT NULL DEFAULT 'EXECUTA'
    CHECK (papel IN ('RESPONDE','EXECUTA','CONSULTADO','INFORMADO')),
  criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  UNIQUE (tarefa_id, pessoa_id, papel)
);
CREATE INDEX IF NOT EXISTS idx_tarefa_part_tarefa ON tarefa_participantes(tarefa_id);
ALTER TABLE tarefa_participantes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tarefa_part_user" ON tarefa_participantes;
CREATE POLICY "tarefa_part_user" ON tarefa_participantes FOR ALL USING (
  EXISTS (SELECT 1 FROM tarefas t JOIN playbooks p ON p.id = t.playbook_id
          WHERE t.id = tarefa_participantes.tarefa_id AND p.user_id = auth.uid())
);
-- Migração de dados: responsável atual vira RESPONDE
INSERT INTO tarefa_participantes (tarefa_id, pessoa_id, papel)
SELECT id, responsavel_pessoa_id, 'RESPONDE' FROM tarefas
WHERE responsavel_pessoa_id IS NOT NULL
ON CONFLICT DO NOTHING;
```
**Rollback:** `DROP TABLE tarefa_participantes;`

### 0.4 `tarefa_okrs` (N:N — substitui `tarefas.okr_id` morto)
```sql
CREATE TABLE IF NOT EXISTS tarefa_okrs (
  tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
  okr_id UUID NOT NULL REFERENCES okrs(id) ON DELETE CASCADE,
  PRIMARY KEY (tarefa_id, okr_id)
);
ALTER TABLE tarefa_okrs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tarefa_okrs_user" ON tarefa_okrs;
CREATE POLICY "tarefa_okrs_user" ON tarefa_okrs FOR ALL USING (
  EXISTS (SELECT 1 FROM tarefas t JOIN playbooks p ON p.id = t.playbook_id
          WHERE t.id = tarefa_okrs.tarefa_id AND p.user_id = auth.uid())
);
INSERT INTO tarefa_okrs (tarefa_id, okr_id)
SELECT id, okr_id FROM tarefas WHERE okr_id IS NOT NULL
ON CONFLICT DO NOTHING;
-- `tarefas.okr_id` mantido por ora (drop só após service migrar pra tarefa_okrs).
```
**Rollback:** `DROP TABLE tarefa_okrs;`

### 0.5 Entrega/aprovação em `tarefa_notas` + setor da pessoa
```sql
ALTER TABLE tarefa_notas ADD COLUMN IF NOT EXISTS tipo TEXT NOT NULL DEFAULT 'PROGRESSO'
  CHECK (tipo IN ('PROGRESSO','ENTREGA','APROVACAO','REPROVACAO'));
-- `texto` da nota tipo ENTREGA = "o que foi entregue" (resumo). Sem coluna nova de conteúdo.
ALTER TABLE tarefa_notas DROP CONSTRAINT IF EXISTS tarefa_notas_origem_check;
ALTER TABLE tarefa_notas ADD CONSTRAINT tarefa_notas_origem_check
  CHECK (origem IN ('DONO','EXTERNO','IA','EXECUTOR'));   -- +EXECUTOR

ALTER TABLE projeto_pessoas ADD COLUMN IF NOT EXISTS area_slug TEXT REFERENCES areas(slug);
```
**Rollback:** `ALTER TABLE tarefa_notas DROP COLUMN tipo;` + restaurar CHECK origem; `ALTER TABLE projeto_pessoas DROP COLUMN area_slug;`

> **Ordem na Wave 0:** 0.2 (areas) → 0.5 (area_slug depende de areas) ; 0.1, 0.3, 0.4 independentes. Tudo num único arquivo transacional.

---

## WAVE 1 — Backend (guardrail revisado + aprovação)

`backend/services/execucao/playbook_service.py`:
- **`_status_alvo_por_checklist`:** trocar `done==total → CONCLUIDA` por `done==total → AGUARDANDO_APROVACAO`. (BLOQUEADA por dependência **antes**, como hoje.)
- **`atualizar_status_tarefa`:** nova regra de transição:
  - `AGUARDANDO_APROVACAO → CONCLUIDA`: só se quem chama for **RESPONDE** da tarefa OU Owner/Org Admin. Senão `ValueError("Apenas o responsável aprova a conclusão.")`. Dispara `tarefas_liberadas` (já existe).
  - `AGUARDANDO_APROVACAO → EM_ANDAMENTO` (reprovar): grava nota tipo `REPROVACAO` (motivo) + evento.
  - Bloquear conclusão direta por não-responsável (mesmo com checklist 100%).
- **Entrega:** `enviar_para_aprovacao(tarefa_id, resumo, anexos[])` → cria nota tipo `ENTREGA` (origem EXECUTOR) + move para `AGUARDANDO_APROVACAO` + evento.
- **Auditoria:** eventos `ENVIAR_APROVACAO`, `APROVAR_TAREFA`, `REPROVAR_TAREFA` em `auditoria_eventos`.

`backend/routers/execucao.py` — novos endpoints:
```
POST  /api/execucao/tarefas/{id}/enviar-aprovacao   { resumo, anexo_ids? }
POST  /api/execucao/tarefas/{id}/aprovar             { }            → CONCLUIDA
POST  /api/execucao/tarefas/{id}/reprovar            { motivo }     → EM_ANDAMENTO
```
**Rollback backend:** reverter para o guardrail atual (`done==total → CONCLUIDA`); remover rotas.

---

## WAVE 2 — Frontend (kanban 5 colunas + Página de Entrega)

- `PlaybookKanban.COLUNAS`: inserir `{ status: 'AGUARDANDO_APROVACAO', titulo: 'Em aprovação' }` entre Em andamento e Bloqueadas. Ordem final: **A fazer · Em andamento · Em aprovação · Bloqueadas · Concluídas**.
- `TarefaModal`: botão muda por papel/estado:
  - executor / em andamento → **"Enviar para aprovação"** (chama `enviar-aprovacao`, abre form com resumo + anexos).
  - responsável / em aprovação → **"Aprovar"** + **"Reprovar"** (com motivo).
- **Card** (TarefaCardInner): exibir **Responsável** (avatar+"Resp.") + **Executores** (chips dos passos). "Bloqueada por: X" quando dependência.
- **Página de Entrega** (no modal, aba/seção): resumo entregue + checklist com executores + anexos + notas — o que o responsável analisa.
- `STATUS_LABEL` + cor do novo status (token).

**Rollback frontend:** remover a coluna/label; restaurar botão "Salvar mudança".

---

## WAVE 3 — Rota `/responsaveis` (KPIs)
- Backend: `GET /api/execucao/responsaveis?playbook_id=` (agregação por pessoa — RF-001).
- Frontend: rota + page (cards/tabela Geo-Intel) + sidebar; click → `/execucao/$id?responsavel=`.

## WAVE 4 — UI de dependências
- `EtapaFormDialog`: "Depende de" (multi-select etapas do playbook).
- Endpoints `POST /tarefas/{id}/dependencias`, `DELETE /dependencias/{id}` com **validação anti-ciclo (DAG)** no service.
- Card/modal: "Bloqueada por: X".

## F3 (depois) — formulário externo por token (`/acesso?code=`), página de consulta pública.

---

## Riscos & mitigação
| Risco | Mitigação |
|-------|-----------|
| DROP CONSTRAINT em prod com nome errado | confirmar `\d tarefas`; aplicar em branch primeiro |
| Linhas em estado removido no rollback | UPDATE para estado válido antes de recriar CHECK |
| Migração de dados parcial (participantes/okrs) | `ON CONFLICT DO NOTHING` + verificação de contagem pós-migração |
| Gate de aprovação só no backend service (não RLS) | service valida papel; follow-up RLS por participante |
| Backend sem --reload | restart manual após deploy do service |
| Cascata de liberação > 1 nível | documentado; recursão opcional em iteração futura |

## Ordem de aplicação (best practice)
1. `create_branch` no Supabase → rodar `20260613_execucao_raci_aprovacao.sql` → validar contagens (participantes = nº tarefas com responsável; okrs migrados).
2. Wave 1 backend em dev (restart manual) → testar transições.
3. Wave 2 frontend → `tsc -b` + smoke no kanban.
4. `merge_branch` → deploy backend (canário, como o street view).
5. Waves 3–4 incrementais.

---

## Critérios de aceite do PLAN
- [ ] Migração roda limpa em branch (0 erro) e contadores batem
- [ ] Rollback de cada passo testado em branch
- [ ] `tsc -b` limpo nas waves de frontend
- [ ] Transição de aprovação rejeita não-responsável
- [ ] Guardrail: 100% checklist → Em aprovação (não conclui sozinho)
- [ ] Anti-ciclo de dependência testado

> **Aprovação:** revisar este PLAN → ajustar → autorizar Wave 0 (branch Supabase).
