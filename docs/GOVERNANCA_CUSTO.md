# Governança de Otimização de Custo — GymSite Intelligence

> Processo formal de análise, proposta, aprovação e implementação de otimizações de custo no pipeline ADK.

---

## 1. Visão Geral

O endpoint `/api/custos/optimizations` analisa o `tokens_pipeline.csv` e detecta oportunidades de economia. No entanto, **nenhuma otimização é aplicada automaticamente** — cada proposta passa por um workflow de aprovação antes da implementação.

### Objetivos
- Transparência: todo mundo vê o que foi detectado, quanto economiza e o status
- Controle: apenas owners/admins aprovam mudanças que afetam o pipeline
- Rastreabilidade: sabemos quem aprovou, quando e qual foi o resultado real

---

## 2. Fluxo do Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  DETECTADA  │ ──► │   PENDENTE  │ ──► │  APROVADA   │ ──► │ IMPLEMENTADA│
│   (auto)    │     │  (proposta) │     │  (decisão)  │     │  (execução) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  REJEITADA  │
                    │  (arquivada)│
                    └─────────────┘
```

### Estados

| Estado | Quem move | Descrição |
|---|---|---|
| **Detectada** | Sistema | Sugestão gerada pelo algoritmo de análise. Não está no banco. |
| **Pendente** | Usuário (owner/admin) | Proposta criada a partir de uma detecção. Aguardando decisão. |
| **Aprovada** | Owner/Admin | Decisão positiva. Pode incluir justificativa. |
| **Implementada** | Owner/Admin | Mudança aplicada no código/config. Deve incluir observação de resultado. |
| **Rejeitada** | Owner/Admin | Decisão negativa. Deve incluir justificativa. |
| **Cancelada** | Owner/Admin | Proposta retirada antes da decisão. |

---

## 3. Tipos de Otimização Detectadas

| Tipo | Descrição | Exemplo |
|---|---|---|
| `MODELO_OVERPRICED` | Agente usando Pro onde Flash/Lite seria suficiente | A3b usando `gemini-3.6-flash` → trocar por `flash` |
| `FLASH_PARA_LITE` | Agente usando Flash onde Lite seria suficiente | A5 usando `flash` → trocar por `flash-lite` |
| `AGENTE_VORAZ` | Agente consumindo >30% do custo total | A6 consome 40% do custo → aplicar Context Caching |
| `ERRO_REPETIDO` | Alta taxa de finish_reason != STOP | A1 com 20% de `MALFORMED_FUNCTION_CALL` → revisar prompt |
| `CACHE_GEOCODING` | Chamadas repetidas de geocoding | A1 chamando mesma cidade 50x → ativar cache |
| `OUTRO` | Qualquer outra sugestão manual | — |

---

## 4. Tabela no Banco

```sql
otimizacoes_custo (
  id uuid primary key,
  org_id uuid not null,
  criado_por uuid,
  criado_em timestamptz,
  tipo otimizacao_tipo,
  agente text,
  modelo_atual text,
  modelo_sugerido text,
  titulo text,
  descricao text,
  economia_brl_estimada numeric(10,4),
  severidade text,  -- alta | media | baixa
  status otimizacao_status,  -- pendente | aprovada | implementada | rejeitada | cancelada
  aprovado_por uuid,
  aprovado_em timestamptz,
  justificativa_aprovacao text,
  implementado_por uuid,
  implementado_em timestamptz,
  resultado_observacao text,
  economia_brl_real numeric(10,4),
  referencia_dados jsonb
)
```

### RLS
- Usuários só veem propostas da sua org
- Service role (backend) pode inserir sem restrição

---

## 5. Endpoints da API

### Listar propostas
```
GET /api/custos/propostas?status=pendente
Authorization: Bearer <token>
```

### Criar proposta
```
POST /api/custos/propostas
Authorization: Bearer <token>
Content-Type: application/json

{
  "tipo": "AGENTE_VORAZ",
  "agente": "ReportConsolidator",
  "modelo_atual": "gemini-3.6-flash",
  "modelo_sugerido": "",
  "titulo": "AGENTE_VORAZ: ReportConsolidator",
  "descricao": "Consome 40.4% do custo total...",
  "economia_brl_estimada": 12.55,
  "severidade": "media",
  "referencia_dados": { "periodo_dias": 30, "total_custo": 155.16 }
}
```

### Atualizar status (aprovar/rejeitar/implementar)
```
PATCH /api/custos/propostas/{id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "aprovada",
  "justificativa": "Context Caching reduz input estático em 89%"
}
```

---

## 6. Interface no Frontend

Acessível em: **CustosPage** (`/custos`) — seção "Governança de Otimização de Custo"

### Abas
1. **Detectadas** — sugestões do algoritmo. Botão "Criar Proposta" converte em pendente.
2. **Pendentes** — aguardando decisão. Botões: Aprovar / Rejeitar.
3. **Aprovadas** — prontas para implementação. Botão: Marcar Implementada.
4. **Implementadas** — histórico com resultado real.
5. **Rejeitadas** — arquivadas com justificativa.

### Permissões
- Apenas `isOwnerOrAdmin` vê a seção
- Qualquer membro da org pode ver propostas (via RLS)
- Apenas owners podem criar/aprovar/rejeitar

---

## 7. Exemplo de Ciclo Completo

### Cenário: Context Caching no A6

**1. Detecção automática**
```
Tipo: AGENTE_VORAZ
Agente: ReportConsolidator
Economia estimada: R$ 4.20/relatório
Severidade: media
```

**2. Criar proposta**
- Admin clica "Criar Proposta" na aba Detectadas
- Sistema insere na tabela com status `pendente`

**3. Análise e aprovação**
- Owner revisa: "O instruction do A6 tem ~6.7K tokens, reenviado 98x. Cache hit é 10x mais barato."
- Clica "Aprovar" com justificativa: "Reduz input estático de R$ 4,71 para R$ 0,51 por relatório."

**4. Implementação**
- Dev aplica Context Caching no `GenerateContentConfig` do A6
- Admin marca como `implementada` com observação: "Cache ativado, TTL 1h."

**5. Validação**
- Após 1 semana, compara custo real: R$ 58,50 (antes R$ 62,75)
- Economia real: R$ 4,25/relatório (próxima da estimativa)
- Atualiza `economia_brl_real`

---

## 8. Checklist de Implementação

- [x] Tabela `otimizacoes_custo` no schema.sql
- [x] Enum `otimizacao_status` e `otimizacao_tipo`
- [x] Endpoints CRUD: GET, POST, PATCH `/api/custos/propostas`
- [x] Hooks React Query: `usePropostasOtimizacao`, `useCriarPropostaOtimizacao`, `useAtualizarPropostaOtimizacao`
- [x] Componente `PropostasWorkflow` no CustosPage
- [x] RLS habilitado na tabela
- [ ] Aplicar migration no Supabase (`psql $DATABASE_URL -f db/schema.sql`)
- [ ] Testar E2E: detectar → criar → aprovar → implementar

---

## 9. Próximas Evoluções

1. **Notificação**: Email/Slack quando uma proposta é criada ou aprovada
2. **ROI acumulado**: Dashboard mostrando economia total já implementada vs. estimada
3. **Auto-criação**: Backend cria propostas automaticamente quando economia > R$ 10/mês
4. **Comparativo**: Antes/Depois de cada otimização com gráfico de custo
