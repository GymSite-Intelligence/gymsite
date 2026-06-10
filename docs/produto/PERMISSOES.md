# Permissões e Compartilhamento

> Modelo de controle de acesso (RBAC), fluxo de convites e regras de privacidade para projetos, playbooks e relatórios.

---

## 1. Princípios

1. **O dono do projeto é soberano.** Ele pode ver, editar, excluir e compartilhar tudo.
2. **Convidados só veem o que precisam.** Um prestador de obra não precisa ver custos financeiros.
3. **Nada é público por padrão.** Todo acesso requer convite explícito.
4. **Auditável.** Todo convite, aceite, remoção e alteração de permissão é logado.

---

## 2. Papéis (Roles)

### 2.1. Papéis por Projeto

| Papel | Descrição | Quem recebe |
|-------|-----------|-------------|
| **Owner (Dono)** | Controle total. Criou o projeto. Pode excluir, arquivar, convidar, remover. | Empreendedor que iniciou o projeto. |
| **Editor** | Pode editar tarefas, marcar como concluída, adicionar comentários, anexos. Não pode excluir projeto nem convidar. | Sócio, gestor de operações. |
| **Viewer** | Pode ver tudo, mas não editar. Pode comentar. | Investidor, consultor externo, franqueador. |
| **Executor** | Pode ver e editar APENAS tarefas atribuídas a ele. Não vê custos totais, OKRs, dashboards. | Prestador de serviço (pedreiro, marceneiro, instalador). |

### 2.2. Papéis por Organização (Enterprise)

| Papel | Descrição | Escopo |
|-------|-----------|--------|
| **Org Admin** | Cria projetos, gerencia usuários da org, define white-label, acessa billing. | Toda a organização. |
| **Org Manager** | Acompanha todos os projetos da org. Pode editar qualquer projeto. Não gerencia billing. | Toda a organização. |
| **Org Viewer** | Dashboard consolidado de todos os projetos. Read-only. | Toda a organização. |

### 2.3. Matriz de Permissões

| Ação | Owner | Editor | Viewer | Executor | Org Admin | Org Manager |
|------|:-----:|:------:|:------:|:--------:|:---------:|:-----------:|
| Ver projeto | ✅ | ✅ | ✅ | ✅* | ✅ | ✅ |
| Editar projeto (nome, descrição) | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Excluir projeto | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Arquivar projeto | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Convidar usuários | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Remover convidados | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Criar/editar tarefas | ✅ | ✅ | ❌ | ✅** | ✅ | ✅ |
| Concluir tarefa | ✅ | ✅ | ❌ | ✅** | ✅ | ✅ |
| Ver todas as tarefas | ✅ | ✅ | ✅ | ❌*** | ✅ | ✅ |
| Ver tarefas atribuídas a mim | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ver custos totais | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Registrar custo real | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Ver OKRs | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Ver dashboard | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Gerar relatório | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Exportar PDF | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Comentar em tarefa | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Adicionar anexo | ✅ | ✅ | ❌ | ✅** | ✅ | ✅ |
| Ver anexos | ✅ | ✅ | ✅ | ✅** | ✅ | ✅ |
| Ver relatório formal | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Configurar notificações do projeto | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |

> *Executor vê apenas título e descrição do projeto, não dados sensíveis.
> **Executor só pode editar tarefas atribuídas a ele.
> ***Executor não vê tarefas de outros (só as dele).

---

## 3. Fluxo de Convite

### 3.1. Convite por Email

```
Owner clica "Convidar" no projeto
    │
    ├──► Digita email + seleciona papel (Editor/Viewer/Executor)
    │
    ├──► Sistema envia email de convite:
    │      "Marcelo te convidou para colaborar no projeto
    │       'Abertura Academia Cabo Branco' como [Editor].
    │       Aceitar convite → [link]"
    │
    ├──► Convite fica PENDENTE por 7 dias
    │
    ├──► Convidado clica link → cria conta (se não tem) → aceita
    │
    └──► Sistema notifica Owner: "[Nome] aceitou seu convite."
```

