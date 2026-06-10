# Limites Técnicos por Tier

> Definição de limites de uso, middleware de controle e comportamento do frontend quando o usuário atinge o limite do plano.

---

## 1. Matriz de Limites

| Recurso | Free | Pro | Enterprise | Justificativa |
|---------|------|-----|------------|---------------|
| **Projetos ativos** | 1 | Ilimitado | Ilimitado | Free serve para experimentar. Pro/Enterprise para operar. |
| **Projetos arquivados/histórico** | 0 | 50 | Ilimitado | Free não guarda histórico. Pro guarda 1 ano de projetos. |
| **Tarefas por playbook** | 10 | Ilimitado | Ilimitado | 10 tarefas cobre ~30% de um playbook médio. suficiente para "sentir" o produto. |
| **Checklist itens por tarefa** | 3 | Ilimitado | Ilimitado | Limita granularidade no Free. |
| **OKRs por playbook** | 1 | 5 | Ilimitado | Free foca em 1 objetivo principal. Pro permite OKRs por área. |
| **Timeline eventos** | 3 | 30 | Ilimitado | Free vê marcos principais. Pro planeja detalhadamente. |
| **Sugestões IA por mês** | 0 | 20 | Ilimitado | Diferenciador principal do Pro. Free não tem IA proativa. |
| **Anexos por projeto** | 2 | 20 | Ilimitado | Free anexa PDF básico. Pro anexa projeto completo. |
| **Tamanho máximo por anexo** | 5MB | 25MB | 100MB | Free: foto/PDF simples. Pro: projeto arquitetônico. |
| **Storage total** | 10MB | 500MB | 10GB | Acumulado por usuário. |
| **Pesquisas de mercado/mês** | 3 | 20 | Ilimitado | Free valida 1-2 bairros. Pro pesquisa várias opções. |
| **Relatórios formais/mês** | 1 | 10 | Ilimitado | Free gera 1 relatório. Pro gera para múltiplos cenários. |
| **Compartilhamento (convidados)** | 0 | 3 por projeto | Ilimitado | Free é uso individual. Pro permite sócios. |
| **Permissões avançadas (RBAC)** | ❌ | ❌ | ✅ | Enterprise tem controle granular de acesso. |
| **API access** | ❌ | ❌ | ✅ | Enterprise integra com ERP/franquia. |
| **White-label (logo da rede)** | ❌ | ❌ | ✅ | Enterprise personaliza relatórios e playbook. |
| **Exportação PDF do relatório** | ❌ | ✅ | ✅ | Free vê online. Pro exporta. |
| **Dashboards analíticos** | ❌ | ✅ | ✅ | Free não tem dashboards. Pro acompanha KPIs. |
| **Notificações por email** | ❌ | ✅ | ✅ | Free só notifica in-app. Pro alerta por email. |
| **Notificações por WhatsApp** | ❌ | ❌ | ✅ | Enterprise tem canal direto com gestor. |
| **Suporte** | Comunidade | Email (48h) | Prioritário (4h) + onboarding | |
| **Preço** | R$ 0 | R$ 99/mês | R$ 499/mês | |

---

## 2. Comportamento ao Atingir Limite

### 2.1. Free atinge limite

| Limite Atingido | Mensagem ao Usuário | CTA |
|-----------------|---------------------|-----|
| 1 projeto ativo | "Você já tem 1 projeto em andamento. Conclua ou arquive para criar outro, ou atualize para Pro." | "Ver planos Pro" |
| 10 tarefas no playbook | "Seu playbook está completo! Libere tarefas ilimitadas e mais recursos com o plano Pro." | "Fazer upgrade" |
| 3 pesquisas/mês | "Você usou suas 3 pesquisas deste mês. Novas pesquisas disponíveis em [data], ou atualize para Pro." | "Ver planos" |
| 1 relatório gerado | "Relatório gerado com sucesso! Crie projetos e relatórios ilimitados com Pro." | "Fazer upgrade" |
| Tenta convidar alguém | "Colaboração em equipe é um recurso do plano Pro. Convide sócios e prestadores." | "Ver planos Pro" |
| Tenta anexar 3º arquivo | "Limite de 2 anexos atingido. Libere mais espaço com o plano Pro." | "Fazer upgrade" |

> **Regra de UX:** Nunca bloquear abruptamente. Sempre mostrar o que o usuário já conquistou ("Você criou 10 tarefas!") antes de pedir upgrade.

### 2.2. Pro atinge limite (raro, mas possível)

| Limite Atingido | Mensagem | CTA |
|-----------------|----------|-----|
| 20 sugestões IA/mês | "Você usou todas as sugestões inteligentes deste mês. Novas sugestões em [data]. Precisa de mais? Fale com a gente." | "Falar com vendas" (Enterprise) |
| 500MB storage | "Seu espaço de armazenamento está quase cheio. Gerencie seus anexos ou atualize para Enterprise." | "Gerenciar anexos" / "Falar com vendas" |

---

## 3. Middleware de Controle (Backend)

