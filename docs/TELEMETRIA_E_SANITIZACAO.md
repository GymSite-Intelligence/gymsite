# Telemetria de Tokens & Sanitização

> **Escopo:** Como o GymSite Intelligence mede consumo de LLM (tokens) e protege dados sensíveis (LGPD) na telemetria.

---

## 1. Telemetria de Tokens — Conceito

### Por que medir tokens?

Cada agente do pipeline A0→A6 chama o Gemini. O custo da API Google é proporcional ao número de tokens (input + output). Sem telemetria:
- Não sabemos qual agente é o mais caro
- Não conseguimos estimar custo por relatório
- Não detectamos anomalias (ex: A3 loop infinito com `finish_reason=MAX_TOKENS`)

### O que é um "token"?

| Tipo | Definição | Exemplo |
|---|---|---|
| **Input (prompt)** | Tokens enviados para o LLM | Instruction + contexto de mercado + tool results |
| **Output (completion)** | Tokens gerados pelo LLM | Resposta em JSON, texto, function call |
| **Total** | Soma input + output | Usado para billing e quota |

### Arquitetura da Telemetria

```
┌─────────────────┐     after_model_callback      ┌─────────────────┐
│   Agente ADK    │ ─────────────────────────────→│ token_telemetry │
│   (A0 → A6)     │    (llm_response + context)   │   (Python)      │
└─────────────────┘                               └─────────────────┘
                                                          │
                                                          ▼
                                               ┌─────────────────┐
                                               │ tokens_pipeline │
                                               │     .csv        │
                                               └─────────────────┘
                                                          │
                                                          ▼
                                               ┌─────────────────┐
                                               │  OpenTelemetry  │
                                               │   (span attrs)  │
                                               └─────────────────┘
```

### Dados Coletados (`metrics/tokens_pipeline.csv`)

| Coluna | Significado |
|---|---|
| `run_id` | ID da execução do pipeline (12 chars hex) |
| `timestamp` | ISO-8601 da chamada LLM |
| `agent_name` | Nome do agente (ContextBuilder, GeoScout, etc.) |
| `tokens_in` | Tokens de prompt |
| `tokens_out` | Tokens de resposta |
| `tokens_total` | Soma (fallback: in + out se API não retornar total) |
| `model` | Modelo usado (gemini-2.5-flash, gemini-2.5-pro) |
| `fonte_usage` | De onde veio o usage_metadata (debug de captura) |
| `finish_reason` | STOP / MAX_TOKENS / MALFORMED_FUNCTION_CALL / SAFETY |

### Por que `after_model_callback` e não `after_agent_callback`?

```
Agente A3 pode fazer:
  LLM call 1 → tool call (buscar concorrentes)
  LLM call 2 → tool call (analisar reviews)
  LLM call 3 → resposta final

after_agent_callback:  1 registro por agente (perde calls 1 e 2)
after_model_callback:  3 registros (cada LLM call separada) ← correto
```

---

## 2. Sanitização — Conceito

### O que é sanitização?

**Sanitização** = remover, mascarar ou transformar dados sensíveis antes de gravar em logs, traces ou métricas.

### Por que sanitizar?

1. **LGPD (Lei 13.709/2018)** — CNPJ, endereço, telefone, email são dados pessoais/empresariais
2. **Segurança** — Chaves de API, tokens de autenticação, secrets
3. **Compliance** — Se um trace OTel vazar para Grafana Cloud, não pode levar PII
4. **Custo** — Dados sanitizados = menos bytes = spans mais leves

### O que sanitizar na telemetria do GymSite?

| Dado | Risco | Como sanitizar |
|---|---|---|
| **CNPJ completo** | LGPD — identifica empresa | `12.***.***/0001-99` (mascarar 4 primeiros dígitos) |
| **Endereço** | LGPD — localização precisa | Remover número; manter bairro + cidade |
| **Telefone/WhatsApp** | LGPD — contato direto | `+55 ** *****-9999` (últimos 4 dígitos) |
| **Email** | LGPD — contato direto | `jo***@academia.com.br` (2 primeiros chars + domínio) |
| **Chaves de API** | Segurança — vazamento de credenciais | Remover completamente; substituir por `[REDACTED]` |
| **Nome fantasia** | LGPD — identificação indireta | Manter; não é pessoal natural |
| **Razão social** | LGPD — identificação empresarial | Manter; é dado público (RFB) |
| **Score / Tokens** | Sem risco | Não sanitizar |

### Regra de Ouro

> **"Se o dado não for essencial para debug/métrica, não grave. Se for sensível, mascare."**

---

## 3. Implementação — Sanitização no Código

### 3.1 Sanitização de CNPJ (reutilizável)