### 3.2. Convite por Link Mágico (Pro/Enterprise)

```
Owner gera link de convite com papel pré-definido
    │
    ├──► Link: https://gymsite.io/convite/abc123?papel=editor
    │
    ├──► Owner envia por WhatsApp/Slack/email manualmente
    │
    ├──► Quem clicar e tiver conta GymSite → entra direto
    │
    └──► Link pode ser revogado a qualquer momento
```

> **Regra:** Link mágico só disponível no Pro e Enterprise. Free não compartilha.

### 3.3. Tabela `projeto_membros`

```sql
CREATE TABLE projeto_membros (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projeto_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id),  -- NULL se convite pendente
    email TEXT NOT NULL,                       -- email do convidado
    papel TEXT NOT NULL
        CHECK (papel IN ('OWNER', 'EDITOR', 'VIEWER', 'EXECUTOR')),
    status TEXT NOT NULL DEFAULT 'PENDENTE'
        CHECK (status IN ('PENDENTE', 'ACEITO', 'RECUSADO', 'REMOVIDO')),
    convidado_por UUID REFERENCES auth.users(id),  -- quem enviou convite
    convite_token TEXT UNIQUE,                 -- para link mágico
    convite_expira_em TIMESTAMPTZ,
    aceitado_em TIMESTAMPTZ,
    removido_em TIMESTAMPTZ,
    removido_por UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX idx_projeto_membros_projeto_user ON projeto_membros(projeto_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX idx_projeto_membros_projeto_email ON projeto_membros(projeto_id, email);
```

---

## 4. Privacidade por Papel

### 4.1. O que cada papel NÃO vê

| Papel | Dados Ocultos | Motivo |
|-------|--------------|--------|
| **Viewer** | Botões de edição, formulários de custo, opção de excluir | Read-only por definição |
| **Executor** | Custo total do projeto, OKRs, dashboards, relatório formal, tarefas dos outros | Segurança comercial. Prestador não precisa saber investimento total. |
| **Editor** | Opção de excluir projeto, convidar usuários, billing | Protege contra erro ou malícia |

### 4.2. Tela do Executor (Exemplo)

```
Projeto: Abertura Academia Cabo Branco

Suas Tarefas:
┌─────────────────────────────────────┐
│ 🔨 Instalar piso vinílico           │
│    Prazo: 15/07/2026                │
│    Checklist: [ ] Medir área        │
│               [ ] Comprar material  │
│               [ ] Instalar          │
│    Anexos: projeto_piso.pdf         │
│    Comentários: 2 novos             │
└─────────────────────────────────────┘

[Marcar como concluída]  [Adicionar foto]

⚠️ Você não tem acesso aos custos e cronograma
    completo do projeto. Fale com [Owner] se precisar.
```

---

## 5. RLS (Row Level Security) por Papel

### 5.1. Tabela `user_projects`

```sql
-- Owner sempre vê
CREATE POLICY "projects_owner" ON user_projects
    FOR ALL USING (auth.uid() = user_id);

-- Membros convidados veem
CREATE POLICY "projects_member" ON user_projects
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM projeto_membros
            WHERE projeto_membros.projeto_id = user_projects.id
            AND projeto_membros.user_id = auth.uid()
            AND projeto_membros.status = 'ACEITO'
        )
    );
```

### 5.2. Tabela `tarefas`

```sql
-- Owner e Editor veem todas
-- Viewer ve todas (read-only via frontend)
-- Executor só vê atribuídas a ele
CREATE POLICY "tarefas_executor" ON tarefas
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM projeto_membros pm
            JOIN user_projects up ON up.id = tarefas.projeto_id
            WHERE pm.projeto_id = tarefas.projeto_id
            AND pm.user_id = auth.uid()
            AND pm.papel = 'EXECUTOR'
            AND tarefas.responsavel_email = (
                SELECT email FROM auth.users WHERE id = auth.uid()
            )
        )
    );
```