### 3.1. Estrutura do Middleware

```python
# services/execucao/limites_service.py

from enum import Enum

class PlanoTier(str, Enum):
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"

LIMITES = {
    PlanoTier.FREE: {
        "projetos_ativos_max": 1,
        "projetos_arquivados_max": 0,
        "tarefas_por_playbook_max": 10,
        "checklist_itens_max": 3,
        "okrs_max": 1,
        "timeline_eventos_max": 3,
        "sugestoes_ia_mes": 0,
        "anexos_por_projeto_max": 2,
        "anexo_tamanho_max_mb": 5,
        "storage_total_mb": 10,
        "pesquisas_mes": 3,
        "relatorios_mes": 1,
        "convidados_por_projeto_max": 0,
        "permissoes_avancadas": False,
        "api_access": False,
        "white_label": False,
        "export_pdf": False,
        "dashboards": False,
        "notificacoes_email": False,
        "notificacoes_whatsapp": False,
    },
    PlanoTier.PRO: {
        "projetos_ativos_max": None,  # ilimitado
        "projetos_arquivados_max": 50,
        "tarefas_por_playbook_max": None,
        "checklist_itens_max": None,
        "okrs_max": 5,
        "timeline_eventos_max": 30,
        "sugestoes_ia_mes": 20,
        "anexos_por_projeto_max": 20,
        "anexo_tamanho_max_mb": 25,
        "storage_total_mb": 500,
        "pesquisas_mes": 20,
        "relatorios_mes": 10,
        "convidados_por_projeto_max": 3,
        "permissoes_avancadas": False,
        "api_access": False,
        "white_label": False,
        "export_pdf": True,
        "dashboards": True,
        "notificacoes_email": True,
        "notificacoes_whatsapp": False,
    },
    PlanoTier.ENTERPRISE: {
        "projetos_ativos_max": None,
        "projetos_arquivados_max": None,
        "tarefas_por_playbook_max": None,
        "checklist_itens_max": None,
        "okrs_max": None,
        "timeline_eventos_max": None,
        "sugestoes_ia_mes": None,
        "anexos_por_projeto_max": None,
        "anexo_tamanho_max_mb": 100,
        "storage_total_mb": 10_000,
        "pesquisas_mes": None,
        "relatorios_mes": None,
        "convidados_por_projeto_max": None,
        "permissoes_avancadas": True,
        "api_access": True,
        "white_label": True,
        "export_pdf": True,
        "dashboards": True,
        "notificacoes_email": True,
        "notificacoes_whatsapp": True,
    }
}

async def verificar_limite(
    user_id: str,
    recurso: str,
    valor_atual: int,
    db
) -> dict:
    """
    Retorna: {"permitido": bool, "limite": int|None, "restante": int|None, "mensagem": str}
    """
    # Buscar tier do usuário
    # Comparar valor_atual com limite
    # Retornar resultado
```

### 3.2. Pontos de Verificação nos Endpoints

| Endpoint | Limite Verificado | Quando Bloqueia |
|----------|-------------------|-----------------|
| `POST /api/consultor/conversar` | `pesquisas_mes` | Se pesquisas do mês >= limite |
| `POST /api/execucao/playbooks` | `projetos_ativos_max` | Se projetos ativos >= limite |
| `POST /api/execucao/playbooks/{id}/gerar` | `relatorios_mes` | Se relatórios do mês >= limite |
| `POST /api/execucao/tarefas` | `tarefas_por_playbook_max` | Se tarefas do playbook >= limite |
| `POST /api/execucao/tarefa-checklist` | `checklist_itens_max` | Se itens da tarefa >= limite |
| `POST /api/execucao/okrs` | `okrs_max` | Se OKRs do playbook >= limite |
| `POST /api/execucao/timeline-eventos` | `timeline_eventos_max` | Se eventos >= limite |
| `POST /api/consultor/anexos` | `anexos_por_projeto_max`, `storage_total_mb`, `anexo_tamanho_max_mb` | Se qualquer limite atingido |
| `POST /api/execucao/sugestoes/{id}/aceitar` | `sugestoes_ia_mes` | Se sugestões do mês >= limite |
| `POST /api/execucao/playbooks/{id}/convidar` | `convidados_por_projeto_max` | Se convidados >= limite |
| `GET /api/execucao/playbooks/{id}/pdf` | `export_pdf` | Se tier não tem permissão |
| `GET /api/execucao/dashboards/{id}` | `dashboards` | Se tier não tem permissão |

### 3.3. Response Padrão de Limite Atingido

```json
{
  "error": "LIMITE_ATINGIDO",
  "recurso": "tarefas_por_playbook",
  "limite": 10,
  "usado": 10,
  "mensagem": "Seu playbook está completo! Libere tarefas ilimitadas com o plano Pro.",
  "cta": {
    "texto": "Fazer upgrade para Pro",
    "link": "/planos"
  },
  "tier_atual": "FREE",
  "tier_sugerido": "PRO"
}
```