```python
# tools/sanitize.py
import re


def mask_cnpj(cnpj: str | None) -> str | None:
    """Mascara CNPJ: 12.345.678/0001-99 → 12.***.***/0001-99"""
    if not cnpj:
        return None
    digits = re.sub(r"\D", "", cnpj)
    if len(digits) != 14:
        return cnpj  # fallback: retorna original se inválido
    return f"{digits[:2]}.***.***/{digits[8:12]}-{digits[12:]}"


def mask_phone(phone: str | None) -> str | None:
    """Mascara telefone: +5585999999999 → +55 ** *****-9999"""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 8:
        return phone
    return f"+{digits[:2]} ** *****-{digits[-4:]}"


def mask_email(email: str | None) -> str | None:
    """Mascara email: joao@academia.com.br → jo***@academia.com.br"""
    if not email or "@" not in email:
        return email
    user, domain = email.split("@", 1)
    visible = user[:2] if len(user) >= 2 else user[:1]
    return f"{visible}***@{domain}"


def redact(value: str | None, label: str = "REDACTED") -> str | None:
    """Remove completamente um valor sensível."""
    return None if value else None


def sanitize_dict(data: dict, rules: dict[str, callable]) -> dict:
    """
    Aplica regras de sanitização em um dict.

    rules = {"cnpj": mask_cnpj, "telefone": mask_phone, "api_key": redact}
    """
    out = dict(data)
    for key, fn in rules.items():
        if key in out:
            out[key] = fn(out[key])
    return out
```

### 3.2 Sanitização nos Spans OpenTelemetry

```python
# tools/agent_telemetry.py (atualizado)
from tools.sanitize import mask_cnpj, mask_phone, mask_email

# Chaves do state que podem conter PII
_SENSITIVE_KEYS = {"cnpj", "telefone", "whatsapp", "email", "contato_cnpj"}


def _sanitize_state(state: dict) -> dict:
    """Retorna cópia do state com dados sensíveis mascarados."""
    safe = {}
    for k, v in state.items():
        if k in ("cnpj",):
            safe[k] = mask_cnpj(v) if isinstance(v, str) else v
        elif k in ("telefone", "whatsapp"):
            safe[k] = mask_phone(v) if isinstance(v, str) else v
        elif k == "email":
            safe[k] = mask_email(v) if isinstance(v, str) else v
        elif k == "contato_cnpj" and isinstance(v, dict):
            safe[k] = {
                kk: (mask_phone(vv) if "whatsapp" in kk else
                     mask_email(vv) if "email" in kk else vv)
                for kk, vv in v.items()
            }
        else:
            safe[k] = v
    return safe
```

### 3.3 Sanitização no Webhook Payload

```python
# prospecting/webhook.py — já sanitiza antes de enviar
payload = _montar_payload(oportunidade)
# payload["data"]["cnpj"] já pode ser mascarado se necessário
```

### 3.4 Sanitização nos Logs de API

```python
# api.py — evitar logar headers de autorização
import logging

logger = logging.getLogger("gymsite.api")

# ❌ Ruim
logger.info(f"Headers: {request.headers}")  # pode conter Authorization

# ✅ Bom
safe_headers = {k: v for k, v in request.headers.items()
                if k.lower() not in ("authorization", "x-claw-secret")}
logger.info(f"Headers: {safe_headers}")
```

---

## 4. Checklist de Sanitização

Antes de deployar com telemetria ativa:

- [ ] Nenhum CNPJ completo em spans OTel, logs CSV, ou webhook payload
- [ ] Nenhuma chave de API em spans (GOOGLE_API_KEY, SUPABASE_SERVICE_ROLE_KEY)
- [ ] Telefones mascarados (últimos 4 dígitos visíveis apenas)
- [ ] Emails mascarados (2 primeiros chars + domínio)
- [ ] Endereços sem número de porta/predio
- [ ] Tokens de autenticação redacted em headers de trace
- [ ] Arquivos CSV de token telemetry protegidos (não commitados, .gitignore)
- [ ] Retenção de dados definida (ex: apagar CSVs com > 90 dias)

---

## 5. Dashboard de Tokens (Frontend)

Sugestão de página `/telemetria` no frontend:

```
┌─────────────────────────────────────────┐
│  Telemetria de Tokens — Último Relatório │
├─────────────────────────────────────────┤
│  Custo estimado: R$ 12,45               │
│  Tokens totais: 145.230                 │
├─────────────────────────────────────────┤
│  Agente          │ Tokens │ %   │ Tempo │
│  ────────────────┼────────┼─────┼───────│
│  A0 Contexto     │ 8.351  │ 6%  │ 45s   │
│  A1 GeoScout     │ 94.590 │ 65% │ 120s  │ ← mais caro
│  A2 DemoAnalyst  │ 12.004 │ 8%  │ 8s    │
│  A3 Competitor   │ 18.230 │ 13% │ 90s   │
│  A4 Financial    │ 2.340  │ 2%  │ 15s   │
│  A5 Contact      │ 4.120  │ 3%  │ 12s   │
│  A6 Report       │ 5.595  │ 4%  │ 30s   │
└─────────────────────────────────────────┘
```

Fonte de dados: `GET /api/relatorios/{id}/custos` (agrega tokens_pipeline.csv por run_id).

---

> **Referências:**
> - `tools/token_telemetry.py` — implementação da coleta
> - `metrics/tokens_pipeline.csv` — dados brutos
> - `tools/agent_telemetry.py` — spans OTel por agente
> - LGPD Art. 7º, 9º, 46º — tratamento de dados empresariais
