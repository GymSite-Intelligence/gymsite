---
name: gymsite-prospecting
description: Módulo de prospecção CNPJ × CNO, pipeline de vendas e webhooks para GymSite Intelligence. Use ao trabalhar com oportunidades de prospecção, status do funil, webhooks para Claw, ou enriquecimento de leads. NÃO use para relatórios PDF ou análise demográfica.
---

# GymSite Intelligence — Prospecção CNPJ × CNO

## Visão Geral

O módulo de prospecção cruza **CNPJs fitness entrantes** (≤90 dias) com **obras CNO** na mesma cidade, gerando oportunidades qualificadas com pipeline de vendas e webhook para CRM.

```mermaid
flowchart LR
    A[CNPJ Fitness<br/>entrantes ≤90d] --> B[Engine de Cruzamento]
    C[CNO / Obras<br/>em_curso|encerrada] --> B
    B --> D[Score de Match<br/>0.0 – 1.0]
    D --> E[Oportunidade<br/>status = 'novo']
    E --> F[SDR Qualifica]
    F --> G[Webhook → Claw]
    G --> H[CRM Engaja]
    H --> I[Status = 'fechado']
```

## Pipeline de Status

| Status | Significado | Quem muda |
|---|---|---|
| `novo` | Criado pelo engine | Sistema |
| `qualificado` | SDR validou fit | Operador |
| `webhook_enviado` | Disparado para Claw | Operador / Sistema |
| `engajado` | Lead respondeu | Claw / Operador |
| `fechado` | Contrato assinado | Operador |
| `descartado` | Não é oportunidade | Operador |

## Webhook para Claw

### Payload

```json
{
  "event": "oportunidade.webhook_enviado",
  "oportunidade": {
    "id": "uuid",
    "cnpj": "12.345.678/0001-99",
    "razao_social": "ACADEMIA FORTE LTDA",
    "cidade": "Fortaleza",
    "uf": "CE",
    "score_match": 0.87,
    "status": "webhook_enviado",
    "contato_cnpj": {
      "decision_maker": "João Silva",
      "cargo": "Sócio-administrador",
      "email": "joao@academiaforte.com.br",
      "whatsapp_link": "https://wa.me/5585999999999"
    }
  }
}
```

### Retry Automático

- Máximo 3 tentativas
- Backoff exponencial: 5s, 15s, 45s
- Log em `webhook_claw_log` com status HTTP e resposta

## API Endpoints

```python
POST   /api/prospeccao/executar              → Dispara engine em background
GET    /api/prospeccao/oportunidades         → Lista com filtros + paginação
GET    /api/prospeccao/oportunidades/{id}    → Detalhe
POST   /api/prospeccao/oportunidades/{id}/webhook → Reenvia webhook
PATCH  /api/prospeccao/oportunidades/{id}/status  → Atualiza status
POST   /api/prospeccao/webhook/configure     → Configura URL por org
```

## Frontend — Componentes

```
ProspeccaoPage.tsx
├── Filtros (Cidade, UF, Status, Prioridade, Score)
├── Cards de Resumo (Total, Novo, Qualificado, Webhook, Engajado, Fechado)
├── Tabela Ordenável (Score, Prioridade, Entrada)
├── Paginação (20 itens/página)
├── Botão Exportar CSV
└── OportunidadeDrawer.tsx
    ├── Badges (Status, Prioridade)
    ├── Dados (CNPJ, CNO, Cidade, Área)
    ├── Contato (Email, WhatsApp, LinkedIn)
    ├── Pipeline (Select de status)
    └── Webhook (Reenviar)
```

## Regras de Ouro

1. **Mudança de status invalida cache** — `queryClient.invalidateQueries({ queryKey: ['prospeccao'] })`
2. **Export CSV usa dados ordenados** — reflete filtros atuais
3. **Webhook só dispara se URL configurada** — verifique `webhook_url` no registro
4. **Paginação reseta ao filtrar** — `setPage(0)` em toda mudança de filtro

## Anti-padrões

- ❌ Não dispare webhook para status != `qualificado` ou `webhook_enviado`
- ❌ Não exclua oportunidades — use `descartado` para manter histórico
- ❌ Não ignore falhas de webhook — monitore `webhook_claw_log`
- ❌ Não use `alert()` para feedback — use toast do Sonner

## Métricas de Negócio

| Métrica | Fórmula | Onde ver |
|---|---|---|
| Taxa de qualificação | Qualificados / Total | Cards de resumo |
| Taxa de conversão | Fechados / Total | Exportar CSV |
| Score médio | AVG(score_match) | Query Supabase |
| Tempo no pipeline | AVG(updated_at - created_at) | Query Supabase |
| Taxa de webhook | Sucessos / Tentativas | `webhook_claw_log` |
