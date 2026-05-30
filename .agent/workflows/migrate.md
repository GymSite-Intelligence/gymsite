---
description: Run database migrations safely. Validates schema, backs up data, applies migrations, and verifies integrity.
---

# Workflow: /migrate

Apply database migrations with zero-downtime safety.

## Prerequisites

- `DATABASE_URL` env var set
- Backup storage available
- Migration files in `db/migrations/`

## Steps

1. **Backup current schema** // turbo
   ```bash
   pg_dump $DATABASE_URL --schema-only > db/backups/schema_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Backup data (optional but recommended)**
   ```bash
   pg_dump $DATABASE_URL --data-only --table=oportunidades_prospeccao > db/backups/data_$(date +%Y%m%d_%H%M%S).sql
   ```

3. **Check pending migrations**
   ```bash
   ls -lt db/migrations/*.sql | head -5
   ```

4. **Apply migrations in order**
   ```bash
   for f in db/migrations/*.sql; do
     echo "Applying: $f"
     psql $DATABASE_URL -f "$f" || exit 1
   done
   ```

5. **Verify schema**
   ```bash
   psql $DATABASE_URL -c "\dt" | grep -E "relatorios|oportunidades|competidores"
   ```

6. **Verify indexes**
   ```bash
   psql $DATABASE_URL -c "\di" | grep idx_oportunidades
   ```

7. **Smoke test**
   ```bash
   curl -s http://localhost:8000/api/health | jq .
   ```

## Rollback

If something breaks:
```bash
# Restore from backup
psql $DATABASE_URL < db/backups/schema_YYYYMMDD_HHMMSS.sql
```

## Safety

- ⚠️ ALWAYS backup before migrating
- ⚠️ Test migrations in staging first
- ⚠️ Never run `DROP TABLE` without explicit user confirmation