**HTTP Status:** `402 Payment Required` (ou `403 Forbidden` se preferir não usar 402).

---

## 4. Estrutura de Dados para Limites

### 4.1. Tabela `user_subscriptions`

```sql
CREATE TABLE user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    org_id UUID REFERENCES orgs(id),

    tier TEXT NOT NULL DEFAULT 'FREE'
        CHECK (tier IN ('FREE', 'PRO', 'ENTERPRISE')),

    -- Período de faturamento
    status TEXT NOT NULL DEFAULT 'ATIVO'
        CHECK (status IN ('ATIVO', 'CANCELADO', 'SUSPENSO', 'TRIAL')),
    trial_ate TIMESTAMPTZ,

    -- Gateway de pagamento
    gateway_customer_id TEXT,
    gateway_subscription_id TEXT,

    -- Limites customizados (Enterprise pode ter limites negociados)
    limites_custom JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    cancelado_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_user_subscriptions_user ON user_subscriptions(user_id);
```

### 4.2. Tabela `uso_mensal` (contadores para reset mensal)

```sql
CREATE TABLE uso_mensal (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    ano_mes TEXT NOT NULL,  -- formato: "2026-06"

    -- Contadores
    pesquisas_feitas INT DEFAULT 0,
    relatorios_gerados INT DEFAULT 0,
    sugestoes_ia_aceitas INT DEFAULT 0,
    anexos_uploadados INT DEFAULT 0,
    storage_usado_mb DECIMAL(10,2) DEFAULT 0,

    UNIQUE(user_id, ano_mes)
);
```

> **Regra:** Todo dia 1, contadores zeram. Job simples (Supabase Cron ou Cloudflare Cron).

---

## 5. Frontend — Tela de Planos e Upgrade

### 5.1. Componentes

```
frontend/src/
 components/
    planos/
       PlanosPage.tsx              # Pública ou autenticada. Compara 3 tiers.
       PlanoCard.tsx               # Card de cada tier com lista de recursos.
       PlanoBadge.tsx              # Badge "Seu plano atual" / "Recomendado".
       UpgradeModal.tsx            # Modal quando limite é atingido.
 hooks/
    useSubscription.ts            # Busca tier atual e limites.
    useLimites.ts                 # Verifica se usuário pode usar recurso X.
```

### 5.2. Comportamento do `useLimites`

```typescript
// Antes de qualquer ação, verifica limite
const { podeUsar, restante, mensagem } = useLimite("tarefas_por_playbook", playbookId);

if (!podeUsar) {
  openUpgradeModal(mensagem);
  return;
}
```

### 5.3. Tela de Planos (Design)

| | Free | Pro (Recomendado) | Enterprise |
|---|:---:|:---:|:---:|
| Preço | R$ 0 | **R$ 99/mês** | R$ 499/mês |
| CTA | "Seu plano atual" | "Fazer upgrade" | "Falar com vendas" |
| Projetos | 1 ativo | Ilimitado | Ilimitado |
| Tarefas | 10 | Ilimitado | Ilimitado |
| Sugestões IA | ❌ | 20/mês | Ilimitado |
| Dashboards | ❌ | ✅ | ✅ |
| PDF Export | ❌ | ✅ | ✅ |
| Convites | ❌ | 3 | Ilimitado |
| API | ❌ | ❌ | ✅ |
| White-label | ❌ | ❌ | ✅ |
| Suporte | Comunidade | Email 48h | Prioritário 4h |

> Destacar Pro com cor primária (recomendado). Enterprise com estilo mais discreto (B2B).

---

## 6. Decisões de Implementação

| Código | Decisão | Justificativa |
|--------|---------|---------------|
| **LT-001** | Limites resetam no dia 1 de cada mês (UTC-3) | Simples de entender. Evita surpresa no meio do mês. |
| **LT-002** | Free pode DELETAR projeto para liberar vaga | Empreendedor não fica preso se errar cidade. |
| **LT-003** | Pro pode downgradar para Free, mas projetos excedentes são arquivados (não apagados) | Regra de soft delete. Usuário pode resgatar com upgrade. |
| **LT-004** | Enterprise limites são "ilimitado" com fair-use (10.000 pesquisas/mês, 100GB storage) | Evita abuso. Limite invisível para 99% dos casos. |
| **LT-005** | Contadores de uso são atualizados síncronos (na mesma transação da ação) | Garante consistência. Não pode haver race condition. |

---

## 7. Checklist de Implementação

- [ ] Tabela `user_subscriptions` criada
- [ ] Tabela `uso_mensal` criada
- [ ] `LIMITES` dict definido em código
- [ ] `verificar_limite()` implementado e testado
- [ ] Middleware aplicado em todos os endpoints relevantes
- [ ] Response 402/403 padronizado
- [ ] `useSubscription` e `useLimites` no frontend
- [ ] `PlanosPage` criada
- [ ] `UpgradeModal` criada e integrada
- [ ] Job de reset mensal configurado
- [ ] Testes: Free atinge limite em cada recurso
