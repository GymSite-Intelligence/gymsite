# ✅ Integração GymSite ↔ VectraClip (Supabase)

## Status: ATIVA E FUNCIONANDO

---

## 🏗️ O que foi implementado

### 1. Trigger SQL no Supabase

**Função:** `sync_gymsite_oportunidade_to_prospect()`
**Trigger:** `trg_sync_gymsite_to_prospect` em `public.oportunidades_prospeccao`

**Comportamento:**
- Quando `status` muda para `'webhook_enviado'`, o trigger insere automaticamente em `vectraclip.prospect_profiles`
- Evita duplicatas por CNPJ
- Company ID fixo: `01b9b40e-2fc4-4cc5-a91e-cb95385d2aa2` (VECTRA IA SERVICES)

### 2. Novas colunas em `vectraclip.prospect_profiles`

```sql
ALTER TABLE vectraclip.prospect_profiles
  ADD COLUMN status text DEFAULT 'COLD',
  ADD COLUMN temperatura text DEFAULT 'frio',
  ADD COLUMN score integer DEFAULT 0,
  ADD COLUMN origem text DEFAULT 'manual',
  ADD COLUMN dados_publicos jsonb DEFAULT '{}',
  ADD COLUMN cidade text,
  ADD COLUMN uf text;
```

### 3. Modificação no `webhook.py`

Atualizado para setar `status = 'webhook_enviado'` quando o webhook é entregue com sucesso (HTTP 2xx).

---

## 🔄 Fluxo de dados

```
GymSite (prospecting)
  → webhook.py envia webhook
  → Atualiza oportunidades_prospeccao.status = 'webhook_enviado'
      → TRIGGER dispara automaticamente
      → Insere em vectraclip.prospect_profiles
          → Aparece no VectraClip (painel de prospects)
```

---

## 🗺️ Mapeamento de Campos

| GymSite (`oportunidades_prospeccao`) | VectraClip (`prospect_profiles`) |
|--------------------------------------|----------------------------------|
| `razao_social` / `nome_fantasia` | `nome_razao_social` |
| `cnpj` | `cnpj` |
| `segmento_operacao` | `setor` |
| `cidade` | `cidade` |
| `uf` | `uf` |
| `endereco_cnpj` (JSONB) | `endereco` (JSONB) |
| `contato_cnpj.telefone` | `telefone` |
| `contato_cnpj.email` | `email_contato` |
| `contato_cnpj` (completo) | `decisores` (JSONB array) |
| `nome_obra`, `situacao_obra`, `area_total_m2`, `score_match`, etc. | `dados_publicos` (JSONB) |
| `score_match` × 100 | `score` (integer, 0-100) |
| - | `status` = `COLD` |
| - | `temperatura` = `frio` |
| - | `origem` = `gymsite_auto` |

---

## 📁 Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `prospecting/webhook.py` | Atualizado para setar status = 'webhook_enviado' |
| `supabase_sync_gymsite_to_prospects.sql` | SQL da função + trigger (já aplicado) |
| `supabase/functions/gymsite-sync/index.ts` | Edge Function alternativa (não deployada) |

---

## 🚀 Como usar

### No GymSite:

1. O prospecting roda e qualifica oportunidades
2. `webhook.py` envia para o destino configurado (ou skipa se não houver URL)
3. Ao receber HTTP 2xx, atualiza `status = 'webhook_enviado'`
4. O trigger automaticamente cria o prospect no VectraClip

### No VectraClip:

1. O prospect aparece automaticamente em **Prospects**
2. Com `status = COLD`, `temperatura = frio`, `origem = gymsite_auto`
3. Campos da obra estão em `dados_publicos`
4. Pode iniciar research, outreach, etc.

---

## 🧪 Teste realizado

```sql
-- Inseriu oportunidade de teste
-- UPDATE status = 'webhook_enviado'
-- ✅ Prospect criado em vectraclip.prospect_profiles com sucesso
```

---

## ⚙️ Configuração opcional

Se quiser usar a **Edge Function** (webhook HTTP ao invés de trigger):

```bash
# Deploy (requer Docker funcionando)
supabase functions deploy gymsite-sync
```

E configurar no `.env.production`:
```env
CLAW_WEBHOOK_URL=https://epgedaiukjippepujuzc.supabase.co/functions/v1/gymsite-sync
CLAW_WEBHOOK_SECRET=sua_chave_secreta
```

---

## ✅ Checklist

- [x] Função SQL criada
- [x] Trigger ativo
- [x] Novas colunas adicionadas em prospect_profiles
- [x] webhook.py atualizado para setar status
- [x] Teste de integração validado
- [x] Score mapeado 0-1 → 0-100
- [x] Duplicatas evitadas por CNPJ