### 5.3. Tabela `relatorio_outputs`

```sql
-- Só Owner, Editor, Viewer e Org Admin/Manager veem
-- Executor NÃO vê
CREATE POLICY "relatorios_restrict" ON relatorio_outputs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM projeto_membros pm
            JOIN user_projects up ON up.id = relatorio_outputs.projeto_id
            WHERE pm.projeto_id = relatorio_outputs.projeto_id
            AND pm.user_id = auth.uid()
            AND pm.status = 'ACEITO'
            AND pm.papel IN ('OWNER', 'EDITOR', 'VIEWER')
        )
        OR EXISTS (
            SELECT 1 FROM org_membros om
            WHERE om.org_id = relatorio_outputs.org_id
            AND om.user_id = auth.uid()
            AND om.papel IN ('ADMIN', 'MANAGER')
        )
    );
```

---

## 6. Auditoria

### 6.1. Tabela `auditoria_acessos`

```sql
CREATE TABLE auditoria_acessos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projeto_id UUID NOT NULL,
    user_id UUID NOT NULL,
    acao TEXT NOT NULL,           -- 'CONVITE_ENVIADO', 'CONVITE_ACEITO', 'MEMBRO_REMOVIDO', 'PAPEL_ALTERADO'
    alvo_user_id UUID,            -- quem foi convidado/removido
    detalhes JSONB,               -- { papel_anterior: 'EDITOR', papel_novo: 'VIEWER' }
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 6.2. Eventos Auditados

- Convite enviado (quem, para quem, qual papel)
- Convite aceito/recusado
- Membro removido
- Papel alterado
- Projeto excluído/arquivado
- Relatório exportado (PDF) — quem baixou

---

## 7. Decisões de Produto

| Código | Decisão | Justificativa |
|--------|---------|---------------|
| **PE-001** | Free não compartilha projeto | Compartilhamento é diferenciador Pro. Free é uso individual. |
| **PE-002** | Executor é um papel real, não apenas Viewer | Prestador precisa marcar tarefa concluída e anexar foto, mas não ver custos. |
| **PE-003** | Convite expira em 7 dias | Segurança. Evita links antigos funcionando eternamente. |
| **PE-004** | Owner pode remover a si mesmo apenas se houver outro Owner | Projeto nunca fica órfão. |
| **PE-005** | Org Admin pode assumir qualquer projeto da org | Gestor de rede precisa acessar projetos de franqueados, mesmo sem convite. |
| **PE-006** | Audit trail é append-only, nunca deletado | Compliance e resolução de conflitos. |

---

## 8. Checklist de Implementação

- [ ] Tabela `projeto_membros` criada com RLS
- [ ] Tabela `org_membros` criada (Enterprise)
- [ ] Tabela `auditoria_acessos` criada
- [ ] Endpoint `POST /api/projetos/{id}/convidar`
- [ ] Endpoint `POST /api/projetos/{id}/convites/{token}/aceitar`
- [ ] Endpoint `DELETE /api/projetos/{id}/membros/{user_id}`
- [ ] Endpoint `PATCH /api/projetos/{id}/membros/{user_id}/papel`
- [ ] Endpoint `POST /api/projetos/{id}/convite-link` (Pro/Enterprise)
- [ ] Endpoint `DELETE /api/projetos/{id}/convite-link` (revogar)
- [ ] RLS policies atualizadas em TODAS as tabelas sensíveis
- [ ] Frontend: tela "Membros do Projeto" com lista, convite, remoção
- [ ] Frontend: badge de papel em cada membro (Owner, Editor, etc.)
- [ ] Email de convite com template
- [ ] Testes: cada papel acessa apenas o que deve
- [ ] Testes: audit trail registra todas as ações
