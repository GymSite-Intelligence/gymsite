---
description: Backup operacional — dump Supabase + inventário de secrets (sem valores) + artifacts opcionais. PowerShell.
---

# Workflow: /backup

> **Canônico:** P-000 §7 (projeto `epgedaiukjippepujuzc`) · `/migrate` pré-DDL.
> **Removido (legado):** `docker-compose.yml`, `competitor_cache/`, `.env.example` na raiz como “config completa”, Bash `date +%Y%m%d` sem nota Windows.
> Shell: **PowerShell**. Git Bash/WSL ok se adaptar paths — não misturar sem cuidado.

## O que entra

| Item | Como |
|---|---|
| Schema + dados críticos | Dump Supabase / `pg_dump` (schemas `gymsite`, `shared`, views `public` se necessário) |
| Inventário de secrets | Nomes das env vars / secrets Cloud Run + CF — **nunca** valores no zip |
| Artifacts | Opcional: `artifacts/` PDFs recentes |
| Código | Já no Git — não duplicar tree inteira no backup |

## Steps

1. **Diretório** // turbo
   ```powershell
   $ts = Get-Date -Format "yyyyMMdd_HHmmss"
   $BACKUP_DIR = "backups\$ts"
   New-Item -ItemType Directory -Force -Path $BACKUP_DIR | Out-Null
   Write-Host "Backup dir: $BACKUP_DIR"
   ```

2. **Dump banco**
   Preferência: Supabase Dashboard → Database → Backups / ou CLI:
   ```powershell
   # Requer DATABASE_URL (service) — NÃO commitar o .sql
   pg_dump $env:DATABASE_URL --schema=gymsite --schema=shared -f "$BACKUP_DIR\db_gymsite_shared.sql"
   ```
   Alternativa mínima pré-migrate: só tabelas tocadas (`--table=gymsite.foo`).

3. **Inventário de secrets (sem valores)**
   ```powershell
   @"
   # Nomes apenas — preencher check manual
   - Cloud Run gymsite-api / gymsite-worker env + Secret Manager
   - SEARCHAPI_KEY, REDIS_URL, SUPABASE_SERVICE_ROLE_KEY
   - CF Pages VITE_* / wrangler
   - APOLLO_* (se prospecção)
   "@ | Set-Content "$BACKUP_DIR\secrets_inventory.txt"
   ```
   Listar nomes via:
   ```powershell
   gcloud run services describe gymsite-api --region=us-central1 --project=gen-lang-client-0106729343 --format="yaml(spec.template.spec.containers[0].env)" | Select-String "name:"
   ```

4. **Artifacts (opcional)**
   ```powershell
   if (Test-Path artifacts) {
     Copy-Item -Recurse artifacts "$BACKUP_DIR\artifacts"
   }
   ```

5. **Manifest**
   ```powershell
   @{
     timestamp = (Get-Date).ToString("o")
     schemas   = @("gymsite", "shared")
     note      = "No secret values. DB dump may contain PII — store securely."
   } | ConvertTo-Json | Set-Content "$BACKUP_DIR\manifest.json"
   Get-ChildItem $BACKUP_DIR -Recurse | Select-Object FullName, Length
   ```

## Restore

- Banco: restore dump completo ou PITR Supabase — **não** confundir schema-only com undo de dados.
- Secrets: recriar no Secret Manager / CF a partir do cofre — não a partir do inventário sozinho.
- Artifacts: copiar de volta se preciso.

## Safety

- ⚠️ Dump = dados sensíveis — fora do Git; storage criptografado
- ⚠️ Nunca copiar `.env` real para `backups/` versionado
- ⚠️ Verificar tamanho/arquivo `.sql` não-vazio antes de apagar origem
