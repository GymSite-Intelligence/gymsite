# Vertex AI — guia de migração (Sprint A)

> **Estado atual (2026-05):** o projeto roda com **`GOOGLE_GENAI_USE_VERTEXAI=false`** (Developer API) para manter **Deep Research no A0**. Só ative Vertex quando o agente Deep Research estiver disponível no Vertex ou se aceitar o fallback grounded no A0.

Migração da Gemini Developer API (API Key) para **Vertex AI** no projeto `gen-lang-client-0106729343`.

## Por quê

- **IAM** em vez de API Key: nenhuma string secreta no `.env`. Pra retirar acesso, basta remover a service account.
- **Audit Log** automático via Cloud Audit Logs (LGPD compliance).
- **Cobrança consolidada** explícita no projeto, independente de qual key foi emitida.
- **Quotas de produção** (10–100× maiores).

## Trade-off

- **Região muda pra `us-central1`** porque Search Grounding **não está disponível** em `southamerica-east1` no Vertex (situação 2026-05). Search Grounding é essencial pro pipeline (A0 Deep Research, A4 aluguel, A3a enrichment). **Não dá pra desligar.**
- Latência: +200-500ms por chamada × ~30 chamadas = +6-15s no total. Pipeline 308s → ~315s. Imperceptível.

---

## Passos manuais (você faz)

### 1. Habilitar Vertex AI API

1. Abrir https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
2. Seletor de projeto no topo: **`gen-lang-client-0106729343`**
3. Clicar **Enable**

### 2. Criar Service Account

1. Abrir https://console.cloud.google.com/iam-admin/serviceaccounts
2. Confirmar projeto `gen-lang-client-0106729343`
3. **+ Create Service Account**
   - **Name:** `gymsite-pipeline`
   - **ID:** `gymsite-pipeline` (auto)
   - **Description:** `ADK Pipeline GymSite Intelligence — Vertex AI`
4. **Continue** → **Grant this service account access**:
   - Role: **Vertex AI User** (`roles/aiplatform.user`)
   - (opcional) **Service Usage Consumer** — desnecessário se o projeto da SA é o mesmo do billing
5. **Done**

### 3. Baixar a chave JSON

1. Na lista de service accounts, clicar em `gymsite-pipeline@gen-lang-client-0106729343.iam.gserviceaccount.com`
2. Aba **Keys** → **Add Key** → **Create new key**
3. Tipo: **JSON** → **Create**
4. Arquivo baixa automático: tipo `gen-lang-client-0106729343-abc123.json`
5. **Mover para um local seguro**, ex:
   ```
   C:\Users\marce\.gcp\gymsite-sa.json
   ```
   (criar pasta `.gcp` se não existir; **NÃO comitar no git**)

---

## Após os 3 passos, me avise

Eu atualizo o `.env` com:

```ini
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=gen-lang-client-0106729343
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=C:\Users\marce\.gcp\gymsite-sa.json
```

E rodo um relatório de validação que checa:
- ✓ Auth via Service Account (sem API key)
- ✓ Search Grounding funcional (A0 retorna dados de mercado atualizados)
- ✓ Persistência de tokens + custo idêntica
- ✓ Tempo de pipeline dentro de +15s da baseline

## Rollback (se algo quebrar)

```ini
# Volta pra Gemini Developer API instantaneamente:
GOOGLE_GENAI_USE_VERTEXAI=false
```

A API Key (`GOOGLE_API_KEY`) permanece no `.env` como fallback. Não precisa apagar a SA — só desativa a flag.

## Auditoria

Após migração, o Cloud Audit Logs do projeto `gen-lang-client-0106729343` mostra cada chamada Vertex feita pela SA `gymsite-pipeline`. Útil pra:
- Provar pro cliente B2B que houve isolamento de carga
- Detectar uso anômalo (alguém com a SA fazendo mais chamadas que o pipeline espera)
- Conformidade LGPD (rastreabilidade de processamento de dados)
