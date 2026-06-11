# Playbook F2 — Enriquecimento do Módulo de Execução

> Spec derivada do benchmark do template Lark "Task Management [AI]"
> (base do Marcelo, analisada via navegador em 11/06/2026) cruzado com o
> estado as-built do módulo (`MODULO_EXECUCAO_E_GESTAO_PROJETO.md`).
> Decisões respeitam P-001..P-007 (`.agent/rules/processo-mudanca.md`).

## 1. O que o benchmark tem e nós não

| # | Conceito (Lark) | Estado no GymSite | Valor |
|---|---|---|---|
| 1 | Progress notes — diário de andamento por tarefa | Não existe | Alto |
| 2 | Overdue em 3 estados: atrasada aberta, **concluída com atraso de N dias**, normal | Só `dias_atraso` runtime de etapa aberta; concluída atrasada vira "normal" | Alto |
| 3 | Camada OKR: objetivo → métrica (Data Index) → atingido, link bidirecional com tarefas | Tabela `okrs` + FK `tarefas.okr_id` **já existem no schema**, sem service/router/UI | Alto |
| 4 | Task summary gerado por IA a partir dos demais campos | Não existe | Médio |
| 5 | Prioridade (Important/Normal) | Não existe | Médio |
| 6 | Múltiplas views sobre os mesmos dados (grade, kanban, calendário, gantt, galeria) | Só Kanban + filtro de categoria | Médio |
| 7 | Dashboard (funil de metas, donut de status, atraso, carga por responsável) | Só header (%/gasto/previsão) | Médio |
| 8 | **Formulário** — link público de escrita externa, sem login | Não existe (padrão análogo já existe: `/acesso?code=` do LeadAccessPage) | Alto (F3) |
| 9 | **Página de consulta** — link público read-only com filtros | Não existe | Médio (F3) |
| 10 | Automações (lembrete de prazo) | Não existe | Médio (F3) |

## 2. Decisão: CRUD de setores — NÃO criar

A categoria da tarefa (`IMOBILIARIO`, `LEGAL`, `RH`, …) é **infraestrutura do
gerador**, não dado do usuário:

- `_DISTRIBUICAO_CAPEX_DETALHADO` no `playbook_generator.py` mapeia capex por
  categoria — categoria livre quebraria a distribuição de custos.
- `CATEGORIA_LABEL`/`CATEGORIA_COR` no front são o vocabulário do domínio
  (P-001: "Imóvel", "Documentação", "Equipe").
- O empreendedor abre **uma** academia; ele não precisa inventar setores,
  precisa que o plano já venha organizado.

Setor customizado só entra se/quando houver tenant de franquia com processo
próprio (fora do horizonte F2/F3).

## 3. Decisão: CRUD de pessoas — SIM, versão leve

Hoje `tarefas.responsavel_nome` é texto solto ("Contador / Empreendedor").
Os responsáveis são **pessoas externas à plataforma** (contador, arquiteto,
fornecedor) — não usuários com login. Logo: entidade leve por projeto, não
gestão de usuários.

```sql
CREATE TABLE projeto_pessoas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_project_id UUID NOT NULL REFERENCES user_projects(id),
  nome TEXT NOT NULL,
  papel TEXT,                 -- "Contador", "Arquiteto", "Sócio"
  email TEXT,
  telefone TEXT,
  criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ      -- P-007
);
ALTER TABLE tarefas ADD COLUMN responsavel_pessoa_id UUID REFERENCES projeto_pessoas(id);
-- responsavel_nome permanece como exibição/fallback (tarefas geradas antes do vínculo)
```

- UI: seção "Pessoas do projeto" na página do plano — lista + modal
  criar/editar (mesmo padrão centralizado do TarefaModal). Soft delete.
- Gerador segue preenchendo `responsavel_nome` sugerido; vincular pessoa real
  é ação do dono (P-003: nada de auto-associação).
- Habilita: carga por responsável no dashboard, destinatário de formulário
  externo (F3), lembretes por e-mail/WhatsApp (F3).

