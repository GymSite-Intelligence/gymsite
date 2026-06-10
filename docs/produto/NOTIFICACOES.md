# Notificações — Eventos, Canais e Preferências

> Matriz de eventos, canais de entrega, frequência e regras de privacidade para o módulo GymSite Execução.

---

## 1. Filosofia

**Regra de ouro:** Notificar o mínimo necessário, no canal certo, na hora certa. Cada notificação deve ter uma ação clara.

**Anti-padrões a evitar:**
- ❌ Spam diário sem relevância
- ❌ Notificar em 3 canais ao mesmo tempo (email + push + WhatsApp)
- ❌ Notificações genéricas sem contexto ("Algo aconteceu")
- ❌ Notificar usuário às 3h da manhã

---

## 2. Eventos que Geram Notificação

### 2.1. Eventos do Consultor Conversacional

| Evento | Prioridade | Descrição | Ação Esperada |
|--------|-----------|-----------|---------------|
| `relatorio_pronto` | Alta | Seu Relatório de Viabilidade está pronto | Abrir relatório |
| `pesquisa_concluida` | Média | Pesquisa de [concorrentes/demografia/pontos] concluída | Ver resultado no chat |
| `novo_concorrente_detectado` | Alta | Nova academia abriu a [X]m do seu ponto | Revisar estratégia |
| `sugestao_ia_nova` | Média | A IA tem uma nova sugestão para seu projeto | Aceitar ou rejeitar |
| `projeto_inativo_7dias` | Baixa | Você não acessou seu projeto há 7 dias | Retomar conversa |

### 2.2. Eventos do Playbook

| Evento | Prioridade | Descrição | Ação Esperada |
|--------|-----------|-----------|---------------|
| `tarefa_atrasada` | Alta | Tarefa "[título]" está atrasada há [N] dias | Ver tarefa e reagendar |
| `tarefa_bloqueada_resolvida` | Média | A tarefa "[X]" que bloqueava "[Y]" foi concluída | Iniciar tarefa Y |
| `marco_se_aproxima` | Média | Faltam [N] dias para "[marco]" | Revisar dependências |
| `marco_atrasado` | Alta | O marco "[marco]" não foi atingido na data prevista | Revisar cronograma |
| `custo_desvio_alerta` | Alta | Custo real está [N]% acima do planejado na categoria [X] | Revisar orçamento |
| `playbook_concluido` | Alta | Parabéns! Seu playbook está 100% concluído | Ver próximos passos |
| `sugestao_ia_playbook` | Média | A IA sugere adicionar tarefa: "[título]" | Aceitar sugestão |
| `convite_aceito` | Baixa | [Nome] aceitou seu convite para o projeto | — |
| `tarefa_atribuida` | Média | Você foi designado como responsável por "[título]" | Ver tarefa |

### 2.3. Eventos de Sistema

| Evento | Prioridade | Descrição | Ação Esperada |
|--------|-----------|-----------|---------------|
| `limite_atingido` | Média | Você atingiu o limite de [recurso] no plano Free | Fazer upgrade |
| `trial_expirando` | Média | Seu período de teste expira em [N] dias | Escolher plano |
| `pagamento_falhou` | Alta | Não conseguimos processar seu pagamento | Atualizar cartão |
| `atualizacao_sistema` | Baixa | Novos recursos disponíveis: [lista] | Explorar |

---

## 3. Matriz Evento × Canal

