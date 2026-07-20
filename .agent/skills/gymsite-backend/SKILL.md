---
name: gymsite-backend
description: Desenvolvimento backend Python para GymSite Intelligence. Use ao criar, modificar ou depurar endpoints FastAPI, schemas Pydantic, integrações Supabase, ou lógica de pipeline. NÃO use para frontend, CSS ou componentes React.
---

# GymSite Intelligence — Backend

## Contexto da Stack

- **Framework:** FastAPI (async, Pydantic v2)
- **Banco:** Supabase (PostgreSQL) via `supabase-py`
- **Autenticação:** JWT + Supabase Auth (RLS bypass via service_role)
- **Agentes:** Google ADK (Agent Development Kit) — runners em background
- **Variáveis:** `python-dotenv`, arquivos `.env` na raiz

## Estrutura de Endpoints

Todos os endpoints REST seguem o padrão `/api/{dominio}/{recurso}`:

```
/api/relatorios              → CRUD de relatórios
/api/prospeccao/oportunidades → Pipeline de prospecção
/api/prospeccao/executar      → Dispara engine em background
```

### Regras de Ouro

1. **Sempre use Pydantic models** para input/output — nunca dicts crus
2. **BackgroundTasks** para jobs longos (engine, ADK pipeline)
3. **Lazy imports** dentro de funções quando a lib pode estar ausente
4. **Handler de exceção global** — use `HTTPException` do FastAPI, nunca `raise` genérico
5. **Supabase client** via `_supabase_client()` helper (reutiliza conexão)

## Padrões de Código

### Modelo Pydantic

```python
from pydantic import BaseModel, Field

class ProspeccaoStatusPatch(BaseModel):
    status: str = Field(..., pattern=r"^(novo|qualificado|webhook_enviado|engajado|fechado|descartado)$")
```

### Endpoint FastAPI

```python
@app.patch("/api/prospeccao/oportunidades/{id}/status")
def patch_status(id: str, payload: ProspeccaoStatusPatch) -> dict:
    from prospecting.engine import update_status
    ok = update_status(id, payload.status)
    if not ok:
        raise HTTPException(status_code=404, detail="Oportunidade não encontrada")
    return {"status": "updated", "id": id}
```

### Supabase Query

```python
def _supabase_client():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

client = _supabase_client()
result = client.table("oportunidades_prospeccao") \
    .select("*") \
    .eq("status", "novo") \
    .order("score_match", desc=True) \
    .limit(20) \
    .execute()
```

## Diretórios Chave

| Diretório | Função |
|---|---|
| `api.py` | FastAPI app principal — registra todos os endpoints |
| `models/schemas.py` | Schemas Pydantic compartilhados |
| `db/` | Migrations SQL + writers |
| `prospecting/` | Engine de prospecção CNPJ×CNO |
| `agents/` | Agentes Google ADK (A0–A9) |
| `tools/` | Utilitários (maps, CNPJ, CNO, scraping) |

## Anti-padrões

- ❌ Não use `print()` em produção — use `logging.getLogger("gymsite.nome_modulo")`
- ❌ Não carregue Google ADK no import global — lazy import dentro da função
- ❌ Não exponha `SUPABASE_SERVICE_ROLE_KEY` no frontend ou em logs
- ❌ Não rode queries Supabase sem `.execute()` — é síncrono

## Segurança

- Sempre valide inputs com Pydantic (SQL injection prevention)
- Use `Field(..., pattern=r"...")` para enums (status, prioridade)
- Rate-limit em endpoints pesados (distance_matrix, scraping)
- Nunca execute `eval()` ou `exec()` em dados de usuário