## 4. Múltiplas views (menu "+" do Lark) — o que absorver

Lark oferece grade, kanban, calendário, gantt, galeria, formulário e página
de consulta como **views sobre a mesma tabela**. Para nós:

- Tab bar na página do plano: **Etapas (Kanban) | Lista | Linha do tempo**.
- View ativa no query param `?view=` (P-006 — F5 mantém a aba).
- **Lista agrupada por situação** vira o default no mobile (P-002): kanban de
  4 colunas exige scroll horizontal; lista agrupada não.
- Linha do tempo (gantt simplificado): barras por etapa usando
  `data_inicio`/`data_prevista_conclusao` + setas das 28 dependências já
  persistidas. Zoom mês/trimestre. Sem edição por arrasto na F2.
- Calendário e galeria: sem caso de uso claro — não fazer.

## 5. Formulários e página de consulta — potencial (F3)

O padrão Lark = colaboração externa sem conta. Nosso produto tem o mesmo
problema: contador, arquiteto e fornecedor não terão login no GymSite.

**Decisão (11/06): formulário é interface por papel, vale para processo
interno também.** O mesmo link recortado serve contador externo e sócio
interno — elimina UI dedicada de atribuição/atualização multi-stakeholder.
Caso VISA: tarefa tem 1 dono (Accountable); passo "Pagar taxa" atribuído ao
contador (Responsible) via `responsavel_pessoa_id` no checklist; comprovante
entra como anexo. Setor duplo na tarefa foi descartado (quebraria capex por
categoria e o kanban).

Já temos o mecanismo análogo pronto: `/acesso?code=` (LeadAccessPage com
código de acesso). Reusar o padrão:

1. **Formulário de atualização de etapa** — dono gera link com token por
   etapa/pessoa; externo abre, vê só os campos liberados (P-003), escreve
   nota de progresso, propõe situação nova e anexa arquivo. Escrita entra
   como nota `origem=EXTERNO` + evento em `auditoria_eventos`; mudança de
   status proposta exige aceite do dono (consistente com a trava de
   dependências do service).
2. **Página de consulta do plano** — link read-only com progresso, previsão
   de abertura e gasto vs previsto, para sócio/investidor/banco. Espelha o
   header da página de execução.
3. **Formulário de cotação** — fornecedor responde orçamento por etapa
   (ex.: 3 cotações de equipamentos); alimenta comparativo e refina
   `custo_planejado` com dado real.
4. Sinergia Vectra Cargo: etapa "Comprar aparelhos de musculação" pode
   embutir formulário de cotação de frete.

## 6. Escopo F2 (ordem de implementação)

1. **Notas de progresso** — `tarefa_notas` append-only (id, tarefa_id, autor,
   texto, criado_em). Seção "Andamento" no TarefaModal. Insumo direto para a
   IA consultora.
2. **Variância na conclusão** — gravar `data_real_conclusao` ao concluir;
   derivar em runtime (C-02, como `dias_atraso`): "concluída com N dias de
   atraso" / "adiantada". Já temos custo real vs previsto; isto fecha o par
   prazo real vs previsto.
3. **Pessoas do projeto** — migração + CRUD leve + vínculo na tarefa (§3).
4. **OKRs expostos** — service/router/UI sobre as tabelas existentes;
   gerador semeia 2–3 objetivos do relatório (meta de alunos da projeção
   financeira, data de abertura). Card de objetivos no topo do plano.
5. **Views Lista + Linha do tempo** com `?view=` (§4).
6. **Resumo IA da etapa** — Gemini (thinking_budget=0) resume título +
   notas + atraso + checklist em 1 frase no modal. Último por depender de 1–2.

F3 (não iniciar antes do F2 rodar de verdade): formulários externos, página
de consulta pública, dashboard de execução, lembretes.

## 7. Fora de escopo decidido

- CRUD de setores/categorias (§2).
- Prioridade na tarefa: adiada — a ordenação real do plano vem das
  dependências topológicas; um campo Important/Normal hoje viraria enfeite.
- Edição de gantt por arrasto.