| Evento | In-App | Email | WhatsApp | Push Web |
|--------|:------:|:-----:|:--------:|:--------:|
| `relatorio_pronto` | ✅ | ✅ | Free: ❌ Pro: ❌ Ent: ✅ | ✅ |
| `pesquisa_concluida` | ✅ | ❌ | ❌ | ❌ |
| `novo_concorrente_detectado` | ✅ | ✅ | Free: ❌ Pro: ❌ Ent: ✅ | ✅ |
| `sugestao_ia_nova` | ✅ | Free: ❌ Pro: ✅ Ent: ✅ | Free: ❌ Pro: ❌ Ent: ✅ | Free: ❌ Pro: ✅ |
| `tarefa_atrasada` | ✅ | Free: ❌ Pro: ✅ Ent: ✅ | Free: ❌ Pro: ❌ Ent: ✅ | Free: ❌ Pro: ✅ |
| `tarefa_bloqueada_resolvida` | ✅ | ❌ | ❌ | ❌ |
| `marco_se_aproxima` (7 dias) | ✅ | ❌ | ❌ | ❌ |
| `marco_se_aproxima` (1 dia) | ✅ | Free: ❌ Pro: ✅ Ent: ✅ | Free: ❌ Pro: ❌ Ent: ✅ | Free: ❌ Pro: ✅ |
| `marco_atrasado` | ✅ | ✅ | Free: ❌ Pro: ❌ Ent: ✅ | ✅ |
| `custo_desvio_alerta` | ✅ | Free: ❌ Pro: ✅ Ent: ✅ | Free: ❌ Pro: ❌ Ent: ✅ | Free: ❌ Pro: ✅ |
| `playbook_concluido` | ✅ | ✅ | Free: ❌ Pro: ❌ Ent: ✅ | ✅ |
| `sugestao_ia_playbook` | ✅ | Free: ❌ Pro: ✅ Ent: ✅ | ❌ | Free: ❌ Pro: ✅ |
| `limite_atedido` | ✅ | ❌ | ❌ | ❌ |
| `trial_expirando` | ✅ | ✅ | ❌ | ❌ |
| `pagamento_falhou` | ✅ | ✅ | ❌ | ✅ |

> **Legenda:** Free = tier Free, Pro = tier Pro, Ent = Enterprise.

---

## 4. Preferências do Usuário

### 4.1. Tabela `notificacao_preferencias`

```sql
CREATE TABLE notificacao_preferencias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),

    -- Canais ativos
    email_ativo BOOLEAN DEFAULT true,
    push_web_ativo BOOLEAN DEFAULT true,
    whatsapp_ativo BOOLEAN DEFAULT false,

    -- Email
    email_frequencia TEXT DEFAULT 'DIARIA'
        CHECK (email_frequencia IN ('IMEDIATA', 'DIARIA', 'SEMANAL', 'NUNCA')),

    -- Horário de silêncio (não notificar)
    silencio_inicio TIME DEFAULT '22:00',
    silencio_fim TIME DEFAULT '08:00',
    silencio_fuso TEXT DEFAULT 'America/Sao_Paulo',

    -- Eventos específicos (override do default)
    eventos_custom JSONB DEFAULT '{}',
    -- Exemplo: {"tarefa_atrasada": {"email": true, "push": true}, "sugestao_ia": {"email": false}}

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(user_id)
);
```

### 4.2. Configuração Padrão por Tier

| Configuração | Free | Pro | Enterprise |
|-------------|------|-----|------------|
| Email | Ativo, frequência DIARIA | Ativo, frequência IMEDIATA | Ativo, IMEDIATA |
| Push Web | Ativo | Ativo | Ativo |
| WhatsApp | ❌ (não disponível) | ❌ (não disponível) | Ativo (configurável) |
| Horário silêncio | 22h-08h | 22h-08h | Configurável |

### 4.3. Frequências

| Frequência | Comportamento |
|-----------|---------------|
| **IMEDIATA** | Envia notificação assim que o evento ocorre (dentro do horário de silêncio). |
| **DIARIA** | Acumula notificações do dia e envia resumo às 18h (ou primeiro login do dia). |
| **SEMANAL** | Resumo toda segunda-feira às 9h com tarefas atrasadas, marcos da semana, sugestões pendentes. |
| **NUNCA** | Só notifica in-app. Nada por email/push. |

---

## 5. Regras de Envio

### 5.1. Horário de Silêncio

- Se evento ocorre entre `silencio_inicio` e `silencio_fim`:
  - **Email:** agenda envio para `silencio_fim + 15min`.
  - **Push/WhatsApp:** segura até `silencio_fim`.
  - **In-app:** aparece imediatamente (usuário escolheu acessar).

### 5.2. Deduplicação

- Mesmo evento não pode gerar mais de 1 notificação por canal em 24h.
  - Ex: `tarefa_atrasada` para a mesma tarefa → 1 email/dia, não 1 por hora.
- Exceção: `novo_concorrente_detectado` → sempre notifica (evento raro e crítico).

### 5.3. Batch de Email Diário

Se usuário escolheu frequência DIARIA:

```
Assunto: Resumo do dia — GymSite

Bom dia, Marcelo! Aqui está o que aconteceu no seu projeto Cabo Branco:

🔴 2 tarefas atrasadas
   • Regularizar no Corpo de Bombeiros (3 dias atrasada)
   • Contratar projetista (1 dia atrasada)

🟡 1 marco se aproximando
   • Entrega da obra civil — faltam 5 dias

💡 1 sugestão da IA
   • Adicionar tarefa "Comprar extintores de incêndio"?

[Ver meu playbook]
```

### 5.4. WhatsApp Enterprise

Para Enterprise, notificações críticas via WhatsApp (evolution-api ou integração com parceiro):

```
GymSite 🏋️

Olá Marcelo,

⚠️ A tarefa "Regularizar no Corpo de Bombeiros" está atrasada há 3 dias.

Isso bloqueia 4 outras tarefas dependentes.

👉 Ver no playbook: https://gymsite.io/pb-001

Responder STOP para pausar notificações.
```

---

## 6. Arquitetura Técnica

### 6.1. Fluxo de Notificação

```
Evento ocorre (ex: tarefa atrasada)
    │
    ▼
[1] Gravar em notificacoes_fila (Supabase table ou Redis queue)
    │
    ▼
[2] Worker processa fila
    ├── Verifica preferências do usuário
    ├── Verifica horário de silêncio
    ├── Verifica deduplicação
    └── Decide canal(is)
    │
    ├──► In-App: INSERT em notificacoes_in_app
    ├──► Email: Chama serviço de email (async)
    ├──► Push: Chama Web Push API (async)
    └──► WhatsApp: Chama evolution-api (async)
```

### 6.2. Tabelas

```sql
-- Fila de notificações pendentes
CREATE TABLE notificacoes_fila (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    evento TEXT NOT NULL,
    payload JSONB NOT NULL,           -- dados do evento
    canais_solicitados TEXT[],        -- ['in_app', 'email']
    status TEXT DEFAULT 'PENDENTE',   -- PENDENTE | PROCESSANDO | ENVIADO | FALHOU
    agendado_para TIMESTAMPTZ,        -- se dentro de silêncio
    tentativas INT DEFAULT 0,
    erro TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Notificações entregues in-app
CREATE TABLE notificacoes_in_app (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    titulo TEXT NOT NULL,
    mensagem TEXT NOT NULL,
    tipo TEXT NOT NULL,               -- evento que gerou
    payload JSONB,                    -- link para recurso
    lida BOOLEAN DEFAULT false,
    clicked BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_notificacoes_in_app_user_unread ON notificacoes_in_app(user_id, lida) WHERE lida = false;
```

### 6.3. Serviço de Email

**Recomendado:** Resend (free tier: 3.000 emails/mês) ou Supabase Edge Function + AWS SES.

**Template base:**
- Header com logo GymSite
- Corpo em linguagem do domínio (nunca técnico)
- CTA claro (botão grande)
- Footer: "Você recebeu porque é usuário do GymSite. Ajustar preferências."

---

## 7. Decisões de Produto

| Código | Decisão | Justificativa |
|--------|---------|---------------|
| **NT-001** | WhatsApp só no Enterprise | Custo de API + complexidade. Empreendedor individual não precisa de urgência máxima. |
| **NT-002** | Free só recebe email em eventos críticos (relatório pronto, marco atrasado) | Incentiva upgrade sem ser agressivo. |
| **NT-003** | Push web sempre ativo (se usuário permitiu) | Gratuito de implementar. Alto engajamento. |
| **NT-004** | Resumo diário às 18h (ou primeiro login) | Não inunda caixa de entrada. Usuário lê quando tem tempo. |
| **NT-005** | In-app notification center persistente | Usuário sempre pode ver histórico, mesmo se perdeu email. |
| **NT-006** | Não notificar sobre "tarefa concluída" (só do próprio usuário) | Evita spam. Se sócio conclui, notifica responsáveis. |

---

## 8. Checklist de Implementação

- [ ] Tabelas `notificacao_preferencias`, `notificacoes_fila`, `notificacoes_in_app` criadas
- [ ] Worker de processamento de fila (Supabase Edge Function ou Celery/Redis)
- [ ] Serviço de email configurado (Resend ou SES)
- [ ] Web Push configurado (service worker no frontend)
- [ ] WhatsApp API configurado (evolution-api) — Fase 3
- [ ] Componente `NotificationCenter.tsx` no frontend (sininho com badge)
- [ ] Tela de preferências de notificação (`/configuracoes/notificacoes`)
- [ ] Templates de email criados (relatório pronto, resumo diário, tarefa atrasada)
- [ ] Testes: envio de cada tipo de notificação em cada canal
- [ ] Testes: horário de silêncio, deduplicação, batch diário
